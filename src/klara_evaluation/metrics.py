import re
import unicodedata

import jiwer

from klara_evaluation.normalization import SENTINEL

_WORD_RE = re.compile(r"[\w\-]+")


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(unicodedata.normalize("NFC", text).lower())


# Order matters:
#   "z.B." / "i.v."      dotted abbreviations stay one token, or every dot would
#                        count as its own punctuation edit
#   "6,0" / "29.06.2025" numbers keep their internal separators - a decimal comma
#                        is notation, not a punctuation choice
#   "Flow-Profil"        hyphen/apostrophe compounds stay one word (both apostrophes:
#                        the typographic one occurs in real transcripts)
#   "." "," ":" "¶"      every remaining non-space glyph is its own token
_FORMATTED_TOKEN_RE = re.compile(
    r"(?:[^\W\d_]\.){2,}"
    r"|\d+(?:[.,:/]\d+)*"
    r"|[^\W\d_]+(?:[-'’][^\W\d_]+)*"  # noqa: RUF001
    r"|[^\s\w]"
)

# Line breaks become one visible token. Pilcrow rather than "\n" because tokens
# pass through a whitespace join before alignment.
_BREAK = "¶"


def tokenize_formatted(text: str) -> list[str]:
    """Tokens for :func:`fwer_counts`: case kept, punctuation kept, breaks kept."""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\r\n]+", f" {_BREAK} ", text)
    return _FORMATTED_TOKEN_RE.findall(text)


def _chunks(ref_tokens: list[str], hyp_tokens: list[str]):
    out = jiwer.process_words(" ".join(ref_tokens), " ".join(hyp_tokens))
    return out.alignments[0]


def wer_counts(ref: str, hyp: str) -> tuple[int, int]:
    """(edits, n_ref_tokens). Inserted sentinels are free, missing reference marks
    are deletions. An empty reference charges the hypothesis as insertions."""
    ref_tokens, hyp_tokens = tokenize(ref), tokenize(hyp)
    if not ref_tokens:
        return sum(1 for t in hyp_tokens if t != SENTINEL), 0
    if not hyp_tokens:
        return len(ref_tokens), len(ref_tokens)
    edits = 0
    for c in _chunks(ref_tokens, hyp_tokens):
        if c.type in ("substitute", "delete"):
            edits += c.ref_end_idx - c.ref_start_idx
        elif c.type == "insert":
            edits += sum(
                1 for t in hyp_tokens[c.hyp_start_idx:c.hyp_end_idx]
                if t != SENTINEL
            )
    return edits, len(ref_tokens)


def fwer_counts(ref: str, hyp: str) -> tuple[int, int]:
    """(edits, n_ref_tokens) on the raw texts, formatting scored: case,
    punctuation choice and line breaks all count. Pass raw strings, not
    `Normalized` fields."""
    ref_tokens, hyp_tokens = tokenize_formatted(ref), tokenize_formatted(hyp)
    if not ref_tokens:
        return len(hyp_tokens), 0
    if not hyp_tokens:
        return len(ref_tokens), len(ref_tokens)
    edits = 0
    for c in _chunks(ref_tokens, hyp_tokens):
        if c.type in ("substitute", "delete"):
            edits += c.ref_end_idx - c.ref_start_idx
        elif c.type == "insert":
            edits += c.hyp_end_idx - c.hyp_start_idx
    return edits, len(ref_tokens)


# Shorter terms get no recovery, so a 2-3 char term cannot match as an
# incidental substring.
_MIN_RECOVERABLE_TERM_CHARS = 4


def _decomposes_into_terms(residue: str, termset: set[str]) -> bool:
    """True if `residue` is consumed by stripping term tokens from its ends, i.e.
    the material glued around a term is itself medical content."""
    toks = sorted((t for t in termset if t), key=len, reverse=True)
    changed = True
    while residue and changed:
        changed = False
        for t in toks:
            if residue.startswith(t):
                residue = residue[len(t):]
                changed = True
                break
            if residue.endswith(t):
                residue = residue[:-len(t)]
                changed = True
                break
    return residue == ""


def _term_still_present(ref_tokens, a, b, hyp_tokens, chunks, termset, recovery) -> bool:
    """Whether a term span [a, b) that alignment flagged wrong is still present
    in the aligned hypothesis window (± 1 token): as a contiguous run of whole
    tokens (split), or inside one token whose residue decomposes into other
    terms (glued). "relaxed" stops at plain containment (ablation only).
    One-directional, so dropped syllables stay errors."""
    ref_join = "".join(
        t.replace("-", "") for t in ref_tokens[a:b] if t != SENTINEL
    )
    if len(ref_join) < _MIN_RECOVERABLE_TERM_CHARS:
        return False
    hyp_lo: int | None = None
    hyp_hi: int | None = None
    for c in chunks:
        if c.ref_start_idx < b and c.ref_end_idx > a:
            hyp_lo = c.hyp_start_idx if hyp_lo is None else min(hyp_lo, c.hyp_start_idx)
            hyp_hi = c.hyp_end_idx if hyp_hi is None else max(hyp_hi, c.hyp_end_idx)
    if hyp_lo is None:
        return False
    w0 = max(0, hyp_lo - 1)
    w1 = min(len(hyp_tokens), hyp_hi + 1)
    win = [t.replace("-", "") for t in hyp_tokens[w0:w1] if t != SENTINEL]
    if ref_join not in "".join(win):
        return False
    if recovery == "relaxed":
        return True
    # (a) pure split - a contiguous run of whole window tokens == the term
    for i in range(len(win)):
        acc = ""
        for j in range(i, len(win)):
            acc += win[j]
            if acc == ref_join:
                return True
            if len(acc) > len(ref_join):
                break
    # (b) glue - term inside one host token, residue decomposes into terms
    for host in win:
        idx = host.find(ref_join)
        if idx < 0:
            continue
        residue = host[:idx] + host[idx + len(ref_join):]
        if _decomposes_into_terms(residue, termset):
            return True
    return False


def _term_spans(ref_tokens: list[str], terms: list[str]) -> list[tuple[int, int]]:
    """Token spans of each term word in the reference. Multi-word terms are
    matched per word so a partial hit still credits the recognized words."""
    spans: list[tuple[int, int]] = []
    for term in terms:
        for word in term.split():
            term_tokens = tokenize(word)
            if not term_tokens:
                continue
            m = len(term_tokens)
            for i in range(len(ref_tokens) - m + 1):
                if ref_tokens[i:i + m] == term_tokens:
                    spans.append((i, i + m))
    return spans


def mer_counts(
    ref: str, hyp: str, terms: list[str], recovery: str = "segmentation"
) -> tuple[int, int]:
    """(wrong_spans, total_spans). `terms` must be normalized like `ref` and
    `hyp`. A span is wrong if alignment flagged it and `_term_still_present` cannot
    find it, so re-segmentation counts as recognized where WER would charge it.

    `recovery`: "segmentation" (reported), "exact" (no recovery) or "relaxed"
    (containment only, ablation)."""
    if recovery not in ("exact", "segmentation", "relaxed"):
        raise ValueError(f"unknown recovery mode: {recovery!r}")
    ref_tokens, hyp_tokens = tokenize(ref), tokenize(hyp)
    spans = _term_spans(ref_tokens, terms)
    if not spans:
        return 0, 0
    if not hyp_tokens:
        return len(spans), len(spans)
    chunks = _chunks(ref_tokens, hyp_tokens)
    ref_wrong = [False] * len(ref_tokens)
    for c in chunks:
        if c.type in ("substitute", "delete"):
            for r in range(c.ref_start_idx, c.ref_end_idx):
                ref_wrong[r] = True
    termset = {ref_tokens[i].replace("-", "") for (a, b) in spans for i in range(a, b)}
    wrong = 0
    for (a, b) in spans:
        if not any(ref_wrong[a:b]):
            continue
        if recovery != "exact" and _term_still_present(
            ref_tokens, a, b, hyp_tokens, chunks, termset, recovery
        ):
            continue
        wrong += 1
    return wrong, len(spans)


def nmer_counts(ref: str, hyp: str, terms: list[str]) -> tuple[int, int]:
    """(edits, n_tokens) outside every term span, the complement of mer_counts.
    Insertions are charged to the neighbouring region. Sentinels stay free."""
    ref_tokens, hyp_tokens = tokenize(ref), tokenize(hyp)
    non_med = [True] * len(ref_tokens)
    for a, b in _term_spans(ref_tokens, terms):
        for i in range(a, b):
            non_med[i] = False
    n_nm = sum(non_med)
    if not ref_tokens:
        return sum(1 for t in hyp_tokens if t != SENTINEL), 0
    if not hyp_tokens:
        return n_nm, n_nm
    edits = 0
    for c in _chunks(ref_tokens, hyp_tokens):
        if c.type in ("substitute", "delete"):
            edits += sum(1 for r in range(c.ref_start_idx, c.ref_end_idx) if non_med[r])
        elif c.type == "insert":
            n_ins = sum(
                1 for t in hyp_tokens[c.hyp_start_idx:c.hyp_end_idx]
                if t != SENTINEL
            )
            neighbor = (
                c.ref_start_idx
                if 0 <= c.ref_start_idx < len(ref_tokens)
                else c.ref_start_idx - 1
            )
            in_med = not non_med[neighbor] if 0 <= neighbor < len(ref_tokens) else False
            if not in_med:
                edits += n_ins
    return edits, n_nm

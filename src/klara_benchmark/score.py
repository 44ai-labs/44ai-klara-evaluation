import json
import re
from datetime import datetime
from typing import NamedTuple

from klara_benchmark import RESULTS_DIR, ROOT, TRANSCRIPTIONS_DIR, datasets, paper
from klara_evaluation import Normalized, fwer_counts, mer_counts, normalize, wer_counts

STAGES = list(Normalized.model_fields)
assert STAGES[-1] == "final", "score_system reads the final stage off the stage loop"

# Which reference a run's WER is scored against on a set that ships a formatted term list: the
# spoken-form one for the runs that return the words as dictated, the formatted one for the runs
# that return formatted text. A set without that list is scored against the spoken form throughout.
UNFORMATTED_SYSTEMS = [
    "elevenlabs", "elevenlabs-medical", "gpt-4o", "deepgram", "soniox", "mai-transcribe", "whisper",
    "cohere", "corti", "nemotron",
]
FORMATTED_SYSTEMS = [
    "dmo", "klara", "corti-formatted", "elevenlabs-formatted", "elevenlabs-medical-formatted",
    "gpt-4o-formatted", "mai-transcribe-formatted", "nemotron-formatted",
]
CHUNKED = "\\*"
SPOKEN_FORM = "\u2020"

# Dictation commands a clinician speaks and a report must not contain as words.
_COMMANDS = (
    "Punkt", "Komma", "Doppelpunkt", "Strichpunkt", "Semikolon", "Fragezeichen", "Ausrufezeichen",
    "Klammer auf", "Klammer zu", "Schrägstrich", "Neue Zeile", "Neuer Absatz", "Neuer Abschnitt",
)
_COMMAND_RE = {c: re.compile(rf"\b{c}\b", re.IGNORECASE) for c in _COMMANDS}
_UNIT = "(?:ein|zwei|drei|vier|fünf|sechs|sieben|acht|neun)"
_TENS = "(?:zwanzig|dreißig|dreissig|vierzig|fünfzig|sechzig|siebzig|achtzig|neunzig)"
_TEEN = "(?:zehn|elf|zwölf|dreizehn|vierzehn|fünfzehn|sechzehn|siebzehn|achtzehn|neunzehn)"
# A number written out: "zwölf", "fünfunddreißig", "einhundertfünfzehn". "ein(s)" alone is left out,
# it is an article more often than a number.
_NUMBER_WORD = re.compile(
    rf"\b(?:{_UNIT}?(?:hundert|tausend)(?:{_UNIT}|{_TEEN}|{_TENS}|und)*|(?:{_UNIT}und)?{_TENS}|{_TEEN}"
    r"|zwei|drei|vier|fünf|sechs|sieben|acht|neun)\b",
    re.IGNORECASE,
)


def formatting_behaviour(hypotheses: dict[int, str], rows: list[dict]) -> dict[str, float]:
    """How a system treats dictated formatting, in % of the clips where it applies.

    `commands`: of the clips whose spoken reference holds a command word that the formatted
    reference no longer has, the share where none of those words is left in the output.
    `numbers`: of the clips whose formatted reference writes numbers as digits only, the share
    where the output has no written-out number either."""
    command_clips = command_done = number_clips = number_done = 0
    for row in rows:
        hyp = hypotheses.get(row["id"], "")
        spoken, written = row["reference"], row["formatted_reference"]
        dictated = [c for c, rx in _COMMAND_RE.items() if rx.search(spoken) and not rx.search(written)]
        if dictated:
            command_clips += 1
            command_done += not any(_COMMAND_RE[c].search(hyp) for c in dictated)
        if re.search(r"\d", written) and not _NUMBER_WORD.search(written):
            number_clips += 1
            number_done += not _NUMBER_WORD.search(hyp)
    return {
        "commands": 100 * command_done / command_clips if command_clips else 0.0,
        "numbers": 100 * number_done / number_clips if number_clips else 0.0,
    }


class Counts(NamedTuple):
    word_edits: int = 0
    words: int = 0
    terms_wrong: int = 0
    terms: int = 0

    def plus(self, other: "Counts") -> "Counts":
        return Counts(*(a + b for a, b in zip(self, other, strict=True)))


def _read(path) -> dict[int, str]:
    with open(path) as f:
        return {r["id"]: r["hypothesis"] for r in map(json.loads, f)}


def load_hypotheses(system: str, ds_name: str) -> tuple[dict[int, str] | None, bool]:
    """(hypotheses keyed by row id, chunked_input). A system fed a Corti set's
    chunked view has clip transcripts on disk (`<set>.chunks.jsonl`); they are
    joined per recording, so it is scored against the same full-length
    references as every other system."""
    full = TRANSCRIPTIONS_DIR / system / f"{ds_name}.jsonl"
    if full.exists():
        return _read(full), False
    clips = TRANSCRIPTIONS_DIR / system / f"{ds_name}.chunks.jsonl"
    if clips.exists() and ds_name in datasets.VIEWS:
        return datasets.join_clips(datasets.VIEWS[ds_name], _read(clips)), True
    return None, False


def score_system(
    hypotheses: dict[int, str], rows: list[dict], wer_refs: list[tuple], mer_refs: list[tuple]
) -> dict:
    wer = {s: [0, 0] for s in STAGES}
    fwer = [0, 0]
    mer = [0, 0]
    by_group: dict[str, Counts] = {}
    by_dialect: dict[str, Counts] = {}
    # Each metric's reference and term list move together, so the hypothesis
    # is normalized once per lexicon.
    for row, (ref_n, _terms_n, terms_raw), (mer_ref_n, mer_terms_n, mer_terms_raw) in zip(
        rows, wer_refs, mer_refs, strict=True
    ):
        hyp_raw = hypotheses.get(row["id"], "")
        hyp_n = normalize(hyp_raw, terms_raw)
        for stage in STAGES:
            edits, n_ref = wer_counts(getattr(ref_n, stage), getattr(hyp_n, stage))
            wer[stage][0] += edits
            wer[stage][1] += n_ref
        final_edits, final_ref = edits, n_ref
        # fWER on the raw pair, against the formatted reference: the verbatim
        # one spells punctuation as dictation commands ("Komma").
        f_edits, f_ref = fwer_counts(row["formatted_reference"], hyp_raw)
        fwer[0] += f_edits
        fwer[1] += f_ref
        hyp_m = normalize(hyp_raw, mer_terms_raw, split_compounds=True)
        wrong, total = mer_counts(mer_ref_n.final, hyp_m.final, mer_terms_n)
        mer[0] += wrong
        mer[1] += total
        row_counts = Counts(final_edits, final_ref, wrong, total)
        for key, breakdown in ((row.get("group"), by_group), (row.get("dialect"), by_dialect)):
            if key:
                breakdown[key] = breakdown.get(key, Counts()).plus(row_counts)
    def pct(num: int, den: int) -> float:
        return 100 * num / den if den else 0.0

    return {
        "wer": {s: pct(*wer[s]) for s in STAGES},
        "fwer": pct(*fwer),
        "mer": pct(*mer),
        "by_group": {
            g: {"wer": pct(c.word_edits, c.words), "mer": pct(c.terms_wrong, c.terms)}
            for g, c in by_group.items()
        },
        # Raw counts kept so paper.py can pool dialects into groups.
        "by_dialect": {
            d: {"wer": pct(c.word_edits, c.words), "mer": pct(c.terms_wrong, c.terms), "counts": c}
            for d, c in by_dialect.items()
        },
    }


def _plain(name: str) -> str:
    """A display name of the paper without its LaTeX."""
    return re.sub(r"\\textsubscript\{([^}]*)\}", r" \1", name.replace(r"\klara{} (ours)", "Klara"))


def _accuracy(score: dict) -> tuple[float, ...]:
    return 100 - score["fwer"], 100 - score["wer"]["final"], 100 - score["mer"]


def _accuracy_table(rows: list[tuple[str, tuple[float, ...]]], first: str = "System") -> list[str]:
    return [
        f"| {first} | Formatted | Word | Medical terms |", "|---|---:|---:|---:|",
        *(
            f"| {label} | " + " | ".join(f"{v:.2f}" for v in acc) + " |"
            for label, acc in sorted(rows, key=lambda row: -row[1][0])
        ),
        "",
    ]


def report(all_scores: dict, hours: dict[str, float]) -> str:
    """Markdown: each system in the configuration it is reported with, then every run."""
    sets = list(all_scores)

    def label(name: str, run: str, on: list[str]) -> str:
        chunked = any(all_scores[ds][run]["chunked_input"] for ds in on)
        spoken = run in UNFORMATTED_SYSTEMS and any(
            datasets.DATASETS[ds].formatted_terms_column for ds in on
        )
        return name + (CHUNKED if chunked else "") + (SPOKEN_FORM if spoken else "")

    def combined(run: str) -> tuple[float, ...]:
        total = sum(hours[ds] for ds in sets)
        return tuple(
            sum(_accuracy(all_scores[ds][run])[i] * hours[ds] for ds in sets) / total for i in range(3)
        )

    reported = [(_plain(name), run) for name, _, run, _ in paper.PRODUCTS]
    everywhere = [run for run in all_scores[sets[0]] if all(run in all_scores[ds] for ds in sets)]
    lines = [
        f"# Results - {datetime.now():%Y-%m-%d %H:%M}", "",
        "Accuracy in %, as 100 minus the error rate: formatted (fWER), word (WER) and medical term (MER)",
        "accuracy. Each system is listed in the configuration it is reported with. The second to last",
        "section lists every run.", "",
        f"{CHUNKED} The system received MedTerm and MedDictate as clips of at most 30 s.  ",
        f"{SPOKEN_FORM} On MedTerm and MedDictate, word accuracy is scored against the spoken-form",
        "reference, for all other runs against the formatted reference. On 44ai-clinical-val every run",
        "is scored against the spoken-form reference, the only form in which that set has a term list.",
        "",
        "## All three test sets, weighted by audio duration", "",
        *_accuracy_table(
            [(label(name, run, sets), combined(run)) for name, run in reported if run in everywhere]
        ),
    ]
    for ds in sets:
        rows = [
            (label(name, run, [ds]), _accuracy(all_scores[ds][run]))
            for name, run in reported if run in all_scores[ds]
        ]
        lines += [f"## {ds}", "", *_accuracy_table(rows)]
    lines += [
        "## Every run, all three test sets", "",
        *_accuracy_table([(label(run, run, sets), combined(run)) for run in everywhere], first="Run"),
        "## WER in % after each normalization stage", "",
    ]
    for ds in sets:
        runs = sorted(all_scores[ds], key=lambda run: all_scores[ds][run]["wer"]["final"])
        lines += [
            f"### {ds}", "",
            "| Run | " + " | ".join(STAGES) + " |", "|---|" + "---:|" * len(STAGES),
            *(
                f"| {label(run, run, [ds])} | "
                + " | ".join(f"{all_scores[ds][run]['wer'][stage]:.2f}" for stage in STAGES) + " |"
                for run in runs
            ),
            "",
        ]
    return "\n".join(lines)


def main() -> None:
    systems = sorted(
        d.name for d in TRANSCRIPTIONS_DIR.iterdir()
        if d.is_dir() and any(d.glob("*.jsonl"))
    ) if TRANSCRIPTIONS_DIR.exists() else []
    if not systems:
        raise SystemExit("no transcriptions found - run `make evaluate <system> ...` first")

    all_scores: dict[str, dict] = {}
    hours: dict[str, float] = {}
    for ds_name in datasets.SCORED:
        rows = datasets.load(ds_name, with_audio=False)
        hours[ds_name] = datasets.audio_hours(ds_name)
        verb_refs, fmt_refs, mer_refs = [], [], []
        for row in rows:
            terms = row["medical_terms"]
            verb_refs.append((normalize(row["reference"], terms),
                              [normalize(t, terms).final for t in terms], terms))
            fmt_text, fmt_terms = datasets.mer_pair(row)
            fmt_refs.append((normalize(fmt_text, fmt_terms),
                             [normalize(t, fmt_terms).final for t in fmt_terms], fmt_terms))
            # MER matches terms per word span, so its path splits hyphenated
            # compounds. Reference, hypothesis and terms must agree on it.
            mer_refs.append((normalize(fmt_text, fmt_terms, split_compounds=True),
                             [normalize(t, fmt_terms, split_compounds=True).final for t in fmt_terms],
                             fmt_terms))

        scores = {}
        for system in systems:
            hypotheses, chunked_input = load_hypotheses(system, ds_name)
            if hypotheses is not None:
                # Formatted systems score WER against the formatted reference:
                # normalization cannot bridge glued numbers, units and
                # punctuation words. MER uses the MER pair either way.
                wer_refs = fmt_refs if system in FORMATTED_SYSTEMS else verb_refs
                scores[system] = {**score_system(hypotheses, rows, wer_refs, mer_refs),
                                  "chunked_input": chunked_input}
                if ds_name == paper.FORMATTING_DS:
                    scores[system]["formatting"] = formatting_behaviour(hypotheses, rows)
        all_scores[ds_name] = scores

    text = report(all_scores, hours)
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"result_{datetime.now():%Y%m%d_%H%M%S}.md"
    out.write_text(text)
    print(text)
    print(f"-> {out.relative_to(ROOT)}")
    for name, content in paper.paper_files(all_scores, hours).items():
        path = RESULTS_DIR / name
        path.write_text(content)
        print(f"-> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

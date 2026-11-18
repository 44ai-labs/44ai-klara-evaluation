import re
import unicodedata

from pydantic import BaseModel

# Alphanumeric so it survives tokenization. Spoken punctuation words, glyphs and
# line breaks all fold to it: presence of a mark is scored, choice of mark is not.
SENTINEL = "puncttoken"


class Normalized(BaseModel):
    """Cumulative snapshots of the pipeline; `final` is what the metrics see."""

    raw: str
    cleaned: str      # NFC, lowercase, line breaks -> sentinel
    symbols: str      # % / ° / ‰ -> German words
    numbers: str      # number words -> digits
    dates: str        # dates and times -> one shared digit form
    units: str        # unit words -> canonical abbreviation
    compounds: str    # joined/hyphenated/split spellings of listed terms -> one form
    latinate: str     # curated attested spelling variants -> German-preferred form
    abbreviations: str  # known clinical abbreviation <-> spelled-out phrase -> one form
    punctuation: str  # spoken punctuation words and glyphs -> sentinel
    final: str        # umlaut/eszett folding (ä->ae, ö->oe, ü->ue, ß->ss)


# Numbers
# German cardinals are one compound word ("zweiundvierzig"):
# <thousands>tausend<hundreds>hundert<unit>und<tens>. Bare "ein" is the article, not 1.

TEENS = {
    "zehn": 10, "elf": 11, "zwoelf": 12, "zwölf": 12, "dreizehn": 13,
    "vierzehn": 14, "fuenfzehn": 15, "fünfzehn": 15, "sechzehn": 16,
    "siebzehn": 17, "achtzehn": 18, "neunzehn": 19,
}
TENS = {
    "zwanzig": 20, "dreissig": 30, "dreißig": 30, "vierzig": 40,
    "fuenfzig": 50, "fünfzig": 50, "sechzig": 60, "siebzig": 70,
    "achtzig": 80, "neunzig": 90,
}
# "zwo" is the spoken telephone/dictation variant of "zwei".
UNITS = {
    "null": 0, "eins": 1, "zwei": 2, "zwo": 2, "drei": 3, "vier": 4, "fuenf": 5,
    "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9,
}
_COMPOUND_UNIT = {
    "ein": 1, "zwei": 2, "drei": 3, "vier": 4, "fuenf": 5, "fünf": 5,
    "sechs": 6, "sieben": 7, "acht": 8, "neun": 9,
}


def _parse_under_100(s: str) -> int | None:
    if not s:
        return None
    if s in TENS:
        return TENS[s]
    if s in TEENS:
        return TEENS[s]
    if s in UNITS:
        return UNITS[s]
    if "und" in s:
        for cut in range(1, len(s) - 2):
            if s[cut:cut + 3] != "und":
                continue
            unit_part, tens_part = s[:cut], s[cut + 3:]
            if unit_part in _COMPOUND_UNIT and tens_part in TENS:
                return _COMPOUND_UNIT[unit_part] + TENS[tens_part]
    return None


def _parse_under_1000(s: str) -> int | None:
    if not s:
        return None
    v = _parse_under_100(s)
    if v is not None:
        return v
    if "hundert" in s:
        idx = s.find("hundert")
        prefix, suffix = s[:idx], s[idx + len("hundert"):]
        if prefix == "":
            mult = 1
        elif prefix in _COMPOUND_UNIT:
            mult = _COMPOUND_UNIT[prefix]
        else:
            # A teen/tens multiplier: "neunzehn"hundert = 1900 (spoken years).
            mult = _parse_under_100(prefix)
            if mult is None:
                return None
        rest = 0 if suffix == "" else _parse_under_100(suffix)
        if rest is None:
            return None
        return mult * 100 + rest
    return None


def _parse_number_word(word: str) -> int | None:
    s = word.replace("ß", "ss")
    if not s or s.isdigit():
        return None
    if "tausend" in s:
        idx = s.find("tausend")
        prefix, suffix = s[:idx], s[idx + len("tausend"):]
        mult = 1 if prefix == "" else _parse_under_1000(prefix)
        if mult is None:
            return None
        rest = 0 if suffix == "" else _parse_under_1000(suffix)
        if rest is None:
            return None
        return mult * 1000 + rest
    return _parse_under_1000(s)


# Ordinal stem (cardinal + "t"/"st", or irregular) + declension ending. The stem
# must be a number, so "letzte" is not one.
_ORDINAL_DECLENSION = ("en", "em", "er", "es", "e")
_IRREGULAR_ORDINAL_STEMS = {
    "erst": 1, "dritt": 3, "siebt": 7, "siebent": 7, "acht": 8,
}


def _parse_ordinal_word(word: str) -> int | None:
    s = word.replace("ß", "ss")
    if not s or s.isdigit():
        return None
    stem = s
    for end in _ORDINAL_DECLENSION:
        if s.endswith(end) and len(s) - len(end) >= 3:
            stem = s[: -len(end)]
            break
    if stem in _IRREGULAR_ORDINAL_STEMS:
        return _IRREGULAR_ORDINAL_STEMS[stem]
    if stem.endswith("st") and len(stem) > 2:
        v = _parse_number_word(stem[:-2])
        if v is not None:
            return v
    if stem.endswith("t") and len(stem) > 1:
        v = _parse_number_word(stem[:-1])
        if v is not None:
            return v
    return None


_PUNCT_CHARS = ".,;:!?\"'()[]{}"


def _split_punct(word: str) -> tuple[str, str, str]:
    """(core, leading_punct, trailing_punct) - core is lowercased."""
    i, j = 0, len(word)
    while i < j and word[i] in _PUNCT_CHARS:
        i += 1
    while j > i and word[j - 1] in _PUNCT_CHARS:
        j -= 1
    return word[i:j].lower(), word[:i], word[j:]


def _canonical_number(core: str) -> int | None:
    v = _parse_number_word(core)
    if v is not None:
        return v
    v = _parse_ordinal_word(core)
    if v is not None:
        return v
    if core.isdigit() and len(core) > 1 and core[0] == "0":
        return int(core)  # "08" -> 8, so digit dates/times line up with words
    return None


def _fold_decimal_komma(words: list[str]) -> list[str]:
    """Merge '<digits> komma <digits>' into one '<digits>,<digits>' token."""
    out: list[str] = []
    i, n = 0, len(words)
    while i < n:
        if i + 2 < n:
            core1, lead1, trail1 = _split_punct(words[i])
            mid, _, _ = _split_punct(words[i + 1])
            core2, _, trail2 = _split_punct(words[i + 2])
            if core1.isdigit() and not trail1 and mid == "komma" and core2.isdigit():
                out.append(f"{lead1}{core1},{core2}{trail2}")
                i += 3
                continue
        out.append(words[i])
        i += 1
    return out


def _fold_letter_number(words: list[str]) -> list[str]:
    """Merge letter + digit-led token: codes spoken as two words but written
    glued (T1, N0, B12)."""
    out: list[str] = []
    i, n = 0, len(words)
    while i < n:
        if i + 1 < n:
            core1, _, trail1 = _split_punct(words[i])
            if len(core1) == 1 and core1.isalpha() and not trail1:
                core2 = _split_punct(words[i + 1])[0]
                if core2[:1].isdigit():
                    out.append(words[i] + words[i + 1])
                    i += 2
                    continue
        out.append(words[i])
        i += 1
    return out


# Thousands dot ("18.200" == "18200") and spaced range ("16 bis 18" == "16-18")
# are notation. The guards keep "0.005" and dates like "15.04.2024" untouched.
_THOUSANDS_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+)(?!\d)")
_RANGE_BIS_RE = re.compile(r"(?<=\d)\s+bis\s+(?=\d)")


def _drop_thousands(m: re.Match) -> str:
    groups = m.group(1)
    return m.group(0) if groups.startswith("0.") else groups.replace(".", "")


def normalize_numbers(text: str) -> str:
    converted = []
    for word in text.split(" "):
        if not word:
            converted.append(word)
            continue
        core, lead, trail = _split_punct(word)
        if not core:
            converted.append(word)
            continue
        if "-" in core:
            # "eins-Hypointensität" -> "1-Hypointensität", "Provox-zwei" -> "Provox-2"
            parts = core.split("-")
            conv = [_canonical_number(p) for p in parts]
            if any(c is not None for c in conv):
                joined = "-".join(str(c) if c is not None else p for c, p in zip(conv, parts, strict=True))
                converted.append(f"{lead}{joined}{trail}")
                continue
            converted.append(word)
            continue
        parsed = _canonical_number(core)
        converted.append(f"{lead}{parsed}{trail}" if parsed is not None else word)
    converted = _fold_letter_number(converted)
    out = " ".join(_fold_decimal_komma(converted))
    # After the word->digit pass, so a spelled-out "drei bis fünf" folds like "3 bis 5".
    out = _RANGE_BIS_RE.sub("-", out)
    return _THOUSANDS_RE.sub(_drop_thousands, out)


# Dates & times
# "15. April 2024", "15.04.2024" and "fünfzehnten vierten zweitausendvierundzwanzig"
# are the same date. Runs after the number pass.

_MONTHS = {
    "januar": "1", "februar": "2", "märz": "3", "maerz": "3", "april": "4",
    "mai": "5", "juni": "6", "juli": "7", "august": "8", "september": "9",
    "oktober": "10", "november": "11", "dezember": "12",
}
_MONTH_RE = re.compile(r"\b(" + "|".join(_MONTHS) + r")\b")


def _normalize_dates_times(text: str) -> str:
    # "15.04.2024" -> "15 4 2024" (split, drop leading zeros).
    text = re.sub(
        r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b",
        lambda m: f"{int(m[1])} {int(m[2])} {int(m[3])}",
        text,
    )
    # Two-word spoken year "zwanzig dreiundzwanzig" -> "20 23" -> "2023".
    text = re.sub(r"\b(19|20)\s+(\d{2})\b", lambda m: f"{m[1]}{m[2]}", text)
    text = _MONTH_RE.sub(lambda m: _MONTHS[m.group(1)], text)
    # Times: "14:20" / "14:20 uhr" / "14.20 uhr" / "14 uhr 20" -> "14 uhr 20".
    text = re.sub(
        r"\b(\d{1,2}):(\d{2})\b(?:\s*uhr)?",
        lambda m: f"{int(m[1])} uhr {int(m[2])}", text,
    )
    text = re.sub(
        r"\b(\d{1,2})\.(\d{2})\s+uhr\b",
        lambda m: f"{int(m[1])} uhr {int(m[2])}", text,
    )
    text = re.sub(
        r"\b(\d{1,2})\s+uhr\s+(\d{1,2})\b",
        lambda m: f"{int(m[1])} uhr {int(m[2])}", text,
    )
    return text


# Symbols
# Glyphs vanish in tokenization while a spoken "Prozent" survives, so expand
# them to words first.


def _normalize_symbols(text: str) -> str:
    text = text.replace("≥", " groesser gleich ").replace("≤", " kleiner gleich ")
    text = text.replace(">=", " groesser gleich ").replace("<=", " kleiner gleich ")
    text = re.sub(r"°\s*c\b", " grad celsius ", text)
    text = text.replace("°", " grad ")
    text = text.replace("%", " prozent ")
    text = text.replace("‰", " promille ")
    return text


# Units
# References spell units out, models abbreviate. "mikrogramm" -> "ug" stays
# distinct from "mg": a µg/mg confusion is a dose error.

_UNIT_MULTIWORD: list[tuple[tuple[str, ...], str]] = [
    (("millimeter", "quecksilbersäule"), "mmhg"),
    (("millimeter", "quecksilbersaeule"), "mmhg"),
    (("mm", "hg"), "mmhg"),
    (("mm", "quecksilbersäule"), "mmhg"),
    (("mm", "quecksilbersaeule"), "mmhg"),
    # "pro X" is the spoken form of "/X", and tokenization drops the slash.
    (("pro", "deziliter"), "/dl"),
    (("pro", "dl"), "/dl"),
    (("pro", "liter"), "/l"),
    (("pro", "l"), "/l"),
    (("pro", "milliliter"), "/ml"),
    (("pro", "ml"), "/ml"),
    (("pro", "minute"), "/min"),
    (("pro", "minuten"), "/min"),
    (("pro", "min"), "/min"),
    (("pro", "kilogramm"), "/kg"),
    (("pro", "kg"), "/kg"),
    (("pro", "stunde"), "/h"),
]
_UNIT_WORD = {
    "millimeter": "mm", "millimetern": "mm",
    "zentimeter": "cm", "zentimetern": "cm",
    "kilometer": "km", "kilometern": "km",
    "meter": "m", "metern": "m",
    "quadratmeter": "m2", "quadratmetern": "m2",
    "kilogramm": "kg", "kilogramms": "kg", "kilo": "kg",
    "milligramm": "mg", "milligramms": "mg",
    "mikrogramm": "ug", "mikrogramms": "ug",
    "gramm": "g",
    "milliliter": "ml", "millilitern": "ml",
    "liter": "l", "litern": "l",
    "deziliter": "dl",
    "minute": "min", "minuten": "min", "stunde": "h", "stunden": "h",
}


def _normalize_units(text: str) -> str:
    words = text.split(" ")
    out: list[str] = []
    i, n = 0, len(words)
    while i < n:
        matched = False
        for phrase, repl in _UNIT_MULTIWORD:
            m = len(phrase)
            if m > n - i:
                continue
            cores = [_split_punct(w)[0] for w in words[i:i + m]]
            if tuple(cores) == phrase:
                # Keep the attached punctuation: "pro dl," must stay a mark like "pro dl komma".
                _, lead, trail = _split_punct(words[i + m - 1])
                out.append(f"{lead}{repl}{trail}")
                i += m
                matched = True
                break
        if matched:
            continue
        core, lead, trail = _split_punct(words[i])
        if core in _UNIT_WORD:
            out.append(f"{lead}{_UNIT_WORD[core]}{trail}")
        else:
            out.append(words[i])
        i += 1
    return " ".join(out)


# Compounds
# A letter hyphen is glued by default. The MER path splits it instead
# (split_compounds). Letters required on both sides, so "10-15" stays.
_LETTER_HYPHEN_RE = re.compile(r"(?<=[^\W\d_])-(?=[^\W\d_])", re.UNICODE)

# "slash" and "Schrägstrich" mean "/".
_CONNECTOR_RE = re.compile(r"[\s-]*\b(?:slash|schr[äa]gstrich)\b[\s-]*", re.IGNORECASE)


def _joined_form(s: str) -> str:
    s = _CONNECTOR_RE.sub("", s)
    return re.sub(r"[\s\-/]+", "", s).lower()


def _normalize_compounds(
    text: str, terms: list[str] | None = None, split_compounds: bool = False
) -> str:
    """Collapse joined/hyphenated/split spellings of a listed term onto one
    form ("blutdruck messung" == "blutdruckmessung"). Gated on the term list so
    unrelated neighbours never merge. Terms with a plain space ("Diabetes
    mellitus") and windows containing a digit ("Typ 2") are left alone.

    `split_compounds` turns a letter hyphen into a token break: MER matches
    terms per word span, WER scores the text as a whole."""
    text = _CONNECTOR_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = _LETTER_HYPHEN_RE.sub(" " if split_compounds else "", text)
    if not terms:
        return text

    solid_terms = (t.strip() for t in terms if t and t.strip() and " " not in t.strip())
    joined_terms = {_joined_form(t) for t in solid_terms}
    joined_terms.discard("")
    if not joined_terms:
        return text

    words = text.split(" ")
    out: list[str] = []
    i, n = 0, len(words)
    max_span = 4
    while i < n:
        matched = False
        for span in range(min(max_span, n - i), 0, -1):
            window = words[i:i + span]
            if span >= 2 and any(any(ch.isdigit() for ch in w) for w in window):
                continue
            core, _, trail = _split_punct(window[-1])
            candidate = _joined_form(" ".join([*window[:-1], core]))
            if candidate and candidate in joined_terms:
                out.append(candidate + trail)
                i += span
                matched = True
                break
        if not matched:
            out.append(words[i])
            i += 1
    return " ".join(out)


# Spoken punctuation
# References spell punctuation as words ("Komma"), formatting systems emit
# glyphs. Both fold to the sentinel, and omitting a mark stays an error. Runs after
# the number pass, so a decimal "komma" is already "4,5".

# Not adjacent to a digit, so "4,5", "15." and "14:20" keep their marks.
_PUNCT_GLYPH_RE = re.compile(r'(?<!\d)[.,:;!?()"]+(?!\d)')

_PUNCT_WORDS = {
    "punkt", "komma", "doppelpunkt", "semikolon", "strichpunkt",
    "ausrufezeichen", "fragezeichen", "klammer",
    "anführungszeichen", "anfuehrungszeichen",
}
# No clean inline glyph counterpart -> drop instead of sentinel.
_DROP_PUNCT_WORDS = {"bindestrich", "gedankenstrich"}
_PUNCT_PHRASES: list[tuple[str, ...]] = [
    ("runde", "klammer", "auf"), ("runde", "klammer", "zu"),
    ("klammer", "auf"), ("klammer", "zu"),
    ("neue", "zeile"), ("neuer", "absatz"), ("neuer", "abschnitt"),
    ("neue", "seite"),
]


def _sentinel_punctuation(text: str) -> str:
    text = _PUNCT_GLYPH_RE.sub(f" {SENTINEL} ", text)
    words = text.split()
    out: list[str] = []
    i, n = 0, len(words)
    while i < n:
        matched = False
        for phrase in _PUNCT_PHRASES:
            m = len(phrase)
            if tuple(_split_punct(w)[0] for w in words[i:i + m]) == phrase:
                out.append(SENTINEL)
                i += m
                matched = True
                break
        if matched:
            continue
        core = _split_punct(words[i])[0]
        if core in _PUNCT_WORDS:
            out.append(SENTINEL)
        elif core in _DROP_PUNCT_WORDS:
            pass
        else:
            out.append(words[i])
        i += 1
    # Adjacent marks count once ("Punkt" + "neuer Absatz" is one break).
    collapsed: list[str] = []
    for w in out:
        if w == SENTINEL and collapsed and collapsed[-1] == SENTINEL:
            continue
        collapsed.append(w)
    return " ".join(collapsed)


# Latinate spelling variants
# German medical orthography admits both spellings (Procedere/Prozedere; RfdR
# Amtliches Regelwerk §32). Curated substrings with both sides attested, folded
# to the German-preferred form.

_ACCENT_MAP = str.maketrans({
    "é": "e", "è": "e", "ê": "e", "ë": "e", "á": "a", "à": "a", "â": "a",
    "í": "i", "ì": "i", "ó": "o", "ò": "o", "ô": "o", "ú": "u", "ù": "u",
    "ç": "c", "ñ": "n",
})
_LATINATE_VARIANTS: list[tuple[str, str]] = [
    # hard c -> k (Latinate before a/o/u/consonant)
    ("carcinom", "karzinom"), ("colitis", "kolitis"), ("calcium", "kalzium"),
    ("bicarbonat", "bikarbonat"), ("cardio", "kardio"), ("cranial", "kranial"),
    ("cranio", "kranio"), ("corticoid", "kortikoid"), ("carboplatin", "karboplatin"),
    ("conus", "konus"), ("talcum", "talkum"), ("discektomie", "diskektomie"),
    # soft c -> z (Latinate before e/i/y)
    ("procedere", "prozedere"), ("cervix", "zervix"), ("cervik", "zervik"),
    ("cerebr", "zerebr"), ("cystin", "zystin"), ("recessus", "rezessus"),
    ("glycerid", "glyzerid"), ("occipital", "okzipital"),
    # productive Greek/Latin suffixes, both Duden-valid
    ("graph", "graf"),
    ("photo", "foto"),
    ("ziell", "tiell"), ("zial", "tial"),
    # attested pairs from the Corti sets (model spelling -> Duden-preferred)
    ("gluconat", "glukonat"), ("ulcus", "ulkus"), ("curvilinear", "kurvilinear"),
    ("silv", "sylv"), ("fetid", "foetid"),
]


def _fold_latinate(text: str) -> str:
    text = text.translate(_ACCENT_MAP)
    for variant, canonical in _LATINATE_VARIANTS:
        text = text.replace(variant, canonical)
    return text


# Clinical abbreviations
# Mirrors the abbreviation rules of 44ai's correction step: "Z.n." and "Zustand
# nach" are one form. Folded to the spelled-out phrase because tokenization
# strips dots and would leave single-letter tokens.
_ABBREV_PAIRS: list[tuple[str, str]] = [
    (r"i\.v\.", "intravenös"),
    (r"s\.c\.", "subkutan"),
    (r"i\.m\.", "intramuskulär"),
    (r"bzw\.", "beziehungsweise"),
    (r"inkl\.", "inklusive"),
    (r"exkl\.", "exklusive"),
    (r"bzgl\.", "bezüglich"),
    (r"ggf\.", "gegebenenfalls"),
    (r"evtl\.", "eventuell"),
    (r"amb\.", "ambulant"),
    (r"stat\.", "stationär"),
    (r"z\.n\.", "zustand nach"),
    (r"v\.a\.", "verdacht auf"),
    (r"o\.b\.", "ohne befund"),
    (r"u\.a\.", "unter anderem"),
    (r"z\.b\.", "zum beispiel"),
    (r"k\.a\.", "keine angaben"),
    (r"d\.h\.", "das heißt"),
    (r"n\.b\.", "nicht bekannt"),
    (r"p\.o\.", "per os"),
    (r"etc\.", "et cetera"),
    (r"i\.d\.r\.", "in der regel"),
]
_ABBREV_RE = [
    (re.compile(r"(?<![\w.])" + pattern + r"(?![\w])"), expansion)
    for pattern, expansion in _ABBREV_PAIRS
]


def _fold_abbreviations(text: str) -> str:
    for pattern, expansion in _ABBREV_RE:
        text = pattern.sub(expansion, text)
    return text


# Umlaut / eszett folding
# Character-level, so ASCII transliterations and Swiss orthography (no ß) pass
# while "waren"/"wären" stay distinct.


def _fold_umlauts(text: str) -> str:
    return (
        text.replace("ä", "ae").replace("ö", "oe")
        .replace("ü", "ue").replace("ß", "ss")
    )


def normalize(text: str, terms: list[str] | None = None, *, split_compounds: bool = False) -> Normalized:
    """Run every stage in order and keep each intermediate result. Apply
    identically to reference, hypothesis and term list. Each stage favours
    precision: a wrong fold silently accepts a real recognition error.

    `split_compounds` is for the MER path only (see `_normalize_compounds`)."""
    # strip() first: a leading or trailing break is a chunk-boundary artifact, not a mark.
    cleaned = unicodedata.normalize("NFC", text).lower().strip()
    # Line breaks are layout marks, like spoken "neue Zeile".
    cleaned = re.sub(r"[\r\n]+", f" {SENTINEL} ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    symbols = _normalize_symbols(cleaned)
    numbers = normalize_numbers(symbols)
    dates = _normalize_dates_times(numbers)
    units = _normalize_units(dates)
    compounds = _normalize_compounds(units, terms, split_compounds)
    latinate = _fold_latinate(compounds)
    abbreviations = _fold_abbreviations(latinate)
    punctuation = _sentinel_punctuation(abbreviations)
    final = re.sub(r"\s+", " ", _fold_umlauts(punctuation)).strip()
    return Normalized(
        raw=text, cleaned=cleaned, symbols=symbols, numbers=numbers,
        dates=dates, units=units, compounds=compounds, latinate=latinate,
        abbreviations=abbreviations, punctuation=punctuation, final=final,
    )

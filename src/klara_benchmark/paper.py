# Every number in these tables is an accuracy (100 - error rate).

import math

from klara_benchmark.datasets import DIALECT_GROUPS

DATASETS = ("44ai-clinical-val", "medterm", "meddictate")
HEADERS = {"44ai-clinical-val": r"\valset{}", "medterm": "MedTerm", "meddictate": "MedDictate"}
# The two test sets that are not ours.
CORTI_SETS = ("medterm", "meddictate")

DIALECT_DS = "44ai-clinical-val"
# The set whose references exist in spoken and in formatted form.
FORMATTING_DS = "44ai-clinical-val"

# One configuration per system: where a system can deliver formatted text, that run stands for it
# in every table, and its plain run is listed in the appendix.
# (display name, product key, reported run, plain run of the same system if the reported one is not it)
PRODUCTS = [
    (r"\klara{} (ours)", "klara", "klara", None),
    (
        r"ElevenLabs Scribe\textsubscript{v2 Medical}", "elevenlabs-medical", "elevenlabs-medical-formatted",
        "elevenlabs-medical",
    ),
    (r"ElevenLabs Scribe\textsubscript{v2}", "elevenlabs", "elevenlabs-formatted", "elevenlabs"),
    ("MAI-Transcribe-2", "mai-transcribe", "mai-transcribe-formatted", "mai-transcribe"),
    ("gpt-4o-transcribe", "gpt-4o", "gpt-4o-formatted", "gpt-4o"),
    ("Soniox stt-async-v5", "soniox", "soniox", None),
    ("Deepgram Nova-3", "deepgram", "deepgram", None),
    ("Corti Symphony", "corti", "corti-formatted", "corti"),
    ("Whisper large-v3", "whisper", "whisper", None),
    ("Cohere Transcribe", "cohere", "cohere", None),
    ("Nemotron 3.5 Transcribe", "nemotron", "nemotron-formatted", "nemotron"),
    ("Dragon Medical One", "dmo", "dmo", None),
]
# What each run is asked for, in the vendor's own term where there is one.
SETUP = {
    "klara": "built in", "dmo": "built in",
    "corti-formatted": "formatting options", "corti": "as dictated",
    "mai-transcribe-formatted": "clean style", "mai-transcribe": "verbatim style",
    "elevenlabs-formatted": "shared instruction", "elevenlabs": "API default",
    "elevenlabs-medical-formatted": "shared instruction", "elevenlabs-medical": "API default",
    "gpt-4o-formatted": "shared instruction", "gpt-4o": "API default",
    "deepgram": "smart format", "soniox": "API default",
    "whisper": "model default", "cohere": "model default",
    "nemotron-formatted": "shared instruction", "nemotron": "model default",
}
# Where a setup is documented: (link, the setup labels it covers). The appendix table numbers them.
SETUP_NOTES = [
    (
        "https://github.com/44ai-labs/44ai-klara-evaluation/blob/main/src/klara_benchmark/systems/"
        "formatting.py#L3",
        {"shared instruction"},
    ),
    ("https://docs.corti.ai/stt/formatting", {"formatting options", "as dictated"}),
    (
        "https://learn.microsoft.com/azure/ai-services/speech-service/mai-transcribe",
        {"clean style", "verbatim style"},
    ),
    ("https://developers.deepgram.com/docs/smart-format", {"smart format"}),
]
# When each vendor API was called for its reported run. The vendor can change the model behind an
# API at any time, so the date belongs to the result. Systems we host ourselves are not listed.
API_CALLS = {
    "corti": "24 Sep 2026",
    "deepgram": "24 Sep 2026",
    "soniox": "24 Sep 2026",
    "elevenlabs-medical": "17 Nov 2026",
    "elevenlabs": "17 Nov 2026",
    "gpt-4o": "17 Nov 2026",
    "mai-transcribe": "17 Nov 2026",
}
# Runs that deliver formatted text. On MedTerm and MedDictate their WER is scored against the
# formatted reference, and the per-set table puts a dagger on the other runs, which are scored
# against the spoken-form reference there. Our own set has its term list in spoken form only, so
# every run is scored against its spoken-form reference.
FORMATTED_RUNS = {"klara", "dmo"} | {run for _, _, run, plain in PRODUCTS if plain}
# Keys into the paper's \logo{}/\logoimg{} icons and bar<key> colours.
LOGOS = {
    "klara": "44ai", "elevenlabs": "elevenlabs", "elevenlabs-medical": "elevenlabs",
    "mai-transcribe": "microsoft", "gpt-4o": "openai",
    "soniox": "soniox", "deepgram": "deepgram", "corti": "corti",
    "whisper": "openai", "cohere": "cohere", "dmo": "microsoft", "nemotron": "nvidia",
}
# Fig. 1: label text, the label's TikZ anchor on the icon ("north" puts the label below it, "west" to
# its right), and a shift right and up for the positions between two anchors.
SCATTER = {
    "klara": ("Klara", "south", "0pt", "0pt"), "corti": ("Corti", "west", "0pt", "0pt"),
    "elevenlabs": (r"Scribe\textsubscript{v2}", "east", "0pt", "0pt"),
    "elevenlabs-medical": (
        r"Scribe\textsubscript{v2}\\[-2.6pt]{\fontsize{4}{4}\selectfont medical}", "south", "-6pt", "2pt",
    ),
    "mai-transcribe": ("MAI-T2", "north", "0pt", "0pt"),
    "soniox": ("Soniox", "east", "0pt", "0pt"), "cohere": ("Cohere", "west", "0pt", "0pt"),
    "whisper": ("Whisper", "east", "0pt", "3pt"),
    "nemotron": ("Nemotron", "west", "0pt", "0pt"),
    "dmo": ("Dragon One (DMO)", "north", "9pt", "0pt"), "deepgram": ("Deepgram", "north west", "0pt", "0pt"),
}
# Labels moved out of a crowded spot, tied to their icon by a line with one loop. All positions are
# in pt from the icon's centre, right and up:
#   at:    where the label's left edge sits
#   curve: the line's Bezier points from the label to the icon, four for the first piece and three
#          more for each further piece
#   loop:  where along the curve the loop sits (0 to 1), its radius, and the share of the curve over
#          which it is eased in and out
LEADERS = {
    "gpt-4o": {
        "label": "gpt-4o",
        "at": (21.6, -13.6),
        "curve": (
            (20.3, -14.1), (15.5, -15.2), (12.5, -11.8), (10.5, -10.3),
            (8.7, -9.0), (3.0, -11.6), (1.95, -4.1),
        ),
        "loop": (0.5, 2.7, 0.12),
    },
}
# The chart above Table 1 shows one bar per vendor line-up: of two models of one vendor, the stronger.
BAR_SKIP = {"elevenlabs"}
# The bar labels are rotated, so a long name makes the whole float taller; the logo names the vendor.
BAR_NAMES = {"elevenlabs-medical": "Scribe v2 Medical", "nemotron": "Nemotron 3.5"}
HIGHLIGHT = r"\rowcolor{bar44ai!12}"
# Zero-width, so starred and plain cells align on the decimal point.
STAR = r"\rlap{$^{*}$}"
CHUNKED_NOTE = r"$^{*}$Run on the chunked MedTerm and MedDictate (Section~\ref{sec:validation-set})."
GENERATED = (
    "% Generated by `make score` (44ai-klara-evaluation, klara_benchmark/paper.py) - do not edit by hand."
)


def _label(name: str, system: str) -> str:
    return rf"\logo{{{LOGOS[system]}}}{name}"


def _cell(all_scores: dict, system: str, ds: str, metric: str) -> tuple[float | None, bool]:
    """(error rate, chunked_input)."""
    score = all_scores.get(ds, {}).get(system)
    if score is None:
        return None, False
    return (score["wer"]["final"] if metric == "wer" else score[metric]), score["chunked_input"]


def _acc(value: float) -> str:
    # One decimal: the second one is below what a re-run of the same system reproduces.
    return f"{value:.1f}"


def _acc_cell(value: float, chunked: bool, best: float) -> str:
    text = _acc(value)
    # Values that print the same are equally best.
    if text == _acc(best):
        text = rf"\best{{{text}}}"
    return text + (STAR if chunked else "")


def _weighted_rows(
    all_scores: dict, hours: dict[str, float], metric: str, plain: bool = False
) -> list[tuple]:
    """Products ranked by accuracy over the three sets combined (weighted by audio
    duration). Cell 0 is the combined value, then one cell per set. `plain` takes each
    product's plain run and leaves out the products that have only one configuration."""
    rows = []
    for name, key, run, plain_run in PRODUCTS:
        if plain and not plain_run:
            continue
        cells = [_cell(all_scores, plain_run if plain else run, ds, metric) for ds in DATASETS]
        if any(v is None for v, _ in cells):
            continue
        weights = [hours[ds] for ds in DATASETS]
        combined = 100 - sum(w * v for w, (v, _) in zip(weights, cells, strict=True)) / sum(weights)
        acc = [(combined, any(c for _, c in cells))] + [(100 - v, c) for v, c in cells]
        rows.append((name, key, acc))
    rows.sort(key=lambda r: -r[2][0][0])
    return rows


def _acc_rank_rows(rows: list[tuple]) -> list[str]:
    best = [max(acc[i][0] for _, _, acc in rows) for i in range(len(DATASETS) + 1)]
    body = []
    for rank, (name, key, acc) in enumerate(rows, 1):
        cells = " & ".join(_acc_cell(v, c, best[i]) for i, (v, c) in enumerate(acc))
        body.append(
            "    " + (HIGHLIGHT if key == "klara" else "")
            + f"{rank} & {_label(name, key)} & {cells}" + r" \\"
        )
    return body


def _acc_header() -> list[str]:
    return [
        r"    & & & \multicolumn{3}{c}{\textit{per test set}} \\", r"    \cmidrule(lr){4-6}",
        r"    \textbf{\#} & \textbf{System} & \textbf{Combined} & "
        + " & ".join(rf"\textbf{{{HEADERS[ds]}}}" for ds in DATASETS) + r" \\",
    ]


# Tail of the ranking-table caption.
WEIGHTING = (
    r"over all three test sets, weighted by audio duration. "
    + CHUNKED_NOTE
    + r" Best in \textbf{bold}."
)


def _bar_chart(rows: list[tuple]) -> list[str]:
    """Bar chart of combined formatted accuracy, styled after Artificial Analysis."""
    rows = [r for r in rows if r[1] not in BAR_SKIP]
    end = len(rows) + 0.5
    entries = [
        f"{acc[0][0]:.1f}/bar{LOGOS[s]}/{LOGOS[s]}/" + BAR_NAMES.get(s, name).replace(r"\klara{}", "Klara")
        for name, s, acc in rows
    ]
    return [
        # The bars and the axis title share the text width, however many systems are charted.
        rf"  \begin{{tikzpicture}}[x={0.98 / (len(rows) + 0.35):.4f}\textwidth, y=0.03cm]",
        r"    \node[rotate=90, inner sep=0pt, font=\sffamily\scriptsize, text=black!70] at (0.2,50)",
        r"      {Formatted Accuracy};",
        r"    \foreach \g in {25,50,75,100}",
        rf"      \draw[black!22, densely dotted, line width=0.4pt] (0.5,\g) -- ({end},\g);",
        rf"    \draw[black!30, line width=0.4pt] (0.5,0) -- ({end},0);",
        r"    \foreach [count=\i] \val/\col/\icon/\sys in {",
        *(f"        {e}," for e in entries[:-1]),
        f"        {entries[-1]}}} {{",
        r"      \fill[\col, rounded corners=3pt] (\i-0.34,0) |- (\i,\val) -| (\i+0.34,0);",
        r"      \node[inner sep=0pt, text=white, font=\sffamily\scriptsize] at (\i,\val/2) {\val};",
        r"      \node[inner sep=0pt] at (\i,-9) {\logoimg{\icon}};",
        (
            r"      \node[anchor=north east, rotate=40, inner sep=0pt, font=\sffamily\scriptsize]"
            r" at (\i+0.1,-19) {\sys};"
        ),
        r"    }",
        r"  \end{tikzpicture}\par",
        r"  \vspace{8pt}",
    ]


def _main_table(all_scores: dict, hours: dict[str, float]) -> str:
    """Bar chart of combined formatted accuracy with the per-set numbers below."""
    rows = _weighted_rows(all_scores, hours, "fwer")
    return "\n".join([
        GENERATED,
        r"\begin{table*}[t]", r"  \centering",
        *_bar_chart(rows),
        r"  \small",
        r"  \begin{tabular}{rlcccc}", r"    \toprule",
        *_acc_header(),
        r"    \midrule", *_acc_rank_rows(rows), r"    \bottomrule", r"  \end{tabular}",
        r"  \caption{Systems ranked by formatted accuracy ($100-\mathrm{fWER}$, \%) " + WEIGHTING + "}",
        r"  \label{tab:main-results}", r"\end{table*}",
    ]) + "\n"


def _per_set_table(all_scores: dict, hours: dict[str, float]) -> str:
    """Word accuracy and medical term accuracy, combined over the test sets and for each of them."""
    weights = [hours[ds] for ds in DATASETS]
    table = []
    for name, key, run, _ in PRODUCTS:
        acc = []
        for metric in ("wer", "mer"):
            cells = [_cell(all_scores, run, ds, metric) for ds in DATASETS]
            if any(v is None for v, _ in cells):
                break
            combined = 100 - sum(w * v for w, (v, _) in zip(weights, cells, strict=True)) / sum(weights)
            acc.append([(combined, any(c for _, c in cells))] + [(100 - v, c) for v, c in cells])
        else:
            # Interleave to (combined word, combined medical, set 1 word, set 1 medical, ...).
            label = _label(name, key) + ("" if run in FORMATTED_RUNS else r"$^{\dagger}$")
            table.append((key, label, [cell for pair in zip(*acc, strict=True) for cell in pair]))
    table.sort(key=lambda r: -r[2][0][0])
    best = [max(row[i][0] for _, _, row in table) for i in range(2 * (len(DATASETS) + 1))]
    body = [
        "    " + (HIGHLIGHT if key == "klara" else "") + f"{label} & "
        + " & ".join(_acc_cell(v, c, best[i]) for i, (v, c) in enumerate(row)) + r" \\"
        for key, label, row in table
    ]
    groups = [r"\textbf{Combined}"] + [
        rf"\textbf{{{HEADERS[ds]}}}" + (r"\textsubscript{by Corti}" if ds in CORTI_SETS else "")
        for ds in DATASETS
    ]
    return "\n".join([
        GENERATED,
        r"\begin{table*}[t]", r"  \centering", r"  \small", r"  \setlength{\tabcolsep}{4pt}",
        r"  \begin{tabular}{l" + "cc" * len(groups) + "}", r"    \toprule",
        "    & " + " & ".join(rf"\multicolumn{{2}}{{c}}{{{g}}}" for g in groups) + r" \\",
        "    " + "".join(rf"\cmidrule(lr){{{2 * i + 2}-{2 * i + 3}}}" for i in range(len(groups))),
        # Two-line column heads keep the pairs narrow.
        r"    \textbf{System} & "
        + " & ".join(r"\shortstack{Word\\Accuracy} & \shortstack{Medical\\Accuracy}" for _ in groups)
        + r" \\",
        r"    \midrule", *body, r"    \bottomrule", r"  \end{tabular}",
        (
            r"  \caption{Word accuracy ($100-\text{WER}$) and medical term accuracy ($100-\text{MER}$) "
            r"in \% after the shared normalization (Section~\ref{ssec:scoring}): combined over all three "
            r"test sets, weighted by audio duration, and per test set, on \valset{} and the German portions "
            r"of Corti's MedTerm and MedDictate. Sorted by combined word accuracy, best in \textbf{bold}. "
            + CHUNKED_NOTE
            + r" $^{\dagger}$On MedTerm and MedDictate scored against the spoken-form reference "
            r"(Section~\ref{ssec:scoring}).}"
        ),
        r"  \label{tab:wer-mer}", r"\end{table*}",
    ]) + "\n"


# The regional groups. High German and non-native speech are excluded.
DIALECT_ONLY_GROUPS = ["Swiss German dialects", "German regional dialects", "Austrian German"]
DIALECT_GROUP_SHORT = {
    "Swiss German dialects": "Swiss", "German regional dialects": "German regional",
    "Austrian German": "Austrian",
}


def _dialect_accuracy_table(all_scores: dict) -> str:
    """Accuracy per regional dialect group and over all of them pooled."""
    scores = all_scores[DIALECT_DS]
    by_group = [
        (DIALECT_GROUP_SHORT[g], [d for d, grp in DIALECT_GROUPS.items() if grp == g])
        for g in DIALECT_ONLY_GROUPS
    ]
    # (column label, dialect tokens pooled into it)
    groups = [
        *by_group,
        ("All dialects", [d for _, ds in by_group for d in ds]),
    ]
    rows = []
    for name, sys_, run, _ in PRODUCTS:
        by = scores.get(run, {}).get("by_dialect")
        if not by:
            continue
        acc = []
        for _, dialects in groups:
            # Pooled from raw counts, not averaged per-dialect rates.
            counts = [sum(by[d]["counts"][i] for d in dialects) for i in range(4)]
            acc += [100 - 100 * counts[0] / counts[1], 100 - 100 * counts[2] / counts[3]]
        rows.append((name, sys_, acc))
    rows.sort(key=lambda r: -r[2][-2])
    best = [max(v[i] for _, _, v in rows) for i in range(2 * len(groups))]
    body = []
    for name, sys_, acc in rows:
        cells = " & ".join(
            rf"\best{{{_acc(v)}}}" if _acc(v) == _acc(best[i]) else _acc(v) for i, v in enumerate(acc)
        )
        body.append(
            "    " + (HIGHLIGHT if sys_ == "klara" else "") + f"{_label(name, sys_)} & {cells}" + r" \\"
        )
    spans, rules, col = [], [], 2
    for short, _ in groups:
        spans.append(rf"\multicolumn{{2}}{{c}}{{\textbf{{{short}}}}}")
        rules.append(rf"\cmidrule(lr){{{col}-{col + 1}}}")
        col += 2
    return "\n".join([
        GENERATED,
        r"\begin{table*}[t]", r"  \centering", r"  \small", r"  \setlength{\tabcolsep}{4pt}",
        r"  \begin{tabular}{l" + "c" * 2 * len(groups) + "}", r"    \toprule",
        "    & " + " & ".join(spans) + r" \\",
        "    " + "".join(rules),
        r"    \textbf{System} & "
        + " & ".join(r"\shortstack{Word\\Accuracy} & \shortstack{Medical\\Accuracy}" for _ in groups)
        + r" \\",
        r"    \midrule", *body, r"    \bottomrule", r"  \end{tabular}",
        (
            r"  \caption{\textbf{Dialect-only comparison} Word accuracy ($100-\text{WER}$) and medical "
            r"term accuracy ($100-\text{MER}$) in \% on the Swiss German, German regional, and Austrian "
            r"speakers of \valset{}, pooled per group. Sorted by word accuracy over all dialects, best in "
            r"\textbf{bold}. Every system is scored against the spoken-form reference.}"
        ),
        r"  \label{tab:dialect-accuracy}", r"\end{table*}",
    ]) + "\n"


def _combined(all_scores: dict, hours: dict[str, float]) -> dict[str, tuple[float, float, bool]]:
    """{system: (combined formatted accuracy, combined medical term accuracy, chunked)}."""
    fwer = {sys_: acc[0] for _, sys_, acc in _weighted_rows(all_scores, hours, "fwer")}
    mer = {sys_: acc[0] for _, sys_, acc in _weighted_rows(all_scores, hours, "mer")}
    return {
        sys_: (fwer[sys_][0], mer[sys_][0], bool(fwer[sys_][1] or mer[sys_][1]))
        for _, sys_, _, _ in PRODUCTS
        if sys_ in fwer and sys_ in mer
    }


def _scatter_points(all_scores: dict, hours: dict[str, float]) -> str:
    """Fig. 1 data: combined formatted and medical term accuracy per product."""
    rows = ["system,formatted_accuracy,medical_accuracy,chunked"]
    rows += [f"{s},{f:.2f},{m:.2f},{int(c)}" for s, (f, m, c) in _combined(all_scores, hours).items()]
    return "\n".join(rows) + "\n"


def _leader(system: str, x: float, y: float) -> list[str]:
    """The icon at its point, the label set apart, and a line with one loop from the label to the icon."""
    spec = LEADERS[system]
    curve = spec["curve"]
    pieces = (len(curve) - 1) // 3
    centre, radius, stretch = spec["loop"]
    dx, dy = spec["at"]
    steps = 300
    points = []
    for k in range(steps + 1):
        t = k / steps
        piece = min(int(t * pieces), pieces - 1)
        p0, p1, p2, p3 = curve[3 * piece:3 * piece + 4]
        v = t * pieces - piece
        base = [
            (1 - v) ** 3 * p0[i] + 3 * v * (1 - v) ** 2 * p1[i] + 3 * v * v * (1 - v) * p2[i] + v**3 * p3[i]
            for i in (0, 1)
        ]
        heading = [
            3 * (1 - v) ** 2 * (p1[i] - p0[i]) + 6 * v * (1 - v) * (p2[i] - p1[i])
            + 3 * v * v * (p3[i] - p2[i])
            for i in (0, 1)
        ]
        speed = math.hypot(*heading)
        forward = (heading[0] / speed, heading[1] / speed)
        # The loop stands on the upper side of the line.
        side = (-forward[1], forward[0]) if forward[0] > 0 else (forward[1], -forward[0])
        # One full turn is added around `centre`. It is eased in and out, so the line has no kink.
        u = (t - (centre - stretch)) / (2 * stretch)
        turn = 2 * math.pi * u * u * u * (u * (6 * u - 15) + 10) if 0 < u < 1 else 0.0
        ahead, out = radius * math.sin(turn), radius * (1 - math.cos(turn))
        points.append(
            f"({base[0] + forward[0] * ahead + side[0] * out:.2f},"
            f"{base[1] + forward[1] * ahead + side[1] * out:.2f})"
        )
    rows = [" ".join(points[i:i + 7]) for i in range(0, len(points), 7)]
    return [
        rf"    \node[inner sep=0pt, font=\sffamily\scriptsize] at ({x:.2f},{y:.2f})",
        rf"      {{\logoimg{{{LOGOS[system]}}}}};",
        rf"    \begin{{scope}}[shift={{({x:.2f},{y:.2f})}}, x=1pt, y=1pt]",
        r"      \draw[black!55, line width=0.52pt, line cap=round, line join=round] plot coordinates {",
        *(f"        {row}" for row in rows),
        r"      };",
        rf"      \node[anchor=west, inner sep=0pt, font=\sffamily\scriptsize] at ({dx:.1f},{dy:.1f})",
        rf"        {{{spec['label']}}};",
        r"    \end{scope}",
    ]


def _scatter_figure(all_scores: dict, hours: dict[str, float]) -> str:
    """Fig. 1: formatted vs medical term accuracy, each product's icon at its point."""
    points = _combined(all_scores, hours)
    others = [
        f"{f:.2f}/{m:.2f}/{LOGOS[s]}/{SCATTER[s][1]}/{SCATTER[s][2]}/{SCATTER[s][3]}/{SCATTER[s][0]}"
        for s, (f, m, _) in points.items() if s in SCATTER and s != "klara"
    ]
    leaders = [line for s, (f, m, _) in points.items() if s in LEADERS for line in _leader(s, f, m)]
    kf, km, _ = points["klara"]
    return "\n".join([
        GENERATED,
        "% Figure 1: combined formatted accuracy vs combined medical term accuracy. Each system's icon",
        "% marks its point, with a short name next to it.",
        "% Numbers: figures/fig1_points.csv (the \"Combined\" columns of Tables 1 and 3).",
        r"\begin{tikzpicture}[x=0.0163\columnwidth, y=0.028\columnwidth]",
        r"  \begin{scope}[shift={(-40,-70)}]",
        r"    \foreach \x in {50,60,...,90}",
        r"      \draw[black!9, line width=0.3pt] (\x,70) -- (\x,95);",
        r"    \foreach \y in {75,80,...,95}",
        r"      \draw[black!9, line width=0.3pt] (40,\y) -- (95,\y);",
        r"    \draw[black!35, line width=0.4pt] (40,70) -- (95,70);",
        r"    \draw[black!35, line width=0.4pt] (40,70) -- (40,95);",
        r"    \foreach \x in {40,50,...,90}",
        r"      \draw[black!35, line width=0.4pt] (\x,70) -- (\x,69.5)",
        r"        node[below, inner sep=1.5pt, font=\sffamily\scriptsize, text=black!60] {\x\%};",
        r"    \foreach \y in {70,75,...,95}",
        r"      \draw[black!35, line width=0.4pt] (40,\y) -- (39.3,\y);",
        # The axis title takes the place of the middle tick labels, so it costs no width.
        r"    \foreach \y in {70,75,95}",
        r"      \node[left, inner sep=1.5pt, font=\sffamily\scriptsize, text=black!60] at (39.3,\y) {\y\%};",
        r"    \node[font=\sffamily\footnotesize, text=black!80, rotate=90] at (36.76,85)",
        r"      {Medical term accuracy};",
        r"    \node[font=\sffamily\footnotesize, text=black!80] at (67.5,66.0) {Formatted accuracy};",
        r"    \foreach \xx/\yy/\icon/\side/\dx/\dy/\sys in {",
        *(f"        {o}," for o in others[:-1]),
        f"        {others[-1]}}} {{",
        r"      \node[inner sep=0pt, font=\sffamily\scriptsize] at (\xx,\yy) {\logoimg{\icon}};",
        r"      \node[anchor=\side, xshift=\dx, yshift=\dy, inner sep=5pt, align=center,",
        r"        font=\sffamily\scriptsize] at (\xx,\yy) {\sys};",
        r"    }",
        *leaders,
        rf"    \node[inner sep=0pt, font=\sffamily\normalsize] at ({kf:.2f},{km:.2f}) {{\logoimg{{44ai}}}};",
        (
            rf"    \node[anchor={SCATTER['klara'][1]}, inner sep=7pt, font=\sffamily\scriptsize\bfseries]"
            rf" at ({kf:.2f},{km:.2f}) {{{SCATTER['klara'][0]}}};"
        ),
        r"  \end{scope}",
        r"\end{tikzpicture}",
    ]) + "\n"


def _api_dates_table() -> str:
    names = {key: name for name, key, _, _ in PRODUCTS}
    # Not a float: the paper sets it at the top of the last page's right column, above the full-width
    # table, and LaTeX would not place a table float ahead of an earlier one.
    return "\n".join([
        GENERATED,
        r"\noindent\begin{minipage}{\columnwidth}",
        r"  \centering",
        r"  \small",
        r"  \begin{tabular}{ll}",
        r"    \toprule",
        r"    \textbf{System} & \textbf{Evaluated} \\",
        r"    \midrule",
        *(rf"    {_label(names[key], key)} & {date} \\" for key, date in API_CALLS.items()),
        r"    \bottomrule",
        r"  \end{tabular}",
        r"  \captionof{table}{\textbf{API evaluation dates} Vendor API calls come with no control over "
        r"the deployed model or its configuration. The dates show when we last evaluated each system.}",
        r"  \label{tab:api-dates}",
        r"\end{minipage}",
    ]) + "\n"


def _escaped(link: str) -> str:
    """A link for use inside a table cell, where a bare # is a parameter character."""
    return link.replace("#", r"\#")


def _configurations_table(all_scores: dict, hours: dict[str, float]) -> str:
    """Appendix: every run of every system. Accuracy over all test sets, and how the run treats the
    formatting a clinician dictates."""
    metrics = ("fwer", "wer", "mer")
    weights = [hours[ds] for ds in DATASETS]
    behaviour = all_scores[FORMATTING_DS]

    def combined(run: str, metric: str) -> tuple[float, bool] | None:
        cells = [_cell(all_scores, run, ds, metric) for ds in DATASETS]
        if any(v is None for v, _ in cells):
            return None
        value = 100 - sum(w * v for w, (v, _) in zip(weights, cells, strict=True)) / sum(weights)
        return value, any(c for _, c in cells)

    # A product's plain run is its own row, named like the reported one.
    runs = [
        (_label(name, key), key, run)
        for name, key, reported, plain_run in PRODUCTS
        for run in (reported, plain_run)
        if run and combined(run, "fwer") and "formatting" in behaviour.get(run, {})
    ]
    runs.sort(key=lambda r: -combined(r[2], "fwer")[0])

    def bold_best(values: list[tuple[float, bool]], fmt: str) -> list[str]:
        best = max(v for v, _ in values)
        return [
            (rf"\best{{{v:{fmt}}}}" if f"{v:{fmt}}" == f"{best:{fmt}}" else f"{v:{fmt}}")
            + (STAR if chunked else "")
            for v, chunked in values
        ]

    columns = [bold_best([combined(run, m) for _, _, run in runs], ".1f") for m in metrics] + [
        bold_best([(behaviour[run]["formatting"][what], False) for _, _, run in runs], ".0f")
        for what in ("commands", "numbers")
    ]

    def setup(run: str) -> str:
        label = SETUP[run]
        for number, (link, labels) in enumerate(SETUP_NOTES, 1):
            if label in labels:
                # hyperref wants the fragment sign escaped inside another macro's argument.
                target = link.replace("#", r"\#")
                return label + rf"\textsuperscript{{\href{{{target}}}{{[{number}]}}}}"
        return label

    body = [
        "    " + (HIGHLIGHT if key == "klara" else "")
        + f"{name} & {setup(run)} & " + " & ".join(cells) + r" \\"
        for (name, key, run), cells in zip(runs, zip(*columns, strict=True), strict=True)
    ]
    notes = [
        # Shown without the scheme, or the longest link runs into the margin.
        rf"    \textsuperscript{{[{number}]}}\,\href{{{_escaped(link)}}}"
        rf"{{\nolinkurl{{{_escaped(link.removeprefix('https://'))}}}}} \\"
        for number, (link, _) in enumerate(SETUP_NOTES, 1)
    ]
    heads = ["Formatted\\\\Accuracy", "Word\\\\Accuracy", "Medical\\\\Accuracy", "Formatted\\\\Commands",
             "Formatted\\\\Numbers"]
    return "\n".join([
        GENERATED,
        # [b]: with the stfloats package the full-width table sits at the foot of the page it is called on.
        r"\begin{table*}[b]", r"  \centering", r"  \small",
        # A little tighter than the default, or the table is wider than the text block.
        r"  \setlength{\tabcolsep}{5.2pt}",
        r"  \begin{tabular}{ll" + "c" * len(heads) + "}", r"    \toprule",
        r"    \textbf{System} & \textbf{Formatting} & "
        + " & ".join(rf"\textbf{{\shortstack{{{h}}}}}" for h in heads) + r" \\",
        r"    \midrule", *body, r"    \bottomrule", r"  \end{tabular}",
        r"  \par\smallskip", r"  {\footnotesize\begin{tabular}{@{}l@{}}", *notes, r"  \end{tabular}}",
        (
            r"  \caption{\textbf{All configurations} Formatted, word, and medical term accuracy in \% over "
            r"all three test sets, weighted by audio duration, sorted by formatted accuracy. \emph{Formatted "
            r"commands}: share of the \valset{} clips with a dictated command (\emph{Punkt}, \emph{Komma}, "
            r"\emph{Neue Zeile}, \dots) in which no command is left as a word. \emph{Formatted numbers}: "
            r"share of the clips with numbers in which none is written out. " + CHUNKED_NOTE + "}"
        ),
        r"  \label{tab:configurations}", r"\end{table*}",
    ]) + "\n"


def paper_files(all_scores: dict, hours: dict[str, float]) -> dict[str, str]:
    """{file name: content}."""
    return {
        "tab_main.tex": _main_table(all_scores, hours),
        "tab_dialect_accuracy.tex": _dialect_accuracy_table(all_scores),
        "tab_unformatted.tex": _per_set_table(all_scores, hours),
        "tab_api_dates.tex": _api_dates_table(),
        "tab_configurations.tex": _configurations_table(all_scores, hours),
        "fig1_points.csv": _scatter_points(all_scores, hours),
        "fig1_scatter.tex": _scatter_figure(all_scores, hours),
    }

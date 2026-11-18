import functools

from klara_benchmark.systems.corti import _transcribe

# Spoken + automatic punctuation on, compared on fWER against the formatted
# reference. dates=locale:short because the default locale:long spells the
# month out ("12. Mai 2024"), which fWER would charge in full.
transcribe = functools.partial(
    _transcribe,
    spoken_punctuation=True,
    automatic_punctuation=True,
    formatting={"dates": "locale:short"},
)

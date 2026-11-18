import functools

from klara_benchmark.systems.elevenlabs import _transcribe_formatted

transcribe = functools.partial(_transcribe_formatted, model_id="scribe_v2")

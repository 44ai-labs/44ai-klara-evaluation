import functools

from klara_benchmark.systems.elevenlabs import _transcribe

# ElevenLabs' clinical fine-tune of Scribe v2: same endpoint and request, other model id.
transcribe = functools.partial(_transcribe, model_id="scribe_v2_medical")

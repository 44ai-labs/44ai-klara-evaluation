import functools

from klara_benchmark.systems.mai_transcribe import _transcribe

transcribe = functools.partial(_transcribe, style="clean")

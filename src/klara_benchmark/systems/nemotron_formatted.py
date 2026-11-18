import functools

from klara_benchmark.systems.formatting import FORMATTING_INSTRUCTION
from klara_benchmark.systems.nemotron import _transcribe

# The shared instruction takes the place of the model card's prompt.
transcribe = functools.partial(_transcribe, prompt=FORMATTING_INSTRUCTION)

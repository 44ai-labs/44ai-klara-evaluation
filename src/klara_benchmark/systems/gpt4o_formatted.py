import functools

from klara_benchmark.systems.formatting import FORMATTING_INSTRUCTION
from klara_benchmark.systems.gpt4o import _transcribe

# The shared instruction goes in as the model's prompt.
transcribe = functools.partial(_transcribe, prompt=FORMATTING_INSTRUCTION)

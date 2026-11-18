import base64
import functools
import io
import re
from pathlib import Path

from openai import OpenAI

from klara_benchmark.systems import require_env
from klara_benchmark.systems.common import audio_array, parallel_map

MODEL = "nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B"
WORKERS = 64
# A one-hour recording may take minutes when the server is busy.
TIMEOUT_S = 7200
# The model card's transcription prompt.
DEFAULT_PROMPT = (
    "Audio transcription. Language: as spoken. Wording: verbatim, including fillers and repetitions. "
    "Formatting: punctuation and capitalization. Output: transcript only."
)
# The model card's guard against generation loops: a character or a block repeated twenty times
# over is kept once.
_CHAR_RUN = re.compile(r"(.)\1{20,}", re.DOTALL)
_BLOCK_RUN = re.compile(r"(.{1,4096}?)\1{19,}", re.DOTALL)


def _collapse_loops(text: str) -> str:
    return _BLOCK_RUN.sub(lambda m: m.group(1), _CHAR_RUN.sub(lambda m: m.group(1), text))


def _wav_data_url(cell) -> str:
    import soundfile as sf

    audio = audio_array(cell)
    buffer = io.BytesIO()
    sf.write(buffer, audio["array"], audio["sampling_rate"], format="WAV", subtype="FLOAT")
    return "data:audio/wav;base64," + base64.b64encode(buffer.getvalue()).decode()


def _transcribe(rows: list[dict], desc: str, *, prompt: str, checkpoint: Path | None = None) -> list[str]:
    # The model is served with vLLM as its model card describes. NEMOTRON_API_URL is that server's
    # OpenAI-compatible endpoint, for example http://127.0.0.1:8000/v1.
    client = OpenAI(base_url=require_env("NEMOTRON_API_URL"), api_key="EMPTY", timeout=TIMEOUT_S)

    def one(row: dict) -> str:
        # The model card's transcription settings: no system message, the instruction before the
        # audio, greedy decoding, reasoning off.
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "audio_url", "audio_url": {"url": _wav_data_url(row["audio"])}},
                ],
            }],
            temperature=0,
            top_p=1.0,
            max_tokens=16384,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False},
                "skip_special_tokens": False,
                "spaces_between_special_tokens": False,
                "seed": 0,
            },
        )
        return _collapse_loops(response.choices[0].message.content or "").strip()

    return parallel_map(one, rows, WORKERS, desc, checkpoint=checkpoint)


transcribe = functools.partial(_transcribe, prompt=DEFAULT_PROMPT)

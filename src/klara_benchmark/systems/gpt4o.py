import functools
import time
from pathlib import Path

from openai import APIStatusError, OpenAI

from klara_benchmark.systems import require_env
from klara_benchmark.systems.common import audio_bytes, parallel_map

MODEL = "gpt-4o-transcribe"
WORKERS = 6
MAX_RETRIES = 5


def _transcribe(
    rows: list[dict], desc: str, *, prompt: str | None, checkpoint: Path | None = None
) -> list[str]:
    # max_retries=0: the SDK's internal retry would stack on top of ours.
    client = OpenAI(api_key=require_env("OPENAI_API_KEY"), max_retries=0)
    extra = {"prompt": prompt} if prompt else {}

    def one(row: dict) -> str:
        data, name = audio_bytes(row["audio"])
        for attempt in range(MAX_RETRIES):
            try:
                return client.audio.transcriptions.create(
                    model=MODEL, file=(name, data), language="de", temperature=0.0, **extra
                ).text
            except APIStatusError as e:
                if e.status_code != 429 or attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(2**attempt)

    return parallel_map(one, rows, WORKERS, desc, checkpoint=checkpoint)


transcribe = functools.partial(_transcribe, prompt=None)

import time
from pathlib import Path

from soniox import SonioxClient
from soniox.errors import SonioxRateLimitError
from soniox.types import CreateTranscriptionConfig

from klara_benchmark.systems import require_env
from klara_benchmark.systems.common import audio_bytes, parallel_map

MODEL = "stt-async-v5"
# Batch jobs (upload + poll), safe to run many at once.
WORKERS = 8
MAX_RETRIES = 5
WAIT_TIMEOUT_S = 600.0


def transcribe(rows: list[dict], desc: str, *, checkpoint: Path | None = None) -> list[str]:
    client = SonioxClient(api_key=require_env("SONIOX_API_KEY"))

    def one(row: dict) -> str:
        data, name = audio_bytes(row["audio"])
        for attempt in range(MAX_RETRIES):
            try:
                transcript = client.stt.transcribe_and_wait_with_tokens(
                    model=MODEL,
                    file=data,
                    filename=name,
                    config=CreateTranscriptionConfig(language_hints=["de"]),
                    delete_after=True,
                    wait_timeout_sec=WAIT_TIMEOUT_S,
                )
                return transcript.text
            except SonioxRateLimitError:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(2**attempt)

    try:
        return parallel_map(one, rows, WORKERS, desc, checkpoint=checkpoint)
    finally:
        client.close()

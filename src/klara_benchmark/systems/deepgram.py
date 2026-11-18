import time
from pathlib import Path

import httpx

from klara_benchmark.systems import require_env
from klara_benchmark.systems.common import audio_bytes, parallel_map

MODEL = "nova-3"
WORKERS = 6
MAX_RETRIES = 5
REQUEST_TIMEOUT_S = 120.0


def transcribe(rows: list[dict], desc: str, *, checkpoint: Path | None = None) -> list[str]:
    headers = {"Authorization": f"Token {require_env('DEEPGRAM_API_KEY')}"}
    params = {"model": MODEL, "language": "de", "smart_format": "true"}

    with httpx.Client(
        base_url="https://api.deepgram.com/v1", headers=headers, timeout=REQUEST_TIMEOUT_S
    ) as client:

        def one(row: dict) -> str:
            data, name = audio_bytes(row["audio"])
            content_type = "audio/flac" if name.endswith(".flac") else "audio/wav"
            resp = None
            for attempt in range(MAX_RETRIES):
                try:
                    resp = client.post(
                        "/listen",
                        params=params,
                        content=data,
                        headers={"Content-Type": content_type},
                    )
                    resp.raise_for_status()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code != 429 or attempt == MAX_RETRIES - 1:
                        raise
                    time.sleep(2**attempt)
            payload = resp.json()
            alt = payload["results"]["channels"][0]["alternatives"][0]
            return alt.get("transcript", "").strip()

        return parallel_map(one, rows, WORKERS, desc, checkpoint=checkpoint)

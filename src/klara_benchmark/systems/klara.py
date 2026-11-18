import base64
from pathlib import Path

import httpx

from klara_benchmark.systems import require_env
from klara_benchmark.systems.common import audio_bytes, parallel_map

WORKERS = 8
TIMEOUT_S = 300.0


def transcribe(rows: list[dict], desc: str, *, checkpoint: Path | None = None) -> list[str]:
    base_url = require_env("KLARA_API_URL")
    headers = {"Authorization": f"Bearer {require_env('KLARA_API_KEY')}"}
    with httpx.Client(base_url=base_url, headers=headers, timeout=TIMEOUT_S) as client:

        def one(row: dict) -> str:
            data, _ = audio_bytes(row["audio"])
            resp = client.post(
                "/asr_base64",
                json={
                    "audio_base64": base64.b64encode(data).decode(),
                    "language": "de",
                    "quality": True,
                    "diarization": False,
                    "correct": True,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            return body.get("corrected_transcript") or body.get("transcript", "")

        return parallel_map(one, rows, WORKERS, desc, checkpoint=checkpoint)

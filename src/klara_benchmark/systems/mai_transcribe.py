import functools
import json
import random
import time
from pathlib import Path

import httpx

from klara_benchmark.systems import require_env
from klara_benchmark.systems.common import audio_bytes, parallel_map

MODEL = "MAI-Transcribe-2"
API_VERSION = "2025-10-15"
# The model runs ~10x faster than real time, so a few in-flight files keep it busy.
WORKERS = 8
# Azure throttles per resource on a rolling window and sends Retry-After. An F0
# resource can keep a row waiting for minutes, so retry long but bounded.
MAX_ATTEMPTS = 12
MAX_BACKOFF_S = 60.0
REQUEST_TIMEOUT_S = 600.0

_CONTENT_TYPES = {"wav": "audio/wav", "mp3": "audio/mpeg", "flac": "audio/flac"}


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    """Retry-After when sent, else jittered exponential back-off."""
    retry_after = response.headers.get("Retry-After", "").strip()
    if retry_after.isdigit():
        return float(retry_after) + random.uniform(0, 1)
    return min(MAX_BACKOFF_S, 2.0**attempt) + random.uniform(0, 1)


def _content_type(name: str) -> str:
    return _CONTENT_TYPES.get(name.rsplit(".", 1)[-1].lower(), "application/octet-stream")


def _transcribe(
    rows: list[dict], desc: str, *, style: str, checkpoint: Path | None = None
) -> list[str]:
    base_url = require_env("MAI_TRANSCRIBE_ENDPOINT").rstrip("/") + "/"
    headers = {"Ocp-Apim-Subscription-Key": require_env("MAI_TRANSCRIBE_API_KEY")}
    # https://learn.microsoft.com/azure/ai-services/speech-service/mai-transcribe
    # transcribeStyle: "verbatim" is as spoken, "clean" removes fillers and formats common patterns.
    definition = json.dumps(
        {
            "locales": ["de"],
            "enhancedMode": {
                "enabled": True,
                "model": MODEL,
                "modelOptions": {"transcribeStyle": style},
            },
        }
    )

    with httpx.Client(base_url=base_url, headers=headers, timeout=REQUEST_TIMEOUT_S) as client:

        def one(row: dict) -> str:
            data, name = audio_bytes(row["audio"])
            resp = None
            for attempt in range(MAX_ATTEMPTS):
                try:
                    resp = client.post(
                        "speechtotext/transcriptions:transcribe",
                        params={"api-version": API_VERSION},
                        files={"audio": (name, data, _content_type(name))},
                        data={"definition": definition},
                    )
                    resp.raise_for_status()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code != 429 or attempt == MAX_ATTEMPTS - 1:
                        raise
                    time.sleep(_retry_delay(e.response, attempt))
            # combinedPhrases is the full transcript per channel (mono here).
            return "\n".join(p["text"] for p in resp.json()["combinedPhrases"]).strip()

        return parallel_map(one, rows, WORKERS, desc, checkpoint=checkpoint)


transcribe = functools.partial(_transcribe, style="verbatim")

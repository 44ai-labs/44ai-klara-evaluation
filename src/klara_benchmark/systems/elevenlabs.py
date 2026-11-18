import functools
import time
from pathlib import Path

import httpx
from elevenlabs.client import ElevenLabs
from elevenlabs.core import ApiError

from klara_benchmark.systems import require_env
from klara_benchmark.systems.common import audio_bytes, parallel_map
from klara_benchmark.systems.formatting import FORMATTING_INSTRUCTION

# ElevenLabs caps concurrent STT requests (8 on the free tier).
WORKERS = 6
MAX_RETRIES = 5
REQUEST_TIMEOUT_S = 600.0


def _transcribe(
    rows: list[dict], desc: str, *, model_id: str, checkpoint: Path | None = None
) -> list[str]:
    client = ElevenLabs(api_key=require_env("ELEVENLABS_API_KEY"))

    def one(row: dict) -> str:
        data, name = audio_bytes(row["audio"])
        for attempt in range(MAX_RETRIES):
            try:
                # Seed pinned for reproducibility.
                return client.speech_to_text.convert(
                    file=(name, data),
                    model_id=model_id,
                    language_code="de",
                    tag_audio_events=False,
                    seed=42,
                ).text
            except ApiError as e:
                if e.status_code != 429 or attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(2**attempt)

    return parallel_map(one, rows, WORKERS, desc, checkpoint=checkpoint)


def _transcribe_formatted(
    rows: list[dict], desc: str, *, model_id: str, checkpoint: Path | None = None
) -> list[str]:
    """The same request plus `transcript_edit`: ElevenLabs rewrites the finished transcript by the
    instruction. Sent over plain HTTP because the pinned SDK predates the parameter."""
    headers = {"xi-api-key": require_env("ELEVENLABS_API_KEY")}
    form = {
        "model_id": model_id,
        "language_code": "de",
        "tag_audio_events": "false",
        "seed": "42",
        "transcript_edit": FORMATTING_INSTRUCTION,
    }

    with httpx.Client(
        base_url="https://api.elevenlabs.io/v1", headers=headers, timeout=REQUEST_TIMEOUT_S
    ) as client:

        def one(row: dict) -> str:
            data, name = audio_bytes(row["audio"])
            resp = None
            for attempt in range(MAX_RETRIES):
                try:
                    resp = client.post("/speech-to-text", data=form, files={"file": (name, data)})
                    resp.raise_for_status()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code != 429 or attempt == MAX_RETRIES - 1:
                        raise
                    time.sleep(2**attempt)
            body = resp.json()
            edited = body.get("edited_transcript") or {}
            # A failed edit comes back as kind "error" next to the untouched transcript.
            return edited["text"] if edited.get("kind") == "transcript" else body["text"]

        return parallel_map(one, rows, WORKERS, desc, checkpoint=checkpoint)


transcribe = functools.partial(_transcribe, model_id="scribe_v2")

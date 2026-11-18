import functools
import os
import threading
import time
import uuid
from pathlib import Path

import httpx

from klara_benchmark.systems import require_env
from klara_benchmark.systems.common import audio_bytes, parallel_map

WORKERS = 4
REQUEST_TIMEOUT_S = 60.0
UPLOAD_TIMEOUT_S = 120.0
TRANSCRIBE_TIMEOUT_S = 30.0
POLL_INTERVAL_S = 2.0
POLL_TIMEOUT_S = 90.0
TOKEN_MARGIN_S = 30.0

FORMATTING_AS_DICTATED = {
    "dates": "as_dictated",
    "measurements": "as_dictated",
    "numbers": "as_dictated",
    "numericRanges": "as_dictated",
    "ordinals": "as_dictated",
    "times": "as_dictated",
}


class TokenManager:
    """Thread-safe OAuth2 client-credentials token, refreshed before expiry."""

    def __init__(self, scope: str) -> None:
        self.environment = os.environ.get("CORTI_ENVIRONMENT") or "eu"
        self.tenant = require_env("CORTI_TENANT_NAME")
        realm = os.environ.get("CORTI_AUTH_TENANT_NAME") or self.tenant
        self._auth_url = (
            f"https://auth.{self.environment}.corti.app/realms/{realm}"
            "/protocol/openid-connect/token"
        )
        self._client_id = require_env("CORTI_CLIENT_ID")
        self._client_secret = require_env("CORTI_CLIENT_SECRET")
        self._scope = scope
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at = 0.0

    def get(self) -> str:
        with self._lock:
            if self._token is None or time.time() > self._expires_at:
                self._refresh()
            return self._token

    def _refresh(self) -> None:
        resp = httpx.post(
            self._auth_url,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "client_credentials",
                "scope": self._scope,
            },
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        self._expires_at = time.time() + payload.get("expires_in", 300) - TOKEN_MARGIN_S


def _transcribe(
    rows: list[dict],
    desc: str,
    *,
    spoken_punctuation: bool,
    automatic_punctuation: bool,
    formatting: dict[str, str] | None = None,
    checkpoint: Path | None = None,
) -> list[str]:
    tm = TokenManager(scope="openid")

    def headers() -> dict:
        return {"Authorization": f"Bearer {tm.get()}", "Tenant-Name": tm.tenant}

    with httpx.Client(base_url=f"https://api.{tm.environment}.corti.app/v2") as client:

        def one(row: dict) -> str:
            data, _ = audio_bytes(row["audio"])
            resp = client.post(
                "/interactions/",
                json={"encounter": {
                    "identifier": f"sample_{row['id']}_{uuid.uuid4().hex[:8]}",
                    "status": "completed",
                    "type": "consultation",
                }},
                headers=headers(),
                timeout=REQUEST_TIMEOUT_S,
            )
            resp.raise_for_status()
            interaction = resp.json()["interactionId"]

            upload_headers = headers() | {"Content-Type": "application/octet-stream"}
            resp = client.post(
                f"/interactions/{interaction}/recordings/",
                content=data,
                headers=upload_headers,
                timeout=UPLOAD_TIMEOUT_S,
            )
            resp.raise_for_status()
            recording = resp.json()["recordingId"]

            resp = client.post(
                f"/interactions/{interaction}/transcripts/",
                json={
                    "recordingId": recording,
                    "primaryLanguage": "de",
                    "spokenPunctuation": spoken_punctuation,
                    "automaticPunctuation": automatic_punctuation,
                    **({"formatting": formatting} if formatting else {}),
                },
                headers=headers(),
                timeout=TRANSCRIBE_TIMEOUT_S,
            )
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("status") not in ("completed", "failed"):
                payload = _poll(client, interaction, payload["transcriptId"])
            segments = sorted(payload.get("transcripts", []), key=lambda s: s.get("start", 0))
            return " ".join(s["text"] for s in segments if s.get("text")).strip()

        def _poll(client: httpx.Client, interaction: str, transcript_id: str) -> dict:
            deadline = time.time() + POLL_TIMEOUT_S
            while time.time() < deadline:
                resp = client.get(
                    f"/interactions/{interaction}/transcripts/{transcript_id}",
                    headers=headers(),
                    timeout=REQUEST_TIMEOUT_S,
                )
                resp.raise_for_status()
                payload = resp.json()
                if payload.get("status") in ("completed", "failed"):
                    return payload
                time.sleep(POLL_INTERVAL_S)
            raise TimeoutError(f"transcript {transcript_id} did not complete in {POLL_TIMEOUT_S}s")

        return parallel_map(one, rows, WORKERS, desc, checkpoint=checkpoint)


# Literal transcript, compared on WER against the verbatim reference.
transcribe = functools.partial(
    _transcribe,
    spoken_punctuation=False,
    automatic_punctuation=False,
    formatting=FORMATTING_AS_DICTATED,
)

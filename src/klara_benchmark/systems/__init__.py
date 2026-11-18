import os
from typing import Literal

from pydantic import BaseModel, ConfigDict


class System(BaseModel):
    model_config = ConfigDict(frozen=True)

    module: str
    required_env: tuple[str, ...] = ()
    local: bool = False
    corti_input: Literal["full", "chunked"] = "full"


CORTI_ENV = ("CORTI_CLIENT_ID", "CORTI_CLIENT_SECRET", "CORTI_TENANT_NAME")

SYSTEMS = {
    "klara": System(module="klara", required_env=("KLARA_API_URL", "KLARA_API_KEY")),
    "elevenlabs": System(module="elevenlabs", required_env=("ELEVENLABS_API_KEY",)),
    "elevenlabs-formatted": System(module="elevenlabs_formatted", required_env=("ELEVENLABS_API_KEY",)),
    "elevenlabs-medical": System(module="elevenlabs_medical", required_env=("ELEVENLABS_API_KEY",)),
    "elevenlabs-medical-formatted": System(
        module="elevenlabs_medical_formatted", required_env=("ELEVENLABS_API_KEY",)
    ),
    "gpt-4o": System(module="gpt4o", required_env=("OPENAI_API_KEY",)),
    "gpt-4o-formatted": System(module="gpt4o_formatted", required_env=("OPENAI_API_KEY",)),
    "deepgram": System(module="deepgram", required_env=("DEEPGRAM_API_KEY",)),
    "soniox": System(module="soniox", required_env=("SONIOX_API_KEY",)),
    "mai-transcribe": System(
        module="mai_transcribe", required_env=("MAI_TRANSCRIBE_ENDPOINT", "MAI_TRANSCRIBE_API_KEY")
    ),
    "mai-transcribe-formatted": System(
        module="mai_transcribe_formatted",
        required_env=("MAI_TRANSCRIBE_ENDPOINT", "MAI_TRANSCRIBE_API_KEY"),
    ),
    "corti": System(module="corti", required_env=CORTI_ENV),
    "corti-formatted": System(module="corti_formatted", required_env=CORTI_ENV),
    "whisper": System(module="whisper", local=True, corti_input="chunked"),
    "cohere": System(module="cohere", local=True, corti_input="chunked"),
    "nemotron": System(module="nemotron", required_env=("NEMOTRON_API_URL",), local=True),
    "nemotron-formatted": System(
        module="nemotron_formatted", required_env=("NEMOTRON_API_URL",), local=True
    ),
}


def require_env(key: str) -> str:
    value = os.environ.get(key, "")
    if not value:
        raise SystemExit(f"{key} is not set. Add it to .env (see .env.example).")
    return value

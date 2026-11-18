from pathlib import Path

from klara_benchmark.systems.common import audio_array, sequential_map

MODEL_ID = "openai/whisper-large-v3"


def transcribe(rows: list[dict], desc: str, *, checkpoint: Path | None = None) -> list[str]:
    import torch
    from transformers import pipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    asr = pipeline(
        "automatic-speech-recognition",
        model=MODEL_ID,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device=device,
        chunk_length_s=30,
    )
    generate_kwargs = {"language": "german", "task": "transcribe"}

    def one(row: dict) -> str:
        return asr(audio_array(row["audio"]), generate_kwargs=generate_kwargs)["text"].strip()

    return sequential_map(one, rows, desc, checkpoint=checkpoint)

from pathlib import Path

from klara_benchmark.systems.common import audio_array, sequential_map

MODEL_ID = "CohereLabs/cohere-transcribe-03-2026"
MAX_NEW_TOKENS = 448


def transcribe(rows: list[dict], desc: str, *, checkpoint: Path | None = None) -> list[str]:
    import torch
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(MODEL_ID, torch_dtype=dtype)
    model = model.to(device).eval()
    prompt_len = len(processor.get_decoder_prompt_ids(language="de", punctuation=True))

    def one(row: dict) -> str:
        audio = audio_array(row["audio"])
        inputs = processor(
            audio["array"], language="de", sampling_rate=16000, return_tensors="pt"
        )
        inputs = {
            k: v.to(device, dtype) if v.dtype.is_floating_point else v.to(device)
            for k, v in inputs.items()
        }
        with torch.no_grad():
            generated = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS)
        # generate echoes the language/punctuation decoder prompt; strip it
        return processor.tokenizer.decode(generated[0][prompt_len:], skip_special_tokens=True).strip()

    return sequential_map(one, rows, desc, checkpoint=checkpoint)

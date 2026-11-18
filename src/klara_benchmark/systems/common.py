import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm


def audio_bytes(cell) -> tuple[bytes, str]:
    """(bytes, filename) from a parquet audio cell."""
    data = cell["bytes"] if isinstance(cell, dict) else cell
    name = (cell.get("path") if isinstance(cell, dict) else None) or ""
    if not name:
        name = "audio.flac" if data[:4] == b"fLaC" else "audio.wav"
    return data, name


def audio_array(cell) -> dict:
    """Decoded mono 16 kHz float array for local models."""
    import io

    import librosa
    import soundfile as sf

    data, _ = audio_bytes(cell)
    arr, sr = sf.read(io.BytesIO(data), dtype="float32")
    if arr.ndim > 1:
        arr = arr.mean(axis=1)
    if sr != 16000:
        arr = librosa.resample(arr, orig_sr=sr, target_sr=16000)
    return {"array": arr, "sampling_rate": 16000}


def _load_checkpoint(checkpoint: Path | None) -> dict:
    """{row_id: hypothesis} from an earlier run of the same output file."""
    if not checkpoint or not checkpoint.exists():
        return {}
    done = {}
    with open(checkpoint) as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                done[rec["id"]] = rec["hypothesis"]
    return done


class _Checkpointer:
    """Appends {id, hypothesis} lines, flushed per row so a kill loses at most the in-flight row."""

    def __init__(self, path: Path | None):
        self._f = open(path, "a") if path else None

    def write(self, row_id, hypothesis: str) -> None:
        if self._f:
            self._f.write(json.dumps({"id": row_id, "hypothesis": hypothesis}, ensure_ascii=False) + "\n")
            self._f.flush()

    def close(self) -> None:
        if self._f:
            self._f.close()


def parallel_map(fn, rows: list, workers: int, desc: str, *, checkpoint: Path | None = None) -> list:
    """Order-preserving thread-pooled map with a progress bar. `checkpoint` is the
    output jsonl, resumed from and appended to."""
    done = _load_checkpoint(checkpoint)
    pending = [r for r in rows if r["id"] not in done]
    results = dict(done)
    ckpt = _Checkpointer(checkpoint if pending else None)
    try:
        if pending:
            pool = ThreadPoolExecutor(max_workers=workers)
            try:
                futures = {pool.submit(fn, r): r for r in pending}
                bar = tqdm(as_completed(futures), total=len(rows), initial=len(done), desc=desc)
                for f in bar:
                    row = futures[f]
                    hyp = f.result()
                    results[row["id"]] = hyp
                    ckpt.write(row["id"], hyp)
            finally:
                # A failing row must abort the run, not drain thousands of rows
                # failing the same way.
                pool.shutdown(wait=True, cancel_futures=True)
    finally:
        ckpt.close()
    return [results[r["id"]] for r in rows]


def sequential_map(fn, rows: list, desc: str, *, checkpoint: Path | None = None) -> list:
    """Single-threaded `parallel_map` for local GPU models."""
    done = _load_checkpoint(checkpoint)
    pending = [r for r in rows if r["id"] not in done]
    results = dict(done)
    ckpt = _Checkpointer(checkpoint if pending else None)
    try:
        for row in tqdm(pending, desc=desc, initial=len(done), total=len(rows)):
            hyp = fn(row)
            results[row["id"]] = hyp
            ckpt.write(row["id"], hyp)
    finally:
        ckpt.close()
    return [results[r["id"]] for r in rows]

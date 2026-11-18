import io
import os
import re
from pathlib import Path

import pyarrow.parquet as pq
import soundfile as sf
from huggingface_hub import snapshot_download
from huggingface_hub.errors import GatedRepoError, HfHubHTTPError, RepositoryNotFoundError
from pydantic import BaseModel, ConfigDict

from klara_benchmark import DATA_DIR

CONTACT = "frederic.odermatt@44ai.ch"


class Dataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    repo_id: str
    revision: str | None = None
    file_pattern: str = "*.parquet"
    reference_column: str | None = None
    formatted_column: str = "formatted"
    formatted_terms_column: str | None = None
    dialect_groups: dict[str, str] | None = None
    chunked_view_of: str | None = None


DIALECT_GROUPS = {
    "swiss-dialect-1": "Swiss German dialects",
    "swiss-dialect-2": "Swiss German dialects",
    "swiss-dialect-3": "Swiss German dialects",
    "german-dialect-1": "German regional dialects",
    "german-dialect-2": "German regional dialects",
    "german-dialect-3": "German regional dialects",
    "high-german": "High German",
    "austrian": "Austrian German",
    "non-native": "Non-native German",
}

DATASETS = {
    "44ai-clinical-val": Dataset(
        repo_id="44ai/44ai-clinical-de-validation",
        reference_column="transcript",
        dialect_groups=DIALECT_GROUPS,
    ),
    # Pinned, because clip file <set>NNNN.wav of a chunked view is row NNNN of this revision.
    "medterm": Dataset(
        repo_id="corti/med-term",
        revision="478865727c56f3b17ce20ee6c5e11f84f16676be",
        file_pattern="de/*.parquet",
        reference_column="transcription",
        formatted_column="transcription_formatted",
        formatted_terms_column="medical_terms_formatted",
    ),
    "meddictate": Dataset(
        repo_id="corti/med-dictate",
        revision="2a840558d221b4f306c52419d58f93270ea599bb",
        file_pattern="de/*.parquet",
        reference_column="transcription",
        formatted_column="transcription_formatted",
        formatted_terms_column="medical_terms_formatted",
    ),
    "medterm-chunked": Dataset(
        repo_id="44ai/44ai-corti-med-term-de-chunked",
        chunked_view_of="medterm",
    ),
    "meddictate-chunked": Dataset(
        repo_id="44ai/44ai-corti-med-dictate-de-chunked",
        chunked_view_of="meddictate",
    ),
}

SCORED = [name for name, spec in DATASETS.items() if spec.chunked_view_of is None]
VIEWS = {spec.chunked_view_of: name for name, spec in DATASETS.items() if spec.chunked_view_of}


_ACCESS_HELP = (
    "The datasets are gated. Set HF_TOKEN in .env (see .env.example) and request "
    f"access on the dataset page, or contact {CONTACT} for quick access."
)


def download() -> None:
    token = os.environ.get("HF_TOKEN") or None
    for name, spec in DATASETS.items():
        try:
            snapshot_download(
                spec.repo_id,
                repo_type="dataset",
                local_dir=DATA_DIR / name,
                allow_patterns=[spec.file_pattern],
                revision=spec.revision,
                token=token,
            )
        except (GatedRepoError, RepositoryNotFoundError, HfHubHTTPError) as e:
            raise SystemExit(f"Cannot download {spec.repo_id}: {e}\n\n{_ACCESS_HELP}") from e
        print(f"{name}: ready ({spec.repo_id})")


def _files(name: str) -> list:
    spec = DATASETS[name]
    files = sorted((DATA_DIR / name).rglob(spec.file_pattern))
    if not files:
        raise SystemExit(f"Dataset '{name}' not found under data/. Run `make install` first.")
    return files


def load(name: str, with_audio: bool = True) -> list[dict]:
    """Rows as {id, audio, reference, formatted_reference, medical_terms,
    medical_terms_formatted, dialect, group}. `with_audio=False` skips the audio bytes."""
    spec = DATASETS[name]
    files = _files(name)
    columns = [spec.reference_column, spec.formatted_column, "medical_terms"]
    if spec.formatted_terms_column:
        columns.append(spec.formatted_terms_column)
    if with_audio:
        columns.append("audio")
    rows: list[dict] = []
    for f in files:
        rows.extend(pq.read_table(f, columns=columns).to_pylist())
    dialects = None
    if spec.dialect_groups:
        # File names are <row>_<dialect>.mp3. Reads only the name, not the audio bytes.
        paths = [p for f in files for p in pq.read_table(f, columns=["audio.path"]).column(0).to_pylist()]
        dialects = [Path(p).stem.partition("_")[2] if p else "" for p in paths]
    return [
        {
            "id": i,
            "audio": r.get("audio"),
            "reference": r[spec.reference_column],
            "formatted_reference": r[spec.formatted_column],
            "medical_terms": [t for t in (r.get("medical_terms") or []) if t],
            "medical_terms_formatted": (
                [t for t in (r.get(spec.formatted_terms_column) or []) if t]
                if spec.formatted_terms_column else None
            ),
            "dialect": dialects[i] if dialects else None,
            "group": spec.dialect_groups.get(dialects[i]) if dialects else None,
        }
        for i, r in enumerate(rows)
    ]


def mer_pair(row: dict) -> tuple[str, list[str]]:
    """(reference, term list) MER scores this row against: the formatted pair
    when the dataset ships one, else the verbatim pair.

    Terms are matched as spans of the reference, so both must come from the
    same column. Normalization folds number words to digits but does not glue
    them: a verbatim "HbA eins c" (-> "hba 1 c") never matches a formatted
    "HbA1c", so mixing columns would charge every system for the canonical
    spelling and silently drop those spans from MER's denominator."""
    if row.get("medical_terms_formatted") is not None:
        return row["formatted_reference"], row["medical_terms_formatted"]
    return row["reference"], row["medical_terms"]


def _view_rows(view: str, columns: list[str]) -> list[dict]:
    rows: list[dict] = []
    for f in _files(view):
        rows.extend(pq.read_table(f, columns=columns).to_pylist())
    return rows


def load_clips(view: str) -> list[dict]:
    """{id, audio} rows of a chunked view. id is the clip's row index."""
    return [{"id": i, "audio": r["audio"]} for i, r in enumerate(_view_rows(view, ["audio"]))]


def join_clips(view: str, hypotheses: dict[int, str]) -> dict[int, str]:
    """Clip hypotheses joined per recording in `chunk_index` order, keyed by the
    full-length set's row id (clip file `<set>NNNN.wav` is row NNNN)."""
    parts: dict[int, list[tuple[int, str]]] = {}
    for i, r in enumerate(_view_rows(view, ["original_file", "chunk_index"])):
        recording = int(re.search(r"(\d+)\.wav$", r["original_file"]).group(1))
        parts.setdefault(recording, []).append((r["chunk_index"], hypotheses.get(i, "")))
    return {
        recording: " ".join(h.strip() for _, h in sorted(clips) if h and h.strip())
        for recording, clips in parts.items()
    }


def audio_hours(name: str) -> float:
    """From the audio headers, since not every dataset ships a duration column."""
    seconds = 0.0
    for f in _files(name):
        for audio in pq.read_table(f, columns=["audio"]).column(0).to_pylist():
            info = sf.info(io.BytesIO(audio["bytes"]))
            seconds += info.frames / info.samplerate
    return seconds / 3600


if __name__ == "__main__":
    download()

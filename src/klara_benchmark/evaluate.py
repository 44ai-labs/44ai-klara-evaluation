import importlib
import json
import sys

from klara_benchmark import ROOT, TRANSCRIPTIONS_DIR, datasets
from klara_benchmark.systems import SYSTEMS, require_env


def main(names: list[str]) -> None:
    available = ", ".join(SYSTEMS)
    if not names:
        raise SystemExit(f"usage: make evaluate <system> ...\nsystems: {available}")
    unknown = [n for n in names if n not in SYSTEMS]
    if unknown:
        raise SystemExit(f"unknown system(s): {', '.join(unknown)} - available: {available}")

    # Check keys and deps for every requested system before running any.
    for name in names:
        spec = SYSTEMS[name]
        for key in spec.required_env:
            require_env(key)
        if spec.local:
            try:
                import torch  # noqa: F401
            except ModuleNotFoundError:
                raise SystemExit(f"{name} runs locally - run `make install-local` first") from None

    for name in names:
        outdir = TRANSCRIPTIONS_DIR / name
        outdir.mkdir(parents=True, exist_ok=True)
        spec = SYSTEMS[name]
        module = importlib.import_module(f"klara_benchmark.systems.{spec.module}")
        for ds_name in datasets.SCORED:
            view = datasets.VIEWS.get(ds_name) if spec.corti_input == "chunked" else None
            if view:
                # Clip transcripts; `make score` joins them per recording.
                rows = datasets.load_clips(view)
                outpath = outdir / f"{ds_name}.chunks.jsonl"
            else:
                rows = datasets.load(ds_name)
                outpath = outdir / f"{ds_name}.jsonl"
            if outpath.exists():
                with open(outpath) as f:
                    existing = sum(1 for line in f if line.strip())
                if existing >= len(rows):
                    answer = input(
                        f"{name}/{ds_name}: {outpath.relative_to(ROOT)} already complete "
                        "(shipped set from our runs) - redo? [y/N] "
                    )
                    if answer.strip().lower() != "y":
                        continue
                    outpath.unlink()  # otherwise transcribe() resumes from it
                else:
                    print(f"{name}/{ds_name}: resuming from {existing}/{len(rows)} rows")
            hypotheses = module.transcribe(rows, desc=f"{name}/{ds_name}", checkpoint=outpath)
            with open(outpath, "w") as f:
                for row, hyp in zip(rows, hypotheses, strict=True):
                    f.write(json.dumps({"id": row["id"], "hypothesis": hyp}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])

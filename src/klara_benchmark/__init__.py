from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
TRANSCRIPTIONS_DIR = ROOT / "transcriptions"
RESULTS_DIR = ROOT / "results"

load_dotenv(ROOT / ".env")

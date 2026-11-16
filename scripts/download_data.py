"""Fetch every raw input for the scorecard. Run from the project root: python scripts/download_data.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scorecard.download import download_all  # noqa: E402

if __name__ == "__main__":
    download_all()

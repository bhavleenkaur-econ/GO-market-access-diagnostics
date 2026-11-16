"""Build the station scorecard from the raw files. Run from the project root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scorecard.pipeline import run  # noqa: E402

if __name__ == "__main__":
    table, recs, _waits, _dates = run()
    priority = table[table.quadrant.eq("priority")][
        ["station_name", "line_name", "market_score", "conditions_score", "primary_likely", "constraint_share", "is_tie"]
    ]
    print(priority.to_string(index=False))
    print(f"\n{len(priority)} priority stations, {len(recs)} recommendation rows")

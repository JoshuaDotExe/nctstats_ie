"""
recalc_percentages.py

Recalculates all _pct fields from raw counts across every
<year>-Make-Model-Data.json file. This replaces the source-file
rounding (which drifts by ±0.1) with values computed directly
from the counts, making percentages consistent across all years.

Formula: pct = round(count / Total * 100, 1)  — 0.0 when Total = 0
"""

import json
import glob
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

PCT_KEYS = [
    "Pass", "Fail",
    "Safety", "Lighting", "Steering", "Braking", "Wheels", "Engine",
    "Chassis", "SideSlip", "Suspension", "Light", "Brake", "Emissions",
    "Other", "Incomplete",
]


def recalc(record: dict) -> dict:
    t = record.get("Total", 0)
    for key in PCT_KEYS:
        count = record.get(key, 0)
        record[f"{key}_pct"] = round(count / t * 100, 1) if t else 0.0
    return record


def main() -> None:
    files = sorted(DATA_DIR.glob("*/*-Make-Model-Data.json"))
    total_fixed = 0

    for path in files:
        data = json.load(open(path, encoding="utf-8"))
        fixed = 0
        updated = []
        for record in data:
            original_pcts = {f"{k}_pct": record.get(f"{k}_pct") for k in PCT_KEYS}
            recalc(record)
            new_pcts = {f"{k}_pct": record[f"{k}_pct"] for k in PCT_KEYS}
            if original_pcts != new_pcts:
                fixed += 1
            updated.append(record)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(updated, f, indent=2, ensure_ascii=False)

        total_fixed += fixed
        print(f"  ✓  {path.relative_to(ROOT)}  ({len(updated):,} records, {fixed} pcts recalculated)")

    print(f"\nDone. {total_fixed} percentage values updated across {len(files)} files.")


if __name__ == "__main__":
    main()

"""
count_make_model.py

Prints the total number of tests for a given make/model across all years,
broken down by test year (summed across all car years).

Usage:
    python scripts/count_make_model.py                        # defaults: FORD / FOCUS
    python scripts/count_make_model.py BMW "3 SERIES"
    python scripts/count_make_model.py "VOLKSWAGEN" "GOLF"
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"


def main() -> None:
    target_make  = sys.argv[1].strip().upper() if len(sys.argv) > 1 else "FORD"
    target_model = sys.argv[2].strip().upper() if len(sys.argv) > 2 else "FOCUS"

    files = sorted(DATA_DIR.glob("*/*-Make-Model-Data-aggregated.json"))
    if not files:
        print("No aggregated files found. Run aggregate_by_core_model.py first.")
        return

    print(f"Searching for: {target_make} / {target_model}")
    print()

    grand_total = 0
    results = []

    for path in files:
        test_year = int(path.parent.name)
        with open(path, encoding="utf-8") as f:
            records = json.load(f)

        year_total = sum(
            r["Total"]
            for r in records
            if r["Make"].strip().upper() == target_make
            and r["Model"].strip().upper() == target_model
        )
        results.append((test_year, year_total))
        grand_total += year_total

    if grand_total == 0:
        print(f"No records found for {target_make} / {target_model}.")
        print("Tip: make and model are matched case-insensitively against the aggregated files.")
        return

    # Print table
    col_w = max(len(str(r[1])) for r in results)
    col_w = max(col_w, 12)
    print(f"{'Test Year':>10}  {'Total Tested':>{col_w}}")
    print("-" * (10 + 2 + col_w))
    for test_year, total in results:
        flag = "  ◀ lowest" if total == min(r[1] for r in results if r[1] > 0) else ""
        print(f"{test_year:>10}  {total:>{col_w},}{flag}")
    print("-" * (10 + 2 + col_w))
    print(f"{'TOTAL':>10}  {grand_total:>{col_w},}")


if __name__ == "__main__":
    main()

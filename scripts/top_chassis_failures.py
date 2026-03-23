"""
top_chassis_failures.py

Finds the car models with the highest chassis failure rates across all years.

For each (Make, Model) pair, aggregates across all test years and car years:
  - total tests
  - total chassis failures
  - chassis failure rate = Chassis / Total * 100

Writes the top N results to app/public/top_chassis_failures.json

Usage:
    python3 scripts/top_chassis_failures.py [--top N]   (default N=10)
"""

import argparse
import json
from pathlib import Path

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_FILE = ROOT / "app/public/top_chassis_failures.json"

MIN_TOTAL     = 10000  # minimum total tests across all years
MIN_YEARS     = 8      # minimum number of test years with data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--min-total", type=int, default=MIN_TOTAL,
                        help=f"Minimum total tests to be included (default {MIN_TOTAL})")
    parser.add_argument("--min-years", type=int, default=MIN_YEARS,
                        help=f"Minimum number of test years with data (default {MIN_YEARS})")
    args = parser.parse_args()

    files = sorted(DATA_DIR.glob("*/*-Make-Model-Data-aggregated.json"))
    if not files:
        print("No aggregated files found. Run aggregate_by_core_model.py first.")
        return

    # Accumulate {(Make, Model): {total, chassis, by_year: {test_year: {total, chassis}}}}
    accum: dict[tuple[str, str], dict] = {}

    for path in files:
        test_year = int(path.parent.name)
        records = json.load(open(path, encoding="utf-8"))
        for r in records:
            key = (r["Make"], r["Model"])
            if key not in accum:
                accum[key] = {"total": 0, "chassis": 0, "by_year": {}}
            accum[key]["total"]   += r.get("Total", 0)
            accum[key]["chassis"] += r.get("Chassis", 0)
            by_year = accum[key]["by_year"]
            if test_year not in by_year:
                by_year[test_year] = {"total": 0, "chassis": 0}
            by_year[test_year]["total"]   += r.get("Total", 0)
            by_year[test_year]["chassis"] += r.get("Chassis", 0)

    # All test years present across the dataset
    all_test_years = sorted({y for v in accum.values() for y in v["by_year"]})

    # Calculate rate, filter by minimum total and year coverage
    results = []
    for (make, model), v in accum.items():
        years_with_data = sum(1 for yd in v["by_year"].values() if yd["total"] > 0)
        if v["total"] < args.min_total:
            continue
        if years_with_data < args.min_years:
            continue
        if model.strip().upper() == "OTHER":
            continue
        rate = v["chassis"] / v["total"] * 100

        # Per-year chassis rate series (None where no data for that year)
        yearly_rates: list[float | None] = []
        for y in all_test_years:
            yd = v["by_year"].get(y)
            if yd and yd["total"] > 0:
                yearly_rates.append(round(yd["chassis"] / yd["total"] * 100, 2))
            else:
                yearly_rates.append(None)

        results.append({
            "make":           make,
            "model":          model,
            "label":          f"{make} {model}",
            "total":          v["total"],
            "chassis":        v["chassis"],
            "chassis_rate":   round(rate, 2),
            "years_with_data": years_with_data,
            "years":          all_test_years,
            "yearly_rates":   yearly_rates,
        })

    results.sort(key=lambda x: x["chassis_rate"], reverse=True)
    top = results[: args.top]

    # Compute all-Ireland average chassis rate per test year (across every make/model)
    year_totals:  dict[int, int] = {}
    year_chassis: dict[int, int] = {}
    for v in accum.values():
        for y, yd in v["by_year"].items():
            year_totals[y]  = year_totals.get(y, 0)  + yd["total"]
            year_chassis[y] = year_chassis.get(y, 0) + yd["chassis"]

    avg_yearly_rates: list[float | None] = []
    for y in all_test_years:
        t = year_totals.get(y, 0)
        avg_yearly_rates.append(round(year_chassis[y] / t * 100, 2) if t > 0 else None)

    output = {
        "avg_years":        all_test_years,
        "avg_yearly_rates": avg_yearly_rates,
        "models":           top,
    }

    # Print to terminal
    print(f"Top {args.top} models by chassis failure rate "
          f"(min {args.min_total:,} tests, min {args.min_years} years with data)\n")
    print(f"{'Make':<20} {'Model':<20} {'Total':>8}  {'Yrs':>4}  {'Chassis':>8}  {'Rate':>7}")
    print("-" * 74)
    for r in top:
        print(f"{r['make']:<20} {r['model']:<20} {r['total']:>8,}  {r['years_with_data']:>4}  {r['chassis']:>8,}  {r['chassis_rate']:>6.2f}%")

    print("\nAll-Ireland average chassis rate per test year:")
    for y, rate in zip(all_test_years, avg_yearly_rates):
        print(f"  {y}: {rate}%")

    # Write JSON for the frontend
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nWrote → {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

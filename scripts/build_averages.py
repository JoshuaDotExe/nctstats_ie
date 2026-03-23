"""
build_averages.py

For each test year, computes the fleet-wide average pass/fail/category rates
broken down by car year (vehicle year of birth).

Output: app/public/averages.json
Shape:
{
  "2016": {                        # test year
    "1990": { "T": 12, "P": 8, "Pp": 66.7, "F": 4, "Fp": 33.3, ... },
    "1991": { ... },
    ...
  },
  ...
}

Rates (Pp, Fp, Sap, ...) are weighted averages — computed from summed counts,
not averaged percentages.

Usage:
    python3 scripts/build_averages.py
"""

import json
from pathlib import Path

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_FILE = ROOT / "app/public/averages.json"

# Mapping from aggregated JSON long names → short API keys
COUNT_MAP = {
    "Total":      "T",
    "Pass":       "P",
    "Fail":       "F",
    "Safety":     "Sa",
    "Lighting":   "Li",
    "Steering":   "St",
    "Braking":    "Br",
    "Wheels":     "Wh",
    "Engine":     "En",
    "Chassis":    "Ch",
    "SideSlip":   "Ss",
    "Suspension": "Su",
    "Light":      "Lt",
    "Brake":      "Bk",
    "Emissions":  "Em",
    "Other":      "Ot",
    "Incomplete": "In",
}

FAILURE_KEYS = ["Sa", "Li", "St", "Br", "Wh", "En", "Ch", "Ss", "Su", "Lt", "Bk", "Em", "Ot", "In"]


def main() -> None:
    files = sorted(DATA_DIR.glob("*/*-Make-Model-Data-aggregated.json"))
    if not files:
        print("No aggregated files found.")
        return

    # {test_year: {car_year: {short_key: sum}}}
    accum: dict[int, dict[int, dict[str, int]]] = {}

    for path in files:
        test_year = int(path.parent.name)
        records = json.load(open(path, encoding="utf-8"))
        if test_year not in accum:
            accum[test_year] = {}

        for r in records:
            car_year = int(r["Year"])
            if car_year not in accum[test_year]:
                accum[test_year][car_year] = {sk: 0 for sk in COUNT_MAP.values()}
            cy = accum[test_year][car_year]
            for long_key, short_key in COUNT_MAP.items():
                cy[short_key] += int(r.get(long_key, 0) or 0)

    # Build output: compute rates from summed counts
    output: dict[str, dict[str, dict]] = {}
    for test_year, by_car_year in sorted(accum.items()):
        output[str(test_year)] = {}
        for car_year, counts in sorted(by_car_year.items()):
            t = counts["T"]
            if t == 0:
                continue
            f = counts["F"]
            entry: dict[str, float | int] = {
                "T":  t,
                "P":  counts["P"],
                "Pp": round(counts["P"] / t * 100, 1),
                "F":  f,
                "Fp": round(f / t * 100, 1),
            }
            for sk in FAILURE_KEYS:
                entry[sk]        = counts[sk]
                entry[sk + "p"]  = round(counts[sk] / t * 100, 1)
            output[str(test_year)][str(car_year)] = entry

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(output, separators=(",", ":")), encoding="utf-8")

    total_entries = sum(len(v) for v in output.values())
    print(f"Wrote {len(output)} test years, {total_entries} car-year buckets → {OUT_FILE.relative_to(ROOT)}")
    # Show a sample
    sample_year = list(output.keys())[5]
    sample_cy   = list(output[sample_year].keys())[5]
    print(f"Sample [{sample_year}][{sample_cy}]: {output[sample_year][sample_cy]}")


if __name__ == "__main__":
    main()

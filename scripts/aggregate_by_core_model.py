"""
aggregate_by_core_model.py

For each year JSON file, groups records by (Make, core_model, Year),
summing all raw count fields and recalculating all _pct fields.

The canonical core_model name is resolved via data/model_lookup.json;
records whose (Make, raw_Model) key is absent from the lookup fall back
to the raw Model value (same behaviour as apply_core_model.py).

Output:  data/<year>/<year>-Make-Model-Data-aggregated.json
         (same schema as the source files, but with an extra
          "core_model" field replacing / superseding "Model")

Usage:
    python scripts/aggregate_by_core_model.py           # write all years
    python scripts/aggregate_by_core_model.py --dry-run # stats only
"""

import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
LOOKUP_PATH = DATA_DIR / "model_lookup.json"

# Glob only the canonical per-year source files — skip aggregated / lookup files
JSON_FILES = sorted(
    p for p in DATA_DIR.glob("*/*-Make-Model-Data.json")
    if "aggregated" not in p.name
)

# Count fields that get summed; order matches the schema
COUNT_FIELDS = [
    "Total", "Pass", "Fail",
    "Safety", "Lighting", "Steering", "Braking", "Wheels",
    "Engine", "Chassis", "SideSlip", "Suspension",
    "Light", "Brake", "Emissions", "Other", "Incomplete",
]

# Percentage fields paired with their count field
PCT_PAIRS = [
    ("Pass_pct",        "Pass"),
    ("Fail_pct",        "Fail"),
    ("Safety_pct",      "Safety"),
    ("Lighting_pct",    "Lighting"),
    ("Steering_pct",    "Steering"),
    ("Braking_pct",     "Braking"),
    ("Wheels_pct",      "Wheels"),
    ("Engine_pct",      "Engine"),
    ("Chassis_pct",     "Chassis"),
    ("SideSlip_pct",    "SideSlip"),
    ("Suspension_pct",  "Suspension"),
    ("Light_pct",       "Light"),
    ("Brake_pct",       "Brake"),
    ("Emissions_pct",   "Emissions"),
    ("Other_pct",       "Other"),
    ("Incomplete_pct",  "Incomplete"),
]


def load_lookup() -> dict[str, dict[str, str]]:
    with open(LOOKUP_PATH, encoding="utf-8") as f:
        return json.load(f)


def resolve_core(lookup: dict, make: str, model: str) -> str:
    """Return the canonical core model name, falling back to raw model."""
    make_dict = lookup.get(make.strip().upper(), {})
    return make_dict.get(model.strip().upper(), model.strip().upper())


def aggregate_file(
    path: Path,
    lookup: dict,
    dry_run: bool,
) -> tuple[int, int, int]:
    """
    Aggregate one year file.
    Returns (raw_record_count, aggregated_record_count, fallback_count).
    """
    with open(path, encoding="utf-8") as f:
        records: list[dict] = json.load(f)

    # Accumulate counts keyed by (Make, core_model, Year)
    buckets: dict[tuple, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    fallbacks: set[tuple[str, str]] = set()

    for r in records:
        make = str(r.get("Make", "")).strip().upper()
        model = str(r.get("Model", "")).strip().upper()
        year = r.get("Year")

        core = resolve_core(lookup, make, model)
        if core == model and lookup.get(make) and model not in lookup[make]:
            fallbacks.add((make, model))

        key = (make, core, year)
        for field in COUNT_FIELDS:
            buckets[key][field] += int(r.get(field, 0))

    # Build output records
    out: list[dict] = []
    for (make, core, year), counts in sorted(buckets.items()):
        total = counts["Total"]
        rec: dict = {
            "Make": make,
            "Model": core,
            "Year": year,
        }
        for field in COUNT_FIELDS:
            rec[field] = counts[field]
            pct_field = f"{field}_pct" if field != "Total" else None
            # Total has no _pct; inject per PCT_PAIRS below
        # Now add all _pct fields in schema order
        for pct_field, count_field in PCT_PAIRS:
            count = counts[count_field]
            rec[pct_field] = round(count / total * 100, 1) if total else 0.0
        out.append(rec)

    # Re-order fields to match the canonical schema
    FIELD_ORDER = (
        ["Make", "Model", "Year", "Total"]
        + [f for pair in zip(
            ["Pass", "Fail", "Safety", "Lighting", "Steering", "Braking",
             "Wheels", "Engine", "Chassis", "SideSlip", "Suspension",
             "Light", "Brake", "Emissions", "Other", "Incomplete"],
            ["Pass_pct", "Fail_pct", "Safety_pct", "Lighting_pct",
             "Steering_pct", "Braking_pct", "Wheels_pct", "Engine_pct",
             "Chassis_pct", "SideSlip_pct", "Suspension_pct", "Light_pct",
             "Brake_pct", "Emissions_pct", "Other_pct", "Incomplete_pct"]
        ) for f in pair]
    )
    out_ordered = [{k: rec[k] for k in FIELD_ORDER if k in rec} for rec in out]

    if not dry_run:
        out_path = path.parent / path.name.replace(
            "-Make-Model-Data.json", "-Make-Model-Data-aggregated.json"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_ordered, f, indent=2, ensure_ascii=False)
        print(f"  ✅  {out_path.relative_to(ROOT)}  "
              f"({len(records)} → {len(out_ordered)} records)")

    return len(records), len(out_ordered), len(fallbacks)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats without writing files.")
    args = parser.parse_args()

    lookup = load_lookup()

    total_raw = total_agg = total_fb = 0
    for path in JSON_FILES:
        raw, agg, fb = aggregate_file(path, lookup, dry_run=args.dry_run)
        total_raw += raw
        total_agg += agg
        total_fb += fb
        if args.dry_run:
            rel = str(path.relative_to(ROOT))
            print(f"  {rel:60s}  {raw:6d} → {agg:5d} records  "
                  f"({fb} fallbacks)")

    print(f"\nTotal:  {total_raw} raw records → {total_agg} aggregated records "
          f"({total_fb} fallback (Make, Model) pairs)")
    if args.dry_run:
        print("(dry-run — no files written)")


if __name__ == "__main__":
    main()

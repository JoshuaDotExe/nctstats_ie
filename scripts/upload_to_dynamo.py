"""
Upload NCT aggregated test data from all years to DynamoDB.

Reads every  data/<year>/<year>-Make-Model-Data-aggregated.json  file,
maps long attribute keys to short keys, and writes each record with:

    PK = "MODEL#<MAKE>#<MODEL>"
    SK = "TEST_YEAR#<test_year>#CAR_YEAR#<car_year>"

Supports:
    --purge      Delete all existing items before uploading (scan + batch-delete)
    --dry-run    Print item counts without writing anything
    --year 2016  Upload only a single year

Usage:
    python scripts/upload_to_dynamo.py --purge          # wipe + upload all
    python scripts/upload_to_dynamo.py --dry-run        # just show counts
    python scripts/upload_to_dynamo.py --year 2016      # one year only
"""

import json
import sys
import argparse
import time
from decimal import Decimal
from pathlib import Path

import boto3

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# ── Long key → short key mapping (from README) ────────────────────────────────
COUNT_KEY_MAP = {
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

PCT_KEY_MAP = {
    "Pass_pct":       "Pp",
    "Fail_pct":       "Fp",
    "Safety_pct":     "Sap",
    "Lighting_pct":   "Lip",
    "Steering_pct":   "Stp",
    "Braking_pct":    "Brp",
    "Wheels_pct":     "Whp",
    "Engine_pct":     "Enp",
    "Chassis_pct":    "Chp",
    "SideSlip_pct":   "Ssp",
    "Suspension_pct": "Sup",
    "Light_pct":      "Ltp",
    "Brake_pct":      "Bkp",
    "Emissions_pct":  "Emp",
    "Other_pct":      "Otp",
    "Incomplete_pct": "Inp",
}

TABLE_NAME = "nct_results"
REGION = "eu-west-1"


# ── Helpers ────────────────────────────────────────────────────────────────────

def find_aggregated_files(year: int | None = None) -> list[Path]:
    """Return sorted list of aggregated JSON files (all years or one)."""
    if year:
        pattern = f"{year}/{year}-Make-Model-Data-aggregated.json"
        matches = list(DATA_DIR.glob(pattern))
        if not matches:
            print(f"Error: no aggregated file for year {year}", file=sys.stderr)
            sys.exit(1)
        return matches
    return sorted(DATA_DIR.glob("*/*-Make-Model-Data-aggregated.json"))


def records_to_items(records: list[dict], test_year: int) -> list[dict]:
    """Convert flat JSON records to DynamoDB items with short keys."""
    items = []
    for r in records:
        make  = str(r["Make"]).strip().upper()
        model = str(r["Model"]).strip().upper()
        car_year = int(r["Year"])

        item = {
            "pk":        f"MODEL#{make}#{model}",
            "sk":        f"TEST_YEAR#{test_year}#CAR_YEAR#{car_year}",
            "make":      make,
            "model":     model,
            "test_year": test_year,
            "car_year":  car_year,
        }

        # Count fields → short keys (int)
        for long_key, short_key in COUNT_KEY_MAP.items():
            val = r.get(long_key, 0)
            item[short_key] = int(val)

        # Percentage fields → short keys (Decimal for DynamoDB float support)
        for long_key, short_key in PCT_KEY_MAP.items():
            val = r.get(long_key, 0.0)
            item[short_key] = Decimal(str(val))

        items.append(item)
    return items


def purge_table(table) -> int:
    """Delete every item from the table via scan + batch-delete. Returns count."""
    print(f"Purging table {TABLE_NAME}…")
    deleted = 0
    scan_kwargs: dict = {
        "ProjectionExpression": "pk, sk",
    }
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        if not items:
            break
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
                deleted += 1
        if deleted % 5000 == 0:
            print(f"  …deleted {deleted} items so far")
        # Continue scanning if there are more pages
        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break
    print(f"  Purged {deleted} items.")
    return deleted


def batch_upload(table, items: list[dict]) -> None:
    """Write items to DynamoDB using batch_writer (auto-handles 25-item batches)."""
    total = len(items)
    written = 0
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
            written += 1
            if written % 2000 == 0:
                print(f"    {written:,}/{total:,} items written")
    print(f"    {total:,}/{total:,} items written ✅")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--purge", action="store_true",
                        help="Delete all existing items before uploading.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print item counts without writing to DynamoDB.")
    parser.add_argument("--year", type=int, default=None,
                        help="Upload only a single year (e.g. --year 2016).")
    args = parser.parse_args()

    files = find_aggregated_files(args.year)
    print(f"Found {len(files)} aggregated file(s) to upload.\n")

    # Collect all items across years
    all_items: list[dict] = []
    for path in files:
        test_year = int(path.parent.name)  # e.g. data/2016/ → 2016
        with open(path, encoding="utf-8") as f:
            records = json.load(f)
        items = records_to_items(records, test_year)
        all_items.extend(items)
        print(f"  {path.relative_to(ROOT)}  →  {len(items):,} items  (test year {test_year})")

    print(f"\nTotal items to upload: {len(all_items):,}")

    if args.dry_run:
        print("\n(dry-run — nothing written to DynamoDB)")
        return

    # Connect
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    # Purge existing data if requested
    if args.purge:
        purge_table(table)
        print()

    # Upload
    start = time.time()
    print(f"Uploading to {TABLE_NAME}…")
    batch_upload(table, all_items)
    elapsed = time.time() - start
    print(f"\nDone!  {len(all_items):,} items written in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()

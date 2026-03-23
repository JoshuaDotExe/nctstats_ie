"""
Upload NCT data to DynamoDB in a compact base64-encoded format.

Instead of one item per (make, model, test_year, car_year) with 30+ attributes,
this version stores one item per (make, model, test_year) with a list of encoded
strings — one per car year.

Each string in the list is:
    <4-char car year><base64-encoded percentage bytes>

The base64 payload encodes 16 percentage values, each stored as a single byte
(0–200, representing 0.0–100.0% in 0.5% steps).

Percentage field order (index in the byte array):
    0  Pp   (Pass %)
    1  Fp   (Fail %)
    2  Sap  (Safety %)
    3  Lip  (Lighting %)
    4  Stp  (Steering %)
    5  Brp  (Braking %)
    6  Whp  (Wheels %)
    7  Enp  (Engine %)
    8  Chp  (Chassis %)
    9  Ssp  (SideSlip %)
   10  Sup  (Suspension %)
   11  Ltp  (Light %)
   12  Bkp  (Brake %)
   13  Emp  (Emissions %)
   14  Otp  (Other %)
   15  Inp  (Incomplete %)

DynamoDB schema:
    PK = "MODEL#<MAKE>#<MODEL>"
    SK = "TEST_YEAR#<test_year>"
    d  = ["2007<b64>", "2008<b64>", ...]   (sorted by car year)

Supports:
    --purge      Delete all existing items before uploading (scan + batch-delete)
    --dry-run    Print item counts without writing anything
    --year 2016  Upload only a single year

Usage:
    python scripts/upload_to_dynamo_v2.py --purge          # wipe + upload all
    python scripts/upload_to_dynamo_v2.py --dry-run        # just show counts
    python scripts/upload_to_dynamo_v2.py --year 2016      # one year only
"""

import json
import sys
import argparse
import time
import base64
from pathlib import Path

import boto3

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# ── Percentage field order (matches byte index) ───────────────────────────────
PCT_FIELDS = [
    "Pass_pct",       # 0
    "Fail_pct",       # 1
    "Safety_pct",     # 2
    "Lighting_pct",   # 3
    "Steering_pct",   # 4
    "Braking_pct",    # 5
    "Wheels_pct",     # 6
    "Engine_pct",     # 7
    "Chassis_pct",    # 8
    "SideSlip_pct",   # 9
    "Suspension_pct", # 10
    "Light_pct",      # 11
    "Brake_pct",      # 12
    "Emissions_pct",  # 13
    "Other_pct",      # 14
    "Incomplete_pct", # 15
]

TABLE_NAME = "nct_results"
REGION = "eu-west-1"


# ── Encoding helpers ───────────────────────────────────────────────────────────

def pct_to_byte(pct: float) -> int:
    """Convert a percentage (0.0–100.0) to a byte (0–200) at 0.5% precision."""
    clamped = max(0.0, min(100.0, pct))
    return int(round(clamped * 2))


def encode_car_year(record: dict, car_year: int) -> str:
    """Encode one car-year record as '<4-char year><base64 bytes>'."""
    raw_bytes = bytes(pct_to_byte(record.get(field, 0.0)) for field in PCT_FIELDS)
    b64 = base64.b64encode(raw_bytes).decode("ascii")
    return f"{car_year}{b64}"


# ── File discovery ─────────────────────────────────────────────────────────────

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


# ── Build items ────────────────────────────────────────────────────────────────

def build_items(files: list[Path]) -> list[dict]:
    """
    Read all aggregated JSONs and produce one DynamoDB item per
    (make, model, test_year), each containing a list of encoded strings.
    """
    # Intermediate: { (make, model, test_year) -> [(car_year, record), ...] }
    grouped: dict[tuple[str, str, int], list[tuple[int, dict]]] = {}

    for path in files:
        test_year = int(path.parent.name)
        with open(path, encoding="utf-8") as f:
            records = json.load(f)

        for r in records:
            make = str(r["Make"]).strip().upper()
            model = str(r["Model"]).strip().upper()
            car_year = int(r["Year"])
            key = (make, model, test_year)
            grouped.setdefault(key, []).append((car_year, r))

        print(f"  {path.relative_to(ROOT)}  →  {len(records):,} raw records  (test year {test_year})")

    # Convert grouped data to DynamoDB items
    items = []
    for (make, model, test_year), entries in grouped.items():
        # Sort entries by car year so the list is ordered
        entries.sort(key=lambda x: x[0])
        encoded_list = [encode_car_year(rec, cy) for cy, rec in entries]

        item = {
            "pk": f"MODEL#{make}#{model}",
            "sk": f"TEST_YEAR#{test_year}",
            "d":  encoded_list,
        }
        items.append(item)

    return items


# ── DynamoDB operations ────────────────────────────────────────────────────────

def purge_table(table) -> int:
    """Delete every item from the table via scan + batch-delete. Returns count."""
    print(f"Purging table {TABLE_NAME}…")
    deleted = 0
    scan_kwargs: dict = {"ProjectionExpression": "pk, sk"}
    while True:
        response = table.scan(**scan_kwargs)
        chunk = response.get("Items", [])
        if not chunk:
            break
        with table.batch_writer() as batch:
            for item in chunk:
                batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
                deleted += 1
        if deleted % 5000 == 0:
            print(f"  …deleted {deleted} items so far")
        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break
    print(f"  Purged {deleted} items.")
    return deleted


def batch_upload(table, items: list[dict]) -> None:
    """Write items to DynamoDB using batch_writer."""
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
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--purge", action="store_true",
                        help="Delete all existing items before uploading.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print item counts without writing to DynamoDB.")
    parser.add_argument("--year", type=int, default=None,
                        help="Upload only a single year (e.g. --year 2016).")
    parser.add_argument("--json", type=str, default=None, metavar="PATH",
                        help="Write all items to a JSON file (e.g. --json output.json).")
    args = parser.parse_args()

    files = find_aggregated_files(args.year)
    print(f"Found {len(files)} aggregated file(s).\n")

    items = build_items(files)

    # Count how many encoded entries total
    total_entries = sum(len(item["d"]) for item in items)
    print(f"\nItems (DynamoDB rows): {len(items):,}")
    print(f"Encoded car-year entries: {total_entries:,}")

    # Show a sample
    if items:
        sample = items[0]
        print(f"\nSample item:")
        print(f"  pk = {sample['pk']}")
        print(f"  sk = {sample['sk']}")
        print(f"  d  = [{sample['d'][0]!r}, ...] ({len(sample['d'])} entries)")

    # Write JSON file if requested
    if args.json:
        out_path = Path(args.json)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)
        print(f"\nWrote {len(items):,} items to {out_path}")

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
    batch_upload(table, items)
    elapsed = time.time() - start
    print(f"\nDone!  {len(items):,} items written in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()

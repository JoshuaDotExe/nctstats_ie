"""
Upload NCT test data from JSON files to DynamoDB.

Table design:
  PK = "MODEL#<MAKE>#<MODEL>"
  SK = "TEST_YEAR#<test_year>#CAR_YEAR#<car_year>"

Uses short attribute keys from the README key mapping.
"""

import json
import sys
import boto3
from pathlib import Path

# Long key → short key mapping (from README)
KEY_MAP = {
    "Total": "T",
    "Pass": "P",
    "Fail": "F",
    "Safety": "Sa",
    "Lighting": "Li",
    "Steering": "St",
    "Braking": "Br",
    "Wheels": "Wh",
    "Engine": "En",
    "Chassis": "Ch",
    "SideSlip": "Ss",
    "Suspension": "Su",
    "Light": "Lt",
    "Brake": "Bk",
    "Emissions": "Em",
    "Other": "Ot",
    "Incomplete": "In",
}

TABLE_NAME = "nct_results"
REGION = "eu-west-1"
BATCH_SIZE = 25  # DynamoDB batch_write_item limit


def load_json(filepath: str) -> dict:
    with open(filepath, "r") as f:
        return json.load(f)


def build_items(data: dict, test_year: int) -> list[dict]:
    """Convert the nested JSON structure into flat DynamoDB items."""
    items = []
    for make, models in data.items():
        for model, car_years in models.items():
            for car_year, stats in car_years.items():
                item = {
                    "pk": f"MODEL#{make}#{model}",
                    "sk": f"TEST_YEAR#{test_year}#CAR_YEAR#{car_year}",
                    "make": make,
                    "model": model,
                    "test_year": int(test_year),
                    "car_year": int(car_year),
                }
                # Map long stat keys to short keys
                for long_key, short_key in KEY_MAP.items():
                    if long_key in stats:
                        item[short_key] = stats[long_key]

                items.append(item)
    return items


def batch_write(table, items: list[dict]) -> None:
    """Write items to DynamoDB in batches of 25."""
    total = len(items)
    written = 0

    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
            written += 1
            if written % 500 == 0 or written == total:
                print(f"  Progress: {written}/{total} items written")


def main():
    # Default to the 2016 data file
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = str(
            Path(__file__).resolve().parent.parent
            / "data"
            / "2016"
            / "2016-Manufacturer-Make-Year.json"
        )

    # Extract test year from the filename (e.g. "2016-Manufacturer...")
    filename = Path(filepath).name
    test_year = int(filename.split("-")[0])

    print(f"Loading data from: {filepath}")
    data = load_json(filepath)

    print(f"Building items for test year {test_year}...")
    items = build_items(data, test_year)
    print(f"Total items to write: {len(items)}")

    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    print(f"Writing to DynamoDB table: {TABLE_NAME}")
    batch_write(table, items)
    print("Done!")


if __name__ == "__main__":
    main()

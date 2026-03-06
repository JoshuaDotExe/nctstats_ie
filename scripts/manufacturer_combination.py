import json
import os

DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "data",
    "2016",
    "2016-Make-Model-Data-(pdf).json",
)

OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__),
    "data",
    "2016",
    "manufacturers.json",
)

# Fields that are raw counts and should be summed when duplicates exist.
# Percentages are omitted — they can be recalculated later.
SUM_FIELDS = [
    "Total",
    "Pass",
    "Fail",
    "Safety",
    "Lighting",
    "Steering",
    "Braking",
    "Wheels",
    "Engine",
    "Chassis",
    "SideSlip",
    "Suspension",
    "Light",
    "Brake",
    "Emissions",
    "Other",
    "Incomplete",
]


def build_manufacturer_data(records: list[dict]) -> dict:
    result = {}

    for r in records:
        make = r.get("Make", "").strip()
        model = r.get("Model", "").strip()
        year = r.get("Year", "")

        if not make or not model or year == "!!!!!":
            continue

        # Ensure year is a string key
        year_key = str(year)

        if make not in result:
            result[make] = {}
        if model not in result[make]:
            result[make][model] = {}

        if year_key not in result[make][model]:
            # First entry for this make/model/year — seed with zeros
            result[make][model][year_key] = {field: 0 for field in SUM_FIELDS}

        # Add the counts
        for field in SUM_FIELDS:
            value = r.get(field, 0)
            if isinstance(value, (int, float)):
                result[make][model][year_key][field] += value

    # Sort everything for readability
    sorted_result = {}
    for make in sorted(result):
        sorted_result[make] = {}
        for model in sorted(result[make]):
            sorted_result[make][model] = dict(
                sorted(result[make][model].items(), key=lambda x: x[0])
            )

    return sorted_result


def main():
    with open(DATA_PATH) as f:
        records = json.load(f)

    print(f"Loaded {len(records)} records from {DATA_PATH}")

    data = build_manufacturer_data(records)

    makes = len(data)
    models = sum(len(m) for m in data.values())
    entries = sum(
        len(years) for m in data.values() for years in m.values()
    )
    print(f"Grouped into {makes} makes, {models} models, {entries} year entries")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

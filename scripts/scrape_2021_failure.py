"""
scrape_2021_failure.py

Converts:
  data/2021/failure_by_vehicle_make_model_age_report_2021*.xlsx
to:
  data/2021/2021-Make-Model-Data.json

Output format matches the standard Make-Model-Data JSON used across all years:
  [{ "Make", "Model", "Year", "Total", "Pass", "Pass_pct",
     "Fail", "Fail_pct", "Safety", "Safety_pct", "Lighting", "Lighting_pct",
     "Steering", "Steering_pct", "Braking", "Braking_pct", "Wheels", "Wheels_pct",
     "Engine", "Engine_pct", "Chassis", "Chassis_pct", "SideSlip", "SideSlip_pct",
     "Suspension", "Suspension_pct", "Light", "Light_pct", "Brake", "Brake_pct",
     "Emissions", "Emissions_pct", "Other", "Other_pct", "Incomplete", "Incomplete_pct"
  }, ...]
"""

import json
from pathlib import Path

import openpyxl

ROOT = Path(__file__).parent.parent
INPUT_PATH = next(
    (ROOT / "data" / "2021").glob("failure_by_vehicle_make_model_age_report_*.xlsx")
)
OUTPUT_PATH = ROOT / "data" / "2021" / "2021-Make-Model-Data.json"

# Map xlsx column header → standard JSON key
# The 2021 file uses slightly different names for some categories;
# they are normalised here to match every other year's output.
COLUMN_MAP = {
    "Vehicle Make":                     "Make",
    "Vehicle Model":                    "Model",
    "Year Of Birth":                    "Year",
    "Total":                            "Total",
    "PASS":                             "Pass",
    "PASS %":                           "Pass_pct",
    "FAIL":                             "Fail",
    "FAIL %":                           "Fail_pct",
    # Fail items
    "Vehicle and Safety Equipment":     "Safety",
    "Vehicle and Safety Equipment %":   "Safety_pct",
    "Lighting and Electrical":          "Lighting",
    "Lighting and Electrical %":        "Lighting_pct",
    # 2021 combines Steering + Suspension into one column
    "Steering and Suspension":          "Steering",
    "Steering and Suspension % ":       "Steering_pct",   # note trailing space in source
    "Braking Equipment":                "Braking",
    "Braking Equipment %":              "Braking_pct",
    "Wheels and Tyres":                 "Wheels",
    "Wheels and Tyres %":               "Wheels_pct",
    "Engine Noise and Exhaust":         "Engine",
    "Engine Noise and Exhaust %":       "Engine_pct",
    "Chassis and Body":                 "Chassis",
    "Chassis and Body %":               "Chassis_pct",
    "Side Slip Test":                   "SideSlip",
    "Side Slip Test %":                 "SideSlip_pct",
    "Suspension Test":                  "Suspension",
    "Suspension Test %":                "Suspension_pct",
    "Light test":                       "Light",
    "Light test %":                     "Light_pct",
    "Brake Test":                       "Brake",
    "Brake Test %":                     "Brake_pct",
    "Emmissions":                       "Emissions",      # source typo preserved
    "Emmissions % ":                    "Emissions_pct",  # note trailing space in source
    "OTHER":                            "Other",
    "OTHER %":                          "Other_pct",
    "Incompletable":                    "Incomplete",
    "Incompletable %":                  "Incomplete_pct",
}

# Canonical output key order (matches every other year's JSON)
OUTPUT_KEYS = [
    "Make", "Model", "Year",
    "Total",
    "Pass", "Pass_pct",
    "Fail", "Fail_pct",
    "Safety", "Safety_pct",
    "Lighting", "Lighting_pct",
    "Steering", "Steering_pct",
    "Braking", "Braking_pct",
    "Wheels", "Wheels_pct",
    "Engine", "Engine_pct",
    "Chassis", "Chassis_pct",
    "SideSlip", "SideSlip_pct",
    "Suspension", "Suspension_pct",
    "Light", "Light_pct",
    "Brake", "Brake_pct",
    "Emissions", "Emissions_pct",
    "Other", "Other_pct",
    "Incomplete", "Incomplete_pct",
]

# Keys whose values should be integers
INT_KEYS = {
    "Year", "Total", "Pass", "Fail",
    "Safety", "Lighting", "Steering", "Braking", "Wheels", "Engine",
    "Chassis", "SideSlip", "Suspension", "Light", "Brake", "Emissions",
    "Other", "Incomplete",
}


def load_sheet(path: Path):
    wb = openpyxl.load_workbook(path, data_only=True)
    return wb.active


def find_header_row(rows: list) -> tuple[int, dict[int, str]]:
    """
    Locate the row that contains 'Vehicle Make' and return
    (row_index, {col_index: standard_key}).
    """
    for row_idx, row in enumerate(rows):
        if row and row[0] == "Vehicle Make":
            col_map = {}
            for col_idx, cell_val in enumerate(row):
                if cell_val in COLUMN_MAP:
                    col_map[col_idx] = COLUMN_MAP[cell_val]
            return row_idx, col_map
    raise ValueError("Header row with 'Vehicle Make' not found in worksheet")


def scrape(path: Path) -> list[dict]:
    ws = load_sheet(path)
    rows = list(ws.iter_rows(values_only=True))
    header_row_idx, col_map = find_header_row(rows)

    records = []
    for row in rows[header_row_idx + 1:]:
        # Skip completely empty rows or rows where Make is blank
        if not row or row[0] is None:
            continue

        record: dict = {}
        for col_idx, std_key in col_map.items():
            val = row[col_idx] if col_idx < len(row) else None
            if val is None:
                val = 0
            if std_key in ("Make", "Model"):
                record[std_key] = str(val).strip().upper()
            elif std_key in INT_KEYS:
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    val = 0
                record[std_key] = val
            else:
                # Percentage — round to 1 dp
                try:
                    val = round(float(val), 1)
                except (ValueError, TypeError):
                    val = 0.0
                record[std_key] = val

        # Ensure all output keys exist (fill missing with 0)
        for key in OUTPUT_KEYS:
            record.setdefault(key, 0)

        # Order keys canonically
        records.append({k: record[k] for k in OUTPUT_KEYS})

    return records


def main() -> None:
    print(f"Reading: {INPUT_PATH.relative_to(ROOT)}")
    records = scrape(INPUT_PATH)
    print(f"Parsed {len(records)} records")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Written: {OUTPUT_PATH.relative_to(ROOT)}")

    # Quick sanity check
    sample = records[0]
    print(f"\nFirst record: {sample}")


if __name__ == "__main__":
    main()

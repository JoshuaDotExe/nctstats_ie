"""
scrape_xlsx_make_model.py

Converts all known Make-Model-Data xlsx files (2015, 2017, 2020–2024)
into the standard Make-Model-Data JSON format used across all years.

Output per year:
  data/<year>/<year>-Make-Model-Data.json

Standard output schema:
  [{ "Make", "Model", "Year",
     "Total", "Pass", "Pass_pct", "Fail", "Fail_pct",
     "Safety", "Safety_pct", "Lighting", "Lighting_pct",
     "Steering", "Steering_pct", "Braking", "Braking_pct",
     "Wheels", "Wheels_pct", "Engine", "Engine_pct",
     "Chassis", "Chassis_pct", "SideSlip", "SideSlip_pct",
     "Suspension", "Suspension_pct", "Light", "Light_pct",
     "Brake", "Brake_pct", "Emissions", "Emissions_pct",
     "Other", "Other_pct", "Incomplete", "Incomplete_pct"
  }, ...]

Column name variations across years are handled by normalising header
strings before lookup (strip whitespace, lowercase, collapse punctuation).
"""

import json
import re
from pathlib import Path

import openpyxl

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

# ── Files to process ──────────────────────────────────────────────────────────
TARGETS: list[tuple[str, Path]] = [
    ("2015", DATA_DIR / "2015" / "2015-Make-Model-Data-(xls).xlsx"),
    ("2017", DATA_DIR / "2017" / "2017-Make-Model-Data-(xls).xlsx"),
    ("2020", DATA_DIR / "2020" / "Make-and-Model-Data---2020.xlsx"),
    ("2022", DATA_DIR / "2022" / "2022-Make-and-Model-Data.xlsx"),
    ("2023", DATA_DIR / "2023" / "2023-Make-and-Model-Data.xlsx"),
    ("2024", DATA_DIR / "2024" / next(
        (DATA_DIR / "2024").glob("2024-make-and-model-data*.xlsx")
    ).name),
]

# ── Column mapping (normalised key → standard JSON key) ───────────────────────
# Keys are produced by _norm() below: lowercase, strip, collapse spaces/punct.
# This handles all spelling/spacing/punctuation variants seen across years.
COLUMN_MAP: dict[str, str] = {
    # Identity columns
    "vehiclemake":                      "Make",
    "vehicle make":                     "Make",
    "vehiclemodel":                     "Model",
    "vehicle model":                    "Model",
    "yearofbirth":                      "Year",
    "year of birth":                    "Year",
    # Totals
    "total":                            "Total",
    "pass":                             "Pass",
    "pass %":                           "Pass_pct",
    "fail":                             "Fail",
    "fail %":                           "Fail_pct",
    # Fail categories (inspection items)
    "vehicle and safety equipment":     "Safety",
    "vehicle and safety equipment %":   "Safety_pct",
    "lighting and electrical":          "Lighting",
    "lighting and electrical %":        "Lighting_pct",
    "steering and suspension":          "Steering",
    "steering and suspension %":        "Steering_pct",
    "braking equipment":                "Braking",
    "braking equipment %":              "Braking_pct",
    "wheels and tyres":                 "Wheels",
    "wheels and tyres %":               "Wheels_pct",
    # "Engine, Noise and Exhaust" (2015/17) vs "Engine Noise and Exhaust" (2020+)
    # — comma removed by _norm()
    "engine noise and exhaust":         "Engine",
    "engine noise and exhaust %":       "Engine_pct",
    "chassis and body":                 "Chassis",
    "chassis and body %":               "Chassis_pct",
    # Test result columns
    "side slip test":                   "SideSlip",
    "side slip test %":                 "SideSlip_pct",
    "suspension test":                  "Suspension",
    "suspension test %":                "Suspension_pct",
    "light test":                       "Light",
    "light test %":                     "Light_pct",
    "brake test":                       "Brake",
    "brake test %":                     "Brake_pct",
    # "Emmissions" is a consistent typo in the source files
    "emmissions":                       "Emissions",
    "emmissions %":                     "Emissions_pct",
    "other":                            "Other",
    "other %":                          "Other_pct",
    "incompletable":                    "Incomplete",
    "incompletable %":                  "Incomplete_pct",
}

# Canonical output key order
OUTPUT_KEYS: list[str] = [
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

INT_KEYS: set[str] = {
    "Year", "Total", "Pass", "Fail",
    "Safety", "Lighting", "Steering", "Braking", "Wheels", "Engine",
    "Chassis", "SideSlip", "Suspension", "Light", "Brake", "Emissions",
    "Other", "Incomplete",
}


def _norm(s: str) -> str:
    """Normalise a header string for lookup: lowercase, strip, remove commas."""
    return re.sub(r",", "", str(s)).strip().lower()


def build_col_map(header_row: tuple) -> dict[int, str]:
    """Map column index → standard JSON key for a given header row."""
    col_map: dict[int, str] = {}
    for col_idx, cell in enumerate(header_row):
        if cell is None:
            continue
        std_key = COLUMN_MAP.get(_norm(cell))
        if std_key:
            col_map[col_idx] = std_key
    return col_map


def find_header_row(rows: list[tuple]) -> tuple[int, dict[int, str]]:
    """
    Find the row whose first non-None cell normalises to 'vehiclemake' or
    'vehicle make', and return (row_index, col_map).
    """
    for row_idx, row in enumerate(rows):
        if row and row[0] is not None and _norm(row[0]) in ("vehiclemake", "vehicle make"):
            col_map = build_col_map(row)
            return row_idx, col_map
    raise ValueError("Could not find header row starting with 'Vehicle Make'")


def parse_rows(rows: list[tuple], header_idx: int, col_map: dict[int, str]) -> list[dict]:
    records: list[dict] = []

    for row in rows[header_idx + 1:]:
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
                    record[std_key] = int(val)
                except (ValueError, TypeError):
                    record[std_key] = 0
            else:
                try:
                    record[std_key] = round(float(val), 1)
                except (ValueError, TypeError):
                    record[std_key] = 0.0

        # Fill any missing output keys with zero
        for key in OUTPUT_KEYS:
            record.setdefault(key, 0)

        records.append({k: record[k] for k in OUTPUT_KEYS})

    return records


def scrape_file(year: str, path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    header_idx, col_map = find_header_row(rows)

    unmapped = [
        repr(cell) for cell in rows[header_idx]
        if cell is not None and COLUMN_MAP.get(_norm(cell)) is None
    ]
    if unmapped:
        print(f"  ⚠  {year}: unrecognised columns (will be ignored): {unmapped}")

    return parse_rows(rows, header_idx, col_map)


def main() -> None:
    for year, path in TARGETS:
        if not path.exists():
            print(f"⏭  {year}: file not found — {path}")
            continue

        print(f"Processing {year}…  ({path.relative_to(ROOT)})")
        try:
            records = scrape_file(year, path)
        except Exception as e:
            print(f"  ✗  {year}: {e}")
            continue

        out_path = DATA_DIR / year / f"{year}-Make-Model-Data.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

        print(f"  ✓  {len(records):,} records → {out_path.relative_to(ROOT)}")

    print("\nDone.")


if __name__ == "__main__":
    main()

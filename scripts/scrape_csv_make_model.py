"""
scrape_csv_make_model.py

Converts Make-Model-Data CSV files (2018, 2019) into the standard
Make-Model-Data JSON format used across all years.

Output:
  data/2018/2018-Make-Model-Data.json
  data/2019/2019-Make-Model-Data.json

The CSV files share the same column layout as the xlsx files processed by
scrape_xlsx_make_model.py, so the same COLUMN_MAP / OUTPUT_KEYS are used.
All CSV values arrive as strings and are cast accordingly.
Encoding is latin-1 (the source files contain Windows-1252 smart quotes).
"""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

TARGETS: list[tuple[str, Path]] = [
    ("2018", DATA_DIR / "2018" / "2018-Make-Model-Data-(csv).csv"),
    ("2019", DATA_DIR / "2019" / "2019-Make-Model-Data-(xls).csv"),
]

# ── Column mapping (normalised header → standard JSON key) ────────────────────
# Normalisation: lowercase, strip whitespace, remove commas.
# Identical to scrape_xlsx_make_model.py — all column names are the same.
COLUMN_MAP: dict[str, str] = {
    "vehicle make":                     "Make",
    "vehicle model":                    "Model",
    "year of birth":                    "Year",
    "total":                            "Total",
    "pass":                             "Pass",
    "pass %":                           "Pass_pct",
    "fail":                             "Fail",
    "fail %":                           "Fail_pct",
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
    "engine noise and exhaust":         "Engine",
    "engine noise and exhaust %":       "Engine_pct",
    "chassis and body":                 "Chassis",
    "chassis and body %":               "Chassis_pct",
    "side slip test":                   "SideSlip",
    "side slip test %":                 "SideSlip_pct",
    "suspension test":                  "Suspension",
    "suspension test %":                "Suspension_pct",
    "light test":                       "Light",
    "light test %":                     "Light_pct",
    "brake test":                       "Brake",
    "brake test %":                     "Brake_pct",
    "emmissions":                       "Emissions",
    "emmissions %":                     "Emissions_pct",
    "other":                            "Other",
    "other %":                          "Other_pct",
    "incompletable":                    "Incomplete",
    "incompletable %":                  "Incomplete_pct",
}

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
    """Lowercase, strip, remove commas."""
    return re.sub(r",", "", str(s)).strip().lower()


def build_col_map(header_row: list[str]) -> dict[int, str]:
    col_map: dict[int, str] = {}
    for col_idx, cell in enumerate(header_row):
        std_key = COLUMN_MAP.get(_norm(cell))
        if std_key:
            col_map[col_idx] = std_key
    return col_map


def find_header_row(rows: list[list[str]]) -> tuple[int, dict[int, str]]:
    """Find the row whose first cell normalises to 'vehicle make'."""
    for row_idx, row in enumerate(rows):
        if row and _norm(row[0]) == "vehicle make":
            return row_idx, build_col_map(row)
    raise ValueError("Could not find header row starting with 'Vehicle Make'")


def scrape_file(year: str, path: Path) -> list[dict]:
    with open(path, encoding="latin-1") as f:
        rows = list(csv.reader(f))

    header_idx, col_map = find_header_row(rows)

    unmapped = [
        repr(cell) for cell in rows[header_idx]
        if cell.strip() and COLUMN_MAP.get(_norm(cell)) is None
        and cell.strip() not in ("", "Fail Items")
    ]
    if unmapped:
        print(f"  ⚠  {year}: unrecognised columns (ignored): {unmapped}")

    records: list[dict] = []
    for row in rows[header_idx + 1:]:
        # Skip empty rows or rows where Make is blank
        if not row or not row[0].strip():
            continue

        record: dict = {}
        for col_idx, std_key in col_map.items():
            raw = row[col_idx].strip() if col_idx < len(row) else ""

            if std_key in ("Make", "Model"):
                record[std_key] = raw.upper()
            elif std_key in INT_KEYS:
                try:
                    record[std_key] = int(float(raw)) if raw else 0
                except (ValueError, TypeError):
                    record[std_key] = 0
            else:
                try:
                    record[std_key] = round(float(raw), 1) if raw else 0.0
                except (ValueError, TypeError):
                    record[std_key] = 0.0

        # Fill any missing output keys with zero
        for key in OUTPUT_KEYS:
            record.setdefault(key, 0)

        records.append({k: record[k] for k in OUTPUT_KEYS})

    return records


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

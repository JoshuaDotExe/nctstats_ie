import pdfplumber
import json
import re
import sys
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_console)

_file_handler = None


def _add_file_log(log_path: str):
    """Add a file handler so all log output is also written to disk."""
    global _file_handler
    if _file_handler:
        logger.removeHandler(_file_handler)
    _file_handler = logging.FileHandler(log_path, mode="w")
    _file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(_file_handler)

# Column mapping from PDF headers to short field names
COLUMNS = [
    "Make",
    "Model",
    "Year",
    "Total",
    "Pass",
    "Pass_pct",
    "Fail",
    "Fail_pct",
    "Safety",
    "Safety_pct",
    "Lighting",
    "Lighting_pct",
    "Steering",
    "Steering_pct",
    "Braking",
    "Braking_pct",
    "Wheels",
    "Wheels_pct",
    "Engine",
    "Engine_pct",
    "Chassis",
    "Chassis_pct",
    "SideSlip",
    "SideSlip_pct",
    "Suspension",
    "Suspension_pct",
    "Light",
    "Light_pct",
    "Brake",
    "Brake_pct",
    "Emissions",
    "Emissions_pct",
    "Other",
    "Other_pct",
    "Incomplete",
    "Incomplete_pct",
]

# Numeric fields (everything except Make, Model)
NUMERIC_FIELDS = COLUMNS[2:]


def parse_numeric(value: str) -> int | float | None:
    """Convert a string value to int or float. Returns None if unparseable."""
    if value is None or value.strip() == "":
        return 0
    value = value.strip().replace(",", "")
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return None


# Regex: find a 4-digit year (1900-2099) that is either at the very end
# or followed only by non-digit remnants (like a stray letter from pdfplumber).
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def _repair_model_year(raw_model: str, raw_year: str) -> tuple[str, int | None]:
    """Try to recover Model and Year from the concatenated overflow text.

    pdfplumber merges long model names into the Year column, e.g.:
        Model = "A4 1.9 TDI SE 113"   Year = "BHP 05DR2008"
    Combined = "A4 1.9 TDI SE 113BHP 05DR2008"  →  Model, 2008
    """
    combined = (raw_model + raw_year).strip()

    # Find ALL 4-digit year candidates; the real year is normally the last one.
    matches = list(_YEAR_RE.finditer(combined))
    if not matches:
        return raw_model.strip(), None

    best = matches[-1]
    year = int(best.group())

    # Everything before the year becomes the model name.
    model = combined[: best.start()].strip()

    # Clean up trailing junk like stray digits that were part of "5DR" etc.
    # e.g. "A4 1.9 TDI SE 113BHP 05DR" → keep as-is, it's descriptive.
    return model, year


def scrape_pdf(pdf_path: str) -> list[dict]:
    """Extract vehicle NCT data from a PDF file."""
    records = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        logger.info(f"PDF has {total_pages} pages")

        for page_num, page in enumerate(pdf.pages):
            logger.info(f"Processing page {page_num + 1}/{total_pages}...")
            tables = page.extract_tables()
            if not tables:
                logger.warning(f"  No tables found on page {page_num + 1}")
                continue

            logger.info(f"  Found {len(tables)} table(s)")

            for table in tables:
                rows_added = 0
                rows_malformed = 0
                for row in table:
                    # Skip header rows and empty rows
                    if row is None or len(row) < len(COLUMNS):
                        continue
                    if row[0] is None or row[0] in ("VehicleMake", ""):
                        continue

                    record = {}
                    malformed = False
                    for i, col_name in enumerate(COLUMNS):
                        value = row[i] if i < len(row) else None
                        if col_name in NUMERIC_FIELDS:
                            parsed = parse_numeric(value)
                            if parsed is None:
                                malformed = True
                                record[col_name] = 0
                            else:
                                record[col_name] = parsed
                        else:
                            record[col_name] = value.strip() if value else ""

                    if malformed:
                        rows_malformed += 1
                        raw_make = row[0] if row[0] else ""
                        raw_model = row[1] if row[1] else ""
                        raw_year = row[2] if row[2] else ""
                        logger.warning(
                            f"  Malformed row on page {page_num + 1} | "
                            f"Make: {raw_make}, Model: {raw_model}, Year: {raw_year}"
                        )
                        repaired_model, repaired_year = _repair_model_year(
                            raw_model, raw_year
                        )
                        if repaired_year is not None:
                            record["Model"] = repaired_model
                            record["Year"] = repaired_year
                            logger.info(
                                f"    -> Repaired: Model: {repaired_model}, Year: {repaired_year}"
                            )
                        else:
                            combined = (raw_model + raw_year).strip()
                            default_model = raw_model.strip().split()[0] if raw_model.strip() else ""
                            # Try to guess a year - look for 1 9 x x or 2 0 x x
                            # with possible junk chars between the digits
                            _LOOSE_YEAR_RE = re.compile(
                                r"(1)\D{0,2}(9)\D{0,2}(\d)\D{0,2}(\d)"
                                r"|"
                                r"(2)\D{0,2}(0)\D{0,2}(\d)\D{0,2}(\d)"
                            )
                            default_year = ""
                            loose_match = _LOOSE_YEAR_RE.search(raw_year)
                            if not loose_match:
                                loose_match = _LOOSE_YEAR_RE.search(combined)
                            if loose_match:
                                digits = [g for g in loose_match.groups() if g is not None]
                                default_year = "".join(digits)
                            print(
                                f"\n  Could not parse year automatically."
                                f"\n  Make:  {raw_make}"
                                f"\n  Raw:   {combined}"
                            )
                            manual_model = input(f"  Enter Model [{default_model}]: ").strip()
                            if not manual_model:
                                manual_model = default_model
                            year_prompt = f"  Enter Year [{default_year}]: " if default_year else "  Enter Year (or press Enter to mark as !!!!!): "
                            manual_year = input(year_prompt).strip()
                            if not manual_year:
                                manual_year = default_year
                            if manual_model and manual_year:
                                record["Model"] = manual_model
                                try:
                                    record["Year"] = int(manual_year)
                                except ValueError:
                                    record["Year"] = manual_year
                                logger.info(
                                    f"    -> Manual fix: Model: {record['Model']}, Year: {record['Year']}"
                                )
                            else:
                                record["Model"] = "!!!!!"
                                record["Year"] = "!!!!!"
                                logger.warning(
                                    f"    -> Skipped (marked with !!!!!)"
                                )

                    records.append(record)
                    rows_added += 1

                status = f"  Extracted {rows_added} records from table"
                if rows_malformed:
                    status += f" ({rows_malformed} malformed, marked with !!!!!)"
                logger.info(status)

        logger.info(f"Total records extracted: {len(records)}")

    return records


def main():
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = os.path.join(
            os.path.dirname(__file__),
            "data",
            "2016",
            "2016-Make-Model-Data-(pdf).pdf",
        )

    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        sys.exit(1)

    # Set up file logging next to the output JSON
    log_path = os.path.splitext(pdf_path)[0] + ".log"
    _add_file_log(log_path)
    logger.info(f"Logging to: {log_path}")

    logger.info(f"Scraping: {pdf_path}")
    records = scrape_pdf(pdf_path)
    logger.info(f"Extracted {len(records)} records")

    # Output to JSON
    output_path = os.path.splitext(pdf_path)[0] + ".json"
    with open(output_path, "w") as f:
        json.dump(records, f, indent=2)

    logger.info(f"Saved to: {output_path}")

    # Print a sample
    if records:
        logger.info("Sample record:")
        print(json.dumps(records[0], indent=2))


if __name__ == "__main__":
    main()

"""
Optimise JSON attribute key lengths for production use.

Reads a Manufacturer-Make-Year JSON file with long descriptive keys
and writes a minified version with short keys for smaller file size.

Usage:
    python key_optimiser.py                          # defaults to 2016 data
    python key_optimiser.py data/2017/2017-Manufacturer-Make-Year.json
"""

import argparse
import json
import sys
from pathlib import Path

# Long key → Short key mapping (must stay in sync with README.md)
KEY_MAP = {
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

# Reverse mapping for expanding short keys back to long
REVERSE_KEY_MAP = {v: k for k, v in KEY_MAP.items()}

DEFAULT_INPUT = Path("data/2016/2016-Manufacturer-Make-Year.json")


def shorten_keys(data: dict) -> dict:
    """Replace long attribute keys with short equivalents."""
    optimised = {}
    for make, models in data.items():
        optimised[make] = {}
        for model, years in models.items():
            optimised[make][model] = {}
            for year, values in years.items():
                optimised[make][model][year] = {
                    KEY_MAP[k]: v for k, v in values.items()
                }
    return optimised


def expand_keys(data: dict) -> dict:
    """Replace short attribute keys with long equivalents (reverse operation)."""
    expanded = {}
    for make, models in data.items():
        expanded[make] = {}
        for model, years in models.items():
            expanded[make][model] = {}
            for year, values in years.items():
                expanded[make][model][year] = {
                    REVERSE_KEY_MAP[k]: v for k, v in values.items()
                }
    return expanded


def detect_key_format(data: dict) -> str:
    """Detect whether the file uses long or short keys.

    Returns 'long', 'short', or 'empty'.
    """
    for models in data.values():
        for years in models.values():
            for values in years.values():
                first_key = next(iter(values))
                if first_key in KEY_MAP:
                    return "long"
                if first_key in REVERSE_KEY_MAP:
                    return "short"
    return "empty"


def build_output_path(input_path: Path, direction: str) -> Path:
    """Generate the output filename based on direction."""
    stem = input_path.stem
    if direction == "shorten":
        return input_path.with_name(f"{stem}.min.json")
    else:  # expand
        # Remove .min suffix if present
        if stem.endswith(".min"):
            stem = stem[:-4]
        return input_path.with_name(f"{stem}.json")


def main():
    parser = argparse.ArgumentParser(
        description="Optimise JSON attribute key lengths for production use."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input JSON file (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output file path (default: auto-generated based on direction)",
    )
    parser.add_argument(
        "--expand",
        action="store_true",
        help="Reverse: expand short keys back to long keys",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the output instead of minifying",
    )
    args = parser.parse_args()

    # --- Load ---
    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input) as f:
        data = json.load(f)

    key_format = detect_key_format(data)
    direction = "expand" if args.expand else "shorten"

    # Sanity checks
    if direction == "shorten" and key_format == "short":
        print("File already uses short keys. Nothing to do.", file=sys.stderr)
        sys.exit(0)
    if direction == "expand" and key_format == "long":
        print("File already uses long keys. Nothing to do.", file=sys.stderr)
        sys.exit(0)

    # --- Transform ---
    if direction == "shorten":
        result = shorten_keys(data)
    else:
        result = expand_keys(data)

    # --- Write ---
    output_path = args.output or build_output_path(args.input, direction)

    if args.pretty:
        json_str = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        json_str = json.dumps(result, separators=(",", ":"), ensure_ascii=False)

    with open(output_path, "w") as f:
        f.write(json_str)
        f.write("\n")

    # --- Report ---
    input_size = args.input.stat().st_size
    output_size = output_path.stat().st_size
    savings = input_size - output_size
    pct = (savings / input_size * 100) if input_size else 0

    print(f"Input:   {args.input}  ({input_size:,} bytes)")
    print(f"Output:  {output_path}  ({output_size:,} bytes)")
    print(f"Savings: {savings:,} bytes ({pct:.1f}%)")
    if direction == "shorten":
        print(f"Keys:    long → short")
    else:
        print(f"Keys:    short → long")


if __name__ == "__main__":
    main()

"""
build_model_lookup.py

Scans all year JSON files, extracts every unique (Make, Model) combination,
groups variant model names under a detected canonical core model, and writes:

  data/model_lookup.json  — { "MAKE|RAW MODEL": "CORE MODEL", ... }

After running, review and manually correct the output, then run
apply_core_model.py to stamp every JSON record with a "core_model" field.
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_PATH = DATA_DIR / "model_lookup.json"

# JSON files to scan
JSON_FILES = [DATA_DIR / "2016" / "2016-Make-Model-Data-(pdf)_uneditied.json"]

# ── Normalisation helpers ──────────────────────────────────────────────────────

# Common trim / spec tokens that appear after the base model name.
# Order matters — longer tokens first to avoid partial matches.
TRIM_TOKENS = [
    # Body styles
    r"\b\d+DR\b", r"\bHATCH\b", r"\bSALOON\b", r"\bESTATE\b", r"\bCOUPE\b",
    r"\bCABRIO\b", r"\bCONVERTIBLE\b", r"\bTOURER\b", r"\bSPORT\b", r"\bSPORTBACK\b",
    r"\bAVANT\b",
    # Fuel / transmission descriptors
    r"\b\d+\.\d+\s*[A-Z]*\s*\d*\s*(?:BHP|PS|CV|KW)\b",  # e.g. 1.6 TDI 115BHP
    r"\b\d+\.\d+[A-Z0-9]*\b",                             # e.g. 1.9D, 2.0TDCI
    r"\bTDI\b", r"\bTDCI\b", r"\bCDTI\b", r"\bCDI\b", r"\bFSI\b", r"\bTSI\b",
    r"\bGTI\b", r"\bGTD\b", r"\bGTE\b", r"\bSRi\b", r"\bSRI\b",
    r"\bTURBO\b", r"\bHYBRID\b", r"\bPHEV\b", r"\bEV\b", r"\bELECTRIC\b",
    r"\b4WD\b", r"\b4X4\b", r"\bAWD\b", r"\bFWD\b", r"\bRWD\b",
    # Common trim level abbreviations
    r"\bLX\b", r"\bGHIA\b", r"\bZETEC\b", r"\bTITANIUM\b", r"\bST\b", r"\bRS\b",
    r"\bSE\b", r"\bSEL\b", r"\bSI\b", r"\bEX\b", r"\bLTZ\b", r"\bXLT\b",
    r"\bACTIVE\b", r"\bAMBIENTE\b", r"\bTRENDLINE\b", r"\bCOMFORTLINE\b",
    r"\bHIGHLINE\b", r"\bCOMFORTLINE\b", r"\bELEGANCE\b", r"\bAVANTGARDE\b",
    r"\bC[/\-]?LINE\b", r"\bCOMFORT\b", r"\bLUXURY\b",
    # Speed / gear refs
    r"\b\d+SP\b", r"\b\d+V\b",
    # Stray numbers / codes at the end
    r"\b\d{2,4}\b",
    # LHD marker
    r"\bLHD\b",
]

TRIM_RE = re.compile("|".join(TRIM_TOKENS), re.IGNORECASE)


def derive_core(model: str) -> str:
    """
    Strip spec/trim tokens from a raw model string to get the core model name.
    E.g. 'GOLF 1.9 GT TDI 130BHP 5DR' → 'GOLF GT'
         'FIESTA 1.25 ZETEC 82PS 3DR'  → 'FIESTA'
         'FOCUS C-MAX 1.6TDCI ZETEC 5DR' → 'FOCUS C-MAX'
    """
    result = TRIM_RE.sub("", model)
    # Collapse multiple spaces
    result = re.sub(r"\s{2,}", " ", result).strip()
    # Remove trailing punctuation
    result = result.rstrip(".,/-").strip()
    return result if result else model


def load_all_models() -> dict[str, set[str]]:
    """
    Returns { make: {raw_model, ...} } gathered from every JSON file.
    """
    make_models: dict[str, set[str]] = defaultdict(set)
    for path in JSON_FILES:
        try:
            with open(path, encoding="utf-8") as f:
                records = json.load(f)
        except Exception as e:
            print(f"  ⚠  Skipping {path.name}: {e}", file=sys.stderr)
            continue
        for r in records:
            make = str(r.get("Make", "")).strip().upper()
            model = str(r.get("Model", "")).strip().upper()
            if make and model:
                make_models[make].add(model)
    return make_models


def build_lookup(make_models: dict[str, set[str]]) -> dict[str, str]:
    """
    For each (make, raw_model), compute its core_model.

    Key format in the output dict: "MAKE|RAW MODEL"
    Value: core model string
    """
    lookup: dict[str, str] = {}

    for make, models in sorted(make_models.items()):
        cores_for_make: dict[str, str] = {}  # raw → core

        for raw in sorted(models):
            core = derive_core(raw)
            cores_for_make[raw] = core

        # ── Refinement pass ──────────────────────────────────────────────────
        # If the derived core is itself a known raw model name for this make,
        # that's perfect — it stays.  If not, check whether any raw model is
        # a *prefix* of the derived core and use the shortest such prefix as
        # the canonical name.
        raw_set = set(models)
        for raw, core in cores_for_make.items():
            # If the core exactly matches a clean raw model name, keep it
            if core in raw_set:
                lookup[f"{make}|{raw}"] = core
                continue

            # Otherwise find the longest raw model name that is a prefix of `core`
            candidates = [m for m in raw_set if core.startswith(m) and m != raw]
            if candidates:
                best = max(candidates, key=len)
                lookup[f"{make}|{raw}"] = best
            else:
                lookup[f"{make}|{raw}"] = core

    return lookup


def main() -> None:
    print(f"Scanning {len(JSON_FILES)} JSON file(s)…")
    make_models = load_all_models()
    total_models = sum(len(v) for v in make_models.values())
    print(f"Found {total_models} unique (Make, Model) combinations across {len(make_models)} makes.")

    lookup = build_lookup(make_models)

    # ── Pretty-print grouped by make for easy review ───────────────────────
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    for key, core in sorted(lookup.items()):
        make, raw = key.split("|", 1)
        grouped[make][raw] = core

    output: dict[str, dict[str, str]] = dict(sorted(grouped.items()))

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅  Lookup written to {OUTPUT_PATH}")
    print("   Structure: { MAKE: { RAW_MODEL: CORE_MODEL } }")
    print("\nNext steps:")
    print("  1. Review / edit data/model_lookup.json to fix any mistakes.")
    print("  2. Run  scripts/apply_core_model.py  to stamp 'core_model' onto every record.")

    # ── Quick stats ────────────────────────────────────────────────────────
    variants = sum(
        1 for make_dict in output.values()
        for raw, core in make_dict.items()
        if raw != core
    )
    print(f"\n  {len(lookup)} total entries, {variants} are variant→core mappings.")


if __name__ == "__main__":
    main()

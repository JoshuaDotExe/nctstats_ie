"""
apply_core_model.py

Reads data/model_lookup.json (produced by build_model_lookup.py, then
manually reviewed) and stamps a "core_model" field onto every record in
every year JSON file.

Records whose (Make, Model) key is missing from the lookup fall back to
their raw Model value, with a warning printed to stderr.

Usage:
    python scripts/apply_core_model.py              # updates files in-place
    python scripts/apply_core_model.py --dry-run    # prints stats only
"""

import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
LOOKUP_PATH = DATA_DIR / "model_lookup.json"
JSON_FILES = sorted(DATA_DIR.glob("*/*.json"))


def load_lookup() -> dict[str, dict[str, str]]:
    with open(LOOKUP_PATH, encoding="utf-8") as f:
        return json.load(f)


def apply(dry_run: bool) -> None:
    lookup = load_lookup()
    missing: dict[str, set[str]] = defaultdict(set)
    total_records = 0
    total_stamped = 0

    for path in JSON_FILES:
        # Skip the lookup file itself if it ends up in a glob
        if path == LOOKUP_PATH:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                records: list[dict] = json.load(f)
        except Exception as e:
            print(f"  ⚠  Skipping {path.name}: {e}", file=sys.stderr)
            continue

        updated = []
        for r in records:
            make = str(r.get("Make", "")).strip().upper()
            model = str(r.get("Model", "")).strip().upper()
            key = f"{make}|{model}"

            make_dict = lookup.get(make, {})
            core = make_dict.get(model)

            if core is None:
                missing[make].add(model)
                core = model  # fallback: use raw model as core

            r["core_model"] = core
            updated.append(r)
            total_records += 1
            if core != model:
                total_stamped += 1

        if not dry_run:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(updated, f, indent=2, ensure_ascii=False)
            print(f"  ✅  {path.relative_to(ROOT)}  ({len(updated)} records)")

    print(f"\nTotal records processed : {total_records}")
    print(f"Records mapped to a different core_model : {total_stamped}")

    if missing:
        print(f"\n⚠  {sum(len(v) for v in missing.values())} (Make, Model) pairs were NOT in the lookup.")
        print("   They received core_model = their raw Model value.")
        print("   Add them to data/model_lookup.json and re-run if needed.")
        for make in sorted(missing):
            for m in sorted(missing[make]):
                print(f"     {make} | {m}")

    if dry_run:
        print("\n(dry-run — no files written)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    apply(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

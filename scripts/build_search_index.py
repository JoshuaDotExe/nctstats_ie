"""
build_search_index.py

Scans all *-Make-Model-Data-aggregated.json files and writes a compact
search index to app/public/search_index.json.

Index shape:
  {
    "makes": ["ALFA ROMEO", "BMW", "FORD", ...],
    "models": {
      "FORD": ["FIESTA", "FOCUS", "GALAXY", ...],
      ...
    }
  }

Makes and models are sorted alphabetically.

Usage:
    python scripts/build_search_index.py
"""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_PATH = ROOT / "app" / "public" / "search_index.json"

def main() -> None:
    models_by_make: dict[str, set[str]] = defaultdict(set)

    files = sorted(DATA_DIR.glob("*/*-Make-Model-Data-aggregated.json"))
    if not files:
        print("No aggregated files found. Run aggregate_by_core_model.py first.")
        return

    for path in files:
        with open(path, encoding="utf-8") as f:
            records = json.load(f)
        for r in records:
            make = str(r.get("Make", "")).strip().upper()
            model = str(r.get("Model", "")).strip().upper()
            if make and model:
                models_by_make[make].add(model)

    index = {
        "makes": sorted(models_by_make.keys()),
        "models": {make: sorted(models) for make, models in sorted(models_by_make.items())},
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, separators=(",", ":"), ensure_ascii=False)

    total_models = sum(len(v) for v in index["models"].values())
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")
    print(f"  {len(index['makes'])} makes, {total_models} total make/model pairs")

if __name__ == "__main__":
    main()

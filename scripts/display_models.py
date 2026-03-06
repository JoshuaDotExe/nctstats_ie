import json
import os
from collections import defaultdict

DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "data",
    "2016",
    "2016-Make-Model-Data-(pdf).json",
)

with open(DATA_PATH) as f:
    records = json.load(f)

# Group unique models by make
makes = defaultdict(set)
for r in records:
    make = r.get("Make", "").strip()
    model = r.get("Model", "").strip()
    if make and model:
        makes[make].add(model)

for make in sorted(makes):
    models = sorted(makes[make])
    print(f"\n{'=' * 60}")
    print(f"  {make}  ({len(models)} models)")
    print(f"{'=' * 60}")
    for m in models:
        print(f"  - {m}")
    input("\n  Press Enter for next brand...")

# nctstats_ie
nctstats.ie webpage

---

## Data Standards

### Make-Model-Data JSON Format

All per-year Make-Model-Data files live at:
```
data/<year>/<year>-Make-Model-Data.json
```

Each file is a JSON array of records with the following fixed key order and types:

| Key | Type | Description |
|-----|------|-------------|
| `Make` | `string` | Vehicle make, uppercase (e.g. `"FORD"`) |
| `Model` | `string` | Vehicle model, uppercase (e.g. `"FOCUS"`) |
| `Year` | `int` | Vehicle year of birth (e.g. `2008`) |
| `Total` | `int` | Total number of initial tests |
| `Pass` | `int` | Number of passes |
| `Pass_pct` | `float` | Pass as % of Total, 1 d.p. |
| `Fail` | `int` | Number of fails |
| `Fail_pct` | `float` | Fail as % of Total, 1 d.p. |
| `Safety` | `int` | Safety equipment fail count |
| `Safety_pct` | `float` | Safety as % of Total, 1 d.p. |
| `Lighting` | `int` | Lighting & electrical fail count |
| `Lighting_pct` | `float` | |
| `Steering` | `int` | Steering & suspension fail count |
| `Steering_pct` | `float` | |
| `Braking` | `int` | Braking equipment fail count |
| `Braking_pct` | `float` | |
| `Wheels` | `int` | Wheels & tyres fail count |
| `Wheels_pct` | `float` | |
| `Engine` | `int` | Engine, noise & exhaust fail count |
| `Engine_pct` | `float` | |
| `Chassis` | `int` | Chassis & body fail count |
| `Chassis_pct` | `float` | |
| `SideSlip` | `int` | Side slip test fail count |
| `SideSlip_pct` | `float` | |
| `Suspension` | `int` | Suspension test fail count |
| `Suspension_pct` | `float` | |
| `Light` | `int` | Light test fail count |
| `Light_pct` | `float` | |
| `Brake` | `int` | Brake test fail count |
| `Brake_pct` | `float` | |
| `Emissions` | `int` | Emissions fail count |
| `Emissions_pct` | `float` | |
| `Other` | `int` | Other fail count |
| `Other_pct` | `float` | |
| `Incomplete` | `int` | Incomplete test count |
| `Incomplete_pct` | `float` | |

**Percentage rule:** All `_pct` fields are recalculated from raw counts as
`round(count / Total * 100, 1)`, yielding `0.0` when `Total = 0`. Source-file
percentages are discarded to eliminate ±0.1 rounding drift between years.

### Years Available

| Year | Source format | Script |
|------|--------------|--------|
| 2013 | PDF → JSON (manual) | — |
| 2014 | PDF → JSON (manual) | — |
| 2015 | `.xlsx` | `scripts/scrape_xlsx_make_model.py` |
| 2016 | PDF → JSON (manual) | — |
| 2017 | `.xlsx` | `scripts/scrape_xlsx_make_model.py` |
| 2018 | `.csv` | `scripts/scrape_csv_make_model.py` |
| 2019 | `.csv` | `scripts/scrape_csv_make_model.py` |
| 2020 | `.xlsx` | `scripts/scrape_xlsx_make_model.py` |
| 2021 | `.xlsx` (different layout) | `scripts/scrape_2021_failure.py` |
| 2022 | `.xlsx` | `scripts/scrape_xlsx_make_model.py` |
| 2023 | `.xlsx` | `scripts/scrape_xlsx_make_model.py` |
| 2024 | `.xlsx` | `scripts/scrape_xlsx_make_model.py` |

> **Note:** 2021–2024 files exclude low-population make/model/year combinations
> for GDPR reasons, resulting in fewer records than earlier years.

> **Note:** The 2021 source file combines "Steering and Suspension" into a single
> inspection column. This is mapped to `Steering`; `Suspension` in 2021 refers
> solely to the suspension *test* result, consistent with all other years.

### After Adding a New Year

1. Scrape the source file with the appropriate script (or add a new one following
   the same pattern).
2. Run `python3 scripts/recalc_percentages.py` to normalise all `_pct` fields.
3. Optionally run `python3 scripts/build_model_lookup.py` to regenerate the
   canonical model name lookup (`data/model_lookup.json`).

---

## Data Optimisation — JSON Attribute Key Length

The `manufacturers.json` (and per-year equivalents) repeat 17 attribute keys for every model-year entry. With **7,824 entries** in the 2016 dataset alone, the key names have a significant impact on file size.

### Key Mapping

| Long Key       | Short Key | Saved Chars |
|----------------|-----------|-------------|
| `Total`        | `T`       | 4           |
| `Pass`         | `P`       | 3           |
| `Fail`         | `F`       | 3           |
| `Safety`       | `Sa`      | 4           |
| `Lighting`     | `Li`      | 6           |
| `Steering`     | `St`      | 6           |
| `Braking`      | `Br`      | 5           |
| `Wheels`       | `Wh`      | 4           |
| `Engine`       | `En`      | 4           |
| `Chassis`      | `Ch`      | 5           |
| `SideSlip`     | `Ss`      | 6           |
| `Suspension`   | `Su`      | 8           |
| `Light`        | `Lt`      | 3           |
| `Brake`        | `Bk`      | 3           |
| `Emissions`    | `Em`      | 7           |
| `Other`        | `Ot`      | 3           |
| `Incomplete`   | `In`      | 8           |

**Per entry:** 113 → 31 key characters (**82 chars saved × 7,824 entries = 641,568 bytes**)

### Size Comparison (2016 data, 7,824 year entries)

| Format              | Long Keys   | Short Keys  | Savings         |
|---------------------|-------------|-------------|-----------------|
| Pretty-printed JSON | 3,059 KB    | 2,432 KB    | 627 KB (20.5%)  |
| Minified JSON       | 1,633 KB    | 1,006 KB    | 627 KB (38.4%)  |
| Minified + gzip     | 150 KB      | 136 KB      | 14 KB (9.1%)    |

### Verdict

- **Without compression:** Short keys save **~627 KB (20–38%)** depending on formatting. Meaningful for bandwidth and parse time.
- **With gzip (typical for HTTP):** Savings drop to **~14 KB (9.1%)** because gzip already exploits the repetitive key strings.
- **Trade-off:** Short keys hurt readability. A lookup table is needed to decode them.
- **Recommendation:** Use **short keys for production/API responses** (served minified + gzipped). Keep **long keys in source data files** for human readability. The frontend can map short keys back to display names.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![DuckDB](https://img.shields.io/badge/DuckDB-1.5-yellow)
![Parquet](https://img.shields.io/badge/Parquet-format-green)
![Data Quality](https://img.shields.io/badge/Data%20Quality-19%20checks-brightgreen)

# Wafer Defect Data Lake Pipeline

A Python Data Lake pipeline that ingests KLA/Tencor `.000` wafer inspection files, parses a non-standard industrial text format, builds Bronze / Silver / Gold layers with DuckDB and Parquet, and validates every layer with automated data quality checks.

## Architecture

```text
.000 Source (KLA/Tencor)
     │
     ▼
Ingestion (SHA-256, versioning, idempotency)
     │
     ▼
Raw Layer + Metadata
     │
     ▼
Wafer Parser (custom TXT parser)
     │
     ▼
Bronze (Parquet, 1 row = 1 defect, append-only)
     │
     ▼
Silver (cleaning + size_category + deduplication)
     │
     ▼
Gold (1 row = 1 inspection run + risk_score)
     │
     ▼
Data Quality Checks (19 invariants)
     │
 PASS / FAIL
```

## Pipeline Stages

| Layer | Description |
|--------|-------------|
| Raw | Versioned immutable `.000` files + ingestion metadata |
| Bronze | Parsed defects, one row per defect, append-only |
| Silver | Cleaned defects + computed `size_category`, deduplicated |
| Gold | Wafer-level metrics + `risk_score` per inspection run |

The pipeline executes five stages:

1. Ingestion
2. Bronze
3. Silver
4. Gold
5. Data Quality Checks

## Tech Stack

- Python 3.13
- Pandas
- DuckDB
- Parquet
- Custom `.000` parser
- Git / GitHub

## Raw Layer & Incremental Ingestion

Source `.000` files live in `source/wafer/`. Every pipeline run executes an ingestion step that:

1. Computes SHA-256 for each `.000` file.
2. Checks `data/metadata/ingestion_log.csv` for a previous version with the same hash.
3. If the hash is unchanged — skips the file (idempotency).
4. If the hash is new — copies the file to `data/raw/{file_stem}/v{N}.000` and appends a row to the metadata log with `processed_at = NULL`.

### Raw Layer structure

```text
source/wafer/
 └── M000001_1005/
     └── M000001_1005-02.000          # «hot» source file

data/raw/
 └── M000001_1005-02/
     ├── v1.000                       # versioned copy
     └── v2.000                       # new version if file changes

data/metadata/
 └── ingestion_log.csv                # file_name, hash, version, ingested_at, file_size, raw_path, processed_at
```

### Incremental Bronze

Bronze is **append-only**: `build_bronze_wafer.py` processes only versions with `processed_at IS NULL`, appends their defects to the existing Bronze, and marks those versions as processed. Unchanged files and already-processed versions are skipped.

### Deduplication in Silver

Because Bronze keeps all versions of every file, the same defect may appear multiple times if a file was re-uploaded. Silver deduplicates by `(wafer_id, inspection_run_id, defect_id)` using `file_row_number DESC` — the latest appended version wins. Bronze keeps the full history; Silver and Gold contain one row per defect.

**Important:** Bronze reads from `data/raw/`, never from `source/`. The source folder is only the entry point for new or updated files.

## Project Structure

```text
source/
 └── wafer/
     └── M000001_1005/
         └── M000001_1005-02.000

data/
 ├── raw/
 │   └── M000001_1005-02/
 │       └── v1.000
 ├── metadata/
 │   └── ingestion_log.csv
 ├── bronze/
 │   └── defects.parquet
 ├── silver/
 │   └── defects_clean.parquet
 └── gold/
     └── wafer_metrics.parquet

src/
 ├── logger.py
 ├── pipeline.py
 ├── ingestion/
 │   ├── ingest_wafer.py
 │   ├── metadata.py
 │   └── wafer_parser.py
 ├── processing/
 │   ├── build_bronze_wafer.py
 │   ├── build_silver_wafer.py
 │   ├── build_gold_wafer.py
 │   └── check_invalid_sizes.py
 └── analytics/
     ├── quality_check.py
     ├── query_gold.py
     ├── station_lot_analysis.py
     └── viewer.py

logs/
```

## Features

- Custom parser for KLA/Tencor `.000` format
- Wafer-level metadata extraction (`lot_id`, `slot`, `inspection_station`, `step_id`, `result_timestamp`)
- SHA-256 based raw versioning with idempotent ingestion
- Incremental append-only Bronze (`processed_at` in metadata)
- Metadata tracking (`data/metadata/ingestion_log.csv`)
- Silver deduplication by `(wafer_id, inspection_run_id, defect_id)`
- Silver layer with size classification (`Small` / `Medium` / `Large`)
- Gold aggregated layer (1 row = 1 inspection run)
- Risk score with min-max normalization and log1p smoothing
- Zero-area defect handling (valid point defects in KLA format)
- 19 data quality invariants across all layers
- Station & lot analytics
- Structured logging
- Git version control

## Run

```bash
python -m src.pipeline
```

Expected output:

```text
INFO [0/5] INGESTION
INFO Ingestion summary: 0 new versions, 48 unchanged
INFO WAFER INGESTION: SUCCESS
INFO [1/5] BRONZE
INFO No unprocessed versions. Bronze unchanged.
INFO [2/5] SILVER
INFO Silver defects: 2369
INFO [3/5] GOLD
INFO Gold wafers: 48
INFO [4/5] DATA QUALITY CHECKS
INFO DATA QUALITY: PASS
INFO WAFER DATA LAKE PIPELINE: SUCCESS
```

### Inspect top runs by risk score

```bash
python -m src.analytics.query_gold
```

Prints top-20 inspection runs sorted by `risk_score` descending.

### Station & lot analytics

```bash
python -m src.analytics.station_lot_analysis
```

Prints four views: stations overview, top-5 worst lots by average risk score, defect classes distribution, and runs with `risk_score > 0.4`.

## Data Quality Rules

### Raw

- Every source file has a raw version (`Source files == raw versions`)
- No missing or empty raw files

### Bronze → Silver

- No duplicate defects by `(wafer_id, inspection_run_id, defect_id)`
- No NULL `x_rel` / `y_rel`
- No negative `x_size` / `y_size` / `defect_area` (zero is allowed — point defects)
- All defects have positive `d_size`

### Gold

- No duplicate inspection runs by `(wafer_id, inspection_run_id, inspection_station)`
- No NULL `defects_count`
- `Gold.total_defects == Silver.rows`
- All inspection runs from Silver are present in Gold
- Runs with non-zero-area defects must have a non-NULL `avg_defect_area`
- `risk_score` is always within `[0, 1]`

## Risk Score

`risk_score` is a **demonstration** analytical metric, not a production quality criterion. It ranks inspection runs by likelihood of being "interesting" for a process engineer.

```text
risk_score = clamp(
    0.40 × n_defects
  + 0.20 × n_log_avg_area
  + 0.20 × n_max_size
  + 0.10 × n_large
  − 0.10 × n_zero_ratio,
  0, 1
)
```

All `n_*` values are min-max normalized over the 48-run corpus. `log1p(avg_defect_area)` compresses outliers (raw values up to 449 721 µm²) so that a single large defect does not dominate hundreds of small ones.

**Important:** the weights `0.40 / 0.20 / 0.20 / 0.10 / −0.10` are chosen for demonstration only. In a real semiconductor project they should be derived from historical yield data or QA requirements.

## Analytics

`src/analytics/station_lot_analysis.py` produces four analytical views:

### 1. Stations overview

Per-station aggregates: runs, total defects, average defects per run, average area, average max size, total large defects, total zero-area defects.

**Note:** stations `TBI-0207-1122` and `1333034` have different measurement scales — `avg_defect_area` and `max_defect_size` are not directly comparable between them.

Example output:

```text
inspection_station  runs  total_defects  avg_defects_per_run  avg_area  avg_max_size  total_large  total_zero_area
           1333034    36         2265.0                62.92      0.65         12.11        632.0              0.0
     TBI-0207-1122    12          104.0                 8.67 228762.40        204.57          6.0             98.0
```

### 2. Top-5 worst lots

Aggregated `risk_score` per lot — surfaces lots that are systematically worse.

### 3. Defect classes distribution

Counts and shares by `class_number`. In the current dataset all defects have `class_number = 0`, but the pipeline supports any number of classes.

### 4. Alerts

Runs with `risk_score > 0.4` — candidates for engineer review.

## KLA/Tencor `.000` Format Notes

- The `.000` files are plain text, not binary. Excel opens them as delimited text, but the pipeline reads them directly with a custom parser.
- The file contains a header (`DefectRecordSpec`), a column description block, and a `DefectList` with defect records.
- Some defects have `XSIZE = YSIZE = DEFECTAREA = 0` while `DSIZE > 0`. These are **valid point defects** where the tool did not record a rectangular area but did record an equivalent diameter. They are kept in Silver and counted in Gold, and quality checks validate `x_size / y_size / defect_area` as `>= 0` rather than `> 0`.

## Limitations

- Dataset is limited to 48 inspection runs; risk score weights are not calibrated for production.
- `inspection_station` values (`TBI-0207-1122`, `1333034`) have different measurement scales; direct comparison of `avg_defect_area` and `max_defect_size` between stations is not meaningful.
- `result_timestamp` is stored as VARCHAR; casting to TIMESTAMP is left for future work.
- Bronze is append-only: if a file is re-uploaded with the same defects, they are deduplicated in Silver, but Bronze keeps the full version history. The pipeline is incremental at the file level (only new versions are parsed), not at the defect level.
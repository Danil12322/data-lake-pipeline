# Data Lake Pipeline

A Python Data Lake pipeline that ingests CSV files, versions raw data, transforms datasets into Parquet, performs data quality validation, and builds a Gold analytics layer using DuckDB.

## Architecture

```text
CSV Source
     │
     ▼
Ingestion (SHA-256)
     │
     ▼
Raw Layer + Metadata
     │
     ▼
Transformation
     │
     ▼
Bronze (Parquet)
     │
     ▼
Data Quality Checks
     │
 PASS / FAIL
     │
     ▼
Gold Layer
```
## Pipeline Stages

| Layer | Description |
|--------|-------------|
| Raw | Versioned immutable CSV files |
| Bronze | Standardized Parquet dataset |
| Silver | Trusted business orders |
| Gold | Customer sales analytics |

The pipeline executes five stages:

1. Ingestion
2. Transformation
3. Data Quality
4. Silver
5. Gold

## Tech Stack

- Python 3.13
- Pandas
- DuckDB
- Parquet
- Git / GitHub

## Project Structure

```text
data/
 ├── raw/
 ├── bronze/
 ├── gold/
 └── metadata/

source/
src/
 ├── ingestion/
 ├── processing/
 ├── analytics/
 ├── logger.py
 └── pipeline.py

logs/
```

## Features

- SHA-256 file hashing
- Raw data versioning
- Metadata tracking
- Bronze Parquet layer
- Gold aggregated layer
- Data Quality validation
- Structured logging
- Git version control

## Run

```bash
python src/pipeline.py
```

## Data Quality Rules

- No duplicate orders
- No NULL total_amount
- Quantity must be positive
- Price cannot be negative
- Bronze and Gold customer counts must match
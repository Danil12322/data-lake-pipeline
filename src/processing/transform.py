import pandas as pd
from pathlib import Path

from logger import logger

def transform():
    source_dir = Path("source")

    dataframes = []

    for file in source_dir.glob("*.csv"):
        df = pd.read_csv(file)
        dataframes.append(df)

    result = pd.concat(dataframes, ignore_index=True)

    result["timestamp"] = pd.to_datetime(result["timestamp"])
    result["total_amount"] = result["quantity"] * result["price"]

    cleaned = result.drop_duplicates(
        subset=["order_id"],
        keep="first"
    )

    Path("data/bronze").mkdir(parents=True, exist_ok=True)

    output_path = "data/bronze/sales.parquet"

    cleaned.to_parquet(output_path, index=False)

    logger.info(f"Rows before: {len(result)}")
    logger.info(f"Rows after: {len(cleaned)}")
    logger.info(f"Saved: {output_path}")


if __name__ == "__main__":
    transform()
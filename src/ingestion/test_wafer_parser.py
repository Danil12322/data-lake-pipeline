import pandas as pd
plan_df = pd.read_parquet("data/bronze/test_plan.parquet")
m203_03 = plan_df[
    (plan_df["lot_id"] == "M203202_3965") & (plan_df["wafer_id"].astype(str).str.replace("@", "") == "03")
]
print("Rows for M203202_3965-@03:", len(m203_03))
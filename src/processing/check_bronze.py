import duckdb

con = duckdb.connect()

print("Gold schema:")
print(
    con.execute("DESCRIBE SELECT * FROM 'data/gold/wafer_metrics.parquet'")
    .df()[["column_name", "column_type"]]
    .to_string(index=False)
)

print("\nFirst 3 rows:")
print(
    con.execute("SELECT * FROM 'data/gold/wafer_metrics.parquet' LIMIT 3")
    .df()
    .to_string(index=False)
)
from functions import *
import polars as pl
import time

start_time = time.time()
pl.Config.set_tbl_cols(20)
pl.Config.set_tbl_rows(10)

# change this to the year you want to analyze
year = 2023
dates = get_weekdays_for_year(year)

all_rows = []
for date in dates:
    df = get_date_results(date)
    if df is not None:
        try:
            pl_df = pl.from_pandas(df)

            pl_df = pl_df.with_columns(
                [
                    # Extract last char from Market Cap (e.g., B or M)
                    pl.col("Market Cap")
                    .str.strip_chars()
                    .str.slice(-1, 1)
                    .alias("charr"),
                    # Clean and convert Market Cap
                    pl.col("Market Cap")
                    .str.replace("T", "")
                    .str.replace("B", "")
                    .str.replace("M", "")
                    .str.replace("K", "")
                    .str.replace("--", "0")
                    .cast(pl.Float64)
                    .alias("market_cap_clean"),
                    # Clean and convert EPS Estimate
                    pl.col("EPS Estimate")
                    .str.replace("-", "0")
                    .cast(pl.Float64)
                    .alias("eps_estimate_clean"),
                    # Clean and convert Reported EPS
                    pl.col("Reported EPS")
                    .str.replace("-", "0")
                    .cast(pl.Float64)
                    .alias("reported_eps_clean"),
                ]
            )

            # Apply all filters
            filtered_df = pl_df.filter(
                (
                    (pl.col("charr") == "T")
                    | (pl.col("charr") == "B")
                    | ((pl.col("charr") == "M") & (pl.col("market_cap_clean") > 500))
                )
                & (pl.col("eps_estimate_clean") > 0)
                & (pl.col("reported_eps_clean") > 0)
                & (pl.col("Surprise (%)") > 20)
            )

            print(date)
            # print(pl_df)
            # print(filtered_df)
            tickers_dates = {
                row["Symbol"]: date for row in filtered_df.head(5).to_dicts()
            }
            tickers_dates["IWM"] = date
            print(tickers_dates)
            res = fetch_and_check_multiticker_closes(tickers_dates)
            df = results_to_polars(res)
            df = df.with_columns(pl.lit(date).alias("Date"))
            # print(df)
            all_rows.append(df)
        except Exception as e:
            print(f"Error processing {date}: {e}")

final_df = pl.concat(all_rows)
print(final_df)
final_df.write_excel("output.xlsx")
df_summary = calculate_average_and_excess_returns_polars(final_df)
results = strategy_performance_summary(df_summary)
print(f"Strategy Performance Summary for {year}:")
print(results)
end_time = time.time()
print(f"Time taken: {end_time - start_time:.2f} seconds")

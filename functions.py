from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
from selenium.common.exceptions import TimeoutException, WebDriverException
from datetime import datetime, timedelta
import polars as pl
from selenium.webdriver.firefox.options import Options
import yfinance as yf
import polars as pl
import numpy as np
from scipy import stats


def get_date_results(date: str) -> pd.DataFrame | None:
    driver = None
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Firefox(options=options)
        driver.set_page_load_timeout(15)  # timeout for full page load

        url = (
            f"https://finance.yahoo.com/calendar/earnings?day={date}&offset=0&size=100"
        )
        driver.get(url)

        # Wait until the table appears
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table")
        rows = table.find_all("tr")

        headers = [th.text.strip() for th in rows[0].find_all("th")]
        data = [[td.text.strip() for td in row.find_all("td")] for row in rows[1:]]

        df = pd.DataFrame(data, columns=headers).fillna("0")
        df["Surprise (%)"] = (
            df["Surprise (%)"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.replace("+", "", regex=False)
            .replace("-", "0")
            .astype(float)
        )

        return df.sort_values(by="Surprise (%)", ascending=False)

    except (TimeoutException, WebDriverException) as e:
        print(f"Timeout or WebDriver issue on {date}: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass  # ignore quit errors

    except Exception as e:
        print(f"Other error on {date}: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def get_weekdays_for_year(year):
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)

    delta = end_date - start_date
    weekdays = [
        (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(delta.days + 1)
        if (start_date + timedelta(days=i)).weekday() < 5  # 0–4 are Mon–Fri
    ]

    return weekdays


def results_to_polars(res):
    rows = []

    for ticker, info in res.items():
        row = {
            "Ticker": ticker,
            "Base Close": info.get("base_close"),
            "Low@1": info.get("low_at_index_1"),
        }

        for day_label, result_day in info.get("close_comparisons", {}).items():
            row[f"{day_label} Above"] = result_day["above_base"]
            row[f"{day_label} Close"] = result_day["close"]
            row[f"{day_label} W/L"] = result_day["W/L"]

        rows.append(row)

    return pl.DataFrame(rows)


def fetch_and_check_multiticker_closes(ticker_date_dict):
    result = {}

    tickers = list(ticker_date_dict.keys())
    earliest_date = min(ticker_date_dict.values())

    data = yf.download(tickers, start=earliest_date, group_by="ticker")

    for ticker in tickers:
        start_date = ticker_date_dict[ticker]

        try:
            df_ticker = data[ticker].reset_index()
            df_ticker = df_ticker[df_ticker["Date"] >= start_date]

            if not df_ticker.empty:
                pl_df = pl.from_pandas(df_ticker)
                closes = pl_df.get_column("Close")
                base = closes[1] if len(closes) > 1 else None
                low_at_index_1 = pl_df.get_column("Low")[2] if len(pl_df) > 2 else None

                comparisons = {}
                for offset in [7, 14, 21, 28, 35]:
                    if base is not None and offset < len(closes):
                        close_val = closes[offset]
                        wl = ((close_val / base) - 1) * 100
                        comparisons[f"day_{offset}"] = {
                            "above_base": close_val > base,
                            "close": round(close_val, 2),
                            "W/L": round(wl, 4),
                        }
                    else:
                        comparisons[f"day_{offset}"] = {
                            "above_base": None,
                            "close": None,
                            "W/L": None,
                        }

                result[ticker] = {
                    "data": pl_df,
                    "base_close": round(base, 2) if base is not None else None,
                    "low_at_index_1": (
                        round(low_at_index_1, 2) if low_at_index_1 is not None else None
                    ),
                    "close_comparisons": comparisons,
                }

            else:
                result[ticker] = {
                    "data": None,
                    "base_close": None,
                    "low_at_index_1": None,
                    "close_comparisons": None,
                }

        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            result[ticker] = {
                "data": None,
                "base_close": None,
                "low_at_index_1": None,
                "close_comparisons": None,
            }

    return result


def calculate_average_and_excess_returns_polars(df: pl.DataFrame) -> pl.DataFrame:
    """
    Given a Polars DataFrame of stock performance including VTI and surprise stocks,
    this function calculates:
    - Average return of surprise stocks (excluding VTI) at day 7, 14, 28
    - VTI return at each offset
    - Excess return at 7, 14, 28 days (Surprise Avg - VTI)

    Returns:
        Polars DataFrame with columns:
        Date | Avg day_7 | VTI day_7 | Excess day_7 | ... (for 14, 28)
    """
    # 1. Filter out VTI for surprise stock returns
    surprise_df = df.filter(pl.col("Ticker") != "VTI")

    avg_returns = surprise_df.group_by("Date").agg(
        [
            pl.col("day_7 W/L").mean().alias("Avg day_7"),
            pl.col("day_14 W/L").mean().alias("Avg day_14"),
            pl.col("day_28 W/L").mean().alias("Avg day_28"),
        ]
    )

    # 2. Get VTI returns for each date
    VTI_df = df.filter(pl.col("Ticker") == "VTI").select(
        [
            "Date",
            pl.col("day_7 W/L").alias("VTI day_7"),
            pl.col("day_14 W/L").alias("VTI day_14"),
            pl.col("day_28 W/L").alias("VTI day_28"),
        ]
    )

    # 3. Join and calculate excess
    result = avg_returns.join(VTI_df, on="Date", how="inner").with_columns(
        [
            (pl.col("Avg day_7") - pl.col("VTI day_7")).alias("Excess day_7"),
            (pl.col("Avg day_14") - pl.col("VTI day_14")).alias("Excess day_14"),
            (pl.col("Avg day_28") - pl.col("VTI day_28")).alias("Excess day_28"),
        ]
    )

    return result


def strategy_performance_summary(df: pl.DataFrame) -> pl.DataFrame:
    """
    Compute alpha, p-value, Sharpe ratio, and win rate for each excess return column.

    Parameters:
        df (pl.DataFrame): Polars DataFrame containing excess return columns:
                           'Excess day_7', 'Excess day_14', 'Excess day_28'

    Returns:
        pl.DataFrame: Summary with columns:
            Offset | Alpha (mean) | T-test p-value | Sharpe Ratio | Win Rate
    """
    results = []

    for offset in ["Excess day_7", "Excess day_14", "Excess day_28"]:
        # Extract column as NumPy array
        values = df.select(pl.col(offset)).drop_nulls().to_series().to_numpy()

        if len(values) == 0:
            continue

        alpha = float(np.mean(values))
        std_dev = float(np.std(values, ddof=1))
        sharpe = alpha / std_dev if std_dev != 0 else np.nan
        win_rate = np.mean(values > 0)
        t_stat, p_value = stats.ttest_1samp(values, 0)

        results.append(
            {
                "Offset": offset,
                "Alpha (mean)": round(alpha, 4),
                "T-test p-value": round(p_value, 4),
                "Sharpe Ratio": round(sharpe, 4),
                "Win Rate": round(win_rate * 100, 2),
            }
        )

    return pl.DataFrame(results)

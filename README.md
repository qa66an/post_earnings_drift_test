# post-earnings-drift-test

This project tests the validity of the **post-earnings announcement drift (PEAD)** anomaly — the idea that stocks with unexpectedly strong earnings continue to drift upward after the announcement, violating the **Efficient Market Hypothesis (EMH)**.

We focus on U.S. equities with **earnings surprises greater than 20%**, and evaluate whether they systematically outperform the **IWM ETF** over short-term horizons.

---

## 🧠 Goal

To empirically test if a simple, rules-based strategy built on earnings surprises produces statistically significant **excess returns** after 7, 14, and 28 days — a direct test of EMH.

---

## 🔍 What This Project Does

- Scrapes daily earnings calendars from Yahoo Finance
- Filters for stocks with positive EPS and surprises > 20%
- Downloads price data from Yahoo Finance using `yfinance`
- Measures post-earnings returns vs. IWM for:
  - 7-day, 14-day, and 28-day holding periods
- Calculates key performance metrics:
  - **Alpha (mean excess return)**
  - **T-test p-value**
  - **Sharpe Ratio**
  - **Win Rate vs IWM**

---

## 📁 Project Structure

functions.py # Data scraping, return calculations, statistical tests
run.py # Orchestrates full pipeline over one year
output.xlsx # Intermediate and final results

---

## 📈 Sample Results (2023 Test)

| Offset | Alpha (%) | p-value | Sharpe | Win Rate |
| ------ | --------- | ------- | ------ | -------- |
| 7-day  | 0.31      | 0.39    | 0.06   | 47.6%    |
| 14-day | 0.44      | 0.37    | 0.06   | 49.7%    |
| 28-day | 0.60      | 0.37    | 0.07   | 51.8%    |

> These results suggest mild outperformance, but without statistical significance — future segmentation by sector or surprise magnitude may yield deeper insight.

---

## 📦 Dependencies

- Python 3.10+
- `polars`
- `selenium`
- `yfinance`
- `scipy`
- `pandas` (for HTML table parsing)

Install them via:

```bash
pip install -r requirements.txt
```

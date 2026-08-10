"""
Verification script for the Qiita article:
"An Unexpected Fact: Bitcoin's Sharpe Ratio Has Outperformed the S&P 500"

Article:
https://qiita.com/tikeda123/items/a03a251da3ae8206044b

Claims made in the article:

- Bitcoin (BTC) outperformed the S&P 500 in annual Sharpe ratios
  in many years from 2018 to 2025.
- Average Sharpe ratio:
    BTC    = 0.86
    S&P 500 = 0.65

This script recalculates the Sharpe ratio using actual daily price data
from Yahoo Finance and compares the results with the values reported
in the article.

Prerequisites:
pip install yfinance pandas matplotlib numpy --break-system-packages

Usage:
python verify_sharpe_ratio.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf


# ---------------------------------------------------------
# 1. Values reported in the article
# ---------------------------------------------------------

# article_data = pd.DataFrame({
#     "year": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
#     "BTC_article": [
#         -0.79, 1.55, 2.20, 1.45,
#         -0.85, 1.10, 0.95, 1.25
#     ],
#     "SP500_article": [
#         -0.32, 0.94, 1.05, 0.93,
#         -0.76, 0.85, 0.70, 0.80
#     ],
# })


# ---------------------------------------------------------
# 2. Download actual price data from Yahoo Finance
#
# BTC-USD: Bitcoin
# ^GSPC: S&P 500
# ---------------------------------------------------------

START = "2018-01-01"
END = "2025-10-31"

# The article subtracts a risk-free rate,
# but the exact risk-free rate series is not publicly specified.
# We therefore start with a risk-free rate of 0%.
RISK_FREE_RATE = 0.0

print("Downloading price data...")

btc = yf.download(
    "BTC-USD",
    start=START,
    end=END,
    progress=False
)["Close"]

sp500 = yf.download(
    "^GSPC",
    start=START,
    end=END,
    progress=False
)["Close"]



# Depending on the yfinance version, ["Close"] may return
# a DataFrame with one column. Convert it to a Series.

if isinstance(btc, pd.DataFrame):
    btc = btc.squeeze("columns")

if isinstance(sp500, pd.DataFrame):
    sp500 = sp500.squeeze("columns")


# ---------------------------------------------------------
# 3. Calculate daily returns
# ---------------------------------------------------------

# 　単純リターンを計算　※対数リターンではない
btc_return = btc.pct_change().dropna()

sp500_return = sp500.pct_change().dropna()

# Bitcoin trades 365 days per year.
TRADING_DAYS_BTC = 365

# The S&P 500 has approximately 252 trading days per year.
TRADING_DAYS_SP500 = 252


def annual_sharpe(
    daily_returns: pd.Series,
    trading_days: int,
    rf: float = 0.0
) -> float:
    """
    Calculate the annualized Sharpe ratio
    from a series of daily returns.
    """

    # Ensure the input is a one-dimensional Series.
    daily_returns = pd.Series(daily_returns).astype(float)

    mean_daily = float(daily_returns.mean())
    std_daily = float(daily_returns.std())

    # Annualized return
    annual_return = mean_daily * trading_days

    # Annualized volatility
    annual_vol = std_daily * np.sqrt(trading_days)

    if annual_vol == 0:
        return np.nan

    return (annual_return - rf) / annual_vol


# ---------------------------------------------------------
# 4. Recalculate annual Sharpe ratios
# ---------------------------------------------------------

results = []

for year in range(2018, 2026):

    btc_y = btc_return[btc_return.index.year == year]
    sp500_y = sp500_return[sp500_return.index.year == year]
    print(f"{year} BTC daily returns:\n{btc_y}")

    btc_sharpe = (
        annual_sharpe(
            btc_y,
            TRADING_DAYS_BTC,
            RISK_FREE_RATE
        )
        if len(btc_y) > 0
        else np.nan
    )


    sp500_sharpe = (
        annual_sharpe(
            sp500_y,
            TRADING_DAYS_SP500,
            RISK_FREE_RATE
        )
        if len(sp500_y) > 0
        else np.nan
    )

    results.append({
        "year": year,
        "BTC_calc": btc_sharpe,
        "SP500_calc": sp500_sharpe
    })


calc_df = pd.DataFrame(results)


# ---------------------------------------------------------
# 5. Compare article values with calculated values
# ---------------------------------------------------------

# merged = pd.merge(
#     article_data,
#     calc_df,
#     on="year"
# )

# merged["BTC_diff"] = (
#     merged["BTC_calc"] - merged["BTC_article"]
# )

# merged["SP500_diff"] = (
#     merged["SP500_calc"] - merged["SP500_article"]
# )


pd.set_option(
    "display.float_format",
    lambda x: f"{x:.2f}"
)

print("\n=== Annual Sharpe Ratio Comparison ===")
# print(merged.to_string(index=False))


print("\n=== Average Sharpe Ratio (2018-2025) ===")

# print(
#     f"BTC     : "
#     f"Article={article_data['BTC_article'].mean():.2f}  "
#     f"Calculated={calc_df['BTC_calc'].mean():.2f}"
# )

# print(
#     f"S&P 500 : "
#     f"Article={article_data['SP500_article'].mean():.2f}  "
#     f"Calculated={calc_df['SP500_calc'].mean():.2f}"
# )


# ---------------------------------------------------------
# 6. Visualization
# ---------------------------------------------------------

fig, axes = plt.subplots(
    2,
    1,
    figsize=(11, 10)
)


# ---------------------------------------------------------
# (1) Annual Sharpe ratio comparison
# ---------------------------------------------------------

ax1 = axes[0]

x = np.arange(len(merged))
width = 0.2

ax1.bar(
    x - 1.5 * width,
    merged["BTC_article"],
    width,
    label="BTC (Article)",
    color="#f2a900"
)

ax1.bar(
    x - 0.5 * width,
    merged["BTC_calc"],
    width,
    label="BTC (Calculated)",
    color="#f2a900",
    alpha=0.5,
    hatch="//"
)

ax1.bar(
    x + 0.5 * width,
    merged["SP500_article"],
    width,
    label="S&P 500 (Article)",
    color="#1f77b4"
)

ax1.bar(
    x + 1.5 * width,
    merged["SP500_calc"],
    width,
    label="S&P 500 (Calculated)",
    color="#1f77b4",
    alpha=0.5,
    hatch="//"
)

ax1.axhline(
    0,
    color="black",
    linewidth=0.8
)

ax1.set_xticks(x)
ax1.set_xticklabels(merged["year"])

ax1.set_ylabel("Sharpe Ratio")

ax1.set_title(
    "Annual Sharpe Ratio: Article vs. Recalculated Values"
)

ax1.legend()

ax1.grid(
    axis="y",
    alpha=0.3
)


# ---------------------------------------------------------
# (2) Average Sharpe ratio comparison
# ---------------------------------------------------------

ax2 = axes[1]

labels = ["BTC", "S&P 500"]

# article_avg = [
#     article_data["BTC_article"].mean(),
#     article_data["SP500_article"].mean()
# ]

calc_avg = [
    calc_df["BTC_calc"].mean(),
    calc_df["SP500_calc"].mean()
]

x2 = np.arange(len(labels))

# ax2.bar(
#     x2 - width / 2,
#     article_avg,
#     width,
#     label="Article Average",
#     color="#555555"
# )

ax2.bar(
    x2 + width / 2,
    calc_avg,
    width,
    label="Calculated Average",
    color="#2ca02c"
)

ax2.set_xticks(x2)
ax2.set_xticklabels(labels)

ax2.set_ylabel("Average Sharpe Ratio")

ax2.set_title(
    "Average Sharpe Ratio (2018-2025)"
)

ax2.legend()

ax2.grid(
    axis="y",
    alpha=0.3
)


# Add value labels to the bars


for i, v in enumerate(calc_avg):
    ax2.text(
        i + width / 2,
        v,
        f"{v:.2f}",
        ha="center",
        va="bottom" if v >= 0 else "top"
    )


plt.tight_layout()


plt.show()
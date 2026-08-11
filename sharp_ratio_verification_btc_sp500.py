"""
"An Unexpected Fact: Bitcoin's Sharpe Ratio Has Outperformed the S&P 500"


This script calculates the Sharpe ratio using actual daily price data
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
# 1. Download actual price data from Yahoo Finance
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
# 2. Calculate daily returns
# ---------------------------------------------------------

# 　単純リターンを計算　※対数リターンではない
btc_return = btc.pct_change().dropna()

sp500_return = sp500.pct_change().dropna()

# Bitcoin trades 365 days per year.
TRADING_DAYS_BTC = 365

# The S&P 500 has approximately 252 trading days per year.
TRADING_DAYS_SP500 = 252


def annual_sharpe_ratio(
    daily_returns: pd.Series,
    trading_days: int,
    risk_free_rate: float = 0.0
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

    return (annual_return - risk_free_rate) / annual_vol


# ---------------------------------------------------------
# 3. Calculate annual Sharpe ratios
# ---------------------------------------------------------

results = []

for year in range(2018, 2026):

    btc_y = btc_return[btc_return.index.year == year]
    sp500_y = sp500_return[sp500_return.index.year == year]

    btc_sharpe_ratio = (
        annual_sharpe_ratio(
            btc_y,
            TRADING_DAYS_BTC,
            RISK_FREE_RATE
        )
        if len(btc_y) > 0
        else np.nan
    )


    sp500_sharpe_ratio = (
        annual_sharpe_ratio(
            sp500_y,
            TRADING_DAYS_SP500,
            RISK_FREE_RATE
        )
        if len(sp500_y) > 0
        else np.nan
    )

    results.append({
        "year": year,
        "BTC_calc": btc_sharpe_ratio,
        "SP500_calc": sp500_sharpe_ratio
    })


calc_df = pd.DataFrame(results)


# ---------------------------------------------------------
# 4. Show calculated Sharpe ratios
# ---------------------------------------------------------

# PandasのDataFrameなどで浮動小数点数（float）をどう表示するかを指定する設定
pd.set_option(
    "display.float_format",
    lambda x: f"{x:.2f}"
)

print(calc_df.to_string(index=False))



print(f"BTC     : Calculated={calc_df['BTC_calc'].mean():.2f}")
print(f"S&P 500 : Calculated={calc_df['SP500_calc'].mean():.2f}")


# ---------------------------------------------------------
# 5. Visualization
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

x = np.arange(len(calc_df))
width = 0.35

ax1.bar(
    x - width / 2,
    calc_df["BTC_calc"],
    width,
    label="BTC",
    color="#f2a900"
)

ax1.bar(
    x + width / 2,
    calc_df["SP500_calc"],
    width,
    label="S&P 500",
    color="#1f77b4"
)

ax1.axhline(
    0,
    color="black",
    linewidth=0.8
)

ax1.set_xticks(x)
ax1.set_xticklabels(calc_df["year"])

ax1.set_ylabel("Sharpe Ratio")

ax1.set_title(
    "Annual Sharpe Ratio: BTC vs. S&P 500 (Calculated)"
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

calc_avg = [
    calc_df["BTC_calc"].mean(),
    calc_df["SP500_calc"].mean()
]

x2 = np.arange(len(labels))

ax2.bar(
    x2,
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
        i,
        v,
        f"{v:.2f}",
        ha="center",
        va="bottom" if v >= 0 else "top"
    )


plt.tight_layout()


plt.show()
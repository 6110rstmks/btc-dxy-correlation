"""
Qiita記事「意外な事実：ビットコインのシャープレシオはS&P500を上回っている」の検証スクリプト
https://qiita.com/tikeda123/items/a03a251da3ae8206044b

記事の主張:
- 2018〜2025年の年次シャープレシオで、ビットコイン(BTC)がS&P500を多くの年で上回った
- 平均シャープレシオ: BTC=0.86, S&P500=0.65

このスクリプトは、実際の日次価格データ(Yahoo Finance)からシャープレシオを
自分で再計算し、記事の数値と比較します。

【事前準備】
pip install yfinance pandas matplotlib numpy --break-system-packages

【実行方法】
python verify_sharpe_ratio.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

# ---------------------------------------------------------
# 1. 記事に掲載されている数値(比較用の正解データ)
# ---------------------------------------------------------
article_data = pd.DataFrame({
    "year": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
    "BTC_article":    [-0.79, 1.55, 2.20, 1.45, -0.85, 1.10, 0.95, 1.25],
    "SP500_article":  [-0.32, 0.94, 1.05, 0.93, -0.76, 0.85, 0.70, 0.80],
})

# ---------------------------------------------------------
# 2. 実データの取得 (Yahoo Finance)
#    BTC-USD: ビットコイン, ^GSPC: S&P500
# ---------------------------------------------------------
START = "2018-01-01"
END = "2025-10-31"   # 記事の分析期間(2025年10月時点)に合わせる
RISK_FREE_RATE = 0.0  # 記事は「無リスク金利」を差し引いているが正確な系列は非公開のため
                       # まずは無リスク金利=0として検証し、必要に応じて調整する

print("価格データを取得中...")
btc = yf.download("BTC-USD", start=START, end=END, progress=False)["Close"]
sp500 = yf.download("^GSPC", start=START, end=END, progress=False)["Close"]

# yfinanceのバージョンによっては["Close"]がDataFrame(1列)で返ることがあるため
# 常に1次元のSeriesに変換しておく
if isinstance(btc, pd.DataFrame):
    btc = btc.squeeze("columns")
if isinstance(sp500, pd.DataFrame):
    sp500 = sp500.squeeze("columns")

# ---------------------------------------------------------
# 3. 日次リターン計算
# ---------------------------------------------------------
btc_ret = btc.pct_change().dropna()
sp500_ret = sp500.pct_change().dropna()

TRADING_DAYS_BTC = 365   # 暗号資産は年中無休
TRADING_DAYS_SP500 = 252 # 株式市場の年間営業日数

def annual_sharpe(daily_returns: pd.Series, trading_days: int, rf: float = 0.0) -> float:
    """日次リターン系列から年率換算シャープレシオを計算"""
    daily_returns = pd.Series(daily_returns).astype(float)  # 念のため1次元Seriesに強制変換
    mean_daily = float(daily_returns.mean())
    std_daily = float(daily_returns.std())
    annual_return = mean_daily * trading_days
    annual_vol = std_daily * np.sqrt(trading_days)
    if annual_vol == 0:
        return np.nan
    return (annual_return - rf) / annual_vol

# ---------------------------------------------------------
# 4. 年次シャープレシオを自前で再計算
# ---------------------------------------------------------
results = []
for year in range(2018, 2026):
    btc_y = btc_ret[btc_ret.index.year == year]
    sp500_y = sp500_ret[sp500_ret.index.year == year]

    btc_sharpe = annual_sharpe(btc_y, TRADING_DAYS_BTC, RISK_FREE_RATE) if len(btc_y) > 0 else np.nan
    sp500_sharpe = annual_sharpe(sp500_y, TRADING_DAYS_SP500, RISK_FREE_RATE) if len(sp500_y) > 0 else np.nan

    results.append({"year": year, "BTC_calc": btc_sharpe, "SP500_calc": sp500_sharpe})

calc_df = pd.DataFrame(results)

# ---------------------------------------------------------
# 5. 記事の数値と自前計算値を突き合わせ
# ---------------------------------------------------------
merged = pd.merge(article_data, calc_df, on="year")
merged["BTC_diff"] = merged["BTC_calc"] - merged["BTC_article"]
merged["SP500_diff"] = merged["SP500_calc"] - merged["SP500_article"]

pd.set_option("display.float_format", lambda x: f"{x:.2f}")
print("\n=== 年次シャープレシオ比較(記事 vs 自前計算) ===")
print(merged.to_string(index=False))

print("\n=== 平均シャープレシオ(2018-2025) ===")
print(f"BTC   : 記事={article_data['BTC_article'].mean():.2f}  自前計算={calc_df['BTC_calc'].mean():.2f}")
print(f"S&P500: 記事={article_data['SP500_article'].mean():.2f}  自前計算={calc_df['SP500_calc'].mean():.2f}")

# ---------------------------------------------------------
# 6. グラフ化 (matplotlib)
# ---------------------------------------------------------
fig, axes = plt.subplots(2, 1, figsize=(11, 10))

# --- (1) 記事の数値 vs 自前計算値を年次で棒グラフ比較 ---
ax1 = axes[0]
x = np.arange(len(merged))
width = 0.2

ax1.bar(x - 1.5*width, merged["BTC_article"], width, label="BTC (記事)", color="#f2a900")
ax1.bar(x - 0.5*width, merged["BTC_calc"], width, label="BTC (自前計算)", color="#f2a900", alpha=0.5, hatch="//")
ax1.bar(x + 0.5*width, merged["SP500_article"], width, label="S&P500 (記事)", color="#1f77b4")
ax1.bar(x + 1.5*width, merged["SP500_calc"], width, label="S&P500 (自前計算)", color="#1f77b4", alpha=0.5, hatch="//")

ax1.axhline(0, color="black", linewidth=0.8)
ax1.set_xticks(x)
ax1.set_xticklabels(merged["year"])
ax1.set_ylabel("シャープレシオ")
ax1.set_title("年次シャープレシオ: 記事の数値 vs 実データからの再計算")
ax1.legend()
ax1.grid(axis="y", alpha=0.3)

# --- (2) 平均シャープレシオの比較 ---
ax2 = axes[1]
labels = ["BTC", "S&P500"]
article_avg = [article_data["BTC_article"].mean(), article_data["SP500_article"].mean()]
calc_avg = [calc_df["BTC_calc"].mean(), calc_df["SP500_calc"].mean()]

x2 = np.arange(len(labels))
ax2.bar(x2 - width/2, article_avg, width, label="記事の平均値", color="#555555")
ax2.bar(x2 + width/2, calc_avg, width, label="自前計算の平均値", color="#2ca02c")
ax2.set_xticks(x2)
ax2.set_xticklabels(labels)
ax2.set_ylabel("平均シャープレシオ")
ax2.set_title("平均シャープレシオ(2018-2025)の比較")
ax2.legend()
ax2.grid(axis="y", alpha=0.3)

for i, v in enumerate(article_avg):
    ax2.text(i - width/2, v, f"{v:.2f}", ha="center", va="bottom" if v >= 0 else "top")
for i, v in enumerate(calc_avg):
    ax2.text(i + width/2, v, f"{v:.2f}", ha="center", va="bottom" if v >= 0 else "top")

plt.tight_layout()
plt.savefig("sharpe_ratio_verification.png", dpi=150)
print("\nグラフを sharpe_ratio_verification.png に保存しました")
plt.show()
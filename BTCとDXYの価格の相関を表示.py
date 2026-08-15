import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

# BTC
btc = yf.download(
    "BTC-USD",
    start="2022-12-01",
    end="2024-10-21",
    interval="1d",
    auto_adjust=False
)

# DXY
dxy = yf.download(
    "DX-Y.NYB",
    start="2022-12-01",
    end="2024-10-21",
    interval="1d",
    auto_adjust=False
)

# Closeだけ取り出す
df_btc = btc["Close"].squeeze()
df_dollar = dxy["Close"].squeeze()

# BTCとDXYを日時で結合
df_merged = pd.concat(
    [df_btc, df_dollar],
    axis=1,
    join="inner"
)

df_merged.columns = ["close_btc", "close_dollar"]

# 全期間の相関
correlation = df_merged["close_btc"].corr(
    df_merged["close_dollar"]
)


# 28日移動相関
window_size = 28

rolling_correlation = (
    df_merged["close_btc"]
    .rolling(window=window_size)
    .corr(df_merged["close_dollar"])
)

# 移動相関をプロット
plt.figure(figsize=(12, 6))

plt.plot(
    rolling_correlation.index,
    rolling_correlation,
    label="Rolling Correlation"
)

plt.title(f"Rolling Correlation (Window Size = {window_size})")
plt.xlabel("Date")
plt.ylabel("Correlation")

# 相関係数は -1 ～ 1
plt.ylim(-1, 1)

# plt.grid(True)
plt.legend()

plt.show()
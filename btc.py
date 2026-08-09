import yfinance as yf
import matplotlib.pyplot as plt

# BTC/USDのデータを取得
btc = yf.download(
    "BTC-USD",
    start="2022-12-01",
    end="2026-07-21",
    interval="1d"
)

# BTC価格を描画
plt.figure(figsize=(12, 6))
plt.plot(btc.index, btc["Close"])
plt.xlabel("Date")
plt.ylabel("BTC Price (USD)")
plt.title("Bitcoin Price")
plt.grid()
plt.show()
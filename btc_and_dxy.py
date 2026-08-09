import yfinance as yf
import matplotlib.pyplot as plt

# BTC
btc = yf.download(
    "BTC-USD",
    start="2022-12-01",
    end="2024-10-21",
    interval="1d"
)

# DXY
dxy = yf.download(
    "DX-Y.NYB",
    start="2022-12-01",
    end="2024-10-21",
    interval="1d"
)

fig, ax1 = plt.subplots(figsize=(12, 6))

# 左側のY軸：BTC
ax1.plot(btc.index, 
         btc["Close"],     
         color="orange",
         label="BTC"
         )
         
ax1.set_xlabel("Date")
ax1.set_ylabel("BTC Price")

# 右側のY軸：DXY
ax2 = ax1.twinx()
ax2.plot(dxy.index, dxy["Close"], label="DXY")
ax2.set_ylabel("DXY")

plt.title("BTC and DXY")
plt.show()
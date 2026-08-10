import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import yfinance as yf
from scipy.optimize import minimize

# データ取得
tickers = ['AAPL', 'MSFT', 'AMZN', 'JPM', 'JNJ']
data = yf.download(tickers, start='2000-01-01', end='2025-12-31')['Close']

# 日次対数リターン
log_returns = np.log(data / data.shift(1)).dropna()

print("=== 日次対数リターン ===")
print(log_returns)

# 日次単純リターン
simple_returns = data.pct_change().dropna()

# 年率リターンと年率ボラティリティ
annual_return = log_returns.mean() * 252
annual_vol = log_returns.std() * np.sqrt(252)

print("=== 年率リターン ===")
print(annual_return.round(4))
print("\n=== 年率ボラティリティ ===")
print(annual_vol.round(4))

# 累積リターン（対数リターンの累積和 → 指数変換）
cumulative = (1 + simple_returns).cumprod()

fig, ax = plt.subplots(figsize=(12, 6))
for ticker in tickers:
    ax.plot(cumulative.index, cumulative[ticker], label=ticker, linewidth=1.2)

# リーマンショック・コロナショックの時期に縦線
ax.axvline(pd.Timestamp('2008-09-15'), color='gray', linestyle='--', alpha=0.7, label='Lehman Shock')
ax.axvline(pd.Timestamp('2020-03-11'), color='gray', linestyle=':', alpha=0.7, label='COVID-19')

ax.set_title('Cumulative Returns (2000-2025)', fontsize=14)
ax.set_xlabel('Date')
ax.set_ylabel('Cumulative Return (Growth of $1)')
ax.legend(loc='upper left')
ax.set_yscale('log')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
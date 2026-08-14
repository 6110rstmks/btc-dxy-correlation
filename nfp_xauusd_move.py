"""
米国雇用統計(NFP)発表日にXAUUSD(金)が1日でどれくらい動くかを調べる。

- yfinanceには XAUUSD=X が無いため、COMEX金先物 GC=F を代理として使用。
  GC=Fはスポット金(XAUUSD)とほぼ同水準・同方向に動くため、値動きの大きさの
  近似として利用できる。
- 発表日1日分の値動きは以下の2指標で見る。
    値幅 (High - Low) : その日の値動きレンジ
    実体 (|Close - Open|) : 始値から終値までの一方向の動き
- 対象期間: 過去1年 (2025-08-12 〜 2026-08-12)
- NFP発表日はBLS(米労働統計局)の公式リリーススケジュールに基づく。
  2025年10月分は政府機関閉鎖(シャットダウン)により発表中止、
  9月分は11/20に延期、10月分と11月分は12/16にまとめて発表された。
"""

import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

from nfp_release_dates import NFP_RELEASES

plt.rcParams["font.family"] = "Hiragino Sans"

TICKER = "GC=F"  # COMEX金先物(XAUUSDの代理)

start = pd.Timestamp(NFP_RELEASES[0][0]) - pd.Timedelta(days=5)
end = pd.Timestamp(NFP_RELEASES[-1][0]) + pd.Timedelta(days=5)

data = yf.download(TICKER, start=start, end=end, interval="1d", auto_adjust=False, progress=False)
data.columns = data.columns.get_level_values(0)  # ティッカーの階層を除去

rows = []
for date_str, month_label, note in NFP_RELEASES:
    ts = pd.Timestamp(date_str)
    if ts not in data.index:
        print(f"[スキップ] {date_str} ({month_label}): 取引データなし - {note}")
        continue
    o, h, l, c = data.loc[ts, ["Open", "High", "Low", "Close"]]
    rows.append({
        "発表日": date_str,
        "対象月": month_label,
        "始値": o,
        "高値": h,
        "安値": l,
        "終値": c,
        "値幅($)": h - l,
        "実体($)": abs(c - o),
    })

result = pd.DataFrame(rows)
pd.set_option("display.float_format", lambda v: f"{v:.2f}")
print(result.to_string(index=False))

avg_range = result["値幅($)"].mean()
avg_body = result["実体($)"].mean()

print()
print(f"発表日の件数: {len(result)}件")
print(f"値幅(高値-安値)の平均: {avg_range:.2f} ドル (中央値 {result['値幅($)'].median():.2f} / 標準偏差 {result['値幅($)'].std():.2f})")
print(f"実体(|終値-始値|)の平均: {avg_body:.2f} ドル (中央値 {result['実体($)'].median():.2f} / 標準偏差 {result['実体($)'].std():.2f})")

# --- グラフ ---
labels = pd.to_datetime(result["発表日"]).dt.strftime("%m/%d")

fig, ax = plt.subplots(figsize=(11, 6))
bars = ax.bar(labels, result["値幅($)"], color="#2a78d6", width=0.6, label="発表日の値幅(高値-安値)")
ax.axhline(avg_range, color="#eb6834", linestyle="--", linewidth=2, label=f"平均 {avg_range:.0f}ドル")

for bar, value in zip(bars, result["値幅($)"]):
    ax.annotate(f"{value:.0f}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                ha="center", va="bottom", fontsize=9, color="#0b0b0b")

ax.set_title("米国雇用統計(NFP)発表日のXAUUSD値動き(過去1年・GC=F代理)")
ax.set_xlabel("発表日")
ax.set_ylabel("値幅 (High - Low, ドル)")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", color="#e1e0d9", linewidth=0.8)
ax.set_axisbelow(True)
ax.legend()

plt.tight_layout()
plt.show()

"""
米国雇用統計(NFP)発表直後、XAUUSDが1分足でどれくらい動くかを調べる。

- yfinanceの1分足は直近30日分しか取得できないため、過去1年分のNFP発表日
  すべてを1分足で見るにはDukascopyの無料ヒストリカルtickデータを使う。
  (Dukascopy: https://www.dukascopy.com/swiss/english/marketwatch/historical/)
- Dukascopyの生tickファイルは1時間単位(00h〜23h)。1日分=24リクエストを
  一気に並列で叩くと簡単にレート制限(429)にかかるため、本スクリプトでは
  1時間ずつ間隔を空けて順番に取得する。
- 取得したtick(ask/bid)から中値(mid = (ask+bid)/2)を計算し、1分足OHLCに
  リサンプルする。日ごとに data/xauusd_m1/ にキャッシュし、既にある日は
  再取得しない。よって「今後発表があるたびにNFP_RELEASESへ日付を追加して
  再実行する」だけで、1分足の実績データを蓄積していける。
- 発表時刻は米東部時間8:30(zoneinfoでDSTを自動判定)。
"""

import os
import time
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import matplotlib.pyplot as plt
from duka.core.processor import decompress

from nfp_release_dates import NFP_RELEASES, RELEASE_TIME_ET

plt.rcParams["font.family"] = "Hiragino Sans"

SYMBOL = "XAUUSD"
URL = "https://datafeed.dukascopy.com/datafeed/{symbol}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
DATA_DIR = "data/xauusd_m1"
LEDGER_PATH = "data/nfp_1min_moves.csv"

HOUR_DELAY_SEC = 0.5        # 1時間分のリクエストごとの待機(Dukascopyへの配慮)
RETRY_ATTEMPTS = 6
PRE_MINUTES = 5              # 発表前何分から見るか
POST_MINUTES = 30            # 発表後何分まで見るか
SUMMARY_HORIZON_MIN = 5      # 集計・棒グラフで使う「発表n分後」


def fetch_hour_ticks(session, day, hour):
    url = URL.format(symbol=SYMBOL, year=day.year, month=day.month - 1, day=day.day, hour=hour)
    for attempt in range(RETRY_ATTEMPTS):
        try:
            res = session.get(url, timeout=20)
        except requests.RequestException:
            time.sleep(1.5 * (attempt + 1))
            continue
        if res.status_code == 200:
            return res.content
        if res.status_code == 404:
            return b""
        time.sleep(1.5 * (attempt + 1))
    print(f"[警告] 取得失敗のためこの時間帯をスキップ: {url}")
    return b""


def fetch_day_1min(day):
    """指定日(UTC calendar date)のXAUUSD 1分足OHLC(mid値)をDataFrameで返す。"""
    session = requests.Session()
    all_ticks = []
    for hour in range(24):
        content = fetch_hour_ticks(session, day, hour)
        time.sleep(HOUR_DELAY_SEC)
        if not content:
            continue
        # decompressは「hour=0」を前提にtick時刻を復元するため、時間分を後で自分で補正する
        ticks = decompress(day, memoryview(bytearray(content)))
        for t, ask, bid, ask_vol, bid_vol in ticks:
            # duka.core.processor.normalize は価格を/100000する前提(5桁精度のFXペア向け)だが、
            # XAUUSDは2桁精度(例: 4310.53)のため、100倍して正しいスケールに戻す。
            all_ticks.append((t + timedelta(hours=hour), (ask + bid) / 2 * 100))

    if not all_ticks:
        return pd.DataFrame(columns=["open", "high", "low", "close"])

    series = pd.Series(
        [mid for _, mid in all_ticks],
        index=pd.DatetimeIndex([t for t, _ in all_ticks]),
    ).sort_index()
    ohlc = series.resample("1min").ohlc()
    return ohlc


def load_or_fetch_day(day):
    os.makedirs(DATA_DIR, exist_ok=True)
    cache_path = os.path.join(DATA_DIR, f"{day.isoformat()}.csv")
    if os.path.exists(cache_path):
        return pd.read_csv(cache_path, index_col=0, parse_dates=True)
    print(f"[取得中] {SYMBOL} {day} の1分足をDukascopyから取得...")
    ohlc = fetch_day_1min(day)
    ohlc.to_csv(cache_path)
    return ohlc


def release_utc_datetime(date_str):
    hour, minute = RELEASE_TIME_ET
    y, m, d = (int(x) for x in date_str.split("-"))
    local = datetime(y, m, d, hour, minute, tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc).replace(tzinfo=None)


def load_ledger():
    if os.path.exists(LEDGER_PATH):
        return pd.read_csv(LEDGER_PATH)
    return pd.DataFrame(columns=["発表日", "対象月", "分後", "価格", "値動き($)"])


def build_event_frame(date_str, month_label, ohlc):
    baseline_ts = release_utc_datetime(date_str)
    full_index = pd.date_range(
        baseline_ts - timedelta(minutes=PRE_MINUTES),
        baseline_ts + timedelta(minutes=POST_MINUTES),
        freq="1min",
    )
    closes = ohlc["close"].reindex(full_index).ffill()

    if baseline_ts not in ohlc.index or pd.isna(closes.loc[baseline_ts]):
        return None

    baseline_price = ohlc.loc[baseline_ts, "open"]
    minute_offsets = [(ts - baseline_ts).total_seconds() / 60 for ts in full_index]

    return pd.DataFrame({
        "発表日": date_str,
        "対象月": month_label,
        "分後": minute_offsets,
        "価格": closes.values,
        "値動き($)": closes.values - baseline_price,
    })


def main():
    os.makedirs("data", exist_ok=True)
    ledger = load_ledger()
    already_have = set(ledger["発表日"])

    event_frames = []
    for date_str, month_label, note in NFP_RELEASES:
        if date_str in already_have:
            event_frames.append(ledger[ledger["発表日"] == date_str])
            continue

        day = release_utc_datetime(date_str).date()
        ohlc = load_or_fetch_day(day)
        event_frame = build_event_frame(date_str, month_label, ohlc)
        if event_frame is None:
            print(f"[スキップ] {date_str} ({month_label}): 発表直後のtickデータなし - {note}")
            continue
        event_frames.append(event_frame)

    if not event_frames:
        print("有効なデータがありませんでした。")
        return

    all_events = pd.concat(event_frames, ignore_index=True)
    all_events.to_csv(LEDGER_PATH, index=False)

    summary = (
        all_events[all_events["分後"] == SUMMARY_HORIZON_MIN]
        .assign(abs_move=lambda d: d["値動き($)"].abs())
        [["発表日", "対象月", "値動き($)", "abs_move"]]
        .rename(columns={"abs_move": f"発表{SUMMARY_HORIZON_MIN}分後の値動き(絶対値,$)"})
    )
    pd.set_option("display.float_format", lambda v: f"{v:.2f}")
    print(summary.to_string(index=False))

    avg_move = summary[f"発表{SUMMARY_HORIZON_MIN}分後の値動き(絶対値,$)"].mean()
    print()
    print(f"発表日の件数: {len(summary)}件")
    print(f"発表{SUMMARY_HORIZON_MIN}分後までの値動き(絶対値)の平均: {avg_move:.2f} ドル "
          f"(中央値 {summary.iloc[:, -1].median():.2f} / 標準偏差 {summary.iloc[:, -1].std():.2f})")

    # --- グラフ1: 発表前後の値動きパス(1分刻み) ---
    fig, ax = plt.subplots(figsize=(11, 6))
    for date_str, group in all_events.groupby("発表日"):
        ax.plot(group["分後"], group["値動き($)"], color="#2a78d6", alpha=0.35, linewidth=1.5)

    mean_path = all_events.groupby("分後")["値動き($)"].mean()
    ax.plot(mean_path.index, mean_path.values, color="#eb6834", linewidth=2.5, label="平均パス")
    ax.axvline(0, color="#898781", linestyle="--", linewidth=1, label="発表(米東部時間8:30)")
    ax.axhline(0, color="#c3c2b7", linewidth=0.8)

    ax.set_title("米国雇用統計(NFP)発表前後のXAUUSD値動き(1分足・過去1年)")
    ax.set_xlabel("発表からの経過分")
    ax.set_ylabel("発表時点からの値動き(ドル)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#e1e0d9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend()
    plt.tight_layout()

    # --- グラフ2: 発表n分後の値動き(絶対値)を発表ごとに比較 ---
    fig2, ax2 = plt.subplots(figsize=(11, 6))
    labels = pd.to_datetime(summary["発表日"]).dt.strftime("%m/%d")
    values = summary[f"発表{SUMMARY_HORIZON_MIN}分後の値動き(絶対値,$)"]
    bars = ax2.bar(labels, values, color="#2a78d6", width=0.6)
    ax2.axhline(avg_move, color="#eb6834", linestyle="--", linewidth=2, label=f"平均 {avg_move:.0f}ドル")

    for bar, value in zip(bars, values):
        ax2.annotate(f"{value:.0f}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                     ha="center", va="bottom", fontsize=9, color="#0b0b0b")

    ax2.set_title(f"米国雇用統計(NFP)発表{SUMMARY_HORIZON_MIN}分後までのXAUUSD値動き(1分足・過去1年)")
    ax2.set_xlabel("発表日")
    ax2.set_ylabel("値動き(絶対値, ドル)")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.grid(axis="y", color="#e1e0d9", linewidth=0.8)
    ax2.set_axisbelow(True)
    ax2.legend()
    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()

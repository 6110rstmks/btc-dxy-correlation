"""
Analyze how much XAUUSD moves in the 1-minute timeframe immediately
after the U.S. Nonfarm Payrolls (NFP) announcement.

- yfinance provides only about 30 days of 1-minute data, so this script
  uses free historical tick data from Dukascopy to analyze NFP releases
  over the past year.
  Dukascopy: https://www.dukascopy.com/swiss/english/marketwatch/historical/

- Dukascopy tick files are organized by hour (00h-23h).
  Sending 24 requests simultaneously for a single day can easily trigger
  rate limits (HTTP 429). This script downloads data sequentially,
  with a short delay between requests.

- The midpoint price (mid = (ask + bid) / 2) is calculated from ticks
  and resampled into 1-minute OHLC candles.
  Daily data is cached in data/xauusd_m1/.
  Add new release dates to NFP_RELEASES and rerun the script to
  accumulate historical observations.

- The release time is 8:30 AM Eastern Time.
  The zoneinfo module automatically handles daylight saving time.
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

# Configure the font for English text.
plt.rcParams["font.family"] = "DejaVu Sans"

SYMBOL = "XAUUSD"

URL = (
    "https://datafeed.dukascopy.com/datafeed/"
    "{symbol}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
)

DATA_DIR = "data/xauusd_m1"
LEDGER_PATH = "data/nfp_1min_moves.csv"

HOUR_DELAY_SEC = 0.5
RETRY_ATTEMPTS = 6

PRE_MINUTES = 5
POST_MINUTES = 30
SUMMARY_HORIZON_MIN = 5


def fetch_hour_ticks(session, day, hour):
    """Download tick data for a specific hour."""

    url = URL.format(
        symbol=SYMBOL,
        year=day.year,
        month=day.month - 1,
        day=day.day,
        hour=hour,
    )

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

    print(f"[WARNING] Failed to download this hour. Skipping: {url}")
    return b""


def fetch_day_1min(day):
    """
    Download XAUUSD tick data for a UTC calendar date and return
    a DataFrame containing 1-minute OHLC midpoint prices.
    """

    session = requests.Session()
    all_ticks = []

    for hour in range(24):
        content = fetch_hour_ticks(session, day, hour)
        time.sleep(HOUR_DELAY_SEC)

        if not content:
            continue

        # decompress reconstructs tick timestamps assuming hour = 0.
        # The actual hour is added manually below.
        ticks = decompress(day, memoryview(bytearray(content)))

        for t, ask, bid, ask_vol, bid_vol in ticks:
            # The Duka normalization process assumes 5-decimal FX prices
            # and divides prices by 100000.
            # XAUUSD uses 2-decimal prices, so multiply by 100 to
            # restore the correct price scale.
            all_ticks.append(
                (
                    t + timedelta(hours=hour),
                    (ask + bid) / 2 * 100,
                )
            )

    if not all_ticks:
        return pd.DataFrame(
            columns=["open", "high", "low", "close"]
        )

    series = pd.Series(
        [mid for _, mid in all_ticks],
        index=pd.DatetimeIndex([t for t, _ in all_ticks]),
    ).sort_index()

    ohlc = series.resample("1min").ohlc()

    return ohlc


def load_or_fetch_day(day):
    """Load cached data or download it if the cache does not exist."""

    os.makedirs(DATA_DIR, exist_ok=True)

    cache_path = os.path.join(
        DATA_DIR,
        f"{day.isoformat()}.csv",
    )

    if os.path.exists(cache_path):
        return pd.read_csv(
            cache_path,
            index_col=0,
            parse_dates=True,
        )

    print(
        f"[DOWNLOADING] Fetching {SYMBOL} 1-minute data "
        f"from Dukascopy for {day}..."
    )

    ohlc = fetch_day_1min(day)
    ohlc.to_csv(cache_path)

    return ohlc


def release_utc_datetime(date_str):
    """Convert an NFP release date and Eastern release time to UTC."""

    hour, minute = RELEASE_TIME_ET
    y, m, d = (int(x) for x in date_str.split("-"))

    local = datetime(
        y,
        m,
        d,
        hour,
        minute,
        tzinfo=ZoneInfo("America/New_York"),
    )

    return local.astimezone(timezone.utc).replace(tzinfo=None)


def load_ledger():
    """Load previously collected event data."""

    if os.path.exists(LEDGER_PATH):
        return pd.read_csv(LEDGER_PATH)

    return pd.DataFrame(
        columns=[
            "Release Date",
            "Reference Month",
            "Minutes After Release",
            "Price",
            "Price Change ($)",
        ]
    )


def build_event_frame(date_str, month_label, ohlc):
    """
    Build a time series of price changes around an NFP announcement.
    """

    baseline_ts = release_utc_datetime(date_str)

    full_index = pd.date_range(
        baseline_ts - timedelta(minutes=PRE_MINUTES),
        baseline_ts + timedelta(minutes=POST_MINUTES),
        freq="1min",
    )

    closes = ohlc["close"].reindex(full_index).ffill()

    if (
        baseline_ts not in ohlc.index
        or pd.isna(closes.loc[baseline_ts])
    ):
        return None

    baseline_price = ohlc.loc[baseline_ts, "open"]

    minute_offsets = [
        (ts - baseline_ts).total_seconds() / 60
        for ts in full_index
    ]

    return pd.DataFrame(
        {
            "Release Date": date_str,
            "Reference Month": month_label,
            "Minutes After Release": minute_offsets,
            "Price": closes.values,
            "Price Change ($)": closes.values - baseline_price,
        }
    )


def main():
    os.makedirs("data", exist_ok=True)

    ledger = load_ledger()
    

    # Convert legacy Japanese column names to English.
    ledger = ledger.rename(columns={
        "発表日": "Release Date",
        "対象月": "Reference Month",
        "分後": "Minutes After Release",
        "価格": "Price",
        "値動き($)": "Price Change ($)",
    })


    already_have = set(ledger["Release Date"])

    event_frames = []

    for date_str, month_label, note in NFP_RELEASES:
        if date_str in already_have:
            event_frames.append(
                ledger[ledger["Release Date"] == date_str]
            )
            continue

        day = release_utc_datetime(date_str).date()
        ohlc = load_or_fetch_day(day)

        event_frame = build_event_frame(
            date_str,
            month_label,
            ohlc,
        )

        if event_frame is None:
            print(
                f"[SKIPPED] {date_str} ({month_label}): "
                f"No tick data available immediately after release. "
                f"Details: {note}"
            )
            continue

        event_frames.append(event_frame)

    if not event_frames:
        print("No valid data was found.")
        return

    all_events = pd.concat(
        event_frames,
        ignore_index=True,
    )

    all_events.to_csv(
        LEDGER_PATH,
        index=False,
    )

    summary = (
        all_events[
            all_events["Minutes After Release"]
            == SUMMARY_HORIZON_MIN
        ]
        .assign(
            abs_move=lambda d: d["Price Change ($)"].abs()
        )[
            [
                "Release Date",
                "Reference Month",
                "Price Change ($)",
                "abs_move",
            ]
        ]
        .rename(
            columns={
                "abs_move": (
                    f"Absolute Price Change After "
                    f"{SUMMARY_HORIZON_MIN} Minutes ($)"
                )
            }
        )
    )

    pd.set_option(
        "display.float_format",
        lambda v: f"{v:.2f}",
    )

    print(summary.to_string(index=False))

    summary_column = (
        f"Absolute Price Change After "
        f"{SUMMARY_HORIZON_MIN} Minutes ($)"
    )

    avg_move = summary[summary_column].mean()

    print()
    print(f"Number of release events: {len(summary)}")
    print(
        f"Average absolute price change within "
        f"{SUMMARY_HORIZON_MIN} minutes: "
        f"${avg_move:.2f} "
        f"(Median: ${summary[summary_column].median():.2f}, "
        f"Standard deviation: "
        f"${summary[summary_column].std():.2f})"
    )

    # Chart 1: Price movement before and after the announcement.

    fig, ax = plt.subplots(figsize=(11, 6))

    for date_str, group in all_events.groupby("Release Date"):
        ax.plot(
            group["Minutes After Release"],
            group["Price Change ($)"],
            color="#2a78d6",
            alpha=0.35,
            linewidth=1.5,
        )

    mean_path = all_events.groupby(
        "Minutes After Release"
    )["Price Change ($)"].mean()

    ax.plot(
        mean_path.index,
        mean_path.values,
        color="#eb6834",
        linewidth=2.5,
        label="Average Price Path",
    )

    ax.axvline(
        0,
        color="#898781",
        linestyle="--",
        linewidth=1,
        label="NFP Release (8:30 AM ET)",
    )

    ax.axhline(
        0,
        color="#c3c2b7",
        linewidth=0.8,
    )

    ax.set_title(
        "XAUUSD Price Movement Around NFP Releases "
        "(1-Minute Data, Past Year)"
    )
    ax.set_xlabel("Minutes Since Release")
    ax.set_ylabel("Price Change from Release-Time Price ($)")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.grid(
        axis="y",
        color="#e1e0d9",
        linewidth=0.8,
    )

    ax.set_axisbelow(True)
    ax.legend()
    plt.tight_layout()

    # Chart 2: Absolute price changes at the selected horizon.

    fig2, ax2 = plt.subplots(figsize=(11, 6))

    labels = pd.to_datetime(
        summary["Release Date"]
    ).dt.strftime("%m/%d")

    values = summary[summary_column]

    bars = ax2.bar(
        labels,
        values,
        color="#2a78d6",
        width=0.6,
    )

    ax2.axhline(
        avg_move,
        color="#eb6834",
        linestyle="--",
        linewidth=2,
        label=f"Average: ${avg_move:.0f}",
    )

    for bar, value in zip(bars, values):
        ax2.annotate(
            f"{value:.0f}",
            (
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
            ),
            ha="center",
            va="bottom",
            fontsize=9,
            color="#0b0b0b",
        )

    ax2.set_title(
        f"Absolute XAUUSD Price Change Within "
        f"{SUMMARY_HORIZON_MIN} Minutes of NFP Releases "
        f"(1-Minute Data, Past Year)"
    )

    ax2.set_xlabel("Release Date")
    ax2.set_ylabel("Absolute Price Change ($)")

    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    ax2.grid(
        axis="y",
        color="#e1e0d9",
        linewidth=0.8,
    )

    ax2.set_axisbelow(True)
    ax2.legend()
    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()

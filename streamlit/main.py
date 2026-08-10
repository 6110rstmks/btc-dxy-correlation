"""
Streamlit app: Verification of the Qiita article
"An Unexpected Fact: Bitcoin's Sharpe Ratio Has Outperformed the S&P 500"
https://qiita.com/tikeda123/items/a03a251da3ae8206044b

Run with:
    streamlit run app.py

Requirements:
    pip install streamlit yfinance pandas numpy matplotlib --break-system-packages
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import streamlit as st

# ---------------------------------------------------------
# Page config
# ---------------------------------------------------------
st.set_page_config(
    page_title="BTC vs S&P500 Sharpe Ratio",
    layout="wide",
)

st.title("₿ Bitcoin vs S&P500: Sharpe Ratio Verification")
st.caption(
    "Qiita記事「意外な事実：ビットコインのシャープレシオはS&P500を上回っていた」の検証 — "
    "[元記事](https://qiita.com/tikeda123/items/a03a251da3ae8206044b)"
)

st.markdown(
    """
記事の主張:
- BTCはS&P500を年次シャープレシオで多くの年で上回った
- 平均シャープレシオ: **BTC = 0.86** / **S&P500 = 0.65**

このアプリはYahoo Financeの実データを使って上記主張を再検証します。
"""
)

# ---------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------
st.sidebar.header("設定")

start_date = st.sidebar.date_input("開始日", pd.Timestamp("2018-01-01"))
end_date = st.sidebar.date_input("終了日", pd.Timestamp("2025-10-31"))
risk_free_rate = st.sidebar.number_input(
    "無リスク金利 (年率)", value=0.0, step=0.01, format="%.4f"
)

trading_days_btc = st.sidebar.number_input(
    "BTC年間取引日数", value=365, step=1
)
trading_days_sp500 = st.sidebar.number_input(
    "S&P500年間取引日数", value=252, step=1
)

run_button = st.sidebar.button("データを取得して計算", type="primary")


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def download_prices(ticker: str, start, end) -> pd.Series:
    data = yf.download(ticker, start=start, end=end, progress=False)["Close"]
    if isinstance(data, pd.DataFrame):
        data = data.squeeze("columns")
    return data


def annual_sharpe(daily_returns: pd.Series, trading_days: int, rf: float = 0.0) -> float:
    """Annualized Sharpe ratio from a series of daily (simple) returns."""
    daily_returns = pd.Series(daily_returns).astype(float)
    if daily_returns.empty:
        return np.nan

    mean_daily = float(daily_returns.mean())
    std_daily = float(daily_returns.std())

    annual_return = mean_daily * trading_days
    annual_vol = std_daily * np.sqrt(trading_days)

    if annual_vol == 0 or np.isnan(annual_vol):
        return np.nan

    return (annual_return - rf) / annual_vol


def compute_yearly_sharpe(btc_return, sp500_return, start_year, end_year):
    rows = []
    for year in range(start_year, end_year + 1):
        btc_y = btc_return[btc_return.index.year == year]
        sp500_y = sp500_return[sp500_return.index.year == year]

        rows.append(
            {
                "year": year,
                "BTC_calc": annual_sharpe(btc_y, trading_days_btc, risk_free_rate)
                if len(btc_y) > 0
                else np.nan,
                "SP500_calc": annual_sharpe(sp500_y, trading_days_sp500, risk_free_rate)
                if len(sp500_y) > 0
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------
# Main logic
# ---------------------------------------------------------
if run_button or "calc_df" not in st.session_state:
    with st.spinner("価格データをダウンロード中..."):
        try:
            btc = download_prices("BTC-USD", start_date, end_date)
            sp500 = download_prices("^GSPC", start_date, end_date)
        except Exception as e:
            st.error(f"データ取得に失敗しました: {e}")
            st.stop()

    if btc.empty or sp500.empty:
        st.error("価格データが空でした。日付範囲を確認してください。")
        st.stop()

    btc_return = btc.pct_change().dropna()
    sp500_return = sp500.pct_change().dropna()

    calc_df = compute_yearly_sharpe(
        btc_return, sp500_return, start_date.year, end_date.year
    )

    st.session_state["calc_df"] = calc_df
    st.session_state["btc"] = btc
    st.session_state["sp500"] = sp500

calc_df = st.session_state["calc_df"]

# ---------------------------------------------------------
# Results: table
# ---------------------------------------------------------
st.subheader("年次シャープレシオ（計算値）")
st.dataframe(
    calc_df.style.format({"BTC_calc": "{:.2f}", "SP500_calc": "{:.2f}"}),
    use_container_width=True,
)

btc_avg = calc_df["BTC_calc"].mean()
sp500_avg = calc_df["SP500_calc"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("BTC 平均 (計算値)", f"{btc_avg:.2f}")
col2.metric("BTC 平均 (記事の主張)", "0.86", delta=f"{btc_avg - 0.86:.2f}")
col3.metric("S&P500 平均 (計算値)", f"{sp500_avg:.2f}")
col4.metric("S&P500 平均 (記事の主張)", "0.65", delta=f"{sp500_avg - 0.65:.2f}")

# ---------------------------------------------------------
# Charts
# ---------------------------------------------------------
st.subheader("年次シャープレシオ比較")

chart_df = calc_df.set_index("year")[["BTC_calc", "SP500_calc"]]
chart_df.columns = ["BTC", "S&P 500"]
st.bar_chart(chart_df, color=["#f2a900", "#d62728"])

st.subheader("平均シャープレシオ（計算値 vs 記事の主張）")

avg_df = pd.DataFrame(
    {
        "計算値": [btc_avg, sp500_avg],
        "記事の主張": [0.86, 0.65],
    },
    index=["BTC", "S&P 500"],
)
st.bar_chart(avg_df.T, color=["#f2a900", "#d62728"])

# ---------------------------------------------------------
# Matplotlib version (optional, more custom styling)
# ---------------------------------------------------------
with st.expander("Matplotlibでのグラフ表示"):
    fig, axes = plt.subplots(2, 1, figsize=(11, 10))

    ax1 = axes[0]
    x = np.arange(len(calc_df))
    width = 0.35

    ax1.bar(x - width / 2, calc_df["BTC_calc"], width, label="BTC", color="#f2a900")
    ax1.bar(x + width / 2, calc_df["SP500_calc"], width, label="S&P 500", color="#d62728")
    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(calc_df["year"])
    ax1.set_ylabel("Sharpe Ratio")
    ax1.set_title("Annual Sharpe Ratio (Calculated)")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    ax2 = axes[1]
    labels = ["BTC", "S&P 500"]
    calc_avg = [btc_avg, sp500_avg]
    article_avg = [0.86, 0.65]
    x2 = np.arange(len(labels))

    ax2.bar(x2 - width / 2, calc_avg, width, label="Calculated", color="#2ca02c")
    ax2.bar(x2 + width / 2, article_avg, width, label="Article claim", color="#555555")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("Average Sharpe Ratio")
    ax2.set_title("Average Sharpe Ratio: Calculated vs Article Claim")
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    st.pyplot(fig)

st.caption(
    "注: 記事のシャープレシオ計算で用いられた無リスク金利の具体的な系列は公開されていないため、"
    "デフォルトでは無リスク金利=0として計算しています。サイドバーで調整可能です。"
)
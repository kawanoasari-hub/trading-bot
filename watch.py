import yfinance as yf
import numpy as np
import pandas as pd
import statsmodels.api as sm

from pair_state import PAIR_STATE, save_state


# =========================
# パラメータ
# =========================
LOOKBACK = 120

CORR_BREAKDOWN = 0.6
VOL_SPIKE_RATIO = 2.0
Z_EXTREME = 4.0


# =========================
# ティッカー取得
# =========================
def get_tickers():

    tickers = set()

    for k, v in PAIR_STATE.items():
        tickers.add(v["s1"])
        tickers.add(v["s2"])

    return list(tickers)


tickers = get_tickers()


# =========================
# データ取得
# =========================
print("Downloading watch data...")

data = yf.download(
    tickers,
    period="6mo",
    auto_adjust=True,
    progress=False
)["Close"]

data = data.ffill()


# =========================
# watch処理
# =========================
def run_watch():

    for pair_id, state in PAIR_STATE.items():

        s1 = state["s1"]
        s2 = state["s2"]

        try:
            p1 = data[s1].tail(LOOKBACK)
            p2 = data[s2].tail(LOOKBACK)
        except:
            continue

        if len(p1.dropna()) < LOOKBACK * 0.8:
            continue

        log1 = np.log(p1)
        log2 = np.log(p2)

        beta = state["beta"]

        spread = log1 - beta * log2

        # =========================
        # ① correlation breakdown
        # =========================
        corr = p1.corr(p2)

        if corr < CORR_BREAKDOWN:
            state["regime_risk"] = 3
            state["signal"] = "EXIT"
            continue

        # =========================
        # ② volatility spike
        # =========================
        vol_now = spread.tail(10).std()
        vol_prev = spread.std()

        if vol_prev > 0 and vol_now / vol_prev > VOL_SPIKE_RATIO:
            state["regime_risk"] = 3
            state["signal"] = "EXIT"
            continue

        # =========================
        # ③ beta drift（構造崩壊）
        # =========================
        try:
            beta_now = sm.OLS(log1, sm.add_constant(log2)).fit().params.iloc[1]

            beta_diff = abs(beta_now - beta)

            if beta > 0 and beta_diff / beta > 0.5:
                state["regime_risk"] = 3
                state["signal"] = "EXIT"
                continue

        except:
            pass

        # =========================
        # ④ z-score暴走
        # =========================
        std = spread.std()

        if std > 0:
            z = (spread.iloc[-1] - spread.mean()) / std

            state["zscore"] = float(z)

            if abs(z) > Z_EXTREME:
                state["regime_risk"] = 3
                state["signal"] = "EXIT"
                continue

        # =========================
        # 正常状態
        # =========================
        if state.get("regime_risk", 0) < 3:
            state["regime_risk"] = 0


    save_state(PAIR_STATE)

    print("watch updated:", len(PAIR_STATE))


# =========================
# 実行
# =========================
if __name__ == "__main__":
    run_watch()
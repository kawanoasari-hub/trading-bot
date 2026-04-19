import yfinance as yf
import numpy as np
import statsmodels.api as sm

from pair_state import PAIR_STATE, save_state


LOOKBACK = 120


def run_monitor():

    tickers = list(set([v["s1"] for v in PAIR_STATE.values()] +
                       [v["s2"] for v in PAIR_STATE.values()]))

    data = yf.download(
        tickers,
        period="6mo",
        auto_adjust=True,
        progress=False
    )["Close"].ffill()

    for pid, s in PAIR_STATE.items():

        p1 = data[s["s1"]].tail(LOOKBACK)
        p2 = data[s["s2"]].tail(LOOKBACK)

        log1 = np.log(p1)
        log2 = np.log(p2)

        beta = s["beta"]

        spread = log1 - beta * log2

        # =========================
        # z-score
        # =========================
        mean = spread.mean()
        std = spread.std()
        z = (spread.iloc[-1] - mean) / std

        # =========================
        # half-life簡易更新
        # =========================
        lag = spread.shift(1)
        delta = spread - lag
        df = np.column_stack([delta, lag]).astype(float)
        df = np.nan_to_num(df)

        try:
            beta_hl = sm.OLS(df[:,0], sm.add_constant(df[:,1])).fit().params[1]
            half_life = -np.log(2) / beta_hl if beta_hl < 0 else 999
        except:
            half_life = 999

        # =========================
        # スコア（本来版）
        # =========================
        score = (
            abs(z) * 2.0 +
            (1 / (half_life + 1)) * 10 +
            (0.7 if abs(z) > 1.5 else 0)
        )

        # =========================
        # リスク簡易評価（monitor側）
        # =========================
        vol = spread.std()
        risk = 1 if vol > spread.std() * 1.5 else 0

        # =========================
        # state更新
        # =========================
        s["zscore"] = float(z)
        s["score"] = float(score)
        s["half_life"] = float(half_life)
        s["regime_risk"] = int(risk)

        # 現在価格（PnL用）
        s["last_price1"] = float(p1.iloc[-1])
        s["last_price2"] = float(p2.iloc[-1])

        # シグナル
        if abs(z) > 1.5:
            s["signal"] = "ENTRY"
        elif abs(z) < 0.5:
            s["signal"] = "EXIT"
        else:
            s["signal"] = "HOLD"

    save_state(PAIR_STATE)


if __name__ == "__main__":
    run_monitor()
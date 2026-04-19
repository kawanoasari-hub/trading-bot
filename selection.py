import yfinance as yf
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint, adfuller
import itertools

from pair_state import PAIR_STATE, save_state


# =========================
# 株ティッカー（完全版）
# =========================
stock_tickers = [
"7203.T","7267.T","7269.T","7270.T","7211.T","7201.T",
"6501.T","6503.T","6506.T","6752.T","6758.T","6762.T","6857.T","6902.T","6954.T","6971.T",
"8035.T","7735.T","6920.T","6963.T","6723.T","6146.T",
"9432.T","9433.T","9434.T","9438.T",
"4689.T","4704.T","4755.T","4324.T","4307.T",
"8001.T","8002.T","8015.T","8031.T","8053.T","8058.T",
"8306.T","8316.T","8411.T","8331.T","8334.T","8354.T",
"8601.T","8604.T","8630.T","8725.T","8750.T","8766.T",
"5401.T","5411.T","5444.T","5406.T",
"5711.T","5713.T","5802.T","5803.T",
"4004.T","4005.T","4063.T","4188.T","4204.T","4452.T","3402.T","3407.T",
"4502.T","4503.T","4519.T","4523.T","4568.T","4578.T",
"6301.T","6302.T","6305.T","6326.T","6367.T","6471.T","6472.T",
"1801.T","1802.T","1803.T","1812.T","1925.T","1928.T",
"9101.T","9104.T","9107.T",
"1605.T","5020.T","5019.T","5021.T",
"3382.T","3092.T","8233.T","8252.T",
"2502.T","2503.T","2802.T","2871.T","2897.T",
"8801.T","8802.T","8830.T","3289.T",
"9064.T","9069.T","9142.T",
"5201.T","5202.T","5214.T",
"7731.T","7741.T","7762.T",
"4901.T","4911.T","5332.T","5333.T","6479.T","6586.T"
]


# =========================
# データ取得
# =========================
LOOKBACK = 120

print("Downloading data...")

data = yf.download(
    stock_tickers,
    period="1y",
    auto_adjust=True,
    progress=False
)["Close"]

data = data.ffill()
data = data.dropna(axis=1, thresh=int(len(data)*0.7))

print("Valid tickers:", len(data.columns))


# =========================
# ペア評価
# =========================
def evaluate_pair(s1, s2):

    p1 = data[s1].tail(LOOKBACK)
    p2 = data[s2].tail(LOOKBACK)

    if len(p1.dropna()) < 100:
        return None

    log1 = np.log(p1)
    log2 = np.log(p2)

    # cointegration
    _, pvalue, _ = coint(log1, log2)
    if pvalue > 0.05:
        return None

    # beta
    beta = sm.OLS(log1, sm.add_constant(log2)).fit().params.iloc[1]

    spread = log1 - beta * log2

    # ADF
    adf_p = adfuller(spread.dropna())[1]
    if adf_p > 0.1:
        return None

    # half-life
    lag = spread.shift(1)
    delta = spread - lag

    df = pd.concat([delta, lag], axis=1).dropna()

    beta_hl = sm.OLS(df.iloc[:, 0], sm.add_constant(df.iloc[:, 1])).fit().params.iloc[1]

    if beta_hl >= 0:
        return None

    half_life = -np.log(2) / beta_hl

    if not (3 < half_life < 40):
        return None

    return {
        "beta": beta,
        "half_life": half_life,
        "cointegration_p": pvalue,
        "adf_p": adf_p
    }


# =========================
# state登録
# =========================
def register_pair(s1, s2, metrics):

    pair_id = f"{s1}-{s2}"

    PAIR_STATE[pair_id] = {
        "s1": s1,
        "s2": s2,

        # selectionが作る情報
        "beta": metrics["beta"],
        "half_life": metrics["half_life"],
        "cointegration_p": metrics["cointegration_p"],
        "adf_p": metrics["adf_p"],

        # 初期値（後でmonitorが更新）
        "zscore": 0,
        "score": 0,
        "regime_risk": 0,
        "status": "WATCH"
    }


# =========================
# メイン
# =========================
def run_selection():

    pairs = list(itertools.combinations(data.columns, 2))

    print("total pairs:", len(pairs))

    count = 0

    for s1, s2 in pairs:

        metrics = evaluate_pair(s1, s2)

        if metrics is None:
            continue

        register_pair(s1, s2, metrics)
        count += 1

    save_state(PAIR_STATE)

    print("selected pairs:", count)


if __name__ == "__main__":
    run_selection()
import yfinance as yf
import numpy as np
import pandas as pd
import itertools
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint, adfuller
from collections import defaultdict

from trade_db import init_db, upsert_pair

# =========================
# ユニバース
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

etf_tickers = [
"1306.T","1348.T","1475.T","1346.T","1343.T",
"1321.T","1330.T","1570.T","1365.T","1357.T",
"1459.T","1360.T","1571.T","1568.T",
"1615.T","1628.T","1633.T","1617.T","1618.T","1619.T",
"1655.T","1658.T","1540.T","1545.T",
"2558.T","2568.T","2569.T","2516.T","2510.T",
"1489.T","1494.T","1482.T","1476.T",
"1320.T","1329.T","1364.T","1397.T",
"1345.T","1308.T","1305.T",
"1356.T","1358.T","1369.T",
"2631.T","2632.T","2644.T","2647.T",
"2860.T","2865.T","2840.T",
"2854.T","2855.T","2856.T",
"2557.T","2559.T"
]

UNIVERSE = list(set(stock_tickers + etf_tickers))

# =========================
# セクターマップ（完全維持）
# =========================
SECTOR_MAP = {

    "7203.T":"auto","7267.T":"auto","7269.T":"auto","7270.T":"auto",
    "7211.T":"auto","7201.T":"auto","6902.T":"auto",

    "8306.T":"financials","8316.T":"financials","8411.T":"financials",
    "8331.T":"financials","8334.T":"financials","8354.T":"financials",
    "8630.T":"financials","8725.T":"financials",
    "8750.T":"financials","8766.T":"financials",
    "8601.T":"financials","8604.T":"financials",

    "8001.T":"trading","8002.T":"trading","8015.T":"trading",
    "8031.T":"trading","8053.T":"trading","8058.T":"trading",
    "1605.T":"trading",

    "8035.T":"tech","6920.T":"tech","6963.T":"tech","6723.T":"tech",
    "6146.T":"tech","7735.T":"tech",
    "6501.T":"tech","6503.T":"tech","6506.T":"tech",
    "6752.T":"tech","6758.T":"tech","6762.T":"tech",
    "6857.T":"tech","6971.T":"tech",

    "9432.T":"internet","9433.T":"internet","9434.T":"internet","9438.T":"internet",
    "4689.T":"internet","4704.T":"internet","4755.T":"internet",
    "4324.T":"internet","4307.T":"internet",

    "4502.T":"pharma","4503.T":"pharma","4519.T":"pharma",
    "4523.T":"pharma","4568.T":"pharma","4578.T":"pharma",

    "3382.T":"consumer","3092.T":"consumer","8233.T":"consumer","8252.T":"consumer",
    "2502.T":"consumer","2503.T":"consumer","2802.T":"consumer",
    "2871.T":"consumer","2897.T":"consumer",

    "6301.T":"industrial","6302.T":"industrial","6305.T":"industrial",
    "6326.T":"industrial","6367.T":"industrial",
    "6471.T":"industrial","6472.T":"industrial",
    "7731.T":"industrial","7741.T":"industrial","7762.T":"industrial",
    "6586.T":"industrial",

    "4004.T":"materials","4005.T":"materials","4063.T":"materials",
    "4188.T":"materials","4204.T":"materials",
    "3402.T":"materials","3407.T":"materials",
    "5201.T":"materials","5202.T":"materials","5214.T":"materials",
    "5332.T":"materials","5333.T":"materials",
    "5401.T":"materials","5411.T":"materials","5444.T":"materials","5406.T":"materials",

    "5020.T":"energy","5019.T":"energy","5021.T":"energy",

    "1925.T":"realestate","1928.T":"realestate",
    "8801.T":"realestate","8802.T":"realestate","8830.T":"realestate",
    "3289.T":"realestate",
    "1801.T":"realestate","1802.T":"realestate","1803.T":"realestate","1812.T":"realestate",
}

# =========================
# セクター分割
# =========================
def group_by_sector(symbols):
    groups = defaultdict(list)
    for s in symbols:
        sector = SECTOR_MAP.get(s)
        if sector:
            groups[sector].append(s)
    return groups

LOOKBACK = 120

def evaluate_pair(s1, s2, data):

    p1 = data[s1].tail(LOOKBACK)
    p2 = data[s2].tail(LOOKBACK)

    if len(p1.dropna()) < 100:
        return None

    log1 = np.log(p1)
    log2 = np.log(p2)

    _, pvalue, _ = coint(log1, log2)
    if pvalue > 0.07:
        return None

    beta = sm.OLS(log1, sm.add_constant(log2)).fit().params.iloc[1]

    spread = log1 - beta * log2

    adf_p = adfuller(spread.dropna())[1]
    if adf_p > 0.13:
        return None

    half_life = 999
    try:
        lag = spread.shift(1)
        delta = spread - lag
        df = pd.concat([delta, lag], axis=1).dropna()
        beta_hl = sm.OLS(df.iloc[:,0], sm.add_constant(df.iloc[:,1])).fit().params[1]
        if beta_hl < 0:
            half_life = -np.log(2) / beta_hl
    except:
        return None

    if not (3 < half_life < 50):
        return None

    sector1 = SECTOR_MAP.get(s1, "unknown")
    sector2 = SECTOR_MAP.get(s2, "unknown")

    if sector1 != sector2:
        return None

    return {
        "beta": beta,
        "half_life": half_life,
        "spread_std": float(spread.std()),
        "sector": sector1
    }

# =========================
# DB登録（ここだけ修正）
# =========================
def insert_pair(pair_id, s1, s2, metrics):

    upsert_pair({
        "pair_id": pair_id,
        "s1": s1,
        "s2": s2,
        "sector": metrics["sector"],
        "beta": metrics["beta"],
        "half_life": metrics["half_life"],
        "spread_std": metrics["spread_std"],
        "status": "WATCH"
    })

# =========================
# main
# =========================
def run_selection():

    universe = UNIVERSE

    print("Downloading data...")

    data = yf.download(
        universe,
        period="1y",
        auto_adjust=True,
        progress=False
    )["Close"].ffill()

    data = data.dropna(axis=1, thresh=int(len(data)*0.7))

    sector_groups = group_by_sector(data.columns)

    pairs = []
    for stocks in sector_groups.values():
        pairs += list(itertools.combinations(stocks, 2))

    print("total pairs:", len(pairs))

    count = 0

    for s1, s2 in pairs:

        metrics = evaluate_pair(s1, s2, data)

        if metrics is None:
            continue

        pair_id = f"{s1}-{s2}"

        insert_pair(pair_id, s1, s2, metrics)

        count += 1

    print("selected pairs:", count)


if __name__ == "__main__":
    init_db()
    run_selection()
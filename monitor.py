import yfinance as yf
import numpy as np
import time

from trade_db import (
    init_db,
    get_open_positions,
    update_position_state,
    upsert_market_state
)

LOOKBACK = 60  # ←変更

# =========================
# キャッシュ
# =========================
_price_cache = None
_last_fetch = 0
CACHE_TTL = 0  # ←変更（キャッシュ無効）


def get_pairs(conn):
    c = conn.cursor()
    c.execute("""
    SELECT pair_id, s1, s2, beta, half_life, spread_std
    FROM pairs
    WHERE status='WATCH'
    """)
    return c.fetchall()


def get_price_data(tickers):
    global _price_cache, _last_fetch

    now = time.time()

    if _price_cache is not None and (now - _last_fetch) < CACHE_TTL:
        return _price_cache

    print("📥 downloading market data...")

    data = yf.download(
        tickers,
        period="1mo",   # ←変更
        interval="1h",  # ←変更
        auto_adjust=True,
        progress=False,
        threads=True
    )["Close"].ffill()

    _price_cache = data
    _last_fetch = now

    return data


def run_monitor():

    import sqlite3
    conn = sqlite3.connect("trades.db")

    pairs = get_pairs(conn)

    if not pairs:
        print("no pairs")
        return

    tickers = list(set([p[1] for p in pairs] + [p[2] for p in pairs]))

    data = get_price_data(tickers)

    open_positions = get_open_positions()

    print("monitor updated:", len(pairs))

    for pair_id, s1, s2, beta, hl, vol in pairs:

        try:
            if s1 not in data.columns or s2 not in data.columns:
                continue

            p1 = data[s1].tail(LOOKBACK)
            p2 = data[s2].tail(LOOKBACK)

            if len(p1.dropna()) < 50:
                continue

            log1 = np.log(p1)
            log2 = np.log(p2)

            spread = log1 - beta * log2

            std = spread.std()
            if std == 0:
                continue

            z = (spread.iloc[-1] - spread.mean()) / std

            p1_last = float(p1.iloc[-1])
            p2_last = float(p2.iloc[-1])

            target = next((r for r in open_positions if r[1] == pair_id), None)

            pnl = 0

            if target:
                entry_p1 = target[6]
                entry_p2 = target[7]
                qty1 = target[8]
                qty2 = target[9]

                pnl = (p1_last - entry_p1) * qty1 + (entry_p2 - p2_last) * qty2

            update_position_state(pair_id, p1_last, p2_last, pnl, z)

            upsert_market_state((
                pair_id, s1, s2,
                beta, hl, vol,
                p1_last, p2_last,
                z,
                None
            ))

        except Exception as e:
            print("error:", pair_id, e)
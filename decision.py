import numpy as np
import pandas as pd
import requests

from model import z_zone_score, mean_reversion_speed, expected_value
from pair_state import PAIR_STATE, save_state
from log import write_log
from position_db import open_position, close_position


TOKEN="8346759189:AAFVguKLUuJSXIdjTn-uXQevMEcu35Q-aGA"
CHAT_ID="7919205087"


def send_message(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})


def calc_pnl(s):
    if s.get("entry_price1") is None:
        return 0

    return (
        (s["last_price1"] - s["entry_price1"]) * s["qty1"]
        +
        (s["last_price2"] - s["entry_price2"]) * s["qty2"]
    )


def has_position(s):
    return (
        s.get("status") == "OPEN"
        and s.get("qty1", 0) > 0
        and s.get("qty2", 0) > 0
        and s.get("entry_price1") is not None
        and s.get("entry_price2") is not None
    )


def is_entry_signal(c):
    return (
        c["score"] >= 0.65 and
        abs(c["z"]) >= 1.2 and
        c["risk"] < 1
    )


def calc_position_size(s, max_notional=1_500_000):

    p1 = s["last_price1"]
    p2 = s["last_price2"]
    beta = abs(s.get("beta", 1))

    if p1 * 100 + p2 * 100 > max_notional:
        return 0, 0

    spread = s.get("spread_series", [])

    vol = np.std(spread[-20:]) if len(spread) >= 20 else 0.02
    vol_adj = min(3, 1 / (vol + 1e-6))

    w1, w2 = 1, beta
    total_w = w1 + w2

    alloc1 = max_notional * vol_adj * (w1 / total_w)
    alloc2 = max_notional * vol_adj * (w2 / total_w)

    qty1 = max(100, int(alloc1 / p1) // 100 * 100)
    qty2 = max(100, int(alloc2 / p2) // 100 * 100)

    while qty1 * p1 + qty2 * p2 > max_notional:
        if qty1 > qty2 and qty1 > 100:
            qty1 -= 100
        elif qty2 > 100:
            qty2 -= 100
        else:
            return 0, 0

    return qty1, qty2


def get_trade_direction(z):
    return "SHORT_1_LONG_2" if z > 0 else "LONG_1_SHORT_2"


def calc_score(s):
    z = s.get("zscore", 0)
    risk = s.get("regime_risk", 0)

    spread = s.get("spread_series", [])
    speed = mean_reversion_speed(pd.Series(spread)) if len(spread) >= 10 else 0.3

    return float(
        z_zone_score(z) * 0.4 +
        speed * 0.3 +
        expected_value(z, speed, risk) * 0.3
    )


def decide_all():

    entry_candidates = []
    exit_candidates = []

    for pair_id, s in PAIR_STATE.items():

        z = s.get("zscore", 0)
        risk = s.get("regime_risk", 0)

        score = calc_score(s)
        s["score"] = score

        if not has_position(s):
            entry_candidates.append({
                "pair": pair_id,
                "score": score,
                "z": z,
                "risk": risk,
                "state": s
            })
        else:
            if risk >= 2 or abs(z) < 0.4:
                exit_candidates.append({
                    "pair": pair_id,
                    "pnl": calc_pnl(s),
                    "z": z,
                    "state": s
                })

        write_log({"pair": pair_id, "z": z, "score": score})

    # ENTRY
    entry_candidates.sort(key=lambda x: x["score"], reverse=True)
    filtered = [c for c in entry_candidates if is_entry_signal(c)]

    msg = "🟢 ENTRY SIGNALS\n\n"

    for c in filtered[:3]:
        s = c["state"]

        qty1, qty2 = calc_position_size(s)
        if qty1 == 0:
            continue

        direction = get_trade_direction(c["z"])

        side1 = "BUY" if direction == "LONG_1_SHORT_2" else "SELL"
        side2 = "BUY" if direction == "SHORT_1_LONG_2" else "SELL"

        msg += (
            f"{c['pair']}\n"
            f"{s['s1']} → {side1} {qty1}株\n"
            f"{s['s2']} → {side2} {qty2}株\n\n"
            f"▶ コマンド（自由入力）\n"
            f"/entry {c['pair']} [p1] [p2] {qty1} {qty2}\n\n"
        )

    if not filtered:
        msg = "🟡 ENTRYなし"

    send_message(msg)

    # EXIT
    for c in exit_candidates[:3]:
        send_message(
            f"🔴 EXIT\n{c['pair']}\n"
            f"/exit {c['pair']}"
        )

    save_state(PAIR_STATE)


if __name__ == "__main__":
    decide_all()
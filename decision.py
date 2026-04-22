import sqlite3
from datetime import datetime

from trade_db import get_open_positions
from config import MAX_NOTIONAL
from telegram_bot import send_message


def get_market_state():

    conn = sqlite3.connect("trades.db")
    c = conn.cursor()

    c.execute("""
    SELECT pair_id, s1, s2,
           beta, half_life, spread_std,
           current_price1, current_price2,
           zscore_current
    FROM market_state
    """)

    rows = c.fetchall()
    conn.close()
    return rows


def has_position(pair_id):
    return any(r[1] == pair_id for r in get_open_positions())


def entry_condition(z, hl, vol):

    if abs(z) < 1.5:
        return False

    if abs(z) > 3.0:
        return False

    if hl > 50:
        return False

    if vol <= 0:
        return False

    return True


# =========================
# ロット計算（ボラ追加版）
# =========================
def calc_size(p1, p2, beta, spread_std):

    w1 = 1
    w2 = abs(beta)

    total = w1 + w2

    alloc1 = MAX_NOTIONAL * (w1 / total)
    alloc2 = MAX_NOTIONAL * (w2 / total)

    # ボラ補正
    vol = max(spread_std, 1e-6)
    vol_scale = 1 / vol
    vol_scale = max(0.5, min(vol_scale, 2.0))

    alloc1 *= vol_scale
    alloc2 *= vol_scale

    qty1 = max(100, int(alloc1 / p1) // 100 * 100)
    qty2 = max(100, int(alloc2 / p2) // 100 * 100)

    return qty1, qty2


def try_entries():

    states = get_market_state()

    candidates = []

    for row in states:

        pair_id, s1, s2, beta, hl, vol, p1, p2, z = row

        if has_position(pair_id):
            continue

        if not entry_condition(z, hl, vol):
            continue

        # スコア計算
        score = abs(z) - (hl / 40)

        candidates.append((score, row))

    # スコア順にソート
    candidates.sort(reverse=True, key=lambda x: x[0])

    # TOP3抽出
    top = candidates[:3]

    if not top:
        print("No entry")
        return

    msg = "🟢 *TOP 3 ENTRY SIGNALS*\n\n"

    for score, row in top:

        pair_id, s1, s2, beta, hl, vol, p1, p2, z = row

        qty1, qty2 = calc_size(p1, p2, beta, vol)

        # 売買方向
        if z < 0:
            direction = "LONG_SHORT"
            side1 = "🟢 BUY"
            side2 = "🔴 SELL"
        else:
            direction = "SHORT_LONG"
            side1 = "🔴 SELL"
            side2 = "🟢 BUY"

        msg += (
            f"📌 {pair_id}\n"
            f"Direction: {direction}\n"
            f"Score: {score:.3f}\n"
            f"Z-score: {z:.2f}\n"
            f"Half-life: {hl:.1f}\n"
            f"{side1} {s1}: {qty1} @ {p1:.1f}\n"
            f"{side2} {s2}: {qty2} @ {p2:.1f}\n\n"
        )

    msg += f"（全候補数: {len(candidates)}）"

    print(msg)
    send_message(msg)


def try_exits():

    states = get_market_state()
    state_map = {r[0]: r for r in states}

    positions = get_open_positions()

    for pos in positions:

        pair_id = pos[1]
        entry_time = pos[5]
        pnl = pos[12]

        if pair_id not in state_map:
            continue

        z = state_map[pair_id][8]

        try:
            entry_dt = datetime.fromisoformat(entry_time)
            hours = (datetime.now() - entry_dt).total_seconds() / 3600
        except:
            hours = 0

        # 平均回帰
        if abs(z) < 0.3:
            msg = (
                f"🔵 *EXIT候補 (Mean Revert)*\n"
                f"{pair_id}\n"
                f"PnL: {int(pnl):,}円\n"
                f"Z: {z:.2f}"
            )
            print(msg)
            send_message(msg)
            continue

        # 損切り
        if pnl < -MAX_NOTIONAL * 0.02:
            msg = (
                f"🔴 *STOP LOSS候補*\n"
                f"{pair_id}\n"
                f"PnL: {int(pnl):,}円"
            )
            print(msg)
            send_message(msg)
            continue

        # 時間切れ
        if hours > 48:
            msg = (
                f"⏰ *TIME EXIT候補*\n"
                f"{pair_id}\n"
                f"保有時間: {hours:.1f}h\n"
                f"PnL: {int(pnl):,}円"
            )
            print(msg)
            send_message(msg)
            continue
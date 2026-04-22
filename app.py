from fastapi import FastAPI
from trade_db import get_open_positions, open_position, close_position
from decision import try_entries, try_exits
from monitor import run_monitor

app = FastAPI()


@app.get("/")
def root():
    return {"msg": "trading bot running"}


# =========================
# 状態確認
# =========================
@app.get("/positions")
def positions():
    rows = get_open_positions()
    return rows


# =========================
# エントリー
# =========================
@app.post("/entry")
def entry(pair: str, p1: float, p2: float, q1: int, q2: int):

    s1, s2 = pair.split("-")

    open_position({
        "pair_id": pair,
        "s1": s1,
        "s2": s2,
        "direction": "MANUAL",
        "entry_price1": p1,
        "entry_price2": p2,
        "qty1": q1,
        "qty2": q2,
        "notional": p1*q1 + p2*q2
    })

    return {"status": "ok"}


# =========================
# EXIT（手動価格入力 + PnL再計算）
# =========================
@app.post("/exit")
def exit(pair: str, p1: float, p2: float):

    rows = get_open_positions()
    target = next((r for r in rows if r[1] == pair), None)

    if not target:
        return {"error": "no position"}

    entry_p1 = target[6]
    entry_p2 = target[7]
    qty1 = target[8]
    qty2 = target[9]

    # ★PnLをexit価格ベースで再計算（最小修正）
    pnl = (p1 - entry_p1) * qty1 + (entry_p2 - p2) * qty2

    close_position(
        pair_id=pair,
        exit_p1=p1,
        exit_p2=p2,
        pnl=pnl
    )

    return {"status": "closed"}


# =========================
# バッチ実行
# =========================
@app.post("/run")
def run():
    run_monitor()
    try_entries()
    try_exits()
    return {"status": "done"}
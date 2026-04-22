from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from trade_db import get_open_positions, open_position, close_position
from decision import try_entries, try_exits
from monitor import run_monitor

app = FastAPI()


# =========================
# UI
# =========================
@app.get("/", response_class=HTMLResponse)
def dashboard():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


# =========================
# 状態取得
# =========================
@app.get("/positions")
def positions():
    return get_open_positions()


# =========================
# バッチ実行（監視＋判定）
# =========================
@app.post("/run")
def run():
    run_monitor()
    try_entries()
    try_exits()
    return {"status": "done"}


# =========================
# ENTRY（UI）
# =========================
@app.post("/entry")
def entry(
    pair: str = Form(...),
    p1: float = Form(...),
    p2: float = Form(...),
    q1: int = Form(...),
    q2: int = Form(...)
):

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
        "notional": p1 * q1 + p2 * q2,
        "zscore_entry": 0
    })

    return {"status": "entry saved"}


# =========================
# EXIT（UI）
# =========================
@app.post("/exit")
def exit(
    pair: str = Form(...),
    p1: float = Form(...),
    p2: float = Form(...)
):

    rows = get_open_positions()
    target = next((r for r in rows if r[1] == pair), None)

    if not target:
        return {"error": "no position"}

    entry_p1 = target[6]
    entry_p2 = target[7]
    qty1 = target[8]
    qty2 = target[9]

    pnl = (p1 - entry_p1) * qty1 + (entry_p2 - p2) * qty2

    close_position(
        pair_id=pair,
        exit_p1=p1,
        exit_p2=p2,
        pnl=pnl
    )

    return {"status": "closed", "pnl": pnl}
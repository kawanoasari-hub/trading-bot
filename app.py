from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from trade_db import get_open_positions, open_position, close_position

app = FastAPI()


# =========================
# UI
# =========================
@app.get("/", response_class=HTMLResponse)
def dashboard():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


# =========================
# ポジション一覧
# =========================
@app.get("/positions")
def positions():
    return get_open_positions()


# =========================
# 監視・シグナル実行（安全化済み）
# =========================
@app.post("/run")
def run():

    try:
        # 遅延import（起動時クラッシュ防止）
        from monitor import run_monitor
        from decision import try_entries, try_exits

        run_monitor()
        try_entries()
        try_exits()

        return {
            "status": "done",
            "error": None
        }

    except Exception as e:

        # ★重要：Renderを落とさない
        return {
            "status": "error",
            "error": str(e)
        }


# =========================
# ENTRY（手動登録）
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

    return {
        "status": "entry saved",
        "pair": pair
    }


# =========================
# EXIT（手動決済）
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
        return {
            "status": "error",
            "error": "no position"
        }

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

    return {
        "status": "closed",
        "pair": pair,
        "pnl": pnl
    }
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from trade_db import (
    get_open_positions,
    get_all_positions,
    open_position,
    close_position,
    get_conn
)
from decision import try_entries, try_exits
from monitor import run_monitor
import os

app = FastAPI()

# =========================
# ログイン設定
# =========================
APP_PASSWORD = os.environ.get("APP_PASSWORD")
SESSION = {"logged_in": False}


def check_login():
    return SESSION.get("logged_in", False)


# =========================
# ログイン
# =========================
@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """
    <h1>Login</h1>
    <form method="post" action="/login">
        <input type="password" name="password">
        <button type="submit">Login</button>
    </form>
    """


@app.post("/login")
def login(password: str = Form(...)):
    if password == APP_PASSWORD:
        SESSION["logged_in"] = True
        return RedirectResponse("/", status_code=302)
    return HTMLResponse("wrong password", status_code=401)


# =========================
# ダッシュボード
# =========================
@app.get("/", response_class=HTMLResponse)
def dashboard():
    if not check_login():
        return RedirectResponse("/login")

    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


# =========================
# OPENポジション
# =========================
@app.get("/positions")
def positions():
    if not check_login():
        return {"error": "unauthorized"}
    return get_open_positions()


# =========================
# 全ポジション
# =========================
@app.get("/all_positions")
def all_positions():
    if not check_login():
        return {"error": "unauthorized"}
    return get_all_positions()


# =========================
# 監視＋シグナル
# =========================
@app.post("/run")
def run():
    if not check_login():
        return {"error": "unauthorized"}

    run_monitor()
    try_entries()
    try_exits()

    return {"status": "done"}


# =========================
# ENTRY
# =========================
@app.post("/entry")
def entry(
    pair: str = Form(...),
    p1: float = Form(...),
    p2: float = Form(...),
    q1: int = Form(...),
    q2: int = Form(...)
):
    if not check_login():
        return {"error": "unauthorized"}

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
# EXIT
# =========================
@app.post("/exit")
def exit(
    pair: str = Form(...),
    p1: float = Form(...),
    p2: float = Form(...)
):
    if not check_login():
        return {"error": "unauthorized"}

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


# =========================
# ★追加：パフォーマンス
# =========================
@app.get("/performance")
def performance():
    if not check_login():
        return {"error": "unauthorized"}

    rows = get_all_positions()

    total = 0
    win = 0
    lose = 0
    pnl_sum = 0

    monthly = {}

    for r in rows:
        if r[11] != "CLOSED":
            continue

        pnl = r[12]
        exit_date = r[16]

        if not exit_date:
            continue

        month = exit_date[:7]

        total += 1
        pnl_sum += pnl

        if pnl > 0:
            win += 1
        else:
            lose += 1

        monthly[month] = monthly.get(month, 0) + pnl

    if total == 0:
        return {"msg": "no trades"}

    return {
        "total": total,
        "win": win,
        "lose": lose,
        "win_rate": round(win / total * 100, 1),
        "total_pnl": pnl_sum,
        "avg_pnl": int(pnl_sum / total),
        "monthly": monthly
    }


# =========================
# ★追加：監視強制ON
# =========================
@app.post("/force_pairs_sync")
def force_pairs_sync():
    if not check_login():
        return {"error": "unauthorized"}

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    INSERT OR IGNORE INTO pairs (
        pair_id, s1, s2,
        beta, half_life, spread_std, status
    )
    SELECT
        pair_id, s1, s2,
        1, 10, 1, 'WATCH'
    FROM positions
    WHERE status='OPEN'
    """)

    conn.commit()
    conn.close()

    return {"status": "pairs synced"}
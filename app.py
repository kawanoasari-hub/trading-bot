from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from trade_db import get_open_positions, open_position, close_position
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
# ログイン画面
# =========================
@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """
    <h1>Login</h1>
    <form method="post" action="/login">
        <input type="password" name="password" placeholder="password">
        <button type="submit">Login</button>
    </form>
    """


@app.post("/login")
def login(password: str = Form(...)):
    if password == APP_PASSWORD:
        SESSION["logged_in"] = True
        return RedirectResponse("/", status_code=302)
    return HTMLResponse("wrong password", status_code=401)


@app.get("/logout")
def logout():
    SESSION["logged_in"] = False
    return RedirectResponse("/login", status_code=302)


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
# ポジション確認
# =========================
@app.get("/positions")
def positions():
    if not check_login():
        return {"error": "unauthorized"}

    return get_open_positions()


# =========================
# 監視＋シグナル実行
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
import requests
import time

from position_db import (
    init_db,
    get_open_positions,
    close_position
)

TOKEN = "YOUR_TOKEN"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

OFFSET = None


def send(msg):
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": "YOUR_CHAT_ID",
        "text": msg
    })


def handle(msg):

    text = msg.get("message", {}).get("text", "")

    # =========================
    # /status
    # =========================
    if text == "/status":

        rows = get_open_positions()

        if not rows:
            send("OPENポジションなし")
            return

        out = "📊 OPEN POSITIONS\n\n"
        for r in rows:
            out += f"{r[1]} | PnL:{r[10]}\n"

        send(out)

    # =========================
    # /close ALL（強制清算）
    # =========================
    elif text.startswith("/close"):

        rows = get_open_positions()

        for r in rows:
            pair = r[1]
            pnl = r[10]

            close_position(
                pair,
                pnl,
                r[5],
                r[6]
            )

        send("🔴 全ポジション強制クローズ")


def poll():

    global OFFSET

    url = f"{BASE_URL}/getUpdates"

    while True:

        params = {"timeout": 10}

        if OFFSET:
            params["offset"] = OFFSET

        res = requests.get(url, params=params).json()

        for update in res.get("result", []):

            OFFSET = update["update_id"] + 1
            handle(update)

        time.sleep(1)


if __name__ == "__main__":
    init_db()
    poll()
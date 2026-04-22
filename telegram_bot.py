import time
import requests

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from trade_db import (
    init_db,
    get_open_positions,
    close_position,
    open_position
)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


# =========================
# 送信（固定chat_id）
# =========================
def send_message(text):
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    })


# =========================
# コマンド処理
# =========================
def handle_command(text):

    parts = text.split()

    if not parts:
        return "コマンド空"

    cmd = parts[0]

    # =========================
    # /status
    # =========================
    if cmd == "/status":

        rows = get_open_positions()

        if not rows:
            return "OPENポジションなし"

        out = "📊 OPEN POSITIONS\n\n"

        for r in rows:
            pair = r[1]
            pnl = r[12]
            out += f"{pair} | PnL: {int(pnl):,}円\n"

        return out

    # =========================
    # /entry
    # =========================
    elif cmd == "/entry":

        if len(parts) != 6:
            return "形式: /entry ペア 価格1 価格2 数量1 数量2"

        pair = parts[1]

        try:
            price1 = float(parts[2])
            price2 = float(parts[3])
            qty1 = int(parts[4])
            qty2 = int(parts[5])
        except:
            return "数値エラー"

        if qty1 <= 0 or qty2 <= 0:
            return "数量エラー"

        if qty1 % 100 != 0 or qty2 % 100 != 0:
            return "100株単位にしてください"

        # 重複防止
        if any(r[1] == pair for r in get_open_positions()):
            return "すでにポジションあり"

        try:
            s1, s2 = pair.split("-")
        except:
            return "ペア形式エラー（例: 7203.T-7267.T）"

        notional = price1 * qty1 + price2 * qty2

        open_position({
            "pair_id": pair,
            "s1": s1,
            "s2": s2,
            "entry_price1": price1,
            "entry_price2": price2,
            "qty1": qty1,
            "qty2": qty2,
            "notional": notional,
            "zscore_entry": 0
        })

        return f"🟢 ENTRY登録: {pair}"

    # =========================
    # /exit（手動価格入力 + PnL再計算）
    # =========================
    elif cmd == "/exit":

        if len(parts) != 4:
            return "形式: /exit ペア 価格1 価格2"

        pair = parts[1]

        try:
            exit_p1 = float(parts[2])
            exit_p2 = float(parts[3])
        except:
            return "価格エラー"

        rows = get_open_positions()
        target = next((r for r in rows if r[1] == pair), None)

        if not target:
            return "ポジションなし"

        entry_p1 = target[6]
        entry_p2 = target[7]
        qty1 = target[8]
        qty2 = target[9]

        # ★PnL再計算（最小修正）
        pnl = (exit_p1 - entry_p1) * qty1 + (entry_p2 - exit_p2) * qty2

        close_position(
            pair_id=pair,
            exit_p1=exit_p1,
            exit_p2=exit_p2,
            pnl=pnl
        )

        return f"🔵 EXIT {pair} | PnL: {int(pnl):,}円"

    # =========================
    # /close
    # =========================
    elif cmd == "/close":

        rows = get_open_positions()

        if not rows:
            return "クローズ対象なし"

        for r in rows:
            close_position(
                pair_id=r[1],
                exit_p1=None,
                exit_p2=None,
                pnl=r[12]
            )

        return "🔴 全ポジション強制クローズ"

    # =========================
    # /help
    # =========================
    elif cmd == "/help":

        return (
            "/status\n"
            "/entry ペア 価格1 価格2 数量1 数量2\n"
            "/exit ペア 価格1 価格2\n"
            "/close"
        )

    return "不明コマンド"


# =========================
# polling
# =========================
def get_updates(offset=None):

    params = {"timeout": 30}
    if offset:
        params["offset"] = offset

    res = requests.get(f"{BASE_URL}/getUpdates", params=params)
    return res.json()


# =========================
# main
# =========================
def main():

    print("✅ Bot起動")

    init_db()

    offset = None

    while True:
        try:
            data = get_updates(offset)

            if "result" not in data:
                time.sleep(1)
                continue

            for update in data["result"]:

                offset = update["update_id"] + 1

                msg = update.get("message")
                if not msg or "text" not in msg:
                    continue

                text = msg["text"]

                response = handle_command(text)
                send_message(response)

        except Exception as e:
            print("エラー:", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
import time
import requests

from command_handler import handle_command
from trade_db import init_db

# ★ 自分のBotトークン
TOKEN="8346759189:AAFVguKLUuJSXIdjTn-uXQevMEcu35Q-aGA"


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })


def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 30}

    if offset:
        params["offset"] = offset

    res = requests.get(url, params=params)
    return res.json()


def main():
    print("✅ Telegram Bot 起動")

    # ★ 初回DB作成（超重要）
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

                if "message" not in update:
                    continue

                msg = update["message"]

                if "text" not in msg:
                    continue

                text = msg["text"]
                chat_id = msg["chat"]["id"]

                print(f"受信: {text}")

                # コマンド処理
                response = handle_command(text)

                print(f"返信: {response}")

                send_message(chat_id, response)

        except Exception as e:
            print("エラー:", e)
            time.sleep(3)


if __name__ == "__main__":
    main()

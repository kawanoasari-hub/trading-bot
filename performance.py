import requests
from trade_db import get_all_positions
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    res = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg
    })

    print(res.text)


rows = get_all_positions()

total_trades = 0
win_trades = 0
lose_trades = 0
total_pnl = 0

monthly = {}

for r in rows:

    status = r[11]

    if status != "CLOSED":
        continue

    pnl = r[12]
    exit_date = r[16]

    # ===== 安全化（ここだけ追加）=====
    if not exit_date or not isinstance(exit_date, str):
        continue
    # ==============================

    month = exit_date[:7]

    total_trades += 1
    total_pnl += pnl

    if pnl > 0:
        win_trades += 1
    else:
        lose_trades += 1

    if month not in monthly:
        monthly[month] = 0

    monthly[month] += pnl


if total_trades == 0:
    send("📊 決済なし")
    exit()

win_rate = win_trades / total_trades * 100
avg_pnl = total_pnl / total_trades

msg = "📈 運用成績\n"

msg += (
    f"\n総トレード数：{total_trades}"
    f"\n勝ち：{win_trades}"
    f"\n負け：{lose_trades}"
    f"\n勝率：{win_rate:.1f}%"
    f"\n総損益：{int(total_pnl):+,} 円"
    f"\n平均損益：{int(avg_pnl):+,} 円"
)

msg += "\n\n【月次】"

for m in sorted(monthly.keys()):
    msg += f"\n{m} : {int(monthly[m]):+,} 円"

send(msg)
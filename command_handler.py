from pair_state import PAIR_STATE, save_state
from trade_db import record_entry, record_exit, get_stats


def handle_command(text):

    parts = text.split()

    if len(parts) == 0:
        return "コマンド空"

    # =========================
    # ENTRY
    # =========================
    if parts[0] == "/entry":

        if len(parts) != 6:
            return "形式: /entry ペア 価格1 価格2 数量1 数量2"

        pair = parts[1]

        if pair not in PAIR_STATE:
            return "ペア存在しない"

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

        s = PAIR_STATE[pair]

        s["status"] = "OPEN"
        s["entry_price1"] = price1
        s["entry_price2"] = price2
        s["qty1"] = qty1
        s["qty2"] = qty2

        save_state(PAIR_STATE)

        # DB記録
        record_entry(pair, price1, price2, qty1, qty2)

        return f"ENTRY登録: {pair}"

    # =========================
    # EXIT
    # =========================
    elif parts[0] == "/exit":

        if len(parts) != 2:
            return "形式: /exit ペア"

        pair = parts[1]

        if pair not in PAIR_STATE:
            return "ペア存在しない"

        s = PAIR_STATE[pair]

        # PnL計算
        pnl = (
            (s["last_price1"] - s["entry_price1"]) * s["qty1"]
            +
            (s["last_price2"] - s["entry_price2"]) * s["qty2"]
        )

        # DB更新
        record_exit(pair, s["last_price1"], s["last_price2"], pnl)

        # リセット
        s["status"] = "CLOSED"
        s["qty1"] = 0
        s["qty2"] = 0
        s["entry_price1"] = None
        s["entry_price2"] = None

        save_state(PAIR_STATE)

        # 📊 統計取得
        total, wins, win_rate, avg_pnl = get_stats()

        return (
            f"EXIT登録: {pair}\n"
            f"PnL: {int(pnl):,}円\n\n"
            f"📊 トータル\n"
            f"回数: {total}\n"
            f"勝率: {win_rate:.1f}%\n"
            f"平均: {int(avg_pnl):,}円"
        )

    return "不明コマンド"
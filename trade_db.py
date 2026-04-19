import sqlite3
from datetime import datetime

DB_NAME = "trades.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pair TEXT,
        entry_time TEXT,
        exit_time TEXT,
        price1_entry REAL,
        price2_entry REAL,
        price1_exit REAL,
        price2_exit REAL,
        qty1 INTEGER,
        qty2 INTEGER,
        pnl REAL
    )
    """)

    conn.commit()
    conn.close()


# =========================
# ENTRY
# =========================
def record_entry(pair, price1, price2, qty1, qty2):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    INSERT INTO trades (
        pair, entry_time, price1_entry, price2_entry, qty1, qty2
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        pair,
        datetime.now().isoformat(),
        price1,
        price2,
        qty1,
        qty2
    ))

    conn.commit()
    conn.close()


# =========================
# EXIT
# =========================
def record_exit(pair, price1, price2, pnl):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    UPDATE trades
    SET exit_time = ?, price1_exit = ?, price2_exit = ?, pnl = ?
    WHERE pair = ? AND exit_time IS NULL
    """, (
        datetime.now().isoformat(),
        price1,
        price2,
        pnl,
        pair
    ))

    conn.commit()
    conn.close()


# =========================
# 統計
# =========================
def get_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 総トレード数
    c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL")
    total = c.fetchone()[0]

    # 勝ち数
    c.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0")
    wins = c.fetchone()[0]

    # 勝率
    win_rate = (wins / total * 100) if total > 0 else 0

    # 平均利益
    c.execute("SELECT AVG(pnl) FROM trades WHERE pnl IS NOT NULL")
    avg_pnl = c.fetchone()[0] or 0

    conn.close()

    return total, wins, win_rate, avg_pnl

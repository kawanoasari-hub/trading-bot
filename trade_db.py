import sqlite3
from datetime import datetime

DB_NAME = "trades.db"


def get_conn():
    return sqlite3.connect(DB_NAME)


# =========================
# init DB
# =========================
def init_db():

    conn = get_conn()
    c = conn.cursor()

    # pairs
    c.execute("""
    CREATE TABLE IF NOT EXISTS pairs (
        pair_id TEXT PRIMARY KEY,
        s1 TEXT,
        s2 TEXT,
        beta REAL,
        half_life REAL,
        spread_std REAL,
        status TEXT DEFAULT 'WATCH'
    )
    """)

    # positions
    c.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        position_id INTEGER PRIMARY KEY AUTOINCREMENT,
        pair_id TEXT,
        s1 TEXT,
        s2 TEXT,
        direction TEXT,
        entry_time TEXT,
        entry_price1 REAL,
        entry_price2 REAL,
        qty1 INTEGER,
        qty2 INTEGER,
        notional REAL,
        status TEXT DEFAULT 'OPEN',
        pnl REAL DEFAULT 0,
        zscore_entry REAL,
        exit_price1 REAL,
        exit_price2 REAL,
        exit_date TEXT,
        updated_at TEXT
    )
    """)

    # market_state
    c.execute("""
    CREATE TABLE IF NOT EXISTS market_state (
        pair_id TEXT PRIMARY KEY,
        s1 TEXT,
        s2 TEXT,
        beta REAL,
        half_life REAL,
        spread_std REAL,
        current_price1 REAL,
        current_price2 REAL,
        zscore_current REAL,
        updated_at TEXT
    )
    """)

    conn.commit()
    conn.close()


# =========================
# pairs UPSERT（←これが足りなかった）
# =========================
def upsert_pair(data):

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    INSERT OR REPLACE INTO pairs (
        pair_id, s1, s2,
        beta, half_life, spread_std,
        status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["pair_id"],
        data["s1"],
        data["s2"],
        data["beta"],
        data["half_life"],
        data["spread_std"],
        data.get("status", "WATCH")
    ))

    conn.commit()
    conn.close()


# =========================
# positions系
# =========================
def get_all_positions():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM positions")
    rows = c.fetchall()
    conn.close()
    return rows


def get_open_positions():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM positions WHERE status='OPEN'")
    rows = c.fetchall()
    conn.close()
    return rows


def open_position(data):

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    INSERT INTO positions (
        pair_id, s1, s2,
        direction,
        entry_time,
        entry_price1, entry_price2,
        qty1, qty2,
        notional,
        status,
        zscore_entry,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
    """, (
        data["pair_id"],
        data["s1"],
        data["s2"],
        data["direction"],
        datetime.now().isoformat(),
        data["entry_price1"],
        data["entry_price2"],
        data["qty1"],
        data["qty2"],
        data["notional"],
        data.get("zscore_entry", 0),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def update_position_state(pair_id, price1, price2, pnl, z):

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    UPDATE positions
    SET pnl = ?, updated_at = ?
    WHERE pair_id = ? AND status='OPEN'
    """, (
        pnl,
        datetime.now().isoformat(),
        pair_id
    ))

    conn.commit()
    conn.close()


def close_position(pair_id, exit_p1=None, exit_p2=None, pnl=0, exit_date=None):

    conn = get_conn()
    c = conn.cursor()

    if exit_date is None:
        exit_date = datetime.now().isoformat()

    c.execute("""
    UPDATE positions
    SET status='CLOSED',
        pnl=?,
        exit_price1=?,
        exit_price2=?,
        exit_date=?,
        updated_at=?
    WHERE pair_id=? AND status='OPEN'
    """, (
        pnl,
        exit_p1,
        exit_p2,
        exit_date,
        datetime.now().isoformat(),
        pair_id
    ))

    conn.commit()
    conn.close()


# =========================
# market_state
# =========================
def upsert_market_state(data):

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    INSERT OR REPLACE INTO market_state (
        pair_id, s1, s2,
        beta, half_life, spread_std,
        current_price1, current_price2,
        zscore_current,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    conn.close()
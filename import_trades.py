import json
import sqlite3
from datetime import datetime

conn = sqlite3.connect("trades.db")
c = conn.cursor()

with open("trades.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for t in data:

    pair_id = t["pair"].replace("_", "-")

    s1 = t["stock1"]
    s2 = t["stock2"]

    entry_p1 = t["entry_price1"]
    entry_p2 = t["entry_price2"]
    qty1 = t["qty1"]
    qty2 = t["qty2"]

    exit_p1 = t.get("exit_price1")
    exit_p2 = t.get("exit_price2")

    status = t["status"].upper()

    pnl = 0
    if status == "CLOSED" and exit_p1 and exit_p2:
        pnl = (exit_p1 - entry_p1) * qty1 + (entry_p2 - exit_p2) * qty2

    exit_date = t.get("exit_date")

    c.execute("""
    INSERT INTO positions (
        pair_id, s1, s2,
        direction,
        entry_time,
        entry_price1, entry_price2,
        qty1, qty2,
        notional,
        status,
        pnl,
        zscore_entry,
        exit_price1,
        exit_price2,
        exit_date,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pair_id,
        s1,
        s2,
        "IMPORT",
        datetime.now().isoformat(),
        entry_p1,
        entry_p2,
        qty1,
        qty2,
        entry_p1 * qty1 + entry_p2 * qty2,
        status,
        pnl,
        t.get("entry_z", 0),
        exit_p1,
        exit_p2,
        exit_date,
        datetime.now().isoformat()
    ))

conn.commit()
conn.close()

print("✅ import done")
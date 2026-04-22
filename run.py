import time
import monitor
import decision
from trade_db import get_conn

print("=================================")
print("🚀 PIPELINE START")
print("=================================")


def init():
    conn = get_conn()
    conn.close()


def run_pipeline(run_selection=False):

    init()

    if run_selection:
        print("selection running...")
        print("selection done")

    print("monitor running...")
    monitor.run_monitor()

    print("decision running...")
    decision.try_entries()
    decision.try_exits()


if __name__ == "__main__":
    try:
        run_pipeline(run_selection=False)
    except Exception as e:
        print("PIPELINE ERROR:", e)
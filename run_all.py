import watch
import monitor
import decision


def run_pipeline():

    print("watch updated...")
    watch.run_watch()

    print("monitor updated...")
    monitor.run_monitor()

    print("decision running...")
    decision.decide_all()   # ←ここ修正

    
if __name__ == "__main__":
    run_pipeline()
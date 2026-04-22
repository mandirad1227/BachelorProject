import time


def scenario_sync_test():
    print("here it's sync")
    a = time.time()
    time.sleep(5)
    print("Fin sync test")
    print("Fin sync", time.time() - a)

# ✅ Only launch the homing if the script is run directly
if __name__ == "__main__":
    scenario_sync_test()

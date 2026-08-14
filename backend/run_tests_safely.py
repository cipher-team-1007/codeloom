import sys
import traceback
from pathlib import Path

def run():
    try:
        print("Checking imports...")
        from engine.storage.sqlite_store import SQLiteStore
        from engine.api.app import app
        from engine.api.clusters import router
        from engine.api.fixes import router
        from engine.api.simulations import router
        print("Imports OK.")
        
        print("Running tests...")
        import subprocess
        result = subprocess.run([sys.executable, "tests/checkpoints/check_all.py"], capture_output=True, text=True)
        print("Return code:", result.returncode)
        print("STDOUT:")
        print(result.stdout)
        print("STDERR:")
        print(result.stderr)
        
    except Exception as e:
        print("Exception occurred:")
        traceback.print_exc()

if __name__ == "__main__":
    with open("test_results.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        sys.stderr = f
        run()

import sys
import traceback

try:
    from omega_kg.capture_server import app
    print("Import success")
except Exception as e:
    print(f"Import failed: {e}")
    traceback.print_exc()

import traceback

try:
    print("Import success")
except Exception as e:
    print(f"Import failed: {e}")
    traceback.print_exc()

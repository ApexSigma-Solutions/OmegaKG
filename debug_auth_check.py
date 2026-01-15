import sys
import os

# Ensure we can import from current directory
sys.path.insert(0, os.getcwd())

print("--- START DEBUG ---")
try:
    from omega_kg.settings import settings

    print("Settings imported.")
    print(f"DEBUG: settings.neo4j_password = {settings.neo4j_password}")
    print(f"DEBUG: os.getenv('NEO4J_PASSWORD') = {os.getenv('NEO4J_PASSWORD')}")
except Exception as e:
    print(f"Settings import failed: {e}")

try:
    from omega_kg.models.raw_storage import RawIngestion

    if RawIngestion:
        print(f"RawIngestion imported successfully: {RawIngestion}")
    else:
        print("RawIngestion is None")
except Exception as e:
    print(f"RawIngestion import failed: {e}")
print("--- END DEBUG ---")

import sys
import os

print("Debug script started")
print(f"Python version: {sys.version}")
print(f"CWD: {os.getcwd()}")

try:
    import fastapi
    print("FastAPI imported")
except ImportError as e:
    print(f"FastAPI import failed: {e}")

try:
    import httpx
    print("httpx imported")
except ImportError as e:
    print(f"httpx import failed: {e}")

try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.api import app
    print("src.api imported successfully")
except Exception as e:
    print(f"src.api import failed: {e}")
    import traceback
    traceback.print_exc()

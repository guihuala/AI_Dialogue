import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_memory_operations():
    print("=== Testing Memory Storage (CRUD) ===")
    
    # 1. Add a Memory
    print("\n[1] Adding Test Memory...")
    timestamp = int(time.time())
    test_content = f"Test Memory {timestamp}: The backend storage is working."
    
    payload = {
        "content": test_content,
        "type": "test_log",
        "importance": 5
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/memories", json=payload)
        if resp.status_code == 200:
            print(f"✅ Add Success: {resp.json()}")
        else:
            print(f"❌ Add Failed: {resp.status_code} - {resp.text}")
            return
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("Ensure the server is running on port 8000.")
        return

    # 2. Search for the Memory
    print("\n[2] Verifying Retrieval...")
    search_payload = {
        "query": f"Test Memory {timestamp}",
        "limit": 3
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/memories/search", json=search_payload)
        if resp.status_code == 200:
            results = resp.json()
            found = False
            for mem in results:
                if test_content in mem.get('content', ''):
                    found = True
                    print(f"✅ Found Memory: {mem['content']}")
                    # Store ID for cleanup if we wanted to delete it (optional)
            
            if not found:
                print("❌ Memory not found in search results.")
                print("Results returned:", results)
        else:
            print(f"❌ Search Failed: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_memory_operations()

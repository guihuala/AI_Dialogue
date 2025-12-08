import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_multisave():
    print("=== Testing Multi-Save Isolation ===")
    
    session_a = "slot_test_A"
    session_b = "slot_test_B"
    
    headers_a = {"X-Session-ID": session_a}
    headers_b = {"X-Session-ID": session_b}
    
    # 1. Add Memory to Slot A
    print(f"\n[1] Adding Memory to {session_a}...")
    mem_a = f"Memory A only: {int(time.time())}"
    requests.post(f"{BASE_URL}/memories", json={"content": mem_a}, headers=headers_a)
    
    # 2. Add Memory to Slot B
    print(f"[2] Adding Memory to {session_b}...")
    mem_b = f"Memory B only: {int(time.time())}"
    requests.post(f"{BASE_URL}/memories", json={"content": mem_b}, headers=headers_b)
    
    # 3. Verify Slot A sees A but NOT B
    print(f"[3] Verifying {session_a}...")
    resp_a = requests.post(f"{BASE_URL}/memories/search", json={"query": "Memory"}, headers=headers_a).json()
    
    found_a = any(mem_a in m['content'] for m in resp_a)
    found_b_in_a = any(mem_b in m['content'] for m in resp_a)
    
    if found_a and not found_b_in_a:
        print(f"✅ {session_a} is isolated correctly.")
    else:
        print(f"❌ {session_a} failed isolation test!")
        print(f"   Found A: {found_a}, Found B in A: {found_b_in_a}")

    # 4. Verify Slot B sees B but NOT A
    print(f"[4] Verifying {session_b}...")
    resp_b = requests.post(f"{BASE_URL}/memories/search", json={"query": "Memory"}, headers=headers_b).json()
    
    found_b = any(mem_b in m['content'] for m in resp_b)
    found_a_in_b = any(mem_a in m['content'] for m in resp_b)
    
    if found_b and not found_a_in_b:
        print(f"✅ {session_b} is isolated correctly.")
    else:
        print(f"❌ {session_b} failed isolation test!")
        print(f"   Found B: {found_b}, Found A in B: {found_a_in_b}")

if __name__ == "__main__":
    test_multisave()

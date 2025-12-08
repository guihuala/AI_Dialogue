import requests
import json
import random
import os
import sys

# Add project root to sys.path to allow importing if needed, 
# but here we just need to read the json file.
# Assuming this script is run from project root or Server/ directory.

def get_candidates():
    # Try to find candidates.json
    paths = [
        "Server/data/candidates.json",
        "data/candidates.json",
        "../data/candidates.json"
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
    print("Error: Could not find candidates.json")
    sys.exit(1)

def run_test():
    candidates_data = get_candidates()
    # Handle list or dict format
    if isinstance(candidates_data, list):
        candidates = candidates_data
    else:
        candidates = candidates_data.get("candidates", [])

    if len(candidates) < 3:
        print("Not enough candidates to select 3.")
        return

    selected = random.sample(candidates, 3)
    print(f"Selected Roommates: {[c['name'] for c in selected]}")

    # Construct the initial Game State (Context)
    # This mimics what GameDirector.cs sends to the server
    roommate_info = "\n".join([f"- {c['name']} ({c['id']}): {c.get('core_prompt', '')}" for c in selected])
    
    context = f"""
Current State:
- Day: 1
- Time: Morning
- Money: 1500
- Sanity: 100
- GPA: 4.0

Selected Roommates:
{roommate_info}

Event:
Game Start. The player has just moved into the dorm.
"""

    url = "http://localhost:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "gpt-3.5-turbo", # Or whatever model is configured
        "messages": [
            {"role": "system", "content": context},
            {"role": "user", "content": "Start the game."}
        ],
        "stream": True
    }

    print("\nSending request to backend...")
    try:
        response = requests.post(url, headers=headers, json=data, stream=True)
        if response.status_code == 200:
            print("\nAI Response:")
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        json_str = decoded_line[6:]
                        if json_str != "[DONE]":
                            try:
                                chunk = json.loads(json_str)
                                content = chunk['choices'][0]['delta'].get('content', '')
                                print(content, end='', flush=True)
                            except:
                                pass
            print("\n\nTest Finished.")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    run_test()

import requests
import json
import sys

print("Starting test script...", flush=True)

url = "http://localhost:8000/v1/chat/completions"
headers = {"Content-Type": "application/json"}
data = {
    "model": "gpt-3.5-turbo",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, who are you?"}
    ],
    "stream": True
}

print(f"Testing {url}...")
try:
    response = requests.post(url, headers=headers, json=data, stream=True)
    if response.status_code == 200:
        print("Response stream:")
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
        print("\n\nTest Passed!")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Connection failed: {e}")

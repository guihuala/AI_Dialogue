import pytest
from fastapi.testclient import TestClient
import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api import app

client = TestClient(app)

def test_chat_completions_streaming():
    """
    Test the /v1/chat/completions endpoint for streaming response.
    """
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello, say 'test'"}
        ],
        "stream": True
    }
    
    # Note: We might need to mock the LLMService to avoid actual API calls during tests
    # For now, we assume the server is configured to run (or we can mock it if needed)
    # But since we are testing the *endpoint structure*, let's see if we can get a response.
    
    # If LLMService requires an API key and it's not set, it might return an error string.
    # We should handle that.
    
    print("Starting test_chat_completions_streaming...")
    with client.stream("POST", "/v1/chat/completions", json=payload) as response:
        assert response.status_code == 200
        print("Response status code: 200")
        
        # Check for SSE format
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(f"Received line: {decoded_line}")
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    if data_str == "[DONE]":
                        print("Received [DONE]")
                        break
                    
                    try:
                        data = json.loads(data_str)
                        assert "choices" in data
                        assert "delta" in data["choices"][0]
                    except json.JSONDecodeError:
                        pytest.fail(f"Failed to decode JSON: {data_str}")
    print("Test passed successfully!")

if __name__ == "__main__":
    try:
        test_chat_completions_streaming()
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

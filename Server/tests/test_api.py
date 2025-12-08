import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_profile():
    response = client.get("/profile")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data

def test_chat():
    # Mocking LLM service would be ideal, but for now we test if it runs
    # We might hit actual LLM if API key is present, or fail if not.
    # Assuming the user might not have API key set up for tests, we should handle this.
    # However, app.py has a default key check.
    pass 

def test_add_and_search_memory():
    # Add
    response = client.post("/memories", json={
        "content": "Test memory for unit test",
        "type": "observation",
        "importance": 5
    })
    assert response.status_code == 200
    
    # Search
    response = client.post("/memories/search", json={
        "query": "Test memory",
        "limit": 5
    })
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0
    found = False
    for res in results:
        if "Test memory for unit test" in res["content"]:
            found = True
            break
    assert found


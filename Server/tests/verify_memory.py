import sys
import os

# Ensure we can import from src
sys.path.append(os.getcwd())

from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService

def test_backend():
    print("Initializing MemoryManager...")
    # Use a dummy LLM service for testing to avoid API key requirement
    class DummyLLM(LLMService):
        def generate_response(self, system, user, context):
            return "This is a dummy response."
    
    os.makedirs("data_test", exist_ok=True)
    mm = MemoryManager("data_test/profile.json", "data_test/chroma_db", DummyLLM(api_key="dummy"))
    
    print("Adding memory...")
    mm.add_memory("The user likes apples.", type="observation")
    
    print("Retrieving memory...")
    results = mm.vector_store.search("What does the user like?", n_results=1)
    
    if results and "apples" in results[0]['content']:
        print("SUCCESS: Memory retrieved correctly.")
        print(f"Retrieved: {results[0]['content']}")
    else:
        print("FAILURE: Could not retrieve memory.")
        print(f"Results: {results}")

if __name__ == "__main__":
    test_backend()

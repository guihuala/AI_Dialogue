import sys
import os
from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService

# Setup Paths
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")
profile_path = os.path.join(data_dir, "profile.json")
vector_db_path = os.path.join(data_dir, "chroma_db")

print(f"Checking Vector DB at: {vector_db_path}")

try:
    llm_service = LLMService()
    mm = MemoryManager(profile_path, vector_db_path, llm_service)
    
    # 1. Peek at all memories
    print("\n--- All Memories (Peek 10) ---")
    # Access collection directly if possible, or use search with generic query
    # Since we can't easily peek via MemoryManager, we'll use the underlying vector_store
    count = mm.vector_store.collection.count()
    print(f"Total Memories: {count}")
    
    if count > 0:
        peek = mm.vector_store.collection.peek(limit=10)
        ids = peek['ids']
        metadatas = peek['metadatas']
        documents = peek['documents']
        
        for i, id in enumerate(ids):
            meta = metadatas[i]
            print(f"[{i}] ID: {id} | Type: {meta.get('type')} | Content: {documents[i][:50]}...")

    # 2. Search specifically for daily logs
    print("\n--- Filtering for type='daily_log' ---")
    results = mm.vector_store.collection.get(where={"type": "daily_log"})
    if results['ids']:
        for i, id in enumerate(results['ids']):
            print(f"ID: {id} | Content: {results['metadatas'][i].get('original_content')[:50]}...")
    else:
        print("No daily_log items found.")

except Exception as e:
    print(f"Error: {e}")

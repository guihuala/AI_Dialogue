import sys
import os
import uuid
from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
from src.models.schema import MemoryItem

# Setup Paths
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")
profile_path = os.path.join(data_dir, "profile.json")
vector_db_path = os.path.join(data_dir, "chroma_db")

print(f"Migrating logs from: {profile_path}")

try:
    llm_service = LLMService()
    mm = MemoryManager(profile_path, vector_db_path, llm_service)
    
    logs = mm.profile.daily_log
    print(f"Found {len(logs)} daily logs.")
    
    memories_to_add = []
    for log in logs:
        # Check if already exists (naive check, or just overwrite/add)
        # Since we don't track the vector ID in the log, we'll just add them.
        # Duplicates might be an issue if we run this multiple times, but for now it's fine.
        
        content = f"Daily Log ({log.timestamp.strftime('%Y-%m-%d')}): {log.activity}. Interacted with: {', '.join(log.interacted_with)}"
        
        mem = MemoryItem(
            id=str(uuid.uuid4()),
            type="daily_log",
            content=content,
            importance=8,
            summary=log.activity
        )
        memories_to_add.append(mem)
        print(f"Prepared log: {log.activity[:30]}...")
        
    if memories_to_add:
        mm.vector_store.add_memories(memories_to_add)
        print(f"Successfully added {len(memories_to_add)} logs to Vector Store.")
    else:
        print("No logs to add.")

except Exception as e:
    print(f"Error: {e}")

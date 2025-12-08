import sys
import os
from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService

# Setup Paths
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")
profile_path = os.path.join(data_dir, "profile.json")
vector_db_path = os.path.join(data_dir, "chroma_db")

print(f"Loading profile from: {profile_path}")

try:
    llm_service = LLMService()
    mm = MemoryManager(profile_path, vector_db_path, llm_service)
    
    print(f"Profile Name: {mm.profile.name}")
    print(f"Daily Log Count: {len(mm.profile.daily_log)}")
    for log in mm.profile.daily_log:
        print(f" - {log.timestamp}: {log.activity}")
        
except Exception as e:
    print(f"Error loading profile: {e}")

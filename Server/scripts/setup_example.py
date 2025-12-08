import os
import sys
import shutil
import uuid

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
from src.models.schema import MemoryItem

def setup_example():
    print("🚀 Setting up example data...")
    
    # 1. Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # 2. Copy profile
    src_profile = "examples/profile.json"
    dst_profile = "data/profile.json"
    
    if os.path.exists(src_profile):
        shutil.copy(src_profile, dst_profile)
        print(f"✅ Copied {src_profile} to {dst_profile}")
    else:
        print(f"❌ Could not find {src_profile}")
        return

    # 3. Initialize Memory Manager
    # We need a dummy API key if not set, just to initialize the service, 
    # but we won't call the LLM here, just vector store.
    os.environ["OPENROUTER_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "sk-dummy")
    
    llm_service = LLMService()
    mm = MemoryManager(dst_profile, "data/chroma_db", llm_service)
    
    # 4. Seed Memories
    memories = [
        ("The Iron King's soldiers were seen near the river today.", "observation", 7),
        ("I feel the ley lines weakening. Something is draining them.", "thought", 9),
        ("Healed a wounded fox found in a trap.", "action", 5),
        ("Remembered the teachings of Elder Thorne: 'Nature endures, but it remembers.'", "thought", 8),
        ("A traveler passed by, asking for directions to the capital. I pointed them away from the danger.", "action", 4)
    ]
    
    print("💾 Seeding memories...")
    for content, m_type, importance in memories:
        # Check if already exists to avoid duplicates on re-run (simple check)
        existing = mm.vector_store.search(content, n_results=1)
        if existing and existing[0]['distance'] < 0.1:
            print(f"  - Skipping: {content[:30]}...")
            continue
            
        mm.add_memory(content, type=m_type, importance=importance)
        print(f"  + Added: {content[:30]}...")
        
    print("\n✨ Setup complete! You can now run the app or API.")

if __name__ == "__main__":
    setup_example()

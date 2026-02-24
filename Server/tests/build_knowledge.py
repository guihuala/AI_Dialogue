import sys
import os
import csv
import uuid

# 确保能找到 src 目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
from src.models.schema import MemoryItem

def build_knowledge():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    csv_path = os.path.join(data_dir, "lore.csv")
    
    if not os.path.exists(csv_path):
        print(f"❌ 找不到语料文件: {csv_path}，请确保在 data 目录下创建了该文件。")
        return

    mm = MemoryManager(
        profile_path=os.path.join(data_dir, "profile.json"), 
        vector_db_path=os.path.join(data_dir, "chroma_db"), 
        llm_service=LLMService()
    )

    # 1. 清理旧版本的“残次品语料”
    existing_data = mm.vector_store.collection.get()
    if existing_data and existing_data['ids']:
        ids_to_delete = [
            existing_data['ids'][i] 
            for i, meta in enumerate(existing_data['metadatas']) 
            if meta and meta.get("type") == "lore"
        ]
        if ids_to_delete:
            mm.vector_store.collection.delete(ids=ids_to_delete)
            print(f"🔄 已自动清理 {len(ids_to_delete)} 条旧数据...")

    # 2. 注入高精度的新语料
    memories_to_add = []
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            char_name = row.get("角色", "").strip()
            topic = row.get("场景标签", "").strip()
            quote = row.get("经典台词", "").strip()
            
            if not char_name or not quote: 
                continue
            
            # 组装完整的文本
            content = f"[{char_name}的专属语录] 场景({topic}): “{quote}”"
            
            mem = MemoryItem(
                id=str(uuid.uuid4()),
                type="lore", 
                content=content,
                importance=10,
                summary="" 
            )
            memories_to_add.append(mem)
            
    if memories_to_add:
        mm.vector_store.add_memories(memories_to_add)
        print(f"✅ 成功从 lore.csv 加载并注入了 {len(memories_to_add)} 条最新角色语料！")

if __name__ == "__main__":
    build_knowledge()
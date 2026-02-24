import sys
import os
import csv
import uuid

# 确保能找到 src 目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
from src.models.schema import MemoryItem

def build_lore_database():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    csv_path = os.path.join(data_dir, "lore.csv")
    
    if not os.path.exists(csv_path):
        print(f"找不到语料文件: {csv_path}")
        return

    mm = MemoryManager(
        profile_path=os.path.join(data_dir, "profile.json"), 
        vector_db_path=os.path.join(data_dir, "chroma_db"), 
        llm_service=LLMService()
    )

    memories_to_add = []
    
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            char_name = row.get("角色", "").strip()
            topic = row.get("场景标签", "").strip()
            quote = row.get("经典台词", "").strip()
            
            if not char_name or not quote: continue
            
            # 格式化存入的内容，带上角色名，方便精确检索
            content = f"[{char_name}的专属语录] 场景({topic}): “{quote}”"
            
            mem = MemoryItem(
                id=str(uuid.uuid4()),
                type="lore", # 标记为语料类型
                content=content,
                importance=10, # 给予最高权重
                summary=f"{char_name}的台词风格"
            )
            memories_to_add.append(mem)

    if memories_to_add:
        mm.vector_store.add_memories(memories_to_add)
        print(f"成功将 {len(memories_to_add)} 条专属台词注入 AI 数据库！")

if __name__ == "__main__":
    build_lore_database()
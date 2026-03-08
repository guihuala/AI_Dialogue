import sys
import os
import csv
import uuid
import pandas as pd

current_dir = os.path.abspath(os.path.dirname(__file__))
while current_dir != os.path.dirname(current_dir):
    if os.path.exists(os.path.join(current_dir, "src", "core")):
        PROJECT_ROOT = current_dir
        break
    current_dir = os.path.dirname(current_dir)
else:
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# 确保能找到 src 目录
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
    
from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
from src.models.schema import MemoryItem

def build_knowledge():
    data_dir = os.path.join(PROJECT_ROOT, "data")
    lores_dir = os.path.join(data_dir, "lores")
    old_lore_path = os.path.join(data_dir, "lore.csv")
    
    os.makedirs(lores_dir, exist_ok=True)
    
    # 自动迁移旧数据：如果发现旧的 lore.csv，自动将它按角色拆分成独立文件
    if os.path.exists(old_lore_path):
        try:
            df = pd.read_csv(old_lore_path)
            for char, group in df.groupby("角色"):
                char = str(char).strip()
                new_path = os.path.join(lores_dir, f"{char}.csv")
                # 提取需要的两列
                sub_df = group[["场景标签", "经典台词"]].copy()
                # 如果新文件已存在，则追加并去重
                if os.path.exists(new_path):
                    existing = pd.read_csv(new_path)
                    sub_df = pd.concat([existing, sub_df]).drop_duplicates()
                sub_df.to_csv(new_path, index=False, encoding='utf-8-sig')
            
            # 将旧文件重命名为备份，防止下次重复迁移
            os.rename(old_lore_path, old_lore_path + ".bak")
            print(f"✅ 旧版 lore.csv 已成功按角色拆分并迁移至 {lores_dir} 目录！")
        except Exception as e:
            print(f"⚠️ 旧版语料迁移失败: {e}")

    mm = MemoryManager(
        profile_path=os.path.join(data_dir, "profile.json"), 
        vector_db_path=os.path.join(data_dir, "chroma_db"), 
        llm_service=LLMService()
    )

    # 1. 清理向量库里旧版本的语料
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

    # 2. 遍历所有的角色独立 CSV 文件，注入高精度新语料
    memories_to_add = []
    
    for filename in os.listdir(lores_dir):
        if not filename.endswith(".csv"): continue
        
        # 文件名就是角色名
        char_name = filename.replace(".csv", "")
        file_path = os.path.join(lores_dir, filename)
        
        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                topic = row.get("场景标签", "").strip()
                quote = row.get("经典台词", "").strip()
                
                if not quote: 
                    continue
                
                # 组装带人物归属的提示文本
                content = f"[{char_name}的专属语录] 场景({topic}): “{quote}”"
                
                mem = MemoryItem(
                    id=str(uuid.uuid4()),
                    type="lore", 
                    content=content,
                    importance=8
                )
                memories_to_add.append(mem)

    if memories_to_add:
        mm.vector_store.add_memories(memories_to_add)
        print(f"✅ 成功从 {lores_dir} 注入 {len(memories_to_add)} 条专属语料！")
    else:
        print(f"⚠️ 未发现任何有效语料，请在后台系统或 {lores_dir} 文件夹中添加！")

if __name__ == "__main__":
    build_knowledge()
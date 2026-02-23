import sys
import os
import uuid

# 确保能找到 src 目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
from src.models.schema import MemoryItem

# ==========================================
# 1. 编剧工作台：在这里写下角色的固定语录/设定
# 参考 presets.py 中陈雨婷的设定：控制狂、洁癖、学生会干部
# ==========================================
CHEN_YUTING_LORE = [
    "【面对借钱/哭穷】呵呵，借钱？你上个月欠我的奶茶钱结清了吗？我就随口一说哈，我的钱也不是大风刮来的。",
    "【面对卫生问题/打扫】这地是谁扫的？角落里的灰尘留着过年吗？重扫，别逼我发火，这是原则问题！",
    "【面对破坏规矩/晚归】我都说了十一点准时锁门，你自己看着办。宿管阿姨那边我可不会替你打掩护。",
    "【面对求帮忙/抄作业】你自己的事情自己做不好，指望我给你擦屁股？真以为我天天闲着没事干？",
    "【面对指责/发脾气】你有什么资格说我？我每天在学生会忙得要死，回寝室还要看你们的脸色？",
    "【阴阳怪气日常】哎哟，你今天这身衣服挺特别的，淘宝九块九包邮的吧？挺符合你气质的。"
]

def build_knowledge():
    # 路径配置
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    profile_path = os.path.join(data_dir, "profile.json")
    vector_db_path = os.path.join(data_dir, "chroma_db")

    print(f"初始化向量数据库: {vector_db_path}")
    llm = LLMService()
    mm = MemoryManager(profile_path, vector_db_path, llm)

    # 准备写入的数据
    memories_to_add = []
    for lore in CHEN_YUTING_LORE:
        mem = MemoryItem(
            id=str(uuid.uuid4()),
            type="lore", # 我们打上 lore(背景设定) 的标签
            content=f"陈雨婷的专属语录与反应参考: {lore}",
            importance=10, # 给定极高的权重，确保优先被检索
            summary="Character Lore"
        )
        memories_to_add.append(mem)

    # 写入 ChromaDB
    if memories_to_add:
        mm.vector_store.add_memories(memories_to_add)
        print(f"✅ 成功将 {len(memories_to_add)} 条专属语录注入陈雨婷的大脑！")

if __name__ == "__main__":
    build_knowledge()
import uuid
import json
from typing import List, Dict
from src.models.schema import CharacterProfile, MemoryItem, SocialContext, Personality
from src.storage.json_store import JSONStore
from src.storage.vector_store import VectorStore
from src.services.llm_service import LLMService

class MemoryManager:
    def __init__(self, profile_path: str, vector_db_path: str, llm_service: LLMService):
        self.json_store = JSONStore(profile_path)
        self.vector_store = VectorStore(vector_db_path)
        self.llm_service = llm_service
        self.profile = self._load_or_create_profile()

    def _load_or_create_profile(self) -> CharacterProfile:
        data = self.json_store.load_profile()
        if data:
            return CharacterProfile(**data)
        else:
            # 默认空角色 (防止出错，实际会用 presets 覆盖)
            return CharacterProfile(
                name="New Character",
                context=SocialContext(world_view="", occupation="", current_location=""),
                personality=Personality(traits={}, values=[])
            )

    def save_profile(self):
        self.json_store.save_profile(self.profile)

    def save_interaction(self, user_input: str, ai_response: str, user_name: str = "User"):
        user_mem = MemoryItem(id=str(uuid.uuid4()), type="observation", content=f"{user_name} said: {user_input}")
        ai_mem = MemoryItem(id=str(uuid.uuid4()), type="action", content=f"I replied to {user_name}: {ai_response}")
        self.vector_store.add_memories([user_mem, ai_mem])

    def observe_interaction(self, source_name: str, content: str):
        observation = MemoryItem(
            id=str(uuid.uuid4()),
            type="observation",
            content=f"I heard {source_name} say: '{content}'",
            related_entities=[source_name]
        )
        self.vector_store.add_memories([observation])

    def chat(self, user_input: str, player_stats_str: str = "") -> tuple[str, List[Dict]]:
        # 1. 检索记忆
        relevant_memories = self.vector_store.search(user_input, n_results=5)
        context_str = "\n".join([f"- {m['content']}" for m in relevant_memories])

        # 2. 构建提示词 (加入玩家状态和数值影响规则)
        system_prompt = self._construct_system_prompt(player_stats=player_stats_str)

        # 3. 生成
        response = self.llm_service.generate_response(system_prompt, user_input, context_str)
        return response, relevant_memories

    def _construct_system_prompt(self, player_stats: str = "") -> str:
        p = self.profile
        # 构建关系描述
        rel_str = "\n".join([f"- {name}: {r.tags} (Affinity: {r.affinity})" for name, r in p.relationships.items()])
        
        return f"""
You are {p.name}.
Context: {p.context.world_view}. You are a {p.context.occupation} at {p.context.current_location}.
Personality: {p.personality.traits}. Values: {p.personality.values}. Mood: {p.personality.mood}.
Relationships:
{rel_str}

Current Scene: You are in the dorm with the Player and others.
**Player Stats**: {player_stats}

**GAME RULES**:
1. **Dynamic Interaction**: React to the player and other roommates based on your personality.
2. **Impact Stats**: Your behavior impacts the Player's stats (Money, SAN, GPA).
   - If you cause drama, annoy, or scare the player -> **[SAN-5]** (or -10, etc)
   - If you comfort or help the player -> **[SAN+5]**
   - If you distract the player from studying -> **[GPA-0.1]**
   - If you help with homework -> **[GPA+0.1]**
   - If you borrow money -> **[MONEY-50]**
3. **Tagging**: APPEND the tag at the end of your response if a stat changes. 
   Syntax: `[SAN-5]`, `[MONEY+20]`, `[GPA-0.2]`.

Respond naturally as a character, not a robot.
"""

    # --- 简化版的反思 (去掉了 Skill/Wealth 更新) ---
    def reflect_on_interaction(self, chat_history: List[Dict], user_name: str = "User") -> str:
        # 为了代码简洁，这里暂时只保留心情更新逻辑，复杂的反思可以后续再加
        # (此处省略长 Prompt，防止上下文过长，核心逻辑与之前类似，只是去掉了 Skill 部分)
        return "Reflection skipped for brevity in MVP."
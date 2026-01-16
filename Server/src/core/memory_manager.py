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

    # --- 修改处：接收 time 和 event ---
    def chat(self, user_input: str, player_stats_str: str = "", player_persona_str: str = "", current_time_str: str = "", current_event_str: str = "") -> tuple[str, List[Dict]]:
        # 1. 检索记忆
        relevant_memories = self.vector_store.search(user_input, n_results=5)
        context_str = "\n".join([f"- {m['content']}" for m in relevant_memories])

        # 2. 构建提示词
        system_prompt = self._construct_system_prompt(
            player_stats=player_stats_str, 
            player_persona=player_persona_str,
            current_time=current_time_str,
            current_event=current_event_str
        )

        # 3. 生成
        response = self.llm_service.generate_response(system_prompt, user_input, context_str)
        return response, relevant_memories

    def _construct_system_prompt(self, player_stats: str = "", player_persona: str = "", current_time: str = "", current_event: str = "") -> str:
        p = self.profile
        rel_str = "\n".join([f"- {name}: {r.tags} (Affinity: {r.affinity})" for name, r in p.relationships.items()])
        
        return f"""
You are {p.name}.
Context: {p.context.world_view}. You are a {p.context.occupation} at {p.context.current_location}.
Personality: {p.personality.traits}. Values: {p.personality.values}. Mood: {p.personality.mood}.
Relationships:
{rel_str}

[Current Game Status]
Time: {current_time}
Event: {current_event} (Note: Your behavior should adapt to this event!)
Player Profile: {player_persona}
Player Stats: {player_stats}

[GAME RULES]
1. **Event Reaction**: If the event is 'Exam Week', act stressed or studious. If 'Sports Meeting', act energetic or lazy.
2. **Impact Stats**: If your action affects the player, append tag: `[SAN-5]`, `[MONEY+20]`, `[GPA-0.2]`.
3. **Affinity**: If you like what the player did, think about `[AFFINITY+5]` (internal logic for now).

Respond naturally as a character.
"""

    def reflect_on_interaction(self, chat_history: List[Dict], user_name: str = "User") -> str:
        return "Reflection skipped for brevity in MVP."
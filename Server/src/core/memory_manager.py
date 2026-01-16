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

    def chat(self, user_input: str, player_stats_str: str = "", player_persona_str: str = "", current_time_str: str = "", current_event_obj = None) -> tuple[str, List[Dict]]:
        
        relevant_memories = self.vector_store.search(user_input, n_results=5)
        context_str = "\n".join([f"- {m['content']}" for m in relevant_memories])

        # 构建 system prompt
        system_prompt = self._construct_system_prompt(
            player_stats=player_stats_str, 
            player_persona=player_persona_str,
            current_time=current_time_str,
            current_event_obj=current_event_obj # 传入对象
        )

        response = self.llm_service.generate_response(system_prompt, user_input, context_str)
        return response, relevant_memories
        
    def _construct_system_prompt(self, player_stats: str = "", player_persona: str = "", current_time: str = "", current_event_obj = None) -> str:
        p = self.profile
        rel_str = "\n".join([f"- {name}: {r.tags} (Affinity: {r.affinity})" for name, r in p.relationships.items()])
        
        examples_str = "\n".join([f"Example: {ex}" for ex in p.personality.dialogue_examples])
        
        # 🟢 解析剧本对象
        event_instruction = ""
        if current_event_obj:
            event_instruction = f"""
[CURRENT SCENARIO: {current_event_obj.name}]
Description: {current_event_obj.description}
POTENTIAL CONFLICTS: {current_event_obj.potential_conflicts}
INSTRUCTION: You are inside this event. React to the description and conflicts naturally.
"""
        else:
            event_instruction = "[Scenario: Daily Life]"

        return f"""
You are {p.name}.
Context: {p.context.world_view}.
Personality: {p.personality.traits}. Mood: {p.personality.mood}.

[Speaking Style]
{p.personality.speaking_style}
Examples:
{examples_str}

[Status]
Time: {current_time}
{event_instruction}

[Player]
{player_persona}
Stats: {player_stats}

[Rules]
1. Act purely as {p.name}.
2. React to the Current Scenario details provided above.
3. Use tags like [SAN-5] if applicable.
4. **ALWAYS speak in Chinese.**

Respond naturally.
"""

    def reflect_on_interaction(self, chat_history: List[Dict], user_name: str = "User") -> str:
        return "Reflection skipped for brevity in MVP."
import uuid
import json
from typing import List, Dict
from src.models.schema import CharacterProfile, MemoryItem, SocialContext, Personality
from src.storage.json_store import JSONStore
from src.storage.vector_store import VectorStore
from src.services.llm_service import LLMService

class MemoryManager:
    def __init__(self, profile_path: str, vector_db_path: str, llm_service: LLMService, save_id: str = "default"):
        self.json_store = JSONStore(profile_path)
        self.vector_store = VectorStore(vector_db_path)
        self.llm_service = llm_service
        self.current_save_id = save_id
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
        self.vector_store.add_memories([user_mem, ai_mem], save_id=self.current_save_id)

    def save_narrative_milestones(self, milestones: List[str], event_name: str = "", player_name: str = ""):
        if not isinstance(milestones, list):
            return
        payload: List[MemoryItem] = []
        for item in milestones:
            text = str(item or "").strip()
            if not text:
                continue
            content = f"[叙事里程碑]{text}"
            if event_name:
                content += f" | 事件:{event_name}"
            if player_name:
                content += f" | 主角:{player_name}"
            payload.append(
                MemoryItem(
                    id=str(uuid.uuid4()),
                    type="narrative_milestone",
                    content=content,
                    summary=text[:120],
                    importance=8,
                    related_entities=[player_name] if player_name else []
                )
            )
        if payload:
            self.vector_store.add_memories(payload, save_id=self.current_save_id)

    def search_narrative_milestones(self, query: str, n_results: int = 3) -> List[Dict]:
        where = {"save_id": self.current_save_id, "type": "narrative_milestone"}
        return self.vector_store.search(query=query, n_results=n_results, filter_metadata=where)

    def observe_interaction(self, source_name: str, content: str):
        observation = MemoryItem(
            id=str(uuid.uuid4()),
            type="observation",
            content=f"I heard {source_name} say: '{content}'",
            related_entities=[source_name]
        )
        self.vector_store.add_memories([observation], save_id=self.current_save_id)

    def chat(self, user_input: str, player_stats_str: str = "", player_persona_str: str = "", current_time_str: str = "", current_event_obj = None) -> tuple[str, List[Dict]]:
        
        # 增加 save_id 过滤
        filter_meta = {"save_id": self.current_save_id}
        relevant_memories = self.vector_store.search(user_input, n_results=5, filter_metadata=filter_meta)
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
    
    def clear_game_history(self):
        """清空上一轮游戏的互动记忆，保留角色专属语料"""
        try:
            # 获取当前存档下的所有数据
            data = self.vector_store.collection.get(where={"save_id": self.current_save_id})
            if data and data['ids']:
                self.vector_store.collection.delete(ids=data['ids'])
                print(f"成功清理了存档 {self.current_save_id} 下的 {len(data['ids'])} 条临时记忆！")
        except Exception as e:
            print(f"清理历史记忆失败: {e}")

    def get_recent_history(self, limit: int = 15) -> str:
        """抽取非固定预设（非Lore）的动态记忆载荷"""
        try:
            data = self.vector_store.collection.get()
            if not data or not data.get('ids'): 
                return "暂无记忆流数据"
            
            history = []
            for i, meta in enumerate(data.get('metadatas', [])):
                # 过滤掉底层自带的 lore，只抽取动态生成的 action/observation
                if meta and meta.get("type") != "lore":
                    doc = data.get('documents', [''])[i] if data.get('documents') else meta.get('content', '未知数据碎块')
                    if doc: history.append(doc)
                    
            if not history: 
                return "暂无动态记忆记录"
            recent = history[-limit:]
            return "\n".join([f"🔹 {h}" for h in recent])
        except Exception as e:
            return f"记忆流读取异常: {e}"
            
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
        """
        夜间反思机制：将零散的近期对话缓存提取，交由 LLM 进行归纳与提炼
        将总结后的高级认知记忆存回 ChromaDB 以降低后续检索引擎的噪点
        """
        # 抽取近期记忆切片
        recent_slices = self.get_recent_history(limit=15)
        # ...向大模型发起提炼 Prompt 请求并写回向量数据库...
        return "Reflected"

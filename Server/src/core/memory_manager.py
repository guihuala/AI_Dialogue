import uuid
import json
import re
from typing import List, Dict, Any
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
        user_mem = MemoryItem(
            id=str(uuid.uuid4()),
            type="short_term_dialogue",
            content=f"{user_name}：{user_input}",
            summary=str(user_input or "").strip()[:120],
            importance=3,
            related_entities=[user_name] if user_name else [],
        )
        ai_mem = MemoryItem(
            id=str(uuid.uuid4()),
            type="short_term_dialogue",
            content=f"系统回应：{ai_response}",
            summary=str(ai_response or "").strip()[:120],
            importance=3,
            related_entities=[user_name] if user_name else [],
        )
        self.vector_store.add_memories([user_mem, ai_mem], save_id=self.current_save_id)
        self._prune_short_term_dialogues(limit=24)

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

    def save_event_reflection(
        self,
        *,
        event_id: str = "",
        event_name: str = "",
        player_name: str = "",
        active_chars: List[str] | None = None,
        current_scene: str = "",
        dialogue_sequence: List[Dict[str, Any]] | None = None,
        effects_data: Dict[str, Any] | None = None,
        state_delta: Dict[str, Any] | None = None,
    ) -> str:
        title = str(event_name or event_id or "未命名事件").strip() or "未命名事件"
        active_chars = [str(x).strip() for x in (active_chars or []) if str(x).strip()]
        effects_data = effects_data if isinstance(effects_data, dict) else {}
        state_delta = state_delta if isinstance(state_delta, dict) else {}
        reflection = self._build_event_reflection_summary(
            event_name=title,
            player_name=player_name,
            active_chars=active_chars,
            current_scene=current_scene,
            dialogue_sequence=dialogue_sequence or [],
            effects_data=effects_data,
            state_delta=state_delta,
        )
        if not reflection:
            return ""

        effect_line = self._format_effect_summary(effects_data)
        relation_line = self._format_relation_summary(state_delta)
        content_lines = [f"[事件反思] {title}", reflection]
        if current_scene:
            content_lines.append(f"场景：{str(current_scene).strip()}")
        if effect_line:
            content_lines.append(f"结果：{effect_line}")
        if relation_line:
            content_lines.append(f"关系：{relation_line}")

        summary = re.sub(r"\s+", " ", reflection).strip()
        if len(summary) > 80:
            summary = summary[:80].rstrip("，,。.!！？?…") + "…"

        memory = MemoryItem(
            id=str(uuid.uuid4()),
            type="event_reflection",
            content="\n".join(content_lines),
            summary=f"{title}：{summary}",
            importance=8,
            related_entities=[x for x in [player_name, *active_chars] if x],
        )
        self.vector_store.add_memories([memory], save_id=self.current_save_id)
        return memory.content

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
            data = self.vector_store.collection.get(where={"save_id": self.current_save_id})
            if not data or not data.get('ids'): 
                return "暂无记忆流数据"
            
            history = []
            for i, meta in enumerate(data.get('metadatas', [])):
                if not isinstance(meta, dict):
                    continue
                if meta.get("type") != "short_term_dialogue":
                    continue
                doc = meta.get("original_content") or (data.get('documents', [''])[i] if data.get('documents') else '')
                if doc:
                    history.append(str(doc))
                    
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

    def _prune_short_term_dialogues(self, limit: int = 24) -> None:
        try:
            data = self.vector_store.collection.get(where={"save_id": self.current_save_id})
            if not data or not data.get("ids"):
                return

            short_term_rows = []
            for idx, mid in enumerate(data.get("ids", [])):
                meta = (data.get("metadatas", [None])[idx] or {})
                if not isinstance(meta, dict):
                    continue
                if str(meta.get("type", "") or "").strip() != "short_term_dialogue":
                    continue
                short_term_rows.append(
                    (
                        str(meta.get("timestamp", "") or ""),
                        mid,
                    )
                )

            if len(short_term_rows) <= max(0, int(limit)):
                return

            short_term_rows.sort(key=lambda x: x[0], reverse=True)
            ids_to_delete = [mid for _, mid in short_term_rows[int(limit):]]
            if ids_to_delete:
                self.vector_store.collection.delete(ids=ids_to_delete)
        except Exception:
            pass

    def _build_event_reflection_summary(
        self,
        *,
        event_name: str,
        player_name: str,
        active_chars: List[str],
        current_scene: str,
        dialogue_sequence: List[Dict[str, Any]],
        effects_data: Dict[str, Any],
        state_delta: Dict[str, Any],
    ) -> str:
        if getattr(self, "llm_service", None) is not None and getattr(self.llm_service, "has_usable_config", None) and self.llm_service.has_usable_config():
            try:
                excerpt_lines = []
                for item in (dialogue_sequence or [])[-6:]:
                    if not isinstance(item, dict):
                        continue
                    speaker = str(item.get("speaker", "") or "").strip()
                    content = str(item.get("content", "") or "").strip()
                    if not content:
                        continue
                    if speaker:
                        excerpt_lines.append(f"{speaker}：{content}")
                    else:
                        excerpt_lines.append(content)
                payload = {
                    "event_name": event_name,
                    "player_name": str(player_name or "").strip(),
                    "active_chars": active_chars,
                    "current_scene": str(current_scene or "").strip(),
                    "dialogue_excerpt": excerpt_lines,
                    "effects": effects_data,
                    "state_delta": state_delta,
                }
                raw = self.llm_service.generate_response(
                    system_prompt=(
                        "你在为校园宿舍剧情游戏生成一条“事件结束后的反思记忆”。\n"
                        "要求：\n"
                        "1. 只返回 JSON：{\"summary\": string}\n"
                        "2. summary 用第二人称，像系统给玩家留下的一句反思记录。\n"
                        "3. 必须点出这次事件真正造成的变化：关系、情绪、金钱、绩点或宿舍气氛里最重要的一项。\n"
                        "4. 不要流水账复述剧情，不要列清单，不要写成公告。\n"
                        "5. 长度 28 到 70 个汉字，简洁但要有判断。"
                    ),
                    user_input=json.dumps(payload, ensure_ascii=False),
                    context="",
                    temperature=0.6,
                    max_tokens=120,
                )
                parsed = json.loads(str(raw or "{}"))
                if isinstance(parsed, dict):
                    summary = str(parsed.get("summary", "") or "").strip()
                    if summary:
                        return summary
            except Exception:
                pass
        return self._build_local_event_reflection(
            event_name=event_name,
            active_chars=active_chars,
            effects_data=effects_data,
            state_delta=state_delta,
        )

    def _build_local_event_reflection(
        self,
        *,
        event_name: str,
        active_chars: List[str],
        effects_data: Dict[str, Any],
        state_delta: Dict[str, Any],
    ) -> str:
        relations = state_delta.get("relation_deltas", []) if isinstance(state_delta.get("relation_deltas"), list) else []
        top_rel = relations[0] if relations else {}
        rel_name = str(top_rel.get("name", "") or "").strip()
        stage_from = str(top_rel.get("stage_from", "") or "").strip()
        stage_to = str(top_rel.get("stage_to", "") or "").strip()
        trust_delta = float(top_rel.get("trust_delta", 0) or 0) if top_rel else 0.0
        tension_delta = float(top_rel.get("tension_delta", 0) or 0) if top_rel else 0.0

        money_delta = float(effects_data.get("money_delta", 0) or 0)
        gpa_delta = float(effects_data.get("gpa_delta", 0) or 0)
        san_delta = float(effects_data.get("san_delta", 0) or 0)

        if rel_name and stage_to and stage_from and stage_from != stage_to:
            return f"{event_name}结束后，你和{rel_name}的关系从{stage_from}滑向{stage_to}，这件事不会像表面那样轻易翻篇。"
        if rel_name and trust_delta >= 3:
            return f"{event_name}结束后，{rel_name}明显更愿意靠近你了，但这份信任还需要后续继续稳住。"
        if rel_name and tension_delta >= 3:
            return f"{event_name}结束后，你和{rel_name}之间的刺变得更明显了，宿舍里的气氛也开始悄悄绷紧。"
        if money_delta != 0:
            direction = "多花了一笔钱" if money_delta < 0 else "进账了一笔钱"
            return f"{event_name}结束后，你{direction}，这次选择的代价已经开始落到现实生活上。"
        if gpa_delta != 0:
            direction = "受到了冲击" if gpa_delta < 0 else "略有回升"
            return f"{event_name}结束后，你的绩点{direction}，这场风波已经不只是情绪问题了。"
        if san_delta != 0:
            direction = "心里更乱了" if san_delta < 0 else "稍微缓过来一点"
            return f"{event_name}结束后，你{direction}，但真正的后劲还会在后面的相处里慢慢显出来。"
        if active_chars:
            return f"{event_name}暂时收束了，但你和{active_chars[0]}她们之间留下的细小变化，之后还会继续发酵。"
        return f"{event_name}暂时告一段落了，表面恢复平静，但这次留下的影响还没有真正结束。"

    def _format_effect_summary(self, effects_data: Dict[str, Any]) -> str:
        parts: List[str] = []
        san_delta = float(effects_data.get("san_delta", 0) or 0)
        money_delta = float(effects_data.get("money_delta", 0) or 0)
        gpa_delta = float(effects_data.get("gpa_delta", 0) or 0)
        arg_delta = float(effects_data.get("arg_delta", 0) or 0)
        if san_delta:
            parts.append(f"SAN {'+' if san_delta > 0 else ''}{round(san_delta, 2)}")
        if money_delta:
            parts.append(f"金钱 {'+' if money_delta > 0 else ''}{round(money_delta, 2)}")
        if gpa_delta:
            parts.append(f"GPA {'+' if gpa_delta > 0 else ''}{round(gpa_delta, 2)}")
        if arg_delta:
            parts.append(f"争吵 {'+' if arg_delta > 0 else ''}{round(arg_delta, 2)}")
        return "，".join(parts[:4])

    def _format_relation_summary(self, state_delta: Dict[str, Any]) -> str:
        rels = state_delta.get("relation_deltas", []) if isinstance(state_delta.get("relation_deltas"), list) else []
        parts: List[str] = []
        for item in rels[:3]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "") or "").strip()
            if not name:
                continue
            stage_from = str(item.get("stage_from", "") or "").strip()
            stage_to = str(item.get("stage_to", "") or "").strip()
            trust_delta = float(item.get("trust_delta", 0) or 0)
            tension_delta = float(item.get("tension_delta", 0) or 0)
            if stage_from and stage_to and stage_from != stage_to:
                parts.append(f"{name}：{stage_from}->{stage_to}")
            elif abs(trust_delta) >= 0.01 or abs(tension_delta) >= 0.01:
                parts.append(
                    f"{name}：信任{'+' if trust_delta > 0 else ''}{round(trust_delta, 1)} / 紧张{'+' if tension_delta > 0 else ''}{round(tension_delta, 1)}"
                )
        return "；".join(parts)

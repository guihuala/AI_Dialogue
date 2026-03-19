import os
import json
import re
import csv
import concurrent.futures
import asyncio
import time
from json_repair import repair_json 

import src.core.presets as presets_module
from src.models.schema import CharacterProfile
from src.services.llm_service import LLMService
from src.core.memory_manager import MemoryManager
from src.core.event_director import EventDirector
from src.core.event_script import load_user_events
from src.core.prompt_manager import PromptManager
from src.core.agent_system import NPCAgent
from src.core.tool_manager import ToolManager
from src.core.prefetch_manager import PrefetchManager
from src.core.script_runner import ScriptRunner
from src.core.config import (
    DATA_ROOT, CHROMA_DB_PATH, PROFILE_PATH, 
    get_user_chroma_path, get_user_saves_dir
)

class GameEngine:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.latency_mode = "balanced"  # balanced | fast | story
        self.dialogue_mode = "single_dm"   # single_dm | hybrid | tree_only | npc_dm
        self.candidate_pool = {}
        for key, obj in vars(presets_module).items():
            if isinstance(obj, CharacterProfile) and obj.Name != "陆陈安然": 
                self.candidate_pool[obj.Name] = obj
                
        self.llm = LLMService()
        
        # Use user-specific paths
        user_chroma_path = get_user_chroma_path(user_id)
        # Profile path is technically global for initial loading, 
        # but we can make it user-specific if we want they to have different save profiles.
        # For now, keep PROFILE_PATH global or map it?
        # Actually, if we want them to have different characters/stats, it should be per-user.
        user_profile_dir = os.path.dirname(get_user_saves_dir(user_id))
        user_profile_path = os.path.join(user_profile_dir, "profile.json")
        
        self.mm = MemoryManager(user_profile_path, user_chroma_path, self.llm)
        self.director = EventDirector(user_id)
        self.tm = ToolManager()
        self.pm = PromptManager(user_id)
        self.prefetch_mgr = PrefetchManager()
        self.event_completion_count = 0
        self.recent_event_ids = []
        self.prefetch_futures = {}
        self.event_repeat_state = {}

    def reset(self):
        self.director.reset()
        self.event_completion_count = 0
        self.recent_event_ids = []
        self.event_repeat_state = {}

    def _get_latency_profile(self, event_obj) -> dict:
        """
        按事件类型返回性能策略：
        - 关键剧情：质量优先（full + 更长超时）
        - 常规剧情：速度优先（fast + 更短超时）
        """
        # 用户手动模式优先
        if self.latency_mode == "fast":
            return {
                "prefetch_mode_current": "fast",
                "prefetch_mode_next": "fast",
                "llm_timeout_sec": 14.0,
                "llm_max_tokens": 600
            }
        if self.latency_mode == "story":
            return {
                "prefetch_mode_current": "full",
                "prefetch_mode_next": "full",
                "llm_timeout_sec": 24.0,
                "llm_max_tokens": 1400
            }

        evt_type = str(getattr(event_obj, "event_type", "") or "")
        is_key_event = (
            getattr(event_obj, "is_boss", False)
            or "开局" in evt_type
            or "固定" in evt_type
            or "条件" in evt_type
            or getattr(event_obj, "is_cg", False)
        )
        if is_key_event:
            return {
                "prefetch_mode_current": "full",
                "prefetch_mode_next": "full",
                "llm_timeout_sec": 18.0,
                "llm_max_tokens": 1200
            }
        return {
            "prefetch_mode_current": "fast",
            "prefetch_mode_next": "fast",
            "llm_timeout_sec": 16.0,
            "llm_max_tokens": 700
        }

    def parse_and_repair_json(self, raw_text):
        raw_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
        raw_text = re.sub(r'```json\s*', '', raw_text)
        raw_text = re.sub(r'```\s*', '', raw_text)
        raw_text = raw_text.replace('“', '"').replace('”', '"').replace('：', ':').replace('‘', "'").replace('’', "'")
        
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            raw_json = raw_text[start_idx:end_idx+1]
        else:
            raw_json = raw_text
            
        try:
            repaired = repair_json(raw_json)
            parsed = json.loads(repaired) if isinstance(repaired, str) else repaired
            if not isinstance(parsed, dict): raise ValueError(f"返回非字典: {type(parsed)}")
            return parsed
        except Exception as e:
            try:
                repaired = repair_json(raw_text)
                parsed = json.loads(repaired) if isinstance(repaired, str) else repaired
                if isinstance(parsed, dict): return parsed
            except: pass
            
            return {
                "narrator_transition": "（系统受到干扰，尝试理清思绪...）",
                "current_scene": "未知",
                "dialogue_sequence": [{"speaker": "系统提示", "content": "（由于未知干扰，当前对话解析失败，请检查参数面板中的“原始输出”查明原因。）", "mood": "neutral"}],
                "npc_background_actions": [],
                "wechat_notifications": [],
                "next_options": ["【深呼吸】", "【重试】", "【继续观察】"],
                "stat_changes": {},
                "is_end": False
            }

    def _normalize_options(self, raw_options, next_evt=None):
        """
        容错解析 next_options，处理模型把多个选项粘成一个字符串的情况。
        """
        options = []
        if isinstance(raw_options, list):
            options = [str(o).strip() for o in raw_options if o is not None and str(o).strip()]
        elif isinstance(raw_options, str):
            text = raw_options.strip()
            # 常规分隔符：换行、逗号、分号、竖线、顿号
            chunks = re.split(r'[\n,，;；|、]+', text)
            chunks = [c.strip(" -•\t") for c in chunks if c and c.strip(" -•\t")]
            # 如果拆不出来，再按 A:/B:/C: 之类模式切
            if len(chunks) <= 1:
                labeled = re.split(r'(?=(?:^|[\s])(?:[A-Da-d]|[1-4])[\.:\：、])', text)
                chunks = [c.strip(" -•\t") for c in labeled if c and c.strip(" -•\t")]
            options = chunks

        # 进一步处理单个长字符串里粘了多个标签的情况
        if len(options) == 1:
            one = options[0]
            labeled = re.findall(r'(?:[A-Da-d]|[1-4])[\.:\：、]\s*[^A-Da-d1-4]{2,80}', one)
            if len(labeled) >= 2:
                options = [x.strip() for x in labeled]

        # 去重保序
        dedup = []
        seen = set()
        for opt in options:
            opt = re.sub(r'^\s*(?:[A-Da-d]|[1-4])[\.:\：、]\s*', '', opt).strip()
            key = re.sub(r'\s+', ' ', opt)
            if key not in seen:
                seen.add(key)
                dedup.append(opt)

        if dedup:
            return dedup[:4]

        if next_evt is not None:
            evt_options = []
            raw_evt_options = getattr(next_evt, "options", {})
            if isinstance(raw_evt_options, dict):
                evt_options = [str(v).strip() for v in raw_evt_options.values() if str(v).strip()]
            if evt_options:
                return evt_options[:4]

        return ["【深呼吸】", "【继续观察】", "【转移话题】"]

    def play_main_turn(self, action_text, selected_chars, current_evt_id, is_transition, api_key, base_url, model, tmp, top_p, max_t, pres_p, freq_p, san, money, gpa, hygiene, reputation, arg_count, chapter, turn, affinity, wechat_data_dict, is_prefetch=False, custom_prompts=None):
        self.llm.update_config(api_key=api_key, base_url=base_url, model=model)
        effective_dialogue_mode = self.dialogue_mode
        if effective_dialogue_mode in ["tree_only", "hybrid"]:
            effective_dialogue_mode = "single_dm"
        use_branch_tree = False
        
        # --- 动态映射逻辑 ---
        roster_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "prompts", "characters", "roster.json")
        roster = {}
        if os.path.exists(roster_path):
            try:
                with open(roster_path, 'r', encoding='utf-8') as f:
                    roster = json.load(f)
            except: pass

        def get_name(cid):
            if cid in roster: return roster[cid].get("name", cid)
            if hasattr(presets_module, "CANDIDATE_POOL") and cid in presets_module.CANDIDATE_POOL:
                return presets_module.CANDIDATE_POOL[cid].Name
            return cid

        selected_chars = [get_name(c) for c in selected_chars]
        
        mapped_affinity = {}
        for k, v in affinity.items():
            mapped_affinity[get_name(k)] = v
        affinity = mapped_affinity

        player_stats = {"money": money, "san": san, "hygiene": hygiene, "gpa": gpa, "reputation": reputation}
        settlement_msg = ""
        
        if is_transition or current_evt_id == "":
            if turn == 0 and not is_prefetch: 
                self.mm.clear_game_history()
                self.director.current_chapter = chapter
                self.director.chapter_progress = 0
                self.director.used_events = []
                
            next_evt = self.director.get_next_event(player_stats, selected_chars, affinity)
            if not next_evt:
                # 游戏全流程已结束 (毕业)
                return {
                    "is_game_over": True,
                    "display_text": "**[大学生活圆满结束]** 你完成了四年的大学生活，走向了人生的新阶段。恭喜毕业！",
                    "chapter": chapter,
                    "turn": turn,
                    "san": san,
                    "money": money,
                    "gpa": gpa,
                    "is_end": True,
                    "next_options": ["查看我的结局", "重新开始"],
                    "dialogue_sequence": [{"speaker": "系统提示", "content": "全剧终。", "mood": "happy"}]
                }

            if next_evt.chapter > chapter:
                money -= 800  
                gpa = max(0.0, min(4.0, 3.0 - (arg_count * 0.05)))
                settlement_msg = f"**[大{chapter}学年结算]** 扣除生活费800。GPA：{gpa:.2f}\n\n"
                chapter = next_evt.chapter; arg_count = 0 
            turn = 1
            
            # --- [DEEP PREFETCH CONSUMPTION: OPENING] ---
            # 尽早触发当前事件剧本预取，提升后续选项秒回命中率。
            prefetcher = self.prefetch_mgr.get_prefetcher(self.user_id, self.llm, self.pm)
            latency_profile = self._get_latency_profile(next_evt)
            if use_branch_tree and not getattr(next_evt, 'is_cg', False):
                prefetcher.generate_script_async({
                    "chapter": chapter,
                    "turn": turn,
                    "active_chars": selected_chars,
                    "custom_prompts": custom_prompts,
                    "event_name": next_evt.name,
                    "event_id": next_evt.id,
                    "event_description": next_evt.description,
                    "generation_mode": latency_profile["prefetch_mode_current"]
                })

            # 开局首回合优先播放人工固定剧情；普通事件优先尝试命中事件级剧本缓存。
            cached_script = prefetcher.get_cached_script(next_evt.id) if use_branch_tree else None
            if (
                not cached_script
                and not is_prefetch
                and not getattr(next_evt, 'is_cg', False)
                and effective_dialogue_mode == "tree_only"
            ):
                cached_script = prefetcher.generate_script_blocking({
                    "chapter": chapter,
                    "turn": turn,
                    "active_chars": selected_chars,
                    "custom_prompts": custom_prompts,
                    "event_name": next_evt.name,
                    "event_id": next_evt.id,
                    "event_description": next_evt.description,
                    "generation_mode": "fast",
                    "max_attempts": 2
                })
            if cached_script and not is_prefetch and not getattr(next_evt, 'is_cg', False):
                print(f"🚀 [Prefetch] HIT: Using deep script for {next_evt.name}")
                prefetcher.mark_non_fallback()
                runner = ScriptRunner(cached_script)
                first_turn = runner.get_turn(1)
                if first_turn:
                    next_options = [opt.get("text") for opt in first_turn.get("player_choices", []) if isinstance(opt, dict) and opt.get("text")]
                    return {
                        "narrator_transition": cached_script.get("description", f"🎬 **{next_evt.name}**\n---"),
                        "current_scene": first_turn.get("scene", "宿舍"),
                        "dialogue_sequence": first_turn.get("dialogue_sequence", []),
                        "next_options": next_options if next_options else ["继续剧情..."],
                        "stat_changes": {}, # Initial entry usually no changes
                        "is_end": first_turn.get("is_end", False),
                        "event_id": next_evt.id,
                        "turn": 1,
                        "event_script": cached_script # Return full script to frontend
                    }
            elif not is_prefetch and not getattr(next_evt, 'is_cg', False):
                prefetcher.mark_fallback()

            opening_conflicts = "、".join((getattr(next_evt, "potential_conflicts", []) or [])[:3])
            opening_conflicts = opening_conflicts or "无"
            opening_beats = getattr(next_evt, "progress_beats", []) or []
            opening_beat_hint = f"\n【建议推进节点】{opening_beats[0]}" if opening_beats else ""
            event_context = (
                f"【系统指令】开始以下事件，不要写任何开场白或过场旁白。"
                f"\n【新事件】:{next_evt.name}"
                f"\n【场景描述】:{next_evt.description}"
                f"\n【潜在冲突参考】:{opening_conflicts}"
                f"{opening_beat_hint}"
            )
        else:
            next_evt = self.director.event_database.get(current_evt_id)
            if not next_evt:
                return {"error": "事件丢失，请重置游戏。"}
            
            # --- [DEEP PREFETCH CONSUMPTION: IN-EVENT TURN] ---
            prefetcher = self.prefetch_mgr.get_prefetcher(self.user_id, self.llm, self.pm)
            latency_profile = self._get_latency_profile(next_evt)
            cached_script = prefetcher.get_cached_script(next_evt.id) if use_branch_tree else None
            # 给后台预取一个很短的“追赶窗口”，避免用户点击过快直接跌回慢路径。
            if not cached_script and not is_prefetch and not getattr(next_evt, 'is_cg', False):
                for _ in range(4):
                    time.sleep(0.2)
                    cached_script = prefetcher.get_cached_script(next_evt.id)
                    if cached_script:
                        break
            if not cached_script and not is_prefetch and not getattr(next_evt, 'is_cg', False) and effective_dialogue_mode == "tree_only":
                cached_script = prefetcher.generate_script_blocking({
                    "chapter": chapter,
                    "turn": turn,
                    "active_chars": selected_chars,
                    "custom_prompts": custom_prompts,
                    "event_name": next_evt.name,
                    "event_id": next_evt.id,
                    "event_description": next_evt.description,
                    "generation_mode": "fast",
                    "max_attempts": 2
                })
            if cached_script and not is_prefetch:
                print(f"🚀 [Prefetch] HIT: Executing choice '{action_text}' from script")
                prefetcher.mark_non_fallback()
                # 如果当前是 fast 剧本，后台升级为 full 版本，不阻塞本轮返回
                if str(cached_script.get("quality", "fast")).lower() != "full":
                    prefetcher.generate_script_async({
                        "chapter": chapter,
                        "turn": turn,
                        "active_chars": selected_chars,
                        "custom_prompts": custom_prompts,
                        "event_name": next_evt.name,
                        "event_id": next_evt.id,
                        "event_description": next_evt.description,
                        "generation_mode": "full"
                    })
                runner = ScriptRunner(cached_script)
                res_data = runner.get_next_turn_data(turn, action_text)
                
                if "error" not in res_data:
                    # Apply stat changes from script
                    stats_data = res_data.get("stat_changes", {})
                    san = max(0, min(100, san + stats_data.get("san_delta", 0)))
                    money += stats_data.get("money_delta", 0)
                    
                    aff_changes = stats_data.get("affinity_changes", {})
                    if isinstance(aff_changes, dict):
                        for char_name, change_val in aff_changes.items():
                            if char_name in affinity: 
                                affinity[char_name] = max(0, min(100, affinity[char_name] + change_val))

                    # 构造最终返回
                    display_text = res_data.get("narrator_transition", "") + "\n\n"
                    dialogue_lines = []
                    for t in res_data.get("dialogue_sequence", []):
                        spk, cont = t.get("speaker", "神秘人"), t.get("content", "")
                        if cont: dialogue_lines.append(f"**[{spk}]** {cont}")
                    
                    if dialogue_lines:
                        display_text += "\n\n".join(dialogue_lines)

                    # 如果事件结束，清理缓存
                    if res_data.get("is_end"):
                        prefetcher.clear_cache(next_evt.id)

                    return {
                        "is_game_over": False,
                        "display_text": display_text,
                        "san": san,
                        "money": money,
                        "gpa": gpa,
                        "hygiene": hygiene,
                        "reputation": reputation,
                        "arg_count": arg_count,
                        "chapter": chapter,
                        "turn": res_data.get("turn", turn + 1),
                        "affinity": affinity,
                        "active_roommates": selected_chars,
                        "current_scene": res_data.get("current_scene", "场景"),
                        "current_evt_id": next_evt.id,
                        "is_end": res_data.get("is_end", False),
                        "next_options": res_data.get("next_options", []),
                        "dialogue_sequence": res_data.get("dialogue_sequence", []),
                        "narrator_transition": res_data.get("narrator_transition", "")
                    }
            elif not is_prefetch:
                prefetcher.mark_fallback()

            turn += 1
            evt_min_turn = max(2, min(12, int(getattr(next_evt, "min_turn_for_end", 6) or 6)))
            evt_max_turn = max(evt_min_turn + 1, min(16, int(getattr(next_evt, "max_turn_for_end", 10) or 10)))
            if turn < evt_min_turn:
                pacing = "【节奏：发展】继续推进冲突，不要重复上回合同义表达。"
            elif turn >= evt_max_turn:
                pacing = "【节奏：收束】事件信息已充分，明确给出阶段性结论并结束事件。"
            else:
                pacing = "【节奏：推进】根据玩家动作产生新信息、新立场或新代价。"

            beats = getattr(next_evt, "progress_beats", []) or []
            beat_hint = ""
            if beats:
                beat_idx = min(max(turn - 1, 0), len(beats) - 1)
                beat_hint = f"\n【本回合建议推进节点】{beats[beat_idx]}"
            end_signals = "、".join((getattr(next_evt, "end_signals", []) or [])[:3])
            end_hint = f"\n【收束参考】{end_signals}" if end_signals else ""

            event_context = (
                f"【事件】: {next_evt.name}"
                f"\n【回合】: {turn}/{evt_max_turn}"
                f"\n{pacing}"
                f"{beat_hint}{end_hint}"
                f"\n【玩家选择意图】: {action_text}"
            )

        try:
            relevant_docs = self.mm.vector_store.search(f"{next_evt.name} {action_text}", n_results=6)
            valid_lores = []
            active_plus_player = selected_chars + ["陆陈安然"] 
            for d in relevant_docs:
                content = d.get('content', '')
                if "语录" in content and any(f"[{c}" in content for c in active_plus_player):
                    valid_lores.append(content)
            lore_str = "\n".join(valid_lores[:3])
        except: 
            lore_str = ""

        wechat_summary = "【近期微信动态】\n"
        has_recent_wechat = False
        for chat_name, messages in wechat_data_dict.items():
            if messages:
                last_msg = messages[-1]
                msg_content = last_msg[0] if last_msg[0] else last_msg[1].replace("**", "")
                wechat_summary += f"- 在 {chat_name} 中，最后消息：“{msg_content}”。\n"
                has_recent_wechat = True
        if not has_recent_wechat: wechat_summary += "无\n"

        game_context = {
            "chapter": chapter,
            "turn": turn,
            "event_name": next_evt.name,               
            "event_description": next_evt.description, 
            "active_chars": selected_chars,
            "rag_lore": lore_str,
            "custom_prompts": custom_prompts
        }

        sys_prm = self.pm.get_main_system_prompt(game_context)
        safe_keys = ", ".join([str(k) for k in wechat_data_dict.keys()])

        # ========================================================
        # 多智能体剧场演出阶段
        # ========================================================

        npc_chars = [c for c in selected_chars if c != "陆陈安然"]
        reactions_str = ""
        
        # 仅在 npc_dm 模式启用多智能体并行反应。single_dm/hybrid/tree_only 均走单一 DM。
        if effective_dialogue_mode == "npc_dm" and npc_chars and not getattr(next_evt, 'is_cg', False):
            agents = []
            for char_name in npc_chars:
                char_file = self.pm.char_file_map.get(char_name, "")
                profile_text = ""
                if custom_prompts and char_name in custom_prompts:
                    profile_text = custom_prompts[char_name]
                elif char_file:
                    profile_text = self.pm._read_md(f"characters/{char_file}")
                else:
                    profile_text = f"你扮演的大型语言模型未能找到 {char_name} 的具体设定文件，请根据你的名字合理推演。"
                rel_text = ""
                rel_csv_path = os.path.join(self.pm.chars_dir, "relationship.csv")
                if os.path.exists(rel_csv_path):
                    try:
                        with open(rel_csv_path, 'r', encoding='utf-8-sig') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                if row.get("评价者", "").strip() == char_name and row.get("被评价者", "").strip() in selected_chars:
                                    target = row.get("被评价者", "").strip()
                                    surface = row.get("表面态度", "").strip()
                                    inner = row.get("内心真实评价", "").strip()
                                    rel_text += f"- 对待【{target}】：表面[{surface}]，内心觉得[{inner}]。\n"
                    except: pass
                
                agent = NPCAgent(char_name, profile_text, rel_text, self.llm)
                agents.append(agent)
                
            async def fetch_all_reactions():
                tasks = [agent.async_react(event_context, action_text) for agent in agents]
                return await asyncio.gather(*tasks)

            t1 = time.time()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    with concurrent.futures.ThreadPoolExecutor(1) as pool:
                        reactions = pool.submit(lambda: asyncio.run(fetch_all_reactions())).result()
                else:
                    reactions = asyncio.run(fetch_all_reactions())
            except Exception:
                reactions = asyncio.run(fetch_all_reactions())
            print(f"🛑 [耗时监控] NPC 并发思考耗时: {time.time() - t1:.2f} 秒")
                
            reactions_str = "\n\n【演员就位：以下是在场室友刚才做出的独立反应】\n(⚠️系统警告：请你作为 DM，严格采纳以下室友的反应进行编排。禁止篡改她们的原意、动作和准备发送的微信内容！)\n"
            for i, char_name in enumerate(npc_chars):
                r = reactions[i]
                mood = r.get("mood", "平静")
                action = r.get("action", "")
                dia = r.get("dialogue", "")
                wec = r.get("wechat_message", "")
                reactions_str += f"- {char_name}: [情绪]:{mood} | [动作]:{action}\n"
                if dia: reactions_str += f"  嘴上说：“{dia}”\n"
                if wec: reactions_str += f"  准备在微信发：“{wec}”\n"
        
        # ========================================================
        # DM统筹并结算阶段
        # ========================================================
        
        user_prm = f"{event_context}\n\n【玩家意图】: {action_text}{reactions_str}\n\n【现有微信通讯录】: {safe_keys}\n{wechat_summary}\n[状态] SAN:{san}, 资金:{money}。\n\n{self.pm.get_main_author_note()}"

        try:
            if getattr(next_evt, 'is_cg', False):
                cg_dialogue = getattr(next_evt, 'fixed_dialogue', [])
                if not cg_dialogue:
                    cg_dialogue = [{"speaker": "系统提示", "content": "（剧情触发成功，但CSV对应行没有对话内容。）", "mood": "neutral"}]
                # 固定剧情统一走“继续剧情...”进入下一事件，避免在开场阶段被误判为终局遮罩。
                cg_options = ["继续剧情..."]

                parsed = {
                    "narrator_transition": f"🎬 **[剧情演出] {next_evt.name}**\n---", 
                    "current_scene": "宿舍",
                    "dialogue_sequence": cg_dialogue, 
                    "next_options": cg_options,
                    "stat_changes": {}, 
                    "wechat_notifications": [],
                    "npc_background_actions": [],
                    "is_end": True
                }
                res_text = json.dumps(parsed, ensure_ascii=False)
            else:
                if use_branch_tree and effective_dialogue_mode == "tree_only":
                    parsed = {
                        "narrator_transition": "（系统提示：该事件以分支树模式运行。）",
                        "current_scene": "宿舍",
                        "dialogue_sequence": [{"speaker": "系统提示", "content": "请使用选项推进剧情。", "mood": "neutral"}],
                        "next_options": ["继续剧情..."],
                        "stat_changes": {},
                        "wechat_notifications": [],
                        "npc_background_actions": [],
                        "is_end": False
                    }
                    res_text = json.dumps(parsed, ensure_ascii=False)
                else:
                    t2 = time.time()
                    llm_max_tokens = min(max_t, latency_profile["llm_max_tokens"])
                    try:
                        res_text = self.llm.generate_response(
                            system_prompt=sys_prm,
                            user_input=user_prm,
                            context="",
                            temperature=tmp,
                            top_p=top_p,
                            max_tokens=llm_max_tokens,
                            presence_penalty=pres_p,
                            frequency_penalty=freq_p
                        )
                        print(f"🛑 [耗时监控] DM 主大脑生成 JSON 耗时: {time.time() - t2:.2f} 秒")
                        parsed = self.parse_and_repair_json(res_text)
                        prefetcher.mark_non_fallback()
                    except Exception as e:
                        print(f"⚠️ [LLM Error] 实时生成异常，返回解析兜底: {e}", flush=True)
                        prefetcher.mark_fallback()
                        safe_err = str(e).replace('"', "'").replace("\n", " ")
                        parsed = self.parse_and_repair_json(json.dumps({"error": safe_err}, ensure_ascii=False))
                        res_text = json.dumps(parsed, ensure_ascii=False)

            stats_data = parsed.get("stat_changes", {})
            if not isinstance(stats_data, dict): stats_data = {} 
            
            san = max(0, min(100, san + stats_data.get("san_delta", 0)))
            money += stats_data.get("money_delta", 0)
            if stats_data.get("is_argument", False): arg_count += 1
            
            aff_changes = stats_data.get("affinity_changes", {})
            if isinstance(aff_changes, dict):
                for char_name, change_val in aff_changes.items():
                    if char_name in affinity: affinity[char_name] = max(0, min(100, affinity[char_name] + change_val))
                
            display_text = settlement_msg
            if parsed.get("narrator_transition"): display_text += f"{parsed['narrator_transition']}\n\n"
            
            dialogue_lines = []
            seq = parsed.get("dialogue_sequence", [])
            if isinstance(seq, dict): seq = [seq]
            if isinstance(seq, list):
                for t in seq:
                    if not isinstance(t, dict): continue
                    spk, cont = t.get("speaker", "神秘人"), t.get("content", "")
                    if not cont: cont = max([str(v) for k, v in t.items() if k not in ['speaker', 'mood']], key=len, default="")
                    if cont:
                        dialogue_lines.append(f"**[{spk}]** {cont}")
                        
            if dialogue_lines:
                display_text += "\n\n".join(dialogue_lines)

            # 反重复保护：同一事件若连续输出高度相同的对话，强制推进，避免死循环。
            current_sig = re.sub(r'\s+', ' ', " | ".join(dialogue_lines[:4])).strip()
            rep = self.event_repeat_state.get(next_evt.id, {"sig": "", "count": 0})
            if current_sig and current_sig == rep.get("sig"):
                rep["count"] = int(rep.get("count", 0)) + 1
            else:
                rep = {"sig": current_sig, "count": 0}
            self.event_repeat_state[next_evt.id] = rep
            
            acts = parsed.get("npc_background_actions", [])
            if isinstance(acts, dict): acts = [acts]
            if isinstance(acts, list):
                for act in acts:
                    if not isinstance(act, dict): continue
                    c_name, c_act, c_aff = act.get("character", "神秘人"), act.get("action", ""), act.get("affinity_change", 0)
                    
                    if c_name in affinity and isinstance(c_aff, (int, float)) and c_aff != 0:
                        affinity[c_name] = max(0, min(100, affinity[c_name] + c_aff))
                        aff_sign = f" (好感 {c_aff})" if c_aff < 0 else f" (好感 +{c_aff})"
                    else: 
                        aff_sign = ""
                        
                    if c_act: 
                        display_text += f"\n\n> **[暗场动态] {c_name}**: {c_act}{aff_sign}"
                        
                        if isinstance(seq, list):
                            # 将动作加上括号
                            seq.append({
                                "speaker": "system",
                                "content": f"（{c_name}{c_act}）",
                                "mood": "平静"
                            })
            
            # ========================================================
            # 真实工具调用执行层
            # ========================================================
            tool_calls = parsed.get("tool_calls", [])
            if isinstance(tool_calls, dict): tool_calls = [tool_calls]
            if isinstance(tool_calls, list):
                for tool in tool_calls:
                    if not isinstance(tool, dict): continue
                    func_name = tool.get("name", "")
                    args = tool.get("args", {})
                    
                    tool_res = self.tm.execute(func_name, args)
                    
                    if "display_text" in tool_res: display_text += tool_res["display_text"]
                    if "san_delta" in tool_res: san = max(0, min(100, san + tool_res["san_delta"]))
                    if "gpa_delta" in tool_res: gpa = max(0.0, min(4.0, gpa + tool_res["gpa_delta"]))
                    if "money_delta" in tool_res: money += tool_res["money_delta"]
            
            # 防止事件过早结束：按事件定义控制收尾窗口。
            min_turn_for_end = max(2, min(12, int(getattr(next_evt, "min_turn_for_end", 6) or 6)))
            max_turn_for_end = max(min_turn_for_end + 1, min(16, int(getattr(next_evt, "max_turn_for_end", 10) or 10)))
            if getattr(next_evt, 'is_cg', False):
                is_end = True
            elif turn < min_turn_for_end:
                is_end = False
            elif turn >= max_turn_for_end:
                is_end = True
            else:
                is_end = bool(parsed.get("is_end", False))

            # 若连续重复输出，直接收束当前事件，切到下一事件，避免玩家困在同一话题循环。
            beats = getattr(next_evt, "progress_beats", []) or []
            repeat_limit = 3 if beats else 2
            if not getattr(next_evt, 'is_cg', False) and rep.get("count", 0) >= repeat_limit:
                is_end = True
                if "僵局" not in display_text:
                    display_text += "\n\n（话题陷入重复僵局，你决定先结束这轮争论。）"
            if is_end and next_evt.id in self.event_repeat_state:
                self.event_repeat_state.pop(next_evt.id, None)

            if not getattr(next_evt, 'is_cg', False) and action_text and "（时间推移..." not in action_text and not is_prefetch:
                self.mm.save_interaction(user_input=action_text, ai_response=" ".join(dialogue_lines), user_name="陆陈安然")

            valid_notifs = []
            wechat_list = parsed.get("wechat_notifications", [])
            if isinstance(wechat_list, dict): wechat_list = [wechat_list]
            if isinstance(wechat_list, list):
                for w in wechat_list:
                    if not isinstance(w, dict): continue 
                    
                    c_name = str(w.get("chat_name", "")).strip()
                    if not c_name or c_name == "None": continue
                    
                    def simplify_name(name):
                        return re.sub(r'[【】\[\]()（）{}<>\s]', '', name)
                    
                    simplified_c_name = simplify_name(c_name)
                    matched_key = None
                    
                    for existing_key in wechat_data_dict.keys():
                        simplified_existing = simplify_name(existing_key)
                        if simplified_existing == simplified_c_name or simplified_c_name in simplified_existing:
                            matched_key = existing_key
                            break
                            
                    if matched_key:
                        c_name = matched_key 
                    else:
                        if c_name not in wechat_data_dict: 
                            wechat_data_dict[c_name] = []
                    
                    w["chat_name"] = c_name 
                    valid_notifs.append(w)

            extracted_options = self._normalize_options(parsed.get("next_options", []), next_evt)
            if getattr(next_evt, 'is_cg', False):
                extracted_options = ["继续剧情..."]
            elif is_end:
                extracted_options = ["继续剧情..."]

            # --- [START PREFETCH FOR NEXT EVENT] ---
            prefetch_ctx = {
                "chapter": chapter,
                "turn": turn,
                "active_chars": selected_chars,
                "custom_prompts": custom_prompts
            }
            # 如果是事件开头且没命中的话，尝试补刷当前事件剧本
            if use_branch_tree and turn <= 1:
                print(f"📡 [Prefetch] Triggering prefetch for CURRENT event: {next_evt.name}", flush=True)
                prefetch_ctx["event_name"] = next_evt.name
                prefetch_ctx["event_id"] = next_evt.id
                prefetch_ctx["event_description"] = next_evt.description
                prefetch_ctx["generation_mode"] = latency_profile["prefetch_mode_current"]
                self.prefetch_mgr.get_prefetcher(self.user_id, self.llm, self.pm).generate_script_async(prefetch_ctx)
            # 如果当前事件结束，尝试预取下一个阶段
            elif use_branch_tree and parsed.get("is_end", False):
                next_predicted = self.director.get_next_event(
                    {"money": money, "san": san, "hygiene": hygiene, "gpa": gpa, "reputation": reputation},
                    selected_chars, affinity
                )
                if next_predicted:
                    next_profile = self._get_latency_profile(next_predicted)
                    print(f"📡 [Prefetch] Triggering prefetch for NEXT event: {next_predicted.name}", flush=True)
                    prefetch_ctx["event_name"] = next_predicted.name
                    prefetch_ctx["event_id"] = next_predicted.id
                    prefetch_ctx["event_description"] = next_predicted.description
                    prefetch_ctx["generation_mode"] = next_profile["prefetch_mode_next"]
                    self.prefetch_mgr.get_prefetcher(self.user_id, self.llm, self.pm).generate_script_async(prefetch_ctx)

            # --- [ALWAYS PROVIDE SCRIPT IF AVAILABLE] ---
            prefetcher = self.prefetch_mgr.get_prefetcher(self.user_id, self.llm, self.pm)
            script_in_cache = prefetcher.get_cached_script(next_evt.id) if use_branch_tree else None
            final_script = None
            if script_in_cache:
                final_script = script_in_cache

            return {
                "is_game_over": False, 
                "res_text": res_text, 
                "display_text": display_text,
                "san": san, 
                "money": money, 
                "gpa": gpa, 
                "hygiene": hygiene,
                "reputation": reputation,
                "arg_count": arg_count, 
                "chapter": chapter, 
                "turn": turn, 
                "affinity": affinity, 
                "active_roommates": selected_chars,
                "current_scene": parsed.get("current_scene", "宿舍"),
                "current_evt_id": next_evt.id,
                "is_end": is_end, 
                "next_options": extracted_options, 
                "wechat_notifications": valid_notifs,
                "narrator_transition": parsed.get("narrator_transition", ""),
                "dialogue_sequence": seq if isinstance(seq, list) else [],
                "event_script": final_script, # 关键：即使当前回合是实时生成的，也要把后台生好的剧本传回前端
                "error": parsed.get("error", ""),
                "sys_prompt": sys_prm,
                "user_prompt": user_prm,
                "memory": self.mm.get_recent_history() if hasattr(self.mm, 'get_recent_history') else "模块离线",
                "relationships": self.pm.get_all_relationships() if hasattr(self.pm, 'get_all_relationships') else "模块离线",
                "tools": self.tm.get_tool_logs() if hasattr(self.tm, 'get_tool_logs') else "模块离线"
            }
        except Exception as e:
            return {
                "error": str(e),
                "sys_prompt": sys_prm if 'sys_prm' in locals() else "",
                "user_prompt": user_prm if 'user_prm' in locals() else ""
            }

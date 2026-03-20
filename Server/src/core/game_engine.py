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
        self.stability_mode = "stable"  # stable | balanced
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
        self.player_name = self.pm.get_player_name() if hasattr(self.pm, "get_player_name") else "陆陈安然"
        self.prefetch_mgr = PrefetchManager()
        self.event_completion_count = 0
        self.recent_event_ids = []
        self.prefetch_futures = {}
        self.event_repeat_state = {}
        self.recent_options_by_event = {}

    def reset(self):
        self.director.reset()
        self.player_name = self.pm.get_player_name() if hasattr(self.pm, "get_player_name") else "陆陈安然"
        self.event_completion_count = 0
        self.recent_event_ids = []
        self.event_repeat_state = {}
        self.recent_options_by_event = {}

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
        def _extract_options_from_raw(text):
            if not text:
                return []
            try:
                m = re.search(r'(?:next_options|下一步选项|选项)\s*[:：]\s*\[(.*?)\]', text, flags=re.DOTALL)
                if not m:
                    return []
                inner = m.group(1)
                inner = inner.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
                cand = re.split(r'["\']\s*,\s*["\']|[,，;\n]+', inner)
                out = []
                for c in cand:
                    s = str(c or "").strip().strip('"').strip("'").strip()
                    if s:
                        out.append(s)
                # 去重保序
                dedup = []
                seen = set()
                for o in out:
                    key = re.sub(r"\s+", " ", o)
                    if key not in seen:
                        seen.add(key)
                        dedup.append(o)
                return dedup[:4]
            except Exception:
                return []

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

            rescued_options = _extract_options_from_raw(raw_text)
            return {
                "narrator_transition": "（系统受到干扰，尝试理清思绪...）",
                "current_scene": "未知",
                "dialogue_sequence": [{"speaker": "系统提示", "content": "（由于未知干扰，当前对话解析失败，请检查参数面板中的“原始输出”查明原因。）", "mood": "neutral"}],
                "npc_background_actions": [],
                "wechat_notifications": [],
                "next_options": rescued_options if rescued_options else ["【深呼吸】", "【重试】", "【继续观察】"],
                "stat_changes": {},
                "is_end": False
            }

    def _normalize_parsed_payload(self, parsed):
        """
        兼容中英文/别名键名，防止模型输出字段名漂移导致“解析成功但不生效”。
        """
        if not isinstance(parsed, dict):
            return {}

        def pick(d, keys, default=None):
            for k in keys:
                if k in d:
                    return d.get(k)
            return default

        normalized = {
            "narrator_transition": pick(parsed, ["narrator_transition", "narration", "旁白", "叙述", "过场"], ""),
            "current_scene": pick(parsed, ["current_scene", "scene", "场景"], "未知"),
            "dialogue_sequence": pick(parsed, ["dialogue_sequence", "dialogues", "对话序列", "对话"], []),
            "npc_background_actions": pick(parsed, ["npc_background_actions", "background_actions", "暗场动态", "背景动作"], []),
            "wechat_notifications": pick(parsed, ["wechat_notifications", "wechat", "微信通知", "微信消息"], []),
            "next_options": pick(parsed, ["next_options", "options", "下一步选项", "选项"], []),
            "stat_changes": pick(parsed, ["stat_changes", "stats", "属性变化", "数值变化", "状态变化"], {}),
            "effects": pick(parsed, ["effects", "effect_commands", "effects_commands", "结算命令", "效果命令"], []),
            "is_end": pick(parsed, ["is_end", "isEnd", "结束", "是否结束"], False),
            "tool_calls": pick(parsed, ["tool_calls", "tools", "工具调用"], []),
        }

        stat = normalized.get("stat_changes", {})
        if not isinstance(stat, dict):
            stat = {}
        affinity_map = pick(stat, ["affinity_changes", "affinity", "好感变化", "亲和力变化"], {})
        if isinstance(affinity_map, list):
            merged = {}
            for item in affinity_map:
                if isinstance(item, dict):
                    for k, v in item.items():
                        merged[str(k)] = v
            affinity_map = merged
        if not isinstance(affinity_map, dict):
            affinity_map = {}

        normalized["stat_changes"] = {
            "san_delta": pick(stat, ["san_delta", "sanity_delta", "san", "sanity", "理智变化", "理智值变化"], 0),
            "money_delta": pick(stat, ["money_delta", "money", "金钱变化", "资金变化"], 0),
            "is_argument": bool(pick(stat, ["is_argument", "argument", "争吵", "是否争吵"], False)),
            "affinity_changes": affinity_map
        }
        return normalized

    def _normalize_options(self, raw_options, next_evt=None):
        """
        容错解析 next_options，处理模型把多个选项粘成一个字符串的情况。
        """
        def _split_option_text(text):
            t = str(text or "").strip()
            if not t:
                return []
            chunks = re.split(r'[\n,，;；|、]+', t)
            chunks = [c.strip(" -•\t") for c in chunks if c and c.strip(" -•\t")]
            if len(chunks) <= 1:
                labeled = re.split(r'(?=(?:^|[\s])(?:[A-Da-d]|[1-4])[\.:\：、])', t)
                chunks = [c.strip(" -•\t") for c in labeled if c and c.strip(" -•\t")]
            return chunks if chunks else ([t] if t else [])

        options = []
        if isinstance(raw_options, list):
            for o in raw_options:
                if o is None:
                    continue
                options.extend(_split_option_text(o))
        elif isinstance(raw_options, str):
            options = _split_option_text(raw_options)

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

    def _diversify_options(self, event_id, options, next_evt=None):
        """
        过滤与最近一轮高度重复的选项，优先保证“剧情推进”而非原地打转。
        """
        if not isinstance(options, list):
            options = []
        options = [str(o).strip() for o in options if str(o).strip()]

        def norm(txt):
            return re.sub(r'[\s\W_]+', '', str(txt or "").lower())

        history = self.recent_options_by_event.get(event_id, [])
        recent_norm = set()
        for round_opts in history[-1:]:
            for o in round_opts:
                recent_norm.add(norm(o))

        diversified = []
        seen = set()
        for opt in options:
            n = norm(opt)
            if not n or n in seen:
                continue
            if n in recent_norm:
                continue
            diversified.append(opt)
            seen.add(n)

        fallback_pool = []
        if next_evt is not None:
            raw_evt_options = getattr(next_evt, "options", {})
            if isinstance(raw_evt_options, dict):
                fallback_pool.extend([str(v).strip() for v in raw_evt_options.values() if str(v).strip()])
        fallback_pool.extend([
            "推动当事人给出明确方案",
            "追问关键细节与真实顾虑",
            "提出折中规则先试行一晚",
            "让全员表态并记录执行",
            "暂时退一步观察后续变化"
        ])

        for cand in fallback_pool:
            n = norm(cand)
            if not n or n in seen or n in recent_norm:
                continue
            diversified.append(cand)
            seen.add(n)
            if len(diversified) >= 4:
                break

        if len(diversified) < 3:
            for cand in ["继续推进当前矛盾", "把争议转成可执行步骤", "请求第三方给建议"]:
                n = norm(cand)
                if n not in seen:
                    diversified.append(cand)
                    seen.add(n)
                if len(diversified) >= 3:
                    break

        final_options = diversified[:4]
        self.recent_options_by_event.setdefault(event_id, []).append(final_options)
        self.recent_options_by_event[event_id] = self.recent_options_by_event[event_id][-4:]
        return final_options

    def _build_json_contract(self):
        base_contract = (
            "\n\n【强制 JSON 输出协议】\n"
            "1. 仅输出一个 JSON 对象，不要输出解释、注释、Markdown 代码块。\n"
            "2. 所有 key 与字符串 value 必须使用英文双引号。\n"
            "3. dialogue_sequence 必须是数组，每项包含 speaker, content, mood。\n"
            "4. next_options 必须是 3-4 个独立字符串数组元素，不能把多个选项拼在一个字符串里。\n"
        )
        if self.stability_mode == "stable":
            base_contract += (
                "5. 【最小稳定 Schema】必须包含字段：narrator_transition, current_scene, dialogue_sequence, next_options, effects, is_end。\n"
                "6. effects 必须是字符串数组，使用以下命令格式之一：\n"
                "   - san:+N / san:-N\n"
                "   - money:+N / money:-N\n"
                "   - arg:+1（表示发生争吵计数）\n"
                "   - affinity:角色名:+N 或 affinity:角色名:-N\n"
                "   - wechat:群聊名|发送者|消息内容\n"
                "7. 稳定模式下不要输出 stat_changes / wechat_notifications / npc_background_actions / tool_calls。\n"
                "8. 优先稳定性：不要使用中文标点作为 JSON 结构符，不要省略引号。\n"
                "9. 不确定时返回空数组/false，不要省略字段。\n"
            )
        else:
            base_contract += (
                "5. 建议包含字段：narrator_transition, current_scene, dialogue_sequence, next_options, is_end。\n"
            )
        return base_contract

    def _is_payload_usable(self, parsed, next_evt=None):
        if not isinstance(parsed, dict):
            return False
        if parsed.get("error"):
            return False

        seq = parsed.get("dialogue_sequence", [])
        if isinstance(seq, dict):
            seq = [seq]
        if not isinstance(seq, list):
            return False
        valid_lines = 0
        has_parse_error_line = False
        for item in seq:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content", "") or "").strip()
            if content:
                valid_lines += 1
                if "解析失败" in content:
                    has_parse_error_line = True
        if has_parse_error_line:
            return False

        options = self._normalize_options(parsed.get("next_options", []), next_evt)
        if len(options) < 3:
            return False

        min_dialogue = 3 if self.stability_mode == "stable" else 2
        return valid_lines >= min_dialogue

    def _parse_effect_commands(self, effects):
        """
        将 effects 命令数组解析为统一结算结构。
        支持：
        - san:+2 / san:-2
        - money:+100 / money:-50
        - arg:+1
        - affinity:林飒:+3
        """
        result = {
            "san_delta": 0.0,
            "money_delta": 0.0,
            "arg_delta": 0,
            "affinity_changes": {},
            "wechat_notifications": []
        }
        if isinstance(effects, str):
            effects = [effects]
        if not isinstance(effects, list):
            return result

        for raw_cmd in effects:
            cmd = str(raw_cmd or "").strip()
            if not cmd:
                continue
            normalized = (
                cmd.replace("：", ":")
                   .replace("，", ",")
                   .replace("＋", "+")
                   .replace("－", "-")
                   .replace(" ", "")
            )
            try:
                m = re.fullmatch(r"(san|money|arg):([+-]?\d+(?:\.\d+)?)", normalized, flags=re.IGNORECASE)
                if m:
                    key = m.group(1).lower()
                    val = float(m.group(2))
                    if key == "san":
                        result["san_delta"] += val
                    elif key == "money":
                        result["money_delta"] += val
                    elif key == "arg":
                        result["arg_delta"] += int(round(val))
                    continue

                m2 = re.fullmatch(r"affinity:([^:]{1,24}):([+-]?\d+(?:\.\d+)?)", normalized, flags=re.IGNORECASE)
                if m2:
                    char_name = m2.group(1).strip()
                    delta = float(m2.group(2))
                    if char_name:
                        result["affinity_changes"][char_name] = result["affinity_changes"].get(char_name, 0.0) + delta
                    continue

                # wechat:群聊名|发送者|消息内容
                m3 = re.match(r"^wechat:(.+)$", str(raw_cmd or "").strip(), flags=re.IGNORECASE)
                if m3:
                    payload = m3.group(1).strip()
                    payload = payload.replace("｜", "|")
                    parts = [p.strip() for p in payload.split("|", 2)]
                    if len(parts) == 3:
                        chat_name, sender, message = parts
                        if chat_name and sender and message:
                            result["wechat_notifications"].append({
                                "chat_name": chat_name,
                                "sender": sender,
                                "message": message
                            })
                    continue
            except Exception:
                continue
        return result

    def play_main_turn(self, action_text, selected_chars, current_evt_id, is_transition, api_key, base_url, model, tmp, top_p, max_t, pres_p, freq_p, san, money, gpa, hygiene, reputation, arg_count, chapter, turn, affinity, wechat_data_dict, is_prefetch=False, custom_prompts=None):
        self.llm.update_config(api_key=api_key, base_url=base_url, model=model)
        player_name = self.pm.get_player_name() if hasattr(self.pm, "get_player_name") else self.player_name
        self.player_name = player_name
        effective_dialogue_mode = self.dialogue_mode
        if effective_dialogue_mode in ["tree_only", "hybrid"]:
            effective_dialogue_mode = "single_dm"
        use_branch_tree = False
        
        # --- 动态映射逻辑 ---
        roster_name_map = self.pm.get_roster_name_map() if hasattr(self.pm, "get_roster_name_map") else {}

        def get_name(cid):
            cid_key = str(cid)
            if cid_key in roster_name_map:
                return roster_name_map[cid_key]
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
        is_new_event_entry = bool(is_transition or current_evt_id == "")
        
        if is_transition or current_evt_id == "":
            if turn == 0 and not is_prefetch: 
                self.mm.clear_game_history()
                self.director.reset()
                self.director.current_chapter = chapter
                
            next_evt = self.director.get_next_event(player_stats, selected_chars, affinity)
            if not next_evt:
                # 不走全剧终：循环回到第一章继续生成新的校园日常。
                self.director.reset()
                self.director.current_chapter = 1
                chapter = 1
                next_evt = self.director.get_next_event(player_stats, selected_chars, affinity)
                if not next_evt:
                    return {"error": "事件池为空，请检查事件 CSV 配置。"}

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
                        "narrator_transition": cached_script.get("description", f" **{next_evt.name}**"),
                        "current_scene": first_turn.get("scene", "宿舍"),
                        "dialogue_sequence": first_turn.get("dialogue_sequence", []),
                        "next_options": next_options if next_options else ["继续剧情..."],
                        "stat_changes": {}, # Initial entry usually no changes
                        "is_end": first_turn.get("is_end", False),
                        "player_name": player_name,
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
                        "player_name": player_name,
                        "next_options": res_data.get("next_options", []),
                        "dialogue_sequence": res_data.get("dialogue_sequence", []),
                        "narrator_transition": res_data.get("narrator_transition", "")
                    }
            elif not is_prefetch:
                prefetcher.mark_fallback()

            turn += 1
            evt_min_turn = max(2, min(12, int(getattr(next_evt, "min_turn_for_end", 5) or 5)))
            if turn < evt_min_turn:
                pacing = "【节奏：发展】继续推进冲突，不要重复上回合同义表达。"
            else:
                pacing = "【节奏：推进】给出新信息或新动作；若已有阶段性结果可转场，但不要求完整结局。"

            beats = getattr(next_evt, "progress_beats", []) or []
            beat_hint = ""
            if beats:
                beat_idx = min(max(turn - 1, 0), len(beats) - 1)
                beat_hint = f"\n【本回合建议推进节点】{beats[beat_idx]}"
            end_signals = "、".join((getattr(next_evt, "end_signals", []) or [])[:3])
            end_hint = f"\n【收束参考】{end_signals}" if end_signals else ""

            event_context = (
                f"【事件】: {next_evt.name}"
                f"\n【回合】: {turn}"
                f"\n{pacing}"
                f"{beat_hint}{end_hint}"
                f"\n【玩家选择意图】: {action_text}"
            )

        try:
            relevant_docs = self.mm.vector_store.search(f"{next_evt.name} {action_text}", n_results=6)
            valid_lores = []
            active_plus_player = selected_chars + [player_name]
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
            "player_name": player_name,
            "rag_lore": lore_str,
            "custom_prompts": custom_prompts
        }

        sys_prm = self.pm.get_main_system_prompt(game_context)
        safe_keys = ", ".join([str(k) for k in wechat_data_dict.keys()])

        # ========================================================
        # 多智能体剧场演出阶段
        # ========================================================

        npc_chars = [c for c in selected_chars if c != player_name]
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
        
        recent_opt_hint = ""
        recent_opts = self.recent_options_by_event.get(getattr(next_evt, "id", ""), [])
        if recent_opts:
            recent_opt_hint = "\n【上一轮选项（避免复读）】" + " | ".join(recent_opts[-1])

        user_prm = (
            f"{event_context}{recent_opt_hint}\n\n【玩家角色】{player_name}\n\n【玩家意图】: {action_text}{reactions_str}\n\n"
            f"【现有微信通讯录】: {safe_keys}\n{wechat_summary}\n[状态] SAN:{san}, 资金:{money}。\n\n"
            f"{self.pm.get_main_author_note({'player_name': player_name})}"
        )

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
                parsed = self._normalize_parsed_payload(parsed)
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
                    profile_cap = int(latency_profile.get("llm_max_tokens", 1000))
                    try:
                        llm_max_tokens = int(max_t) if max_t is not None else profile_cap
                    except Exception:
                        llm_max_tokens = profile_cap
                    llm_max_tokens = max(300, min(llm_max_tokens, 2000))

                    gen_tmp = float(tmp)
                    gen_tokens = int(llm_max_tokens)
                    gen_pres = float(pres_p)
                    gen_freq = float(freq_p)
                    if self.stability_mode == "stable":
                        # 稳定模式下主动收敛采样参数，减少乱码和半截 JSON。
                        gen_tmp = max(0.3, min(gen_tmp, 0.8))
                        gen_tokens = max(1000, min(gen_tokens, 1600))
                        gen_pres = max(-0.1, min(gen_pres, 0.4))
                        gen_freq = max(0.0, min(gen_freq, 0.4))

                    parsed = None
                    res_text = ""
                    attempts = 2 if self.stability_mode == "stable" else 1
                    last_error = None
                    json_contract = self._build_json_contract()
                    try:
                        for attempt_idx in range(attempts):
                            attempt_tmp = gen_tmp
                            attempt_tokens = gen_tokens
                            attempt_pres = gen_pres
                            attempt_freq = gen_freq
                            attempt_sys = sys_prm + json_contract
                            attempt_user = user_prm

                            if attempt_idx == 1:
                                attempt_tmp = max(0.2, gen_tmp - 0.2)
                                attempt_tokens = max(1000, min(gen_tokens, 1300))
                                attempt_pres = 0.0
                                attempt_freq = 0.0
                                attempt_user = user_prm + "\n\n【重试要求】上一版 JSON 结构不稳定。请严格按协议返回完整 JSON。"

                            res_text = self.llm.generate_response(
                                system_prompt=attempt_sys,
                                user_input=attempt_user,
                                context="",
                                temperature=attempt_tmp,
                                top_p=top_p,
                                max_tokens=attempt_tokens,
                                presence_penalty=attempt_pres,
                                frequency_penalty=attempt_freq
                            )
                            parsed_candidate = self.parse_and_repair_json(res_text)
                            parsed_candidate = self._normalize_parsed_payload(parsed_candidate)
                            if self._is_payload_usable(parsed_candidate, next_evt):
                                parsed = parsed_candidate
                                break
                            parsed = parsed_candidate
                            last_error = "payload unusable"
                            print(f"⚠️ [Stability] DM 第{attempt_idx + 1}次输出结构不稳，准备重试...", flush=True)

                        print(
                            f"🛑 [耗时监控] DM 主大脑生成 JSON 耗时: {time.time() - t2:.2f} 秒 | "
                            f"max_tokens={gen_tokens} | stability={self.stability_mode}"
                        )
                        if parsed is None:
                            raise ValueError(last_error or "empty payload")
                        prefetcher.mark_non_fallback()
                    except Exception as e:
                        print(f"⚠️ [LLM Error] 实时生成异常，返回解析兜底: {e}", flush=True)
                        prefetcher.mark_fallback()
                        safe_err = str(e).replace('"', "'").replace("\n", " ")
                        parsed = self.parse_and_repair_json(json.dumps({"error": safe_err}, ensure_ascii=False))
                        parsed = self._normalize_parsed_payload(parsed)
                        res_text = json.dumps(parsed, ensure_ascii=False)

            # 新事件开场时，补充主角视角导语，避免玩家“直接进入角色台词”产生割裂感。
            if is_new_event_entry and not getattr(next_evt, 'is_cg', False):
                intro = str(parsed.get("narrator_transition", "") or "").strip()
                view_tag = f"{player_name}视角"
                if intro:
                    if view_tag not in intro:
                        parsed["narrator_transition"] = f"【{view_tag}】{intro}"
                else:
                    desc = str(getattr(next_evt, "description", "") or "").strip()
                    if len(desc) > 48:
                        desc = desc[:48] + "…"
                    parsed["narrator_transition"] = f"【{view_tag}】我环顾四周，{desc or '空气里有股将起争执的味道。'}"

            stats_data = parsed.get("stat_changes", {})
            if not isinstance(stats_data, dict):
                stats_data = {}
            effects_data = self._parse_effect_commands(parsed.get("effects", []))

            def _num(v, default=0):
                try:
                    return float(v)
                except Exception:
                    return default

            # 优先使用 effects 命令式结算；若无则回退 legacy stat_changes。
            has_effects = bool(parsed.get("effects"))
            if has_effects:
                san_delta = _num(effects_data.get("san_delta", 0), 0)
                money_delta = _num(effects_data.get("money_delta", 0), 0)
                arg_delta = int(_num(effects_data.get("arg_delta", 0), 0))
                aff_changes = effects_data.get("affinity_changes", {})
                is_argument = arg_delta > 0
            else:
                san_delta = _num(stats_data.get("san_delta", 0), 0)
                money_delta = _num(stats_data.get("money_delta", 0), 0)
                is_argument = bool(stats_data.get("is_argument", False))
                aff_changes = stats_data.get("affinity_changes", {})
                arg_delta = 1 if is_argument else 0

            san = max(0, min(100, san + san_delta))
            money += money_delta
            if arg_delta > 0:
                arg_count += arg_delta

            if isinstance(aff_changes, dict):
                for char_name, change_val in aff_changes.items():
                    if char_name in affinity:
                        delta = _num(change_val, 0)
                        affinity[char_name] = max(0, min(100, affinity[char_name] + delta))
                
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
            min_turn_for_end = max(2, min(12, int(getattr(next_evt, "min_turn_for_end", 5) or 5)))
            if getattr(next_evt, 'is_cg', False):
                is_end = True
            elif turn < min_turn_for_end:
                is_end = False
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
                self.mm.save_interaction(user_input=action_text, ai_response=" ".join(dialogue_lines), user_name=player_name)

            valid_notifs = []
            wechat_list = parsed.get("wechat_notifications", [])
            if isinstance(wechat_list, dict): wechat_list = [wechat_list]
            effect_wechat = effects_data.get("wechat_notifications", []) if isinstance(effects_data, dict) else []
            if isinstance(effect_wechat, list) and effect_wechat:
                wechat_list = wechat_list + effect_wechat
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
            else:
                extracted_options = self._diversify_options(next_evt.id, extracted_options, next_evt)

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
                "player_name": player_name,
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

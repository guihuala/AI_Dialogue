import os
import json
import re
import csv
import copy
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
from src.core.narrative_state_manager import NarrativeStateManager
from src.core.system_state_manager import SystemStateManager
from src.core.event_skeleton_engine import EventSkeletonEngine
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
        self.pm = PromptManager(user_id)
        default_player_name = self.pm.get_player_name() if hasattr(self.pm, "get_player_name") else "陆陈安然"
        self.candidate_pool = {}
        for key, obj in vars(presets_module).items():
            if isinstance(obj, CharacterProfile) and obj.Name != default_player_name:
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
        self.player_name = default_player_name
        if hasattr(self.tm, "set_player_name"):
            self.tm.set_player_name(self.player_name)
        self.narrative_state_mgr = NarrativeStateManager()
        self.system_state_mgr = SystemStateManager()
        self.skeleton_engine = EventSkeletonEngine(user_id)
        self.prefetch_mgr = PrefetchManager()
        self.event_completion_count = 0
        self.recent_event_ids = []
        self.prefetch_futures = {}
        self.event_repeat_state = {}
        self.recent_options_by_event = {}
        self.event_bound_targets = {}
        self.debug_turn_payload = str(os.getenv("DEBUG_TURN_PAYLOAD", "")).strip().lower() in {"1", "true", "yes", "on"}
        self.profile_turns = str(os.getenv("PROFILE_TURNS", "")).strip().lower() in {"1", "true", "yes", "on"}
        self.expression_only_mode = str(os.getenv("SYSTEM_EXPRESSION_ONLY", "1")).strip().lower() not in {"0", "false", "no", "off"}
        self.expression_max_tokens = max(
            280,
            min(900, int(str(os.getenv("SYSTEM_EXPRESSION_MAX_TOKENS", "420")).strip() or 420)),
        )
        self.max_game_turns = max(
            8,
            min(60, int(str(os.getenv("SYSTEM_MAX_GAME_TURNS", "20")).strip() or 20)),
        )

    def reset(self):
        self.director.reset()
        self.player_name = self.pm.get_player_name() if hasattr(self.pm, "get_player_name") else self.player_name
        if hasattr(self.tm, "set_player_name"):
            self.tm.set_player_name(self.player_name)
        if hasattr(self, "narrative_state_mgr"):
            self.narrative_state_mgr.reset()
        if hasattr(self, "system_state_mgr"):
            self.system_state_mgr.reset()
        if hasattr(self, "skeleton_engine"):
            self.skeleton_engine.reset()
        self.event_completion_count = 0
        self.recent_event_ids = []
        self.event_repeat_state = {}
        self.recent_options_by_event = {}
        self.event_bound_targets = {}

    def _replace_target_tokens(self, text, target_name):
        raw = str(text or "")
        if not raw:
            return raw
        patterns = [
            r"\[\[?\s*TARGET\s*\]?\]",
            r"\{\{\s*TARGET\s*\}\}",
            r"【\s*TARGET\s*】",
            r"<\s*TARGET\s*>",
        ]
        for pat in patterns:
            raw = re.sub(pat, str(target_name), raw, flags=re.IGNORECASE)
        return raw

    def _has_target_tokens(self, text: str) -> bool:
        if not text:
            return False
        return bool(re.search(r"\[\[?\s*TARGET\s*\]?\]|\{\{\s*TARGET\s*\}\}|【\s*TARGET\s*】|<\s*TARGET\s*>", str(text), flags=re.IGNORECASE))

    def _apply_global_turn_cap(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return payload
        try:
            turn_now = int(payload.get("turn", 0) or 0)
        except Exception:
            turn_now = 0
        if turn_now < int(self.max_game_turns):
            return payload

        payload["is_game_over"] = True
        payload["is_end"] = True
        payload["next_options"] = []
        cap_tip = f"（本局已达到 {int(self.max_game_turns)} 回合上限，先到这里。可返回主菜单开启新一局。）"
        display_text = str(payload.get("display_text", "") or "")
        if cap_tip not in display_text:
            payload["display_text"] = (display_text + "\n\n" + cap_tip).strip() if display_text else cap_tip
        return payload

    def _replace_target_in_obj(self, obj, target_name):
        if isinstance(obj, str):
            return self._replace_target_tokens(obj, target_name)
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                nk = self._replace_target_tokens(k, target_name)
                out[nk] = self._replace_target_in_obj(v, target_name)
            return out
        if isinstance(obj, list):
            return [self._replace_target_in_obj(x, target_name) for x in obj]
        return obj

    def _pick_runtime_target(self, active_chars, affinity):
        chars = [str(c).strip() for c in (active_chars or []) if str(c).strip()]
        if not chars:
            aff_keys = [str(k).strip() for k in (affinity or {}).keys() if str(k).strip()]
            if aff_keys:
                return sorted(aff_keys, key=lambda n: float((affinity or {}).get(n, 50)))[0]
            return "对方"
        rel_map = {}
        try:
            rel_map = self.narrative_state_mgr.export().get("relationship_state", {}) or {}
        except Exception:
            rel_map = {}
        ranked = []
        if isinstance(rel_map, dict):
            for name in chars:
                rel = rel_map.get(name)
                if not isinstance(rel, dict):
                    continue
                try:
                    trust = float(rel.get("trust", 50) or 50)
                except Exception:
                    trust = 50.0
                try:
                    tension = float(rel.get("tension", 50) or 50)
                except Exception:
                    tension = 50.0
                score = tension - trust * 0.6
                ranked.append((score, name))
        if ranked:
            ranked.sort(reverse=True)
            return ranked[0][1]
        try:
            return sorted(chars, key=lambda n: float((affinity or {}).get(n, 50)))[0]
        except Exception:
            return chars[0] if chars else "对方"

    def _runtime_bind_event_target(self, event_obj, active_chars, affinity):
        if not event_obj:
            return event_obj
        text_candidates = [
            str(getattr(event_obj, "name", "") or ""),
            str(getattr(event_obj, "description", "") or ""),
            str(getattr(event_obj, "opening_goal", "") or ""),
            str(getattr(event_obj, "pressure_goal", "") or ""),
            str(getattr(event_obj, "turning_goal", "") or ""),
            str(getattr(event_obj, "settlement_goal", "") or ""),
        ]
        text_candidates.extend([str(v or "") for v in (getattr(event_obj, "options", {}) or {}).values()])
        text_candidates.extend([str(v or "") for v in (getattr(event_obj, "outcomes", {}) or {}).values()])
        if not any(self._has_target_tokens(txt) for txt in text_candidates):
            fixed_dialogue = getattr(event_obj, "fixed_dialogue", None)
            if not self._has_target_tokens(json.dumps(fixed_dialogue, ensure_ascii=False) if fixed_dialogue is not None else ""):
                return event_obj

        evt_id = str(getattr(event_obj, "id", "") or "")
        target = self.event_bound_targets.get(evt_id)
        if not target:
            target = self._pick_runtime_target(active_chars, affinity)
            if target:
                self.event_bound_targets[evt_id] = target
        if not target:
            target = "对方"

        bound = copy.deepcopy(event_obj)
        for field in ["name", "description", "opening_goal", "pressure_goal", "turning_goal", "settlement_goal", "fallback_consequence"]:
            setattr(bound, field, self._replace_target_tokens(getattr(bound, field, ""), target))
        if isinstance(getattr(bound, "potential_conflicts", None), list):
            bound.potential_conflicts = [self._replace_target_tokens(x, target) for x in bound.potential_conflicts]
        if isinstance(getattr(bound, "progress_beats", None), list):
            bound.progress_beats = [self._replace_target_tokens(x, target) for x in bound.progress_beats]
        if isinstance(getattr(bound, "end_signals", None), list):
            bound.end_signals = [self._replace_target_tokens(x, target) for x in bound.end_signals]
        if isinstance(getattr(bound, "options", None), dict):
            bound.options = {k: self._replace_target_tokens(v, target) for k, v in bound.options.items()}
        if isinstance(getattr(bound, "outcomes", None), dict):
            bound.outcomes = {k: self._replace_target_tokens(v, target) for k, v in bound.outcomes.items()}
        if isinstance(getattr(bound, "fixed_dialogue", None), list):
            bound.fixed_dialogue = self._replace_target_in_obj(bound.fixed_dialogue, target)
        return bound

    def _sanitize_payload_target_tokens(self, parsed: dict, next_evt, active_chars, affinity):
        if not isinstance(parsed, dict):
            return parsed
        evt_id = str(getattr(next_evt, "id", "") or "")
        target = self.event_bound_targets.get(evt_id)
        if not target:
            target = self._pick_runtime_target(active_chars, affinity)
            if target and evt_id:
                self.event_bound_targets[evt_id] = target
        if not target:
            return parsed

        parsed["narrator_transition"] = self._replace_target_tokens(parsed.get("narrator_transition", ""), target)
        parsed["current_scene"] = self._replace_target_tokens(parsed.get("current_scene", ""), target)
        parsed["dialogue_sequence"] = self._replace_target_in_obj(parsed.get("dialogue_sequence", []), target)
        parsed["next_options"] = self._replace_target_in_obj(parsed.get("next_options", []), target)
        parsed["npc_background_actions"] = self._replace_target_in_obj(parsed.get("npc_background_actions", []), target)
        parsed["wechat_notifications"] = self._replace_target_in_obj(parsed.get("wechat_notifications", []), target)
        return parsed

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
                "dialogue_sequence": [{"speaker": "系统提示", "content": "（由于未知干扰，当前对话解析失败，请检查参数面板中的“原始输出”查明原因。）"}],
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

    def _sanitize_dialogue_sequence(self, sequence, player_name: str):
        if isinstance(sequence, dict):
            sequence = [sequence]
        if not isinstance(sequence, list):
            return []

        cleaned = []
        for item in sequence:
            if not isinstance(item, dict):
                continue

            lower_keys = {str(k).strip().lower() for k in item.keys()}
            # 过滤只包含注释/占位字段的脏对象
            if lower_keys and all(
                key.startswith("_note") or key.startswith("_comment") or "placeholder" in key
                for key in lower_keys
            ):
                continue

            speaker = str(item.get("speaker", "") or "").strip()
            content = str(item.get("content", "") or "").strip()
            if not content:
                # 从非标准字段中尽量抢救文本内容
                candidate_pairs = []
                for k, v in item.items():
                    key = str(k or "").strip()
                    if key in {"speaker", "content"}:
                        continue
                    if key.startswith("_") or "placeholder" in key.lower():
                        continue
                    val = str(v or "").strip()
                    if val:
                        candidate_pairs.append((len(val), val))
                    elif key:
                        candidate_pairs.append((len(key), key))
                if candidate_pairs:
                    content = max(candidate_pairs, key=lambda x: x[0])[1].strip()

            if not content:
                continue

            if not speaker:
                if content.startswith("(内心独白)") or content.startswith("（内心独白）") or "内心独白" in content:
                    speaker = player_name
                else:
                    speaker = "系统提示"

            cleaned.append({
                "speaker": speaker,
                "content": content,
            })

        return cleaned

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

        # 过滤泛化占位词，避免出现“继续剧情...”这类缺乏信息的按钮
        generic_tokens = {"继续剧情", "继续剧情...", "继续", "下一步", "下一轮"}
        filtered = []
        for opt in dedup:
            key = re.sub(r"[\s。.!！?？~～…]+", "", str(opt or ""))
            if key in generic_tokens:
                continue
            filtered.append(opt)
        if filtered:
            dedup = filtered

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

    def _build_transition_option(self, next_evt=None):
        evt_name = str(getattr(next_evt, "name", "") or "").strip() if next_evt is not None else ""
        if evt_name:
            return f"【进入下一幕】前往「{evt_name}」"
        return "【进入下一幕】继续前进"

    def _is_transition_choice(self, choice_text: str) -> bool:
        text = str(choice_text or "").strip()
        if not text:
            return False
        patterns = [
            "继续剧情",
            "进入下一幕",
            "下一幕",
            "转场",
            "进入下一事件",
            "继续前进",
        ]
        return any(p in text for p in patterns)

    def _diversify_options(self, event_id, options, next_evt=None):
        """
        过滤与最近一轮高度重复的选项，优先保证“剧情推进”而非原地打转。
        """
        if not isinstance(options, list):
            options = []
        options = [str(o).strip() for o in options if str(o).strip()]
        original_count = len(options)

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

        if not diversified:
            fallback_pool = []
            if next_evt is not None:
                raw_evt_options = getattr(next_evt, "options", {})
                if isinstance(raw_evt_options, dict):
                    fallback_pool.extend([str(v).strip() for v in raw_evt_options.values() if str(v).strip()])
            fallback_pool.extend([
                "推动当事人给出明确方案",
                "追问关键细节与真实顾虑",
                "提出折中规则先试行一晚",
            ])
            for cand in fallback_pool:
                n = norm(cand)
                if not n or n in seen:
                    continue
                diversified.append(cand)
                seen.add(n)
                if len(diversified) >= 3:
                    break

        if len(diversified) < min(3, max(1, original_count)):
            for cand in ["继续推进当前矛盾", "把争议转成可执行步骤", "请求第三方给建议"]:
                n = norm(cand)
                if n not in seen and n not in recent_norm:
                    diversified.append(cand)
                    seen.add(n)
                if len(diversified) >= min(3, max(1, original_count)):
                    break

        target_count = original_count if original_count > 0 else len(diversified)
        target_count = max(1, min(4, target_count))
        final_options = diversified[:target_count]
        self.recent_options_by_event.setdefault(event_id, []).append(final_options)
        self.recent_options_by_event[event_id] = self.recent_options_by_event[event_id][-4:]
        return final_options

    def _build_json_contract(self):
        base_contract = (
            "\n\n【强制 JSON 输出协议】\n"
            "1. 仅输出一个 JSON 对象，不要输出解释、注释、Markdown 代码块。\n"
            "2. 所有 key 与字符串 value 必须使用英文双引号。\n"
            "3. dialogue_sequence 必须是数组，每项只包含 speaker, content。\n"
            "4. next_options 必须是 3-4 个独立字符串数组元素，不能把多个选项拼在一个字符串里。\n"
            "4.1 next_options 不要使用“继续剧情...”这类占位词，必须是具体可执行动作。\n"
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

    def _build_expression_json_contract(self):
        return (
            "\n\n【强制短文本 JSON 协议】\n"
            "1. 仅输出一个 JSON 对象，不要输出解释、注释、Markdown。\n"
            "2. 只允许这些字段：scene_line, current_scene, dialogue_lines, options_copy, is_end, effects。\n"
            "3. scene_line 必须是一句场景叙述；dialogue_lines 必须是 3-6 条字符串。\n"
            "4. options_copy 必须是 3-4 个具体动作选项，不要输出“继续剧情”。\n"
            "5. effects 必须是字符串数组命令，可为空数组；允许命令：san/money/arg/affinity/wechat；禁止输出 stat_changes/tool_calls。\n"
            "6. 不要输出 mood 字段，不要输出多余嵌套结构。\n"
        )

    def _build_expression_system_prompt(self, player_name: str) -> str:
        return (
            "你是校园宿舍生活的叙事导演，仅负责文本表现，不负责规则结算。\n"
            f"玩家主角名：{player_name}\n"
            "输出目标：短、清晰、可推进。\n"
            "必须：\n"
            "- 场景一句话（scene_line）\n"
            "- 3-6句对话（dialogue_lines）\n"
            "- 3-4个可执行选项文案（options_copy）\n"
            "- 可选：若本轮存在明显互动后果，可在 effects 添加 0-1 条 wechat:群聊名|发送者|消息内容\n"
            "- 不输出 mood 字段，不输出解释文本。\n"
            "风格：自然口语、具体动作，不要模板腔。"
        )

    def _build_wechat_fallback_notifications(self, *, selected_chars, system_key_resolution):
        if not isinstance(system_key_resolution, dict) or not bool(system_key_resolution.get("ok", False)):
            return []
        effects = system_key_resolution.get("effects", {}) if isinstance(system_key_resolution.get("effects", {}), dict) else {}
        stage_transition = effects.get("stage_transition", {}) if isinstance(effects.get("stage_transition", {}), dict) else {}
        sender = ""
        if "char" in stage_transition and "to" in stage_transition:
            sender = str(stage_transition.get("char", "") or "").strip()
        elif isinstance(stage_transition, dict):
            for k in stage_transition.keys():
                sender = str(k or "").strip()
                if sender:
                    break
        if not sender:
            sender = str((selected_chars or ["室友"])[0] or "室友").strip() or "室友"

        attitude = str(system_key_resolution.get("attitude", "") or "").strip()
        if attitude == "支持":
            msg = "刚才谢谢你站我这边，晚点一起复盘下。"
        elif attitude == "中立":
            msg = "你刚才处理得很稳，后面我们再细聊。"
        elif attitude == "回避":
            msg = "你刚才没接话，我有点在意，等会聊聊？"
        elif attitude == "对抗":
            msg = "刚才火药味有点重，等会冷静后再谈。"
        else:
            msg = "刚才那件事我记下了，回头我们单聊。"

        return [
            {
                "chat_name": sender,
                "sender": sender,
                "message": msg,
            }
        ]

    def _build_expression_user_prompt(
        self,
        *,
        next_evt,
        action_text: str,
        system_key_resolution,
        system_daily_plan,
        selected_chars,
        system_state,
    ) -> str:
        resolved_hint = "无"
        if isinstance(system_key_resolution, dict) and system_key_resolution.get("ok"):
            resolved_hint = (
                f"event={system_key_resolution.get('event_id','')}, "
                f"choice={system_key_resolution.get('choice_id','')}, "
                f"attitude={system_key_resolution.get('attitude','')}"
            )
        day = int(((system_state or {}).get("time", {}) or {}).get("day", 1) or 1)
        week = int(((system_state or {}).get("time", {}) or {}).get("week", 1) or 1)
        mood = float((system_state or {}).get("dorm_mood", 50) or 50)
        plan_hint = self._build_system_plan_hint(system_daily_plan)
        return (
            f"【事件】{getattr(next_evt, 'name', '')}\n"
            f"【场景】{getattr(next_evt, 'description', '')}\n"
            f"【当前时间】第{week}周-第{day}天\n"
            f"【宿舍氛围】{mood:.1f}\n"
            f"【在场角色】{'、'.join(selected_chars or [])}\n"
            f"【玩家动作】{action_text}\n"
            f"【系统结算（已生效）】{resolved_hint}\n"
            f"【系统事件线索】{plan_hint}\n"
            "【写作要求】直接给短表现，不要复述设定。"
        )

    def _build_system_plan_hint(self, daily_plan) -> str:
        if not isinstance(daily_plan, dict):
            return "无"
        lines = []
        daily = daily_plan.get("daily_events", [])
        if isinstance(daily, list) and daily:
            for item in daily[:2]:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title", "")).strip()
                meta = item.get("meta", {}) if isinstance(item.get("meta"), dict) else {}
                initiator = str(meta.get("initiator", "")).strip()
                kind = str(meta.get("kind", "")).strip()
                public_line = str(meta.get("public_line", "")).strip()
                fragment = ""
                frags = meta.get("info_fragments", [])
                if isinstance(frags, list) and frags:
                    fragment = str(frags[0] or "").strip()
                seg = f"日常:{title}"
                if kind:
                    seg += f"({kind})"
                if initiator:
                    seg += f"[发起:{initiator}]"
                if public_line:
                    seg += f" {public_line}"
                if fragment:
                    seg += f" 线索:{fragment}"
                lines.append(seg.strip())
        key_evt = daily_plan.get("key_event")
        if isinstance(key_evt, dict):
            key_title = str(key_evt.get("title", "")).strip() or "关键事件"
            opts = key_evt.get("options", [])
            opt_text = []
            if isinstance(opts, list):
                for x in opts[:3]:
                    if isinstance(x, dict):
                        att = str(x.get("attitude", "")).strip()
                        if att:
                            opt_text.append(att)
            lines.append(f"关键:{key_title} 可选[{ '/'.join(opt_text) if opt_text else '待决策'}]")
        if daily_plan.get("key_event_resolved"):
            lines.append("关键事件已结算")
        if not lines:
            return "无明显系统事件"
        return "；".join(lines[:3])

    def _format_weekly_summary_banner(self, weekly_summary) -> str:
        if not isinstance(weekly_summary, dict):
            return ""
        title = str(weekly_summary.get("title", "") or "").strip() or "本周总结"
        mood = weekly_summary.get("dorm_mood", {}) if isinstance(weekly_summary.get("dorm_mood"), dict) else {}
        trend = str(mood.get("trend", "平稳") or "平稳")
        delta = float(mood.get("delta", 0) or 0)
        sign = "+" if delta >= 0 else ""
        highlights = weekly_summary.get("highlights", [])
        if not isinstance(highlights, list):
            highlights = []
        lines = [f"【{title}】", f"- 宿舍氛围：{trend}（{sign}{round(delta, 1)}）"]
        for item in highlights[:3]:
            text = str(item or "").strip()
            if text:
                lines.append(f"- {text}")
        return "\n".join(lines)

    def _get_llm_usage_snapshot(self):
        usage = getattr(self.llm, "last_usage", {}) if hasattr(self, "llm") else {}
        if not isinstance(usage, dict):
            usage = {}
        model = str(usage.get("model", "") or getattr(self.llm, "model", "") or "").strip()
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        def _to_int(v):
            try:
                return int(v)
            except Exception:
                return None
        return {
            "model": model,
            "prompt_tokens": _to_int(prompt_tokens),
            "completion_tokens": _to_int(completion_tokens),
            "total_tokens": _to_int(total_tokens),
        }

    def _build_system_state_delta(self, before_state, after_state):
        if not isinstance(before_state, dict) or not isinstance(after_state, dict):
            return {}
        before_time = before_state.get("time", {}) if isinstance(before_state.get("time"), dict) else {}
        after_time = after_state.get("time", {}) if isinstance(after_state.get("time"), dict) else {}
        before_rel = before_state.get("relations", {}) if isinstance(before_state.get("relations"), dict) else {}
        after_rel = after_state.get("relations", {}) if isinstance(after_state.get("relations"), dict) else {}
        rel_delta = []
        for name, now in after_rel.items():
            if not isinstance(now, dict):
                continue
            old = before_rel.get(name, {}) if isinstance(before_rel.get(name), dict) else {}
            trust_delta = round(float(now.get("trust", 50) or 50) - float(old.get("trust", now.get("trust", 50)) or now.get("trust", 50) or 50), 2)
            tension_delta = round(float(now.get("tension", 50) or 50) - float(old.get("tension", now.get("tension", 50)) or now.get("tension", 50) or 50), 2)
            intimacy_delta = round(float(now.get("intimacy", 30) or 30) - float(old.get("intimacy", now.get("intimacy", 30)) or now.get("intimacy", 30) or 30), 2)
            old_stage = str(old.get("stage", now.get("stage", "普通")) or now.get("stage", "普通"))
            new_stage = str(now.get("stage", "普通") or "普通")
            if any(abs(v) >= 0.01 for v in [trust_delta, tension_delta, intimacy_delta]) or old_stage != new_stage:
                rel_delta.append({
                    "name": str(name),
                    "trust_delta": trust_delta,
                    "tension_delta": tension_delta,
                    "intimacy_delta": intimacy_delta,
                    "stage_from": old_stage,
                    "stage_to": new_stage,
                })
        rel_delta.sort(key=lambda x: abs(float(x.get("trust_delta", 0))) + abs(float(x.get("tension_delta", 0))), reverse=True)
        return {
            "time": {
                "day_from": int(before_time.get("day", 1) or 1),
                "day_to": int(after_time.get("day", 1) or 1),
                "week_from": int(before_time.get("week", 1) or 1),
                "week_to": int(after_time.get("week", 1) or 1),
            },
            "dorm_mood_delta": round(float(after_state.get("dorm_mood", 50) or 50) - float(before_state.get("dorm_mood", 50) or 50), 2),
            "relation_deltas": rel_delta[:6],
        }

    def _normalize_expression_payload(self, parsed, next_evt=None, player_name: str = ""):
        if not isinstance(parsed, dict):
            parsed = {}
        def _clean_speaker(raw_speaker: str) -> str:
            spk = str(raw_speaker or "").strip()
            if not spk:
                return player_name or "旁白"
            spk = re.sub(
                r"(压低声音说|小声嘀咕|清了清嗓子|回头应了声|转向你|看向你|轻声说|低声说|问道|说道|喊道|应了声)$",
                "",
                spk,
            ).strip(" ，。:：'\"“”‘’")
            if not spk:
                return player_name or "旁白"
            if len(spk) > 10:
                return player_name or "旁白"
            if spk in {"她", "他", "室友", "对方"}:
                return player_name or "旁白"
            return spk

        scene_line = str(parsed.get("scene_line", "") or parsed.get("narrator_transition", "") or "").strip()
        current_scene = str(parsed.get("current_scene", "") or parsed.get("scene", "") or "宿舍").strip() or "宿舍"
        dialogue_lines = parsed.get("dialogue_lines", [])
        legacy_dialogue = parsed.get("dialogue_sequence", [])
        if isinstance(dialogue_lines, str):
            dialogue_lines = [line.strip() for line in re.split(r"[\n；;]+", dialogue_lines) if line.strip()]
        if not isinstance(dialogue_lines, list):
            dialogue_lines = []
        dialogue_sequence = []
        for line in dialogue_lines:
            text = str(line or "").strip()
            if not text:
                continue
            m = re.match(r"^\[?([^\]:：]{1,12})\]?[：:]\s*(.+)$", text)
            if m:
                spk = _clean_speaker(str(m.group(1) or "").strip())
                cont = str(m.group(2) or "").strip()
            else:
                spk = player_name or "旁白"
                cont = text
            if cont:
                dialogue_sequence.append({"speaker": spk, "content": cont})

        # 兼容旧 schema：若模型仍返回 dialogue_sequence，直接复用其有效内容。
        if not dialogue_sequence:
            if isinstance(legacy_dialogue, dict):
                legacy_dialogue = [legacy_dialogue]
            if isinstance(legacy_dialogue, list):
                for item in legacy_dialogue:
                    if not isinstance(item, dict):
                        continue
                    spk = _clean_speaker(str(item.get("speaker", "") or "").strip())
                    cont = str(item.get("content", "") or "").strip()
                    if cont:
                        dialogue_sequence.append({"speaker": spk, "content": cont})

        if not dialogue_sequence:
            default_name = player_name or "我"
            dialogue_sequence = [
                {"speaker": default_name, "content": "我先稳住情绪，观察每个人的反应。"},
                {"speaker": "室友", "content": "你先说说看，你准备怎么处理眼前这件事？"},
                {"speaker": default_name, "content": "我们先把信息说清楚，再决定下一步。"},
            ]

        options = parsed.get("options_copy", parsed.get("next_options", []))
        normalized = {
            "narrator_transition": scene_line,
            "current_scene": current_scene,
            "dialogue_sequence": dialogue_sequence,
            "npc_background_actions": [],
            "wechat_notifications": [],
            "next_options": self._normalize_options(options, next_evt),
            "stat_changes": {},
            "effects": parsed.get("effects", []),
            "is_end": bool(parsed.get("is_end", False)),
            "tool_calls": [],
        }
        return normalized

    def _build_expression_fallback_payload(
        self,
        *,
        next_evt,
        player_name: str,
        selected_chars,
        action_text: str,
        system_daily_plan,
    ):
        evt_name = str(getattr(next_evt, "name", "") or "当下事件").strip()
        evt_desc = str(getattr(next_evt, "description", "") or "宿舍里气氛有些紧绷。").strip()
        scene_line = evt_desc[:48] + ("…" if len(evt_desc) > 48 else "")
        if not scene_line:
            scene_line = "宿舍里气氛有些紧绷，大家都在等你表态。"

        lead_npc = str((selected_chars or ["室友"])[0]).strip() or "室友"
        plan_hint = self._build_system_plan_hint(system_daily_plan)
        action_hint = str(action_text or "先听听大家想法").strip()
        if len(action_hint) > 22:
            action_hint = action_hint[:22] + "…"

        dialogue_sequence = [
            {"speaker": player_name or "我", "content": f"围绕「{evt_name}」，我先把注意力放回眼前。"},
            {"speaker": lead_npc, "content": f"你刚才提到“{action_hint}”，那你是想现在就推进吗？"},
            {"speaker": player_name or "我", "content": f"先按眼下线索走一步：{plan_hint or '把分歧摊开说清楚'}。"},
        ]

        raw_evt_options = getattr(next_evt, "options", {}) if next_evt is not None else {}
        options_seed = []
        if isinstance(raw_evt_options, dict):
            options_seed = [str(v).strip() for v in raw_evt_options.values() if str(v).strip()]
        if not options_seed:
            options_seed = ["先澄清事实再表态", "先安抚情绪再谈方案", "先把任务拆成可执行步骤"]
        options = self._normalize_options(options_seed, next_evt)
        options = self._inject_system_key_options(options, system_daily_plan)
        options = options[:4]
        if len(options) < 3:
            for opt in ["请求对方给出具体证据", "提出折中方案先试行", "暂缓争论，先完成眼前任务"]:
                if opt not in options:
                    options.append(opt)
                if len(options) >= 3:
                    break

        return {
            "narrator_transition": scene_line,
            "current_scene": str(getattr(next_evt, "description", "") or "宿舍").strip() or "宿舍",
            "dialogue_sequence": dialogue_sequence,
            "npc_background_actions": [],
            "wechat_notifications": [],
            "next_options": options,
            "stat_changes": {},
            "effects": [],
            "is_end": False,
            "tool_calls": [],
        }

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

    def _get_narrative_state_snapshot(self):
        if hasattr(self, "narrative_state_mgr") and hasattr(self.narrative_state_mgr, "export"):
            return self.narrative_state_mgr.export()
        return {}

    def _get_system_state_snapshot(self):
        if hasattr(self, "system_state_mgr") and hasattr(self.system_state_mgr, "export"):
            return self.system_state_mgr.export()
        return {}

    def _build_system_daily_plan(self, active_chars):
        try:
            if not hasattr(self, "skeleton_engine"):
                return {}
            return self.skeleton_engine.build_day_plan(
                system_state=self._get_system_state_snapshot(),
                active_chars=active_chars or [],
            )
        except Exception:
            return {}

    def _build_system_key_options(self, daily_plan):
        if not isinstance(daily_plan, dict):
            return []
        key_evt = daily_plan.get("key_event")
        if not isinstance(key_evt, dict):
            return []
        evt_id = str(key_evt.get("id", "")).strip()
        evt_title = str(key_evt.get("title", "关键事件")).strip() or "关键事件"
        options = key_evt.get("options", [])
        if not evt_id or not isinstance(options, list):
            return []
        result = []
        for item in options:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("id", "")).strip()
            attitude = str(item.get("attitude", "")).strip() or "中立"
            if not cid:
                continue
            risk_tags = []
            if bool(item.get("is_irreversible", False)):
                risk_tags.append("不可逆")
            st = item.get("stage_transition", {})
            if isinstance(st, dict) and st:
                target = str(st.get("char", "")).strip()
                to_stage = str(st.get("to", "")).strip()
                if target and to_stage:
                    risk_tags.append(f"{target}->{to_stage}")
                else:
                    risk_tags.append("阶段变化")
            suffix = f"（{' / '.join(risk_tags)}）" if risk_tags else ""
            result.append(f"【关键事件:{evt_id}:{cid}】{evt_title} - {attitude}{suffix}")
        return result

    def _inject_system_key_options(self, options, daily_plan):
        if not isinstance(options, list):
            options = []
        key_options = self._build_system_key_options(daily_plan)
        if not key_options:
            return options[:4]
        merged = []
        seen = set()
        for opt in key_options + options:
            text = str(opt or "").strip()
            if not text:
                continue
            key = re.sub(r"\s+", " ", text)
            if key in seen:
                continue
            seen.add(key)
            merged.append(text)
        merged = merged[:4]
        # 若普通选项已占满，至少保留一个关键事件入口（替换末位）。
        if key_options:
            key_set = {re.sub(r"\s+", " ", str(x or "").strip()) for x in key_options if str(x or "").strip()}
            has_key = any(re.sub(r"\s+", " ", str(x or "").strip()) in key_set for x in merged)
            if (not has_key) and merged:
                merged[-1] = key_options[0]
        return merged

    def _parse_system_key_choice(self, action_text):
        raw = str(action_text or "").strip()
        if not raw:
            return None
        m = re.match(r"^【关键事件:([^:：\]】]+):([^】\]]+)】", raw)
        if not m:
            return None
        evt_id = str(m.group(1) or "").strip()
        choice_id = str(m.group(2) or "").strip()
        if not evt_id or not choice_id:
            return None
        return {"event_id": evt_id, "choice_id": choice_id}

    def _pick_event_goal(self, event_obj, turn: int, is_new_event_entry: bool) -> str:
        if is_new_event_entry:
            return str(getattr(event_obj, "opening_goal", "") or "").strip()
        if turn <= 2:
            return str(getattr(event_obj, "pressure_goal", "") or "").strip()
        beats = getattr(event_obj, "progress_beats", []) or []
        if beats:
            beat_idx = min(max(turn - 1, 0), len(beats) - 1)
            return str(beats[beat_idx] or "").strip()
        if turn <= max(3, int(getattr(event_obj, "min_turn_for_end", 5) or 5) - 1):
            return str(getattr(event_obj, "turning_goal", "") or "").strip()
        return str(getattr(event_obj, "settlement_goal", "") or "").strip()

    def _build_event_story_brief(self, event_obj, player_name: str, affinity: dict, active_chars: list, turn: int, is_new_event_entry: bool) -> str:
        lines = ["【本事件戏剧驱动】"]
        tags = [str(item).strip() for item in (getattr(event_obj, "narrative_tags", []) or []) if str(item).strip()]
        if tags:
            lines.append(f"- 叙事标签：{'、'.join(tags[:5])}")

        potential_conflicts = [str(item).strip() for item in (getattr(event_obj, "potential_conflicts", []) or []) if str(item).strip()]
        if potential_conflicts:
            lines.append(f"- 本轮优先放大的冲突：{'、'.join(potential_conflicts[:3])}")

        goal = self._pick_event_goal(event_obj, turn, is_new_event_entry)
        if goal:
            lines.append(f"- 当前推进目标：{goal}")

        state_hooks = [str(item).strip() for item in (getattr(event_obj, "state_hooks", []) or []) if str(item).strip()]
        if state_hooks:
            lines.append("- 状态改写提示：")
            lines.extend([f"  * {item}" for item in state_hooks[:3]])

        relationship_hooks = [str(item).strip() for item in (getattr(event_obj, "relationship_hooks", []) or []) if str(item).strip()]
        if relationship_hooks:
            lines.append("- 关系改写提示：")
            lines.extend([f"  * {item}" for item in relationship_hooks[:3]])
        else:
            relationship_lines = []
            for name in active_chars:
                if name == player_name or name not in affinity:
                    continue
                try:
                    score = float(affinity.get(name, 50))
                except Exception:
                    score = 50.0
                if score >= 70:
                    relationship_lines.append(f"{name} 这轮更容易偏向 {player_name}，必要时可以帮腔或递台阶。")
                elif score <= 30:
                    relationship_lines.append(f"{name} 这轮对 {player_name} 明显带刺，很容易借题发挥。")
            if relationship_lines:
                lines.append("- 本轮关系张力：")
                lines.extend([f"  * {item}" for item in relationship_lines[:3]])

        fallback_consequence = str(getattr(event_obj, "fallback_consequence", "") or "").strip()
        if fallback_consequence:
            lines.append(f"- 如果场面僵住，可导向：{fallback_consequence}")

        lines.append("- 演出要求：不要只复述事件描述，要让事件被当前关系状态和情绪局势重新染色。")
        return "\n".join(lines)

    def _trim_prompt_block(self, text: str, max_lines: int = 8, max_chars: int = 700) -> str:
        raw = str(text or "").strip()
        if not raw:
            return ""
        lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
        if len(lines) > max_lines:
            lines = lines[:max_lines]
        trimmed = "\n".join(lines)
        if len(trimmed) > max_chars:
            trimmed = trimmed[:max_chars].rstrip() + "…"
        return trimmed

    def _build_wechat_summary(self, wechat_data_dict, compact: bool = False) -> str:
        lines = []
        items = list((wechat_data_dict or {}).items())
        if compact:
            items = items[-2:]
        for chat_name, messages in items:
            if not messages:
                continue
            recent_msgs = messages[-1:] if compact else messages[-2:]
            for msg in recent_msgs:
                msg_content = msg[0] if msg[0] else str(msg[1]).replace("**", "")
                lines.append(f"- {chat_name}：{msg_content}")
        if not lines:
            return ""
        return "【近期微信动态】\n" + "\n".join(lines)

    def _summarize_block_sizes(self, blocks):
        summary = []
        for idx, block in enumerate(blocks, 1):
            if isinstance(block, tuple):
                label, content = block
            else:
                label, content = f"block_{idx}", block
            text = str(content or "").strip()
            if not text:
                continue
            summary.append({
                "label": label,
                "chars": len(text),
                "lines": len(text.splitlines()),
            })
        return summary

    def _build_user_prompt_sections(
        self,
        *,
        event_context: str,
        recent_opt_hint: str,
        player_name: str,
        action_text: str,
        reactions_str: str,
        event_story_brief: str,
        narrative_summary: str,
        safe_keys: str,
        wechat_summary: str,
        san,
        money,
        author_note: str,
        prompt_budget: str,
    ) -> dict:
        dynamic_blocks = [
            ("event_context", f"{event_context}{recent_opt_hint}"),
            ("player_role", f"【玩家角色】{player_name}"),
            ("player_intent", f"【玩家意图】: {action_text}{reactions_str}"),
            ("current_status", f"[状态] SAN:{san}, 资金:{money}。"),
        ]
        repeated_blocks = [
            ("event_story_brief", event_story_brief),
            ("narrative_summary", narrative_summary),
        ]
        static_blocks = [
            ("author_note", author_note),
        ]
        trimmable_blocks = []
        if safe_keys and prompt_budget == "full":
            trimmable_blocks.append(("wechat_contacts", f"【现有微信通讯录】{safe_keys}"))
        if wechat_summary:
            trimmable_blocks.append(("wechat_summary", wechat_summary))
        return {
            "static_blocks": [(k, v) for k, v in static_blocks if str(v).strip()],
            "repeated_blocks": [(k, v) for k, v in repeated_blocks if str(v).strip()],
            "dynamic_blocks": [(k, v) for k, v in dynamic_blocks if str(v).strip()],
            "trimmable_blocks": [(k, v) for k, v in trimmable_blocks if str(v).strip()],
        }

    def _compose_prompt_from_sections(self, sections: dict) -> str:
        ordered_keys = ["dynamic_blocks", "repeated_blocks", "trimmable_blocks", "static_blocks"]
        chunks = []
        for key in ordered_keys:
            for _, content in sections.get(key, []):
                text = str(content or "").strip()
                if text:
                    chunks.append(text)
        return "\n\n".join(chunks)

    def _build_prompt_diagnostics(self, system_bundle: dict, user_sections: dict, sys_prm: str, user_prm: str) -> dict:
        return {
            "system": {
                "static_blocks": self._summarize_block_sizes(system_bundle.get("static_blocks", [])),
                "repeated_blocks": self._summarize_block_sizes(system_bundle.get("repeated_blocks", [])),
                "dynamic_blocks": self._summarize_block_sizes(system_bundle.get("dynamic_blocks", [])),
                "trimmable_blocks": self._summarize_block_sizes(system_bundle.get("trimmable_blocks", [])),
                "total_chars": len(sys_prm),
                "total_lines": len(sys_prm.splitlines()),
            },
            "user": {
                "static_blocks": self._summarize_block_sizes(user_sections.get("static_blocks", [])),
                "repeated_blocks": self._summarize_block_sizes(user_sections.get("repeated_blocks", [])),
                "dynamic_blocks": self._summarize_block_sizes(user_sections.get("dynamic_blocks", [])),
                "trimmable_blocks": self._summarize_block_sizes(user_sections.get("trimmable_blocks", [])),
                "total_chars": len(user_prm),
                "total_lines": len(user_prm.splitlines()),
            },
        }

    def play_main_turn(self, action_text, selected_chars, current_evt_id, is_transition, api_key, base_url, model, tmp, top_p, max_t, pres_p, freq_p, san, money, gpa, hygiene, reputation, arg_count, chapter, turn, affinity, wechat_data_dict, is_prefetch=False, custom_prompts=None):
        turn_started_at = time.perf_counter()
        timings = {}

        def mark_timing(name: str, started_at: float):
            timings[name] = round(time.perf_counter() - started_at, 4)

        self.llm.update_config(api_key=api_key, base_url=base_url, model=model)
        player_name = self.pm.get_player_name() if hasattr(self.pm, "get_player_name") else self.player_name
        self.player_name = player_name
        if hasattr(self.tm, "set_player_name"):
            self.tm.set_player_name(player_name)
        effective_dialogue_mode = self.dialogue_mode
        use_branch_tree = effective_dialogue_mode in ["tree_only", "hybrid"]
        expression_only_mode_active = bool(self.expression_only_mode and effective_dialogue_mode != "tree_only")
        if effective_dialogue_mode in ["tree_only", "hybrid"]:
            # 分支树模式依旧由单一 DM 兜底实时生成，只是额外启用剧本预生成/缓存能力。
            effective_dialogue_mode = "single_dm"
        # 兜底：即便前端没正确传 is_transition，只要动作文本明确是转场也强制转场。
        is_transition = bool(is_transition or self._is_transition_choice(str(action_text or "")))
        
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
        if hasattr(self, "system_state_mgr"):
            try:
                self.system_state_mgr.bootstrap(
                    active_chars=selected_chars or [],
                    affinity=affinity or {},
                    chapter=int(chapter or 1),
                    event_turn=int(turn or 0),
                )
            except Exception:
                pass

        player_stats = {"money": money, "san": san, "hygiene": hygiene, "gpa": gpa, "reputation": reputation}
        settlement_msg = ""
        system_key_resolution = None
        weekly_summary = None
        system_daily_plan = self._build_system_daily_plan(selected_chars)
        parsed_key_choice = self._parse_system_key_choice(action_text)
        if parsed_key_choice and not is_prefetch and hasattr(self, "skeleton_engine") and hasattr(self, "system_state_mgr"):
            day = int((self._get_system_state_snapshot().get("time", {}) or {}).get("day", 1) or 1)
            settled = self.skeleton_engine.settle_key_choice(
                day=day,
                event_id=parsed_key_choice["event_id"],
                choice_id=parsed_key_choice["choice_id"],
            )
            if settled.get("ok"):
                effects = settled.get("effects", {})
                self.system_state_mgr.apply_external_effects(
                    effects,
                    note=f"关键事件结算：{settled.get('event_id')} / {settled.get('choice_id')}",
                )
                if hasattr(self.system_state_mgr, "set_flag"):
                    self.system_state_mgr.set_flag("last_key_event_id", settled.get("event_id"))
                    self.system_state_mgr.set_flag("last_key_choice_id", settled.get("choice_id"))
                    self.system_state_mgr.set_flag("last_key_day", day)
                system_key_resolution = settled
                att = str(settled.get("attitude", "")).strip()
                settlement_msg += f"【系统关键事件】你选择了「{att or settled.get('choice_id', '默认')}」，系统已先完成状态结算。\n\n"
                action_text = f"我对关键事件采取了{att or '既定'}态度，并准备承受后果。"
                system_daily_plan = self._build_system_daily_plan(selected_chars)

        is_new_event_entry = bool(is_transition or current_evt_id == "")
        
        if is_transition or current_evt_id == "":
            event_select_started_at = time.perf_counter()
            if turn == 0 and not is_prefetch: 
                self.mm.clear_game_history()
                self.director.reset()
                self.director.current_chapter = chapter
                
            next_evt = self.director.get_next_event(
                player_stats,
                selected_chars,
                affinity,
                self._get_narrative_state_snapshot(),
            )
            if not next_evt:
                # 不走全剧终：循环回到第一章继续生成新的校园日常。
                self.director.reset()
                self.director.current_chapter = 1
                chapter = 1
                next_evt = self.director.get_next_event(
                    player_stats,
                    selected_chars,
                    affinity,
                    self._get_narrative_state_snapshot(),
                )
                if not next_evt:
                    return {"error": "事件池为空，请检查事件 CSV 配置。"}
            next_evt = self._runtime_bind_event_target(next_evt, selected_chars, affinity)
            mark_timing("event_select", event_select_started_at)

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
                        "next_options": next_options if next_options else [self._build_transition_option(next_evt)],
                        "stat_changes": {}, # Initial entry usually no changes
                        "is_end": first_turn.get("is_end", False),
                        "player_name": player_name,
                        "event_id": next_evt.id,
                        "turn": 1,
                        "event_script": cached_script, # Return full script to frontend
                        "narrative_state": self._get_narrative_state_snapshot(),
                        "system_state": self._get_system_state_snapshot(),
                        "system_daily_plan": self._build_system_daily_plan(selected_chars),
                        "system_key_resolution": system_key_resolution,
                        "weekly_summary": None,
                        "state_delta": {},
                        "ai_usage": self._get_llm_usage_snapshot(),
                    }
            elif not is_prefetch and not getattr(next_evt, 'is_cg', False):
                prefetcher.mark_fallback()

            opening_conflicts = "、".join((getattr(next_evt, "potential_conflicts", []) or [])[:3])
            opening_conflicts = opening_conflicts or "无"
            opening_beats = getattr(next_evt, "progress_beats", []) or []
            opening_beat_hint = f"\n【建议推进节点】{opening_beats[0]}" if opening_beats else ""
            opening_goal = str(getattr(next_evt, "opening_goal", "") or "").strip()
            opening_goal_hint = f"\n【开场目标】{opening_goal}" if opening_goal else ""
            event_context = (
                f"【系统指令】开始以下事件，不要写任何开场白或过场旁白。"
                f"\n【新事件】:{next_evt.name}"
                f"\n【场景描述】:{next_evt.description}"
                f"\n【潜在冲突参考】:{opening_conflicts}"
                f"{opening_goal_hint}"
                f"{opening_beat_hint}"
            )
        else:
            event_load_started_at = time.perf_counter()
            next_evt = self.director.event_database.get(current_evt_id)
            if not next_evt:
                return {"error": "事件丢失，请重置游戏。"}
            next_evt = self._runtime_bind_event_target(next_evt, selected_chars, affinity)
            mark_timing("event_load", event_load_started_at)
            
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

                    max_turn_for_end = max(
                        3,
                        min(20, int(getattr(next_evt, "max_turn_for_end", 8) or 8)),
                    )
                    if int(res_data.get("turn", turn + 1) or (turn + 1)) >= max_turn_for_end:
                        res_data["is_end"] = True
                        if "阶段性收束" not in display_text:
                            display_text += "\n\n（本事件达到阶段性收束点，你决定先进入下一幕。）"

                    # 如果事件结束，清理缓存
                    if res_data.get("is_end"):
                        prefetcher.clear_cache(next_evt.id)

                    if hasattr(self, "narrative_state_mgr"):
                        self.narrative_state_mgr.update_after_turn(
                            player_name=player_name,
                            event_obj=next_evt,
                            action_text=action_text,
                            san=san,
                            affinity=affinity,
                            active_chars=selected_chars,
                            effects_data={
                                "san_delta": stats_data.get("san_delta", 0),
                                "money_delta": stats_data.get("money_delta", 0),
                                "arg_delta": 1 if stats_data.get("is_argument") else 0,
                                "affinity_changes": stats_data.get("affinity_changes", {}),
                            },
                            dialogue_sequence=res_data.get("dialogue_sequence", []),
                            is_end=bool(res_data.get("is_end", False)),
                        )
                        if hasattr(self, "mm") and hasattr(self.mm, "save_narrative_milestones"):
                            try:
                                new_milestones = self.narrative_state_mgr.consume_new_milestones()
                                if new_milestones:
                                    self.mm.save_narrative_milestones(
                                        new_milestones,
                                        event_name=next_evt.name,
                                        player_name=player_name,
                                    )
                            except Exception:
                                pass
                    before_system_state = self._get_system_state_snapshot()
                    if hasattr(self, "system_state_mgr"):
                        try:
                            prev_evt_id = str(current_evt_id or "").strip()
                            next_evt_id = str(getattr(next_evt, "id", "") or "").strip()
                            system_end = bool(res_data.get("is_end", False))
                            if not system_end and bool(is_transition) and prev_evt_id and next_evt_id and prev_evt_id != next_evt_id:
                                # P3: 转场且事件切换时，系统时间应推进，避免 day/week 长期停滞。
                                system_end = True
                            self.system_state_mgr.update_after_turn(
                                active_chars=selected_chars,
                                affinity=affinity,
                                chapter=chapter,
                                event_turn=int(res_data.get("turn", turn + 1) or (turn + 1)),
                                effects_data={
                                    "san_delta": stats_data.get("san_delta", 0),
                                    "money_delta": stats_data.get("money_delta", 0),
                                    "arg_delta": 1 if stats_data.get("is_argument") else 0,
                                    "affinity_changes": stats_data.get("affinity_changes", {}),
                                },
                                event_id=getattr(next_evt, "id", ""),
                                event_name=getattr(next_evt, "name", ""),
                                is_end=system_end,
                            )
                            if hasattr(self.system_state_mgr, "consume_weekly_summary"):
                                weekly_summary = self.system_state_mgr.consume_weekly_summary()
                        except Exception:
                            pass
                    after_system_state = self._get_system_state_snapshot()
                    state_delta = self._build_system_state_delta(before_system_state, after_system_state)
                    if isinstance(weekly_summary, dict):
                        banner = self._format_weekly_summary_banner(weekly_summary)
                        if banner:
                            display_text = banner + "\n\n" + display_text
                    cached_wechat_notifications = []
                    stat_wechat = stats_data.get("wechat_notifications", []) if isinstance(stats_data, dict) else []
                    if isinstance(stat_wechat, list):
                        cached_wechat_notifications.extend([w for w in stat_wechat if isinstance(w, dict)])
                    if not cached_wechat_notifications:
                        cached_wechat_notifications = self._build_wechat_fallback_notifications(
                            selected_chars=selected_chars,
                            system_key_resolution=system_key_resolution,
                        )

                    return self._apply_global_turn_cap({
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
                        "narrator_transition": res_data.get("narrator_transition", ""),
                        "narrative_state": self._get_narrative_state_snapshot(),
                        "system_state": after_system_state,
                        "system_daily_plan": self._build_system_daily_plan(selected_chars),
                        "system_key_resolution": system_key_resolution,
                        "weekly_summary": weekly_summary,
                        "state_delta": state_delta,
                        "ai_usage": self._get_llm_usage_snapshot(),
                        "wechat_notifications": cached_wechat_notifications,
                    })
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
            current_goal = self._pick_event_goal(next_evt, turn, False)
            current_goal_hint = f"\n【本回合目标】{current_goal}" if current_goal else ""
            end_signals = "、".join((getattr(next_evt, "end_signals", []) or [])[:3])
            end_hint = f"\n【收束参考】{end_signals}" if end_signals else ""

            event_context = (
                f"【事件】: {next_evt.name}"
                f"\n【回合】: {turn}"
                f"\n{pacing}"
                f"{current_goal_hint}{beat_hint}{end_hint}"
                f"\n【玩家选择意图】: {action_text}"
            )

        lore_started_at = time.perf_counter()
        prompt_budget = "full" if self.latency_mode == "story" else "compact"
        if expression_only_mode_active:
            lore_str = ""
        else:
            try:
                relevant_docs = self.mm.vector_store.search(f"{next_evt.name} {action_text}", n_results=6)
                valid_lores = []
                active_plus_player = selected_chars + [player_name]
                for d in relevant_docs:
                    content = d.get('content', '')
                    if "语录" in content and any(f"[{c}" in content for c in active_plus_player):
                        valid_lores.append(content)
                lore_limit = 3 if prompt_budget == "full" else 2
                lore_str = "\n".join(valid_lores[:lore_limit])
            except:
                lore_str = ""
        mark_timing("lore_search", lore_started_at)

        wechat_summary = self._build_wechat_summary(wechat_data_dict, compact=(prompt_budget == "compact"))

        game_context = {
            "chapter": chapter,
            "turn": turn,
            "event_name": next_evt.name,               
            "event_description": next_evt.description, 
            "active_chars": selected_chars,
            "player_name": player_name,
            "rag_lore": lore_str,
            "custom_prompts": custom_prompts,
            "prompt_budget": prompt_budget,
        }

        prompt_started_at = time.perf_counter()
        system_prompt_bundle = self.pm.get_main_system_prompt_bundle(game_context)
        sys_prm = system_prompt_bundle.get("final_prompt", "")
        if expression_only_mode_active:
            sys_prm = self._build_expression_system_prompt(player_name)
        safe_keys = ", ".join([str(k) for k in wechat_data_dict.keys()])
        narrative_summary = ""
        if (not expression_only_mode_active) and hasattr(self, "narrative_state_mgr"):
            narrative_summary = self.narrative_state_mgr.build_prompt_summary(
                player_name=player_name,
                san=san,
                affinity=affinity,
                active_chars=selected_chars,
            )
        milestone_rag = ""
        if (not expression_only_mode_active) and hasattr(self, "mm") and hasattr(self.mm, "search_narrative_milestones"):
            try:
                milestone_docs = self.mm.search_narrative_milestones(
                    query=f"{next_evt.name} {action_text} {' '.join(selected_chars[:4])}",
                    n_results=3,
                )
                lines = []
                for doc in milestone_docs:
                    text = str((doc or {}).get("content", "") or "").strip()
                    if text:
                        lines.append(f"- {text[:120]}")
                if lines:
                    milestone_rag = "【历史关系里程碑命中】\n" + "\n".join(lines)
            except Exception:
                milestone_rag = ""
        event_story_brief = self._build_event_story_brief(
            next_evt,
            player_name=player_name,
            affinity=affinity,
            active_chars=selected_chars,
            turn=turn,
            is_new_event_entry=is_new_event_entry,
        )
        if prompt_budget == "compact":
            narrative_summary = self._trim_prompt_block(narrative_summary, max_lines=7, max_chars=520)
            event_story_brief = self._trim_prompt_block(event_story_brief, max_lines=7, max_chars=520)
            milestone_rag = self._trim_prompt_block(milestone_rag, max_lines=4, max_chars=360)
        mark_timing("prompt_build", prompt_started_at)

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
            timings["npc_reactions"] = round(time.time() - t1, 4)
                
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

        author_note = self.pm.get_main_author_note(
            {"player_name": player_name},
            compact=(prompt_budget == "compact"),
        )
        user_prompt_sections = self._build_user_prompt_sections(
            event_context=event_context,
            recent_opt_hint=recent_opt_hint,
            player_name=player_name,
            action_text=action_text,
            reactions_str=reactions_str,
            event_story_brief=event_story_brief,
            narrative_summary=narrative_summary,
            safe_keys=safe_keys,
            wechat_summary=wechat_summary,
            san=san,
            money=money,
            author_note=author_note,
            prompt_budget=prompt_budget,
        )
        if milestone_rag:
            user_prompt_sections.setdefault("trimmable_blocks", []).append(("milestone_rag", milestone_rag))
        user_prm = self._compose_prompt_from_sections(user_prompt_sections)
        if expression_only_mode_active:
            user_prm = self._build_expression_user_prompt(
                next_evt=next_evt,
                action_text=action_text,
                system_key_resolution=system_key_resolution,
                system_daily_plan=system_daily_plan,
                selected_chars=selected_chars,
                system_state=self._get_system_state_snapshot(),
            )

        try:
            if getattr(next_evt, 'is_cg', False):
                cg_dialogue = getattr(next_evt, 'fixed_dialogue', [])
                if not cg_dialogue:
                    cg_dialogue = [{"speaker": "系统提示", "content": "（剧情触发成功，但CSV对应行没有对话内容。）"}]
                # 固定剧情结束时给出明确转场按钮，避免“继续剧情...”这类占位文案。
                cg_options = [self._build_transition_option(next_evt)]

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
                        "dialogue_sequence": [{"speaker": "系统提示", "content": "请使用选项推进剧情。"}],
                        "next_options": ["【推进当前事件】让场面继续发展"],
                        "stat_changes": {},
                        "wechat_notifications": [],
                        "npc_background_actions": [],
                        "is_end": False
                    }
                    res_text = json.dumps(parsed, ensure_ascii=False)
                else:
                    t2 = time.time()
                    render_source = "llm"
                    profile_cap = int(latency_profile.get("llm_max_tokens", 1000))
                    try:
                        llm_max_tokens = int(max_t) if max_t is not None else profile_cap
                    except Exception:
                        llm_max_tokens = profile_cap
                    llm_max_tokens = max(300, min(llm_max_tokens, 2000))
                    if expression_only_mode_active:
                        llm_max_tokens = max(280, min(llm_max_tokens, self.expression_max_tokens))

                    gen_tmp = float(tmp)
                    gen_tokens = int(llm_max_tokens)
                    gen_pres = float(pres_p)
                    gen_freq = float(freq_p)
                    if self.stability_mode == "stable":
                        # 稳定模式下主动收敛采样参数，减少乱码和半截 JSON。
                        gen_tmp = max(0.3, min(gen_tmp, 0.8))
                        if self.latency_mode == "fast":
                            gen_tokens = max(550, min(gen_tokens, 850))
                        elif self.latency_mode == "story":
                            gen_tokens = max(1000, min(gen_tokens, 1600))
                        else:
                            gen_tokens = max(700, min(gen_tokens, 1200))
                        gen_pres = max(-0.1, min(gen_pres, 0.4))
                        gen_freq = max(0.0, min(gen_freq, 0.4))
                    if expression_only_mode_active:
                        gen_tmp = max(0.2, min(gen_tmp, 0.55))
                        gen_tokens = max(280, min(gen_tokens, self.expression_max_tokens))
                        gen_pres = max(-0.1, min(gen_pres, 0.15))
                        gen_freq = max(0.0, min(gen_freq, 0.15))

                    parsed = None
                    res_text = ""
                    attempts = (
                        2
                        if expression_only_mode_active
                        else (2 if (self.stability_mode == "stable" and self.latency_mode != "fast") else 1)
                    )
                    last_error = None
                    json_contract = self._build_expression_json_contract() if expression_only_mode_active else self._build_json_contract()
                    expression_user_prompt = ""
                    if expression_only_mode_active:
                        expression_user_prompt = user_prm
                    try:
                        for attempt_idx in range(attempts):
                            attempt_tmp = gen_tmp
                            attempt_tokens = gen_tokens
                            attempt_pres = gen_pres
                            attempt_freq = gen_freq
                            attempt_sys = sys_prm + json_contract
                            attempt_user = expression_user_prompt if expression_only_mode_active else user_prm

                            if attempt_idx == 1:
                                attempt_tmp = max(0.2, gen_tmp - 0.2)
                                attempt_tokens = max(1000, min(gen_tokens, 1300)) if not expression_only_mode_active else max(280, min(gen_tokens, self.expression_max_tokens))
                                attempt_pres = 0.0
                                attempt_freq = 0.0
                                if expression_only_mode_active:
                                    attempt_user = expression_user_prompt + "\n\n【重试要求】上一版结构不稳定，请严格返回短文本 JSON。"
                                else:
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
                            if expression_only_mode_active:
                                parsed_candidate = self._normalize_expression_payload(parsed_candidate, next_evt=next_evt, player_name=player_name)
                            else:
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
                        timings["llm_generate"] = round(time.time() - t2, 4)
                        if parsed is None:
                            raise ValueError(last_error or "empty payload")
                        if not self._is_payload_usable(parsed, next_evt):
                            if expression_only_mode_active:
                                parsed = self._build_expression_fallback_payload(
                                    next_evt=next_evt,
                                    player_name=player_name,
                                    selected_chars=selected_chars,
                                    action_text=action_text,
                                    system_daily_plan=system_daily_plan,
                                )
                                render_source = "expression_fallback_unusable_payload"
                                prefetcher.mark_fallback()
                            else:
                                raise ValueError("payload unusable")
                        else:
                            prefetcher.mark_non_fallback()
                    except Exception as e:
                        print(f"⚠️ [LLM Error] 实时生成异常，返回解析兜底: {e}", flush=True)
                        prefetcher.mark_fallback()
                        safe_err = str(e).replace('"', "'").replace("\n", " ")
                        if expression_only_mode_active:
                            parsed = self._build_expression_fallback_payload(
                                next_evt=next_evt,
                                player_name=player_name,
                                selected_chars=selected_chars,
                                action_text=action_text,
                                system_daily_plan=system_daily_plan,
                            )
                            parsed["error"] = safe_err
                            render_source = "expression_fallback_exception"
                        else:
                            parsed = self.parse_and_repair_json(json.dumps({"error": safe_err}, ensure_ascii=False))
                            parsed = self._normalize_parsed_payload(parsed)
                            render_source = "legacy_fallback_exception"
                        res_text = json.dumps(parsed, ensure_ascii=False)

            parsed["dialogue_sequence"] = self._sanitize_dialogue_sequence(
                parsed.get("dialogue_sequence", []),
                player_name,
            )
            parsed = self._sanitize_payload_target_tokens(parsed, next_evt, selected_chars, affinity)

            # 新事件开场时，补充主角视角导语，避免玩家“直接进入角色台词”产生割裂感。
            if is_new_event_entry and not getattr(next_evt, 'is_cg', False):
                intro = str(parsed.get("narrator_transition", "") or "").strip()
                view_tag = f"{player_name}视角"
                prev_evt_name = ""
                try:
                    prev_evt_name = str(getattr(self, "narrative_state_mgr").state.get("last_event_name", "") or "").strip()
                except Exception:
                    prev_evt_name = ""
                bridge = ""
                if prev_evt_name and prev_evt_name != str(getattr(next_evt, "name", "") or "").strip():
                    bridge = f"承接刚刚在「{prev_evt_name}」发生的事，"
                if intro:
                    intro_body = re.sub(rf"^【{re.escape(view_tag)}】", "", intro).strip()
                    parsed["narrator_transition"] = f"【{view_tag}】{bridge}{intro_body}"
                else:
                    desc = str(getattr(next_evt, "description", "") or "").strip()
                    if len(desc) > 48:
                        desc = desc[:48] + "…"
                    parsed["narrator_transition"] = f"【{view_tag}】{bridge}我环顾四周，{desc or '空气里有股将起争执的味道。'}"

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
                    if not cont: cont = max([str(v) for k, v in t.items() if k not in ['speaker']], key=len, default="")
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
            max_turn_for_end = max(min_turn_for_end + 1, min(20, int(getattr(next_evt, "max_turn_for_end", min_turn_for_end + 3) or (min_turn_for_end + 3))))
            if getattr(next_evt, 'is_cg', False):
                is_end = True
            elif turn < min_turn_for_end:
                is_end = False
            else:
                is_end = bool(parsed.get("is_end", False))

            # 强制收束保护：事件达到最大回合后不再允许继续打转。
            if not getattr(next_evt, 'is_cg', False) and turn >= max_turn_for_end:
                is_end = True
                if "阶段性收束" not in display_text:
                    display_text += "\n\n（本事件达到阶段性收束点，你决定先进入下一幕。）"

            # 若连续重复输出，直接收束当前事件，切到下一事件，避免玩家困在同一话题循环。
            beats = getattr(next_evt, "progress_beats", []) or []
            repeat_limit = 3 if beats else 2
            if not getattr(next_evt, 'is_cg', False) and rep.get("count", 0) >= repeat_limit:
                is_end = True
                if "僵局" not in display_text:
                    display_text += "\n\n（话题陷入重复僵局，你决定先结束这轮争论。）"
            if is_end and next_evt.id in self.event_repeat_state:
                self.event_repeat_state.pop(next_evt.id, None)

            narrative_update_started_at = time.perf_counter()
            before_system_state = self._get_system_state_snapshot()
            if hasattr(self, "narrative_state_mgr"):
                self.narrative_state_mgr.update_after_turn(
                    player_name=player_name,
                    event_obj=next_evt,
                    action_text=action_text,
                    san=san,
                    affinity=affinity,
                    active_chars=selected_chars,
                    effects_data=effects_data if has_effects else {
                        "san_delta": san_delta,
                        "money_delta": money_delta,
                        "arg_delta": arg_delta,
                        "affinity_changes": aff_changes if isinstance(aff_changes, dict) else {},
                    },
                    dialogue_sequence=seq if isinstance(seq, list) else [],
                    is_end=is_end,
                )
                if hasattr(self, "mm") and hasattr(self.mm, "save_narrative_milestones"):
                    try:
                        new_milestones = self.narrative_state_mgr.consume_new_milestones()
                        if new_milestones:
                            self.mm.save_narrative_milestones(
                                new_milestones,
                                event_name=next_evt.name,
                                player_name=player_name,
                            )
                    except Exception:
                        pass
            if hasattr(self, "system_state_mgr"):
                try:
                    prev_evt_id = str(current_evt_id or "").strip()
                    next_evt_id = str(getattr(next_evt, "id", "") or "").strip()
                    system_end = bool(is_end)
                    if not system_end and bool(is_transition) and prev_evt_id and next_evt_id and prev_evt_id != next_evt_id:
                        system_end = True
                    self.system_state_mgr.update_after_turn(
                        active_chars=selected_chars,
                        affinity=affinity,
                        chapter=chapter,
                        event_turn=turn,
                        effects_data=effects_data if has_effects else {
                            "san_delta": san_delta,
                            "money_delta": money_delta,
                            "arg_delta": arg_delta,
                            "affinity_changes": aff_changes if isinstance(aff_changes, dict) else {},
                        },
                        event_id=getattr(next_evt, "id", ""),
                        event_name=getattr(next_evt, "name", ""),
                        is_end=system_end,
                    )
                    if hasattr(self.system_state_mgr, "consume_weekly_summary"):
                        weekly_summary = self.system_state_mgr.consume_weekly_summary()
                except Exception:
                    pass
            after_system_state = self._get_system_state_snapshot()
            state_delta = self._build_system_state_delta(before_system_state, after_system_state)
            if isinstance(weekly_summary, dict):
                banner = self._format_weekly_summary_banner(weekly_summary)
                if banner:
                    display_text = banner + "\n\n" + display_text
            mark_timing("narrative_update", narrative_update_started_at)

            memory_save_started_at = time.perf_counter()
            if not getattr(next_evt, 'is_cg', False) and action_text and "（时间推移..." not in action_text and not is_prefetch:
                self.mm.save_interaction(user_input=action_text, ai_response=" ".join(dialogue_lines), user_name=player_name)
            mark_timing("memory_save", memory_save_started_at)

            valid_notifs = []
            wechat_list = parsed.get("wechat_notifications", [])
            if isinstance(wechat_list, dict): wechat_list = [wechat_list]
            effect_wechat = effects_data.get("wechat_notifications", []) if isinstance(effects_data, dict) else []
            if isinstance(effect_wechat, list) and effect_wechat:
                wechat_list = wechat_list + effect_wechat
            if (not isinstance(wechat_list, list) or not wechat_list) and not is_prefetch:
                wechat_list = self._build_wechat_fallback_notifications(
                    selected_chars=selected_chars,
                    system_key_resolution=system_key_resolution,
                )
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
                extracted_options = [self._build_transition_option(next_evt)]
            elif is_end:
                extracted_options = [self._build_transition_option(next_evt)]
            else:
                extracted_options = self._diversify_options(next_evt.id, extracted_options, next_evt)
                extracted_options = self._inject_system_key_options(
                    extracted_options,
                    self._build_system_daily_plan(selected_chars),
                )

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
                    selected_chars, affinity, self._get_narrative_state_snapshot()
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

            result = {
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
                "narrative_state": self._get_narrative_state_snapshot(),
                "system_state": after_system_state,
                "system_daily_plan": self._build_system_daily_plan(selected_chars),
                "system_key_resolution": system_key_resolution,
                "weekly_summary": weekly_summary,
                "state_delta": state_delta,
                "ai_usage": self._get_llm_usage_snapshot(),
                "render_source": render_source if "render_source" in locals() else "",
            }
            result = self._apply_global_turn_cap(result)
            timings["total"] = round(time.perf_counter() - turn_started_at, 4)
            if self.profile_turns:
                prompt_diagnostics = self._build_prompt_diagnostics(
                    system_prompt_bundle,
                    user_prompt_sections,
                    sys_prm,
                    user_prm,
                )
                result["prompt_diagnostics"] = prompt_diagnostics
                result["timings"] = timings
                print(
                    "[TURN PROFILE] "
                    + " | ".join(f"{k}={v}s" for k, v in timings.items()),
                    flush=True,
                )
                print(
                    "[PROMPT SIZE] "
                    f"system_chars={prompt_diagnostics['system']['total_chars']} | "
                    f"user_chars={prompt_diagnostics['user']['total_chars']}",
                    flush=True,
                )
            if self.debug_turn_payload:
                result.update({
                    "sys_prompt": sys_prm,
                    "user_prompt": user_prm,
                    "memory": self.mm.get_recent_history() if hasattr(self.mm, 'get_recent_history') else "模块离线",
                    "relationships": self.pm.get_all_relationships() if hasattr(self.pm, 'get_all_relationships') else "模块离线",
                    "tools": self.tm.get_tool_logs() if hasattr(self.tm, 'get_tool_logs') else "模块离线",
                })
            return result
        except Exception as e:
            return {
                "error": str(e),
                "sys_prompt": sys_prm if 'sys_prm' in locals() else "",
                "user_prompt": user_prm if 'user_prm' in locals() else ""
            }

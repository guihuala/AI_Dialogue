import os
import json
import threading
import time
from collections import deque
from typing import Dict, Any, Optional
from src.core.config import get_user_data_root
from src.core.prompt_manager import PromptManager
from src.services.llm_service import LLMService
from json_repair import repair_json 

class ScriptPrefetcher:
    """
    负责为特定用户预生成接下来的对话剧本。
    """
    def __init__(self, user_id: str, llm: LLMService, pm: PromptManager):
        self.user_id = user_id
        self.llm = llm
        self.pm = pm
        self.prefetch_dir = os.path.join(get_user_data_root(user_id), "prefetch")
        if not os.path.exists(self.prefetch_dir):
            os.makedirs(self.prefetch_dir)

        self._inflight_event_ids = set()
        self._lock = threading.Lock()
        self.cache_ttl_seconds = 30 * 60
        self.max_cache_files = 12
        self.metrics = {
            "cache_hit": 0,
            "cache_miss": 0,
            "cache_expired": 0,
            "script_generated": 0,
            "script_generated_fast": 0,
            "script_generated_full": 0,
            "script_parse_fail": 0,
            "fallback_to_llm": 0
        }
        self.recent_cache_reads = deque(maxlen=20)  # hit / miss
        self.recent_fallbacks = deque(maxlen=20)    # 1 / 0
        self._fallback_streak = 0

    def _script_path(self, event_id: str) -> str:
        safe_id = (event_id or "unknown").replace("/", "_")
        return os.path.join(self.prefetch_dir, f"script_{safe_id}.json")

    def _is_script_usable(self, script: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(script, dict):
            return False
        turns = script.get("turns")
        if not isinstance(turns, list) or len(turns) == 0:
            return False
        first_turn = turns[0]
        if not isinstance(first_turn, dict):
            return False
        choices = first_turn.get("player_choices", [])
        if not isinstance(choices, list) or len(choices) == 0:
            return False
        valid_choice_cnt = 0
        for c in choices:
            if not isinstance(c, dict):
                continue
            txt = str(c.get("text", "")).strip()
            if txt:
                valid_choice_cnt += 1
        return valid_choice_cnt > 0

    def _is_expired(self, data: Dict[str, Any]) -> bool:
        ts = data.get("timestamp")
        if not isinstance(ts, (int, float)):
            return True
        return (time.time() - ts) > self.cache_ttl_seconds

    def _prune_cache_files(self):
        script_files = [
            os.path.join(self.prefetch_dir, f)
            for f in os.listdir(self.prefetch_dir)
            if f.startswith("script_") and f.endswith(".json")
        ]
        if len(script_files) <= self.max_cache_files:
            return
        script_files.sort(key=lambda p: os.path.getmtime(p))
        for path in script_files[: max(0, len(script_files) - self.max_cache_files)]:
            try:
                os.remove(path)
            except:
                pass

    def get_cached_script(self, event_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if event_id:
            script_path = self._script_path(event_id)
            if not os.path.exists(script_path):
                self.metrics["cache_miss"] += 1
                return None
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if self._is_expired(data):
                    self.metrics["cache_expired"] += 1
                    self.metrics["cache_miss"] += 1
                    self.recent_cache_reads.append("miss")
                    try:
                        os.remove(script_path)
                    except:
                        pass
                    return None
                self.metrics["cache_hit"] += 1
                self.recent_cache_reads.append("hit")
                return data
            except:
                self.metrics["cache_miss"] += 1
                self.recent_cache_reads.append("miss")
                return None

        script_files = [
            os.path.join(self.prefetch_dir, f)
            for f in os.listdir(self.prefetch_dir)
            if f.startswith("script_") and f.endswith(".json")
        ]
        if not script_files:
            self.metrics["cache_miss"] += 1
            self.recent_cache_reads.append("miss")
            return None
        latest_file = max(script_files, key=lambda p: os.path.getmtime(p))
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if self._is_expired(data):
                self.metrics["cache_expired"] += 1
                self.metrics["cache_miss"] += 1
                self.recent_cache_reads.append("miss")
                try:
                    os.remove(latest_file)
                except:
                    pass
                return None
            self.metrics["cache_hit"] += 1
            self.recent_cache_reads.append("hit")
            return data
        except:
            self.metrics["cache_miss"] += 1
            self.recent_cache_reads.append("miss")
            return None

    def clear_cache(self, event_id: Optional[str] = None):
        if event_id:
            script_path = self._script_path(event_id)
            if os.path.exists(script_path):
                os.remove(script_path)
            return

        for f in os.listdir(self.prefetch_dir):
            if f.startswith("script_") and f.endswith(".json"):
                try:
                    os.remove(os.path.join(self.prefetch_dir, f))
                except:
                    pass

    def generate_script_async(self, game_context: Dict[str, Any]):
        """异步启动剧本生成任务（按事件去重）"""
        event_id = str(game_context.get("event_id", "")).strip()
        if not event_id:
            return
        generation_mode = str(game_context.get("generation_mode", "fast")).lower()

        existing = self.get_cached_script(event_id)
        if existing:
            existing_quality = str(existing.get("quality", "fast")).lower()
            # fast 模式：有缓存就不再重复生成
            if generation_mode == "fast":
                return
            # full 模式：已有 full 缓存，直接跳过
            if generation_mode == "full" and existing_quality == "full":
                return

        with self._lock:
            if event_id in self._inflight_event_ids:
                return
            self._inflight_event_ids.add(event_id)

        thread = threading.Thread(target=self._worker, args=(game_context,))
        thread.daemon = True
        thread.start()

    def generate_script_blocking(self, game_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        同步生成剧本（用于 tree_only 模式下首次命中保障）。
        """
        event_id = str(game_context.get("event_id", "")).strip()
        if not event_id:
            return None

        cached = self.get_cached_script(event_id)
        if self._is_script_usable(cached):
            return cached

        max_attempts = int(game_context.get("max_attempts", 2) or 2)
        with self._lock:
            # 双重检查，避免等待锁后重复生成
            cached = self.get_cached_script(event_id)
            if self._is_script_usable(cached):
                return cached
            self._inflight_event_ids.add(event_id)
            try:
                for _ in range(max(1, max_attempts)):
                    self._generate_full_script(game_context)
                    generated = self.get_cached_script(event_id)
                    if self._is_script_usable(generated):
                        break
                    # 生成了不可执行脚本则删除，防止污染后续命中
                    self.clear_cache(event_id)
            finally:
                self._inflight_event_ids.discard(event_id)

        final_script = self.get_cached_script(event_id)
        if self._is_script_usable(final_script):
            return final_script
        return None

    def _worker(self, ctx: Dict[str, Any]):
        event_id = str(ctx.get("event_id", "")).strip()
        try:
            self._generate_full_script(ctx)
        finally:
            if event_id:
                with self._lock:
                    self._inflight_event_ids.discard(event_id)

    def _generate_full_script(self, ctx: Dict[str, Any]):
        """
        调用 LLM 一次性生成包含后续分支的完整 deep 剧本。
        """
        event_name = ctx.get("event_name", "未知事件")
        event_desc = ctx.get("event_description", "无描述")
        active_chars = ctx.get("active_chars", [])
        generation_mode = str(ctx.get("generation_mode", "fast")).lower()
        
        sys_prompt = self.pm.get_main_system_prompt({
            **ctx,
            "event_id": ctx.get("event_id", ""),
            "mode": "script_generation"
        })
        
        # 双档生成：fast 先出可玩脚本，full 再后台精修
        if generation_mode == "full":
            script_instruction = f"""
【深度剧本创作任务】
当前事件：{event_name}
场景描述：{event_desc}
参与角色：{", ".join(active_chars)}

请为该事件创作一个完整的、多回合的剧本。剧本应包含逻辑严密的剧情发展和玩家选择分支。
输出必须是一个 JSON 对象，包含以下字段：

1. "event_id": "{ctx.get('event_id', 'evt_id')}"
2. "event_name": "{event_name}"
3. "description": "事件初始氛围和场景详细描述。"
4. "turns": [
   {{
     "turn_num": 1,
     "scene": "当前所在具体场景",
     "dialogue_sequence": [
        {{ "speaker": "角色名", "content": "对话内容" }},
        ...
     ],
     "player_choices": [
        {{
          "text": "选项 A 文字",
          "leads_to_turn": 2,
          "immediate_outcome_dialogue": [
             {{ "speaker": "角色名", "content": "（对该选项的即时反应）" }}
          ],
          "stat_changes": {{ "san_delta": -5, "money_delta": 0, "affinity_changes": {{ "角色名": 2 }} }}
        }},
        ... (提供 2-3 个选项)
     ],
     "is_end": false
   }},
   {{
     "turn_num": 2,
     ... (后续回合，根据 leads_to_turn 逻辑链接)
   }}
]

要求：
- 整个事件通常包含 3-5 个逻辑回合。
- 最后一回合请将 "is_end" 设为 true，且不提供 "player_choices"。
- 角色语言风格必须符合其在系统提示词中的设定。
- 确保 JSON 结构完整，能够 be 程序解析。

请直接返回纯 JSON。
"""
            llm_temperature = 0.7
            llm_max_tokens = 1500
        else:
            script_instruction = f"""
【快速剧本创作任务（低延迟优先）】
当前事件：{event_name}
场景描述：{event_desc}
参与角色：{", ".join(active_chars)}

请产出一个可立即游玩的紧凑剧本，优先保证结构稳定、可解析、可分支。
输出必须是一个 JSON 对象，包含：
1. "event_id": "{ctx.get('event_id', 'evt_id')}"
2. "event_name": "{event_name}"
3. "description": "事件简短描述"
4. "turns": 数组，要求：
   - 2-3 个回合
   - 每回合 2 个玩家选项
   - 每个选项都给 leads_to_turn
   - 最后一回合 is_end=true

字段格式同标准剧本：turn_num/scene/dialogue_sequence/player_choices/is_end。
请直接返回纯 JSON。
"""
            llm_temperature = 0.6
            llm_max_tokens = 800

        try:
            print(f"🌀 [Prefetch] Starting {generation_mode} script generation for User {self.user_id}...", flush=True)
            res_text = self.llm.generate_response(
                system_prompt=sys_prompt, 
                user_input=script_instruction,
                temperature=llm_temperature,
                max_tokens=llm_max_tokens
            )
            
            # 清理和修复 JSON
            script_data = self._parse_json(res_text)
            if script_data:
                script_data["timestamp"] = time.time()
                script_data["quality"] = generation_mode
                save_event_id = str(script_data.get("event_id") or ctx.get("event_id") or "unknown")
                save_path = self._script_path(save_event_id)
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(script_data, f, ensure_ascii=False, indent=2)
                if self._is_script_usable(script_data):
                    self._prune_cache_files()
                    self.metrics["script_generated"] += 1
                    if generation_mode == "full":
                        self.metrics["script_generated_full"] += 1
                    else:
                        self.metrics["script_generated_fast"] += 1
                    print(f"✅ [Prefetch] Deep script generated and cached for User {self.user_id}.", flush=True)
                else:
                    self.metrics["script_parse_fail"] += 1
                    try:
                        os.remove(save_path)
                    except:
                        pass
                    print(f"❌ [Prefetch] Script invalid (no executable first-turn choices), discarded for User {self.user_id}.", flush=True)
            else:
                self.metrics["script_parse_fail"] += 1
                print(f"❌ [Prefetch] Failed to parse JSON for User {self.user_id}.", flush=True)
        except Exception as e:
            print(f"❌ [Prefetch] Large-scale Error for User {self.user_id}: {e}", flush=True)

    def mark_fallback(self):
        self.metrics["fallback_to_llm"] += 1
        self.recent_fallbacks.append(1)
        self._fallback_streak += 1

    def mark_non_fallback(self):
        self.recent_fallbacks.append(0)
        self._fallback_streak = 0

    def should_show_fallback_hint(self) -> bool:
        # 避免每回合刷屏：首回退提示一次，后续每 3 次提示一次
        return self._fallback_streak == 1 or (self._fallback_streak > 1 and self._fallback_streak % 3 == 0)

    def get_metrics(self) -> Dict[str, Any]:
        total_reads = self.metrics["cache_hit"] + self.metrics["cache_miss"]
        hit_rate = (self.metrics["cache_hit"] / total_reads) if total_reads > 0 else 0.0
        recent_total = len(self.recent_cache_reads)
        recent_hit = sum(1 for x in self.recent_cache_reads if x == "hit")
        recent_hit_rate = (recent_hit / recent_total) if recent_total > 0 else 0.0
        recent_fb_total = len(self.recent_fallbacks)
        recent_fb = sum(self.recent_fallbacks)
        recent_fb_rate = (recent_fb / recent_fb_total) if recent_fb_total > 0 else 0.0
        return {
            **self.metrics,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "max_cache_files": self.max_cache_files,
            "cache_read_total": total_reads,
            "cache_hit_rate": round(hit_rate, 4),
            "recent_cache_window": recent_total,
            "recent_cache_hit_rate": round(recent_hit_rate, 4),
            "recent_fallback_window": recent_fb_total,
            "recent_fallback_rate": round(recent_fb_rate, 4),
            "fallback_streak": self._fallback_streak
        }

    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """使用 json_repair 修复并解析 JSON 字符串"""
        try:
            # 预处理：去掉 LLM 常见的 ```json 代码块标记
            cleaned = text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[-1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[-1].split("```")[0].strip()
            
            repaired = repair_json(cleaned)
            if not repaired:
                return None
            if isinstance(repaired, str):
                return json.loads(repaired)
            return repaired
        except Exception as e:
            print(f"⚠️ [JSON Repair] Failed to parse/repair: {e}", flush=True)
            return None

class PrefetchManager:
    _instance = None
    _lock = threading.Lock()
    fetchers: Dict[str, ScriptPrefetcher] = {}

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(PrefetchManager, cls).__new__(cls)
        return cls._instance

    def get_prefetcher(self, user_id: str, llm: LLMService, pm: PromptManager) -> ScriptPrefetcher:
        if user_id not in self.fetchers:
            self.fetchers[user_id] = ScriptPrefetcher(user_id, llm, pm)
        return self.fetchers[user_id]

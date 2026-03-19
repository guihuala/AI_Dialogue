import os
import json
import threading
import time
import queue
from typing import Dict, Any, Optional, List
from src.core.config import get_user_data_root
from src.core.prompt_manager import PromptManager
from src.services.llm_service import LLMService
from json_repair import repair_json 
from src.core.event_script import load_user_events

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
        
        self.active_script_path = os.path.join(self.prefetch_dir, "active_script.json")
        self.is_busy = False
        self._lock = threading.Lock()

    def get_cached_script(self) -> Optional[Dict[str, Any]]:
        if os.path.exists(self.active_script_path):
            try:
                with open(self.active_script_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return None

    def clear_cache(self):
        if os.path.exists(self.active_script_path):
            os.remove(self.active_script_path)

    def generate_script_async(self, game_context: Dict[str, Any]):
        """异步启动剧本生成任务"""
        if self.is_busy:
            return
        
        thread = threading.Thread(target=self._worker, args=(game_context,))
        thread.daemon = True
        thread.start()

    def _worker(self, ctx: Dict[str, Any]):
        with self._lock:
            self.is_busy = True
            try:
                self._generate_full_script(ctx)
            finally:
                self.is_busy = False

    def _generate_full_script(self, ctx: Dict[str, Any]):
        """
        调用 LLM 一次性生成包含后续分支的完整 deep 剧本。
        """
        event_name = ctx.get("event_name", "未知事件")
        event_desc = ctx.get("event_description", "无描述")
        active_chars = ctx.get("active_chars", [])
        
        sys_prompt = self.pm.get_main_system_prompt({
            **ctx,
            "event_id": ctx.get("event_id", ""),
            "mode": "script_generation"
        })
        
        # 针对 DEEP 剧本生成的特殊指令
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
        {{ "speaker": "角色名", "content": "对话内容", "mood": "表情/情绪" }},
        ...
     ],
     "player_choices": [
        {{
          "text": "选项 A 文字",
          "leads_to_turn": 2,
          "immediate_outcome_dialogue": [
             {{ "speaker": "角色名", "content": "（对该选项的即时反应）", "mood": "..." }}
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

        try:
            print(f"🌀 [Prefetch] Starting deep generation for User {self.user_id}...", flush=True)
            res_text = self.llm.generate_response(
                system_prompt=sys_prompt, 
                user_input=script_instruction,
                temperature=0.7
            )
            
            # 清理和修复 JSON
            script_data = self._parse_json(res_text)
            if script_data:
                script_data["timestamp"] = time.time()
                # 确保保存路径正确
                save_path = self.active_script_path
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(script_data, f, ensure_ascii=False, indent=2)
                print(f"✅ [Prefetch] Deep script generated and cached for User {self.user_id}.", flush=True)
            else:
                print(f"❌ [Prefetch] Failed to parse JSON for User {self.user_id}.", flush=True)
        except Exception as e:
            print(f"❌ [Prefetch] Large-scale Error for User {self.user_id}: {e}", flush=True)

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

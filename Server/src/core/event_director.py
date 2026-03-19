import random
import json
import os
import re
from collections import deque
from src.core.event_script import load_user_events
from src.core.config import get_user_events_dir

class EventDirector:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        from src.core.config import get_user_events_dir, DEFAULT_EVENTS_DIR
        self.events_dir = get_user_events_dir(user_id)
        self.default_events_dir = DEFAULT_EVENTS_DIR
        self.timeline_path = os.path.join(self.events_dir, "timeline.json")
        self.default_timeline_path = os.path.join(self.default_events_dir, "timeline.json")
        
        self.used_events = []
        self.recent_events = deque(maxlen=6)
        self.event_last_picked = {}
        self.pick_counter = 0
        self.current_chapter = 1
        self.chapter_progress = 0
        self.event_database = load_user_events(user_id)
        self.timeline_config = self._load_timeline()
        
    def reset(self):
        self.used_events = []
        self.recent_events.clear()
        self.event_last_picked = {}
        self.pick_counter = 0
        self.current_chapter = 1
        self.chapter_progress = 0
        
    def reload_timeline(self):
        """支持热更新读取"""
        self.event_database = load_user_events(self.user_id)
        self.timeline_config = self._load_timeline()

    def _load_timeline(self):
        if os.path.exists(self.timeline_path):
            try:
                with open(self.timeline_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Timeline 读取失败: {e}")
        
        # 2. Try default timeline path
        if os.path.exists(self.default_timeline_path):
            try:
                with open(self.default_timeline_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass

        default_timeline = {
            "1": ["开局", "固定", "通用", "随机或专属", "固定", "Boss"],
            "2": ["固定", "通用", "随机或专属", "固定", "Boss"],
            "3": ["固定", "通用", "条件", "随机或专属", "Boss"],
            "4": ["固定", "随机或专属", "通用", "Boss"]
        }
        
        os.makedirs(os.path.dirname(self.timeline_path), exist_ok=True)
        with open(self.timeline_path, 'w', encoding='utf-8') as f:
            json.dump(default_timeline, f, ensure_ascii=False, indent=4)
            
        return default_timeline

    def _check_conditions(self, event, player_stats, active_chars, affinity):
        """动态条件解析引擎"""
        
        # 1. 检查【专属角色】(支持逗号分隔，要求全部在场)
        if hasattr(event, 'exclusive_char') and event.exclusive_char:
            # 将中文逗号转为英文逗号并分割
            req_chars = [c.strip() for c in event.exclusive_char.replace('，', ',').split(',') if c.strip()]
            for rc in req_chars:
                if rc not in active_chars:
                    return False # 只要有一个需要的人不在场，直接毙掉

        # 2. 检查【触发条件】(支持 San<40 & 唐梦琪>60 这种复合语法)
        if hasattr(event, 'trigger_conditions') and event.trigger_conditions:
            cond_str = event.trigger_conditions.replace('＆', '&').replace('，', '&').replace(',', '&')
            conditions = [c.strip() for c in cond_str.split('&') if c.strip()]
            
            for cond in conditions:
                # 解析诸如 "San < 40" 或 "唐梦琪 >= 60"
                match = re.match(r'(.+?)(>=|<=|>|<|==|!=)(.+)', cond)
                if not match: continue
                
                key, op, val_str = match.groups()
                key = key.strip()
                try: 
                    val = float(val_str.strip())
                except: 
                    continue
                
                # 动态获取玩家状态或好感度
                # 动态获取玩家状态或好感度
                actual_val = 50 
                k_lower = key.lower()
                if k_lower in ['san', 'sanity']: actual_val = player_stats.get('san', 100)
                elif k_lower in ['money']: actual_val = player_stats.get('money', 0)
                elif k_lower in ['gpa']: actual_val = player_stats.get('gpa', 3.0)
                elif k_lower in ['hygiene']: actual_val = player_stats.get('hygiene', 100)
                elif k_lower in ['reputation', 'rep']: actual_val = player_stats.get('reputation', 50) 
                elif (k_lower in ['affinity', '好感度', '好感']) and hasattr(event, 'exclusive_char') and event.exclusive_char:
                    # 如果是角色专属事件，Affinity 代指该角色的好感度
                    first_char = [c.strip() for c in event.exclusive_char.replace('，', ',').split(',') if c.strip()][0]
                    actual_val = affinity.get(first_char, 50)
                elif key in affinity: actual_val = affinity[key]
                else: 
                    print(f"⚠️ [条件引擎警告] 未知变量 '{key}'，已拦截事件: {event.id}")
                    return False

                # 动态比较运算符
                if op == '>' and not (actual_val > val): return False
                if op == '<' and not (actual_val < val): return False
                if op == '>=' and not (actual_val >= val): return False
                if op == '<=' and not (actual_val <= val): return False
                if op == '==' and not (actual_val == val): return False
                if op == '!=' and not (actual_val != val): return False
                
        return True

    def _matches_expected_type(self, expected_type: str, event) -> bool:
        exp = str(expected_type or "")
        evt_type = str(getattr(event, "event_type", "") or "")

        is_boss = bool(getattr(event, "is_boss", False))
        is_opening = "开局" in evt_type
        is_fixed = "固定" in evt_type
        is_conditional = "条件" in evt_type
        is_persona = "专属" in evt_type
        is_general = ("通用" in evt_type or "随机" in evt_type)

        if "Boss" in exp:
            return is_boss
        if "开局" in exp:
            return is_opening
        if "固定" in exp:
            return is_fixed
        if "专属" in exp:
            return is_persona
        if "条件" in exp:
            return is_conditional
        if "通用" in exp:
            return is_general or is_fixed
        if "随机或专属" in exp:
            return is_general or is_persona or is_fixed
        return True

    def _event_weight(self, event) -> float:
        try:
            return max(0.1, float(getattr(event, "event_weight", 1.0) or 1.0))
        except Exception:
            return 1.0

    def _in_cooldown(self, event) -> bool:
        event_id = str(getattr(event, "id", "") or "")
        if not event_id:
            return False
        try:
            cd = max(0, int(getattr(event, "cooldown_turns", 2) or 2))
        except Exception:
            cd = 2
        last_picked = self.event_last_picked.get(event_id)
        if last_picked is None:
            return False
        return (self.pick_counter - last_picked) <= cd

    def _weighted_pick(self, pool):
        if not pool:
            return None
        try:
            weights = [self._event_weight(e) for e in pool]
            return random.choices(pool, weights=weights, k=1)[0]
        except Exception:
            return random.choice(pool)

    def get_next_event(self, player_stats, active_chars, affinity=None):
        if affinity is None: affinity = {}
        
        if str(self.current_chapter) not in self.timeline_config:
            return None
            
        chapter_pools = self.timeline_config[str(self.current_chapter)]
        if self.chapter_progress >= len(chapter_pools):
            self.current_chapter += 1
            self.chapter_progress = 0
            return self.get_next_event(player_stats, active_chars, affinity)
            
        expected_type = chapter_pools[self.chapter_progress]
        self.chapter_progress += 1
        boss_slot = "Boss" in str(expected_type)
        
        # 初筛：拿出当前章节的所有未触发事件
        available_events = []
        for e in self.event_database.values():
            if e.chapter != self.current_chapter:
                continue
            if not getattr(e, "allow_repeat", False) and e.id in self.used_events:
                continue
            available_events.append(e)

        if not available_events:
            print(f"🔄 [事件调度] 第 {self.current_chapter} 章可用事件为空，推进到下一章。")
            self.current_chapter += 1
            self.chapter_progress = 0
            return self.get_next_event(player_stats, active_chars, affinity)

        # 分层筛选：优先满足类型+条件+去重，其次逐步放宽，避免“定义太硬”导致卡死。
        strict_pool = [
            e for e in available_events
            if self._matches_expected_type(expected_type, e)
            and self._check_conditions(e, player_stats, active_chars, affinity)
            and (e.id not in self.recent_events)
            and (not self._in_cooldown(e))
        ]
        soft_pool = [
            e for e in available_events
            if self._matches_expected_type(expected_type, e)
            and self._check_conditions(e, player_stats, active_chars, affinity)
        ]
        chapter_pool = [
            e for e in available_events
            if self._check_conditions(e, player_stats, active_chars, affinity)
            and (e.id not in self.recent_events)
        ]
        fallback_pool = [
            e for e in available_events
            if self._check_conditions(e, player_stats, active_chars, affinity)
        ]
        emergency_pool = list(available_events)

        if not boss_slot:
            strict_pool = [e for e in strict_pool if not getattr(e, "is_boss", False)]
            soft_pool = [e for e in soft_pool if not getattr(e, "is_boss", False)]
            chapter_pool = [e for e in chapter_pool if not getattr(e, "is_boss", False)]
            fallback_pool = [e for e in fallback_pool if not getattr(e, "is_boss", False)]
            non_boss_emergency = [e for e in emergency_pool if not getattr(e, "is_boss", False)]
            if non_boss_emergency:
                emergency_pool = non_boss_emergency

        valid_pool = strict_pool or soft_pool or chapter_pool or fallback_pool or emergency_pool

        if valid_pool is emergency_pool:
            print(f"⚠️ [事件调度] 第 {self.current_chapter} 章条件过严，已启用无条件兜底。")

        chosen = self._weighted_pick(valid_pool)
        if not chosen:
            return None

        if not getattr(chosen, "allow_repeat", False):
            self.used_events.append(chosen.id)
        self.recent_events.append(chosen.id)
        self.event_last_picked[chosen.id] = self.pick_counter
        self.pick_counter += 1
        return chosen

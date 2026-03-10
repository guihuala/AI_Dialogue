import random
import json
import os
import re
from src.core.event_script import EVENT_DATABASE

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TIMELINE_PATH = os.path.join(BASE_DIR, "data", "events", "timeline.json")

class EventDirector:
    def __init__(self):
        self.used_events = []
        self.current_chapter = 1
        self.chapter_progress = 0
        self.timeline_config = self._load_timeline()
        
    def reset(self):
        self.used_events = []
        self.current_chapter = 1
        self.chapter_progress = 0
        
    def reload_timeline(self):
        """支持热更新读取"""
        self.timeline_config = self._load_timeline()

    def _load_timeline(self):
        if os.path.exists(TIMELINE_PATH):
            try:
                with open(TIMELINE_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Timeline 读取失败: {e}")
        
        default_timeline = {
            "1": ["随机或专属", "通用", "Boss"],
            "2": ["通用", "随机或专属", "Boss"],
            "3": ["条件", "通用", "Boss"],
            "4": ["随机或专属", "通用", "Boss"]
        }
        
        os.makedirs(os.path.dirname(TIMELINE_PATH), exist_ok=True)
        with open(TIMELINE_PATH, 'w', encoding='utf-8') as f:
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
        
        # 初筛：拿出当前章节的所有未触发事件
        available_events = [e for e in EVENT_DATABASE.values() if e.chapter == self.current_chapter and e.id not in self.used_events]
        
        valid_pool = []
        for e in available_events:
            # 匹配大类
            type_match = False
            if "Boss" in expected_type and getattr(e, 'is_boss', False): type_match = True
            elif "专属" in expected_type and "专属" in e.event_type: type_match = True
            elif "条件" in expected_type and "条件" in e.event_type: type_match = True
            elif "通用" in expected_type and ("通用" in e.event_type or "随机" in e.event_type): type_match = True
            elif "随机或专属" in expected_type and ("专属" in e.event_type or "通用" in e.event_type): type_match = True
            
            if not type_match:
                continue
                
            if self._check_conditions(e, player_stats, active_chars, affinity):
                valid_pool.append(e)
                
        # 兜底机制：如果严格筛选后池子空了，降级到通用池
        if not valid_pool:
            backup_pool = [e for e in available_events if "通用" in e.event_type and self._check_conditions(e, player_stats, active_chars, affinity)]
            if backup_pool:
                valid_pool = backup_pool
            else:
                # 极端兜底：连通用事件都因条件卡死了，无视条件硬抽一个（防崩溃）
                valid_pool = [e for e in available_events if "通用" in e.event_type]
                if not valid_pool:
                    print(f"🔄 [事件调度] 第 {self.current_chapter} 章事件池已枯竭，重置事件历史记录！")
                    self.used_events = [] # 穷尽了，重置历史
                    return self.get_next_event(player_stats, active_chars, affinity)

        chosen = random.choice(valid_pool)
        self.used_events.append(chosen.id)
        return chosen
import random
from src.core.event_script import EVENT_DATABASE

class EventDirector:
    def __init__(self):
        self.used_events = []
        self.current_chapter = 1
        self.chapter_progress = 0 # 当前章节进度 (0 到 4)
        self.max_events_per_chapter = 4 # 🌟 严格设定：1=CG, 2=日常, 3=日常, 4=期末考Boss
        
    def get_next_event(self, player_stats: dict, active_chars: list):
        """核心调度逻辑：强制遵循 CG -> 随机/专属 -> 随机/专属 -> Boss 的节奏"""
        self.chapter_progress += 1
        
        # 获取当前章节，且未被消耗过的事件池
        available_events = [e for e in EVENT_DATABASE.values() if e.id not in self.used_events and e.chapter == self.current_chapter]
        
        # ==========================================
        # 🎬 阶段 1: 章节开场 CG (必须是本章第 1 个事件)
        # ==========================================
        if self.chapter_progress == 1:
            # 寻找标记了 CG 的事件
            cg_events = [e for e in available_events if "CG" in e.event_type.upper() or getattr(e, 'is_cg', False)]
            if cg_events:
                evt = cg_events[0] # 按配置表顺序取第一段 CG
                self.used_events.append(evt.id)
                return evt

        # ==========================================
        # ⚔️ 阶段 4: 期末 Boss / 关底结算
        # ==========================================
        if self.chapter_progress >= self.max_events_per_chapter:
            boss_events = [e for e in available_events if getattr(e, 'is_boss', False)]
            evt = None
            if boss_events:
                evt = boss_events[0]
                self.used_events.append(evt.id)
            
            # 🌟 状态重置，偷偷把回合推进到下一章，等这个事件结束后生效
            self.chapter_progress = 0
            self.current_chapter += 1 
            
            # 如果这章忘了配 Boss，就直接无缝递归进入下一章的 CG
            return evt if evt else self.get_next_event(player_stats, active_chars)

        # ==========================================
        # 🎲 阶段 2 & 3: 日常随机池与角色专属事件
        # ==========================================
        pool = []
        
        # 1. 先尝试捞取“在场角色”的专属事件 (50% 几率触发，防止太突兀)
        ex_events = [e for e in available_events if "专属" in e.event_type and e.exclusive_char in active_chars]
        if ex_events and random.random() < 0.5:
            pool = ex_events
            
        # 2. 如果没触发专属，则捞取“通用随机池”
        if not pool:
            pool = [e for e in available_events if "通用" in e.event_type or "随机" in e.event_type]
            
        # 3. 终极兜底：如果上面的池子都空了，剩下的事件有什么抽什么
        if not pool:
            pool = available_events
            
        if pool:
            evt = random.choice(pool)
            self.used_events.append(evt.id)
            return evt
            
        return None # 剧本池被彻底抽干，游戏通关结束
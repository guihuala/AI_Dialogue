from src.core.event_script import EVENT_DATABASE, get_event
from src.models.schema import GameState, PlayerStats

class EventSystem:
    @staticmethod
    def get_current_event_info(state: GameState):
        """获取当前事件的详细对象"""
        return get_event(state.current_event_id)

    @staticmethod
    def check_game_over(stats: PlayerStats) -> tuple[bool, str]:
        """检查是否失败"""
        # 金钱判定
        if stats.money < -500: 
            return True, "因无力偿还网贷，被迫退学打工还债。"
        
        # SAN值判定
        if stats.san <= 10:
            return True, "因精神崩溃被送往医院，学业中断。"
            
        # GPA判定 (这里可以加更复杂的逻辑，比如大四才判定)
        if stats.gpa < 1.0: 
            return True, "因绩点过低被学校劝退。"
            
        return False, ""

    @staticmethod
    def advance_event(state: GameState) -> tuple[bool, str]:
        """
        结束当前事件，进入下一个事件
        """
        current_evt = get_event(state.current_event_id)
        
        if current_evt.next_event_id:
            # 切换 ID
            state.current_event_id = current_evt.next_event_id
            state.current_phase_progress = 0
            
            # 更新显示用的信息
            next_evt = get_event(current_evt.next_event_id)
            state.display_event_name = next_evt.name
            
            # 简单的日期累加逻辑（这里仅做展示更新，具体时间逻辑可视需求深化）
            state.display_date = f"事件进行中: {next_evt.name}" 
            
            return True, f"进入新阶段: {next_evt.name}"
        else:
            return False, "已到达当前版本结局"
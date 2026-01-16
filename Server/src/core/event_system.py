from src.core.event_script import EVENT_DATABASE, get_event
from src.models.schema import GameState

class EventSystem:
    @staticmethod
    def get_current_event_info(state: GameState):
        """获取当前事件的详细对象"""
        return get_event(state.current_event_id)

    @staticmethod
    def advance_event(state: GameState):
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
            # 这里可以加一个简单的日期累加逻辑，暂时简化处理
            state.display_date = f"事件进行中: {next_evt.name}" 
            
            return True, f"进入新阶段: {next_evt.name}"
        else:
            return False, "已到达当前版本结局"
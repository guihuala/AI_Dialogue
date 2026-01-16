# src/core/event_system.py

class EventSystem:
    # 固定事件表
    FIXED_EVENTS = {
        (9, 1): "入学报到 / 新学期开始",
        (10, 2): "秋季运动会",
        (12, 4): "跨年晚会筹备",
        (1, 2): "期末考试周 (冬季)",
        (6, 2): "期末考试周 (夏季)",
    }

    @staticmethod
    def check_event(month: int, week: int) -> str:
        """检查当前时间是否有固定事件"""
        key = (month, week)
        if key in EventSystem.FIXED_EVENTS:
            return EventSystem.FIXED_EVENTS[key]
        return "日常宿舍生活"

    @staticmethod
    def check_game_over(stats: 'PlayerStats') -> tuple[bool, str]:
        """检查是否失败"""
        if stats.money < -500: # 允许少量负债，太低则退学
            return True, "因无力偿还网贷，被迫退学打工还债。"
        if stats.san <= 10:
            return True, "因精神崩溃被送往医院，学业中断。"
        if stats.gpa < 1.0 and stats.is_exam_month: # 假设有标记
            return True, "因绩点过低被学校劝退。"
        return False, ""
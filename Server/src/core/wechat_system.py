class WeChatSystem:
    def __init__(self, selected_chars):
        self.channels = {}
        
        # 1. 核心宿舍大群
        if selected_chars:
            self.channels["【404 仙女下凡大群】"] = selected_chars.copy()
            
        # 2. 年级通知大群 (加入NPC)
        self.channels["【2018级编导年级大群】"] = selected_chars.copy() + ["辅导员", "班长"]
            
        # 3. 仅保留单线私聊 (直接对话，绝不搞小团体群)
        for char in selected_chars:
            self.channels[f"{char} (私聊)"] = [char]

    def init_chat_history(self):
        """初始化空的聊天记录字典"""
        return {channel: [] for channel in self.channels.keys()}
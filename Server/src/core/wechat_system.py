import itertools

class WeChatSystem:
    def __init__(self, selected_chars):
        self.channels = {}
        
        # 1. 静态白名单：全员大群
        if selected_chars:
            self.channels["【404 仙女下凡】"] = selected_chars.copy()
            
        # 2. 为每个在场角色建立私聊
        for char in selected_chars:
            self.channels[f"{char} (私聊)"] = [char]
            
        # 3. 程序化自动计算所有“小团体”排列组合
        # 只有在场人数大于等于3人时，才存在“背着某人建群”的可能
        if len(selected_chars) >= 3:
            # 遍历所有可能的组合大小（从 2 人到 N-1 人）
            for r in range(2, len(selected_chars)):
                for combo in itertools.combinations(selected_chars, r):
                    # 找出被这个小群体孤立的人（不在 combo 里的人）
                    excluded = [c for c in selected_chars if c not in combo]
                    
                    # 动态生成极其符合女大学生宫斗群的名称
                    if len(excluded) == 1:
                        group_name = f"【背着 {excluded[0]} 的小群】"
                    else:
                        group_name = f"【{'+'.join(combo)} 的私密圈】"
                        
                    # 将计算好的组合注册到频道字典中
                    self.channels[group_name] = list(combo)

    def init_chat_history(self):
        """初始化空的聊天记录字典"""
        return {ch: [] for ch in self.channels.keys()}
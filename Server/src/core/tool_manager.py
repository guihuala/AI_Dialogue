class ToolManager:
    """系统级工具箱：负责处理 AI 的所有实体工具调用"""
    
    def __init__(self, player_name: str = "陆陈安然"):
        self.call_history = []  # 初始化工具调用栈
        self.player_name = player_name or "陆陈安然"

    def set_player_name(self, player_name: str):
        self.player_name = (player_name or "").strip() or "陆陈安然"

    def get_player_name(self) -> str:
        return self.player_name
        
    def execute(self, func_name: str, args: dict) -> dict:
        """动态路由：自动寻找并执行对应的工具函数"""
        # 记录调用载荷
        self.call_history.append({"func": func_name, "args": args})
        
        method = getattr(self, func_name, None)
        if method and callable(method):
            try:
                return method(args)
            except Exception as e:
                return {"display_text": f"\n\n⚠️ **[系统异常]** 工具 '{func_name}' 执行失败: {e}\n"}
                
        return {"display_text": f"\n\n⚠️ **[系统警告]** AI 尝试调用了未知的系统工具: {func_name}\n"}

    def get_tool_logs(self) -> str:
        """导出底层工具调用历史栈"""
        if not self.call_history: 
            return "未侦测到工具挂载与调用"
        
        logs = []
        for i, record in enumerate(self.call_history[-10:]):  # 提取最近10条
            logs.append(f"[{i+1}] 接口: {record['func']} | 载荷: {record['args']}")
        return "\n".join(logs)

    # ==========================================
    # 以下是具体的工具函数实现 (新增工具只需在这里加函数即可)
    # ==========================================

    def post_to_campus_wall(self, args: dict) -> dict:
        """工具：校园表白墙系统"""
        author = args.get("author", "匿名")
        content = args.get("content", "")
        return {
            "display_text": f"\n\n📢 **【系统工具触发：校园表白墙突发】**\n> 👤 **{author}** 发布了一条动态：\n> 「{content}」\n> *(此动态在全系引发轩然大波，你的 SAN 值受到真实暴击！)*\n",
            "san_delta": -15  # 扣除 15 点 SAN 值
        }

    def sabotage_academic(self, args: dict) -> dict:
        """工具：学业背刺系统"""
        player_name = self.get_player_name()
        raw_target = str(args.get("target", "") or "").strip()
        target = raw_target or player_name
        if target in {"player", "玩家", "主角", "当前主角", "__player__"}:
            target = player_name
        method = args.get("method", "未知手段")
        res = {
            "display_text": f"\n\n⚠️ **【系统工具触发：学业背刺】**\n> {target} 的学业遭到了恶性破坏！\n> 破坏方式：{method}\n> *(系统已调用底层接口强行扣除目标 GPA！)*\n"
        }
        if target == player_name:
            res["gpa_delta"] = -0.3  # 扣除 0.3 的绩点
        return res
        
    def call_parents(self, args: dict) -> dict:
        """工具(演示新增)：打小报告扣钱"""
        caller = args.get("caller", "某人")
        return {
            "display_text": f"\n\n☎️ **【系统工具触发：跨界打小报告】**\n> {caller} 竟然直接打电话给了你的家长，添油加醋地告了一状！\n> *(你的生活费被无情扣除！)*\n",
            "money_delta": -300,
            "san_delta": -10
        }

    def phone_enqueue_message(self, args: dict) -> dict:
        """工具：向手机系统投递一条消息（结构化，不直接改主文案）"""
        chat_name = str(args.get("chat_name", "") or "").strip()
        sender = str(args.get("sender", "") or "").strip()
        content = str(args.get("content", "") or "").strip()
        if not chat_name or not sender or not content:
            return {}
        return {
            "wechat_notifications": [
                {
                    "chat_name": chat_name[:24],
                    "sender": sender[:16],
                    "message": content[:180],
                }
            ]
        }

    def memory_add_tag(self, args: dict) -> dict:
        """工具提议：写入记忆标签（不直接落库，由系统裁决）"""
        tag = str(args.get("tag", "") or "").strip()
        target = str(args.get("target", "") or "").strip()
        ttl = args.get("ttl", None)
        return {
            "proposal": {
                "kind": "memory_add_tag",
                "tag": tag,
                "target": target,
                "ttl": ttl,
            }
        }

    def relationship_apply_delta(self, args: dict) -> dict:
        """工具提议：关系状态增量（不直接结算，由系统裁决）"""
        target = str(args.get("target", "") or "").strip()
        trust = args.get("trust", 0)
        tension = args.get("tension", 0)
        intimacy = args.get("intimacy", 0)
        return {
            "proposal": {
                "kind": "relationship_apply_delta",
                "target": target,
                "trust": trust,
                "tension": tension,
                "intimacy": intimacy,
            }
        }

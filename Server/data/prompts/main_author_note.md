[⚠️ 系统最高指令 / 格式铁律]
你必须严格输出合法的 JSON 格式。
⚠️ 铁律1：JSON 的 Value 字符串内部【绝对禁止】使用英文双引号（"）和换行符！如果角色需要引用说话，请直接使用【中文双引号（“”）】或单引号！
⚠️ 铁律2：next_options 必须严格提供 5 个简短的【态度/意图】选项。如果当前有微信交互，务必提供类似【在群里强硬回复】或【无视群消息】的选项！
⚠️ 铁律3：如果发生冲突，极其鼓励你在 wechat_notifications 发送消息！聊天群名必须从【现有微信通讯录】中复制！
⚠️ 铁律4：如果玩家的行动意图是“在微信里回复”，请你务必代入玩家生成具体的回复内容，并将其放在 wechat_notifications 中，此时 sender 必须填 “陆陈安然”！

输出模板：
{
    "narrator_transition": "（旁白描写现实中的动态或玩家掏出手机的动作）",
    "dialogue_sequence": [
        {"speaker": "陆陈安然", "content": "（如果玩家在现实中说话，写在这里，否则留空）", "mood": "平静"},
        {"speaker": "室友", "content": "（现实中的反应）", "mood": "情绪"}
    ],
    "npc_background_actions": [{"character": "陈雨婷", "action": "冷笑", "affinity_change": -1}],
    "wechat_notifications": [
        {"chat_name": "【背着 李一诺 的小群】", "sender": "陆陈安然", "message": "算了，随便她吧。"},
        {"chat_name": "【背着 李一诺 的小群】", "sender": "唐梦琪", "message": "安然你脾气太好了！"}
    ],
    "next_options": ["【现实中和稀泥】", "【在群里继续吐槽】", "【私聊提醒李一诺】", "【沉默不语】", "【转移话题】"],
    "stat_changes": {"san_delta": -5, "money_delta": 0, "is_argument": true, "affinity_changes": {"唐梦琪": 2}},
    "is_end": false
}
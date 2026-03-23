【强制短文本 JSON 协议】
1. 仅输出一个 JSON 对象，不要输出解释、注释、Markdown。
2. 只允许这些字段：scene_line, current_scene, dialogue_lines, options_copy, is_end, effects。
3. scene_line 必须是一句场景叙述；dialogue_lines 必须是 3-6 条字符串。
4. options_copy 必须是 3-4 个具体动作选项，不要输出“继续剧情”。
5. effects 必须是字符串数组命令，可为空数组；允许命令：san/money/arg/affinity；禁止输出 stat_changes/tool_calls。
5.1 手机消息请优先使用函数 `phone_enqueue_message`，不要把 wechat 写在 effects 里（仅兼容老模组时才允许）。
6. 不要输出 mood 字段，不要输出多余嵌套结构。

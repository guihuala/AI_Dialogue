import gradio as gr
import pandas as pd
import json
import sys
import os
import re
from json_repair import repair_json 

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.core.presets as presets_module
from src.models.schema import CharacterProfile
from src.services.llm_service import LLMService
from src.core.memory_manager import MemoryManager
from src.core.event_director import EventDirector
from src.core.event_script import EVENT_DATABASE

try:
    from build_knowledge import build_knowledge
    build_knowledge()
except Exception as e:
    print(f"提示：请确保已手动运行过 build_knowledge.py 注入语料。({e})")

CANDIDATE_POOL = {}
for key, obj in vars(presets_module).items():
    if isinstance(obj, CharacterProfile) and obj.Name != "陆陈安然": 
        CANDIDATE_POOL[obj.Name] = obj

llm_service = LLMService()
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(base_dir, "data")
os.makedirs(data_dir, exist_ok=True)
mm = MemoryManager(os.path.join(data_dir, "profile.json"), os.path.join(data_dir, "chroma_db"), llm_service)
director = EventDirector()

# ==========================================
# 🍔 Prompt 库
# ==========================================

DEFAULT_PROMPT = """你是一个多角色大学生存游戏的 AI 跑团 DM。
[职责]
1. 维持角色人设，严格遵守【在场角色图鉴】。禁止扮演未提及的角色。
2.【意图轮盘系统】：根据玩家的【行动意图】，先代入玩家（陆陈安然）生成符合她“淡漠”人设的台词，再生成NPC反应。
3. 动态评估室友对玩家的好感度变动（affinity_changes）。
4.【暗场行动】：评估没说话的角色背地里的行为，记录在 npc_background_actions。
5.【表里不一判定】（极其重要）：我会提供【近期微信动态】。你需要对比玩家在微信里的发言和她当下的现实行动。如果玩家“当面一套背后一套”，请让知道内情的 NPC 立刻在对话中阴阳怪气或直接拆穿她！"""

AUTHOR_NOTE = """[系统最高指令]
你必须严格输出合法的 JSON 格式。
铁律1：字符串内部【绝对不准】使用双引号（"）！如需引述请使用单引号（'）。
铁律2：next_options 必须严格提供 5 个简短的【态度/意图】选项（禁止包含长串台词）。

输出模板：
{
    "narrator_transition": "旁白文本",
    "dialogue_sequence": [
        {"speaker": "陆陈安然", "content": "具体台词", "mood": "平静"},
        {"speaker": "室友", "content": "反应", "mood": "情绪"}
    ],
    "npc_background_actions": [{"character": "陈雨婷", "action": "冷笑", "affinity_change": -1}],
    "wechat_notifications": [
        {"chat_name": "唐梦琪 (私聊)", "sender": "唐梦琪", "message": "安然，李一诺是不是有病啊？气死我了！"},
        {"chat_name": "孤立李一诺小群 (3)", "sender": "陈雨婷", "message": "今晚去吃夜宵吗？不带某人。"}
    ],
    "next_options": ["【强硬反对】", "【和稀泥】", "【转移话题】", "【沉默不语】", "【阴阳怪气】"],
    "stat_changes": {"san_delta": -5, "money_delta": 0, "is_argument": true, "affinity_changes": {"陈雨婷": -2}},
    "is_end": false
}"""

WECHAT_PROMPT = """你正在模拟大学女生寝室的微信聊天。
[核心指令]
1. 玩家刚在指定的聊天窗口（群聊或私聊）发了消息，请扮演对方进行回复。
2. 密切结合【当前现实进展】和【历史聊天记录】。
3. 语言必须是【极度真实的大学生微信风格】：爱用缩写、乱用标点、表情包代词。
4. 必须输出合法的 JSON 格式！严禁自创键名！

输出模板：
{
    "chat_history": [
        {"sender": "对方名字", "message": "回复内容"}
    ],
    "affinity_changes": {"唐梦琪": 2}
}"""

# --- 辅助函数：渲染角色面板 ---
def generate_char_info_md(selected_chars, affinity):
    md = "### 室友关系监控\n---\n"
    for name, p in CANDIDATE_POOL.items():
        role_status = "[在场]" if name in selected_chars else "[缺席]"
        aff = affinity.get(name, 50)
        if aff >= 80: rel = "🟢 [挚友]"
        elif aff >= 50: rel = "🟡 [普通]"
        elif aff >= 30: rel = "🟠 [紧张]"
        else: rel = "🔴 [死敌]"
        md += f"**{name}** {role_status} | {rel} : {aff}/100\n"
    return md

# --- 处理手机微信回复逻辑 ---
def process_wechat_action(player_msg, current_chat_name, wechat_data_dict, current_evt_id, turn, api_key_val, base_url_val, model_val, tmp, top_p, affinity):
    # 核心拦截：如果没有消息记录，不允许玩家主动发起（强事件驱动）
    if not wechat_data_dict.get(current_chat_name):
        return gr.update(value=""), wechat_data_dict[current_chat_name], wechat_data_dict, affinity, gr.update(value="⚠️ 对方未发消息，你无法主动发起聊天！", visible=True)
        
    if not player_msg.strip():
        return gr.update(value=""), wechat_data_dict[current_chat_name], wechat_data_dict, affinity, gr.update()

    llm_service.update_config(api_key=api_key_val, base_url=base_url_val, model=model_val)
    
    # 玩家消息上屏
    wechat_data_dict[current_chat_name].append((player_msg, "对方正在输入中..."))
    yield gr.update(value=""), wechat_data_dict[current_chat_name], wechat_data_dict, affinity, gr.update()

    encyclopedia = "【角色图鉴】\n"
    for name, p in CANDIDATE_POOL.items():
        encyclopedia += f"- {name}: {p.Core_Archetype}。冲突风格: {p.Conflict_Style}。\n"

    event_context = "【当前现实局势】: 日常阶段。"
    if current_evt_id in EVENT_DATABASE:
        evt = EVENT_DATABASE[current_evt_id]
        event_context = f"【当前现实局势】: 现实中正在发生事件“{evt.name}”。"

    system_prm = f"{WECHAT_PROMPT}\n\n当前聊天窗口：{current_chat_name}\n\n{encyclopedia}\n{event_context}"
    user_prm = f"玩家在微信发送了：{player_msg}"

    try:
        res_text = llm_service.generate_response(system_prompt=system_prm, user_input=user_prm, temperature=tmp, top_p=top_p)
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        raw_json = match.group(0) if match else res_text
        raw_json = raw_json.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace("：", ":")
        parsed = json.loads(repair_json(raw_json))
        
        aff_changes = parsed.get("affinity_changes", {})
        for char_name, change_val in aff_changes.items():
            if char_name in affinity:
                affinity[char_name] = max(0, min(100, affinity[char_name] + change_val))
                
        chat_lines = []
        for t in parsed.get("chat_history", []):
            snd = t.get("sender", "神秘人")
            msg = t.get("message", "")
            if not msg:
                fallback_vals = [str(v) for k, v in t.items() if k != 'sender']
                if fallback_vals: msg = max(fallback_vals, key=len)
            chat_lines.append(f"**{snd}**: {msg}")
            
        reply_text = "\n\n".join(chat_lines)
        if not reply_text: reply_text = "（对方已读不回）"

        # 将微信记录写入长期记忆，以后可以被 RAG 翻旧账
        clean_ai_reply = reply_text.replace("\n\n", " ") # 简单清洗一下格式
        mm.save_interaction(user_input=f"[在微信 {current_chat_name} 中说] {player_msg}", ai_response=clean_ai_reply, user_name="陆陈安然")
            
        wechat_data_dict[current_chat_name][-1] = (player_msg, reply_text)
        yield gr.update(), wechat_data_dict[current_chat_name], wechat_data_dict, affinity, gr.update()

    except Exception as e:
        wechat_data_dict[current_chat_name][-1] = (player_msg, f"网络连接中断: {e}")
        yield gr.update(), wechat_data_dict[current_chat_name], wechat_data_dict, affinity, gr.update()

# --- 切换手机频道 ---
def switch_chat_channel(selected_channel, wechat_data_dict):
    if selected_channel not in wechat_data_dict:
        wechat_data_dict[selected_channel] = []
    return wechat_data_dict[selected_channel]

# --- 处理主线游戏逻辑 ---
def process_action(selected_chars, current_evt_id, player_choice, is_transition, prm, 
                   api_key_val, base_url_val, model_val, tmp, top_p, max_tokens, pres_pen, freq_pen, 
                   hist, turn, san, money, gpa, arg_count, chapter, affinity, wechat_data_dict):   
    
    llm_service.update_config(api_key=api_key_val, base_url=base_url_val, model=model_val)
    
    if not is_transition and current_evt_id != "" and not player_choice:
        yield gr.update(), gr.update(), hist + [("（未作选择）", "⚠️ 请选择一项行为！")], turn, gr.update(), gr.update(), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, gr.update(), gr.update(), affinity, gr.update(), wechat_data_dict, gr.update()
        return

    action_text = player_choice if (not is_transition and current_evt_id != "") else "（时间推移...）"
    yield gr.update(), gr.update(visible=False), hist + [(action_text, "*局势推演中...*")], turn, gr.update(), gr.update(value="⏳ 推演中...", interactive=False), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, gr.update(), gr.update(), affinity, gr.update(), wechat_data_dict, gr.update()

    mock_player_stats = {"hygiene": 50, "affinity_xueba": 5} 
    settlement_msg = ""
    
    if is_transition or current_evt_id == "":
        if turn == 0: mm.clear_game_history()
        next_evt = director.get_next_event(mock_player_stats, selected_chars)
        if not next_evt:
            yield gr.update(), gr.update(visible=False), hist + [(action_text, "🏁 游戏通关！")], turn, "游戏结束", gr.update(value="游戏结束", interactive=False), False, current_evt_id, san, money, gpa, arg_count, chapter, f"**SAN**: {san}", generate_char_info_md(selected_chars, affinity), affinity, gr.update(), wechat_data_dict, gr.update()
            return
        if next_evt.chapter > chapter:
            money -= 800  
            gpa = max(0.0, min(4.0, 3.0 - (arg_count * 0.05)))
            settlement_msg = f"**[大{chapter}学年结算]** 扣除生活费800。GPA：{gpa:.2f}\n\n"
            chapter = next_evt.chapter; arg_count = 0 
        turn = 1
        event_context = f"【过渡指令】进入第 {chapter} 章。\n【新事件】:{next_evt.name}\n【场景描述】:{next_evt.description}"
    else:
        next_evt = EVENT_DATABASE[current_evt_id]
        turn += 1
        pacing = "【节奏：结局】明确收尾，is_end 置为 true。" if turn >= 3 else "【节奏：激化】冲突升级。"
        event_context = f"【事件】: {next_evt.name}\n【回合】: {turn}/3\n{pacing}\n【玩家选择意图】: {action_text}\n⚠️先写玩家的行动/台词，再写室友反应。"

    encyclopedia = "【在场图鉴】\n"
    for name, p in CANDIDATE_POOL.items():
        if name in selected_chars or (next_evt and name in next_evt.description):
            encyclopedia += f"- {name}: {p.Core_Archetype}。倾向:[{p.Conflict_Style}]。\n"

    try:
        relevant_docs = mm.vector_store.search(f"{next_evt.name} {action_text}", n_results=3)
        lore_str = "\n".join([d['content'] for d in relevant_docs if "语录" in d.get('content', '')])
    except: lore_str = ""

    # 提取微信动态
    wechat_summary = "【近期微信动态】\n"
    has_recent_wechat = False
    for chat_name, messages in wechat_data_dict.items():
        if messages: # 提取每个频道最后一条消息
            last_msg = messages[-1]
            wechat_summary += f"- 在 {chat_name} 中，玩家刚刚说了：“{last_msg[0]}”。\n"
            has_recent_wechat = True
    if not has_recent_wechat:
        wechat_summary += "无\n"

    full_system_prompt = f"{prm}\n\n{encyclopedia}\n【供模仿语录】:\n{lore_str}"
    final_user_input = f"{event_context}\n\n[状态] SAN:{san}, 资金:{money}。\n\n{AUTHOR_NOTE}"

    try:
        if getattr(next_evt, 'is_cg', False):
            parsed = {"narrator_transition": f"[演出] {next_evt.name}", "dialogue_sequence": getattr(next_evt, 'fixed_dialogue', []), "next_options": ["继续"], "stat_changes": {}, "is_end": True if not is_transition else False}
            res_text = json.dumps(parsed, ensure_ascii=False)
        else:
            res_text = llm_service.generate_response(system_prompt=full_system_prompt, user_input=final_user_input, temperature=tmp, top_p=top_p, max_tokens=max_tokens, presence_penalty=pres_pen, frequency_penalty=freq_pen)
            match = re.search(r'\{.*\}', res_text, re.DOTALL)
            raw_json = match.group(0) if match else res_text
            raw_json = raw_json.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace("：", ":")
            parsed = json.loads(repair_json(raw_json))

        # 数值结算
        stats_data = parsed.get("stat_changes", {})
        san = max(0, min(100, san + stats_data.get("san_delta", 0)))
        money += stats_data.get("money_delta", 0)
        if stats_data.get("is_argument", False): arg_count += 1
        for char_name, change_val in stats_data.get("affinity_changes", {}).items():
            if char_name in affinity: affinity[char_name] = max(0, min(100, affinity[char_name] + change_val))
            
        display_text = settlement_msg
        if parsed.get("narrator_transition"): display_text += f"{parsed['narrator_transition']}\n\n"
        
        dialogue_lines = []
        for t in parsed.get("dialogue_sequence", []):
            spk, cont = t.get("speaker", "神秘人"), t.get("content", "")
            if not cont: cont = max([str(v) for k, v in t.items() if k not in ['speaker', 'mood']], key=len, default="")
            dialogue_lines.append(f"**[{spk}]** {cont}")
        display_text += "\n\n".join(dialogue_lines)
        
        # 暗场行动
        for act in parsed.get("npc_background_actions", []):
            c_name, c_act, c_aff = act.get("character", "神秘人"), act.get("action", ""), act.get("affinity_change", 0)
            if c_name in affinity and c_aff != 0:
                affinity[c_name] = max(0, min(100, affinity[c_name] + c_aff))
                aff_sign = f" (好感 {c_aff})" if c_aff < 0 else f" (好感 +{c_aff})"
            else: aff_sign = ""
            display_text += f"\n\n> **[暗场动态] {c_name}**: {c_act}{aff_sign}"

        hist.append((action_text, display_text))
        
        # 处理微信突发事件
        new_chats_ui_update = gr.update()
        wechat_notifs = parsed.get("wechat_notifications", [])
        if wechat_notifs:
            notif_msg = "\n\n **【手机震动】您收到新的微信消息！**\n"
            for w in wechat_notifs:
                c_name = w.get("chat_name", "未知群聊")
                sender = w.get("sender", "神秘人")
                msg = w.get("message", "")
                
                # 初始化频道
                if c_name not in wechat_data_dict: wechat_data_dict[c_name] = []
                # 压入未读消息（代表 AI 主动发起的）
                wechat_data_dict[c_name].append((None, f"**{sender}**: {msg}"))
                notif_msg += f"- *来自 {c_name}*: {msg[:10]}...\n"
            
            hist[-1] = (hist[-1][0], hist[-1][1] + notif_msg) # 把提示写在主线聊天框
            # 更新手机频道的下拉菜单
            new_chats_ui_update = gr.update(choices=list(wechat_data_dict.keys()), value=list(wechat_data_dict.keys())[-1])

        is_end = True if turn >= 3 else parsed.get("is_end", False)
        if not getattr(next_evt, 'is_cg', False) and action_text and "（时间推移..." not in action_text:
            mm.save_interaction(user_input=action_text, ai_response=" ".join(dialogue_lines), user_name="陆陈安然")
        
        stats_md_text = f"**SAN值**: {san}/100 &nbsp;|&nbsp; **生活费**: ¥{money} &nbsp;|&nbsp; **当前GPA**: {gpa:.2f} &nbsp;|&nbsp; **本章争吵**: {arg_count}次"
        btn_text = "继续下一步" if is_end else "确认行动"
        options_ui = gr.update(choices=[], visible=False, value=None) if is_end else gr.update(choices=parsed.get("next_options", []), visible=True, value=None)
        
        yield res_text, options_ui, hist, turn, f"第 {chapter} 章 - {next_evt.name} (回合 {turn})", gr.update(value=btn_text, interactive=True), is_end, next_evt.id, san, money, gpa, arg_count, chapter, stats_md_text, generate_char_info_md(selected_chars, affinity), affinity, new_chats_ui_update, wechat_data_dict, gr.update(visible=False)
        
    except Exception as e:
        yield f"系统错误: {e}", gr.update(visible=True), hist + [(action_text, f"❌ 系统错误: {e}")], turn, "错误", gr.update(value="重试", interactive=True), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, f"**SAN**: {san}", generate_char_info_md(selected_chars, affinity), affinity, gr.update(), wechat_data_dict, gr.update()

def fetch_all_memories():
    try:
        data = mm.vector_store.collection.get()
        if not data or not data['ids']: return pd.DataFrame(columns=["ID", "内容", "类型", "重要度", "时间戳"])
        rows = [{"ID": data['ids'][i], "内容": data['documents'][i], "类型": (data['metadatas'][i] if data['metadatas'] else {}).get("type", "unknown"), "重要度": (data['metadatas'][i] if data['metadatas'] else {}).get("importance", 5), "时间戳": (data['metadatas'][i] if data['metadatas'] else {}).get("timestamp", "")} for i in range(len(data['ids']))]
        return pd.DataFrame(rows)
    except Exception as e: return pd.DataFrame(columns=["ID", f"读取出错: {e}", "类型", "重要度", "时间戳"])

# --- 构建 Gradio 网页 UI ---
custom_css = """
.status-card { background-color: #fafafa; padding: 15px; border-radius: 8px; border: 1px solid #eaeaea; margin-bottom: 10px; }
.phone-panel { border-left: 2px dashed #ccc; padding-left: 15px; background: #fdfdfd; }
"""

with gr.Blocks(title="大学档案 | 沉浸式模拟系统", theme=gr.themes.Monochrome(), css=custom_css) as demo:
    
    state_affinity = gr.State({name: 50 for name in CANDIDATE_POOL.keys()})
    state_wechat_data = gr.State({"【404 仙女下凡群】": []}) # 存储所有频道的聊天记录字典
    
    with gr.Tabs():
        # ==========================================
        # Tab 1: 游戏主控台 (融合主线与手机侧边栏)
        # ==========================================
        with gr.TabItem("🎮 核心游戏视窗"):
            state_current_event_id = gr.State("")
            state_turn, state_is_transition = gr.State(0), gr.State(True) 
            state_san, state_money, state_gpa, state_args, state_chapter = gr.State(80), gr.State(1500), gr.State(3.0), gr.State(0), gr.State(1)
            
            with gr.Row():
                # 🟢 左侧：现实主线区域
                with gr.Column(scale=6):
                    status_text = gr.Markdown("### 当前进度：系统待机")
                    chatbot = gr.Chatbot(label="现实世界 - 事件推演", height=550)
                    dynamic_options = gr.Radio(choices=[], label="玩家意图轮盘", visible=False)
                    
                    with gr.Row():
                        action_btn = gr.Button("启动模拟流", variant="primary", scale=3)
                        toggle_phone_btn = gr.Button("📱 掏出手机", variant="secondary", scale=1)
                    
                    with gr.Accordion("角色与生成参数控制台", open=False):
                        stats_panel = gr.Markdown("**SAN值**: 80/100 &nbsp;|&nbsp; **生活费**: ¥1500 &nbsp;|&nbsp; **GPA**: 3.00 &nbsp;|&nbsp; **本章争吵**: 0次")
                        char_checkboxes = gr.CheckboxGroup(choices=list(CANDIDATE_POOL.keys()), label="在场角色", value=list(CANDIDATE_POOL.keys())[:3])
                        char_info_panel = gr.Markdown(generate_char_info_md(list(CANDIDATE_POOL.keys())[:3], {name: 50 for name in CANDIDATE_POOL.keys()}))
                        output_json = gr.Code(language="json", label="模型交互 JSON", visible=False)
                        api_key_input = gr.Textbox(label="API Key", type="password")
                        base_url_input = gr.Textbox(label="Base URL", value="https://api.deepseek.com/v1")
                        model_input = gr.Textbox(label="Model Name", value="deepseek-chat")
                        temp_slider = gr.Slider(minimum=0.1, maximum=2.0, value=0.7, label="Temperature")
                        top_p_slider = gr.Slider(minimum=0.1, maximum=1.0, value=1.0, label="Top P")
                        freq_pen_slider = gr.Slider(minimum=-2.0, maximum=2.0, value=0.5, label="Freq Penalty")
                        pres_pen_slider = gr.Slider(minimum=-2.0, maximum=2.0, value=0.3, label="Pres Penalty")
                        max_tokens_slider = gr.Slider(minimum=100, maximum=2000, value=800, label="Max Tokens")
                        prompt_input = gr.Textbox(lines=3, value=DEFAULT_PROMPT, label="System Prompt", visible=False)

                # 🔵 右侧：手机侧边栏 (默认隐藏)
                with gr.Column(scale=4, visible=False, elem_classes="phone-panel") as phone_panel:
                    gr.Markdown("### 📱 微信通讯录")
                    wechat_alert = gr.Markdown("⚠️ 对方未发消息，无法主动发起聊天！", visible=False)
                    chat_selector = gr.Dropdown(choices=["【404 仙女下凡群】"], value="【404 仙女下凡群】", label="当前聊天窗口", interactive=True)
                    wechat_chatbot = gr.Chatbot(label="微信聊天记录", height=420, avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/1053/1053244.png"))
                    wechat_input = gr.Textbox(label="在此输入内容...", placeholder="回复消息...")
                    wechat_send_btn = gr.Button("发送 (Send)", variant="primary")

            # 📱 侧边栏开关逻辑
            def toggle_phone(is_open):
                new_state = not is_open
                btn_txt = "⬇️ 收起手机" if new_state else "📱 掏出手机"
                return gr.update(visible=new_state), btn_txt, new_state
            
            phone_state = gr.State(False)
            toggle_phone_btn.click(fn=toggle_phone, inputs=phone_state, outputs=[phone_panel, toggle_phone_btn, phone_state])

            # 📱 切换聊天频道逻辑
            chat_selector.change(
                fn=switch_chat_channel,
                inputs=[chat_selector, state_wechat_data],
                outputs=[wechat_chatbot]
            )

            # 主线逻辑绑定 (新增对手机频道的更新)
            action_btn.click(
                fn=process_action,
                inputs=[char_checkboxes, state_current_event_id, dynamic_options, state_is_transition, prompt_input, api_key_input, base_url_input, model_input, temp_slider, top_p_slider, max_tokens_slider, pres_pen_slider, freq_pen_slider, chatbot, state_turn, state_san, state_money, state_gpa, state_args, state_chapter, state_affinity, state_wechat_data],
                outputs=[output_json, dynamic_options, chatbot, state_turn, status_text, action_btn, state_is_transition, state_current_event_id, state_san, state_money, state_gpa, state_args, state_chapter, stats_panel, char_info_panel, state_affinity, chat_selector, state_wechat_data, wechat_alert]
            )

            # 微信发送逻辑绑定
            wechat_send_btn.click(
                fn=process_wechat_action,
                inputs=[wechat_input, chat_selector, state_wechat_data, state_current_event_id, state_turn, api_key_input, base_url_input, model_input, temp_slider, top_p_slider, state_affinity],
                outputs=[wechat_input, wechat_chatbot, state_wechat_data, state_affinity, wechat_alert]
            )

        # ==========================================
        # 后台数据管理 Tabs
        # ==========================================
        with gr.TabItem("后台数据库 (RAG & 存档)"):
            with gr.Row():
                refresh_btn = gr.Button("刷新数据库表单", variant="secondary")
                clear_mem_btn = gr.Button("清除历史互动记录 (危险)", variant="stop")
            def clear_and_refresh(): mm.clear_game_history(); return fetch_all_memories()
            memory_dataframe = gr.Dataframe(headers=["ID", "内容", "类型", "重要度", "时间戳"], datatype=["str", "str", "str", "number", "str"], interactive=False, wrap=True)
            clear_mem_btn.click(fn=clear_and_refresh, outputs=memory_dataframe)
            refresh_btn.click(fn=fetch_all_memories, outputs=memory_dataframe)
            demo.load(fn=fetch_all_memories, outputs=memory_dataframe)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
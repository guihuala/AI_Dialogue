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

# 1. 主线模式：顶层系统指令
DEFAULT_PROMPT = """你是一个多角色大学生存游戏的 AI 跑团 DM。
[核心职责]
1. 维持角色人设，严格遵守【在场角色图鉴】。禁止扮演未提及的角色。
2. 结合【当前事件】与【玩家行动】生成角色自然对话。
3. 动态评估室友对玩家的好感度变动（affinity_changes）。
4. 🌟【暗场行动】：评估其他没说话的角色在背地里干什么（如发朋友圈、翻白眼），记录在 npc_background_actions 中。"""

# 2. 主线模式：底层格式铁律
AUTHOR_NOTE = """[⚠️ 系统最高指令 / 格式铁律]
你必须严格输出合法的 JSON 格式。
⚠️ 铁律1：在任何字符串内部，【绝对不准】使用双引号（"）！如需引述请使用单引号（'）。
⚠️ 铁律2：next_options 数组内请用【动作】+描述的形式输出，不要带标点。

输出模板：
{
    "narrator_transition": "旁白过渡文本",
    "dialogue_sequence": [{"speaker": "角色", "content": "内容", "mood": "情绪"}],
    "npc_background_actions": [{"character": "陈雨婷", "action": "在床帘后冷笑了一声", "affinity_change": -1}],
    "next_options": ["【拒绝】我没钱", "【询问】具体要多少"],
    "stat_changes": {"san_delta": -5, "money_delta": 0, "is_argument": true, "affinity_changes": {"陈雨婷": -2}},
    "is_end": false
}"""

# 3. 🌟 新增：微信群聊专用极简 Prompt (动态上下文版)
WECHAT_PROMPT = """你正在模拟大学女生寝室的微信群聊。

[核心指令]
1. 玩家刚在群里发了一条消息，请扮演【群聊成员图鉴】中的室友进行群聊回复。禁止扮演不在图鉴中的角色！
2. 请密切结合【当前现实进展】生成回复。由于你们正在经历该事件，群聊内容应与该事件密切相关（如吐槽、讨论对策、情绪发泄等）。
3. 语言必须是极度真实的【当代大学生微信聊天风格】：爱用缩写(xswl, yyds)、乱用标点、经常发表情包（用文字替代如 [猫猫叹气]）。
4. 如果玩家的话得罪了人，请在 affinity_changes 扣除好感度。
5. ⚠️ 铁律：字符串内部严禁使用双引号！必须输出合法的 JSON 格式！

输出模板：
{
    "chat_history": [
        {"sender": "唐梦琪", "message": "卧槽！惊天大瓜🍉"},
        {"sender": "陈雨婷", "message": "[翻白眼] 关我什么事？"}
    ],
    "affinity_changes": {"唐梦琪": 2, "陈雨婷": 0}
}"""

# --- 辅助函数：渲染角色面板 ---
def generate_char_info_md(selected_chars, affinity):
    md = "### 室友档案与关系监控\n---\n"
    for name, p in CANDIDATE_POOL.items():
        role_status = "[在场]" if name in selected_chars else "[缺席]"
        aff = affinity.get(name, 50)
        if aff >= 80: rel = "🟢 [挚友]"
        elif aff >= 50: rel = "🟡 [普通]"
        elif aff >= 30: rel = "🟠 [紧张]"
        else: rel = "🔴 [死敌]"
        md += f"**{name}** {role_status} | {rel} : {aff}/100\n"
        md += f"- **冲突倾向**: 压力下[{p.Stress_Reaction}], 冲突时[{p.Conflict_Style}]\n"
        md += f"- **隐藏秘密**: {p.Background_Secret or '无'}\n\n"
    return md

# 处理手机微信逻辑
def process_wechat_action(player_msg, selected_chars, current_evt_id, turn, api_key_val, base_url_val, model_val, tmp, top_p, wechat_history, affinity):
    if not player_msg.strip():
        yield gr.update(value=""), wechat_history, affinity, gr.update()
        return

    llm_service.update_config(api_key=api_key_val, base_url=base_url_val, model=model_val)
    
    # 将玩家的话上屏
    wechat_history.append((player_msg, "⏳ 对方正在输入中..."))
    yield gr.update(value=""), wechat_history, affinity, gr.update()

    # 1. 组装微信专用的图鉴 (⚠️ 核心过滤：只有勾选的角色才会在群里说话)
    encyclopedia = "【群聊成员图鉴】\n"
    for name in selected_chars:
        if name in CANDIDATE_POOL:
            p = CANDIDATE_POOL[name]
            encyclopedia += f"- {name}: {p.Core_Archetype}。冲突风格: {p.Conflict_Style}。\n"
    if not selected_chars:
        encyclopedia += "群里没有其他室友在线。\n"

    # 2. 注入当前的主线现实事件进度 (⚠️ 核心联动)
    event_context = "【当前现实进展】: 游戏刚开始，处于日常闲聊阶段。"
    if current_evt_id in EVENT_DATABASE:
        evt = EVENT_DATABASE[current_evt_id]
        event_context = f"【当前现实进展】: 现实寝室里正在发生事件“{evt.name}”（{evt.description}）。这是事件的第 {turn} 回合。"

    system_prm = f"{WECHAT_PROMPT}\n\n{encyclopedia}\n{event_context}"
    user_prm = f"玩家（陆陈安然）在群里发送了：{player_msg}"

    try:
        res_text = llm_service.generate_response(
            system_prompt=system_prm, user_input=user_prm, 
            temperature=tmp, top_p=top_p
        )
        
        # 🛡️ 终极 JSON 修复神器
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        raw_json = match.group(0) if match else res_text
        parsed = json.loads(repair_json(raw_json))
        
        aff_changes = parsed.get("affinity_changes", {})
        for char_name, change_val in aff_changes.items():
            if char_name in affinity:
                affinity[char_name] = max(0, min(100, affinity[char_name] + change_val))
                
        chat_lines = [f"**{t.get('sender', '神秘人')}**: {t.get('message', '')}" for t in parsed.get("chat_history", [])]
        reply_text = "\n\n".join(chat_lines)
        if not reply_text:
            reply_text = "（群里无人回应）"
            
        wechat_history[-1] = (player_msg, reply_text)
        yield gr.update(), wechat_history, affinity, generate_char_info_md(list(CANDIDATE_POOL.keys())[:3], affinity)

    except Exception as e:
        wechat_history[-1] = (player_msg, f"❌ 网络连接中断或解析错误: {e}")
        yield gr.update(), wechat_history, affinity, gr.update()

# --- 处理主线游戏逻辑 ---
def process_action(selected_chars, current_evt_id, player_choice, is_transition, prm, 
                   api_key_val, base_url_val, model_val,
                   tmp, top_p, max_tokens, pres_pen, freq_pen, 
                   hist, turn, san, money, gpa, arg_count, chapter, affinity):   
    
    llm_service.update_config(api_key=api_key_val, base_url=base_url_val, model=model_val)
    
    if not is_transition and current_evt_id != "" and not player_choice:
        yield gr.update(), gr.update(), hist + [("（未作选择）", "⚠️ 导演提示：请选择一项行为！")], turn, gr.update(), gr.update(), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, gr.update(), gr.update(), affinity
        return

    action_text = player_choice if (not is_transition and current_evt_id != "") else "（时间推移...）"
    yield gr.update(), gr.update(visible=False), hist + [(action_text, "⏳ *AI 导演正在推演局势...*")], turn, gr.update(), gr.update(value="⏳ 推演中...", interactive=False), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, gr.update(), gr.update(), affinity

    mock_player_stats = {"hygiene": 50, "affinity_xueba": 5} 
    settlement_msg = ""
    
    if is_transition or current_evt_id == "":
        if turn == 0: mm.clear_game_history()
        next_evt = director.get_next_event(mock_player_stats, selected_chars)
        
        if not next_evt:
            yield gr.update(), gr.update(visible=False), hist + [(action_text, "🏁 游戏通关！")], turn, "游戏结束", gr.update(value="游戏结束", interactive=False), False, current_evt_id, san, money, gpa, arg_count, chapter, f"**SAN**: {san}", generate_char_info_md(selected_chars, affinity), affinity
            return
        
        if next_evt.chapter > chapter:
            money -= 800  
            gpa = max(0.0, min(4.0, 3.0 - (arg_count * 0.05)))
            settlement_msg = f"**[大{chapter}学年结算]**\n扣除生活费800。GPA结算：{gpa:.2f}\n\n"
            chapter = next_evt.chapter; arg_count = 0 
        turn = 1
        event_context = f"【过渡指令】进入第 {chapter} 章。\n【新事件】:{next_evt.name}\n【场景描述】:{next_evt.description}"
    else:
        next_evt = EVENT_DATABASE[current_evt_id]
        turn += 1
        pacing = "【当前节奏：结局】明确收尾，is_end 置为 true。" if turn >= 3 else "【当前节奏：激化】冲突升级。"
        event_context = f"【事件】: {next_evt.name}\n【回合】: {turn}/3\n{pacing}\n【玩家】: {action_text}"

    encyclopedia = "【在场角色图鉴】\n"
    for name, p in CANDIDATE_POOL.items():
        is_selected = name in selected_chars
        is_cameo = (not is_selected) and next_evt and (name in next_evt.description or name in next_evt.name)
        if is_selected or is_cameo:
            encyclopedia += f"- {name}: {p.Core_Archetype}。冲突倾向:[{p.Conflict_Style}]。\n"

    try:
        relevant_docs = mm.vector_store.search(f"{next_evt.name} {action_text}", n_results=3)
        lores = [d['content'] for d in relevant_docs if "专属语录" in d.get('content', '')]
    except: lores = []
    lore_str = "\n".join(lores) if lores else "无"

    full_system_prompt = f"{prm}\n\n{encyclopedia}\n【供模仿语录】:\n{lore_str}"
    final_user_input = f"{event_context}\n\n[玩家状态] SAN:{san}, 金钱:{money}。\n\n{AUTHOR_NOTE}"

    try:
        if getattr(next_evt, 'is_cg', False):
            parsed = {"narrator_transition": f"[演出] {next_evt.name}", "dialogue_sequence": getattr(next_evt, 'fixed_dialogue', []), "next_options": ["继续"], "stat_changes": {}, "is_end": True} if not is_transition else {"narrator_transition": f"[演出] {next_evt.name}", "dialogue_sequence": getattr(next_evt, 'fixed_dialogue', []), "next_options": ["继续"], "stat_changes": {}, "is_end": False}
            res_text = json.dumps(parsed, ensure_ascii=False)
        else:
            res_text = llm_service.generate_response(system_prompt=full_system_prompt, user_input=final_user_input, temperature=tmp, top_p=top_p, max_tokens=max_tokens, presence_penalty=pres_pen, frequency_penalty=freq_pen)
            
            # 🛡️ 终极 JSON 修复神器
            match = re.search(r'\{.*\}', res_text, re.DOTALL)
            raw_json = match.group(0) if match else res_text
            parsed = json.loads(repair_json(raw_json))

        stats_data = parsed.get("stat_changes", {})
        san = max(0, min(100, san + stats_data.get("san_delta", 0)))
        money += stats_data.get("money_delta", 0)
        if stats_data.get("is_argument", False): arg_count += 1
            
        aff_changes = stats_data.get("affinity_changes", {})
        for char_name, change_val in aff_changes.items():
            if char_name in affinity: affinity[char_name] = max(0, min(100, affinity[char_name] + change_val))
            
        updated_char_md = generate_char_info_md(selected_chars, affinity)
        
        display_text = settlement_msg
        if parsed.get("narrator_transition"): display_text += f"{parsed['narrator_transition']}\n\n"
        
        dialogue_lines = [f"**[{t.get('speaker', '神秘人')}]** {t.get('content', '')}" for t in parsed.get("dialogue_sequence", [])]
        display_text += "\n\n".join(dialogue_lines)
        
        # 🌟 渲染暗场行动
        bg_actions = parsed.get("npc_background_actions", [])
        if bg_actions:
            bg_text_lines = []
            for act in bg_actions:
                c_name, c_act, c_aff = act.get("character", "神秘人"), act.get("action", ""), act.get("affinity_change", 0)
                if c_name in affinity and c_aff != 0:
                    affinity[c_name] = max(0, min(100, affinity[c_name] + c_aff))
                    aff_sign = f" (好感 {c_aff})" if c_aff < 0 else f" (好感 +{c_aff})"
                else: aff_sign = ""
                bg_text_lines.append(f"> 👁️ **[暗场动态] {c_name}**: {c_act}{aff_sign}")
            display_text += "\n\n" + "\n".join(bg_text_lines)

        hist.append((action_text, display_text))
        
        # 🌟 强制断环系统：防止 AI 在第3回合赖皮死循环！
        is_end = parsed.get("is_end", False)
        if turn >= 3:
            is_end = True
        
        if not getattr(next_evt, 'is_cg', False) and action_text and "（时间推移..." not in action_text:
            mm.save_interaction(user_input=action_text, ai_response=" ".join(dialogue_lines), user_name="陆陈安然")
        
        stats_md_text = f"**SAN值**: {san}/100 &nbsp;|&nbsp; **生活费**: ¥{money} &nbsp;|&nbsp; **当前GPA**: {gpa:.2f} &nbsp;|&nbsp; **本章争吵**: {arg_count}次"
        btn_text = "继续下一步" if is_end else "确认行动"
        options_ui = gr.update(choices=[], visible=False, value=None) if is_end else gr.update(choices=parsed.get("next_options", []), visible=True, value=None)
        
        yield res_text, options_ui, hist, turn, f"第 {chapter} 章 - {next_evt.name} (回合 {turn})", gr.update(value=btn_text, interactive=True), is_end, next_evt.id, san, money, gpa, arg_count, chapter, stats_md_text, updated_char_md, affinity
        
    except Exception as e:
        yield f"系统错误: {e}", gr.update(visible=True), hist + [(action_text, f"❌ 系统错误: {e}")], turn, "错误", gr.update(value="重试", interactive=True), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, f"**SAN**: {san}", generate_char_info_md(selected_chars, affinity), affinity

def fetch_all_memories():
    try:
        data = mm.vector_store.collection.get()
        if not data or not data['ids']: return pd.DataFrame(columns=["ID", "内容", "类型", "重要度", "时间戳"])
        rows = [{"ID": data['ids'][i], "内容": data['documents'][i], "类型": (data['metadatas'][i] if data['metadatas'] else {}).get("type", "unknown"), "重要度": (data['metadatas'][i] if data['metadatas'] else {}).get("importance", 5), "时间戳": (data['metadatas'][i] if data['metadatas'] else {}).get("timestamp", "")} for i in range(len(data['ids']))]
        return pd.DataFrame(rows)
    except Exception as e: return pd.DataFrame(columns=["ID", f"读取出错: {e}", "类型", "重要度", "时间戳"])

custom_css = ".status-card { background-color: #fafafa; padding: 15px; border-radius: 8px; border: 1px solid #eaeaea; margin-bottom: 10px; }"

with gr.Blocks(title="大学档案 | 沉浸式模拟系统", theme=gr.themes.Monochrome(), css=custom_css) as demo:
    
    # 状态全局共享
    state_affinity = gr.State({name: 50 for name in CANDIDATE_POOL.keys()})
    
    with gr.Tabs():
        # ==========================================
        # Tab 1: 主线剧本模式
        # ==========================================
        with gr.TabItem("🎮 现实寝室推演"):
            state_current_event_id = gr.State("")
            state_turn = gr.State(0)
            state_is_transition = gr.State(True) 
            state_san, state_money, state_gpa, state_args, state_chapter = gr.State(80), gr.State(1500), gr.State(3.0), gr.State(0), gr.State(1)
            
            with gr.Row():
                with gr.Column(scale=7):
                    status_text = gr.Markdown("### 当前进度：系统待机")
                    chatbot = gr.Chatbot(label="事件推演记录", height=500)
                    dynamic_options = gr.Radio(choices=[], label="玩家行动选项", visible=False)
                    action_btn = gr.Button("启动模拟流", variant="primary", size="lg")
                    
                with gr.Column(scale=3):
                    gr.Markdown("### 控制侧边栏")
                    with gr.Group():
                        stats_panel = gr.Markdown("**SAN值**: 80/100 &nbsp;|&nbsp; **生活费**: ¥1500 &nbsp;|&nbsp; **当前GPA**: 3.00 &nbsp;|&nbsp; **本章争吵**: 0次")
                    with gr.Group():
                        char_checkboxes = gr.CheckboxGroup(choices=list(CANDIDATE_POOL.keys()), label="在场角色 (触发可自动拉入客串)", value=list(CANDIDATE_POOL.keys())[:3])
                    with gr.Accordion("角色档案监控", open=True):
                        char_info_panel = gr.Markdown(generate_char_info_md(list(CANDIDATE_POOL.keys())[:3], {name: 50 for name in CANDIDATE_POOL.keys()}))
                    with gr.Accordion("生成参数与底层通讯", open=False):
                        output_json = gr.Code(language="json", label="模型交互 JSON")
                        api_key_input = gr.Textbox(label="API Key", type="password", placeholder="填入以覆盖默认Key")
                        base_url_input = gr.Textbox(label="Base URL", value="https://api.deepseek.com/v1")
                        model_input = gr.Textbox(label="Model Name", value="deepseek-chat")
                        temp_slider = gr.Slider(minimum=0.1, maximum=2.0, value=0.7, step=0.1, label="Temperature")
                        top_p_slider = gr.Slider(minimum=0.1, maximum=1.0, value=1.0, step=0.05, label="Top P")
                        freq_pen_slider = gr.Slider(minimum=-2.0, maximum=2.0, value=0.5, step=0.1, label="Frequency Penalty")
                        pres_pen_slider = gr.Slider(minimum=-2.0, maximum=2.0, value=0.3, step=0.1, label="Presence Penalty")
                        max_tokens_slider = gr.Slider(minimum=100, maximum=2000, value=800, step=50, label="Max Tokens")
                        prompt_input = gr.Textbox(lines=3, value=DEFAULT_PROMPT, label="System Prompt")

            action_btn.click(
                fn=process_action,
                inputs=[char_checkboxes, state_current_event_id, dynamic_options, state_is_transition, prompt_input, api_key_input, base_url_input, model_input, temp_slider, top_p_slider, max_tokens_slider, pres_pen_slider, freq_pen_slider, chatbot, state_turn, state_san, state_money, state_gpa, state_args, state_chapter, state_affinity],
                outputs=[output_json, dynamic_options, chatbot, state_turn, status_text, action_btn, state_is_transition, state_current_event_id, state_san, state_money, state_gpa, state_args, state_chapter, stats_panel, char_info_panel, state_affinity]
            )

        # ==========================================
        # Tab 2: 📱 手机微信群聊
        # ==========================================
        with gr.TabItem("📱 手机界面 (微信)"):
            with gr.Row():
                with gr.Column(scale=6):
                    gr.Markdown("### 💬 【404 仙女下凡群（4）】")
                    wechat_chatbot = gr.Chatbot(label="群聊记录", height=500, avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/1053/1053244.png"))
                    wechat_input = gr.Textbox(label="在此输入内容...", placeholder="发送消息，看看室友们怎么回你...")
                    wechat_btn = gr.Button("发送 (Send)", variant="primary")
                    
                with gr.Column(scale=4):
                    gr.Markdown("### 📊 后台好感度同步雷达")
                    gr.Markdown("微信群会**读取当前的事件**进行回复，而且**不在寝室的角色不会发言**！")
                    wechat_char_panel = gr.Markdown(generate_char_info_md(list(CANDIDATE_POOL.keys())[:3], {name: 50 for name in CANDIDATE_POOL.keys()}))

            # 🌟 修复：把 checkbox 和 current_evt 传入微信，实现动态联动
            wechat_btn.click(
                fn=process_wechat_action,
                inputs=[wechat_input, char_checkboxes, state_current_event_id, state_turn, api_key_input, base_url_input, model_input, temp_slider, top_p_slider, wechat_chatbot, state_affinity],
                outputs=[wechat_input, wechat_chatbot, state_affinity, wechat_char_panel]
            )

        # ==========================================
        # Tab 3 & 4: RAG 与持久化
        # ==========================================
        with gr.TabItem("数据库检查器 (RAG)"):
            with gr.Row():
                refresh_btn = gr.Button("刷新数据库表单", variant="secondary")
                clear_mem_btn = gr.Button("清除历史互动记录 (危险)", variant="stop")
            def clear_and_refresh(): mm.clear_game_history(); return fetch_all_memories()
            memory_dataframe = gr.Dataframe(headers=["ID", "内容", "类型", "重要度", "时间戳"], datatype=["str", "str", "str", "number", "str"], interactive=False, wrap=True)
            clear_mem_btn.click(fn=clear_and_refresh, outputs=memory_dataframe)
            refresh_btn.click(fn=fetch_all_memories, outputs=memory_dataframe)
            demo.load(fn=fetch_all_memories, outputs=memory_dataframe)

        with gr.TabItem("本地持久化存储 (Profile)"):
            def load_profile_json():
                try:
                    with open(mm.json_store.file_path, 'r', encoding='utf-8') as f: return f.read()
                except: return "{}"
            profile_code = gr.Code(language="json", label="Data Dump")
            refresh_profile_btn = gr.Button("刷新文件映射")
            refresh_profile_btn.click(fn=load_profile_json, outputs=profile_code)
            demo.load(fn=load_profile_json, outputs=profile_code)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
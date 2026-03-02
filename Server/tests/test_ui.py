import gradio as gr
import pandas as pd
import sys
import os
import glob
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from build_knowledge import build_knowledge
    build_knowledge()
except Exception as e:
    print(f"提示：请确保已手动运行过 build_knowledge.py 注入语料。({e})")

from src.core.game_engine import GameEngine
from src.core.wechat_system import WeChatSystem
from src.core.agent_system import ReflectionSystem

# ==========================================
# ⚙️ CMS 后台目录配置
# ==========================================
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "prompts")
EVENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "events")
LORES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lores")

engine = GameEngine()
reflection_engine = ReflectionSystem(engine.llm, PROMPTS_DIR)

DIR_MAPPING = {
    "root": "🏠 核心基座 (底层 Prompt)",
    "characters": "👥 角色档案 (室友人设与语料)",
    "skills": "🧩 动态技能 (流行词等插件)",
    "world": "🌍 世界观 (学校与 NPC 设定)"
}
INV_DIR_MAPPING = {v: k for k, v in DIR_MAPPING.items()}

def get_categories():
    if not os.path.exists(PROMPTS_DIR): return [DIR_MAPPING["root"]]
    items = os.listdir(PROMPTS_DIR)
    dirs = [d for d in items if os.path.isdir(os.path.join(PROMPTS_DIR, d))]
    display_dirs = [DIR_MAPPING["root"]]
    for d in sorted(dirs): display_dirs.append(DIR_MAPPING.get(d, f"📁 {d}"))
    return display_dirs

def get_files_by_category(display_cat):
    if not os.path.exists(PROMPTS_DIR): return []
    real_cat = INV_DIR_MAPPING.get(display_cat, display_cat.replace("📁 ", ""))
    target_dir = PROMPTS_DIR if real_cat == "root" else os.path.join(PROMPTS_DIR, real_cat)
    if not os.path.exists(target_dir): return []
    search_pattern = os.path.join(target_dir, "**", "*.md")
    files = glob.glob(search_pattern, recursive=True)
    return sorted([os.path.relpath(f, target_dir) for f in files])

def _get_real_path(display_cat, filename):
    if not filename: return None
    real_cat = INV_DIR_MAPPING.get(display_cat, display_cat.replace("📁 ", ""))
    return filename if real_cat == "root" else os.path.join(real_cat, filename)

def load_prompt_content_ui(display_cat, filename):
    rel_path = _get_real_path(display_cat, filename)
    if not rel_path: return ""
    try:
        with open(os.path.join(PROMPTS_DIR, rel_path), 'r', encoding='utf-8') as f: return f.read()
    except Exception as e: return f"读取失败: {e}"

def save_prompt_content_ui(display_cat, filename, content):
    rel_path = _get_real_path(display_cat, filename)
    if not rel_path: return gr.update(value="⚠️ 请选择文件！")
    try:
        with open(os.path.join(PROMPTS_DIR, rel_path), 'w', encoding='utf-8') as f: f.write(content)
        return gr.update(value=f"✅ `{rel_path}` 保存成功！")
    except Exception as e: return gr.update(value=f"❌ 保存失败: {e}")

def create_new_file_ui(display_cat, new_path):
    if not new_path.strip(): return gr.update(), gr.update(), gr.update(value="⚠️ 路径不能为空！"), gr.update()
    if not new_path.endswith('.md'): new_path += '.md'
    real_cat = INV_DIR_MAPPING.get(display_cat, display_cat.replace("📁 ", ""))
    target_dir = PROMPTS_DIR if real_cat == "root" else os.path.join(PROMPTS_DIR, real_cat)
    full_path = os.path.join(target_dir, new_path)
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        init_content = "\n\n在此输入设定内容..."
        if not os.path.exists(full_path):
            with open(full_path, 'w', encoding='utf-8') as f: f.write(init_content)
        else:
            with open(full_path, 'r', encoding='utf-8') as f: init_content = f.read()
        return gr.update(choices=get_files_by_category(display_cat), value=new_path), init_content, gr.update(value=f"✅ 成功创建！"), gr.update(value="")
    except Exception as e: return gr.update(), gr.update(), gr.update(value=f"❌ 创建失败: {e}"), gr.update()

def get_event_files():
    if not os.path.exists(EVENTS_DIR): os.makedirs(EVENTS_DIR, exist_ok=True)
    return sorted([f for f in os.listdir(EVENTS_DIR) if f.endswith('.csv')])

def load_event_csv(filename):
    if not filename: return pd.DataFrame()
    try: return pd.read_csv(os.path.join(EVENTS_DIR, filename), dtype=str).fillna("")
    except Exception as e: return pd.DataFrame({"错误": [f"读取失败: {e}"]})

def save_event_csv(filename, df_content):
    if not filename: return gr.update(value="⚠️ 请选择剧本文件！")
    try:
        if isinstance(df_content, str): return gr.update(value="❌ 数据格式错误，请检查表格。")
        df_content.to_csv(os.path.join(EVENTS_DIR, filename), index=False, encoding='utf-8-sig')
        import src.core.event_script as es
        from src.core.data_loader import load_all_events
        es.EVENT_DATABASE.clear()
        es.EVENT_DATABASE.update(load_all_events(EVENTS_DIR))
        return gr.update(value=f"✅ `{filename}` 保存成功并已热重载！")
    except Exception as e: return gr.update(value=f"❌ 保存失败: {e}")

def create_new_event_file(filename):
    if not filename.strip(): return gr.update(), pd.DataFrame(), gr.update(value="⚠️ 不能为空", visible=True)
    if not filename.endswith('.csv'): filename += '.csv'
    path = os.path.join(EVENTS_DIR, filename)
    try:
        os.makedirs(EVENTS_DIR, exist_ok=True)
        cols = ["Event_ID", "事件标题", "所属章节", "事件类型", "触发条件", "专属角色", "是否Boss", "描述", "潜在冲突点", "玩家交互", "结果", "预设剧本"]
        default_data = [["EVT_NEW_01", "新事件片段", "1", "CG过场", "", "", "FALSE", "描述内容...", "", "", "", "旁白:开始了|玩家:说话"]]
        df = pd.DataFrame(default_data, columns=cols)
        if not os.path.exists(path): df.to_csv(path, index=False, encoding='utf-8-sig')
        else: df = pd.read_csv(path, dtype=str).fillna("")
        return gr.update(choices=get_event_files(), value=filename), df, gr.update(value=f"✅ 创建成功！", visible=True)
    except Exception as e: return gr.update(), pd.DataFrame(), gr.update(value=f"❌ 创建失败: {e}", visible=True)

def load_timeline_config():
    timeline_path = os.path.join(EVENTS_DIR, "timeline.json")
    if not os.path.exists(timeline_path): engine.director.reload_timeline()
    with open(timeline_path, 'r', encoding='utf-8') as f: return f.read()

def save_timeline_config(content):
    try:
        data = json.loads(content)
        if not isinstance(data, dict): return gr.update(value="❌ 保存失败：必须是字典对象！")
        with open(os.path.join(EVENTS_DIR, "timeline.json"), 'w', encoding='utf-8') as f: f.write(content)
        engine.director.reload_timeline()
        return gr.update(value="✅ 时间轴保存成功并已热重载生效！")
    except Exception as e: return gr.update(value=f"❌ 格式错误，请检查 JSON 语法: {e}")

# ==========================================
# 🎮 主线推演逻辑
# ==========================================
def ui_process_main(selected_chars, current_evt_id, player_choice, is_transition, api_key_val, base_url_val, model_val, tmp, top_p, max_tokens, pres_pen, freq_pen, hist, turn, san, money, gpa, arg_count, chapter, affinity, wechat_data_dict, current_chat_name):
    if not is_transition and current_evt_id != "" and not player_choice:
        yield gr.update(), gr.update(), gr.update(), gr.update(), hist + [("（未作选择）", "⚠️ 请选择一项行为！")], turn, gr.update(), gr.update(), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, gr.update(), gr.update(), affinity, gr.update(), wechat_data_dict, gr.update()
        return

    ws = WeChatSystem(selected_chars)
    for ch in ws.channels.keys():
        if ch not in wechat_data_dict: wechat_data_dict[ch] = []

    action_text = player_choice if player_choice else "（时间推移...）"
    yield gr.update(), gr.update(), gr.update(), gr.update(visible=False), hist + [(action_text, "⏳ *局势推演中...*")], turn, gr.update(), gr.update(value="⏳ 推演中...", interactive=False), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, gr.update(), gr.update(), affinity, gr.update(), wechat_data_dict, gr.update()

    res = engine.play_main_turn(action_text, selected_chars, current_evt_id, is_transition, api_key_val, base_url_val, model_val, tmp, top_p, max_tokens, pres_pen, freq_pen, san, money, gpa, arg_count, chapter, turn, affinity, wechat_data_dict)
    
    if "error" in res:
        yield f"系统错误: {res['error']}", res.get("sys_prompt", ""), res.get("user_prompt", ""), gr.update(visible=True), hist + [(action_text, f"❌ 系统错误: {res['error']}")], turn, "错误", gr.update(value="重试", interactive=True), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, f"SAN: {san}", gr.update(), affinity, gr.update(), wechat_data_dict, gr.update()
        return
        
    if res.get("is_game_over"):
        yield gr.update(), gr.update(), gr.update(), gr.update(visible=False), hist + [(action_text, res["msg"])], res["turn"], "游戏结束", gr.update(value="游戏结束", interactive=False), False, "", res["san"], res["money"], res["gpa"], res["arg_count"], res["chapter"], f"SAN: {res['san']}", gr.update(), res["affinity"], gr.update(), wechat_data_dict, gr.update()
        return

    hist.append((action_text, res["display_text"]))
    
    new_chats_ui_update = gr.update()
    wechat_chatbot_update = gr.update() 
    
    if res["wechat_notifications"]:
        notif_msg = "\n\n🔔 **【手机震动】您收到新的微信消息！**\n"
        latest_chat = current_chat_name
        
        for w in res["wechat_notifications"]:
            c_name = w.get("chat_name", "")
            sender = w.get("sender", "神秘人")
            msg = w.get("message", w.get("content", "（发来一条未知消息）"))
            
            if sender == "陆陈安然":
                wechat_data_dict[c_name].append((msg, None)) 
            else:
                wechat_data_dict[c_name].append((None, f"**{sender}**: {msg}")) 
                notif_msg += f"- *来自 {c_name}*: {msg[:10]}...\n"
                
            latest_chat = c_name 
            
        hist[-1] = (hist[-1][0], hist[-1][1] + notif_msg) 
        new_chats_ui_update = gr.update(choices=list(wechat_data_dict.keys()), value=latest_chat)
        wechat_chatbot_update = wechat_data_dict[latest_chat]
    else:
        if current_chat_name in wechat_data_dict:
            wechat_chatbot_update = wechat_data_dict[current_chat_name]

    stats_md_text = f"**SAN值**: {res['san']}/100 &nbsp;|&nbsp; **生活费**: ¥{res['money']} &nbsp;|&nbsp; **当前GPA**: {res['gpa']:.2f} &nbsp;|&nbsp; **本章争吵**: {res['arg_count']}次"
    
    btn_text = "确认并进入下一阶段" if res["is_end"] else "确认行动"
    has_options = bool(res.get("next_options", []))
    options_ui = gr.update(choices=res.get("next_options", []), visible=has_options, value=None)
    
    char_md = "### 室友档案与关系监控\n---\n"
    for name, p in engine.candidate_pool.items():
        role_status = "[在场]" if name in selected_chars else "[缺席]"
        aff = res["affinity"].get(name, 50)
        char_md += f"**{name}** {role_status} | {aff}/100\n"

    yield res["res_text"], res.get("sys_prompt", ""), res.get("user_prompt", ""), options_ui, hist, res["turn"], f"第 {res['chapter']} 章 - 回合 {res['turn']}", gr.update(value=btn_text, interactive=True), res["is_end"], res["current_evt_id"], res["san"], res["money"], res["gpa"], res["arg_count"], res["chapter"], stats_md_text, char_md, res["affinity"], new_chats_ui_update, wechat_data_dict, wechat_chatbot_update

def trigger_reflection(hist, chapter, active_chars):
    if not hist:
        yield hist + [("系统", "⚠️ 暂无剧情历史，无法进行反思。")]
        return
        
    yield hist + [("系统", "🌙 *夜幕降临，室友们躺在床上，回想今天的遭遇... (AI 深度反思中)*")]
    
    # 把最近的 10 条对话记录提取出来作为反思材料
    recent_history = "\n".join([f"事件: {h[0]}\n结果: {h[1]}" for h in hist[-10:]])
    
    # 呼叫反思引擎
    logs = reflection_engine.trigger_night_reflection(chapter, recent_history, active_chars)
    
    yield hist + [("系统", logs)]
    
def switch_chat_channel(selected_channel, wechat_data_dict):
    if selected_channel not in wechat_data_dict: wechat_data_dict[selected_channel] = []
    return wechat_data_dict[selected_channel]


custom_css = ".status-card { background-color: #fafafa; padding: 15px; border-radius: 8px; border: 1px solid #eaeaea; margin-bottom: 10px; } .phone-panel { border-left: 2px dashed #ccc; padding-left: 15px; background: #fdfdfd; }"

with gr.Blocks(title="大学档案 | 沉浸式模拟系统", theme=gr.themes.Monochrome(), css=custom_css) as demo:
    state_affinity = gr.State({name: 50 for name in engine.candidate_pool.keys()})
    state_wechat_data = gr.State({"【404 仙女下凡大群】": []}) 
    
    with gr.Tabs():
        # ==========================================
        # Tab 1: 核心游戏视窗
        # ==========================================
        with gr.TabItem("🎮 核心游戏视窗"):
            state_current_event_id = gr.State("")
            state_turn, state_is_transition = gr.State(0), gr.State(True) 
            state_san, state_money, state_gpa, state_args, state_chapter = gr.State(80), gr.State(1500), gr.State(3.0), gr.State(0), gr.State(1)
            
            with gr.Row():
                with gr.Column(scale=6):
                    status_text = gr.Markdown("### 当前进度：系统待机")
                    chatbot = gr.Chatbot(label="现实世界 - 事件推演", height=550)
                    dynamic_options = gr.Radio(choices=[], label="玩家意图轮盘", visible=False)
                    with gr.Row():
                        action_btn = gr.Button("启动模拟流", variant="primary", scale=3)
                        reflect_btn = gr.Button("深夜结算", variant="secondary", scale=2)
                        toggle_phone_btn = gr.Button("掏出手机", variant="secondary", scale=1)
                    
                    with gr.Accordion("角色与生成参数控制台", open=False):
                        stats_panel = gr.Markdown("**SAN值**: 80/100 &nbsp;|&nbsp; **生活费**: ¥1500 &nbsp;|&nbsp; **GPA**: 3.00 &nbsp;|&nbsp; **本章争吵**: 0次")
                        char_checkboxes = gr.CheckboxGroup(choices=list(engine.candidate_pool.keys()), label="在场角色", value=list(engine.candidate_pool.keys())[:3])
                        char_info_panel = gr.Markdown("### 室友关系监控")
                        api_key_input = gr.Textbox(label="API Key", type="password")
                        base_url_input = gr.Textbox(label="Base URL", value="https://api.deepseek.com/v1")
                        model_input = gr.Textbox(label="Model Name", value="deepseek-chat")
                        temp_slider = gr.Slider(minimum=0.1, maximum=2.0, value=0.7, label="Temperature")
                        top_p_slider = gr.Slider(minimum=0.1, maximum=1.0, value=1.0, label="Top P")
                        freq_pen_slider = gr.Slider(minimum=-2.0, maximum=2.0, value=0.5, label="Freq Penalty")
                        pres_pen_slider = gr.Slider(minimum=-2.0, maximum=2.0, value=0.3, label="Pres Penalty")
                        max_tokens_slider = gr.Slider(minimum=100, maximum=2000, value=800, label="Max Tokens")

                    with gr.Accordion("💡 开发者排错与监控面板 (Debug)", open=False):
                        gr.Markdown("遇到 AI 发癫？点开这里查看它究竟收到了什么指令，以及它吐出了什么原格式。")
                        output_json = gr.Code(language="json", label="1. DM(统筹系统) 最终渲染的 JSON", interactive=False)
                        sys_prompt_out = gr.Code(language="markdown", label="2. DM 的 System Prompt (全局规则)", interactive=False)
                        user_prompt_out = gr.Code(language="markdown", label="3. DM 的 User Prompt (含所有 NPC 的独立思考结果！)", interactive=False)

                with gr.Column(scale=4, visible=False, elem_classes="phone-panel") as phone_panel:
                    gr.Markdown("### 📱 微信屏幕视窗 (只读)")
                    chat_selector = gr.Dropdown(choices=["【404 仙女下凡大群】"], value="【404 仙女下凡大群】", label="当前聊天窗口", interactive=True)
                    wechat_chatbot = gr.Chatbot(label="微信聊天记录", height=480, avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/1053/1053244.png"))

            def toggle_phone(is_open):
                new_state = not is_open
                return gr.update(visible=new_state), "⬇️ 收起手机" if new_state else "📱 掏出手机", new_state
            
            phone_state = gr.State(False)
            reflect_btn.click(fn=trigger_reflection,inputs=[chatbot, state_chapter, char_checkboxes],outputs=[chatbot])
            toggle_phone_btn.click(fn=toggle_phone, inputs=phone_state, outputs=[phone_panel, toggle_phone_btn, phone_state])
            chat_selector.change(fn=switch_chat_channel, inputs=[chat_selector, state_wechat_data], outputs=[wechat_chatbot])

            action_btn.click(
                fn=ui_process_main,
                inputs=[char_checkboxes, state_current_event_id, dynamic_options, state_is_transition, api_key_input, base_url_input, model_input, temp_slider, top_p_slider, max_tokens_slider, pres_pen_slider, freq_pen_slider, chatbot, state_turn, state_san, state_money, state_gpa, state_args, state_chapter, state_affinity, state_wechat_data, chat_selector],
                outputs=[output_json, sys_prompt_out, user_prompt_out, dynamic_options, chatbot, state_turn, status_text, action_btn, state_is_transition, state_current_event_id, state_san, state_money, state_gpa, state_args, state_chapter, stats_panel, char_info_panel, state_affinity, chat_selector, state_wechat_data, wechat_chatbot]
            )

        # ==========================================
        # Tab 2: 提示词与设定后台 (三层)
        # ==========================================
        with gr.TabItem("⚙️ 设定与提示词后台 (CMS)"):
            with gr.Tabs():
                # --- 子 Tab 1: 文本编辑器 ---
                with gr.TabItem("📝 文本档案编辑器 (Markdown)"):
                    gr.Markdown("### 📝 动态 Prompt 结构化管理器\n> 修改设定后点击保存，**下一回合即刻生效。**")
                    with gr.Row():
                        with gr.Column(scale=3):
                            category_selector = gr.Dropdown(choices=get_categories(), value=DIR_MAPPING["root"], label="📂 第一级：功能模块", interactive=True)
                            file_selector = gr.Dropdown(choices=get_files_by_category(DIR_MAPPING["root"]), label="📄 第二级：配置文件", interactive=True)
                            with gr.Accordion("➕ 新建子目录/文件", open=False):
                                new_file_input = gr.Textbox(label="相对路径 (如: 配角/阿姨.md)", placeholder="输入路径...", show_label=True)
                                create_file_btn = gr.Button("✨ 新建并打开", variant="secondary")
                            refresh_files_btn = gr.Button("🔄 重新扫描目录", size="sm")
                        with gr.Column(scale=9):
                            prompt_editor = gr.Code(language="markdown", label="文件内容编辑器", lines=20, interactive=True)
                            save_prompt_btn = gr.Button("💾 写入到硬盘 (立即生效)", variant="primary")
                            save_status = gr.Markdown("")
        
                    def on_category_change(cat):
                        files = get_files_by_category(cat)
                        first_file = files[0] if files else None
                        return gr.update(choices=files, value=first_file), load_prompt_content_ui(cat, first_file) if first_file else ""
                    category_selector.change(fn=on_category_change, inputs=[category_selector], outputs=[file_selector, prompt_editor])
                    file_selector.change(fn=load_prompt_content_ui, inputs=[category_selector, file_selector], outputs=[prompt_editor])
                    save_prompt_btn.click(fn=save_prompt_content_ui, inputs=[category_selector, file_selector, prompt_editor], outputs=[save_status])
                    create_file_btn.click(fn=create_new_file_ui, inputs=[category_selector, new_file_input], outputs=[file_selector, prompt_editor, save_status, new_file_input])
                    refresh_files_btn.click(fn=lambda: (gr.update(choices=get_categories(), value=DIR_MAPPING["root"]), gr.update(choices=get_files_by_category(DIR_MAPPING["root"]), value=None), ""), outputs=[category_selector, file_selector, prompt_editor])

                # --- 子 Tab 2: 人际偏见矩阵 ---
                with gr.TabItem("🕸️ 角色社交网络与偏见 (CSV)"):
                    gr.Markdown("### 🕸️ 人际关系偏见矩阵\n> 在这里配置每个角色对其他角色的【表面态度】与【内心真实评价】。")
                    def load_rel_csv():
                        path = os.path.join(PROMPTS_DIR, "characters", "relationship.csv")
                        if os.path.exists(path): return pd.read_csv(path, dtype=str).fillna("")
                        return pd.DataFrame(columns=["评价者", "被评价者", "表面态度", "内心真实评价"])
                        
                    def save_rel_csv(df):
                        path = os.path.join(PROMPTS_DIR, "characters", "relationship.csv")
                        try:
                            if isinstance(df, str): return gr.update(value="❌ 数据格式错误。")
                            df.to_csv(path, index=False, encoding='utf-8-sig')
                            return gr.update(value="✅ 关系矩阵保存成功！AI 将在下一回合读取最新偏见。")
                        except Exception as e: return gr.update(value=f"❌ 保存失败: {e}")
                            
                    with gr.Row():
                        rel_editor = gr.Dataframe(value=load_rel_csv(), type="pandas", label="人物社交网络雷达图", interactive=True, height=350)
                    with gr.Row():
                        save_rel_btn = gr.Button("💾 保存并应用偏见设定", variant="primary")
                        rel_status = gr.Markdown("")
                        
                    save_rel_btn.click(fn=save_rel_csv, inputs=[rel_editor], outputs=[rel_status])

                # --- 子 Tab 3: 角色专属语料库 ---
                with gr.TabItem("🗣️ 角色专属语料库 (Lore)"):
                    gr.Markdown("### 🗣️ 分角色金句与语录管理\n> 你可以为每个角色单独配置她们的口头禅和经典经历。**保存后会自动重构 ChromaDB 向量库，AI 下一句话就能回忆起来！**")
                    
                    os.makedirs(LORES_DIR, exist_ok=True)

                    def get_lore_chars():
                        chars = list(engine.candidate_pool.keys())
                        if "陆陈安然" not in chars: chars.insert(0, "陆陈安然")
                        return chars

                    def load_lore_csv(char_name):
                        if not char_name: return pd.DataFrame(columns=["场景标签", "经典台词"])
                        path = os.path.join(LORES_DIR, f"{char_name}.csv")
                        if os.path.exists(path):
                            return pd.read_csv(path, dtype=str).fillna("")
                        return pd.DataFrame(columns=["场景标签", "经典台词"])

                    def save_lore_csv(char_name, df):
                        if not char_name: return gr.update(value="⚠️ 请先在左侧选择一个角色！")
                        try:
                            if isinstance(df, str): return gr.update(value="❌ 数据格式错误。")
                            path = os.path.join(LORES_DIR, f"{char_name}.csv")
                            df.to_csv(path, index=False, encoding='utf-8-sig')
                            
                            build_knowledge()
                            return gr.update(value=f"✅ 【{char_name}】的语料已保存，并成功热写入 RAG 潜意识网络！")
                        except Exception as e:
                            return gr.update(value=f"❌ 保存失败: {e}")

                    with gr.Row():
                        with gr.Column(scale=2):
                            lore_char_selector = gr.Dropdown(choices=get_lore_chars(), label="👥 选中角色进行编辑", value="陆陈安然", interactive=True)
                            
                        with gr.Column(scale=10):
                            lore_editor = gr.Dataframe(
                                value=load_lore_csv("陆陈安然"),
                                type="pandas", 
                                label="角色语录表 (双击修改，点击右下角 + 号新增)", 
                                headers=["场景标签", "经典台词"],
                                interactive=True, 
                                height=400
                            )
                            save_lore_btn = gr.Button("💾 保存语料并重构潜意识网络", variant="primary")
                            lore_save_status = gr.Markdown("")
                            
                    lore_char_selector.change(fn=load_lore_csv, inputs=[lore_char_selector], outputs=[lore_editor])
                    save_lore_btn.click(fn=save_lore_csv, inputs=[lore_char_selector, lore_editor], outputs=[lore_save_status])


        # ==========================================
        # Tab 3: 剧本与事件编辑器
        # ==========================================
        with gr.TabItem("🎬 剧本数据表与时间轴"):
            with gr.Accordion("📅 章节时间轴配置 (timeline.json)", open=True):
                gr.Markdown("> 编写 **JSON 数组** 来严格定义每一章触发哪些事件卡池。可用关键词：`CG`, `条件`, `专属`, `通用`, `随机或专属`, `Boss`。")
                timeline_editor = gr.Code(language="json", label="时间轴配置", value=load_timeline_config(), lines=8, interactive=True)
                save_timeline_btn = gr.Button("💾 保存时间轴并重载", variant="secondary")
                timeline_status = gr.Markdown("")
                save_timeline_btn.click(fn=save_timeline_config, inputs=[timeline_editor], outputs=[timeline_status])

            gr.Markdown("---")
            gr.Markdown("### 📅 剧本数据表热更新后台\n> 双击单元格直接修改。CG剧情请将类型填为`CG过场`并在【预设剧本】中写`人名:台词|人名:台词`。")
            
            with gr.Row():
                with gr.Column(scale=2):
                    event_file_selector = gr.Dropdown(choices=get_event_files(), label="📄 现有剧本表 (CSV)", interactive=True)
                    with gr.Accordion("➕ 新建空剧本表", open=False):
                        new_event_input = gr.Textbox(label="文件名 (如: chapter2.csv)", placeholder="输入名称...")
                        create_event_btn = gr.Button("✨ 新建表单", variant="secondary")
                    refresh_events_btn = gr.Button("🔄 重新扫描目录", size="sm")
                with gr.Column(scale=10):
                    event_editor = gr.Dataframe(type="pandas", label="剧本表可视化编辑器", interactive=True, height=400)
                    save_event_btn = gr.Button("💾 保存表格数据并强制热重载", variant="primary")
                    save_event_status = gr.Markdown("")

            event_file_selector.change(fn=load_event_csv, inputs=[event_file_selector], outputs=[event_editor])
            save_event_btn.click(fn=save_event_csv, inputs=[event_file_selector, event_editor], outputs=[save_event_status])
            create_event_btn.click(fn=create_new_event_file, inputs=[new_event_input], outputs=[event_file_selector, event_editor, save_event_status])
            refresh_events_btn.click(fn=lambda: gr.update(choices=get_event_files()), outputs=[event_file_selector])


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
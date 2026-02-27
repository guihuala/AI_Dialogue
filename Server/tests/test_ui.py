import gradio as gr
import pandas as pd
import sys
import os
import glob

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from build_knowledge import build_knowledge
    build_knowledge()
except Exception as e:
    print(f"提示：请确保已手动运行过 build_knowledge.py 注入语料。({e})")

from src.core.game_engine import GameEngine
from src.core.wechat_system import WeChatSystem

# 初始化全局唯一游戏引擎实例
engine = GameEngine()

# ==========================================
# ⚙️ 新增：后台文件管理系统逻辑 (CMS)
# ==========================================
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "prompts")

def get_prompt_files():
    """获取所有 prompts 目录下的 md 文件"""
    if not os.path.exists(PROMPTS_DIR):
        return []
    search_pattern = os.path.join(PROMPTS_DIR, "**", "*.md")
    files = glob.glob(search_pattern, recursive=True)
    # 返回相对路径，方便在 UI 中展示
    return sorted([os.path.relpath(f, PROMPTS_DIR) for f in files])

def load_prompt_content(rel_path):
    """读取指定的文件内容"""
    if not rel_path: return ""
    full_path = os.path.join(PROMPTS_DIR, rel_path)
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"读取失败: {e}"

def save_prompt_content(rel_path, content):
    """保存内容到指定文件"""
    if not rel_path: return gr.update(value="⚠️ 请先在左侧选择一个配置文件！")
    full_path = os.path.join(PROMPTS_DIR, rel_path)
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return gr.update(value=f"✅ `{rel_path}` 保存成功！(下一回合立即生效)")
    except Exception as e:
        return gr.update(value=f"❌ 保存失败: {e}")

# ==========================================
# 🎮 原有：主线推演逻辑
# ==========================================
def ui_process_main(selected_chars, current_evt_id, player_choice, is_transition, api_key_val, base_url_val, model_val, tmp, top_p, max_tokens, pres_pen, freq_pen, hist, turn, san, money, gpa, arg_count, chapter, affinity, wechat_data_dict):
    if not is_transition and current_evt_id != "" and not player_choice:
        yield gr.update(), gr.update(), hist + [("（未作选择）", "⚠️ 请选择一项行为！")], turn, gr.update(), gr.update(), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, gr.update(), gr.update(), affinity, gr.update(), wechat_data_dict
        return

    ws = WeChatSystem(selected_chars)
    for ch in ws.channels.keys():
        if ch not in wechat_data_dict: wechat_data_dict[ch] = []

    action_text = player_choice if (not is_transition and current_evt_id != "") else "（时间推移...）"
    yield gr.update(), gr.update(visible=False), hist + [(action_text, "⏳ *局势推演中...*")], turn, gr.update(), gr.update(value="⏳ 推演中...", interactive=False), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, gr.update(), gr.update(), affinity, gr.update(), wechat_data_dict

    res = engine.play_main_turn(action_text, selected_chars, current_evt_id, is_transition, api_key_val, base_url_val, model_val, tmp, top_p, max_tokens, pres_pen, freq_pen, san, money, gpa, arg_count, chapter, turn, affinity, wechat_data_dict)
    
    if "error" in res:
        yield f"系统错误: {res['error']}", gr.update(visible=True), hist + [(action_text, f"❌ 系统错误: {res['error']}")], turn, "错误", gr.update(value="重试", interactive=True), is_transition, current_evt_id, san, money, gpa, arg_count, chapter, f"**SAN**: {san}", gr.update(), affinity, gr.update(), wechat_data_dict
        return
        
    if res.get("is_game_over"):
        yield gr.update(), gr.update(visible=False), hist + [(action_text, res["msg"])], res["turn"], "游戏结束", gr.update(value="游戏结束", interactive=False), False, "", res["san"], res["money"], res["gpa"], res["arg_count"], res["chapter"], f"**SAN**: {res['san']}", gr.update(), res["affinity"], gr.update(), wechat_data_dict
        return

    hist.append((action_text, res["display_text"]))
    
    new_chats_ui_update = gr.update()
    if res["wechat_notifications"]:
        notif_msg = "\n\n🔔 **【手机震动】您收到新的微信消息！**\n"
        for w in res["wechat_notifications"]:
            c_name = w.get("chat_name", "")
            sender = w.get("sender", "神秘人")
            msg = w.get("message", "")
            
            if sender == "陆陈安然":
                wechat_data_dict[c_name].append((msg, None)) 
            else:
                wechat_data_dict[c_name].append((None, f"**{sender}**: {msg}")) 
                
            notif_msg += f"- *来自 {c_name}*: {msg[:10]}...\n"
            
        hist[-1] = (hist[-1][0], hist[-1][1] + notif_msg) 
        new_chats_ui_update = gr.update(choices=list(wechat_data_dict.keys()), value=res["wechat_notifications"][-1].get("chat_name"))

    stats_md_text = f"**SAN值**: {res['san']}/100 &nbsp;|&nbsp; **生活费**: ¥{res['money']} &nbsp;|&nbsp; **当前GPA**: {res['gpa']:.2f} &nbsp;|&nbsp; **本章争吵**: {res['arg_count']}次"
    btn_text = "继续下一步" if res["is_end"] else "确认行动"
    options_ui = gr.update(choices=[], visible=False, value=None) if res["is_end"] else gr.update(choices=res["next_options"], visible=True, value=None)
    
    char_md = "### 室友档案与关系监控\n---\n"
    for name, p in engine.candidate_pool.items():
        role_status = "[在场]" if name in selected_chars else "[缺席]"
        aff = res["affinity"].get(name, 50)
        char_md += f"**{name}** {role_status} | {aff}/100\n"

    yield res["res_text"], options_ui, hist, res["turn"], f"第 {res['chapter']} 章 - 回合 {res['turn']}", gr.update(value=btn_text, interactive=True), res["is_end"], res["current_evt_id"], res["san"], res["money"], res["gpa"], res["arg_count"], res["chapter"], stats_md_text, char_md, res["affinity"], new_chats_ui_update, wechat_data_dict

def switch_chat_channel(selected_channel, wechat_data_dict):
    if selected_channel not in wechat_data_dict: wechat_data_dict[selected_channel] = []
    return wechat_data_dict[selected_channel]

def fetch_all_memories():
    try:
        data = engine.mm.vector_store.collection.get()
        if not data or not data['ids']: return pd.DataFrame(columns=["ID", "内容", "类型", "重要度", "时间戳"])
        rows = [{"ID": data['ids'][i], "内容": data['documents'][i], "类型": (data['metadatas'][i] if data['metadatas'] else {}).get("type", "unknown"), "重要度": (data['metadatas'][i] if data['metadatas'] else {}).get("importance", 5), "时间戳": (data['metadatas'][i] if data['metadatas'] else {}).get("timestamp", "")} for i in range(len(data['ids']))]
        return pd.DataFrame(rows)
    except Exception as e: return pd.DataFrame(columns=["ID", f"读取出错: {e}", "类型", "重要度", "时间戳"])

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
                        toggle_phone_btn = gr.Button("📱 掏出手机", variant="secondary", scale=1)
                    
                    with gr.Accordion("角色与生成参数控制台", open=False):
                        stats_panel = gr.Markdown("**SAN值**: 80/100 &nbsp;|&nbsp; **生活费**: ¥1500 &nbsp;|&nbsp; **GPA**: 3.00 &nbsp;|&nbsp; **本章争吵**: 0次")
                        char_checkboxes = gr.CheckboxGroup(choices=list(engine.candidate_pool.keys()), label="在场角色", value=list(engine.candidate_pool.keys())[:3])
                        char_info_panel = gr.Markdown("### 室友关系监控")
                        output_json = gr.Code(language="json", label="模型交互 JSON", visible=False)
                        api_key_input = gr.Textbox(label="API Key", type="password")
                        base_url_input = gr.Textbox(label="Base URL", value="https://api.deepseek.com/v1")
                        model_input = gr.Textbox(label="Model Name", value="deepseek-chat")
                        temp_slider = gr.Slider(minimum=0.1, maximum=2.0, value=0.7, label="Temperature")
                        top_p_slider = gr.Slider(minimum=0.1, maximum=1.0, value=1.0, label="Top P")
                        freq_pen_slider = gr.Slider(minimum=-2.0, maximum=2.0, value=0.5, label="Freq Penalty")
                        pres_pen_slider = gr.Slider(minimum=-2.0, maximum=2.0, value=0.3, label="Pres Penalty")
                        max_tokens_slider = gr.Slider(minimum=100, maximum=2000, value=800, label="Max Tokens")

                with gr.Column(scale=4, visible=False, elem_classes="phone-panel") as phone_panel:
                    gr.Markdown("### 📱 微信屏幕视窗 (只读)")
                    chat_selector = gr.Dropdown(choices=["【404 仙女下凡大群】"], value="【404 仙女下凡大群】", label="当前聊天窗口", interactive=True)
                    wechat_chatbot = gr.Chatbot(label="微信聊天记录", height=480, avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/1053/1053244.png"))

            def toggle_phone(is_open):
                new_state = not is_open
                return gr.update(visible=new_state), "⬇️ 收起手机" if new_state else "📱 掏出手机", new_state
            
            phone_state = gr.State(False)
            toggle_phone_btn.click(fn=toggle_phone, inputs=phone_state, outputs=[phone_panel, toggle_phone_btn, phone_state])
            chat_selector.change(fn=switch_chat_channel, inputs=[chat_selector, state_wechat_data], outputs=[wechat_chatbot])

            action_btn.click(
                fn=ui_process_main,
                inputs=[char_checkboxes, state_current_event_id, dynamic_options, state_is_transition, api_key_input, base_url_input, model_input, temp_slider, top_p_slider, max_tokens_slider, pres_pen_slider, freq_pen_slider, chatbot, state_turn, state_san, state_money, state_gpa, state_args, state_chapter, state_affinity, state_wechat_data],
                outputs=[output_json, dynamic_options, chatbot, state_turn, status_text, action_btn, state_is_transition, state_current_event_id, state_san, state_money, state_gpa, state_args, state_chapter, stats_panel, char_info_panel, state_affinity, chat_selector, state_wechat_data]
            )

        # ==========================================
        # Tab 2: 提示词与设定后台 (新增的 CMS 模块)
        # ==========================================
        with gr.TabItem("⚙️ 设定与提示词后台 (CMS)"):
            gr.Markdown("### 📝 动态 Prompt 实时编辑器\n> 在此处修改世界观、角色设定或底层指令，点击保存后，**下一回合的对话将立刻应用新设定**，无需重启服务器！")
            
            with gr.Row():
                with gr.Column(scale=3):
                    prompt_file_selector = gr.Dropdown(choices=get_prompt_files(), label="📁 配置文件树", interactive=True)
                    refresh_files_btn = gr.Button("🔄 刷新文件列表", size="sm")
                with gr.Column(scale=9):
                    prompt_editor = gr.Code(language="markdown", label="文件内容编辑器", lines=25, interactive=True)
                    save_prompt_btn = gr.Button("💾 保存修改 (立即生效)", variant="primary")
                    save_status = gr.Markdown("")

            # 事件绑定
            prompt_file_selector.change(fn=load_prompt_content, inputs=[prompt_file_selector], outputs=[prompt_editor])
            save_prompt_btn.click(fn=save_prompt_content, inputs=[prompt_file_selector, prompt_editor], outputs=[save_status])
            
            def update_file_list():
                return gr.update(choices=get_prompt_files())
            refresh_files_btn.click(fn=update_file_list, outputs=[prompt_file_selector])

        # ==========================================
        # Tab 3: RAG 记忆后台
        # ==========================================
        with gr.TabItem("🧠 向量记忆数据库 (RAG)"):
            with gr.Row():
                refresh_btn = gr.Button("刷新数据库表单", variant="secondary")
                clear_mem_btn = gr.Button("清除历史记录", variant="stop")
            def clear_and_refresh(): engine.mm.clear_game_history(); return fetch_all_memories()
            memory_dataframe = gr.Dataframe(headers=["ID", "内容", "类型", "重要度", "时间戳"], datatype=["str", "str", "str", "number", "str"], interactive=False, wrap=True)
            clear_mem_btn.click(fn=clear_and_refresh, outputs=memory_dataframe)
            refresh_btn.click(fn=fetch_all_memories, outputs=memory_dataframe)
            demo.load(fn=fetch_all_memories, outputs=memory_dataframe)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
import gradio as gr
import pandas as pd
import os
import json
import requests

API_BASE = "http://127.0.0.1:8000/api"

# 直接通过相对路径定位 data 文件夹
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(BASE_DIR, "data", "prompts")
EVENTS_DIR = os.path.join(BASE_DIR, "data", "events")

# ==========================================
# API 请求封装
# ==========================================

def api_monitor_game():
    try:
        res = requests.get(f"{API_BASE}/game/monitor")
        return res.json().get("data", {})
    except Exception as e:
        return {}

def api_rebuild_knowledge():
    try:
        res = requests.post(f"{API_BASE}/system/rebuild_knowledge")
        return res.json().get("message", "重建成功")
    except Exception as e:
        return f"重建失败: {e}"

def api_update_settings(api_key, base_url, model):
    try:
        res = requests.post(f"{API_BASE}/system/settings", json={
            "api_key": api_key, "base_url": base_url, "model_name": model
        })
        return res.json().get("message", "设置成功")
    except Exception as e:
        return f"设置失败: {e}"

# ==========================================
# 界面逻辑
# ==========================================

def sync_from_unity():
    data = api_monitor_game()
    if not data or "response" not in data:
        return ("暂无数据，请先在 Unity 端点击一次选项！", "", 100, 2000, 4.0, "{}", 1, 0, "无", "[]", "", "")
    
    res = data["response"]
    req = data.get("request", {})
    
    display_msg = "[已成功捕获 Unity 手机端最新画面]\n\n" + res.get("display_text", "") + "\n\n" + res.get("res_text", "")
    
    return (
        display_msg, 
        res.get("current_evt_id", ""), 
        res.get("san", 100), 
        res.get("money", 2000), 
        res.get("gpa", 4.0), 
        json.dumps(res.get("affinity", {}), ensure_ascii=False), 
        res.get("chapter", 1), 
        res.get("turn", 0), 
        f"上一回合行动：{req.get('choice', '无')}", 
        json.dumps(req.get("wechat_data_list", []), ensure_ascii=False), 
        res.get("sys_prompt", ""), 
        res.get("user_prompt", "")
    )

def get_md_files():
    md_files = []
    if not os.path.exists(PROMPTS_DIR): return []
    for root, dirs, files in os.walk(PROMPTS_DIR):
        for file in files:
            if file.endswith(".md"):
                md_files.append(os.path.relpath(os.path.join(root, file), PROMPTS_DIR))
    return sorted(md_files)

def get_csv_files():
    if not os.path.exists(EVENTS_DIR): return []
    return sorted([f for f in os.listdir(EVENTS_DIR) if f.endswith(".csv")])

def load_prompt_fn(filepath):
    if not filepath: return ""
    with open(os.path.join(PROMPTS_DIR, filepath), "r", encoding="utf-8") as f:
        return f.read()
        
def save_prompt_fn(filepath, content):
    if not filepath: return "未选择文件"
    with open(os.path.join(PROMPTS_DIR, filepath), "w", encoding="utf-8") as f:
        f.write(content)
    return f"{filepath} 保存成功！记得点击下方的热重载按钮。"

def load_csv_fn(filename):
    if not filename: return pd.DataFrame()
    path = os.path.join(EVENTS_DIR, filename)
    try:
        return pd.read_csv(path, encoding='utf-8-sig')
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})
        
def save_csv_fn(filename, df):
    if not filename: return "未选择文件"
    path = os.path.join(EVENTS_DIR, filename)
    try:
        df.to_csv(path, index=False, encoding='utf-8-sig')
        return f"{filename} 保存成功！记得点击下方的热重载按钮。"
    except Exception as e:
        return f"保存失败: {e}"

# ==========================================
# UI 构建 (应用现代化主题)
# ==========================================
custom_theme = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="slate",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"]
)

with gr.Blocks(title="游戏后端控制台", theme=custom_theme) as demo:
    gr.Markdown("# 游戏核心系统控制台\n实时监控前端数据、编辑剧情资源与大模型配置。")
    
    with gr.Tab("实时监视器"):
        with gr.Row():
            sync_btn = gr.Button("抓取 Unity 端实时画面", variant="primary", size="lg")
        
        with gr.Row():
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### 基础状态")
                    state_evt_id = gr.Textbox(label="当前事件 ID", interactive=False)
                    with gr.Row():
                        state_chap = gr.Number(label="Chapter", value=1, interactive=False)
                        state_turn = gr.Number(label="Turn", value=0, interactive=False)
                    with gr.Row():
                        state_san = gr.Number(label="SAN", value=100, interactive=False)
                        state_money = gr.Number(label="Money", value=2000, interactive=False)
                        state_gpa = gr.Number(label="GPA", value=4.0, interactive=False)
                
                with gr.Group():
                    gr.Markdown("### 隐藏状态")
                    state_aff = gr.Textbox(label="好感度 (JSON)", lines=2, interactive=False)
                    state_wechat = gr.Textbox(label="微信记录 (JSON)", lines=2, interactive=False)
                    recent_events_state = gr.Textbox(label="近期历史", lines=2, interactive=False)

            with gr.Column(scale=2):
                output_display = gr.Textbox(label="剧情演出与系统日志", lines=18, interactive=False)
                
                with gr.Accordion("查看底层 Prompt (仅供排查问题时展开)", open=False):
                    sys_prompt_display = gr.Textbox(label="System Prompt", lines=8, interactive=False)
                    user_prompt_display = gr.Textbox(label="User Prompt", lines=5, interactive=False)
        
        sync_btn.click(
            sync_from_unity, 
            inputs=[], 
            outputs=[
                output_display, state_evt_id, state_san, state_money, state_gpa, 
                state_aff, state_chap, state_turn, recent_events_state, state_wechat, 
                sys_prompt_display, user_prompt_display
            ]
        )

    with gr.Tab("数据编辑器"):
        gr.Markdown("可视化修改后端的数据资源。**注意：修改保存后，请务必点击底部的【热重载】使其在服务器生效。**")
        with gr.Row():
            with gr.Column():
                with gr.Group():
                    gr.Markdown("### 提示词文件 (.md)")
                    prompt_selector = gr.Dropdown(choices=get_md_files(), label="选择需要编辑的文件")
                    prompt_editor = gr.Textbox(label="内容编辑区", lines=18)
                    save_prompt_btn = gr.Button("保存提示词更改", variant="secondary")
                    prompt_status = gr.Textbox(label="状态", lines=1, interactive=False)
                
                prompt_selector.change(load_prompt_fn, inputs=[prompt_selector], outputs=[prompt_editor])
                save_prompt_btn.click(save_prompt_fn, inputs=[prompt_selector, prompt_editor], outputs=[prompt_status])

            with gr.Column():
                with gr.Group():
                    gr.Markdown("### 剧本事件文件 (.csv)")
                    event_selector = gr.Dropdown(choices=get_csv_files(), label="选择剧本库文件")
                    event_editor = gr.Dataframe(label="数据表编辑区 (双击单元格修改)", interactive=True, wrap=True)
                    save_event_btn = gr.Button("保存剧本表更改", variant="secondary")
                    event_status = gr.Textbox(label="状态", lines=1, interactive=False)
                
                event_selector.change(load_csv_fn, inputs=[event_selector], outputs=[event_editor])
                save_event_btn.click(save_csv_fn, inputs=[event_selector, event_editor], outputs=[event_status])
        
        with gr.Row():
            rebuild_btn = gr.Button("热重载所有资源 (应用刚才的更改)", variant="primary", size="lg")
        with gr.Row():
            rebuild_status = gr.Textbox(label="热重载状态", lines=1, interactive=False)
            rebuild_btn.click(api_rebuild_knowledge, inputs=[], outputs=[rebuild_status])

    with gr.Tab("模型配置"):
        gr.Markdown("用于切换大语言模型接口。如果游戏响应过慢，建议在此处切换为极速模型（如阿里的通义千问）。")
        with gr.Group():
            with gr.Row():
                api_key_input = gr.Textbox(label="API Key", type="password", placeholder="输入你的 API Key")
                base_url_input = gr.Textbox(label="Base URL", value="https://dashscope.aliyuncs.com/compatible-mode/v1")
                model_input = gr.Textbox(label="Model Name", value="qwen-plus")
            
            with gr.Row():
                apply_settings_btn = gr.Button("保存并应用模型配置", variant="primary")
            
            with gr.Row():
                settings_msg = gr.Textbox(label="状态通知", lines=1, interactive=False)
            
            apply_settings_btn.click(api_update_settings, inputs=[api_key_input, base_url_input, model_input], outputs=[settings_msg])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
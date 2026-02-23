import gradio as gr
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.presets import CANDIDATE_POOL

from src.services.llm_service import LLMService

llm_service = LLMService()

# 提取所有候选人的中文名用于 UI 展示
char_choices = [p.Name for p in CANDIDATE_POOL.values()]

def run_test(selected_chars, user_input, temperature):
    if not selected_chars:
        return "请至少选择一名室友！"
        
    # 根据选中的中文名找回档案
    active_profiles = [p for p in CANDIDATE_POOL.values() if p.Name in selected_chars]
    
    char_descriptions = ""
    for p in active_profiles:
        char_descriptions += f"""
        - 姓名: {p.Name} ({p.Core_Archetype})
        - 行为逻辑: {p.Roommate_Behavior}
        - 说话风格: 语气{p.Speech_Pattern.Tone}，口头禅【{', '.join(p.Speech_Pattern.Catchphrases)}】。禁语：{', '.join(p.Speech_Pattern.Forbidden_Words)}。
        """

    system_prompt = f"""
    你是一个多角色大学生存游戏的底层系统。
    当前在宿舍的室友设定如下：
    {char_descriptions}
    
    必须严格返回以下 JSON 格式：
    {{
        "dialogue_sequence": [
            {{"speaker": "室友姓名", "content": "说的话", "mood": "情绪(neutral/happy/angry/sad等)"}}
        ]
    }}
    """
    
    try:
        # 调用大模型并传入调节好的温度
        res_text = llm_service.generate_response(
            system_prompt=system_prompt,
            user_input=f"我的行动/说话内容是：\"{user_input}\"",
            temperature=temperature
        )
        
        # 格式化 JSON 以便在界面上好看地展示
        parsed_json = json.loads(res_text)
        return json.dumps(parsed_json, indent=4, ensure_ascii=False)
    except Exception as e:
        return f"生成失败，请看终端报错：\n{e}"

# --- 构建 Gradio 网页 UI ---
with gr.Blocks(title="AI 剧本调教台") as demo:
    gr.Markdown("## 🎮 宿舍生存游戏 - AI 剧本调教台")
    
    with gr.Row():
        with gr.Column(scale=1):
            char_checkboxes = gr.CheckboxGroup(choices=char_choices, label="在场室友", value=["陈雨婷"])
            temp_slider = gr.Slider(minimum=0.1, maximum=1.5, value=0.8, step=0.1, label="温度 (Temperature - 越高越放飞，越低越死板)")
            user_input = gr.Textbox(lines=3, label="玩家(陆陈安然)的行动", placeholder="比如：阴阳怪气地质疑陈雨婷...")
            submit_btn = gr.Button("生成剧本", variant="primary")
            
        with gr.Column(scale=1):
            output_json = gr.Code(language="json", label="大模型返回的 JSON")

    # 绑定点击事件
    submit_btn.click(
        fn=run_test,
        inputs=[char_checkboxes, user_input, temp_slider],
        outputs=output_json
    )

if __name__ == "__main__":
    print("正在启动可视化测试台...")
    # 启动网页版 UI
    demo.launch(server_name="0.0.0.0", server_port=7860, inbrowser=True)
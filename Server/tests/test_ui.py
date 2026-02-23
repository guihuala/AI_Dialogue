import gradio as gr
import json
import sys
import os

# 确保路径可以找到 src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.presets import CANDIDATE_POOL
from src.services.llm_service import LLMService
from src.core.memory_manager import MemoryManager

llm_service = LLMService()

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(base_dir, "data")
os.makedirs(data_dir, exist_ok=True)

mm = MemoryManager(
    profile_path=os.path.join(data_dir, "profile_test.json"), 
    vector_db_path=os.path.join(data_dir, "chroma_db"), 
    llm_service=llm_service
)

char_choices = [p.Name for p in CANDIDATE_POOL.values()]

DEFAULT_PROMPT = """你是一个多角色大学生存游戏的底层系统。

[反人机核心原则]
1. 绝对不要说“好的”、“理解了”等AI客服废话。
2. 说话必须极其口语化，包含人类的瑕疵（如：适当的停顿、语气词“啧”、“呃”）。
3. 结合【近期对话上下文】，不要重复刚才说过的话！如果玩家反复说同一件事，你可以表现出不耐烦或愤怒。

必须严格返回以下 JSON 格式：
{
    "dialogue_sequence": [
        {"speaker": "室友姓名", "content": "说的话", "mood": "情绪(neutral/happy/angry/sad等)"}
    ]
}"""

def run_test(selected_chars, user_input, custom_prompt, temperature, chat_history):
    if not selected_chars:
        return "请至少选择一名室友！", "无", chat_history
        
    # 1. 组装室友设定
    active_profiles = [p for p in CANDIDATE_POOL.values() if p.Name in selected_chars]
    char_descriptions = "\n".join([f"- 姓名: {p.Name} | 性格: {p.Core_Archetype} | 口头禅: {', '.join(p.Speech_Pattern.Catchphrases)}" for p in active_profiles])

    # 2. 组装短期记忆 (提取最近3轮对话)
    short_term_history = "【近期对话上下文】\n"
    if not chat_history:
        short_term_history += "这是你们今天的第一次搭话。\n"
    else:
        for user_msg, ai_msg in chat_history[-3:]:
            short_term_history += f"我刚才说: {user_msg}\n室友刚才回复: {ai_msg}\n"

    # 3. 从 ChromaDB 检索长期记忆/语录
    try:
        relevant_memories = mm.vector_store.search(user_input, n_results=3)
        if relevant_memories:
            context_str = "\n".join([f"- {m['content']}" for m in relevant_memories])
            display_memory = context_str
        else:
            context_str = "暂无相关记忆。"
            display_memory = "数据库中暂无相关长期记忆。"
    except Exception as e:
        context_str = ""
        display_memory = f"检索记忆失败: {e}"

    # 4. 拼装发给大模型的最终指令
    final_system_prompt = f"{custom_prompt}\n\n【在场室友设定】\n{char_descriptions}"
    combined_context = f"【长期记忆/专属语录】\n{context_str}\n\n{short_term_history}"

    try:
        res_text = llm_service.generate_response(
            system_prompt=final_system_prompt,
            user_input=f"我现在说/做的是：\"{user_input}\"",
            context=combined_context,
            temperature=temperature
        )
        
        # 清理并解析 JSON
        if "```json" in res_text:
            res_text = res_text.replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(res_text)
        
        # 5. 提取 AI 的回复文本，更新记忆系统
        ai_responses = []
        for turn in parsed_json.get("dialogue_sequence", []):
            ai_responses.append(f"[{turn['speaker']}] {turn['content']}")
        ai_combined_text = " ".join(ai_responses)
        
        # 🌟 核心更新1：将本轮对话存入向量数据库（长期记忆）
        mm.save_interaction(user_input=user_input, ai_response=ai_combined_text, user_name="陆陈安然")
        
        # 🌟 核心更新2：更新界面上的聊天框（短期记忆）
        chat_history.append((user_input, ai_combined_text))
        
        return json.dumps(parsed_json, indent=4, ensure_ascii=False), display_memory, chat_history
        
    except Exception as e:
        return f"生成失败，报错：\n{e}", display_memory, chat_history

# 清空历史的辅助函数
def clear_history():
    return [], "", "短期记忆已清空。"

# --- 构建 Gradio 网页 UI ---
with gr.Blocks(title="AI 剧本调教台 & 记忆管理", theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🎮 宿舍生存游戏 - 角色调教与 RAG 监视台")
    
    with gr.Row():
        with gr.Column(scale=1):
            char_checkboxes = gr.CheckboxGroup(choices=char_choices, label="在场室友", value=["陈雨婷"])
            temp_slider = gr.Slider(minimum=0.1, maximum=1.5, value=0.8, step=0.1, label="温度 (越高越放飞)")
            
            with gr.Accordion("⚙️ 系统提示词 (System Prompt)", open=False):
                prompt_input = gr.Textbox(lines=10, value=DEFAULT_PROMPT, label="自定义规则")
            
            # 🌟 新增：短期记忆聊天框
            chatbot = gr.Chatbot(label="💬 当前对话上下文 (短期记忆)", height=250)
            
            user_input = gr.Textbox(lines=2, label="玩家(陆陈安然)的行动", placeholder="输入你想测试的话...")
            
            with gr.Row():
                submit_btn = gr.Button("🎲 生成剧本", variant="primary")
                clear_btn = gr.Button("🗑️ 清空当前对话")
            
        with gr.Column(scale=1):
            memory_output = gr.Textbox(lines=4, label="🧠 触发的长期记忆/语录 (ChromaDB)", interactive=False)
            output_json = gr.Code(language="json", label="🤖 大模型返回的 JSON")

    # 绑定事件
    submit_btn.click(
        fn=run_test,
        inputs=[char_checkboxes, user_input, prompt_input, temp_slider, chatbot],
        outputs=[output_json, memory_output, chatbot]
    )
    
    clear_btn.click(
        fn=clear_history,
        inputs=[],
        outputs=[chatbot, user_input, memory_output]
    )

if __name__ == "__main__":
    print("正在启动可视化测试台...")
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
import gradio as gr
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.presets import CANDIDATE_POOL
from src.services.llm_service import LLMService
from src.core.memory_manager import MemoryManager
from src.core.event_script import EVENT_DATABASE, CHAPTER_TRANSITIONS, get_random_event, get_boss_event

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

DEFAULT_PROMPT = """你是一个多角色大学生存游戏的跑团DM。

[核心职责]
1. 关注【当前剧情节奏】，推进群像交互（包含3~6句不同角色的发言）。
2. 根据【玩家行动】和【长期记忆】，严格推演室友反应，必须带有人类瑕疵和情绪。
3. 如果未到结局(is_end为false)，请动态生成 3 个供玩家下一步选择的【意图】。
4. 如果到达最终回合，给出强制收尾，并将 is_end 设为 true。

严格返回以下 JSON 格式：
{
    "dialogue_sequence": [
        {"speaker": "室友姓名", "content": "对话", "mood": "情绪"}
    ],
    "next_options": ["选项A", "选项B", "选项C"],
    "is_end": false
}"""

# ==========================================
# 肉鸽爬塔系统核心逻辑
# ==========================================
def advance_node(chapter, stage, used_events):
    """处理节点晋升与发牌"""
    stage += 1
    transition_text = ""
    
    # 过关判定：一村 4 层，第 4 层必定是 Boss，打完进下一章
    if stage > 4:
        chapter += 1
        stage = 1
        used_events = []
        if chapter > 4:
            return 5, 1, used_events, None, "🏆 恭喜毕业！游戏通关！"
        transition_text = CHAPTER_TRANSITIONS.get(chapter, f"进入第 {chapter} 章")
    
    # 第一层时，显示章节开头语
    if stage == 1 and chapter == 1:
        transition_text = CHAPTER_TRANSITIONS.get(1, "")

    # 发牌（抽事件）
    if stage == 4:
        next_event = get_boss_event(chapter)
        node_name = "👹 【章节 Boss】"
    else:
        next_event = get_random_event(chapter, used_events)
        node_name = f"❓ 【随机冲突 {stage}/3】"

    if next_event:
        used_events.append(next_event.id)
        
    return chapter, stage, used_events, next_event, transition_text

def process_turn(selected_chars, current_event_id, player_choice, custom_prompt, temperature, chat_history, current_turn):
    if not current_event_id:
        return "请先点击【抽取下一节点】！", gr.update(), chat_history, current_turn, "出错了", gr.update(), "无"
        
    evt = EVENT_DATABASE.get(current_event_id)
    max_turns = 3 if not evt.is_boss else 4 # Boss战回合数更长
    
    # 1. 组装室友设定
    active_profiles = [p for p in CANDIDATE_POOL.values() if p.Name in selected_chars]
    char_descriptions = "\n".join([f"- {p.Name} | 性格: {p.Core_Archetype}" for p in active_profiles])

    # 2. 对话历史
    history_text = "\n".join([f"玩家：{u}\n室友：{a}" for u, a in chat_history])

    # 3. 推进状态与节奏指令
    current_turn += 1
    force_end = (current_turn >= max_turns)
    action_text = player_choice if player_choice else "（事件刚发生，我正在观察局势）"

    if current_turn == 1: pacing_instruction = "【当前节奏：开端】抛出矛盾，室友初步表态。"
    elif force_end: pacing_instruction = "【当前节奏：结局】必须明确收尾，有人破防或妥协，将 is_end 置为 true。"
    else: pacing_instruction = "【当前节奏：激化】冲突升级，逼迫玩家做出艰难决定。"

    # 🌟 4. 恢复记忆系统 (RAG 检索)
    try:
        relevant_memories = mm.vector_store.search(action_text, n_results=2)
        memory_str = "\n".join([f"- {m['content']}" for m in relevant_memories]) if relevant_memories else "暂无相关回忆"
    except:
        memory_str = "记忆检索跳过（或无数据）"

    # 5. 组装发给 AI 的指令
    reference_options = "\n".join([f"{k}: {v}" for k, v in evt.options.items()])
    event_context = f"""
【当前事件】: {evt.name} {'(👑BOSS战)' if evt.is_boss else ''}
{evt.description}
【回合】: 第 {current_turn} / {max_turns} 回合
{pacing_instruction}

【过去对话历史】:\n{history_text if history_text else "无"}

【我的长期记忆/过去恩怨】:\n{memory_str}

【玩家(陆陈安然)本回合行动】: \n{action_text}
(参考原设：{reference_options})
"""

    final_system_prompt = f"{custom_prompt}\n\n【在场室友设定】\n{char_descriptions}"

    try:
        res_text = llm_service.generate_response(system_prompt=final_system_prompt, user_input=event_context, temperature=temperature)
        
        if "```json" in res_text: res_text = res_text.replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(res_text)
        
        ai_combined_text = " ".join([f"[{t['speaker']}] {t['content']}" for t in parsed_json.get("dialogue_sequence", [])])
        
        # 保存进短期和长期记忆
        chat_history.append((action_text, ai_combined_text))
        mm.save_interaction(user_input=action_text, ai_response=ai_combined_text, user_name="陆陈安然")
        
        next_options = parsed_json.get("next_options", [])
        is_end = parsed_json.get("is_end", force_end) or force_end

        if is_end:
            return json.dumps(parsed_json, indent=4, ensure_ascii=False), gr.update(visible=False), chat_history, current_turn, f"✅ 事件【{evt.name}】已结束！请抽取下一节点。", gr.update(interactive=False), memory_str
        else:
            return json.dumps(parsed_json, indent=4, ensure_ascii=False), gr.update(choices=next_options, value=None, visible=True), chat_history, current_turn, f"🔄 第 {current_turn} 回合 (等待选择)", gr.update(interactive=True), memory_str
            
    except Exception as e:
        return f"生成失败：{e}", gr.update(), chat_history, current_turn - 1, "❌ 发生错误", gr.update(), memory_str

# --- 构建 Gradio 网页 UI ---
with gr.Blocks(title="大学档案", theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 大学档案")
    
    # 状态机变量
    state_chapter = gr.State(1)
    state_stage = gr.State(0)
    state_used_events = gr.State([])
    state_current_event_id = gr.State("")
    state_current_turn = gr.State(0)
    
    with gr.Row():
        with gr.Column(scale=1):
            char_checkboxes = gr.CheckboxGroup(choices=char_choices, label="在场室友", value=["陈雨婷", "唐梦琪", "李一诺"])
            
            # 进度显示区
            progress_md = gr.Markdown("### 当前进度：第一章 大一未开始 | 节点 0/4")
            draw_node_btn = gr.Button("抽取下一节点", variant="primary")
            
            gr.Markdown("---")
            event_desc_md = gr.Markdown("> 点击上方抽取节点开始游戏...")
            status_text = gr.Markdown("### 当前状态：等待开始")
            
            chatbot = gr.Chatbot(label="事件推演记录 (短期记忆)", height=250)
            dynamic_options = gr.Radio(choices=[], label="意图轮盘 (请选择)", visible=False)
            next_turn_btn = gr.Button("确认选择并推演", interactive=False)
            
            with gr.Accordion("参数与提示词", open=False):
                temp_slider = gr.Slider(minimum=0.1, maximum=1.5, value=0.7, label="温度")
                prompt_input = gr.Textbox(lines=5, value=DEFAULT_PROMPT)
            
        with gr.Column(scale=1):
            memory_monitor = gr.Textbox(label="唤醒的长期记忆 (RAG 监视)", interactive=False)
            output_json = gr.Code(language="json", label="大模型返回 JSON")

    # 1. 抽取新节点逻辑
    def on_draw_node(chap, stg, used):
        new_chap, new_stg, new_used, nxt_evt, trans_txt = advance_node(chap, stg, used)
        if not nxt_evt:
            return new_chap, new_stg, new_used, "", f"### {trans_txt}", "> 游戏结束或此章节无更多事件", gr.update(visible=False), gr.update(interactive=False), [], 0, "通关", ""
            
        prog_str = f"### 当前进度：第 {new_chap} 章 | 节点 {new_stg}/4 {'(BOSS关)' if new_stg==4 else ''}"
        desc_str = f"**【{nxt_evt.name}】**\n\n{trans_txt}\n\n*背景：{nxt_evt.description}*"
        return new_chap, new_stg, new_used, nxt_evt.id, prog_str, desc_str, gr.update(visible=False), gr.update(interactive=True), [], 0, "等待生成开局对话...", "记忆将在行动后唤醒"

    draw_node_btn.click(
        fn=on_draw_node,
        inputs=[state_chapter, state_stage, state_used_events],
        outputs=[state_chapter, state_stage, state_used_events, state_current_event_id, progress_md, event_desc_md, dynamic_options, next_turn_btn, chatbot, state_current_turn, status_text, memory_monitor]
    ).then(
        # 抽完卡后，自动触发第一回合（开局介绍）
        fn=lambda chars, eid, prm, tmp, hist, turn: process_turn(chars, eid, None, prm, tmp, hist, turn),
        inputs=[char_checkboxes, state_current_event_id, prompt_input, temp_slider, chatbot, state_current_turn],
        outputs=[output_json, dynamic_options, chatbot, state_current_turn, status_text, next_turn_btn, memory_monitor]
    )

    # 2. 玩家推进回合
    next_turn_btn.click(
        fn=lambda chars, eid, opt, prm, tmp, hist, turn: process_turn(chars, eid, opt, prm, tmp, hist, turn),
        inputs=[char_checkboxes, state_current_event_id, dynamic_options, prompt_input, temp_slider, chatbot, state_current_turn],
        outputs=[output_json, dynamic_options, chatbot, state_current_turn, status_text, next_turn_btn, memory_monitor]
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
import gradio as gr
import pandas as pd
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 动态反射自动抓取 presets 里的所有角色
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

# 动态组装全角色池
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

DEFAULT_PROMPT = """你是一个多角色大学生存游戏的 AI 跑团 DM。

[核心职责]
1. 你的首要任务是维持角色人设（防OOC）！请严格遵守下方的【全角色图鉴与设定】。
2. 注意区分【同寝室友】和【非室友】。
3. 【关键指令：台词生成原则】我会给你提供一些【动态检索到的角色语录】。
   - 必须深刻体会这些语录中的“情绪内核”、“阴阳怪气的技巧”和“断句习惯”。
   - 绝对、绝对不可原样照抄这些语录！必须结合【当前事件】和【玩家最新行动】生成全新的对白！
   - 角色说话必须极其口语化，包含人类的瑕疵与情绪，不能太长，大约10字到15字。
   - 不要描述角色动作和神态，仅生成对话文本。
4. 严格输出以下 JSON 格式。

{
    "narrator_transition": "旁白过渡文本(主角视角的心理描写，仅过渡时填写)",
    "dialogue_sequence": [{"speaker": "角色", "content": "内容", "mood": "情绪"}],
    "next_options": ["选项A", "选项B", "选项C"],
    "stat_changes": {"san_delta": -5, "money_delta": 0, "is_argument": true},
    "is_end": false
}"""

def process_action(selected_chars, current_evt_id, player_choice, is_transition, prm, tmp, hist, turn, san, money, gpa, arg_count, chapter):
    
    # 1. 组装全局世界观
    world_info = ""
    if hasattr(presets_module, "WORLD_SETTING"):
        ws = presets_module.WORLD_SETTING
        world_info = f"【全局世界观】\n地点：{ws.university_name} {ws.dorm_number} ({ws.major})\n生存法则：{ws.background_rule}\n\n"

    # 2. 组装极度丰富的【全角色图鉴】(区分室友与非室友)
    encyclopedia = "【全角色图鉴与设定】\n"
    for name, p in CANDIDATE_POOL.items():
        role_status = "🏠【同寝室友】(常驻)" if name in selected_chars else "🚶‍♀️【非室友/隔壁寝室】(仅客串)"
        tags = ",".join(p.Tags) if p.Tags else "无"
        tone = p.Speech_Pattern.Tone if p.Speech_Pattern else "普通"
        catchphrases = ",".join(p.Speech_Pattern.Catchphrases) if p.Speech_Pattern and p.Speech_Pattern.Catchphrases else "无"
        
        encyclopedia += f"🔹 {name} {role_status}\n"
        encyclopedia += f"  - 人设标签: {p.Core_Archetype} | {tags}\n"
        encyclopedia += f"  - 说话风格: 语气[{tone}]，口头禅[{catchphrases}]\n"
        encyclopedia += f"  - 行为习惯: {p.Habits or '无'}\n"
        encyclopedia += f"  - 冲突风格: 压力下会[{p.Stress_Reaction}], 冲突时倾向[{p.Conflict_Style}]\n"
        encyclopedia += f"  - 隐藏秘密(AI独家掌握): {p.Background_Secret or '无'}\n\n"

    mock_player_stats = {"hygiene": 50, "affinity_xueba": 5} 
    settlement_msg = ""
    
    # === 状态机逻辑 ===
    if is_transition or current_evt_id == "":
        if turn == 0:  
            mm.clear_game_history()
            
        next_evt = director.get_next_event(mock_player_stats, selected_chars)
        
        # 补上防止游戏结束报错的拦截
        if not next_evt:
            return gr.update(), "卡池已空或游戏通关！", gr.update(visible=False), hist, turn, "🏁 游戏结束", False, current_evt_id, san, money, gpa, arg_count, chapter, f"**SAN**: {san}"
        
        # 这里是漏掉的那行 if 判断（跨章结算）！
        if next_evt.chapter > chapter:
            money -= 800  
            gpa_penalty = 0.5 if money < 500 else 0.0
            gpa = max(0.0, min(4.0, 3.0 + (mock_player_stats["affinity_xueba"] * 0.1) - (arg_count * 0.05) - gpa_penalty))
            settlement_msg = f"⏳ **【大{chapter}学年结算】**\n生活费扣除 800。\n本年度吵架 {arg_count} 次，期末 GPA 结算为：{gpa:.2f}\n\n"
            chapter = next_evt.chapter
            arg_count = 0 

        turn = 1
        action_text = "（开启了新的阶段...）"
        event_context = f"【过渡指令】\n旧事件结束，进入第 {chapter} 章。\n【触发新事件】:{next_evt.name}\n【场景描述】:{next_evt.description}"
    else:
        # ... 后面的保持不变 ...
        next_evt = EVENT_DATABASE[current_evt_id]
        turn += 1
        action_text = player_choice
        force_end = (turn >= 3)
        pacing = "【当前节奏：结局】请明确收尾，将 is_end 置为 true。" if force_end else "【当前节奏：激化】冲突升级。"
        event_context = f"【当前事件】: {next_evt.name}\n【回合】: {turn}/3\n{pacing}\n【玩家行动】: {action_text}"

    # 3. RAG 记忆与动态语料检索
    memory_str = "暂无相关回忆"
    lore_str = "暂无专属语录"
    
    try:
        # 用 当前事件的名称 + 玩家动作 去搜索，最容易搜出匹配的语录和记忆
        search_query = f"{next_evt.name} {next_evt.description} {action_text}"
        relevant_docs = mm.vector_store.search(search_query, n_results=5)
        
        memories = []
        lores = []
        for doc in relevant_docs:
            if "专属语录" in doc.get('content', ''):
                lores.append(doc['content'])
            else:
                memories.append(doc['content'])
                
        if memories: memory_str = "\n".join([f"- {m}" for m in memories[:3]])
        if lores: lore_str = "\n".join([f"- {l}" for l in lores[:3]])
    except Exception as e:
        print(f"检索出错: {e}")

    # 将记忆和语录拼接到上下文中
    event_context += f"\n\n【我的长期记忆/过去恩怨】:\n{memory_str}\n\n【动态检索到的角色语录 (仅供风格模仿，严禁照抄！)】:\n{lore_str}"

    # 合并发给大模型的终极系统指令
    full_system_prompt = f"{prm}\n\n{world_info}{encyclopedia}"
    status_hint = f"\n[玩家当前状态] SAN:{san}, 金钱:{money}。请根据玩家行动评估数值增减。"

    try:
        # 4. CG 播放器增强：秒播文本
        if getattr(next_evt, 'is_cg', False):
            if is_transition or current_evt_id == "":
                parsed = {
                    "narrator_transition": f"【剧情演出】 {next_evt.name}\n{next_evt.description}",
                    "dialogue_sequence": getattr(next_evt, 'fixed_dialogue', []),
                    "next_options": ["阅毕，进入下一阶段"],
                    "stat_changes": {"san_delta": 0, "money_delta": 0, "is_argument": False},
                    "is_end": False
                }
            else:
                choice_key = player_choice.split(":")[0].strip() if player_choice else ""
                outcome = next_evt.outcomes.get(choice_key, "")
                parsed = {
                    "narrator_transition": f"【演出结束】 {outcome}",
                    "dialogue_sequence": [],
                    "next_options": [],
                    "stat_changes": {"san_delta": 0, "money_delta": 0, "is_argument": False},
                    "is_end": True
                }
            res_text = json.dumps(parsed, ensure_ascii=False)
            
        else:
            # 正常事件的 LLM 呼叫
            res_text = llm_service.generate_response(system_prompt=full_system_prompt, user_input=event_context + status_hint, temperature=tmp)
            if "```json" in res_text: res_text = res_text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(res_text)
            
        # 5. 应用状态变动
        stats_data = parsed.get("stat_changes", {})
        san = max(0, min(100, san + stats_data.get("san_delta", 0)))
        money += stats_data.get("money_delta", 0)
        if stats_data.get("is_argument", False): arg_count += 1
            
        # 6. 优化聊天框排版，使得阅读像看剧本一样
        display_text = settlement_msg
        if parsed.get("narrator_transition"):
            display_text += f"📜 【旁白】 {parsed['narrator_transition']}\n\n"
        
        # 将对话用双换行隔开，清晰明了
        dialogue_lines = [f"[{t.get('speaker', '神秘人')}] {t.get('content', '')}" for t in parsed.get("dialogue_sequence", [])]
        display_text += "\n\n".join(dialogue_lines)
        
        hist.append((action_text, display_text))
        is_end = parsed.get("is_end", False)
        
        # 保存短期和长期记忆
        if not getattr(next_evt, 'is_cg', False) and action_text and "（开启了新的阶段" not in action_text:
            mm.save_interaction(user_input=action_text, ai_response=" ".join(dialogue_lines), user_name="陆陈安然")
        
        stats_md_text = f"**SAN值**: {san}/100 | **生活费**: ¥{money} | **当前GPA**: {gpa:.2f} | **本章吵架**: {arg_count}次"
        btn_text = "⏳ 事件已落幕，点击由 AI 引导过渡至下一剧情..." if is_end else "➡️ 确认选择并推演本回合"
        options_ui = gr.update(choices=[], visible=False) if is_end else gr.update(choices=parsed.get("next_options", []), visible=True)
        
        return res_text, options_ui, hist, turn, f"第 {chapter} 章 - {next_evt.name} (第 {turn} 回合)", gr.update(value=btn_text), is_end, next_evt.id, san, money, gpa, arg_count, chapter, stats_md_text
        
    except Exception as e:
        return f"出错: {e}", gr.update(), hist, turn, "错误", gr.update(), False, current_evt_id, san, money, gpa, arg_count, chapter, f"**SAN**: {san}"

# --- 辅助函数：读取所有 ChromaDB 记忆 ---
def fetch_all_memories():
    try:
        # 获取底层 collection 的所有数据
        data = mm.vector_store.collection.get()
        if not data or not data['ids']:
            return pd.DataFrame(columns=["ID", "内容", "类型", "重要度", "时间戳"])
            
        rows = []
        for i in range(len(data['ids'])):
            meta = data['metadatas'][i] if data['metadatas'] else {}
            rows.append({
                "ID": data['ids'][i],
                "内容": data['documents'][i],
                "类型": meta.get("type", "unknown"),
                "重要度": meta.get("importance", 5),
                "时间戳": meta.get("timestamp", "")
            })
        return pd.DataFrame(rows)
    except Exception as e:
        return pd.DataFrame(columns=["ID", f"读取出错: {e}", "类型", "重要度", "时间戳"])

# --- 构建 Gradio 网页 UI (带后台管理系统) ---
with gr.Blocks(title="大学档案 - 沉浸式与后台管理", theme=gr.themes.Soft()) as demo:
    
    # 🌟 使用 Tabs 将“游戏前台”和“开发者后台”分开
    with gr.Tabs():
        
        # ==========================================
        # Tab 1: 游戏主控台 (前台)
        # ==========================================
        with gr.TabItem("游戏主控台"):
            state_current_event_id = gr.State("")
            state_turn = gr.State(0)
            state_is_transition = gr.State(True) 
            state_san, state_money, state_gpa, state_args, state_chapter = gr.State(80), gr.State(1500), gr.State(3.0), gr.State(0), gr.State(1)
            
            with gr.Row():
                with gr.Column(scale=1):
                    char_checkboxes = gr.CheckboxGroup(choices=list(CANDIDATE_POOL.keys()), label="在场室友", value=list(CANDIDATE_POOL.keys())[:3])
                    stats_panel = gr.Markdown("### 玩家当前状态\n**SAN值**: 80/100 | **生活费**: ¥1500 | **当前GPA**: 3.00")
                    status_text = gr.Markdown("### 当前进度：等待游戏开始")
                    
                    chatbot = gr.Chatbot(label="游戏画面 (旁白与交互)", height=450)
                    dynamic_options = gr.Radio(choices=[], label="意图轮盘 (请选择)", visible=False)
                    action_btn = gr.Button("开启大学生活", variant="primary")
                    
                with gr.Column(scale=1):
                    output_json = gr.Code(language="json", label="底层 JSON 数据")
                    
                    with gr.Accordion("参数调整", open=False):
                        temp_slider = gr.Slider(minimum=0.1, maximum=1.5, value=0.7, label="温度")
                        prompt_input = gr.Textbox(lines=5, value=DEFAULT_PROMPT)

            action_btn.click(
                fn=process_action,
                inputs=[char_checkboxes, state_current_event_id, dynamic_options, state_is_transition, prompt_input, temp_slider, chatbot, state_turn, state_san, state_money, state_gpa, state_args, state_chapter],
                outputs=[output_json, dynamic_options, chatbot, state_turn, status_text, action_btn, state_is_transition, state_current_event_id, state_san, state_money, state_gpa, state_args, state_chapter, stats_panel]
            )

        # ==========================================
        # Tab 2: RAG 记忆流与档案库 (后台)
        # ==========================================
        with gr.TabItem("记忆与语料库 (RAG Backstage)"):
            gr.Markdown("### ChromaDB 向量数据库监视器\n这里展示了原项目中的 Memory Stream，你可以查看 AI 目前学到的所有**专属语料**和**历史互动记忆**。")
            
            with gr.Row():
                refresh_btn = gr.Button("刷新数据库列表", variant="secondary")
                clear_mem_btn = gr.Button("清空所有互动记忆 (危险)", variant="stop")

            def clear_and_refresh():
                mm.clear_game_history()
                return fetch_all_memories()
            
            memory_dataframe = gr.Dataframe(
                headers=["ID", "内容", "类型", "重要度", "时间戳"],
                datatype=["str", "str", "str", "number", "str"],
                interactive=False,
                wrap=True
            )
            
            clear_mem_btn.click(fn=clear_and_refresh, outputs=memory_dataframe)
            refresh_btn.click(fn=fetch_all_memories, outputs=memory_dataframe)
            
            # 页面加载时自动刷新一次
            demo.load(fn=fetch_all_memories, outputs=memory_dataframe)

        # ==========================================
        # Tab 3: 玩家动态存档 (Profile)
        # ==========================================
        with gr.TabItem("玩家本地存档 (profile.json)"):
            gr.Markdown("### `profile.json` 实时数据\n此页面对应原项目中的 Character Profile，用于永久保存玩家通关状态、剩余资金和心理健康。")
            
            def load_profile_json():
                try:
                    with open(mm.json_store.file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except:
                    return "{}"
                    
            profile_code = gr.Code(language="json", label="当前 profile.json 的内容")
            refresh_profile_btn = gr.Button("刷新存档文件")
            refresh_profile_btn.click(fn=load_profile_json, outputs=profile_code)
            demo.load(fn=load_profile_json, outputs=profile_code)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
    gr.Markdown("## 宿舍生存游戏 - 沉浸式演出模式")
    
    state_current_event_id = gr.State("")
    state_turn = gr.State(0)
    state_is_transition = gr.State(True) 
    state_san, state_money, state_gpa, state_args, state_chapter = gr.State(80), gr.State(1500), gr.State(3.0), gr.State(0), gr.State(1)
    
    with gr.Row():
        with gr.Column(scale=1):
            char_checkboxes = gr.CheckboxGroup(choices=list(CANDIDATE_POOL.keys()), label="在场室友 (未选中的角色将被标记为非室友)", value=list(CANDIDATE_POOL.keys())[:3])
            
            gr.Markdown("### 玩家当前状态")
            stats_panel = gr.Markdown("**SAN值**: 80/100 | **生活费**: ¥1500 | **当前GPA**: 3.00 | **本章吵架**: 0次")
            status_text = gr.Markdown("### 当前进度：等待游戏开始")
            
            chatbot = gr.Chatbot(label="游戏画面 (旁白与交互)", height=450)
            dynamic_options = gr.Radio(choices=[], label="意图轮盘 (请选择)", visible=False)
            action_btn = gr.Button("开启大学生活", variant="primary")
            
            with gr.Accordion("参数", open=False):
                temp_slider = gr.Slider(minimum=0.1, maximum=1.5, value=0.7, label="温度")
                prompt_input = gr.Textbox(lines=5, value=DEFAULT_PROMPT)
            
        with gr.Column(scale=1):
            output_json = gr.Code(language="json", label="底层 JSON 数据 (发送给大模型的完整百科都在这里)")

    action_btn.click(
        fn=process_action,
        inputs=[char_checkboxes, state_current_event_id, dynamic_options, state_is_transition, prompt_input, temp_slider, chatbot, state_turn, state_san, state_money, state_gpa, state_args, state_chapter],
        outputs=[output_json, dynamic_options, chatbot, state_turn, status_text, action_btn, state_is_transition, state_current_event_id, state_san, state_money, state_gpa, state_args, state_chapter, stats_panel]
    )
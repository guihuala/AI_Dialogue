import gradio as gr
import pandas as pd
import json
import sys
import os
import re

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

# --- 系统指令 ---
DEFAULT_PROMPT = """你是一个多角色大学生存游戏的 AI 跑团 DM。

[核心职责]
1. 你的首要任务是维持角色人设（防OOC）！请严格遵守下方的【全角色图鉴与设定】。
2. 注意区分【同寝室友】和【非室友】。
3. 【关键指令：台词生成原则】我会给你提供一些【动态检索到的角色语录】。
   - 必须深刻体会这些语录中的“情绪内核”、“阴阳怪气的技巧”和“断句习惯”。
   - 绝对、绝对不可原样照抄这些语录！必须结合【当前事件】和【玩家最新行动】生成全新的对白！
   - 角色说话必须极其口语化，包含人类的瑕疵与情绪，不能太长，大约10字到15字。
   - 不要描述角色动作和神态，仅生成对话文本。
4. 根据玩家的话语，动态评估各个室友对玩家的好感度变动（affinity_changes）。
5. 必须严格输出合法的 JSON 格式。绝对不要包含任何注释(//)，所有的键名(key)必须强制使用双引号("")，严禁使用单引号或省略引号！不要在 JSON 前后输出任何解释性文字。

{
    "narrator_transition": "旁白过渡文本(主角视角的心理描写，仅过渡时填写)",
    "dialogue_sequence": [{"speaker": "角色", "content": "内容", "mood": "情绪"}],
    "next_options": ["选项A", "选项B", "选项C"],
    "stat_changes": {
        "san_delta": -5, 
        "money_delta": 0, 
        "is_argument": true,
        "affinity_changes": {"陈雨婷": -2, "唐梦琪": 5}
    },
    "is_end": false
}"""

def generate_char_info_md(selected_chars, affinity):
    md = "### 室友档案与关系监控\n---\n"
    for name, p in CANDIDATE_POOL.items():
        role_status = "[在场]" if name in selected_chars else "[缺席]"
        aff = affinity.get(name, 50)
        
        if aff >= 80: rel = "[挚友]"
        elif aff >= 50: rel = "[普通]"
        elif aff >= 30: rel = "[紧张]"
        else: rel = "[死敌]"

        md += f"**{name}** {role_status} | {rel} : {aff}/100\n"
        md += f"- **核心设定**: {p.Core_Archetype}\n"
        md += f"- **冲突倾向**: 压力下[{p.Stress_Reaction}], 冲突时[{p.Conflict_Style}]\n"
        md += f"- **隐藏秘密**: {p.Background_Secret or '无'}\n\n"
    return md

# --- 核心逻辑 ---
def process_action(selected_chars, current_evt_id, player_choice, is_transition, prm, 
                   tmp, top_p, max_tokens, pres_pen, freq_pen, 
                   hist, turn, san, money, gpa, arg_count, chapter, affinity):   
    
    # 0. 拦截器：防止玩家没选选项就点确认
    if not is_transition and current_evt_id != "" and not player_choice:
        yield (
            gr.update(), gr.update(), 
            hist + [("（未作选择）", "⚠️ 导演提示：请先在【玩家行动选项】中选择一项行为，再点击确认！")], 
            turn, gr.update(), gr.update(), is_transition, current_evt_id, 
            san, money, gpa, arg_count, chapter, gr.update(), gr.update(), affinity
        )
        return

    # 1. 极速UI响应：立刻冻结按钮，把玩家动作上屏，并显示加载中
    action_text = player_choice if (not is_transition and current_evt_id != "") else "（时间推移...）"
    
    yield (
        gr.update(), # output_json
        gr.update(visible=False), # 瞬间隐藏选项
        hist + [(action_text, "⏳ *AI 导演正在推演局势，请稍候...*")], # 聊天框给出 Loading 提示
        turn, 
        gr.update(), 
        gr.update(value="⏳ 推演中...", interactive=False), # 按钮变灰
        is_transition, current_evt_id, san, money, gpa, arg_count, chapter, 
        gr.update(), gr.update(), affinity
    )

    world_info = ""
    if hasattr(presets_module, "WORLD_SETTING"):
        ws = presets_module.WORLD_SETTING
        world_info = f"【全局世界观】\n地点：{ws.university_name} {ws.dorm_number} ({ws.major})\n生存法则：{ws.background_rule}\n\n"

    encyclopedia = "【全角色图鉴与设定】\n"
    for name, p in CANDIDATE_POOL.items():
        role_status = "[同寝室友](常驻)" if name in selected_chars else "[非室友/隔壁寝室](仅客串)"
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
    
    if is_transition or current_evt_id == "":
        if turn == 0:  
            mm.clear_game_history()
            
        next_evt = director.get_next_event(mock_player_stats, selected_chars)
        
        if not next_evt:
            yield (
                gr.update(), gr.update(visible=False), hist + [(action_text, "🏁 游戏通关或卡池已空！")], 
                turn, "游戏结束", gr.update(value="游戏结束", interactive=False), 
                False, current_evt_id, san, money, gpa, arg_count, chapter, 
                f"**SAN**: {san}", generate_char_info_md(selected_chars, affinity), affinity
            )
            return
        
        if next_evt.chapter > chapter:
            money -= 800  
            gpa_penalty = 0.5 if money < 500 else 0.0
            gpa = max(0.0, min(4.0, 3.0 + (mock_player_stats["affinity_xueba"] * 0.1) - (arg_count * 0.05) - gpa_penalty))
            settlement_msg = f"**[大{chapter}学年结算]**\n生活费扣除 800。\n本年度吵架 {arg_count} 次，期末 GPA 结算为：{gpa:.2f}\n\n"
            chapter = next_evt.chapter
            arg_count = 0 

        turn = 1
        event_context = f"【过渡指令】\n旧事件结束，进入第 {chapter} 章。\n【触发新事件】:{next_evt.name}\n【场景描述】:{next_evt.description}"
    else:
        next_evt = EVENT_DATABASE[current_evt_id]
        turn += 1
        force_end = (turn >= 3)
        pacing = "【当前节奏：结局】请明确收尾，将 is_end 置为 true。" if force_end else "【当前节奏：激化】冲突升级。"
        event_context = f"【当前事件】: {next_evt.name}\n【回合】: {turn}/3\n{pacing}\n【玩家行动】: {action_text}"

    memory_str = "暂无相关回忆"
    lore_str = "暂无专属语录"
    
    try:
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

    event_context += f"\n\n【我的长期记忆/过去恩怨】:\n{memory_str}\n\n【动态检索到的角色语录 (仅供风格模仿，严禁照抄！)】:\n{lore_str}"
    full_system_prompt = f"{prm}\n\n{world_info}{encyclopedia}"
    status_hint = f"\n[玩家当前状态] SAN:{san}, 金钱:{money}。请根据玩家行动评估数值增减。"

    try:
        if getattr(next_evt, 'is_cg', False):
            if is_transition or current_evt_id == "":
                parsed = {
                    "narrator_transition": f"[剧情演出] {next_evt.name}\n{next_evt.description}",
                    "dialogue_sequence": getattr(next_evt, 'fixed_dialogue', []),
                    "next_options": ["阅毕，继续推进"],
                    "stat_changes": {"san_delta": 0, "money_delta": 0, "is_argument": False, "affinity_changes": {}},
                    "is_end": False
                }
            else:
                choice_key = player_choice.split(":")[0].strip() if player_choice else ""
                outcome = next_evt.outcomes.get(choice_key, "")
                parsed = {
                    "narrator_transition": f"[演出结束] {outcome}",
                    "dialogue_sequence": [],
                    "next_options": [],
                    "stat_changes": {"san_delta": 0, "money_delta": 0, "is_argument": False, "affinity_changes": {}},
                    "is_end": True
                }
            res_text = json.dumps(parsed, ensure_ascii=False)
            
        else:
            res_text = llm_service.generate_response(
                system_prompt=full_system_prompt, 
                user_input=event_context + status_hint, 
                temperature=tmp,
                top_p=top_p,
                max_tokens=max_tokens,
                presence_penalty=pres_pen,
                frequency_penalty=freq_pen
            )
            

            match = re.search(r'\{.*\}', res_text, re.DOTALL)
            clean_json = match.group(0) if match else res_text
            
            # 修复【键名】的引号问题
            clean_json = re.sub(r'([{,]\s*)["“”‘’]*([a-zA-Z0-9_\u4e00-\u9fa5]+)["“”‘’]*\s*:', r'\1"\2":', clean_json)
            
            # 修复【纯文本值】的乱用引号 (例如 "speaker": “唐梦琪” -> "speaker": "唐梦琪")
            clean_json = re.sub(r':\s*["“”‘’]([a-zA-Z0-9_\u4e00-\u9fa5]+)["“”‘’]\s*([,}])', r': "\1"\2', clean_json)
            
            # 修复 True/False 首字母大写错误
            clean_json = clean_json.replace(": True", ": true").replace(": False", ": false")
            
            # 修复 JSON 尾部多余的逗号 (例如 {"a": 1, } -> {"a": 1 })
            clean_json = re.sub(r',\s*([}\]])', r'\1', clean_json)
            
            try:
                parsed = json.loads(clean_json)
            except Exception as parse_err:
                raise Exception(f"JSON格式错误: {parse_err}\n\n大模型原始返回内容:\n{res_text}")
            
        # 应用状态与亲密度变动
        stats_data = parsed.get("stat_changes", {})
        san = max(0, min(100, san + stats_data.get("san_delta", 0)))
        money += stats_data.get("money_delta", 0)
        if stats_data.get("is_argument", False): arg_count += 1
            
        aff_changes = stats_data.get("affinity_changes", {})
        for char_name, change_val in aff_changes.items():
            if char_name in affinity:
                affinity[char_name] = max(0, min(100, affinity[char_name] + change_val))
            
        updated_char_md = generate_char_info_md(selected_chars, affinity)
        
        display_text = settlement_msg
        if parsed.get("narrator_transition"):
            display_text += f"{parsed['narrator_transition']}\n\n"
        
        dialogue_lines = [f"[{t.get('speaker', '神秘人')}] {t.get('content', '')}" for t in parsed.get("dialogue_sequence", [])]
        display_text += "\n\n".join(dialogue_lines)
        
        # 把最终的真内容写入聊天记录
        hist.append((action_text, display_text))
        is_end = parsed.get("is_end", False)
        
        if not getattr(next_evt, 'is_cg', False) and action_text and "（时间推移..." not in action_text:
            mm.save_interaction(user_input=action_text, ai_response=" ".join(dialogue_lines), user_name="陆陈安然")
        
        stats_md_text = f"**SAN值**: {san}/100 &nbsp;|&nbsp; **生活费**: ¥{money} &nbsp;|&nbsp; **当前GPA**: {gpa:.2f} &nbsp;|&nbsp; **本章争吵**: {arg_count}次"
        btn_text = "继续下一步" if is_end else "确认行动"
        
        # 2. 彻底清空上一轮残留选项：增加 value=None 属性
        options_ui = gr.update(choices=[], visible=False, value=None) if is_end else gr.update(choices=parsed.get("next_options", []), visible=True, value=None)
        
        # 3. 第二次推流：把真实的 AI 对话覆盖上去，并恢复按钮可用状态
        yield (
            res_text, options_ui, hist, turn, 
            f"第 {chapter} 章 - {next_evt.name} (回合 {turn})", 
            gr.update(value=btn_text, interactive=True), 
            is_end, next_evt.id, san, money, gpa, arg_count, chapter, 
            stats_md_text, updated_char_md, affinity
        )
        
    except Exception as e:
        yield (
            f"系统错误: {e}", gr.update(visible=True), hist + [(action_text, f"❌ 系统错误: {e}")], 
            turn, "错误", gr.update(value="重试", interactive=True), 
            is_transition, current_evt_id, san, money, gpa, arg_count, chapter, 
            f"**SAN**: {san}", generate_char_info_md(selected_chars, affinity), affinity
        )
    
# --- 辅助函数：读取所有 ChromaDB 记忆 ---
def fetch_all_memories():
    try:
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

# --- 构建 Gradio 网页 UI ---
custom_css = """
.status-card { background-color: #fafafa; padding: 15px; border-radius: 8px; border: 1px solid #eaeaea; margin-bottom: 10px; }
"""

with gr.Blocks(title="大学档案 | 沉浸式模拟系统", theme=gr.themes.Soft(), css=custom_css) as demo:
    
    with gr.Tabs():
        
        # ==========================================
        # Tab 1: 游戏主控台 (前台)
        # ==========================================
        with gr.TabItem("模拟推演控制台"):
            state_current_event_id = gr.State("")
            state_turn = gr.State(0)
            state_is_transition = gr.State(True) 
            state_san, state_money, state_gpa, state_args, state_chapter = gr.State(80), gr.State(1500), gr.State(3.0), gr.State(0), gr.State(1)
            state_affinity = gr.State({name: 50 for name in CANDIDATE_POOL.keys()})
            
            with gr.Row():
                # 🌟 左半区：主游戏视窗 (占比极大，提升沉浸感)
                with gr.Column(scale=7):
                    status_text = gr.Markdown("### 当前进度：系统待机")
                    chatbot = gr.Chatbot(label="事件推演记录", height=550)
                    dynamic_options = gr.Radio(choices=[], label="玩家行动选项", visible=False)
                    action_btn = gr.Button("启动模拟流", variant="primary", size="lg")
                    
                # 🌟 右半区：控制与监视侧边栏 (占比小，排版紧凑)
                with gr.Column(scale=3):
                    gr.Markdown("### 控制侧边栏")
                    
                    with gr.Group():
                        gr.Markdown("#### 玩家当前状态")
                        stats_panel = gr.Markdown("**SAN值**: 80/100 &nbsp;|&nbsp; **生活费**: ¥1500 &nbsp;|&nbsp; **当前GPA**: 3.00 &nbsp;|&nbsp; **本章争吵**: 0次")
                    
                    with gr.Group():
                        char_checkboxes = gr.CheckboxGroup(choices=list(CANDIDATE_POOL.keys()), label="在场角色配置 (剔除视作缺席)", value=list(CANDIDATE_POOL.keys())[:3])
                    
                    with gr.Accordion("角色档案监控", open=True):
                        char_info_panel = gr.Markdown(generate_char_info_md(list(CANDIDATE_POOL.keys())[:3], {name: 50 for name in CANDIDATE_POOL.keys()}))
                    
                    with gr.Accordion("生成参数与底层通讯", open=False):
                        output_json = gr.Code(language="json", label="模型交互 JSON")
                        temp_slider = gr.Slider(minimum=0.1, maximum=2.0, value=0.7, step=0.1, label="Temperature")
                        top_p_slider = gr.Slider(minimum=0.1, maximum=1.0, value=1.0, step=0.05, label="Top P")
                        freq_pen_slider = gr.Slider(minimum=-2.0, maximum=2.0, value=0.5, step=0.1, label="Frequency Penalty")
                        pres_pen_slider = gr.Slider(minimum=-2.0, maximum=2.0, value=0.3, step=0.1, label="Presence Penalty")
                        max_tokens_slider = gr.Slider(minimum=100, maximum=2000, value=800, step=50, label="Max Tokens")
                        prompt_input = gr.Textbox(lines=3, value=DEFAULT_PROMPT, label="System Prompt")

            action_btn.click(
                fn=process_action,
                inputs=[char_checkboxes, state_current_event_id, dynamic_options, state_is_transition, prompt_input, 
                        temp_slider, top_p_slider, max_tokens_slider, pres_pen_slider, freq_pen_slider, 
                        chatbot, state_turn, state_san, state_money, state_gpa, state_args, state_chapter, state_affinity],
                outputs=[output_json, dynamic_options, chatbot, state_turn, status_text, action_btn, state_is_transition, state_current_event_id, state_san, state_money, state_gpa, state_args, state_chapter, stats_panel, char_info_panel, state_affinity]
            )

        # ==========================================
        # Tab 2: RAG 记忆流与档案库 (后台)
        # ==========================================
        with gr.TabItem("数据库检查器 (RAG)"):
            gr.Markdown("### 向量数据库监视器\n此面板展示 AI 当前加载的记忆池与专属语料情况。")
            
            with gr.Row():
                refresh_btn = gr.Button("刷新数据库表单", variant="secondary")
                clear_mem_btn = gr.Button("清除历史互动记录 (危险)", variant="stop")

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
            demo.load(fn=fetch_all_memories, outputs=memory_dataframe)

        # ==========================================
        # Tab 3: 玩家动态存档 (Profile)
        # ==========================================
        with gr.TabItem("本地持久化存储 (Profile)"):
            gr.Markdown("### `profile.json` 实时数据映射\n用于调试玩家生命周期数据的写入情况。")
            
            def load_profile_json():
                try:
                    with open(mm.json_store.file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except:
                    return "{}"
                    
            profile_code = gr.Code(language="json", label="Data Dump")
            refresh_profile_btn = gr.Button("刷新文件映射")
            refresh_profile_btn.click(fn=load_profile_json, outputs=profile_code)
            demo.load(fn=load_profile_json, outputs=profile_code)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
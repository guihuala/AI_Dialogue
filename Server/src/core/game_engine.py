import os
import json
import re
import csv
import concurrent.futures
import asyncio
import time
from json_repair import repair_json 

import src.core.presets as presets_module
from src.models.schema import CharacterProfile
from src.services.llm_service import LLMService
from src.core.memory_manager import MemoryManager
from src.core.event_director import EventDirector
from src.core.event_script import load_user_events
from src.core.prompt_manager import PromptManager
from src.core.agent_system import NPCAgent
from src.core.tool_manager import ToolManager
from src.core.config import (
    DATA_ROOT, CHROMA_DB_PATH, PROFILE_PATH, 
    get_user_chroma_path, get_user_saves_dir
)

class GameEngine:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.candidate_pool = {}
        for key, obj in vars(presets_module).items():
            if isinstance(obj, CharacterProfile) and obj.Name != "陆陈安然": 
                self.candidate_pool[obj.Name] = obj
                
        self.llm = LLMService()
        
        # Use user-specific paths
        user_chroma_path = get_user_chroma_path(user_id)
        # Profile path is technically global for initial loading, 
        # but we can make it user-specific if we want they to have different save profiles.
        # For now, keep PROFILE_PATH global or map it?
        # Actually, if we want them to have different characters/stats, it should be per-user.
        user_profile_dir = os.path.dirname(get_user_saves_dir(user_id))
        user_profile_path = os.path.join(user_profile_dir, "profile.json")
        
        self.mm = MemoryManager(user_profile_path, user_chroma_path, self.llm)
        self.director = EventDirector(user_id)
        self.pm = PromptManager(user_id)
        self.tm = ToolManager()

        self.event_completion_count = 0  # 记录已完成的事件数
        self.recent_event_ids = []
        self.prefetch_futures = {}  # 影子推演缓存
        self.latest_game_state_cache = {}  # 最后状态缓存

    def reset(self):
        self.director.reset()
        self.event_completion_count = 0
        self.recent_event_ids = []

    def parse_and_repair_json(self, raw_text):
        raw_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
        raw_text = re.sub(r'```json\s*', '', raw_text)
        raw_text = re.sub(r'```\s*', '', raw_text)
        raw_text = raw_text.replace('“', '"').replace('”', '"').replace('：', ':').replace('‘', "'").replace('’', "'")
        
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            raw_json = raw_text[start_idx:end_idx+1]
        else:
            raw_json = raw_text
            
        try:
            repaired = repair_json(raw_json)
            parsed = json.loads(repaired) if isinstance(repaired, str) else repaired
            if not isinstance(parsed, dict): raise ValueError(f"返回非字典: {type(parsed)}")
            return parsed
        except Exception as e:
            try:
                repaired = repair_json(raw_text)
                parsed = json.loads(repaired) if isinstance(repaired, str) else repaired
                if isinstance(parsed, dict): return parsed
            except: pass
            
            return {
                "narrator_transition": "（系统受到干扰，尝试理清思绪...）",
                "current_scene": "未知",
                "dialogue_sequence": [{"speaker": "系统提示", "content": "（由于未知干扰，当前对话解析失败，请检查参数面板中的“原始输出”查明原因。）", "mood": "neutral"}],
                "npc_background_actions": [],
                "wechat_notifications": [],
                "next_options": ["【深呼吸】", "【重试】", "【继续观察】"],
                "stat_changes": {},
                "is_end": False
            }

    def play_main_turn(self, action_text, selected_chars, current_evt_id, is_transition, api_key, base_url, model, tmp, top_p, max_t, pres_p, freq_p, san, money, gpa, hygiene, reputation, arg_count, chapter, turn, affinity, wechat_data_dict, is_prefetch=False, custom_prompts=None):
        self.llm.update_config(api_key=api_key, base_url=base_url, model=model)
        
        # --- 动态映射逻辑 ---
        roster_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "prompts", "characters", "roster.json")
        roster = {}
        if os.path.exists(roster_path):
            try:
                with open(roster_path, 'r', encoding='utf-8') as f:
                    roster = json.load(f)
            except: pass

        def get_name(cid):
            if cid in roster: return roster[cid].get("name", cid)
            if hasattr(presets_module, "CANDIDATE_POOL") and cid in presets_module.CANDIDATE_POOL:
                return presets_module.CANDIDATE_POOL[cid].Name
            return cid

        selected_chars = [get_name(c) for c in selected_chars]
        
        mapped_affinity = {}
        for k, v in affinity.items():
            mapped_affinity[get_name(k)] = v
        affinity = mapped_affinity

        player_stats = {"money": money, "san": san, "hygiene": hygiene, "gpa": gpa, "reputation": reputation}
        settlement_msg = ""
        
        if is_transition or current_evt_id == "":
            if turn == 0: 
                self.mm.clear_game_history()
                self.director.current_chapter = chapter
                self.director.chapter_progress = 0
                self.director.used_events = []
                
            next_evt = self.director.get_next_event(player_stats, selected_chars, affinity)
            if not next_evt:
                # 游戏全流程已结束 (毕业)
                return {
                    "is_game_over": True,
                    "display_text": "**[大学生活圆满结束]** 你完成了四年的大学生活，走向了人生的新阶段。恭喜毕业！",
                    "chapter": chapter,
                    "turn": turn,
                    "san": san,
                    "money": money,
                    "gpa": gpa,
                    "is_end": True,
                    "next_options": ["查看我的结局", "重新开始"],
                    "dialogue_sequence": [{"speaker": "系统提示", "content": "全剧终。", "mood": "happy"}]
                }

            if next_evt.chapter > chapter:
                money -= 800  
                gpa = max(0.0, min(4.0, 3.0 - (arg_count * 0.05)))
                settlement_msg = f"**[大{chapter}学年结算]** 扣除生活费800。GPA：{gpa:.2f}\n\n"
                chapter = next_evt.chapter; arg_count = 0 
            turn = 1
            event_context = f"【系统指令】开始以下事件，不要写任何开场白或过场旁白。\n【新事件】:{next_evt.name}\n【场景描述】:{next_evt.description}"
        else:
            next_evt = self.director.event_database.get(current_evt_id)
            if not next_evt:
                return {"error": "事件丢失，请重置游戏。"}
            turn += 1
            # 将 turn >= 3 改为 turn >= 6
            pacing = "【节奏：结局】事件已充分发展，请明确收尾，将 is_end 置为 true。" if turn >= 6 else "【节奏：激化】冲突升级，引发新的讨论。"
            event_context = f"【事件】: {next_evt.name}\n【回合】: {turn}/6\n{pacing}\n【玩家选择意图】: {action_text}"

        try:
            relevant_docs = self.mm.vector_store.search(f"{next_evt.name} {action_text}", n_results=6)
            valid_lores = []
            active_plus_player = selected_chars + ["陆陈安然"] 
            for d in relevant_docs:
                content = d.get('content', '')
                if "语录" in content and any(f"[{c}" in content for c in active_plus_player):
                    valid_lores.append(content)
            lore_str = "\n".join(valid_lores[:3])
        except: 
            lore_str = ""

        wechat_summary = "【近期微信动态】\n"
        has_recent_wechat = False
        for chat_name, messages in wechat_data_dict.items():
            if messages:
                last_msg = messages[-1]
                msg_content = last_msg[0] if last_msg[0] else last_msg[1].replace("**", "")
                wechat_summary += f"- 在 {chat_name} 中，最后消息：“{msg_content}”。\n"
                has_recent_wechat = True
        if not has_recent_wechat: wechat_summary += "无\n"

        game_context = {
            "chapter": chapter,
            "turn": turn,
            "event_name": next_evt.name,               
            "event_description": next_evt.description, 
            "active_chars": selected_chars,
            "rag_lore": lore_str,
            "custom_prompts": custom_prompts
        }

        sys_prm = self.pm.get_main_system_prompt(game_context)
        safe_keys = ", ".join([str(k) for k in wechat_data_dict.keys()])

        # ========================================================
        # 多智能体剧场演出阶段
        # ========================================================

        npc_chars = [c for c in selected_chars if c != "陆陈安然"]
        reactions_str = ""
        
        if npc_chars and not getattr(next_evt, 'is_cg', False):
            agents = []
            for char_name in npc_chars:
                char_file = self.pm.char_file_map.get(char_name, "")
                profile_text = ""
                if custom_prompts and char_name in custom_prompts:
                    profile_text = custom_prompts[char_name]
                elif char_file:
                    profile_text = self.pm._read_md(f"characters/{char_file}")
                else:
                    profile_text = f"你扮演的大型语言模型未能找到 {char_name} 的具体设定文件，请根据你的名字合理推演。"
                rel_text = ""
                rel_csv_path = os.path.join(self.pm.chars_dir, "relationship.csv")
                if os.path.exists(rel_csv_path):
                    try:
                        with open(rel_csv_path, 'r', encoding='utf-8-sig') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                if row.get("评价者", "").strip() == char_name and row.get("被评价者", "").strip() in selected_chars:
                                    target = row.get("被评价者", "").strip()
                                    surface = row.get("表面态度", "").strip()
                                    inner = row.get("内心真实评价", "").strip()
                                    rel_text += f"- 对待【{target}】：表面[{surface}]，内心觉得[{inner}]。\n"
                    except: pass
                
                agent = NPCAgent(char_name, profile_text, rel_text, self.llm)
                agents.append(agent)
                
            async def fetch_all_reactions():
                tasks = [agent.async_react(event_context, action_text) for agent in agents]
                return await asyncio.gather(*tasks)

            t1 = time.time()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    with concurrent.futures.ThreadPoolExecutor(1) as pool:
                        reactions = pool.submit(lambda: asyncio.run(fetch_all_reactions())).result()
                else:
                    reactions = asyncio.run(fetch_all_reactions())
            except Exception:
                reactions = asyncio.run(fetch_all_reactions())
            print(f"🛑 [耗时监控] NPC 并发思考耗时: {time.time() - t1:.2f} 秒")
                
            reactions_str = "\n\n【演员就位：以下是在场室友刚才做出的独立反应】\n(⚠️系统警告：请你作为 DM，严格采纳以下室友的反应进行编排。禁止篡改她们的原意、动作和准备发送的微信内容！)\n"
            for i, char_name in enumerate(npc_chars):
                r = reactions[i]
                mood = r.get("mood", "平静")
                action = r.get("action", "")
                dia = r.get("dialogue", "")
                wec = r.get("wechat_message", "")
                reactions_str += f"- {char_name}: [情绪]:{mood} | [动作]:{action}\n"
                if dia: reactions_str += f"  嘴上说：“{dia}”\n"
                if wec: reactions_str += f"  准备在微信发：“{wec}”\n"
        
        # ========================================================
        # DM统筹并结算阶段
        # ========================================================
        
        user_prm = f"{event_context}\n\n【玩家意图】: {action_text}{reactions_str}\n\n【现有微信通讯录】: {safe_keys}\n{wechat_summary}\n[状态] SAN:{san}, 资金:{money}。\n\n{self.pm.get_main_author_note()}"

        try:
            if getattr(next_evt, 'is_cg', False):
                cg_dialogue = getattr(next_evt, 'fixed_dialogue', [])
                if not cg_dialogue:
                    cg_dialogue = [{"speaker": "系统提示", "content": "（剧情触发成功，但CSV对应行没有对话内容。）", "mood": "neutral"}]
                
                cg_options_dict = getattr(next_evt, 'options', {})
                cg_options = list(cg_options_dict.values()) if cg_options_dict else ["继续剧情..."]

                parsed = {
                    "narrator_transition": f"🎬 **[剧情演出] {next_evt.name}**\n---", 
                    "current_scene": "宿舍",
                    "dialogue_sequence": cg_dialogue, 
                    "next_options": cg_options,
                    "stat_changes": {}, 
                    "wechat_notifications": [],
                    "npc_background_actions": [],
                    "is_end": True
                }
                res_text = json.dumps(parsed, ensure_ascii=False)
            else:
                t2 = time.time()
                res_text = self.llm.generate_response(system_prompt=sys_prm, user_input=user_prm, temperature=tmp, top_p=top_p, max_tokens=max_t, presence_penalty=pres_p, frequency_penalty=freq_p)
                print(f"🛑 [耗时监控] DM 主大脑生成 JSON 耗时: {time.time() - t2:.2f} 秒")
                parsed = self.parse_and_repair_json(res_text)

            stats_data = parsed.get("stat_changes", {})
            if not isinstance(stats_data, dict): stats_data = {} 
            
            san = max(0, min(100, san + stats_data.get("san_delta", 0)))
            money += stats_data.get("money_delta", 0)
            if stats_data.get("is_argument", False): arg_count += 1
            
            aff_changes = stats_data.get("affinity_changes", {})
            if isinstance(aff_changes, dict):
                for char_name, change_val in aff_changes.items():
                    if char_name in affinity: affinity[char_name] = max(0, min(100, affinity[char_name] + change_val))
                
            display_text = settlement_msg
            if parsed.get("narrator_transition"): display_text += f"{parsed['narrator_transition']}\n\n"
            
            dialogue_lines = []
            seq = parsed.get("dialogue_sequence", [])
            if isinstance(seq, dict): seq = [seq]
            if isinstance(seq, list):
                for t in seq:
                    if not isinstance(t, dict): continue
                    spk, cont = t.get("speaker", "神秘人"), t.get("content", "")
                    if not cont: cont = max([str(v) for k, v in t.items() if k not in ['speaker', 'mood']], key=len, default="")
                    if cont:
                        dialogue_lines.append(f"**[{spk}]** {cont}")
                        
            if dialogue_lines:
                display_text += "\n\n".join(dialogue_lines)
            
            acts = parsed.get("npc_background_actions", [])
            if isinstance(acts, dict): acts = [acts]
            if isinstance(acts, list):
                for act in acts:
                    if not isinstance(act, dict): continue
                    c_name, c_act, c_aff = act.get("character", "神秘人"), act.get("action", ""), act.get("affinity_change", 0)
                    
                    if c_name in affinity and isinstance(c_aff, (int, float)) and c_aff != 0:
                        affinity[c_name] = max(0, min(100, affinity[c_name] + c_aff))
                        aff_sign = f" (好感 {c_aff})" if c_aff < 0 else f" (好感 +{c_aff})"
                    else: 
                        aff_sign = ""
                        
                    if c_act: 
                        display_text += f"\n\n> **[暗场动态] {c_name}**: {c_act}{aff_sign}"
                        
                        if isinstance(seq, list):
                            # 将动作加上括号
                            seq.append({
                                "speaker": "system",
                                "content": f"（{c_name}{c_act}）",
                                "mood": "平静"
                            })
            
            # ========================================================
            # 真实工具调用执行层
            # ========================================================
            tool_calls = parsed.get("tool_calls", [])
            if isinstance(tool_calls, dict): tool_calls = [tool_calls]
            if isinstance(tool_calls, list):
                for tool in tool_calls:
                    if not isinstance(tool, dict): continue
                    func_name = tool.get("name", "")
                    args = tool.get("args", {})
                    
                    tool_res = self.tm.execute(func_name, args)
                    
                    if "display_text" in tool_res: display_text += tool_res["display_text"]
                    if "san_delta" in tool_res: san = max(0, min(100, san + tool_res["san_delta"]))
                    if "gpa_delta" in tool_res: gpa = max(0.0, min(4.0, gpa + tool_res["gpa_delta"]))
                    if "money_delta" in tool_res: money += tool_res["money_delta"]
            
            is_end = True if getattr(next_evt, 'is_cg', False) or turn >= 6 else parsed.get("is_end", False)

            if not getattr(next_evt, 'is_cg', False) and action_text and "（时间推移..." not in action_text and not is_prefetch:
                self.mm.save_interaction(user_input=action_text, ai_response=" ".join(dialogue_lines), user_name="陆陈安然")

            valid_notifs = []
            wechat_list = parsed.get("wechat_notifications", [])
            if isinstance(wechat_list, dict): wechat_list = [wechat_list]
            if isinstance(wechat_list, list):
                for w in wechat_list:
                    if not isinstance(w, dict): continue 
                    
                    c_name = str(w.get("chat_name", "")).strip()
                    if not c_name or c_name == "None": continue
                    
                    def simplify_name(name):
                        return re.sub(r'[【】\[\]()（）{}<>\s]', '', name)
                    
                    simplified_c_name = simplify_name(c_name)
                    matched_key = None
                    
                    for existing_key in wechat_data_dict.keys():
                        simplified_existing = simplify_name(existing_key)
                        if simplified_existing == simplified_c_name or simplified_c_name in simplified_existing:
                            matched_key = existing_key
                            break
                            
                    if matched_key:
                        c_name = matched_key 
                    else:
                        if c_name not in wechat_data_dict: 
                            wechat_data_dict[c_name] = []
                    
                    w["chat_name"] = c_name 
                    valid_notifs.append(w)

            extracted_options = parsed.get("next_options", [])
            if isinstance(extracted_options, str):
                extracted_options = [o.strip() for o in extracted_options.split(",") if o.strip()]
                
            if not isinstance(extracted_options, list) or not extracted_options:
                if getattr(next_evt, 'is_cg', False):
                    extracted_options = ["继续剧情..."]
                else:
                    extracted_options = ["【深呼吸】", "【继续观察】", "【转移话题】", "【沉默】", "【叹气】"]

            return {
                "is_game_over": False, 
                "res_text": res_text, 
                "display_text": display_text,
                "san": san, 
                "money": money, 
                "gpa": gpa, 
                "hygiene": hygiene,
                "reputation": reputation,
                "arg_count": arg_count, 
                "chapter": chapter, 
                "turn": turn, 
                "affinity": affinity, 
                "active_roommates": selected_chars,
                "current_scene": parsed.get("current_scene", "宿舍"),
                "current_evt_id": next_evt.id,
                "is_end": is_end, 
                "next_options": extracted_options, 
                "wechat_notifications": valid_notifs,
                "narrator_transition": parsed.get("narrator_transition", ""),
                "dialogue_sequence": seq if isinstance(seq, list) else [],
                "error": parsed.get("error", ""),
                "sys_prompt": sys_prm,
                "user_prompt": user_prm,
                "memory": self.mm.get_recent_history() if hasattr(self.mm, 'get_recent_history') else "模块离线",
                "relationships": self.pm.get_all_relationships() if hasattr(self.pm, 'get_all_relationships') else "模块离线",
                "tools": self.tm.get_tool_logs() if hasattr(self.tm, 'get_tool_logs') else "模块离线"
            }
        except Exception as e:
            return {
                "error": str(e),
                "sys_prompt": sys_prm if 'sys_prm' in locals() else "",
                "user_prompt": user_prm if 'user_prm' in locals() else ""
            }
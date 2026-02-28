import os
import json
import re
from json_repair import repair_json 

import src.core.presets as presets_module
from src.models.schema import CharacterProfile
from src.services.llm_service import LLMService
from src.core.memory_manager import MemoryManager
from src.core.event_director import EventDirector
from src.core.event_script import EVENT_DATABASE

from src.core.prompt_manager import PromptManager

class GameEngine:
    def __init__(self):
        self.candidate_pool = {}
        for key, obj in vars(presets_module).items():
            if isinstance(obj, CharacterProfile) and obj.Name != "陆陈安然": 
                self.candidate_pool[obj.Name] = obj
                
        self.llm = LLMService()
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        self.mm = MemoryManager(os.path.join(data_dir, "profile.json"), os.path.join(data_dir, "chroma_db"), self.llm)
        self.director = EventDirector()
        self.pm = PromptManager()

    def parse_and_repair_json(self, raw_text):
        """🌟 终极容错 JSON 解析器，防模型发癫"""
        raw_text = re.sub(r'```json\s*', '', raw_text)
        raw_text = re.sub(r'```\s*', '', raw_text)
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        raw_json = match.group(0) if match else raw_text
        
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
                "dialogue_sequence": [{"speaker": "系统提示", "content": "（由于未知干扰，部分对话解析失败，但世界仍在运转。）", "mood": "neutral"}],
                "npc_background_actions": [],
                "wechat_notifications": [],
                "next_options": ["【深呼吸】", "【继续观察】", "【沉默】"],
                "stat_changes": {},
                "is_end": False
            }

    def play_main_turn(self, action_text, selected_chars, current_evt_id, is_transition, api_key, base_url, model, tmp, top_p, max_t, pres_p, freq_p, san, money, gpa, arg_count, chapter, turn, affinity, wechat_data_dict):
        self.llm.update_config(api_key=api_key, base_url=base_url, model=model)
        
        player_stats = {"money": money, "san": san, "hygiene": 100}
        settlement_msg = ""
        
        if is_transition or current_evt_id == "":
            if turn == 0: self.mm.clear_game_history()
            next_evt = self.director.get_next_event(player_stats, selected_chars)
            if not next_evt: return {"is_game_over": True, "msg": "🏁 游戏通关！", "san": san, "money": money, "gpa": gpa, "arg_count": arg_count, "chapter": chapter, "turn": turn, "affinity": affinity, "current_evt_id": ""}
            
            if next_evt.chapter > chapter:
                money -= 800  
                gpa = max(0.0, min(4.0, 3.0 - (arg_count * 0.05)))
                settlement_msg = f"**[大{chapter}学年结算]** 扣除生活费800。GPA：{gpa:.2f}\n\n"
                chapter = next_evt.chapter; arg_count = 0 
            turn = 1
            event_context = f"【过渡指令】进入第 {chapter} 章。\n【新事件】:{next_evt.name}\n【场景描述】:{next_evt.description}"
        else:
            next_evt = EVENT_DATABASE.get(current_evt_id)
            if not next_evt:
                return {"error": "事件丢失，请重置游戏。"}
            turn += 1
            pacing = "【节奏：结局】明确收尾，is_end 置为 true。" if turn >= 3 else "【节奏：激化】冲突升级。"
            event_context = f"【事件】: {next_evt.name}\n【回合】: {turn}/3\n{pacing}\n【玩家选择意图】: {action_text}\n⚠️请根据意图生成玩家台词（若涉及微信请放在 wechat_notifications 中），以及室友反应。"

        try:
            relevant_docs = self.mm.vector_store.search(f"{next_evt.name} {action_text}", n_results=3)
            lore_str = "\n".join([d['content'] for d in relevant_docs if "语录" in d.get('content', '')])
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
            "rag_lore": lore_str
        }

        sys_prm = self.pm.get_main_system_prompt(game_context)
        
        # 🌟 核心修复 1：强制将字典里的 Key 转为 string 之后再 join，即便大模型塞进了数字也绝对不会崩溃！
        safe_keys = ", ".join([str(k) for k in wechat_data_dict.keys()])
        user_prm = f"{event_context}\n\n【现有微信通讯录】: {safe_keys}\n{wechat_summary}\n[状态] SAN:{san}, 资金:{money}。\n\n{self.pm.get_main_author_note()}"

        try:
            if getattr(next_evt, 'is_cg', False):
                cg_dialogue = getattr(next_evt, 'fixed_dialogue', [])
                if not cg_dialogue:
                    cg_dialogue = [{"speaker": "系统提示", "content": "（剧情触发成功，但CSV对应行没有对话内容。）", "mood": "neutral"}]
                
                cg_options_dict = getattr(next_evt, 'options', {})
                cg_options = list(cg_options_dict.values()) if cg_options_dict else ["继续剧情..."]

                parsed = {
                    "narrator_transition": f"🎬 **[剧情演出] {next_evt.name}**\n---", 
                    "dialogue_sequence": cg_dialogue, 
                    "next_options": cg_options,
                    "stat_changes": {}, 
                    "wechat_notifications": [],
                    "npc_background_actions": [],
                    "is_end": True
                }
                res_text = json.dumps(parsed, ensure_ascii=False)
            else:
                res_text = self.llm.generate_response(system_prompt=sys_prm, user_input=user_prm, temperature=tmp, top_p=top_p, max_tokens=max_t, presence_penalty=pres_p, frequency_penalty=freq_p)
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
                    else: aff_sign = ""
                    if c_act: display_text += f"\n\n> 👁️ **[暗场动态] {c_name}**: {c_act}{aff_sign}"

            is_end = True if getattr(next_evt, 'is_cg', False) or turn >= 3 else parsed.get("is_end", False)
            
            if not getattr(next_evt, 'is_cg', False) and action_text and "（时间推移..." not in action_text:
                self.mm.save_interaction(user_input=action_text, ai_response=" ".join(dialogue_lines), user_name="陆陈安然")
            
            valid_notifs = []
            wechat_list = parsed.get("wechat_notifications", [])
            if isinstance(wechat_list, dict): wechat_list = [wechat_list]
            if isinstance(wechat_list, list):
                for w in wechat_list:
                    if not isinstance(w, dict): continue 
                    
                    # 🌟 核心修复 2：强行把大模型生成的群名转换为字符串，根绝后患！
                    c_name = str(w.get("chat_name", "")).strip()
                    if not c_name or c_name == "None": continue
                    
                    # 动态建群
                    if c_name not in wechat_data_dict: 
                        wechat_data_dict[c_name] = []
                    
                    w["chat_name"] = c_name # 写回修正后的字符串
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
                "arg_count": arg_count, 
                "chapter": chapter, 
                "turn": turn, 
                "affinity": affinity, 
                "current_evt_id": next_evt.id,
                "is_end": is_end, 
                "next_options": extracted_options, 
                "wechat_notifications": valid_notifs
            }
        except Exception as e:
            return {"error": str(e)}
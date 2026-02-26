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
        
        # 动态定位项目根目录下的 data 文件夹
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        self.mm = MemoryManager(os.path.join(data_dir, "profile.json"), os.path.join(data_dir, "chroma_db"), self.llm)
        self.director = EventDirector()
        self.pm = PromptManager()

    def parse_and_repair_json(self, raw_text):
        """统一的 JSON 容错解析流水线"""
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        raw_json = match.group(0) if match else raw_text
        raw_json = raw_json.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace("：", ":")
        return json.loads(repair_json(raw_json))

    def play_wechat_turn(self, player_msg, current_chat_name, wechat_sys, current_evt_id, turn, api_key, base_url, model, tmp, top_p, affinity):
        """处理微信通讯逻辑"""
        self.llm.update_config(api_key=api_key, base_url=base_url, model=model)
        
        members = wechat_sys.channels.get(current_chat_name, [])
        encyclopedia = "【群聊成员图鉴】\n"
        for name in members:
            if name in self.candidate_pool:
                encyclopedia += f"- {name}: {self.candidate_pool[name].Core_Archetype}。冲突风格: {self.candidate_pool[name].Conflict_Style}。\n"

        event_context = "【当前现实局势】: 日常阶段。"
        if current_evt_id in EVENT_DATABASE:
            evt = EVENT_DATABASE[current_evt_id]
            event_context = f"【当前现实局势】: 现实中正在发生事件“{evt.name}”。"

        system_prm = f"{self.pm.get_wechat_prompt(current_chat_name, members)}\n\n{encyclopedia}\n{event_context}"
        user_prm = f"玩家（陆陈安然）发送了：{player_msg}"

        try:
            res_text = self.llm.generate_response(system_prompt=system_prm, user_input=user_prm, temperature=tmp, top_p=top_p)
            parsed = self.parse_and_repair_json(res_text)
            
            for char_name, change_val in parsed.get("affinity_changes", {}).items():
                if char_name in affinity:
                    affinity[char_name] = max(0, min(100, affinity[char_name] + change_val))
                    
            chat_lines = []
            for t in parsed.get("chat_history", []):
                snd = t.get("sender", "神秘人")
                if snd not in members and snd != "陆陈安然": snd = members[0] if members else "神秘人"
                
                msg = t.get("message", "")
                if not msg: msg = max([str(v) for k, v in t.items() if k != 'sender'], key=len, default="")
                chat_lines.append(f"**{snd}**: {msg}")
                
            reply_text = "\n\n".join(chat_lines) if chat_lines else "（对方已读不回）"
                
            clean_ai_reply = reply_text.replace("\n\n", " ") 
            self.mm.save_interaction(user_input=f"[在微信 {current_chat_name} 中说] {player_msg}", ai_response=clean_ai_reply, user_name="陆陈安然")
                
            return reply_text, affinity, None
        except Exception as e:
            return f"❌ 网络错误: {e}", affinity, str(e)

    def play_main_turn(self, action_text, selected_chars, current_evt_id, is_transition, api_key, base_url, model, tmp, top_p, max_t, pres_p, freq_p, san, money, gpa, arg_count, chapter, turn, affinity, wechat_data_dict):
        """处理现实主线逻辑"""
        self.llm.update_config(api_key=api_key, base_url=base_url, model=model)
        mock_player_stats = {"hygiene": 50, "affinity_xueba": 5} 
        settlement_msg = ""
        
        if is_transition or current_evt_id == "":
            if turn == 0: self.mm.clear_game_history()
            next_evt = self.director.get_next_event(mock_player_stats, selected_chars)
            if not next_evt: return {"is_game_over": True, "msg": "🏁 游戏通关！", "san": san, "money": money, "gpa": gpa, "arg_count": arg_count, "chapter": chapter, "turn": turn, "affinity": affinity, "current_evt_id": ""}
            
            if next_evt.chapter > chapter:
                money -= 800  
                gpa = max(0.0, min(4.0, 3.0 - (arg_count * 0.05)))
                settlement_msg = f"**[大{chapter}学年结算]** 扣除生活费800。GPA：{gpa:.2f}\n\n"
                chapter = next_evt.chapter; arg_count = 0 
            turn = 1
            event_context = f"【过渡指令】进入第 {chapter} 章。\n【新事件】:{next_evt.name}\n【场景描述】:{next_evt.description}"
        else:
            next_evt = EVENT_DATABASE[current_evt_id]
            turn += 1
            pacing = "【节奏：结局】明确收尾，is_end 置为 true。" if turn >= 3 else "【节奏：激化】冲突升级。"
            event_context = f"【事件】: {next_evt.name}\n【回合】: {turn}/3\n{pacing}\n【玩家选择意图】: {action_text}\n⚠️先写玩家的行动/台词，再写室友反应。"

        encyclopedia = "【在场图鉴】\n"
        for name in selected_chars:
            if name in self.candidate_pool:
                encyclopedia += f"- {name}: {self.candidate_pool[name].Core_Archetype}。倾向:[{self.candidate_pool[name].Conflict_Style}]。\n"

        try:
            relevant_docs = self.mm.vector_store.search(f"{next_evt.name} {action_text}", n_results=3)
            lore_str = "\n".join([d['content'] for d in relevant_docs if "语录" in d.get('content', '')])
        except: lore_str = ""

        wechat_summary = "【近期微信动态】\n"
        has_recent_wechat = False
        for chat_name, messages in wechat_data_dict.items():
            if messages:
                wechat_summary += f"- 在 {chat_name} 中，玩家刚刚说了：“{messages[-1][0]}”。\n"
                has_recent_wechat = True
        if not has_recent_wechat: wechat_summary += "无\n"

        sys_prm = f"{self.pm.get_main_system_prompt()}\n\n{encyclopedia}\n【供模仿语录】:\n{lore_str}"
        user_prm = f"{event_context}\n\n【现有微信通讯录】: {', '.join(wechat_data_dict.keys())}\n{wechat_summary}\n[状态] SAN:{san}, 资金:{money}。\n\n{self.pm.get_main_author_note()}"

        try:
            if getattr(next_evt, 'is_cg', False):
                parsed = {"narrator_transition": f"[演出] {next_evt.name}", "dialogue_sequence": getattr(next_evt, 'fixed_dialogue', []), "next_options": ["继续"], "stat_changes": {}, "is_end": True if not is_transition else False}
                res_text = json.dumps(parsed, ensure_ascii=False)
            else:
                res_text = self.llm.generate_response(system_prompt=sys_prm, user_input=user_prm, temperature=tmp, top_p=top_p, max_tokens=max_t, presence_penalty=pres_p, frequency_penalty=freq_p)
                parsed = self.parse_and_repair_json(res_text)

            stats_data = parsed.get("stat_changes", {})
            san = max(0, min(100, san + stats_data.get("san_delta", 0)))
            money += stats_data.get("money_delta", 0)
            if stats_data.get("is_argument", False): arg_count += 1
            for char_name, change_val in stats_data.get("affinity_changes", {}).items():
                if char_name in affinity: affinity[char_name] = max(0, min(100, affinity[char_name] + change_val))
                
            display_text = settlement_msg
            if parsed.get("narrator_transition"): display_text += f"{parsed['narrator_transition']}\n\n"
            
            dialogue_lines = []
            for t in parsed.get("dialogue_sequence", []):
                spk, cont = t.get("speaker", "神秘人"), t.get("content", "")
                if not cont: cont = max([str(v) for k, v in t.items() if k not in ['speaker', 'mood']], key=len, default="")
                dialogue_lines.append(f"**[{spk}]** {cont}")
            display_text += "\n\n".join(dialogue_lines)
            
            for act in parsed.get("npc_background_actions", []):
                c_name, c_act, c_aff = act.get("character", "神秘人"), act.get("action", ""), act.get("affinity_change", 0)
                if c_name in affinity and c_aff != 0:
                    affinity[c_name] = max(0, min(100, affinity[c_name] + c_aff))
                    aff_sign = f" (好感 {c_aff})" if c_aff < 0 else f" (好感 +{c_aff})"
                else: aff_sign = ""
                display_text += f"\n\n> 👁️ **[暗场动态] {c_name}**: {c_act}{aff_sign}"

            is_end = True if turn >= 3 else parsed.get("is_end", False)
            if not getattr(next_evt, 'is_cg', False) and action_text and "（时间推移..." not in action_text:
                self.mm.save_interaction(user_input=action_text, ai_response=" ".join(dialogue_lines), user_name="陆陈安然")
            
            valid_notifs = []
            for w in parsed.get("wechat_notifications", []):
                c_name = w.get("chat_name", "")
                if c_name in wechat_data_dict: valid_notifs.append(w)

            return {
                "is_game_over": False, "res_text": res_text, "display_text": display_text,
                "san": san, "money": money, "gpa": gpa, "arg_count": arg_count, "chapter": chapter, 
                "turn": turn, "affinity": affinity, "current_evt_id": next_evt.id,
                "is_end": is_end, "next_options": parsed.get("next_options", []),
                "wechat_notifications": valid_notifs
            }
        except Exception as e:
            return {"error": str(e)}
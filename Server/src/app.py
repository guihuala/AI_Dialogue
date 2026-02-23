from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import random
import sys
import os

# 把当前文件的上一级目录加入系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.presets import CANDIDATE_POOL
from src.models.schema import PlayerStats
from src.services.llm_service import LLMService

app = FastAPI(title="Roommate Survival Game API")

# 初始化你封装好的 LLM 客户端
llm_service = LLMService()

# --- 保持你原有的请求体定义完全不变 ---
class GetOptionsRequest(BaseModel):
    active_roommates: List[str]

class PerformActionRequest(BaseModel):
    choice: str
    active_roommates: List[str]

# --- 路由与接口 ---

@app.post("/api/get_options")
def get_options(req: GetOptionsRequest): # 去掉 async，适配你的同步 LLMService
    """
    接入 LLM 动态生成玩家的行动选项
    """
    if not req.active_roommates:
        raise HTTPException(status_code=400, detail="没有传入室友数据")
        
    active_profiles = [CANDIDATE_POOL[c_id] for c_id in req.active_roommates if c_id in CANDIDATE_POOL]
    char_names = [p.Name for p in active_profiles]
    
    # 构建发给 LLM 的系统指令
    system_prompt = f"""
    你是一个文字冒险游戏的选项生成器。玩家正在宿舍，面对的室友有：{', '.join(char_names)}。
    请根据当前情况，提供3个不同态度的对话选项（必须包含：附和、沉默/转移话题、阴阳怪气/质疑）。
    
    请严格返回 JSON 格式（不要有任何 markdown 标记），结构如下：
    {{
        "options": ["选项1的文本", "选项2的文本", "选项3的文本"]
    }}
    """
    
    try:
        # 调用你写好的方法
        response_text = llm_service.generate_response(
            system_prompt=system_prompt,
            user_input="请为我生成本回合的三个行动选项。",
            context="当前处于宿舍日常互动阶段。"
        )
        
        # 清理可能存在的 ```json 标记
        if "```json" in response_text:
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
        result = json.loads(response_text)
        return result
    except Exception as e:
        print(f"LLM 解析选项失败: {e}")
        # 兜底机制，防止游戏因网络波动卡死
        return {"options": ["[附和] 确实是这样...", "[沉默] ...", "[阴阳怪气] 呵呵，你开心就好。"]}


@app.post("/api/perform_action")
def perform_action(req: PerformActionRequest): # 去掉 async
    """
    接收玩家选择，调用 LLM 进行对话推演和数值结算
    """
    active_profiles = [CANDIDATE_POOL[c_id] for c_id in req.active_roommates if c_id in CANDIDATE_POOL]
    
    # 提取室友设定，防止 AI 发生 OOC
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
    
    请根据室友的性格，推演接下来的对话发展（1~3句即可）。同时，评估玩家行动对自身属性（SAN值 0-100, 资金, GPA 0-4.0）的影响。
    
    必须严格返回以下 JSON 格式（不要有任何 markdown 标记）：
    {{
        "dialogue_sequence": [
            {{"speaker": "室友姓名", "content": "说的话", "mood": "情绪"}}
        ],
        "player_stats": {{"san": 75, "gpa": 3.0, "money": 1500}},
        "game_time": {{"year": "一", "month": 10, "week": 2}},
        "current_event": "宿舍日常纷争"
    }}
    """

    try:
        # 调用你写好的推演方法
        response_text = llm_service.generate_response(
            system_prompt=system_prompt,
            user_input=f"我的行动/说话内容是：\"{req.choice}\"",
            context="当前时间：大一 第一学期"
        )
        
        # 清理 JSON 格式
        if "```json" in response_text:
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
        result = json.loads(response_text)
        return result

    except Exception as e:
        print(f"LLM 推演对话失败: {e}")
        return {
            "dialogue_sequence": [{"speaker": "System", "content": "室友们陷入了尴尬的沉默...", "mood": "neutral"}],
            "player_stats": {"san": 80, "gpa": 3.0, "money": 1500},
            "game_time": {"year": "一", "month": 9, "week": 1},
            "current_event": "系统卡顿"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
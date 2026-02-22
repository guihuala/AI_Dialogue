from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import random

import sys
import os
# 把当前文件的上一级目录（即 Server 文件夹）加入系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.presets import CANDIDATE_POOL
from src.models.schema import PlayerStats

app = FastAPI(title="Roommate Survival Game API")

# --- 请求体定义 ---
class GetOptionsRequest(BaseModel):
    active_roommates: List[str]

class PerformActionRequest(BaseModel):
    choice: str
    active_roommates: List[str]

# --- 路由与接口 ---

@app.post("/api/get_options")
async def get_options(req: GetOptionsRequest):
    """
    接收当前存活的室友名单，返回玩家本回合可以做出的行为选项。
    将来这里可以接入 LLM，根据上下文动态生成选项。
    """
    if not req.active_roommates:
        raise HTTPException(status_code=400, detail="没有传入室友数据")
        
    # 意图选项系统
    base_options = ["附和", "质疑", "沉默", "阴阳怪气", "转移话题"]
    
    # 模拟 LLM 动态生成的具体话术
    dynamic_options = [
        f"[{opt}] {random.choice(['确实是这样...', '你确定吗？', '...', '呵呵，你开心就好。', '对了，你们吃饭了吗？'])}" 
        for opt in random.sample(base_options, 3)
    ]
    
    return {"options": dynamic_options}


@app.post("/api/perform_action")
async def perform_action(req: PerformActionRequest):
    """
    接收玩家的选择，调用 LLM 进行推演，返回状态更新和对话演出序列。
    """
    # 1. 解析玩家选择（实际开发中，这里要把 choice 喂给大模型）
    print(f"玩家选择了: {req.choice}，当前室友: {req.active_roommates}")
    
    # 2. 模拟数值结算 (对应你文档中的增量结算制)
    # 实际应从后端的 GameState 或数据库中读取当前值并修改
    mock_stats = {
        "san": random.randint(30, 80),
        "gpa": round(random.uniform(2.0, 4.0), 2),
        "money": random.randint(500, 2000)
    }
    
    # 3. 模拟时间推进
    mock_time = {
        "year": "一",
        "month": random.randint(9, 12),
        "week": random.randint(1, 4)
    }
    
    # 4. 模拟大模型生成的剧本演出序列 (Dialogue Sequence)
    # 根据 active_roommates 随机挑两个人说话
    speakers = random.sample(req.active_roommates, min(2, len(req.active_roommates))) if req.active_roommates else ["System"]
    
    mock_dialogue = [
        {
            "speaker": speakers[0], 
            "content": f"（针对玩家的'{req.choice}'）你这话是什么意思？"
        },
        {
            "speaker": speakers[1] if len(speakers) > 1 else "System", 
            "content": "好了好了，别吵了，辅导员马上来查寝了！"
        }
    ]
    
    return {
        "player_stats": mock_stats,
        "game_time": mock_time,
        "current_event": "日常：突击查寝",
        "dialogue_sequence": mock_dialogue
    }

if __name__ == "__main__":
    import uvicorn
    # 运行于 8000 端口，Unity 端请求地址应为 http://127.0.0.1:8000/api/...
    uvicorn.run(app, host="0.0.0.0", port=8000)
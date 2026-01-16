from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

# --- 1. 基础组件 ---

class GameTime(BaseModel):
    year: int = Field(default=1, description="年级 (1-4)")
    month: int = Field(default=9, description="月份 (1-12)")
    week: int = Field(default=1, description="周数 (1-4)")
    
    def advance(self):
        """推进时间：每周推进一次"""
        self.week += 1
        if self.week > 4:
            self.week = 1
            self.month += 1
            if self.month > 12:
                self.month = 1
                self.year += 1

class PlayerStats(BaseModel):
    money: float = Field(default=1000.0, description="生活费")
    san: int = Field(default=80, description="理智值 (0-100)")
    gpa: float = Field(default=3.5, description="绩点 (0.0-4.0)")

class SocialContext(BaseModel):
    world_view: str = Field(..., description="The general setting")
    occupation: str = Field(..., description="Current job/role")
    current_location: str = Field(..., description="Location")

class Personality(BaseModel):
    traits: Dict[str, int] = Field(..., description="Big Five or traits")
    values: List[str] = Field(..., description="Core values")
    mood: Optional[str] = Field(default="Neutral")

class Relationship(BaseModel):
    target_name: str
    affinity: int = Field(default=0, description="Affinity score")
    tags: List[str] = Field(default=[], description="Friend, Enemy, etc.")

class DailyLogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    activity: str = Field(..., description="Summary")

# --- 2. 角色与记忆 ---

class CharacterProfile(BaseModel):
    name: str
    context: SocialContext
    personality: Personality
    relationships: Dict[str, Relationship] = Field(default_factory=dict)
    daily_log: List[DailyLogEntry] = Field(default=[])
    updated_at: datetime = Field(default_factory=datetime.now)

class MemoryItem(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    type: str = Field(..., description="observation, thought, action")
    content: str
    summary: Optional[str] = Field(default=None)
    importance: int = Field(default=1)
    related_entities: List[str] = Field(default=[])

# --- 3. 全局游戏状态 (新增) ---

class GameState(BaseModel):
    time: GameTime = Field(default_factory=GameTime)
    stats: PlayerStats = Field(default_factory=PlayerStats)
    current_event: str = "入学报到" # 当前发生的事件
    is_game_over: bool = False
    game_over_reason: str = ""
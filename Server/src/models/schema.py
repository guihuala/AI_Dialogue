from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

# --- 新增：玩家属性 (全局唯一的玩家状态) ---
class PlayerStats(BaseModel):
    money: float = Field(default=1000.0, description="生活费")
    san: int = Field(default=80, description="理智值 (0-100)")
    gpa: float = Field(default=3.5, description="绩点 (0.0-4.0)")

# 1. Social Context (保留，用于描述角色背景)
class SocialContext(BaseModel):
    world_view: str = Field(..., description="The general setting or world view")
    occupation: str = Field(..., description="Current job or role")
    current_location: str = Field(..., description="Current physical location")

# 2. Personality (保留，核心)
class Personality(BaseModel):
    traits: Dict[str, int] = Field(..., description="Big Five or other traits")
    values: List[str] = Field(..., description="Core values and beliefs")
    mood: Optional[str] = Field(default="Neutral", description="Current emotional state")

# 3. Relationships (保留，用于记录对其他人的看法)
class Relationship(BaseModel):
    target_name: str
    affinity: int = Field(default=0, description="Affinity score (-100 to 100)")
    tags: List[str] = Field(default=[], description="Tags like 'Friend', 'Enemy'")

# 4. Daily Log (保留，用于反思总结)
class DailyLogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    activity: str = Field(..., description="Summary of what happened")

# --- 角色档案 (精简版) ---
class CharacterProfile(BaseModel):
    name: str
    context: SocialContext
    personality: Personality
    relationships: Dict[str, Relationship] = Field(default_factory=dict)
    # 删除了 wealth, health, skills
    daily_log: List[DailyLogEntry] = Field(default=[])
    updated_at: datetime = Field(default_factory=datetime.now)

# --- Memory Stream Item ---
class MemoryItem(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    type: str = Field(..., description="observation, thought, or action")
    content: str
    summary: Optional[str] = Field(default=None)
    importance: int = Field(default=1)
    related_entities: List[str] = Field(default=[])
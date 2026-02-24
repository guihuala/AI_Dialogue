from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

# ==========================================
# 1. 记忆与检索系统相关模型 (Memory System)
# ==========================================
class MemoryItem(BaseModel):
    id: str
    type: str  # 例如: "observation", "action", "daily_log", "lore"
    content: str
    importance: int = 5
    summary: str = ""
    related_entities: List[str] = []
    
    # 时间戳字段：如果创建时没传时间，就自动获取现在的真实时间
    timestamp: datetime = Field(default_factory=datetime.now)

class DailyLog(BaseModel):
    timestamp: datetime
    activity: str
    interacted_with: List[str] = []

# ==========================================
# 2. 角色设定与档案模型 (Character Profiles)
# ==========================================
class SocialContext(BaseModel):
    world_view: str = ""
    occupation: str = ""
    current_location: str = ""

class SpeechPattern(BaseModel):
    Tone: str = ""
    Length: str = ""
    Forbidden_Words: List[str] = []
    Catchphrases: List[str] = []
    Formatting: str = ""

class Personality(BaseModel):
    Extroversion: int = 50
    Neuroticism: int = 50
    Agreeableness: int = 50
    traits: Dict[str, Any] = {}
    values: List[str] = []
    mood: str = "neutral"
    speaking_style: str = ""
    dialogue_examples: List[str] = []

class Relationship(BaseModel):
    Value: int = 0
    Label: str = ""
    tags: List[str] = []
    affinity: int = 0

class CurrentStatus(BaseModel):
    Sanity: int = 100
    GPA_Potential: float = 4.0
    Money: float = 0.0

class CharacterProfile(BaseModel):
    # 兼容 presets.py 的字段命名
    Character_ID: Optional[str] = None
    Name: Optional[str] = None
    Core_Archetype: Optional[str] = None
    Tags: List[str] = []
    Speech_Pattern: Optional[SpeechPattern] = None
    Stress_Reaction: Optional[str] = None
    Conflict_Style: Optional[str] = None
    Current_Status: Optional[CurrentStatus] = None
    Background_Secret: Optional[str] = None
    Habits: Optional[str] = None
    Roommate_Behavior: Optional[str] = None
    External_Behavior: Optional[str] = None
    
    # 兼容 memory_manager.py 的字段命名
    name: Optional[str] = None
    context: Optional[SocialContext] = None
    personality: Optional[Personality] = None
    relationships: Dict[str, Relationship] = {}
    daily_log: List[DailyLog] = []

    def __init__(self, **data):
        super().__init__(**data)
        # 自动同步 Name 和 name 字段，防止双边代码调用报错
        if self.name is None and self.Name is not None:
            self.name = self.Name
        if self.Name is None and self.name is not None:
            self.Name = self.name
        
        # 容错：如果没传 context 和 personality，给个默认空对象防止报错
        if self.context is None:
            self.context = SocialContext()
        if self.personality is None:
            self.personality = Personality()

# ==========================================
# 3. 游戏系统与事件模型 (Game System)
# ==========================================
class PlayerStats(BaseModel):
    san: int = 100
    gpa: float = 4.0
    money: float = 0.0

class ScriptedEvent(BaseModel):
    id: str
    name: str
    chapter: int = 1         # 属于第几章 (1-4)
    is_boss: bool = False    # 是否是该章底层的 Boss 事件
    duration_days: int = 1
    description: str
    potential_conflicts: List[str] = []
    mandatory_participants: List[str] = []
    next_event_id: Optional[str] = None
    
    # 对接策划表格的选项与结果机制
    options: Dict[str, str] = {}  # 例如 {"A": "少数服从多数", "B": "独裁"}
    outcomes: Dict[str, str] = {} # 例如 {"A": "输的一方叹气掉SAN", "B": "得罪一半人"}

class GameState(BaseModel):
    current_event_id: str
    current_phase_progress: int = 0
    display_event_name: str = ""
    display_date: str = ""
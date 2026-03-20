from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

# ==========================================
# 1. 记忆与检索系统相关模型
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
# 2. 角色设定与档案模型
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
        
        # 如果没传 context 和 personality，给个默认空对象防止报错
        if self.context is None:
            self.context = SocialContext()
        if self.personality is None:
            self.personality = Personality()

# ==========================================
# 3. 游戏系统与事件模型
# ==========================================
class PlayerStats:
    san: int = 100
    money: float = 1500.0
    gpa: float = 3.0
    hygiene: int = 100
    reputation: int = 50

class ScriptedEvent(BaseModel):
    id: str
    name: str
    chapter: int = 1         # 属于第几章 (1-4)

    # 四大分类与触发条件
    event_type: str = "通用随机池"  # 可选: "固定池", "通用随机池", "条件触发池", "角色专属事件"
    trigger_conditions: str = ""   # 对应表格里的 "Hygiene<60", "与角色好感度>50" 等
    exclusive_char: str = ""       # 如果是专属事件，对应角色名（如 "唐梦琪"）
    is_boss: bool = False

    description: str
    potential_conflicts: List[str] = []
    mandatory_participants: List[str] = []
    next_event_id: Optional[str] = None
    event_weight: float = 1.0
    cooldown_turns: int = 2
    min_turn_for_end: int = 5
    max_turn_for_end: int = 10
    progress_beats: List[str] = []
    end_signals: List[str] = []
    allow_repeat: bool = False
    narrative_tags: List[str] = []
    state_hooks: List[str] = []
    relationship_hooks: List[str] = []
    opening_goal: str = ""
    pressure_goal: str = ""
    turning_goal: str = ""
    settlement_goal: str = ""
    fallback_consequence: str = ""
    
    options: Dict[str, str] = {}  # 例如 {"A": "少数服从多数", "B": "独裁"}
    outcomes: Dict[str, str] = {} # 例如 {"A": "输的一方叹气掉SAN", "B": "得罪一半人"}

    is_cg: bool = False
    fixed_dialogue: List[Dict[str, str]] = []

class GameState(BaseModel):
    current_event_id: str
    current_phase_progress: int = 0
    display_event_name: str = ""
    display_date: str = ""

# ==========================================
# 4. 全局世界观与背景设定
# ==========================================
class WorldSetting(BaseModel):
    university_name: str = "某不知名大学"
    major: str = "未知专业"
    dorm_number: str = "404寝室"
    background_rule: str = "普通的大学生活。"

from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class SpeechPattern(BaseModel):
    Tone: str                    
    Length: str                  
    Forbidden_Words: List[str]   
    Catchphrases: List[str]      
    Formatting: str              

class Personality(BaseModel):
    Extroversion: int            
    Neuroticism: int             
    Agreeableness: int           

class Relationship(BaseModel):
    Value: int                   
    Label: str                   

class CurrentStatus(BaseModel):
    Sanity: int                  
    GPA_Potential: float         
    Money: int                   

class CharacterProfile(BaseModel):
    Character_ID: str
    Name: str
    Core_Archetype: str          
    Tags: List[str]              
    Speech_Pattern: SpeechPattern
    Personality: Personality
    Stress_Reaction: str         
    Conflict_Style: str          
    Relationships: Dict[str, Relationship] = Field(default_factory=dict)
    Current_Status: CurrentStatus
    
    # --- 角色背景与双面行为逻辑 ---
    Background_Secret: str = ""  
    Habits: str = ""             
    Roommate_Behavior: str = ""  # 进圈逻辑
    External_Behavior: str = ""  # 出圈逻辑

# --- 游戏状态与事件系统所需结构 ---
class PlayerStats(BaseModel):
    san: int = 80
    gpa: float = 3.0
    money: int = 1500

class GameState(BaseModel):
    current_event_id: str
    player_stats: PlayerStats = Field(default_factory=PlayerStats)
    active_roommates: List[str] = Field(default_factory=list)
    turn_number: int = 1

class ScriptedEvent(BaseModel):
    id: str
    name: str
    duration_days: int
    description: str
    potential_conflicts: List[str]
    mandatory_participants: List[str]
    next_event_id: Optional[str] = None
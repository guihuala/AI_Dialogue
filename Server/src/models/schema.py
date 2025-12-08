from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

# 1. Social Context
class SocialContext(BaseModel):
    world_view: str = Field(..., description="The general setting or world view")
    occupation: str = Field(..., description="Current job or role")
    current_location: str = Field(..., description="Current physical location")

# 2. Personality & Values
class Personality(BaseModel):
    traits: Dict[str, int] = Field(..., description="Big Five or other traits, e.g., {'Openness': 8}")
    values: List[str] = Field(..., description="Core values and beliefs")
    mood: Optional[str] = Field(default="Neutral", description="Current emotional state")
    growth_history: List[str] = Field(default=[], description="History of personality changes")

# 3. Relationships
class Relationship(BaseModel):
    target_name: str
    affinity: int = Field(default=0, description="Affinity score (-100 to 100)")
    tags: List[str] = Field(default=[], description="Tags like 'Friend', 'Enemy'")
    history: List[str] = Field(default=[], description="Key interaction summary")

# 4. Wealth
class Wealth(BaseModel):
    currency: float = Field(default=0.0)
    assets: List[str] = Field(default=[])

# 5. Health
class Health(BaseModel):
    hp: int = Field(default=100)
    stamina: int = Field(default=100)
    status_effects: List[str] = Field(default=[])

# 6. Skills
class Skill(BaseModel):
    name: str
    level: int = Field(default=1)
    description: str

# 7. Daily Log
class DailyLogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    activity: str = Field(..., description="Summary of what happened")
    interacted_with: List[str] = Field(default=[], description="Names of people interacted with")

# --- Aggregate Profile ---
class CharacterProfile(BaseModel):
    name: str
    context: SocialContext
    personality: Personality
    relationships: Dict[str, Relationship] = Field(default_factory=dict)
    wealth: Wealth
    health: Health
    skills: List[Skill] = Field(default=[])
    daily_log: List[DailyLogEntry] = Field(default=[])
    updated_at: datetime = Field(default_factory=datetime.now)

# --- Memory Stream Item ---
class MemoryItem(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    type: str = Field(..., description="observation, thought, or action")
    content: str
    summary: Optional[str] = Field(default=None, description="Summarized content for indexing")
    importance: int = Field(default=1, description="Importance score 1-10")
    related_entities: List[str] = Field(default=[])

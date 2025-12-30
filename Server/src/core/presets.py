from ..models.schema import CharacterProfile, SocialContext, Personality, Wealth, Health, Skill

# 角色 1: 诸葛亮
ZHUGE = CharacterProfile(
    name="诸葛亮",
    context=SocialContext(world_view="三国", occupation="丞相", current_location="五丈原"),
    personality=Personality(traits={"智慧": 10}, values=["鞠躬尽瘁"], mood="忧虑"),
    wealth=Wealth(currency=500),
    health=Health(hp=60),
    skills=[]
)

# 角色 2: 老维克
VIC = CharacterProfile(
    name="老维克",
    context=SocialContext(world_view="赛博朋克2077", occupation="义体医生", current_location="第13区诊所"),
    personality=Personality(traits={"贪婪": 7, "专业": 9}, values=["等价交换"], mood="烦躁"),
    wealth=Wealth(currency=1200),
    health=Health(hp=85),
    skills=[]
)

# --- 角色注册表 ---
CHARACTER_REGISTRY = {
    "zhuge": ZHUGE,
    "vic": VIC
}
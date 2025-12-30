from ..models.schema import CharacterProfile, SocialContext, Personality

# 通用背景模板
ART_SCHOOL_CTX = SocialContext(
    world_view="现代知名艺术学院，竞争激烈，人际关系复杂。每个人都想成名，或者是想毁掉成名的人。",
    occupation="大二学生",
    current_location="女生宿舍 404 室"
)

# 1. Alice - 卷王
ALICE = CharacterProfile(
    name="Alice",
    context=ART_SCHOOL_CTX,
    personality=Personality(
        traits={"焦虑": 9, "野心": 10, "完美主义": 9}, 
        values=["GPA至上", "精英主义", "不能输给任何人"], 
        mood="因为画展截稿日临近而极度紧绷"
    )
)

# 2. Bella - 叛逆乐手
BELLA = CharacterProfile(
    name="Bella",
    context=ART_SCHOOL_CTX,
    personality=Personality(
        traits={"冲动": 8, "反叛": 9, "直接": 10}, 
        values=["自由", "打破规则", "朋克精神"], 
        mood="宿醉未醒，有些烦躁"
    )
)

# 3. Clara - 富家千金
CLARA = CharacterProfile(
    name="Clara",
    context=ART_SCHOOL_CTX,
    personality=Personality(
        traits={"傲慢": 7, "天真": 6, "品味挑剔": 9}, 
        values=["金钱能解决一切", "艺术是烧钱的游戏"], 
        mood="觉得宿舍太小，正在挑剔卫生问题"
    )
)

# 4. Dora - 神秘灵媒
DORA = CharacterProfile(
    name="Dora",
    context=ART_SCHOOL_CTX,
    personality=Personality(
        traits={"神叨": 9, "敏感": 8, "神经质": 7}, 
        values=["命运", "灵感来自虚空", "各种迷信"], 
        mood="盯着角落的阴影发呆"
    )
)

# 5. Eva - 社交达人(腹黑)
EVA = CharacterProfile(
    name="Eva",
    context=ART_SCHOOL_CTX,
    personality=Personality(
        traits={"圆滑": 9, "虚伪": 7, "八卦": 10}, 
        values=["人脉即资源", "利用价值", "表面和平"], 
        mood="挂着完美的假笑刷社交媒体"
    )
)

# 6. Fiona - 隐形社恐大神
FIONA = CharacterProfile(
    name="Fiona",
    context=ART_SCHOOL_CTX,
    personality=Personality(
        traits={"内向": 10, "观察力": 9, "社恐": 9}, 
        values=["安全感", "不被注意", "二次元才是真爱"], 
        mood="戴着降噪耳机，试图降低存在感"
    )
)

CHARACTER_REGISTRY = {
    "alice": ALICE,
    "bella": BELLA,
    "clara": CLARA,
    "dora": DORA,
    "eva": EVA,
    "fiona": FIONA
}
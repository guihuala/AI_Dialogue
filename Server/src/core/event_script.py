from src.models.schema import ScriptedEvent

# 1. 开学全院自我介绍
EVT_INTRO = ScriptedEvent(
    id="evt_intro_01",
    name="新生见面会",
    duration_days=1,
    description="""
    今天是艺术学院新生的第一次全员大会。所有人都聚集在阶梯教室。
    院长正在台上发表冗长的讲话，台下的学生们开始躁动。
    这是一个展示个性、结交盟友或树立敌人的关键时刻。
    """,
    potential_conflicts=[
        "有人因为衣着品味被嘲笑",
        "Alice 试图在自我介绍时抢风头，引起其他人反感",
        "Bella 在院长讲话时大声喧哗或睡觉",
        "Clara 嫌弃阶梯教室的椅子太硬"
    ],
    mandatory_participants=["alice", "bella", "clara", "dora", "eva", "fiona"], # 所有人都在
    next_event_id="evt_military_01"
)

# 2. 军训环节
EVT_MILITARY = ScriptedEvent(
    id="evt_military_01",
    name="地狱军训",
    duration_days=14,
    description="""
    为期两周的封闭式军训。烈日当头，教官极其严厉。
    所有人都穿着丑陋的迷彩服，妆容花掉，精疲力竭。
    体力差的人开始拖后腿，集体荣誉感与个人主义开始剧烈碰撞。
    """,
    potential_conflicts=[
        "Fiona 因为体质弱晕倒，有人认为是装的",
        "Alice 指责 Bella 站军姿不标准导致全队受罚",
        "Eva 试图通过讨好教官来获得休息时间",
        "因为洗澡排队问题引发的宿舍内斗"
    ],
    mandatory_participants=[], # 默认选中的室友在场
    next_event_id="evt_midterm_01" # 假设下一个是期中
)

# 事件库索引
EVENT_DATABASE = {
    EVT_INTRO.id: EVT_INTRO,
    EVT_MILITARY.id: EVT_MILITARY
}

def get_event(event_id: str) -> ScriptedEvent:
    return EVENT_DATABASE.get(event_id, EVT_INTRO)
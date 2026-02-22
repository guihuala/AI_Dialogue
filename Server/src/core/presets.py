from src.models.schema import CharacterProfile, SpeechPattern, Personality, Relationship, CurrentStatus

# --- 0. 玩家设定 ---
PLAYER_ANRAN = CharacterProfile(
    Character_ID="player_anran",
    Name="陆陈安然",
    Core_Archetype="温吞/淡漠/选择困难症/观察型内倾",
    Tags=["Observer", "Headphones", "Passive", "Dissociation"],
    Speech_Pattern=SpeechPattern(
        Tone="calm_and_detached",
        Length="variable_but_often_silent",
        Forbidden_Words=["我保证", "一定能", "绝对"],
        Catchphrases=["哦", "随便吧", "我都行"],
        Formatting="no_emoji_strict"
    ),
    Personality=Personality(Extroversion=20, Neuroticism=30, Agreeableness=60),
    Stress_Reaction="dissociation_and_observe", 
    Conflict_Style="avoidance_or_secret_complaint",
    Current_Status=CurrentStatus(Sanity=80, GPA_Potential=3.0, Money=1500),
    Background_Secret="拥有wb小号，记录对室友的吐槽。表面附和背地蛐蛐。若被发现将大幅降SAN。",
    Habits="经常戴着耳机（没放音乐），无声观察。悄悄整理公共区域。",
    Roommate_Behavior="作为树洞和倾听者，看透一切但不干涉。",
    External_Behavior="N/A"
)

# --- 1. 唐梦琪 ---
TANG_MENGQI = CharacterProfile(
    Character_ID="tang_mengqi",
    Name="唐梦琪",
    Core_Archetype="天真烂漫/极度情绪化/外向型依赖",
    Tags=["Shopaholic", "Boyfriend_Dependent"],
    Speech_Pattern=SpeechPattern(
        Tone="dramatic_and_emotional",
        Length="long_and_rambling",
        Forbidden_Words=["穷", "便宜", "买不起"],
        Catchphrases=["既然你没有说我，那我就可以这么做", "宝宝"],
        Formatting="heavy_emoji_usage"
    ),
    Personality=Personality(Extroversion=90, Neuroticism=85, Agreeableness=40),
    Stress_Reaction="shopping_spree",
    Conflict_Style="revenge_my_way", 
    Relationships={"player_anran": Relationship(Value=0, Label="喜欢的丫鬟")},
    Current_Status=CurrentStatus(Sanity=70, GPA_Potential=2.0, Money=-500), 
    Background_Secret="家里负债，父母常吵架，但自身高消费习惯难改。",
    Habits="每天收大件快递。外放直播/连麦。不搞卫生。",
    Roommate_Behavior="极度自我，偶尔分发零食。不允许违抗她的'命令'。",
    External_Behavior="隔壁寝室的富家女，常因外放噪音或炫富引发冲突事件。"
)

# --- 2. 李一诺 ---
LI_YINUO = CharacterProfile(
    Character_ID="li_yinuo",
    Name="李一诺",
    Core_Archetype="厌恶低效/规则至上/优绩主义",
    Tags=["Rule_Enforcer", "Early_Bird", "GPA_Oriented"],
    Speech_Pattern=SpeechPattern(
        Tone="formal_and_criticizing",
        Length="concise",
        Forbidden_Words=["随便", "躺平", "晚起"],
        Catchphrases=["时间是最大的成本", "这太低效了"],
        Formatting="structured_bullet_points"
    ),
    Personality=Personality(Extroversion=40, Neuroticism=75, Agreeableness=30),
    Stress_Reaction="double_down_on_studying",
    Conflict_Style="logical_argument_and_rule_citation",
    Relationships={"player_anran": Relationship(Value=0, Label="取决于GPA表现")},
    Current_Status=CurrentStatus(Sanity=65, GPA_Potential=3.9, Money=1000),
    Background_Secret="害怕努力失败。对规则的严格执行源于内心对秩序崩塌的恐惧。",
    Habits="早6点闹钟。制定严格公约。熄灯后开台灯且翻书声大。",
    Roommate_Behavior="规则执行者，玩家表现低效会施加同辈压力。",
    External_Behavior="班里的学习委员，经常在群里催收作业，是系统规则的代理人。"
)

# --- 3. 赵鑫 ---
ZHAO_XIN = CharacterProfile(
    Character_ID="zhao_xin",
    Name="赵鑫",
    Core_Archetype="老鼠人/韧性强/实用主义/抠搜",
    Tags=["Hoarder", "Gamer", "Frugal", "Tomboy"],
    Speech_Pattern=SpeechPattern(
        Tone="low_pitch_and_fast",
        Length="short",
        Forbidden_Words=["买新的", "扔掉"],
        Catchphrases=["浪费钱", "能用就行"],
        Formatting="minimalist"
    ),
    Personality=Personality(Extroversion=20, Neuroticism=40, Agreeableness=40),
    Stress_Reaction="gaming_binge",
    Conflict_Style="silent_resentment_or_explosive",
    Current_Status=CurrentStatus(Sanity=80, GPA_Potential=2.5, Money=3000), 
    Background_Secret="隐忍但有清晰底线，被触及会引发可怕的报复。",
    Habits="囤积外卖盒和可回收物。疯狂打JRPG。宿舍做饭。",
    Roommate_Behavior="生活成本低但囤积癖严重，常引发卫生矛盾。",
    External_Behavior="隔壁寝室的代购/二手商，玩家没钱时可找她交易，可能引发纠纷。"
)

# --- 4. 林飒 ---
LIN_SA = CharacterProfile(
    Character_ID="lin_sa",
    Name="林飒",
    Core_Archetype="爱装B/反叛/感性/艺术至上",
    Tags=["Rebel", "Artistic", "Smoker", "Night_Owl"],
    Speech_Pattern=SpeechPattern(
        Tone="cool_and_humorous",
        Length="variable",
        Forbidden_Words=["规矩", "应该", "听话"],
        Catchphrases=["绝了", "这很艺术", "规则就是用来打破的"],
        Formatting="lowercase_and_slang"
    ),
    Personality=Personality(Extroversion=70, Neuroticism=50, Agreeableness=65),
    Stress_Reaction="smoking_and_avoidance",
    Conflict_Style="humor_deflection",
    Relationships={"player_anran": Relationship(Value=20, Label="灵魂理解的安全屋")},
    Current_Status=CurrentStatus(Sanity=60, GPA_Potential=3.2, Money=1200),
    Background_Secret="和一些女同学的关系被说闲话。极度害怕被保守的父母知道真实情况。",
    Habits="昼伏夜出，在寝室吸烟掩盖味道。常发幽默pyq。",
    Roommate_Behavior="好相处且提供情绪价值，但作息颠倒且吸烟会引爆矛盾。",
    External_Behavior="出没校园夜场的风云人物，作为外部事件切入时会带来流言蜚语或地下文化冲突。"
)

# --- 5. 陈雨婷 ---
CHEN_YUTING = CharacterProfile(
    Character_ID="chen_yuting",
    Name="陈雨婷",
    Core_Archetype="控制狂/社交为王/精于算计",
    Tags=["Student_Council_Leader", "Clean_Freak", "Two_Faced", "Information_Hub"],
    Speech_Pattern=SpeechPattern(
        Tone="passive_aggressive",
        Length="short_and_sharp",
        Forbidden_Words=["哈哈", "亲", "随便"],
        Catchphrases=["我就随口一说", "这是原则问题"],
        Formatting="no_emoji_strict"
    ),
    Personality=Personality(Extroversion=80, Neuroticism=80, Agreeableness=30), 
    Stress_Reaction="blame_others",
    Conflict_Style="cold_war",
    Relationships={"player_anran": Relationship(Value=50, Label="战略盟友")},
    Current_Status=CurrentStatus(Sanity=75, GPA_Potential=3.8, Money=2000),
    Background_Secret="掌握大量学生及老师的黑料。最大弱点是害怕失去权力。",
    Habits="手机不离手。喜欢拉小群组，寝室里接听涉及秘密的电话。",
    Roommate_Behavior="极度靠谱，能提供情报特权，但有洁癖极难伺候，容不得反抗。",
    External_Behavior="铁面无私的学生会干部。若不选她做室友，会突袭检查寝室施压扣分。"
)

# --- 6. 苏浅 ---
SU_QIAN = CharacterProfile(
    Character_ID="su_qian",
    Name="苏浅",
    Core_Archetype="社恐/内向敏感/脆弱易碎",
    Tags=["Social_Phobia", "Net_Famous", "Depressed", "Artist"],
    Speech_Pattern=SpeechPattern(
        Tone="hesitant",
        Length="very_short",
        Forbidden_Words=["绝对", "一定", "我保证"],
        Catchphrases=["对不起", "...那个", "是我不好"],
        Formatting="ellipses_heavy"
    ),
    Personality=Personality(Extroversion=10, Neuroticism=95, Agreeableness=60),
    Stress_Reaction="breakdown_and_medication",
    Conflict_Style="flight_and_crying",
    Current_Status=CurrentStatus(Sanity=40, GPA_Potential=3.5, Money=1800),
    Background_Secret="网络名气不好，曾被指控抄袭且被开盒泄露身份证照，导致严重躯体化。",
    Habits="极少讲话，习惯眼神交流。深夜或独处时画同人和oc。玩二次元手游。",
    Roommate_Behavior="存在感极低，遭遇网暴事件时需要玩家耗费SAN去安抚。",
    External_Behavior="隔壁班透明人，偶尔在网上引发巨大节奏，导致线下班级氛围诡异紧张。"
)

# 统一导出所有候选人字典，方便根据 ID 快速提取
CANDIDATE_POOL = {
    "tang_mengqi": TANG_MENGQI,
    "li_yinuo": LI_YINUO,
    "zhao_xin": ZHAO_XIN,
    "lin_sa": LIN_SA,
    "chen_yuting": CHEN_YUTING,
    "su_qian": SU_QIAN
}
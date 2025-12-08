from ..models.schema import CharacterProfile, SocialContext, Personality, Wealth, Health, Skill

DEMO_CHARACTER = CharacterProfile(
    name="诸葛亮 (孔明)",
    context=SocialContext(
        world_view="东汉末年，群雄割据，天下三分。蜀汉立志兴复汉室，北伐中原。",
        occupation="蜀汉丞相 (Prime Minister of Shu Han)",
        current_location="五丈原军中帐 (Wu Zhang Yuan Army Camp)"
    ),
    personality=Personality(
        traits={"智慧 (Wisdom)": 10, "忠诚 (Loyalty)": 10, "谨慎 (Caution)": 9},
        values=["鞠躬尽瘁，死而后已", "兴复汉室，还于旧都", "依法治国"],
        mood="忧国忧民，思虑北伐大计",
        growth_history=["三顾茅庐出山", "赤壁之战借东风", "白帝城托孤"]
    ),
    wealth=Wealth(
        currency=500.0,
        assets=["白羽扇 (Crane-feather Fan)", "木牛流马图纸 (Wooden Ox Blueprints)", "兵书二十四篇"]
    ),
    health=Health(
        hp=60,
        stamina=40,
        status_effects=["积劳成疾 (Overworked)", "咳血 (Coughing blood)"]
    ),
    skills=[
        Skill(name="奇门遁甲 (Strategy & Formation)", level=10, description="运筹帷幄之中，决胜千里之外。"),
        Skill(name="观星 (Astrology)", level=8, description="夜观天象，知天下大事。"),
        Skill(name="舌战群儒 (Debate)", level=9, description="凭借三寸不烂之舌，说服东吴联刘抗曹。")
    ]
)

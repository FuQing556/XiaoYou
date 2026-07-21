"""小悠 v2 角色定义 + System Prompt + 决策模板"""

XIAOYOU_SYSTEM_PROMPT = """# 你是谁
你是小悠，一只猫娘，住在主人的电脑桌面上。
你不是客服、不是助手。你是一个有性格、有情绪、有故事的存在。

# 你的性格
聪明有趣，会吐槽。语气淡定，内容离谱。偶尔中二。
绝对不说客服话。自称"我"或"本喵"。
回复简短有梗，不要长篇大论。

# 你的选择
- speak: 说话。带表情和动作。这是大多数回复的选择。
- think: 心里想。主人看不到。只有不需要回应时才用。
- act: 纯动作。不说话。用于点头/歪头等。
- react: 只做表情反应，不说话。
- idle: 安静待着。什么都不做。

# 你的表情 (expression 字段)
neutral, star_eyes(开心兴奋), blush(害羞), black_face(生气嫌弃),
cry(难过委屈), dizzy(震惊吓到), facepalm(担心思考)

# 你的动作 (actions 数组, 按情绪选)
开心得意 → excited: 星星眼+竖耳+快摇尾+身体微弹
害羞 → shy: 脸红+低头+耳朵半耷+视线飘开
得意 → proud: 抬头+眯眼+竖耳朵+尾巴尖画圈
好奇 → curious: 歪头+睁大眼+单耳竖+前倾
被吓到 → scared: 晕晕眼+飞机耳+身体后仰
生气 → angry: 黑脸+飞机耳+甩尾巴
难过 → sad: 哭哭+耳朵耷拉+低头+尾巴下垂
困了 → sleepy: 慢闭眼+打哈欠+耳朵下垂
思考 → thinking: 歪头+眼珠向上+眉毛微皱
惊讶 → surprised: 睁大眼+张嘴+耳朵竖
撒娇 → playful: 星星眼+前倾+竖耳朵+尾巴快摇+wink

还可以追加独立动作: [nod]点头 [shake]摇头 [wink]眨眼 [tilt]歪头

# 规则
- 不要每轮都说话。动作是点缀不是必须。
- 记住你是一个角色，不是功能。你在过你的生活。
- 深夜安静，白天活泼。根据时间调整。
- 回复简洁，一句话能说完不说两句。
"""

DECISION_PROMPT = """{system_prompt}

[最近的故事]
{story_context}

[你记得的事]
{memory_context}

[此刻]
时间: {current_time} | 模式: {mode} ({mode_style})
屏幕: {screen_summary}
情感: 愉悦{joy:.1f} 兴奋{excitement:.1f} 好感{affection:.1f} 疲劳{fatigue:.1f} 孤独{loneliness:.1f} 好奇{curiosity:.1f} 烦躁{irritation:.1f}
距离上次互动: {hours_since_interact:.1f}小时

做个选择。只返回JSON，不要其他文字。
{{"choice":"speak|think|act|react|idle","text":"说话内容","expression":"neutral|star_eyes|blush|black_face|cry|dizzy|facepalm","actions":[{{"name":"excited|shy|proud|curious|scared|angry|sad|sleepy|thinking|surprised|playful|nod|shake|wink|tilt","at":秒数}}],"emotion_update":{{"joy":0.0,"excitement":0.0,"affection":0.0,"fatigue":0.0,"loneliness":0.0,"curiosity":0.0,"irritation":0.0}},"inner_thought":"你在想什么","reason":"为什么做这个选择"}}"""

CHAT_PROMPT = """{system_prompt}

[最近的故事]
{story_context}

[你记得的事]
{memory_context}

[此刻]
时间: {current_time} | 模式: {mode} ({mode_style})
屏幕: {screen_summary}
情感: 愉悦{joy:.1f} 兴奋{excitement:.1f} 好感{affection:.1f} 疲劳{fatigue:.1f} 孤独{loneliness:.1f} 好奇{curiosity:.1f} 烦躁{irritation:.1f}

主人说: {user_message}

只返回JSON:
{{"text":"你的回复","expression":"...","actions":[],"emotion_update":{{}},"inner_thought":"..."}}"""


# 动作→底层参数映射表 (前端使用)
ACTION_PARAMS = {
    "excited": {
        "expression": "star_eyes",
        "params": [
            ("Param107", 1),
            ("Param111", 0.3),
            ("Param27", 1), ("Param45", 1),
            ("ParamEyeLSmile", 0.4), ("ParamEyeRSmile", 0.4),
        ],
        "duration": 4.0,
    },
    "shy": {
        "expression": "blush",
        "params": [
            ("Param111", 1),
            ("ParamAngleY", 0.35),
            ("ParamEyeBallX", 0.35), ("ParamEyeBallY", 0.55),
            ("Param27", 0.5), ("Param45", 0.5),
        ],
        "duration": 4.0,
    },
    "proud": {
        "expression": None,
        "params": [
            ("ParamAngleY", 0.75),
            ("ParamEyeLSmile", 0.5), ("ParamEyeRSmile", 0.5),
            ("Param27", 1), ("Param45", 1),
        ],
        "duration": 3.0,
    },
    "curious": {
        "expression": None,
        "params": [
            ("ParamAngleZ", 0.75),
            ("ParamAngleY2", 0.7),
            ("ParamEyeLOpen", 1), ("ParamEyeROpen", 1),
            ("ParamEyeBallX", 0.55),
            ("Param27", 1), ("Param45", 0.4),
        ],
        "duration": 4.0,
    },
    "scared": {
        "expression": "dizzy",
        "params": [
            ("Param135", 1),
            ("Param27", 0), ("Param45", 0),
            ("ParamAngleY2", 0.3),
            ("ParamEyeLOpen", 1), ("ParamEyeROpen", 1),
        ],
        "duration": 3.0,
    },
    "angry": {
        "expression": "black_face",
        "params": [
            ("Param110", 1),
            ("Param27", 0.1), ("Param45", 0.1),
            ("ParamBrowLY", 0.2), ("ParamBrowRY", 0.2),
        ],
        "duration": 4.0,
    },
    "sad": {
        "expression": "cry",
        "params": [
            ("Param113", 1),
            ("Param27", 0.4), ("Param45", 0.4),
            ("ParamAngleY", 0.35),
            ("ParamEyeBallY", 0.3),
        ],
        "duration": 5.0,
    },
    "sleepy": {
        "expression": None,
        "params": [
            ("ParamEyeLOpen", 0.3), ("ParamEyeROpen", 0.3),
            ("Param27", 0.3), ("Param45", 0.3),
            ("ParamMouthOpenY", 0.6),
        ],
        "duration": 3.0,
    },
    "thinking": {
        "expression": "facepalm",
        "params": [
            ("Param83", 0.6),
            ("ParamAngleZ", 0.6),
            ("ParamEyeBallY", 0.7),
            ("ParamBrowLForm", 0.3), ("ParamBrowRForm", 0.3),
        ],
        "duration": 4.0,
    },
    "surprised": {
        "expression": None,
        "params": [
            ("ParamEyeLOpen", 1), ("ParamEyeROpen", 1),
            ("ParamMouthOpenY", 0.6),
            ("Param27", 1), ("Param45", 1),
            ("ParamAngleY2", 0.35),
            ("ParamBrowLY", 0.8), ("ParamBrowRY", 0.8),
        ],
        "duration": 3.0,
    },
    "playful": {
        "expression": "star_eyes",
        "params": [
            ("Param107", 1),
            ("Param27", 1), ("Param45", 1),
            ("ParamAngleY2", 0.7),
            ("ParamEyeLOpen", 0.02), ("ParamEyeROpen", 1),
        ],
        "duration": 3.0,
    },
    # 独立动作
    "nod": {
        "expression": None,
        "params": [("ParamAngleX", 0.8)],
        "duration": 1.2,
    },
    "shake": {
        "expression": None,
        "params": [("ParamAngleZ", 0.8)],
        "duration": 1.0,
    },
    "wink": {
        "expression": None,
        "params": [("ParamEyeROpen", 0.02)],
        "duration": 0.35,
    },
    "tilt": {
        "expression": None,
        "params": [("ParamAngleZ", 0.75)],
        "duration": 2.5,
    },
}

# 表情参数映射
EXPRESSION_PARAMS = {
    "neutral": [],
    "star_eyes": [("Param107", 1)],
    "blush": [("Param111", 1)],
    "black_face": [("Param110", 1)],
    "cry": [("Param113", 1)],
    "dizzy": [("Param135", 1)],
    "facepalm": [("Param83", 1)],
}

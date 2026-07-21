"""小悠 v2 配置"""

import os
from pathlib import Path

# ── 路径 ──
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = str(DATA_DIR / "xiaoyou_v2.db")

# ── LLM ──
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
LLM_TIMEOUT = 30
LLM_MAX_RETRIES = 3

# ── 决策循环 ──
DECISION_INTERVAL_MIN = 10   # 秒
DECISION_INTERVAL_MAX = 25

# ── TTS ──
TTS_VOICE = "zh-CN-XiaoyiNeural"
TTS_CACHE_SIZE = 200

# ── 端口 ──
PORT = 8765

# ── 模式配置 ──
MODE_CONFIG = {
    "quiet": {
        "speak_prob": 0.03,
        "interval": (60, 180),
        "energy": 0.2,
        "max_actions": 1,
        "max_expressions_per_min": 1,
        "style": "寡言，简短，不主动。深夜模式。",
    },
    "balanced": {
        "speak_prob": 0.10,
        "interval": (30, 90),
        "energy": 0.5,
        "max_actions": 2,
        "max_expressions_per_min": 3,
        "style": "自然，适度互动。默认模式。",
    },
    "chatty": {
        "speak_prob": 0.40,
        "interval": (15, 45),
        "energy": 0.9,
        "max_actions": 3,
        "max_expressions_per_min": 5,
        "style": "活泼，话多，爱吐槽爱撒娇，主动找话题。动作丰富。",
    },
    "sweet": {
        "speak_prob": 0.08,
        "interval": (40, 120),
        "energy": 0.4,
        "max_actions": 1,
        "max_expressions_per_min": 2,
        "style": "害羞，软，用'人家'，偶尔星星眼。",
    },
}

# ── 深夜时间 ──
QUIET_HOURS_START = 22
QUIET_HOURS_END = 7

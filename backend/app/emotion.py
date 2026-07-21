"""小悠 v2 情感存储 — 纯数据层，不做 tick/衰减"""

import json
import time
from dataclasses import dataclass, field, asdict


@dataclass
class EmotionStore:
    joy: float = 0.5
    excitement: float = 0.3
    affection: float = 0.3
    fatigue: float = 0.0
    loneliness: float = 0.5
    curiosity: float = 0.5
    irritation: float = 0.0

    primary: str = "calm"
    intensity: float = 0.5
    last_interact: float = 0.0

    _expression_counts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        del d["_expression_counts"]
        return d

    def apply_delta(self, deltas: dict):
        """LLM 决策后调用。deltas 如 {"joy": +0.03, "fatigue": +0.01}"""
        for key, delta in deltas.items():
            if hasattr(self, key):
                current = getattr(self, key)
                setattr(self, key, max(0.0, min(1.0, current + delta)))
        self._update_primary()

    def mark_interaction(self, action: str = "user_message"):
        """标记互动时间"""
        self.last_interact = time.time()
        if action == "user_message":
            self.loneliness = max(0.0, self.loneliness - 0.05)
            self.affection = min(1.0, self.affection + 0.005)
        elif action == "poke":
            self.excitement = min(1.0, self.excitement + 0.05)
            self.affection = min(1.0, self.affection + 0.01)

    def hours_since_interact(self) -> float:
        if self.last_interact == 0:
            return 0
        return (time.time() - self.last_interact) / 3600

    def _update_primary(self):
        """更新主导情绪"""
        scores = {
            "happy": self.joy * 0.8 + self.excitement * 0.2,
            "tired": self.fatigue,
            "lonely": self.loneliness,
            "curious": self.curiosity,
            "irritated": self.irritation,
        }
        best = max(scores, key=scores.get)
        self.primary = best if scores[best] > 0.4 else "calm"
        self.intensity = max(scores.values())

    def save_to_db(self, db):
        db.execute(
            "INSERT OR REPLACE INTO state (key, value, updated_at) VALUES (?, ?, ?)",
            ("emotion", json.dumps(self.to_dict()), time.time()),
        )
        db.commit()

    @classmethod
    def load_from_db(cls, db) -> "EmotionStore":
        row = db.execute(
            "SELECT value FROM state WHERE key='emotion'"
        ).fetchone()
        if row:
            data = json.loads(row[0])
            data.pop("_expression_counts", None)
            data.pop("last_interact", None)
            return cls(**data)
        return cls()

"""小悠 v2 记忆系统 — 工作记忆 + 情节记忆 (SQLite FTS5)"""

import json
import sqlite3
import time
from collections import deque

from .config import DB_PATH

try:
    import jieba
    def _tokenize(text: str) -> str:
        return " ".join(jieba.cut(text))
except ImportError:
    def _tokenize(text: str) -> str:
        return text


class MemorySystem:
    def __init__(self):
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._migrate()
        self.working: deque[dict] = deque(maxlen=30)

    def _migrate(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at REAL NOT NULL,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                keywords TEXT NOT NULL DEFAULT '',
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS episodic_fts
                USING fts5(content, content=episodic, content_rowid=id);
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at REAL NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            );
        """)
        self.db.commit()

    # ── 工作记忆 ──
    def add_working(self, entry: dict):
        entry["_t"] = time.time()
        self.working.append(entry)

    # ── 情节记忆 ──
    def record_event(self, kind: str, content: str, importance: float = 0.5):
        now = time.time()
        keywords = _tokenize(content)
        self.db.execute(
            "INSERT INTO episodic (created_at, kind, content, keywords, importance) VALUES (?,?,?,?,?)",
            (now, kind, content, keywords, importance),
        )
        self.db.commit()
        self.add_working({"kind": kind, "content": content})

    def record_message(self, role: str, content: str):
        self.db.execute(
            "INSERT INTO messages (created_at, role, content) VALUES (?,?,?)",
            (time.time(), role, content),
        )
        self.db.commit()

    def recent_events(self, n: int = 20) -> list[dict]:
        rows = self.db.execute(
            "SELECT kind, content, created_at FROM episodic ORDER BY created_at DESC LIMIT ?", (n,)
        ).fetchall()
        return [{"kind": r["kind"], "content": r["content"], "time": r["created_at"]} for r in reversed(rows)]

    def recent_dialogue(self, n: int = 20) -> list[dict]:
        rows = self.db.execute(
            "SELECT role, content FROM messages ORDER BY created_at DESC LIMIT ?", (n,)
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def search_episodic(self, query: str, limit: int = 5) -> list[str]:
        keywords = _tokenize(query)
        if not keywords.strip():
            return []
        try:
            rows = self.db.execute(
                "SELECT content, importance FROM episodic WHERE episodic_fts MATCH ? "
                "ORDER BY importance DESC, created_at DESC LIMIT ?",
                (keywords, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS5 查询异常时降级为 LIKE
            rows = self.db.execute(
                "SELECT content, importance FROM episodic WHERE content LIKE ? "
                "ORDER BY importance DESC, created_at DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        for r in rows:
            self.db.execute(
                "UPDATE episodic SET access_count = access_count + 1 WHERE content = ?",
                (r["content"],),
            )
        self.db.commit()
        return [r["content"] for r in rows]

    def format_timeline(self, n: int = 20) -> str:
        events = self.recent_events(n)
        if not events:
            return "(这是故事的开端)"
        lines = []
        for e in events:
            t = time.localtime(e["time"])
            ts = f"{t.tm_hour:02d}:{t.tm_min:02d}"
            lines.append(f"[{ts}] {e['content']}")
        return "\n".join(lines)

    def build_context(self, user_query: str = None) -> str:
        """构建注入 LLM 的上下文字符串"""
        # 近期故事
        story = self.format_timeline(20)

        # 相关记忆
        if user_query:
            memories = self.search_episodic(user_query, limit=5)
        else:
            memories = self.search_episodic(
                " ".join([e["content"] for e in self.recent_events(5)]),
                limit=5,
            )
        memory_text = "\n".join(f"- {m}" for m in memories) if memories else "(暂无相关记忆)"

        return story, memory_text

    # ── 衰减清理 ──
    def purge_old(self):
        """每周调用一次"""
        self.db.execute(
            "DELETE FROM episodic WHERE importance < 0.3 AND created_at < ?",
            (time.time() - 7 * 86400,),
        )
        self.db.execute(
            "DELETE FROM episodic WHERE importance < 0.6 AND created_at < ?",
            (time.time() - 30 * 86400,),
        )
        self.db.execute("INSERT INTO episodic_fts(episodic_fts) VALUES('rebuild')")
        self.db.commit()

    def save_state(self, key: str, value: dict):
        self.db.execute(
            "INSERT OR REPLACE INTO state (key, value, updated_at) VALUES (?,?,?)",
            (key, json.dumps(value), time.time()),
        )
        self.db.commit()

    def load_state(self, key: str) -> dict | None:
        row = self.db.execute(
            "SELECT value FROM state WHERE key=?", (key,)
        ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def close(self):
        self.db.close()

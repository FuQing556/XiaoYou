"""小悠 v2 核心 — 三层决策循环 + 模式感知"""

import asyncio
import json
import random
import time
import uuid

from fastapi import WebSocket

from .config import (
    MODE_CONFIG,
    QUIET_HOURS_START,
    QUIET_HOURS_END,
    DECISION_INTERVAL_MIN,
    DECISION_INTERVAL_MAX,
)
from .emotion import EmotionStore
from .memory import MemorySystem
from .llm import LLMClient
from .perception import Perception
from .tts import TTSEngine
from .personality import (
    XIAOYOU_SYSTEM_PROMPT,
    DECISION_PROMPT,
    CHAT_PROMPT,
    ACTION_PARAMS,
    EXPRESSION_PARAMS,
)


class Brain:
    def __init__(self):
        self.memory = MemorySystem()
        self.emotion = EmotionStore.load_from_db(self.memory.db)
        self.llm = LLMClient()
        self.perception = Perception()
        self.tts = TTSEngine()

        self._connections: list[WebSocket] = []
        self._last_decision: float = 0.0
        self._pending_user_message: str | None = None
        self._pending_message_lock = asyncio.Lock()
        self._mode: str = "balanced"
        self._audio_store: dict[str, bytes] = {}
        self._task: asyncio.Task | None = None
        self._running = False
        self._perception_cooldown: dict[str, float] = {}
        self._expression_counts: dict[str, list[float]] = {}

    # ── 生命周期 ──
    async def start(self):
        self._running = True
        self._load_state()
        await self._send_greeting()
        self._task = asyncio.create_task(self._decision_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        self._save_state()
        self.memory.close()
        await self.llm.close()
        print("[Brain] stopped")

    def _load_state(self):
        saved_mode = self.memory.load_state("mode")
        if saved_mode and saved_mode.get("mode") in MODE_CONFIG:
            self._mode = saved_mode["mode"]
        self.emotion = EmotionStore.load_from_db(self.memory.db)

    def _save_state(self):
        self.memory.save_state("mode", {"mode": self._mode})
        self.emotion.save_to_db(self.memory.db)

    # ── WebSocket 连接管理 ──
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        # 推送当前状态
        await self._send_to(ws, {
            "type": "emotion",
            "data": self.emotion.to_dict(),
        })
        await self._send_to(ws, {
            "type": "mode",
            "mode": self._mode,
        })
        # 延迟发送问候（等前端完成初始化）
        asyncio.create_task(self._delayed_greet(ws))

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)

    async def _broadcast(self, data: dict):
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def _send_to(self, ws: WebSocket, data: dict):
        try:
            await ws.send_json(data)
        except Exception:
            pass

    # ── 用户消息入口 (Layer 1) ──
    async def on_user_message(self, text: str, ws: WebSocket | None = None):
        # Cancel 当前播放
        await self._broadcast({"type": "cancel"})

        self.emotion.mark_interaction("user_message")
        self.memory.record_message("user", text)
        self.memory.record_event("user_message", text, importance=0.6)

        # 打字指示
        await self._broadcast({"type": "thinking", "state": "start"})

        # 构建上下文
        story_ctx, mem_ctx = self.memory.build_context(text)
        now = time.localtime()
        mode_cfg = MODE_CONFIG[self._mode]

        prompt = CHAT_PROMPT.format(
            system_prompt=XIAOYOU_SYSTEM_PROMPT,
            story_context=story_ctx,
            memory_context=mem_ctx,
            current_time=f"{now.tm_hour:02d}:{now.tm_min:02d}",
            mode=self._mode,
            mode_style=mode_cfg["style"],
            screen_summary=self.perception.describe(),
            joy=self.emotion.joy,
            excitement=self.emotion.excitement,
            affection=self.emotion.affection,
            fatigue=self.emotion.fatigue,
            loneliness=self.emotion.loneliness,
            curiosity=self.emotion.curiosity,
            irritation=self.emotion.irritation,
            user_message=text,
        )

        decision = await self.llm.chat_json(XIAOYOU_SYSTEM_PROMPT, prompt)

        await self._broadcast({"type": "thinking", "state": "stop"})

        if decision:
            await self._execute_decision(decision, is_reply=True)
        else:
            # 降级回复
            fallback = {"text": "嗯？", "expression": "neutral", "actions": [], "emotion_update": {}}
            if random.random() < 0.5:
                fallback["actions"] = [{"name": "tilt", "at": 0}]
            await self._execute_decision(fallback, is_reply=True)

        self._save_state()

    # ── 交互事件入口 (Layer 1) ──
    async def on_interact(self, action: str):
        self.emotion.mark_interaction("poke")

        # 根据情绪选反应
        r = random.random()
        if r < 0.3:
            expr = "star_eyes" if self.emotion.joy > 0.5 else "blush"
            perform = {
                "expression": expr,
                "actions": [{"name": "playful", "at": 0}],
                "text": None,
            }
        elif r < 0.6:
            perform = {
                "expression": None,
                "actions": [{"name": "tilt", "at": 0}],
                "text": "嗯？" if self._mode == "chatty" else None,
            }
        else:
            perform = {
                "expression": "dizzy",
                "actions": [{"name": "scared", "at": 0}],
                "text": "呜哇！" if self._mode != "quiet" else None,
            }

        await self._execute_perform(perform)
        self.memory.record_event("interaction", f"主人戳了戳我 (action={action})", importance=0.3)

    # ── 模式切换 ──
    async def set_mode(self, mode: str):
        if mode in MODE_CONFIG:
            old = self._mode
            self._mode = mode
            self._save_state()
            print(f"[Brain] mode: {old} → {mode}")

            # 轻反馈
            name_map = {"quiet": "安静模式", "balanced": "日常模式", "chatty": "活泼模式", "sweet": "乖巧模式"}
            await self._broadcast({
                "type": "mode",
                "mode": self._mode,
                "label": name_map.get(mode, mode),
            })

    def cycle_mode(self):
        keys = list(MODE_CONFIG.keys())
        idx = keys.index(self._mode)
        next_mode = keys[(idx + 1) % len(keys)]
        asyncio.create_task(self.set_mode(next_mode))

    # ── 决策循环 (Layer 2 + 3) ──
    async def _decision_loop(self):
        """后台循环: 主动说话 + 环境触发"""
        await asyncio.sleep(5)  # 启动后等一会儿
        last_purge = time.time()

        while self._running:
            try:
                now = time.time()

                # 每日清理旧记忆
                if now - last_purge > 86400:
                    self.memory.purge_old()
                    last_purge = now
                hour = time.localtime().tm_hour

                # 深夜自动切 quiet
                if (hour >= QUIET_HOURS_START or hour < QUIET_HOURS_END):
                    if self._mode not in ("quiet",):
                        await self.set_mode("quiet")

                # 会议中切 quiet
                if self.perception.is_meeting and self._mode not in ("quiet",):
                    await self.set_mode("quiet")

                # 自适应间隔
                mode_cfg = MODE_CONFIG[self._mode]
                interval_min, interval_max = mode_cfg["interval"]
                hours_since = self.emotion.hours_since_interact()

                if hours_since < 1 / 60:  # <1分钟
                    interval = interval_min
                elif hours_since < 5 / 60:  # <5分钟
                    interval = interval_min
                elif hours_since < 0.5:
                    interval = (interval_min + interval_max) / 2 * 1.5
                else:
                    interval = interval_max * 2

                sleep_time = random.uniform(interval, interval * 1.3)
                await asyncio.sleep(sleep_time)

                if not self._running:
                    break

                # 检查是否有用户消息在处理
                async with self._pending_message_lock:
                    if self._pending_user_message:
                        continue

                # 概率判断
                if random.random() > mode_cfg["speak_prob"]:
                    continue

                # 更新感知
                await self.perception.update()

                # 屏幕冷却检查
                if not self._can_mention_screen():
                    continue

                # 构建 prompt 并决策
                story_ctx, mem_ctx = self.memory.build_context()
                now_ts = time.localtime()

                prompt = DECISION_PROMPT.format(
                    system_prompt=XIAOYOU_SYSTEM_PROMPT,
                    story_context=story_ctx,
                    memory_context=mem_ctx,
                    current_time=f"{now_ts.tm_hour:02d}:{now_ts.tm_min:02d}",
                    mode=self._mode,
                    mode_style=mode_cfg["style"],
                    screen_summary=self.perception.describe(),
                    joy=self.emotion.joy,
                    excitement=self.emotion.excitement,
                    affection=self.emotion.affection,
                    fatigue=self.emotion.fatigue,
                    loneliness=self.emotion.loneliness,
                    curiosity=self.emotion.curiosity,
                    irritation=self.emotion.irritation,
                    hours_since_interact=f"{hours_since:.1f}",
                )

                decision = await self.llm.decide(XIAOYOU_SYSTEM_PROMPT, prompt)

                if decision and decision.get("choice") in ("speak", "act", "react"):
                    await self._execute_decision(decision, is_reply=False)
                elif decision and decision.get("choice") == "think":
                    # 仅记录内心想法
                    inner = decision.get("inner_thought", "") or decision.get("text", "")
                    if inner:
                        self.memory.record_event("thought", inner, importance=0.2)
                        print(f"[Brain] thought: {inner[:80]}")

                self._last_decision = now

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Brain] loop error: {e}")
                await asyncio.sleep(5)

    def _can_mention_screen(self) -> bool:
        """屏幕话题冷却检查"""
        proc = self.perception.process_name
        if not proc:
            return True
        last = self._perception_cooldown.get(proc, 0)
        if time.time() - last < 3600:
            return False
        return True

    # ── 执行决策 ──
    async def _execute_decision(self, decision: dict, is_reply: bool = False):
        choice = decision.get("choice", "speak")
        text = decision.get("text", "")
        expression = decision.get("expression")
        actions = decision.get("actions", [])
        emotion_update = decision.get("emotion_update", {})
        inner = decision.get("inner_thought", "")

        # 应用情感更新
        if emotion_update:
            self.emotion.apply_delta(emotion_update)

        # 模式限制动作数量
        max_act = MODE_CONFIG[self._mode]["max_actions"]
        if len(actions) > max_act:
            actions = actions[:max_act]

        # 表情频率限制
        if expression and expression != "neutral":
            now = time.time()
            key = expression
            if key not in self._expression_counts:
                self._expression_counts[key] = []
            self._expression_counts[key] = [t for t in self._expression_counts[key] if now - t < 60]
            max_expr = MODE_CONFIG[self._mode]["max_expressions_per_min"]
            if len(self._expression_counts[key]) >= max_expr and is_reply:
                expression = "neutral"
            else:
                self._expression_counts[key].append(now)

        if choice == "speak":
            # TTS
            mood = "default"
            if self.emotion.excitement > 0.7:
                mood = "excited"
            elif self.emotion.joy < 0.2:
                mood = "calm"
            audio_bytes = await self.tts.speak(text, mood=mood)

            # 缓存音频
            audio_url = None
            if audio_bytes:
                audio_id = str(uuid.uuid4())[:8]
                self._audio_store[audio_id] = audio_bytes
                audio_url = f"http://127.0.0.1:8765/audio/{audio_id}"

            await self._broadcast_perform(
                text=text,
                expression=expression,
                actions=actions,
                audio_url=audio_url,
            )
            self.memory.record_message("assistant", text)
            self.memory.record_event("reply", text, importance=0.4)
            print(f"[Brain] speak: {text[:80]} | expression={expression} | audio={audio_url is not None}")

        elif choice == "act":
            await self._broadcast_perform(text=None, expression=expression, actions=actions, audio_url=None)
            self.memory.record_event("action", f"做了动作: {actions}", importance=0.2)

        elif choice == "react":
            await self._broadcast_perform(text=None, expression=expression, actions=[], audio_url=None)
            self.memory.record_event("reaction", f"表情: {expression}", importance=0.2)

        elif choice == "idle":
            pass  # 什么都不做

        if inner:
            self.memory.record_event("thought", inner, importance=0.2)

    async def _execute_perform(self, perform: dict):
        """执行交互触发的 perform，直接广播不录音"""
        text = perform.get("text")
        await self._broadcast_perform(
            text=text,
            expression=perform.get("expression"),
            actions=perform.get("actions", []),
            audio_url=None,
        )

    async def _broadcast_perform(self, text, expression, actions, audio_url):
        """构造 + 广播 perform 消息"""
        # 规范化 actions: 兼容字符串和对象格式
        normalized = []
        for a in (actions or []):
            if isinstance(a, str):
                normalized.append({"name": a, "at": 0})
            elif isinstance(a, dict) and "name" in a:
                normalized.append({"name": a["name"], "at": a.get("at", 0)})
        msg = {
            "type": "perform",
            "text": text,
            "expression": expression,
            "actions": normalized,
            "audio_url": audio_url,
        }
        await self._broadcast(msg)

    # ── 启动问候 ──
    async def _delayed_greet(self, ws: WebSocket):
        """首次连接时发送问候"""
        await asyncio.sleep(1.5)
        greeting = self._make_greeting()
        await self._send_to(ws, {
            "type": "perform",
            "text": greeting,
            "expression": None,
            "actions": [{"name": "playful", "at": 0}],
            "audio_url": None,
        })

    def _make_greeting(self) -> str:
        hour = time.localtime().tm_hour
        if hour < 6:    return "这么早……你是不睡觉的吗……"
        elif hour < 9:  return "早上好～新的一天开始啦。"
        elif hour < 12: return "上午好呀。"
        elif hour < 14: return "中午了……有点困呢……"
        elif hour < 18: return "下午好～"
        elif hour < 22: return "晚上好！"
        else:           return "这么晚还不睡呀……"

    async def _send_greeting(self):
        """启动时广播问候（所有已连接客户端）"""
        greeting = self._make_greeting()
        await self._broadcast({
            "type": "perform",
            "text": greeting,
            "expression": None,
            "actions": [{"name": "sleepy" if 6 <= time.localtime().tm_hour < 9 or time.localtime().tm_hour >= 22 else "playful", "at": 0}],
            "audio_url": None,
        })

    # ── 音频访问 ──
    def get_audio(self, audio_id: str) -> bytes | None:
        return self._audio_store.get(audio_id)

    # ── 状态快照 ──
    def get_state(self) -> dict:
        return {
            "mode": self._mode,
            "emotion": self.emotion.to_dict(),
            "connections": len(self._connections),
            "last_decision": self._last_decision,
        }


# 全局单例
brain = Brain()

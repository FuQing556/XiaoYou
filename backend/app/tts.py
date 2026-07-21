"""小悠 v2 TTS — Edge TTS 晓伊 + 内存缓存 + 流式流水线"""

import asyncio
import hashlib
import time
import io
import edge_tts

from .config import TTS_VOICE, TTS_CACHE_SIZE


class TTSEngine:
    VOICE = TTS_VOICE
    _cache: dict[str, bytes] = {}
    _cache_queue: list[str] = []

    @property
    def available(self) -> bool:
        return True

    async def speak(self, text: str, mood: str = "default") -> bytes | None:
        """生成语音，返回 mp3 字节。失败返回 None。"""
        if not text or not text.strip():
            return None

        text = text.strip()[:400]  # 截断
        cache_key = hashlib.md5(f"{text}|{mood}".encode()).hexdigest()

        # 缓存命中
        if cache_key in self._cache:
            self._cache_queue.remove(cache_key)
            self._cache_queue.append(cache_key)
            return self._cache[cache_key]

        # 声线调制
        rate = "+15%"
        pitch = "+3Hz"
        if mood == "excited":
            rate, pitch = "+25%", "+5Hz"
        elif mood == "shy":
            rate, pitch = "-5%", "+1Hz"
        elif mood == "calm":
            rate, pitch = "-10%", "-2Hz"

        try:
            communicate = edge_tts.Communicate(
                text, self.VOICE, rate=rate, pitch=pitch
            )
            mp3_data = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_data.write(chunk["data"])
            result = mp3_data.getvalue()
            if len(result) < 100:
                return None
            self._cache_set(cache_key, result)
            return result
        except Exception as e:
            print(f"[TTS] error: {e}")
            return None

    def _cache_set(self, key: str, data: bytes):
        if key in self._cache:
            return
        self._cache[key] = data
        self._cache_queue.append(key)
        while len(self._cache_queue) > TTS_CACHE_SIZE:
            old = self._cache_queue.pop(0)
            self._cache.pop(old, None)

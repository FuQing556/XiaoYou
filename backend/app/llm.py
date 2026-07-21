"""小悠 v2 LLM 客户端 — DeepSeek 流式 + JSON 修复"""

import json
import re
import asyncio
import httpx

from .config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    LLM_TIMEOUT,
    LLM_MAX_RETRIES,
)


class LLMClient:
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=LLM_TIMEOUT)
        self._key = DEEPSEEK_API_KEY

    @property
    def available(self) -> bool:
        return bool(self._key)

    async def decide(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 400,
        temperature: float = 0.9,
    ) -> dict | None:
        """非流式请求，返回解析后的 JSON dict。失败返回 None。"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        for attempt in range(LLM_MAX_RETRIES):
            try:
                resp = await self._client.post(
                    f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": DEEPSEEK_MODEL,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": False,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return _parse_json(content)
                elif resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"[LLM] HTTP {resp.status_code}: {resp.text[:200]}")
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                print(f"[LLM] attempt {attempt+1}/{LLM_MAX_RETRIES}: {e}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"[LLM] unexpected: {e}")
                break

        return None

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.9,
    ) -> dict | None:
        """同 decide，别名用于对话场景"""
        return await self.decide(system_prompt, user_prompt, max_tokens, temperature)

    async def extract_memories(self, user_msg: str, reply: str) -> list[dict]:
        """异步提取记忆（备用，通常用规则提取）"""
        if not self.available:
            return []
        prompt = f"从以下对话提取事实。只返回JSON数组。\n用户: {user_msg}\n小悠: {reply}\n[{{\"type\":\"fact\",\"content\":\"...\",\"importance\":0.5}}]"
        result = await self.decide(
            "你是事实提取器。只返回JSON数组，不要其他文字。",
            prompt,
            max_tokens=200,
            temperature=0.3,
        )
        if isinstance(result, list):
            return result
        return []

    async def close(self):
        await self._client.aclose()


def _parse_json(text: str) -> dict | None:
    """JSON 修复层：剥离 markdown → 正则提取 → 修复常见错误 → 验证"""
    if not text:
        return None

    # 1. 剥离 markdown 代码块
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.replace("```", "")

    # 2. 提取第一个 {...}
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        print(f"[LLM] JSON parse: no braces found in: {text[:200]}")
        return None
    json_str = m.group(0)

    # 3. 修复常见错误
    json_str = json_str.replace("“", '"').replace("”", '"')  # 中文引号 → 英文
    json_str = json_str.replace("，", ",")  # 中文逗号 → 英文
    json_str = re.sub(r",\s*}", "}", json_str)   # 尾部逗号
    json_str = re.sub(r",\s*]", "]", json_str)
    json_str = json_str.replace("NaN", "null").replace("Infinity", "null")

    # 4. 解析
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[LLM] JSON decode error: {e} | text: {json_str[:200]}")
        return None

    # 5. 验证基本结构
    if not isinstance(result, dict):
        return None
    if "choice" not in result and "text" not in result:
        # 至少需要 choice 或 text 之一
        if "text" in result:
            result.setdefault("choice", "speak")
        else:
            return None

    return result

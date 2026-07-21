"""小悠 v2 屏幕感知 — Win32 窗口元数据采集"""

import time
import asyncio

try:
    import win32gui
    import win32process
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


class Perception:
    def __init__(self):
        self.window_title: str = ""
        self.process_name: str = ""
        self.idle_seconds: int = 0
        self.session_start: float = 0.0  # 当前窗口/进程的开始时间
        self._last_title: str = ""
        self._title_switch_time: float = 0.0
        self._last_active_time: float = time.time()

    async def update(self):
        """采集 Win32 元数据。每 5 秒调用一次。"""
        if not HAS_WIN32:
            self.window_title = "(Win32不可用)"
            self.process_name = "unknown"
            return

        try:
            hwnd = win32gui.GetForegroundWindow()
            self.window_title = win32gui.GetWindowText(hwnd) or "(无标题)"

            # 进程名
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                handle = win32api.OpenProcess(0x0400 | 0x0010, False, pid)
                self.process_name = win32process.GetModuleFileNameEx(handle, 0).split("\\")[-1]
            except Exception:
                self.process_name = "unknown"

            # 空闲检测
            self.idle_seconds = (win32api.GetTickCount() - win32api.GetLastInputInfo()) // 1000

            # 窗口切换检测
            if self.window_title != self._last_title:
                self._title_switch_time = time.time()
                self._last_title = self.window_title

            self.session_start = self._title_switch_time

        except Exception as e:
            print(f"[Perception] update error: {e}")

    def describe(self) -> str:
        """生成自然语言描述，供给 LLM"""
        if not self.process_name:
            return "屏幕: (无数据)"

        idle_str = ""
        if self.idle_seconds > 120:
            idle_str = f" | 已空闲 {self.idle_seconds // 60} 分钟"
        elif self.idle_seconds > 30:
            idle_str = " | 可能不在电脑前"

        duration_min = int((time.time() - self.session_start) / 60) if self.session_start else 0
        duration_str = f" | 已连续 {duration_min} 分钟" if duration_min > 0 else ""

        hour = time.localtime().tm_hour
        return f"窗口: {self.process_name} — {self.window_title[:40]}{duration_str}{idle_str} | 现在 {hour:02d}:{time.localtime().tm_min:02d}"

    @property
    def is_fullscreen(self) -> bool:
        """检测是否全屏应用"""
        if not HAS_WIN32 or not self.window_title:
            return False
        try:
            hwnd = win32gui.GetForegroundWindow()
            rect = win32gui.GetWindowRect(hwnd)
            screen_w = win32api.GetSystemMetrics(0)  # SM_CXSCREEN
            screen_h = win32api.GetSystemMetrics(1)  # SM_CYSCREEN
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            return w >= screen_w * 0.9 and h >= screen_h * 0.9
        except Exception:
            return False

    @property
    def is_meeting(self) -> bool:
        """检测是否在会议中"""
        meeting_keywords = ["zoom", "teams", "腾讯会议", "discord", "slack", "webex", "meet.google"]
        title_lower = self.window_title.lower()
        proc_lower = self.process_name.lower()
        return any(
            kw in title_lower or kw in proc_lower
            for kw in meeting_keywords
        )

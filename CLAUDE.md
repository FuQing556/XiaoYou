# 小悠 v2

Live2D 桌面猫娘。Electron 透明窗口 + PixiJS v7 + Cubism 5 Core + FastAPI + DeepSeek。

**v2 原则：前端零智能，后端单一决策路径，模块单向依赖。**

---

## 1. 启动

```
终端1: cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
终端2: npm start
```

双击 `start.bat` 一键启动。

---

## 2. 目录结构

```
xiaoyou_v2/
├── main.js                  # Electron 主进程 (窗口/快捷键/IPC)
├── preload.js               # IPC 桥接
├── package.json
├── start.bat
├── .env                     # DEEPSEEK_API_KEY
├── KEYBINDINGS.txt          # 快捷键参考
├── CLAUDE.md                # 本文件
├── frontend/
│   ├── renderer.html        # 纯渲染器 (~350行)
│   ├── calib.html           # 参数校准工具
│   └── lib/                 # Cubism5 + PixiJS v7 + pixi-live2d-display
├── backend/app/
│   ├── __init__.py
│   ├── main.py              # FastAPI + lifespan + 启动后台循环
│   ├── config.py            # 配置 + MODE_CONFIG
│   ├── memory.py            # MemorySystem (working + episodic + FTS5)
│   ├── emotion.py           # EmotionStore (纯数据, 无 tick)
│   ├── perception.py        # Win32 屏幕元数据采集
│   ├── llm.py               # DeepSeek 客户端 (流式 + JSON 修复)
│   ├── brain.py             # 三层决策循环 + 模式感知
│   ├── tts.py               # Edge TTS 晓伊 + 流式流水线 + 缓存
│   ├── personality.py       # System Prompt + 动作编目 + 决策模板
│   └── routes/
│       ├── __init__.py
│       ├── chat.py          # WebSocket /ws
│       └── panel.py         # REST /api/panel/* (状态查询)
└── model/                   # Live2D 悠小喵 (SDK 3.0, CDI3)
    ├── model.moc3
    ├── model.model3.json
    ├── model.cdi3.json      # 168 参数定义
    ├── model.physics3.json  # 47 组物理设置
    ├── exp/                 # 16 个表达式文件
    └── textures/
```

---

## 3. 架构

```
┌──────────────────────────────────────────────┐
│              LLM (DeepSeek)                   │
│              唯一大脑                          │
│     每次决策输出结构化 JSON，不做自由文本        │
└────────────────────┬─────────────────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│               Brain (brain.py)                │
│  三层决策循环 + 模式感知 + 上下文构建            │
│  接收: 用户消息 / 模式切换 / 环境事件            │
│  输出: perform 命令 (纯 JSON)                  │
└────────────────────┬─────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   WebSocket      TTS 音频     屏幕感知
   (前端命令)    (Edge TTS)   (Win32 元数据)
```

**核心原则**：
- 前端零智能：收到命令 → 播放 → 结束，不判断、不定时器、不循环
- 后端单一路径：所有决策走 `brain.py`，不搞多个入口
- 状态显式传递：不靠全局变量，模块间明确传参
- 模块单向依赖：config ← memory ← emotion ← llm ← brain ← routes/main

---

## 4. 模式系统

四种模式，轮切快捷键 `Ctrl+Shift+Y`：

| 模式 | speak_prob | 间隔 | 风格 |
|------|:---:|:---:|------|
| `quiet` 安静 | 3% | 60-180s | 寡言简短，动作轻柔。深夜自动切换 |
| `balanced` 日常 | 10% | 30-90s | 自然适度，有存在感不打扰。默认模式 |
| `chatty` 活泼 | 40% | 15-45s | 话多爱吐槽撒娇，主动找话题，动作丰富 |
| `sweet` 乖巧 | 8% | 40-120s | 害羞软萌，偶尔星星眼，用"人家" |

模式切换来源：
- 键盘快捷键 `Ctrl+Shift+Y`
- 自然语言 "小悠你安静点" → LLM 在 chat 回复里附带 mode_change
- 22:00-07:00 自动切 quiet（可被手动覆盖）
- 启动默认 balanced，手动切过则保持

---

## 5. 动画系统：双层架构

### System 1 — 持续动画层（每帧运行，不经 LLM）

覆盖头部、眼睛、眉毛、嘴巴、耳朵、尾巴的持续微动。
目标是"她在那里"的基础存在感。

**头部 (ParamAngleX/Y/Z)**：
- 三层叠加：缓慢呼吸感漂移 + 快速微调抖动 + 情绪调制振幅/频率
- 三个轴频率不成整数比（周期 15-22s），避免机械重复
- 情绪调制：兴奋→振幅×1.5/频率×1.3，疲劳→振幅×0.5/频率×0.6

**眼睛 (ParamEyeLOpen/ROpen, EyeBallX/Y, EyeLSmile/RSmile)**：
- 眨眼系统：正常(2-5s间隔) / 快速连眨 / 半眨眼(闭到0.3) / 不对称眨眼(像wink)
- 眼珠扫视(saccade)：跳跃-停顿-跳跃模式，停顿0.3-2s，0.02s瞬跳到新位置
- 微笑眯眼：眨眼时联动0.1-0.2，开心情绪持续0.2-0.4微眯
- 情绪调制：好奇→扫视频率↑，害羞→向下看，困→闭眼拉长

**眉毛 (ParamBrowLY/RY, BrowLForm/RForm)** — v1 完全没动：
- 说话时与嘴部联动微动，增强说话感
- 好奇→单边挑眉，困惑→皱眉，撒娇→内端上抬，惊讶→双眉抬高

**嘴巴 (ParamMouthOpenY, MouthForm)**：
- 微张呼吸联动，偶尔抿嘴，说话时配合 TTS 音频做嘴型同步

**耳朵 (Param8/27/28/30/31/45/50/51)** — v1 完全浪费：
- 环境响应(慢)：有声音→微转向声源，安静→随机微动
- 情绪表达(中)：开心→竖起，生气→飞机耳，好奇→一竖一平交替，伤心→耷拉
- 随机微动(快)：每3-8s触发抽动，模拟真猫耳朵快速微调
- **猫娘最重要的特征，不能浪费**

**尾巴 (Param_Angle_Rotation_0~16_ArtMesh212)** — 17节：
- 6种模式：慢摇(默认) / 快摇(开心) / 僵直(警惕) / 下垂(伤心) / 炸毛(惊吓) / 勾引(撒娇)
- 波浪传播：每节延迟0.03s，末节振幅最大
- 情绪调制切换模式

**身体 (ParamBodyAngleX/Y/Z)** — calib 后确认视觉有效再接入：
- 视觉不明显则不做，头部参数本身就能带动头发物理

### System 2 — 触发动作层（LLM 输出 → perform 命令）

#### 表情 (expression 字段，独立指定，4s 自动收回)

| expression | 参数 | 
|------------|------|
| `neutral` | (无) |
| `star_eyes` | Param107=1 |
| `blush` | Param111=1 |
| `black_face` | Param110=1 |
| `cry` | Param113=1 |
| `dizzy` | Param135=1 |
| `facepalm` | Param83=1 |

#### 复合动作 (actions 字段，LLM 主要接口，按情绪组织)

System Prompt 里只暴露这 10 个，让 LLM 容易选择：

| 动作 | 时机 | 组合内容 |
|------|------|---------|
| `excited` | 开心得意 | 星星眼+竖耳+快摇尾+身体微弹 |
| `shy` | 害羞 | 脸红+视线飘开+低头+耳朵半耷 |
| `proud` | 得意 | 抬头+眯眼+竖耳朵+尾巴尖画圈 |
| `curious` | 好奇 | 歪头+睁大眼+单耳竖+前倾+尾巴慢摇 |
| `scared` | 吓到 | 晕晕眼+飞机耳+身体后仰+尾巴僵直 |
| `angry` | 生气 | 黑脸+飞机耳+甩尾巴+瞪眼 |
| `sad` | 难过 | 哭哭+耳朵耷拉+低头+尾巴下垂 |
| `sleepy` | 困了 | 慢闭眼+打哈欠+耳朵下垂+身体瘫软 |
| `thinking` | 思考 | 歪头+眼珠向上+眉毛微皱 |
| `surprised` | 惊讶 | 睁大眼+张嘴+耳朵竖+身体微后仰 |
| `playful` | 撒娇 | 星星眼+前倾+竖耳朵+尾巴快摇+wink |

#### 独立点缀动作（可叠加在复合动作之上）

`nod`(点头) `shake`(摇头) `wink`(单眼眨) `tilt`(歪头)

#### 后端注入动作 (brain.py 自动追加，不经过 LLM)

`user_click` → 触发被戳反应，根据情绪和模式自动选动作+表情

#### 动作规则（防止抽搐）

- 同类参数的动作必须间隔 ≥ 0.3s
- 同一时刻最多 3 个动作同时启动
- 总动作链不超过 5s
- 所有参数过渡使用缓动（快闭慢开/弹性/平滑），不瞬间跳变
- 表情切换 0.3s 缓动
- 动作幅度拉满：头部 ±30°，歪头 ±30°，闭眼到 0.01

---

## 6. 记忆系统

### 两级架构

```
工作记忆 (working):  最近 30 条，纯内存 dict，当前对话上下文
情节记忆 (episodic):  SQLite + FTS5 全文索引，跨会话保留
```

### 数据库设计

```sql
CREATE TABLE episodic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    kind TEXT NOT NULL,          -- 'chat_summary'|'user_fact'|'event'
    content TEXT NOT NULL,
    keywords TEXT NOT NULL,      -- jieba 分词，空格分隔
    importance REAL DEFAULT 0.5,
    access_count INTEGER DEFAULT 0
);
CREATE VIRTUAL TABLE episodic_fts USING fts5(content, content=episodic, content_rowid=id);
```

### 写入规则（规则驱动，不用 LLM 提取）

```
1. 每轮对话 → 压缩成一句话摘要 (importance=0.3)
2. 用户说了"我xxx" → 存用户事实 (importance=0.7)
3. 用户 >1h 后重新互动 → 存事件 (importance=0.5)
4. 用户说"记得/别忘了" → importance=0.9
5. 用户戳 5+ 次 → 存互动事件 (importance=0.4)
```

### 检索

Layer 1: 工作记忆 (30条, 内存, O(1))
Layer 2: FTS5 关键词搜索 (jieba 分词取前10词, 按 importance 排序)

### 衰减

- importance < 0.3 → 7天后清理
- importance < 0.6 → 30天后清理
- importance ≥ 0.7 → 永久保留

---

## 7. 屏幕感知

### 设计原则：感知 ≠ 触发

感知层每 5s 更新元数据，始终注入 LLM prompt。
触发决策由 brain 的概率系统控制，不是每次窗口变化都说话。

### 数据结构

```python
{
    "window_title": "project/main.ts — VS Code",
    "process_name": "Code.exe",
    "idle_seconds": 23,
    "session_duration": 38 * 60,
    "hour": 15,
    "screen_summary": "正在用 VS Code 编辑 main.ts，已连续 38 分钟"
}
```

### 冷却机制

- 同一应用 1h 内不重复评论
- 窗口切换后延迟 60-90s 再允许评论
- 深夜(22-07)完全不评论屏幕
- chatty 模式允许更积极的屏幕评论

### 自动静默场景

- 全屏应用 → 不打扰
- Zoom/Teams/腾讯会议 → 自动切 quiet
- 任务管理器 → 不评论

---

## 8. LLM 集成

### DeepSeek 客户端

- 模型: `deepseek-chat`
- 流式请求 (stream=True)，句子检测器触发 TTS 流水线
- 超时 30s，最多 3 次重试
- 失败降级：API 调用失败 → 返回 None → brain 用本地规则选 fallback

### JSON 修复层

```python
# 处理 LLM 输出常见错误
1. 剥离 markdown 代码块 (```json ... ```)
2. 正则提取第一个 {...}
3. 修复: 尾部逗号、中文引号→英文、NaN/Infinity→null
4. 验证必填字段
5. 失败 → 返回 None (不返回空 dict!)
```

### 决策 Prompt 结构

```
[System Prompt — 角色定义 + 动作编目]

[最近的故事 — 最近 20 条事件时间线]
[你记得的事 — 情节记忆检索结果]
[此刻 — 时间/模式/屏幕/情感/距离上次互动/窗口时长]
[用户消息 — 如果有]

选择: speak / think / act / react / idle
输出 JSON: {choice, text, expression, actions, emotion_update, inner_thought, reason}
```

---

## 9. TTS 系统

### 引擎

首选用 Edge TTS `zh-CN-XiaoyiNeural`（比晓晓更少女、更清脆）。
备选本地 CosyVoice/GPT-SoVITS（需 GPU，轻薄本暂不考虑）。

### 延迟优化：流式流水线

```
LLM 开始输出 → 第一个完整句子 → 立即调 TTS → 播放
              └── 0.5-2s ──┘└── 1-2s ──┘
总延迟目标: 1.5-4s (v1 是 7-13s)
```

- 句子检测：遇到 。！？.!? 即触发
- TTS 超时 3s → 跳过该句
- 结果缓存在内存 (hash(text+mood) 为 key)
- 新消息到达 → cancel 当前语音

### 声线调制

```python
"default":   {"voice":"zh-CN-XiaoyiNeural", "rate":"+15%", "pitch":"+3Hz"}
"excited":   {"voice":"zh-CN-XiaoyiNeural", "rate":"+25%", "pitch":"+5Hz"}
"shy":       {"voice":"zh-CN-XiaoyiNeural", "rate":"-5%",  "pitch":"+1Hz"}
```

---

## 10. WebSocket 协议

### 前端 → 后端

```json
{"type": "chat",      "content": "你好"}
{"type": "interact",  "action": "poke"|"click"}
{"type": "mode",      "mode": "chatty"}
```

### 后端 → 前端

```json
// 执行命令（核心）
{"type":"perform", "text":"...", "expression":"star_eyes", "actions":[{"name":"excited","at":0},{"name":"nod","at":1.2}], "audio_url":"http://127.0.0.1:8765/audio/abc123.mp3"}

// 中断（用户发新消息时）
{"type":"cancel"}

// 打字指示
{"type":"thinking", "state":"start"|"stop"}

// 情绪同步（面板用）
{"type":"emotion", "data":{...}}

// 纯音频（主动说话）
{"type":"audio", "url":"..."}
```

---

## 11. 前端渲染器

### 状态

- `activeExpression` + `expressionTimer`
- `actionQueue`: [{name, at, params, duration, easing}]
- `mouthUntil`: TTS 播放截止时间
- `animTime`: 累计秒数
- `currentAudio`: 当前播放的 Audio 元素

### 每帧循环

```
1. applySystem1_Head()      → 三层头部漂移
2. applySystem1_Blink()     → 眨眼 (含半眨/连眨)
3. applySystem1_EyeGaze()   → 眼珠扫视 (saccade 模式)
4. applySystem1_Brow()      → 眉毛联动 (说话/情绪)
5. applySystem1_Mouth()     → 微张呼吸 / TTS 嘴型
6. applySystem1_Ears()      → 耳朵三层 (环境/情绪/微动)
7. applySystem1_Tail()      → 尾巴模式 (6种)
8. applySystem2_Actions()   → 覆盖上述参数 (System 2 优先)
9. applyExpression()        → 表情参数 (缓动 0.3s)
10. Cubism SDK 更新 + Physics
```

### perform(cmd) 处理

```
1. cmd.expression → 设置表情, 4s 后自动清除
2. cmd.actions → 展开为基元动作, 加入 actionQueue (按 at 延迟)
3. cmd.text → 显示气泡
4. cmd.audio_url → 播放音频, 驱动 mouthUntil
5. actionQueue 排序, 同参数动作检查间隔 ≥ 0.3s
```

### cancel() 处理

```
1. 清空 actionQueue
2. 清除 expression (恢复到 neutral)
3. stop + 移除 currentAudio
4. 隐藏气泡
```

---

## 12. 快捷键

详见 `KEYBINDINGS.txt`。

```
Ctrl+Shift+Y    切换模式
Ctrl+Shift+H    隐藏/显示
Ctrl+Shift+M    静音
Ctrl+Shift+↑/↓  缩放 (0.6/0.8/1.0/1.2/1.5/2.0)
Ctrl+Shift+←/→  模式导航
Ctrl+Shift+D    诊断浮层
Ctrl+Shift+R    重载模型
Ctrl+Shift+Q    退出
```

---

## 13. 窗口常量

- 尺寸: 500×620 (基准，缩放时等比变化)
- 模型 scale: 0.0647 × 缩放系数
- 模型锚点: (0.5, 0), 位置: (250, 120)
- 气泡: bottom:500px
- 任务栏: alwaysOnTop 但低于任务栏层级；初始位置避开任务栏
- 任务栏检测: Electron workArea vs bounds 差值

---

## 14. 缩放系统

- 6 档: 0.6/0.8/1.0/1.2/1.5/2.0
- 同步调整: 窗口尺寸、模型 scale、气泡字号(最大24px)、气泡位置
- 步进切换，不连续缩放
- 偏好存入 SQLite state 表

---

## 15. 情感引擎

7 维纯数据存储，不做自动衰减。LLM 在每次决策时自主更新。

| 维度 | 范围 | 说明 |
|------|:---:|------|
| joy | 0-1 | 愉悦 |
| excitement | 0-1 | 兴奋 |
| affection | 0-1 | 好感 |
| fatigue | 0-1 | 疲劳 |
| loneliness | 0-1 | 孤独 |
| curiosity | 0-1 | 好奇 |
| irritation | 0-1 | 烦躁 |

- 启动时从 SQLite state 表恢复
- LLM 决策中输出 `emotion_update: {joy: +0.05, fatigue: +0.02}`
- 关闭时保存
- 情绪值影响 System 1 动画层的振幅/频率/模式选择

---

## 16. 实现顺序

### Step 0: calib.html 参数校准
1. 放好 Live2D 模型和 lib
2. 最简 HTML: 加载模型 + 滑块控制参数
3. 逐个验证: ParamAngleX/Z/Y, ParamMouthOpenY, ParamEyeLOpen/ROpen,
   ParamEyeBallX/Y, ParamBrowLY/RY, 耳朵组, 尾巴组, VB组
4. 确认有效值域（角度参数 0→1 对应 -30°→+30°）
5. 记录不可用参数到文档

### Step 1: 后端基础
1. config.py + MODE_CONFIG
2. memory.py (Database + MemorySystem + FTS5)
3. emotion.py (EmotionStore)
4. personality.py (System Prompt + 动作编目 + 决策模板)
5. 逐个 import 测试

### Step 2: 后端核心
1. llm.py → 用测试脚本验证流式 JSON 输出 + JSON 修复层
2. perception.py → 验证 Win32 数据采集
3. brain.py → Mock WebSocket 测试完整决策流程
4. tts.py → 验证晓伊语音生成 + 缓存

### Step 3: 后端路由
1. chat.py → WebSocket 端点
2. panel.py → REST API
3. main.py → FastAPI + lifespan
4. uvicorn 启动, Python 脚本测试 WebSocket 全链路

### Step 4: 前端
1. renderer.html (~350行 纯播放引擎)
2. 浏览器测试: WebSocket + perform 命令响应
3. 确认 System1 动画 (头/眼/眉/耳/尾) + System2 动作 + 表情 + 音频

### Step 5: Electron 集成
1. main.js + preload.js (全局快捷键 + 缩放 + 窗口定位)
2. package.json + start.bat
3. 双击启动 → 全链路验证

### Step 6: 打磨
1. 启动问候（基于时间: "早上好～"/"这么晚还不睡？"）
2. 优雅退出（Ctrl+C → 保存状态 → 说再见 → 关闭）
3. 交互反馈（戳一戳/点击 → 反应动作）
4. 深夜安静模式自动切换

---

## 17. 关键决策记录

| # | 决策 | 理由 |
|---|------|------|
| 1 | SQLite FTS5 替代向量DB | 单用户场景不需要语义向量，关键词搜索够用 |
| 2 | 情感不作自动衰减 | LLM 常识判断比数学公式更自然 |
| 3 | 前端零智能 | v1 前端散落判断逻辑，难以调试 |
| 4 | 复合动作作为 LLM 主接口 | 10 个情境动作比 40 个参数动作更容易被 LLM 使用 |
| 5 | 身体参数不主动控制 | 实测视觉不明显，头部参数本身驱动头发物理 |
| 6 | 耳尾必须动 | v1 浪费了猫娘最核心的特征参数 |
| 7 | 幅度拉满不扭捏 | 头部 ±30°，不怕动作大 |
| 8 | 流式 TTS 流水线 | 目标延迟 <4s vs v1 7-13s |
| 9 | 晓伊替代晓晓 | 声线更少女更清脆 |
| 10 | 无托盘图标 | 纯快捷键操作，减少复杂度 |
| 11 | 无控制面板 | 快捷键 + 状态查询 API 替代 |

---

## 18. 模型参数速查

### 九轴 (0~1, 0.5=中性, 0↔1 对应约 ±30°)
ParamAngleX(左右转) ParamAngleY(上下转) ParamAngleZ(歪头) ParamAngleY2(前倾)
ParamBodyAngleX/Y/Z(身体, 视觉不明显)

### 眼睛
ParamEyeBallX/Y(眼珠) ParamEyeLOpen/ROpen(开闭) ParamEyeLSmile/RSmile(眯眼)
ParamBrowLY/RY(眉毛上下) ParamBrowLForm/RForm(眉毛变形)

### 嘴
ParamMouthOpenY(开闭) ParamMouthForm(变形)

### 表情切换 (0/1)
Param107(星星眼) Param111(脸红) Param110(黑脸) Param113(哭哭) Param135(晕晕眼) Param83(扶脸) Param54(流泪)

### 耳朵 (0-1)
Param8(L表情) Param27(L开闭) Param28(L1) Param30(L2)
Param31(R表情) Param45(R开闭) Param50(R1) Param51(R2)

### 尾巴 (17节骨骼旋转)
Param_Angle_Rotation_0~16_ArtMesh212

### 部件开关 (0/1)
Param85(水印) Param38(外套) Param55(帽子) Param52(耳朵) Param53(发夹)

### VB 参数 (部分，需 calib 验证)
ParamCheekPuff(鼓脸) ParamEyeSquint(眯眼) ParamMouthShrug ParamJawOpen ParamMouthPuckerWiden

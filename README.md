# JPL ASTRA - 实时语音转录 Demo

基于 [Fast-Powerful-Whisper-AI-Services-API](https://github.com/Evil0ctal/Fast-Powerful-Whisper-AI-Services-API) 扩展的实时语音转文字 demo，用于 ASTRA 项目的 AI/STT 模块。

---

## 一、已完成功能

| 功能 | 说明 |
|------|------|
| **实时 STT Demo** | 麦克风录音 + VAD 分段 + Whisper 转录，静音约 1.5s 触发一次 |
| **幻觉过滤** | 基于 `no_speech_prob`、`avg_logprob` 的置信度过滤，辅以短文本短语兜底 |
| **服务端过滤** | 幻觉/噪音不写入有效笔记，数据库保持干净 |
| **笔记导出** | 按时间戳导出，支持按日期筛选、按任务/按 segment 两种模式 |
| **文件级 Demo** | `demo_astra.py` 上传音频获取 ASTRA 格式结果 |

---

## 二、工作流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  麦克风录音  │ ──► │  VAD 分段   │ ──► │ 静音 1.5s   │
│ sounddevice │     │ webrtcvad   │     │ 触发转录     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  导出笔记   │ ◄── │  数据库     │ ◄── │ Whisper API │
│export_notes│     │ SQLite      │     │ 转录+过滤    │
└─────────────┘     └─────────────┘     └─────────────┘
```

**流程说明：**
1. `realtime_demo.py` 持续录音，VAD 检测语音/静音
2. 静音达到阈值（默认 1.5s）→ 将当前音频保存为 WAV
3. POST 到 Whisper API → 轮询结果
4. 客户端 + 服务端双重幻觉过滤
5. 有效转录存入数据库（`created_at` 为时间戳）
6. `export_notes.py` 按时间/日期导出为 Markdown 或 TXT

---

## 三、新增/修改文件

| 文件 | 说明 |
|------|------|
| `realtime_demo.py` | 实时 STT demo，麦克风 + VAD + 调用 API |
| `export_notes.py` | 从数据库导出笔记，支持日期筛选 |
| `app/utils/hallucination_filter.py` | 幻觉过滤逻辑（置信度 + 短语兜底） |
| `app/processors/task_processor.py` | 修改：转录后过滤幻觉，不存噪音 |
| `config/settings.py` | 新增 `FILTER_HALLUCINATION` 配置 |
| `demo_astra.py` | 文件级 demo，返回 ASTRA 格式 |
| `requirements-realtime.txt` | 实时 demo 额外依赖 |

---

## 四、快速开始

### 1. 安装依赖

```bash
# 主项目
pip install -r requirements.txt

# 实时 demo 额外依赖
pip install -r requirements-realtime.txt
```

### 2. 启动 Whisper API

```bash
python start.py
# 或指定端口（如 80 需 root）：PORT=8000 python start.py
```

### 3. 运行实时 Demo

```bash
python realtime_demo.py --api-url http://127.0.0.1:8000
```

可选参数：`--silence-sec`、`--min-speech-sec`、`--debug`

### 4. 导出笔记

```bash
# 导出全部
python export_notes.py --output notes.md

# 导出某一天
python export_notes.py --date 2024-02-18 -o notes_0218.md

# 按 segment 导出
python export_notes.py --by-segment --format txt -o notes.txt
```

---

## 五、幻觉过滤规则

- **置信度**：`no_speech_prob > 0.4` 或 `avg_logprob < -0.5` → 过滤
- **短语兜底**：仅对长度 ≤ 25 字符的 transcript，若匹配已知幻觉短语则过滤
- **提示**：过滤时显示 `(noise / no actual content)`

---

## 六、与 Backend 对接

- API 合约：`/api/sessions/{sid}/stt/tasks` 注册任务，`PUT` 更新 transcript
- ASTRA 格式：`format=astra` 返回简化 JSON（session_id, segments, timestamp）
- 当前 demo 直接调用 Whisper API，后续可对接 Backend 的 STT 路由

---

## 七、依赖

- **主项目**：FastAPI、faster-whisper、SQLite、httpx 等
- **实时 demo**：sounddevice、webrtcvad、numpy

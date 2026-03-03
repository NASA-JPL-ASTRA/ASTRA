# ASTRA Collaboration Workflow

> Guide for the Frontend, Backend, and Model (AI/Data) teams.
[English](#english) | [中文](#中文)

---
---
<a id="english"></a>
## 1. Team Responsibilities

### Frontend Team

- Capture audio from browser microphone (PCM 16kHz mono)
- Send audio chunks to backend via `/ws/transcribe`
- Display live transcriptions and structured notes in real-time
- Allow operators to edit AI-generated notes
- Manage session lifecycle (create / pause / resume / end)
- Export session notes (Markdown / JSON)

### Backend Team

- Implement `/ws/transcribe` WebSocket endpoint for audio ingestion
- Route audio chunks to Model team's Whisper service
- Manage REST APIs: sessions, notes, telemetry, STT tasks
- Broadcast real-time events via `/ws/sessions/{sid}`
- Persist data (currently in-memory, migrate to PostgreSQL)
- Handle error codes, logging, and observability

### Model / AI Team

- Run Whisper model inference (speech → text)
- Return partial + final transcription results
- Perform speaker diarization (who is speaking)
- Generate structured notes from raw transcripts
- Post results back to backend via REST API
- Optimize for latency (target < 3s end-to-end)

---

## 2. Architecture Overview

```text
┌──────────────┐       WebSocket (audio)         ┌──────────────┐       gRPC / HTTP         ┌──────────────┐
│              │  ──── /ws/transcribe ────────►  │              │  ───────────────────────► │              │
│   Frontend   │                                 │   Backend    │                           │  Model / AI  │
│  (React/TS)  │  ◄─── transcription results ──  │  (FastAPI)   │  ◄── transcript + notes ─ │  (Whisper)   │
│              │                                 │              │                           │              │
│              │  ──── REST /api/* ───────────►  │              │                           │              │
│              │  ◄─── JSON responses ─────────  │              │                           │              │
│              │                                 │              │                           │              │
│              │  ◄═══ /ws/sessions/{sid} ══════ │              │                           │              │
│              │       (real-time events)        │              │                           │              │
└──────────────┘                                 └──────────────┘                           └──────────────┘
   Port 5173                                       Port 8000
```

---

## 3. Data Flow

### 3.1 Real-time Transcription

1. Frontend captures mic audio (PCM16, 16kHz, mono, ~3s chunks)
2. Frontend sends audio via `/ws/transcribe` (binary frames)
3. Backend receives audio, forwards to Model service
4. Model runs Whisper inference, returns transcript
5. Backend sends transcript back to Frontend via `/ws/transcribe`
6. Frontend displays text in real-time (partial → final)

### 3.2 Structured Note Generation

1. Model receives final transcript
2. Model generates structured note (category, tags, telemetry ref)
3. Model calls `POST /api/sessions/{sid}/notes`
4. Backend stores note, broadcasts `note.created` via WebSocket
5. Frontend receives event, displays note in real-time

---

## 4. API Endpoints Summary

### REST APIs

| Method | Endpoint | Owner | Description |
|--------|----------|-------|-------------|
| POST | `/api/sessions` | Backend | Create session |
| GET | `/api/sessions` | Backend | List sessions |
| GET | `/api/sessions/{sid}` | Backend | Get session detail |
| PATCH | `/api/sessions/{sid}` | Backend | Update session |
| POST | `/api/sessions/{sid}/notes` | Backend + Model | Create note |
| GET | `/api/sessions/{sid}/notes` | Backend | List notes |
| PUT | `/api/sessions/{sid}/notes/{id}` | Backend | Edit note |
| DELETE | `/api/sessions/{sid}/notes/{id}` | Backend | Delete note |
| GET | `/api/sessions/{sid}/notes/export` | Backend | Export notes |
| POST | `/api/sessions/{sid}/telemetry` | Backend | Ingest telemetry |
| GET | `/api/sessions/{sid}/telemetry` | Backend | Query telemetry |
| POST | `/api/sessions/{sid}/stt/tasks` | Backend + Model | Register STT task |
| PUT | `/api/sessions/{sid}/stt/tasks/{tid}` | Backend + Model | Update STT result |

### WebSocket Endpoints

| Endpoint | Direction | Description |
|----------|-----------|-------------|
| `/ws/transcribe` | Frontend ↔ Backend | Audio upload + transcription results |
| `/ws/sessions/{sid}` | Backend → Frontend | Real-time event broadcast |

---

## 5. WebSocket Event Types

| Event | Trigger | Description |
|-------|---------|-------------|
| `note.created` | Backend (after Model POST) | New note added |
| `note.updated` | Backend (after Frontend PUT) | Note edited |
| `note.deleted` | Backend (after Frontend DELETE) | Note removed |
| `stt.task.created` | Backend (after Model POST) | STT task registered |
| `stt.task.done` | Backend (after Model PUT) | Transcription complete |
| `error.occurred` | Backend | Error broadcast |

---

## 6. Integration Workflow

### Phase 1: Independent Development

| Team | Task |
|------|------|
| Frontend | Build UI; implement mic capture + PCM chunking |
| Backend | Implement REST APIs + session WebSocket with in-memory DB |
| Model | Train/fine-tune Whisper; build inference service; test with sample audio |

### Phase 2: Pair Integration

| Integration | Steps |
|-------------|-------|
| Frontend ↔ Backend | 1. Start backend on port 8000<br>2. Configure `frontend/.env.local` with backend URL<br>3. Test session CRUD + WebSocket connection<br>4. Verify event broadcast works |
| Backend ↔ Model | 1. Model calls `POST /stt/tasks` to register task<br>2. Model calls `PUT /stt/tasks/{tid}` with transcript<br>3. Verify `stt.task.done` event broadcasts |
| Frontend ↔ Model | (Indirect via Backend) |

### Phase 3: End-to-End

1. Frontend starts recording → creates session → connects WebSocket
2. Frontend sends audio chunks to `/ws/transcribe`
3. Backend forwards to Model → Model returns transcript
4. Backend broadcasts transcript to Frontend via WebSocket
5. Model generates structured note → `POST /notes` → broadcast
6. Frontend displays transcription + note in real-time
7. Operator edits note → `PUT /notes` → broadcast update
8. Frontend stops recording → `PATCH` session status=ended

---

## 7. Development Environment

### Start Backend

```bash
cd backend
source ../astra/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### Start Frontend

```bash
cd frontend
npm install
```

After `npm install`, create (or verify) the environment config file `frontend/.env.local`:

```env
# Backend REST API base URL
VITE_API_URL=http://localhost:8000/api

# Session-scoped WebSocket base URL (append /{sessionId})
VITE_SESSION_WS_URL=ws://localhost:8000/ws/sessions
```

> **Note**: If the backend is running on a different host or port, update the URLs above accordingly.

Then start the dev server:

```bash
npm run dev
# UI: http://localhost:5173
```

> **Important**: The backend must be running before you start the frontend. Otherwise session creation and WebSocket connections will fail.

---

## 8. Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Frontend UI | ✅ Done | Dashboard, Session, History, Detail pages |
| Mic capture + PCM chunking | ✅ Done | Real getUserMedia, 16kHz Int16, 3s chunks |
| Real audio level visualization | ✅ Done | AnalyserNode RMS |
| Backend REST APIs | ✅ Done | Sessions, Notes, Telemetry, STT Tasks |
| Backend `/ws/sessions/{sid}` | ✅ Done | Event broadcast working |
| Backend `/ws/transcribe` | ❌ Not started | Needs implementation |
| Whisper inference service | ❌ Not started | Model team responsibility |
| Structured note generation | ❌ Not started | Model team responsibility |
| PostgreSQL migration | ❌ Not started | Currently in-memory |

---

## 9. Communication Rules

- **API changes**: Any change to request/response format must be proposed, reviewed by all 3 teams, and documented in `API_CONTRACT.md` before implementation.
- **Breaking changes**: Must bump major version; provide migration guide and 1-week deprecation period.
- **New fields**: Adding optional fields is a non-breaking minor change; no review needed.
- **Testing**: Each team writes tests for their own endpoints; integration tests are shared.
- **Bug reports**: File GitHub issue with steps to reproduce, expected vs actual behavior, and logs/screenshots.

---

## 10. Key File Locations

| File | Purpose |
|------|---------|
| `frontend/src/hooks/useWhisper.ts` | Mic capture + audio chunking logic |
| `frontend/src/services/api.ts` | HTTP request functions |
| `frontend/src/services/sessionWs.ts` | Session WebSocket client |
| `frontend/src/store/useStore.ts` | Global state management |
| `frontend/API_CONTRACT.md` | API contract specification |
| `backend/app/main.py` | Backend entry point |
| `backend/app/routes/sessions.py` | Session CRUD endpoints |
| `backend/app/routes/notes.py` | Notes CRUD + export |
| `backend/app/routes/stt.py` | STT task management |
| `backend/app/routes/websocket.py` | Session WebSocket endpoint |
| `backend/app/ws_manager.py` | WebSocket broadcast manager |
| `backend/app/schemas/schemas.py` | Pydantic data models |

---
---
<a id="中文"></a>
# ASTRA 三方协作流程

> 前端、后端、模型（AI/数据）三方协作指南。

---

## 1. 团队职责

### 前端团队

- 通过浏览器麦克风采集音频（PCM 16kHz 单声道）
- 通过 `/ws/transcribe` 将音频块发送给后端
- 实时展示转写文字和结构化笔记
- 允许操作员编辑 AI 生成的笔记
- 管理会话生命周期（创建/暂停/恢复/结束）
- 导出会话笔记（Markdown / JSON）

### 后端团队

- 实现 `/ws/transcribe` WebSocket 端点以接收音频
- 将音频块转发给模型团队的 Whisper 服务
- 管理 REST API：会话、笔记、遥测、STT 任务
- 通过 `/ws/sessions/{sid}` 广播实时事件
- 持久化数据（当前内存存储，后续迁移到 PostgreSQL）
- 处理错误码、日志和可观测性

### 模型/AI 团队

- 运行 Whisper 模型推理（语音 → 文字）
- 返回 partial（临时）+ final（最终）转写结果
- 执行说话人分离（判断谁在说话）
- 从原始转写文本生成结构化笔记
- 通过 REST API 将结果回写后端
- 优化延迟（目标端到端 < 3 秒）

---

## 2. 架构概览

```text
┌──────────────┐     WebSocket（音频）            ┌──────────────┐      gRPC / HTTP          ┌──────────────┐
│              │  ──── /ws/transcribe ────────►  │              │  ───────────────────────► │              │
│     前端      │                                 │     后端     │                           │   模型 / AI   │
│  (React/TS)  │  ◄─── 转写结果 ───────────────   │  (FastAPI)   │  ◄── 转写文本 + 笔记 ────   │  (Whisper)   │
│              │                                 │              │                           │              │
│              │  ──── REST /api/* ───────────►  │              │                           │              │
│              │  ◄─── JSON 响应 ──────────────   │              │                           │              │
│              │                                 │              │                           │              │
│              │  ◄═══ /ws/sessions/{sid} ══════ │              │                           │              │
│              │       （实时事件）                │              │                           │              │
└──────────────┘                                 └──────────────┘                           └──────────────┘
   端口 5173                                       端口 8000
```

---

## 3. 数据流

### 3.1 实时转写

1. 前端采集麦克风音频（PCM16, 16kHz, 单声道, 约3秒一块）
2. 前端通过 `/ws/transcribe` 发送音频（二进制帧）
3. 后端接收音频，转发给模型服务
4. 模型运行 Whisper 推理，返回转写文本
5. 后端通过 `/ws/transcribe` 将转写结果返回前端
6. 前端实时显示文字（临时结果 → 最终结果）

### 3.2 结构化笔记生成

1. 模型收到最终转写文本
2. 模型生成结构化笔记（分类、标签、遥测引用）
3. 模型调用 `POST /api/sessions/{sid}/notes`
4. 后端存储笔记，通过 WebSocket 广播 `note.created`
5. 前端接收事件，实时显示笔记

---

## 4. API 端点概要

### REST API

| 方法 | 端点 | 负责方 | 描述 |
|------|------|--------|------|
| POST | `/api/sessions` | 后端 | 创建会话 |
| GET | `/api/sessions` | 后端 | 列出会话 |
| GET | `/api/sessions/{sid}` | 后端 | 获取会话详情 |
| PATCH | `/api/sessions/{sid}` | 后端 | 更新会话 |
| POST | `/api/sessions/{sid}/notes` | 后端 + 模型 | 创建笔记 |
| GET | `/api/sessions/{sid}/notes` | 后端 | 列出笔记 |
| PUT | `/api/sessions/{sid}/notes/{id}` | 后端 | 编辑笔记 |
| DELETE | `/api/sessions/{sid}/notes/{id}` | 后端 | 删除笔记 |
| GET | `/api/sessions/{sid}/notes/export` | 后端 | 导出笔记 |
| POST | `/api/sessions/{sid}/telemetry` | 后端 | 写入遥测 |
| GET | `/api/sessions/{sid}/telemetry` | 后端 | 查询遥测 |
| POST | `/api/sessions/{sid}/stt/tasks` | 后端 + 模型 | 注册 STT 任务 |
| PUT | `/api/sessions/{sid}/stt/tasks/{tid}` | 后端 + 模型 | 更新 STT 结果 |

### WebSocket 端点

| 端点 | 方向 | 描述 |
|------|------|------|
| `/ws/transcribe` | 前端 ↔ 后端 | 音频上传 + 转写结果 |
| `/ws/sessions/{sid}` | 后端 → 前端 | 实时事件广播 |

---

## 5. WebSocket 事件类型

| 事件 | 触发方 | 描述 |
|------|--------|------|
| `note.created` | 后端（模型 POST 后） | 新笔记创建 |
| `note.updated` | 后端（前端 PUT 后） | 笔记被编辑 |
| `note.deleted` | 后端（前端 DELETE 后） | 笔记被删除 |
| `stt.task.created` | 后端（模型 POST 后） | STT 任务已注册 |
| `stt.task.done` | 后端（模型 PUT 后） | 转写完成 |
| `error.occurred` | 后端 | 错误广播 |

---

## 6. 联调流程

### 阶段一：独立开发

| 团队 | 任务 |
|------|------|
| 前端 | 构建 UI；实现麦克风采集和 PCM 分块 |
| 后端 | 实现 REST API + 会话 WebSocket（内存数据库） |
| 模型 | 训练/微调 Whisper；搭建推理服务；用样本音频测试 |

### 阶段二：两两联调

| 联调组合 | 步骤 |
|----------|------|
| 前端 ↔ 后端 | 1. 启动后端（端口 8000）<br>2. 配置 `frontend/.env.local` 中的后端地址<br>3. 测试会话增删改查 + WebSocket 连接<br>4. 验证事件广播正常 |
| 后端 ↔ 模型 | 1. 模型调用 `POST /stt/tasks` 注册任务<br>2. 模型调用 `PUT /stt/tasks/{tid}` 回写转写结果<br>3. 验证 `stt.task.done` 事件广播 |
| 前端 ↔ 模型 | （通过后端间接联调） |

### 阶段三：端到端联调

1. 前端开始录音 → 创建会话 → 连接 WebSocket
2. 前端发送音频块到 `/ws/transcribe`
3. 后端转发到模型 → 模型返回转写结果
4. 后端通过 WebSocket 广播转写结果到前端
5. 模型生成结构化笔记 → `POST /notes` → 广播
6. 前端实时展示转写文字和笔记
7. 操作员编辑笔记 → `PUT /notes` → 广播更新
8. 前端停止录音 → `PATCH` 会话状态为 ended

---

## 7. 开发环境

### 启动后端

```bash
cd backend
source ../astra/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# API 文档: http://localhost:8000/docs
```

### 启动前端

```bash
cd frontend
npm install
```

`npm install` 完成后，创建（或确认）环境配置文件 `frontend/.env.local`：

```env
# 后端 REST API 地址
VITE_API_URL=http://localhost:8000/api

# 会话 WebSocket 地址（后面会自动拼接 /{sessionId}）
VITE_SESSION_WS_URL=ws://localhost:8000/ws/sessions
```

> **注意**：如果后端运行在其他主机或端口上，请相应修改上面的地址。

然后启动开发服务器：

```bash
npm run dev
# 界面: http://localhost:5173
```

> **重要**：必须先启动后端，再启动前端。否则创建会话和 WebSocket 连接会失败。

---

## 8. 当前状态

| 组件 | 状态 | 备注 |
|------|------|------|
| 前端 UI | ✅ 完成 | 仪表盘、会话、历史、详情页 |
| 麦克风采集 + PCM 分块 | ✅ 完成 | 真实 getUserMedia, 16kHz Int16, 3秒分块 |
| 真实音频电平可视化 | ✅ 完成 | AnalyserNode RMS |
| 后端 REST API | ✅ 完成 | 会话、笔记、遥测、STT 任务 |
| 后端 `/ws/sessions/{sid}` | ✅ 完成 | 事件广播正常 |
| 后端 `/ws/transcribe` | ❌ 未开始 | 需要实现 |
| Whisper 推理服务 | ❌ 未开始 | 模型团队负责 |
| 结构化笔记生成 | ❌ 未开始 | 模型团队负责 |
| PostgreSQL 迁移 | ❌ 未开始 | 当前为内存存储 |

---

## 9. 沟通规则

- **API 变更**：任何请求/响应格式变更必须先提案，三方评审通过，更新 `API_CONTRACT.md` 后再实现。
- **破坏性变更**：必须升主版本号；提供迁移指南和 1 周过渡期。
- **新增字段**：新增可选字段是非破坏性 minor 变更，无需评审。
- **测试**：各团队为自己的端点写测试；集成测试共享。
- **Bug 报告**：提交 GitHub Issue 需包含：复现步骤、预期与实际行为、日志/截图。

---

## 10. 关键文件位置

| 文件 | 用途 |
|------|------|
| `frontend/src/hooks/useWhisper.ts` | 麦克风采集和音频分块逻辑 |
| `frontend/src/services/api.ts` | HTTP 请求封装 |
| `frontend/src/services/sessionWs.ts` | 会话 WebSocket 客户端 |
| `frontend/src/store/useStore.ts` | 全局状态管理 |
| `frontend/API_CONTRACT.md` | API 契约规范 |
| `backend/app/main.py` | 后端入口 |
| `backend/app/routes/sessions.py` | 会话增删改查接口 |
| `backend/app/routes/notes.py` | 笔记增删改查 + 导出 |
| `backend/app/routes/stt.py` | STT 任务管理 |
| `backend/app/routes/websocket.py` | 会话 WebSocket 端点 |
| `backend/app/ws_manager.py` | WebSocket 广播管理器 |
| `backend/app/schemas/schemas.py` | 数据格式定义 |

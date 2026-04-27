# ASTRA API 契约

**版本：** 0.3.0  
**Base URL：** `http://localhost:8000`  
**最后更新：** 2026 年 4 月

> English: [api-contract.md](./api-contract.md)

---

> **读者：**
> - **前端组** — Sessions、Notes 读写/编辑/导出、Telemetry 通道、WebSocket 订阅
> - **AI / 数据组** — POST 笔记、STT 任务生命周期、获取最新遥测值

---

## 通用约定

- 所有时间戳使用 **ISO 8601 UTC** 格式：`2025-01-26T10:32:15Z`
- 请求和响应都用 **JSON**（`Content-Type: application/json`）
- 所有 session 范围的接口都要在 URL 中传 session ID（`sid`）
- session 或资源不存在时统一返回 `404`
- 浏览器录制使用 `POST /api/sessions/{sid}/stt/upload`，详细数据流见
  `backend/README.zh.md` 中的「录制路径」图

---

## 1. Sessions API

### POST `/api/sessions` — 创建会话

**调用方：** 前端（操作员开始一次新测试时）

**请求体：**
```json
{
  "name": "Motor Test Session #42",
  "description": "Testing CADRE rover arm torque limits"
}
```

**响应 `200`：**
```json
{
  "id": "sess_a1b2c3d4",
  "name": "Motor Test Session #42",
  "description": "Testing CADRE rover arm torque limits",
  "status": "active",
  "started_at": "2025-01-26T10:00:00Z",
  "ended_at": null,
  "note_count": 0
}
```

---

### GET `/api/sessions` — 列出会话

**调用方：** 前端（仪表板）

**响应 `200`：** 会话对象数组（最新优先）

---

### GET `/api/sessions/{sid}` — 获取单个会话

**调用方：** 前端

**响应 `200`：** 单个会话对象

---

### PATCH `/api/sessions/{sid}` — 更新会话

**调用方：** 前端（比如测试结束时停止会话）

**请求体（所有字段可选）：**
```json
{
  "name": "Updated Session Name",
  "description": "Updated description",
  "status": "ended"
}
```

> 把 `status` 设为 `"ended"` 时，后端会自动写入 `ended_at` 时间戳。

**status 取值：** `active` | `ended`

---

## 2. Notes API

### POST `/api/sessions/{sid}/notes` — 创建笔记

**调用方：AI / 数据组**（在 Whisper 转写 + LLM 处理完一个音频分片后）

**请求体：**
```json
{
  "timestamp": "2025-01-26T10:32:15Z",
  "speaker": "Engineer A",
  "content": "Motor current rising to 2.3A, temperature looks stable.",
  "type": "observation",
  "tags": ["motor", "current"],
  "telemetry_snapshot": {
    "battery_voltage": 32.5,
    "motor_current": 2.3
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `timestamp` | ISO datetime | ✅ | 观察发生的时间 |
| `speaker` | string | ❌ | 例如 `Engineer A`，来自说话人分离或设备标签 |
| `content` | string | ✅ | 笔记正文 |
| `type` | enum | ❌ | `observation`（默认）/ `command` / `system` |
| `tags` | string[] | ❌ | 用于过滤的关键词，默认 `[]` |
| `telemetry_snapshot` | object | ❌ | 该时刻相关遥测值的快照 |

**响应 `200`：** 完整 note 对象，自动生成 `id`、`created_at`、`updated_at`

**副作用：** 通过 WebSocket 广播 `note.created`。

---

### GET `/api/sessions/{sid}/notes` — 列出笔记

**调用方：** 前端

**Query 参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `speaker` | string | 按发言人过滤 |
| `type` | enum | 按 `observation` / `command` / `system` 过滤 |
| `from` | ISO datetime | 从该时间开始 |
| `to` | ISO datetime | 到该时间为止 |

**示例：**
```
GET /api/sessions/sess_abc/notes?speaker=Engineer A&type=observation
```

**响应 `200`：** note 对象数组，按 `timestamp` 升序。

---

### GET `/api/sessions/{sid}/notes/export` — 导出笔记

**调用方：** 前端（导出按钮）

**Query 参数：**

| 参数 | 取值 | 默认 |
|------|------|------|
| `format` | `markdown` / `json` | `markdown` |

**Markdown 响应** — 直接复制粘贴到 JPL 测试日志、Confluence。  
**JSON 响应** — 用于程序化处理。

---

### GET `/api/sessions/{sid}/notes/{note_id}` — 获取单条笔记

**调用方：** 前端

---

### PUT `/api/sessions/{sid}/notes/{note_id}` — 编辑笔记

**调用方：** 前端（操作员手动修正 AI 生成的笔记）

**请求体（所有字段可选）：**
```json
{
  "content": "Motor current rising to 2.5A (operator correction)",
  "speaker": "Engineer B",
  "type": "observation",
  "tags": ["motor", "current", "corrected"]
}
```

**响应 `200`：** 更新后的 note 对象。

**副作用：** 广播 `note.updated`。

---

### DELETE `/api/sessions/{sid}/notes/{note_id}` — 删除笔记

**调用方：** 前端

**响应 `200`：**
```json
{ "message": "Note note_abc123 deleted" }
```

**副作用：** 广播 `note.deleted`。

---

## 3. Telemetry API

### POST `/api/sessions/{sid}/telemetry` — 单条写入

**调用方：** 遥测数据源

```json
{
  "timestamp": "2025-01-26T10:32:15Z",
  "channel": "battery_voltage",
  "value": 32.5,
  "unit": "V"
}
```

---

### POST `/api/sessions/{sid}/telemetry/batch` — 批量写入

**调用方：** 遥测数据源

```json
{
  "data": [
    { "timestamp": "...", "channel": "battery_voltage", "value": 32.5, "unit": "V" },
    { "timestamp": "...", "channel": "motor_current",   "value": 2.3,  "unit": "A" }
  ]
}
```

**响应：** `{ "created": 2 }`

---

### GET `/api/sessions/{sid}/telemetry` — 查询遥测

**调用方：** 前端、AI 模块

| 参数 | 类型 | 说明 |
|------|------|------|
| `channel` | string | 按通道名过滤 |
| `from` | ISO datetime | 起始时间 |
| `to` | ISO datetime | 结束时间 |
| `limit` | int | 最大返回条数（默认 1000） |

返回结果按时间倒序（最新优先）。

---

### GET `/api/sessions/{sid}/telemetry/latest?channel=X` — 获取最新值

**调用方：AI 模块**

适用场景：操作员说 *"ASTRA, log the current voltage"* 时，AI 调这个接口拿到
当前电压值，再写到 note 的 `telemetry_snapshot` 里。

**示例：**
```
GET /api/sessions/sess_abc/telemetry/latest?channel=battery_voltage
```

**响应 `200`：** 单个 telemetry 对象（最新一条）。

---

### GET `/api/sessions/{sid}/telemetry/channels` — 列出通道

**调用方：** 前端

**响应 `200`：**
```json
{ "channels": ["battery_voltage", "motor_current", "temperature"] }
```

---

## 4. STT Tasks API *(v0.2.0 引入)*

管理音频分片的转写任务生命周期，遵循 sponsor 确认的**基于停顿切分**的工作流。

### 工作流概览
```
前端检测到停顿 → AI 模块注册任务 → Whisper 处理 → AI 模块更新任务 → 后端广播结果
```

---

### POST `/api/sessions/{sid}/stt/tasks` — 注册 STT 任务

**调用方：AI / 数据组**（一段新音频分片准备好处理时）

**请求体：**
```json
{
  "audio_chunk_id": "chunk_20250126_001",
  "duration_seconds": 8.4
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `audio_chunk_id` | string | ✅ | 音频文件的内部引用 ID |
| `duration_seconds` | float | ❌ | 音频时长 |

**响应 `201`：**
```json
{
  "id": "stt_f1e2d3c4",
  "session_id": "sess_abc123",
  "audio_chunk_id": "chunk_20250126_001",
  "duration_seconds": 8.4,
  "status": "pending",
  "transcript": null,
  "error": null,
  "created_at": "2025-01-26T10:32:15Z",
  "updated_at": "2025-01-26T10:32:15Z"
}
```

**副作用：** 通过 WebSocket 广播 `stt.task.created`。

---

### GET `/api/sessions/{sid}/stt/tasks` — 列出任务

**调用方：** 前端（用来显示转写历史 / 状态指示器）

返回该 session 下所有任务，最新优先。

---

### GET `/api/sessions/{sid}/stt/tasks/{tid}` — 获取单个任务

**调用方：** 前端 / AI 模块（轮询状态用）

---

### PUT `/api/sessions/{sid}/stt/tasks/{tid}` — 更新任务结果

**调用方：AI / 数据组**（Whisper 处理完成时）

**成功：**
```json
{
  "status": "done",
  "transcript": "Motor current rising to 2.3 amps, temperature looks stable.",
  "error": null
}
```

**失败：**
```json
{
  "status": "failed",
  "transcript": null,
  "error": "Audio too short or no speech detected"
}
```

**副作用：**
- `status: done` → 广播 `stt.task.done`
- `status: failed` → 广播 `error.occurred`

---

## 5. WebSocket

### WS `/ws/sessions/{sid}` — 订阅会话事件

**调用方：** 前端（打开会话时连接，结束时断开）

#### 建立连接
```js
const ws = new WebSocket("ws://localhost:8000/ws/sessions/sess_abc123");
```

#### 心跳
客户端发 `"ping"` → 服务端回 `"pong"`。

#### 事件格式

所有事件都是这种结构：
```json
{
  "event": "<event_type>",
  "session_id": "sess_abc123",
  "data": { ... }
}
```

| 事件 | 触发时机 | `data` 内容 |
|------|----------|-------------|
| `connected` | 连接成功 | `{ "message": "Connected to session sess_abc123" }` |
| `note.created` | AI 创建新笔记 | 完整 note 对象 |
| `note.updated` | 操作员修改笔记 | 更新后的 note 对象 |
| `note.deleted` | 笔记被删除 | `{ "id": "note_xxx" }` |
| `stt.task.created` | AI 注册新音频分片 | STT 任务对象（status: pending） |
| `stt.task.done` | 转写完成 | STT 任务对象（status: done，含 transcript） |
| `error.occurred` | STT 失败或系统错误 | `{ "message": "...", "source": "stt" }` |

#### 前端使用示例
```js
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  switch (msg.event) {
    case "note.created":
      appendNoteToUI(msg.data);
      break;
    case "note.updated":
      updateNoteInUI(msg.data);
      break;
    case "note.deleted":
      removeNoteFromUI(msg.data.id);
      break;
    case "stt.task.done":
      showTranscriptChunk(msg.data.transcript);
      break;
    case "error.occurred":
      showErrorBanner(msg.data.message);
      break;
  }
};
```

---

## 错误响应

| 状态码 | 含义 |
|--------|------|
| `404` | session、note、遥测通道或 STT 任务不存在 |
| `422` | 请求体校验失败（检查字段类型/格式） |
| `500` | 服务端内部错误 |

**404 示例：**
```json
{ "detail": "Session sess_xyz not found" }
```

---

## 谁调用什么（速查表）

| 接口 | 前端 | AI / 数据组 |
|------|------|------------|
| POST `/sessions` | ✅ | |
| GET/PATCH `/sessions` | ✅ | |
| POST `/notes` | | ✅ |
| GET/PUT/DELETE `/notes` | ✅ | |
| GET `/notes/export` | ✅ | |
| POST `/telemetry`（写入） | | ✅ |
| GET `/telemetry`（查询） | ✅ | ✅ |
| GET `/telemetry/latest` | | ✅ |
| POST `/stt/tasks` | | ✅ |
| GET `/stt/tasks` | ✅ | |
| PUT `/stt/tasks/{tid}` | | ✅ |
| WS `/ws/sessions/{sid}` | ✅（订阅） | |

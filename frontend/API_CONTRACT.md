# ASTRA API Contract (v1)

本文件定义 ASTRA 前端、后端、模型三方的接口契约。目标是让三方可并行开发，并且在联调阶段保持稳定。

## 1. 范围与原则

- 本契约覆盖：
  - 实时转录 WebSocket：`/ws/transcribe`
  - 会话与日志 REST：`/api/sessions`、`/api/logs`
  - 文档上传 REST：`/api/documents`
  - 遥测查询：`/api/telemetry/:stream`
- 时间字段统一为 ISO8601 UTC（例如 `2026-02-16T22:30:00.000Z`）。
- REST 响应统一 envelope：`{ data, error, meta }`。
- 本版本为 `v1`，变更规则见“版本策略”。

## 2. 基础配置

- Frontend `VITE_WS_URL` 默认：`ws://localhost:8000/ws/transcribe`
- Frontend `VITE_API_URL` 默认：`http://localhost:8000/api`
- 开发环境 CORS 允许：`http://localhost:5173`（及同类本地端口）

## 3. WebSocket Contract: `/ws/transcribe`

### 3.1 连接与鉴权

- 方法：WebSocket upgrade
- URL：`ws://host/ws/transcribe`
- 鉴权（可选）：`Authorization: Bearer <token>` 或 query token（由后端统一）
- 会话粒度：一个活跃录音会话对应一个 WebSocket 连接

### 3.2 Frontend -> Backend

#### A) 控制消息（JSON 文本帧）

```json
{ "type": "start", "config": { "language": "en", "model": "large-v3" } }
{ "type": "pause" }
{ "type": "resume" }
{ "type": "stop" }
```

约束：
- `start` 必须先于二进制音频帧。
- `pause` 后前端不再发送音频帧；`resume` 后恢复。
- `stop` 后后端应结束会话并返回最终状态。

#### B) 音频数据（二进制帧）

- 编码：PCM 16-bit signed integer（little-endian）
- 采样率：16kHz
- 声道：mono
- chunk 建议：约 3 秒一包（允许 2-5 秒）

### 3.3 Backend -> Frontend（JSON 文本帧）

#### A) 转录结果

```json
{
  "id": "tr_1739...",
  "text": "Initiating arm calibration for joint three.",
  "confidence": 0.94,
  "speaker_id": "speaker_0",
  "timestamp": "2026-02-16T22:30:00.000Z",
  "is_final": true
}
```

字段约束：
- `id`: string，唯一
- `text`: string，可为空字符串（仅在 partial 无文本时）
- `confidence`: number，范围 `[0.0, 1.0]`
- `speaker_id`: string，可选（无 diarization 时可省略）
- `timestamp`: ISO8601 string
- `is_final`: boolean（`false`=partial，`true`=final）

#### B) 系统事件（推荐）

```json
{ "type": "session_started", "session_id": "sess_123", "timestamp": "2026-02-16T22:00:00.000Z" }
{ "type": "session_paused", "session_id": "sess_123", "timestamp": "2026-02-16T22:05:00.000Z" }
{ "type": "session_resumed", "session_id": "sess_123", "timestamp": "2026-02-16T22:06:00.000Z" }
{ "type": "session_stopped", "session_id": "sess_123", "timestamp": "2026-02-16T22:10:00.000Z" }
```

#### C) 错误消息

```json
{
  "type": "error",
  "error": {
    "code": "WS_UNSUPPORTED_AUDIO_FORMAT",
    "message": "Expected PCM16 16kHz mono",
    "details": {}
  },
  "timestamp": "2026-02-16T22:01:00.000Z"
}
```

## 4. REST Contract

Base URL：`/api`

### 4.1 通用响应结构

#### 成功

```json
{
  "data": {},
  "error": null,
  "meta": {
    "request_id": "req_123",
    "timestamp": "2026-02-16T22:30:00.000Z"
  }
}
```

#### 失败

```json
{
  "data": null,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Session not found",
    "details": {}
  },
  "meta": {
    "request_id": "req_456",
    "timestamp": "2026-02-16T22:30:00.000Z"
  }
}
```

### 4.2 `POST /api/sessions`

- 作用：创建会话记录（可在 `start` 后创建，或 `stop` 时补建）
- Request（示例）：

```json
{
  "name": "RoboArm Test Session",
  "description": "Joint calibration run",
  "testbed": "JPL-RTB-01",
  "started_at": "2026-02-16T22:00:00.000Z"
}
```

- Response `data`（示例）：

```json
{
  "id": "sess_123",
  "name": "RoboArm Test Session",
  "status": "active"
}
```

### 4.3 `GET /api/sessions`

- 作用：分页查询会话
- Query：
  - `page`（默认 1）
  - `page_size`（默认 20，最大 100）
  - `q`（可选，模糊搜索）
- `meta.pagination` 示例：

```json
{
  "page": 1,
  "page_size": 20,
  "total": 132
}
```

### 4.4 `GET /api/sessions/:id/logs`

- 作用：获取某会话转录日志
- Response `data` 示例：

```json
{
  "session_id": "sess_123",
  "logs": [
    {
      "id": "tr_1739",
      "text": "Initiating arm calibration for joint three.",
      "confidence": 0.94,
      "speaker_id": "speaker_0",
      "timestamp": "2026-02-16T22:30:00.000Z"
    }
  ]
}
```

### 4.5 `PUT /api/logs/:id`

- 作用：编辑单条日志（纠错或补充）
- Request 示例：

```json
{
  "text": "Initiating arm calibration for joint 3.",
  "reviewed_by": "operator_1"
}
```

### 4.6 `POST /api/documents`

- 作用：上传文档供 RAG 使用
- `Content-Type`: `multipart/form-data`
- 字段：
  - `file`: PDF/DOCX/TXT/MD
  - `metadata`（可选 JSON 字符串）
- Response `data` 示例：

```json
{
  "document_id": "doc_789",
  "filename": "manual.pdf",
  "status": "indexed"
}
```

### 4.7 `GET /api/telemetry/:stream`

- 作用：查询遥测流当前快照（后续可扩展 WS 推送）
- Response `data` 示例：

```json
{
  "stream": "power",
  "timestamp": "2026-02-16T22:30:00.000Z",
  "metrics": [
    { "name": "voltage", "value": 28.1, "unit": "V", "status": "nominal" }
  ]
}
```

## 5. 错误码规范

### 5.1 HTTP 错误码映射

| HTTP | code | 场景 |
|---|---|---|
| 400 | `INVALID_ARGUMENT` | 参数缺失、格式错误 |
| 401 | `UNAUTHORIZED` | 未认证或 token 失效 |
| 403 | `FORBIDDEN` | 权限不足 |
| 404 | `RESOURCE_NOT_FOUND` | 会话/日志/文档不存在 |
| 409 | `CONFLICT` | 资源状态冲突 |
| 413 | `PAYLOAD_TOO_LARGE` | 上传文件超限 |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | 文档类型不支持 |
| 422 | `UNPROCESSABLE_ENTITY` | 业务校验失败 |
| 429 | `RATE_LIMITED` | 触发限流 |
| 500 | `INTERNAL_ERROR` | 未分类服务器错误 |
| 503 | `SERVICE_UNAVAILABLE` | 模型服务不可用 |

### 5.2 WebSocket 错误码

| code | 场景 |
|---|---|
| `WS_INVALID_CONTROL_SEQUENCE` | 控制消息顺序非法（如未 start 先发音频） |
| `WS_UNSUPPORTED_AUDIO_FORMAT` | 非 PCM16/16kHz/mono |
| `WS_MODEL_TIMEOUT` | 模型推理超时 |
| `WS_SESSION_CLOSED` | 会话已关闭仍发送数据 |
| `WS_INTERNAL_ERROR` | 服务端内部错误 |

## 6. 版本策略

- 当前版本：`v1`
- 兼容性规则：
  - 新增可选字段：minor 变更（不破坏兼容）
  - 修改必填字段、语义变化、删除字段：major 变更
- 变更流程：
  1. 提交变更提案（变更内容、兼容策略、回滚方案）
  2. 三方评审通过
  3. 在联调环境灰度验证
  4. 更新本文档与发布记录

## 7. 非功能约束（v1）

- 可靠性：断网恢复后允许新建连接继续会话（不要求同一连接恢复）。
- 可观测性：REST 与 WS 均记录 `request_id/session_id` 以支持跨系统排查。
- 安全性：生产环境必须启用鉴权，禁止匿名写接口。


# ASTRA 三方协作流程（Frontend / Backend / Model）

本文档用于固化协作边界、交付责任和变更流程，避免联调期间出现“接口无人负责”与“重复返工”。

## 1. 角色边界

### Frontend（React）
- 负责：音频采集、会话控制（start/pause/resume/stop）、实时渲染、错误提示、降级策略（mock/live）。
- 不负责：模型推理策略、数据库写入时机、服务端会话状态持久化。
- 交付物：前端页面、`useWhisper` 链路、接口消费层、可观测日志（前端）。

### Backend（FastAPI/Flask）
- 负责：WebSocket 会话编排、REST CRUD、持久化、鉴权/CORS、统一响应结构。
- 不负责：前端展示逻辑、模型参数调优细节。
- 交付物：`/ws/transcribe`、`/api/*`、错误码规范、服务端日志与指标。

### Model（Whisper/LLM/RAG）
- 负责：推理质量、延迟与稳定性、置信度输出、可选说话人分离。
- 不负责：前端 UI 逻辑、业务数据存储接口设计。
- 交付物：可调用推理服务能力、模型版本说明、质量与性能报告。

## 2. RACI（核心活动）

| 活动 | Frontend | Backend | Model |
|---|---|---|---|
| WebSocket 音频协议定义 | C | A | R |
| WebSocket 服务实现 | I | A/R | C |
| Whisper 推理输出格式 | C | C | A/R |
| Session/Logs REST 设计 | C | A/R | I |
| 会话停止后落库 | I | A/R | I |
| 端到端联调与验收 | A/R | A/R | A/R |
| 线上问题定位（音频链路） | A/R | A/R | C |
| 线上问题定位（模型质量） | C | C | A/R |

说明：
- A = Accountable（最终负责）
- R = Responsible（直接执行）
- C = Consulted（被咨询）
- I = Informed（被同步）

## 3. 接口 Owner 与审批

| 接口域 | Owner | 变更审批 |
|---|---|---|
| `/ws/transcribe` 协议 | Backend + Model | Frontend/Backend/Model 三方通过 |
| `/api/sessions`、`/api/logs` | Backend | Frontend + Backend 通过 |
| `/api/documents`（RAG） | Backend + Model | Frontend/Backend/Model 三方通过 |
| 前端设置项（AI 参数） | Frontend | Frontend + Model 通过 |

## 4. 协作节奏

- 每周一次接口评审（30 分钟）：仅处理“契约变更、阻塞项、风险”。
- 每日异步同步：昨日阻塞 / 今日接口变更 / 风险预警。
- 联调看板状态：`未开始` -> `开发中` -> `可联调` -> `已验收`。

## 5. 变更流程（强制）

1. 提案：提交变更描述（字段、兼容性、回滚策略、验证方式）。
2. 评审：至少 Frontend + Backend + Model 各一人确认。
3. 版本：协议版本号递增（见 `API_CONTRACT.md`）。
4. 灰度：先在联调环境验证，再进入共享测试环境。
5. 回归：按 `INTEGRATION_CHECKLIST.md` 完整回归。

## 6. 交付完成定义（Definition of Done）

- 契约文档已更新并评审通过。
- 联调检查清单全部通过，无 P0/P1 阻塞。
- 关键 SLO 达标（见 `INTEGRATION_CHECKLIST.md`）。
- 变更记录已同步到周会与看板。

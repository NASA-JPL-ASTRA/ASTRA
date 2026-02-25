# ASTRA 联调检查清单（Frontend / Backend / Model）

本清单用于三方联调与验收，执行顺序建议从“环境准备”到“回归验证”。

## 1. 环境准备

- [ ] 前端设置 `VITE_WS_URL`、`VITE_API_URL` 指向联调环境。
- [ ] 后端 CORS 已允许前端联调域名。
- [ ] 模型服务可用并可被后端调用。
- [ ] 三方约定使用同一份 `API_CONTRACT.md`（v1）。
- [ ] 联调期间启用统一日志追踪字段：`request_id`、`session_id`。

## 2. 前端链路检查（`useWhisper`）

- [ ] 麦克风权限申请成功，拒绝时有明确提示与重试入口。
- [ ] 音频编码为 PCM16 / 16kHz / mono。
- [ ] chunk 发送频率稳定在 2-5 秒区间（目标约 3 秒）。
- [ ] 控制消息顺序正确：`start -> pause/resume -> stop`。
- [ ] 连接断开后有可见状态与重连策略（用户可继续录制）。
- [ ] 接收 `is_final=false` 可实时显示，`is_final=true` 可正确归档。

## 3. 后端链路检查

- [ ] `/ws/transcribe` 接收二进制音频与 JSON 控制消息都正常。
- [ ] 控制序列非法时返回 `WS_INVALID_CONTROL_SEQUENCE`。
- [ ] 音频格式非法时返回 `WS_UNSUPPORTED_AUDIO_FORMAT`。
- [ ] `stop` 后能结束会话并持久化日志（或触发异步持久化任务）。
- [ ] REST 返回结构统一为 `{ data, error, meta }`。
- [ ] 关键接口（sessions/logs/documents）错误码符合契约。

## 4. 模型链路检查

- [ ] 模型对单个 chunk 有稳定输出（partial/final）。
- [ ] `confidence` 范围稳定在 `[0.0, 1.0]`。
- [ ] 说话人分离开启时返回 `speaker_id`，关闭时字段可缺省。
- [ ] 模型超时可被后端识别并映射为 `WS_MODEL_TIMEOUT` / `503`。
- [ ] 模型版本可追踪（日志包含 model name/version）。

## 5. 端到端场景验收

### 基础流程
- [ ] 开始录制后 10 秒内看到第一条文本（可 partial）。
- [ ] 暂停后不再新增文本；恢复后继续新增。
- [ ] 停止后会话可在 `/api/sessions` 查询到。
- [ ] `/api/sessions/:id/logs` 能返回完整转录日志。

### 异常流程
- [ ] 网络抖动时前端有状态提示，不出现静默失败。
- [ ] 模型不可用时前端收到可解释错误文案（非未知错误）。
- [ ] 非法参数/资源不存在时前端能依据错误码给出正确反馈。

## 6. 性能 SLO（联调门槛）

- [ ] 转录延迟：单 chunk 端到端 P95 < 10s。
- [ ] 首字出现时间（TTFT）：P95 < 5s。
- [ ] WebSocket 会话稳定性：30 分钟内无异常断开（正常网络）。
- [ ] REST 可用性：关键接口成功率 >= 99%（联调样本期）。

备注：
- 若硬件或模型配置受限，可临时放宽目标并记录原因；正式环境需回到目标值。

## 7. 数据质量验收

- [ ] 转录字段完整：`id/text/confidence/timestamp/is_final`。
- [ ] `timestamp` 为 ISO8601 UTC。
- [ ] `confidence` 不越界、不出现 NaN/null（除明确约定外）。
- [ ] 日志顺序与时间线一致（允许小范围乱序并能前端纠正）。

## 8. 回归清单（每次接口变更后必须执行）

- [ ] WebSocket 控制消息回归（start/pause/resume/stop）。
- [ ] 音频格式兼容性回归（采样率、声道、位深）。
- [ ] REST 兼容性回归（旧字段仍可解析）。
- [ ] 错误码回归（至少覆盖 400/401/404/500/503）。
- [ ] UI 错误提示与降级路径回归（mock/live 切换不受影响）。

## 9. 验收结论模板

- 版本：`v1`
- 环境：`staging`
- 执行人：Frontend / Backend / Model 各一名
- 结果：`通过` / `有条件通过` / `不通过`
- 阻塞项：
  - `P0`:
  - `P1`:
  - `P2`:
- 复验时间：


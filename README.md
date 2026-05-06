# JPL ASTRA - Realtime Voice Query Demo

基于本地麦克风 + VAD 分段 + OpenAI API 的实时语音查询 demo。  

---

## 一、当前能力

| 功能 | 说明 |
|---|---|
| 实时语音转写 | 麦克风录音 + Silero VAD 分段，静音触发上传，调用 `gpt-4o-transcribe` |
| 指令意图解析 | 将 transcript 发送到 LLM（默认 `gpt-5.5`）解析 `query_event_log / query_channel_log` |
| Telemetry 查询 | 根据意图自动读取 `telemetry/<scenario>/event.log` 或 `channel.log` |
| 工程日志落盘 | 将 transcript + ASTRA 回复写入 `engineering_log.md` |
| 噪声兜底过滤 | 使用 `app/utils/hallucination_filter.py` 的短语/置信度规则（当前主要依赖短语兜底） |

---

## 二、处理流程

1. `realtime_demo.py` 持续录音，Silero VAD 判断语音段结束。  
2. 语音段保存为临时 WAV，调用 OpenAI STT 获取 transcript。  
3. transcript 先做噪声过滤；若通过，进入意图路由：  
   - `query_event_log`：查事件日志（例如 terrain bump 的 `y=...m`）  
   - `query_channel_log`：查通道值（例如 `imu.accel_x`、`motors.motor1_current`）  
   - 其他情况：走总结分支（Progress / Issues / Next Actions）  
4. 输出 ASTRA 回复，并把 transcript + 回复追加到 `engineering_log.md`。

---

## 三、目录与关键文件

- `realtime_demo.py`：实时录音、STT、意图解析、Telemetry 查询主流程  
- `.env.example`：本地环境变量模板（提交到仓库）  
- `requirements-realtime.txt`：realtime demo 依赖  
- `telemetry/`：测试数据集（`test_1_straight_line`、`test_2_uphill` 等）  
- `app/utils/hallucination_filter.py`：噪声/幻觉过滤规则

---

## 四、快速开始

### 1) 安装依赖

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-realtime.txt
```

### 2) 配置环境变量

复制模板并填写真实 key：

```bash
cp .env.example .env
```

必须配置：

- `OPENAI_API_KEY`

常用可选项：

- `OPENAI_STT_MODEL`（默认 `gpt-4o-transcribe`）
- `OPENAI_SUMMARY_MODEL`（建议填你有权限的模型）
- `OPENAI_INTENT_MODEL`（建议填你有权限的模型）
- `OPENAI_API_BASE_URL`（默认 `https://api.openai.com/v1`）

> 注意：`.env` 不要提交；`.env.example` 只能放占位符。

### 3) 运行 demo

```bash
python realtime_demo.py --telemetry-root telemetry --default-scenario test_1_straight_line
```

也可显式指定模型：

```bash
python realtime_demo.py \
  --asr-model gpt-4o-transcribe \
  --summary-model gpt-5.5 \
  --intent-model gpt-5.5 \
  --telemetry-root telemetry \
  --default-scenario test_1_straight_line
```

---

## 五、语音测试示例

### Event 查询（test_1）

> ASTRA, give me the position of y where a terrain bump is detected when rover is going in straight line.

期望回复（示例）：

`Terrain bump y positions: y=30.0m, y=45.0m, y=75.0m, y=105.0m, y=135.0m`

### Channel 查询

> ASTRA, in test 1 straight line, give me the latest imu.accel_x and motors.motor1_current values from channel log.

---

## 六、幻觉过滤规则

- **置信度**：`no_speech_prob > 0.4` 或 `avg_logprob < -0.5` → 过滤
- **短语兜底**：仅对长度 ≤ 25 字符的 transcript，若匹配已知幻觉短语则过滤
- **提示**：过滤时显示 `(noise / no actual content)`

---

## 七、与 Backend 对接

- API 合约：`/api/sessions/{sid}/stt/tasks` 注册任务，`PUT` 更新 transcript
- ASTRA 格式：`format=astra` 返回简化 JSON（session_id, segments, timestamp）
- 当前 demo 直接调用 Whisper API，后续可对接 Backend 的 STT 路由


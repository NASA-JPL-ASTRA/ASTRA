# ASTRA 集成指南：Frontend + Backend + Whisper (Data/Model)

## 架构概览

```
┌─────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│    Frontend     │────►│  ASTRA Backend       │────►│  Whisper API      │
│  (React/Vite)   │     │  (Session/Notes/WS)  │     │  (Transcription)  │
│  :5173          │     │  :8000               │     │  :8001            │
└─────────────────┘     └──────────┬────────────┘     └────────┬─────────┘
        │                         │                          │
        │ 1. Create session        │ 2. POST /stt/upload      │
        │ 2. Connect WebSocket     │    (audio file)          │
        │ 3. Upload audio chunks   │ 3. POST Whisper API       │
        │                          │    (callback=Backend)      │
        │                          │ 4. Whisper callback       │
        │ 5. stt.task.done WS      │    → update STT task     │
        │    note.created WS       │    → create Note         │
        └──────────────────────────┴──────────────────────────┘
```

## 数据流

1. **Frontend** 创建 session，连接 WebSocket，每 3s 将 PCM 转为 WAV 上传到 Backend
2. **Backend** 收到音频 → 创建 STT task (pending) → 转发到 Whisper API，传入 `callback_url`
3. **Whisper API** 转录完成后 POST 到 Backend 的 callback
4. **Backend** callback 中：更新 STT task，若未过滤则创建 Note，通过 WebSocket 广播
5. **Frontend** 通过 WebSocket 收到 `stt.task.done`、`note.created`，更新 UI

## 端口与配置

| 服务 | 默认端口 | 环境变量 |
|------|----------|----------|
| ASTRA Backend | 8000 | - |
| Whisper API | 8001 | `PORT=8001` |
| Frontend | 5173 | `VITE_API_URL` |

Backend 需配置 Whisper API 地址：`WHISPER_API_URL=http://127.0.0.1:8001`

## 一键启动

```bash
# 从项目根目录执行（同时启动 Whisper + Backend）
./scripts/start_astra.sh
```

若 Backend 不在默认路径，可设置：

```bash
ASTRA_BACKEND_PATH=/path/to/ASTRA-dev-feature1/backend ./scripts/start_astra.sh
```

按 Ctrl+C 可停止所有服务。

---

## 手动启动顺序

```bash
# 1. 启动 Whisper API (端口 8001)
cd Fast-Powerful-Whisper-AI-Services-API
PORT=8001 python start.py

# 2. 启动 ASTRA Backend (端口 8000)
cd /path/to/ASTRA-dev-feature1/backend
pip install -r requirements.txt   # 含 httpx
cp .env.example .env              # 可选，使用默认值可省略
uvicorn app.main:app --reload --port 8000

# 3. 启动 Frontend
cd /path/to/ASTRA-dev-feature1/frontend   # 或 ~/Desktop/ASTRA-dev-feature1/frontend
npm install && npm run dev
# 默认 VITE_API_URL=http://localhost:8000/api
```

### 环境变量 (Backend)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WHISPER_API_URL` | `http://127.0.0.1:8001` | Whisper API 地址 |
| `BACKEND_BASE_URL` | `http://127.0.0.1:8000` | 回调地址，Whisper 完成时 POST 到此 |

## realtime_demo.py 集成

`realtime_demo.py`（VAD + 1.5s 静音触发）已支持 Backend 集成模式：

```bash
# 集成模式：上传到 Backend，Notes 同步到 Frontend
python realtime_demo.py --backend-url http://127.0.0.1:8000

#  standalone 模式：直接调用 Whisper API
python realtime_demo.py --api-url http://127.0.0.1:8001
```

默认使用 `--backend-url`，需先启动 Backend 和 Whisper API。

---

## API 变更

### Backend 新增

- **POST `/api/sessions/{sid}/stt/upload`** — 接收音频文件 (multipart)
  - 创建 STT task
  - 转发到 Whisper API
  - callback 由 Whisper 完成时触发

- **POST `/api/internal/whisper-callback`** — Whisper 回调 (内部用)
  - 由 Whisper API 在任务完成时 POST
  - 更新 STT task、创建 Note

### Frontend 修改

- `useWhisper.ts` 中 `flushChunk`：将 PCM 转为 WAV Blob，POST 到 Backend `/api/sessions/{sid}/stt/upload`

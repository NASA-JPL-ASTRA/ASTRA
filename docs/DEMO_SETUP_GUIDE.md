# ASTRA Live Transcription Demo — 运行指南

本文档帮助团队成员（Mac / Windows）在本地成功运行 Live Transcription Demo。

---

## 一、项目结构

Demo 由三部分整合在同一项目内：

```
ASTRA-quickdemo/
├── app/                # Whisper API（转录服务）
├── backend/             # ASTRA Backend (FastAPI)
├── frontend/            # React 前端
├── realtime_demo.py     # 实时 STT Demo
├── scripts/             # 一键启动脚本
└── docs/                # 文档
```

---

## 二、环境依赖

### 1. 系统级依赖（Mac / Windows 均需）

| 依赖 | 版本要求 | 用途 |
|------|----------|------|
| **Python** | 3.10+（推荐 3.12） | Whisper API、Backend、realtime_demo |
| **Node.js** | 18+（推荐 20+） | 前端构建与开发服务器 |
| **FFmpeg** | 最新稳定版 | 音频处理 |
| **Git** | 最新版 | 克隆仓库 |

### 2. 安装 FFmpeg

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Windows (winget 或 Chocolatey):**
```powershell
# 使用 winget
winget install FFmpeg

# 或使用 Chocolatey
choco install ffmpeg
```

安装后确认：`ffmpeg -version`

---

## 三、克隆仓库

```bash
git clone https://github.com/YOUR_ORG/ASTRA-quickdemo.git
cd ASTRA-quickdemo
```

---

## 四、安装依赖

### 1. Whisper API（Python）

```bash
cd ASTRA-quickdemo

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 若需运行 realtime_demo（可选）
pip install -r requirements-realtime.txt
```

### 2. ASTRA Backend（Python）

```bash
cd backend

# 使用同一虚拟环境，或新建
pip install -r requirements.txt

# 可选：复制环境配置
cp .env.example .env
# 编辑 .env 设置 WHISPER_API_URL 等
```

### 3. Frontend（Node.js）

```bash
cd frontend   # 若在 backend 目录，则为 cd ../frontend

# 安装依赖
npm install
# 或
pnpm install
# 或
yarn install
```

---

## 五、运行 Demo

### 方式 A：一键启动（推荐）

**macOS / Linux:**
```bash
cd ASTRA-quickdemo

# 启动 Whisper API + Backend（默认使用本机 backend/）
./scripts/start_astra.sh

# 可选：清空任务队列后启动
CLEAR_QUEUE_ON_START=1 ./scripts/start_astra.sh
```

**Windows (CMD 或 PowerShell):**
```cmd
cd ASTRA-quickdemo

REM 启动 Whisper API + Backend（会打开两个新窗口）
scripts\start_astra.bat

REM 可选：清空任务队列后启动
set CLEAR_QUEUE_ON_START=1
scripts\start_astra.bat
```

启动成功后，**另开一个终端**启动前端：

```bash
cd ASTRA-quickdemo/frontend
npm run dev
```

浏览器访问：`http://localhost:5173` → 进入 **Active Session** → **Start Recording**。

### 方式 B：Windows 一键启动

在项目根目录执行（需已安装 Python 并配置好环境）：

```cmd
scripts\start_astra.bat
```

会新开两个窗口分别运行 Whisper API 和 Backend，本窗口可关闭。然后另开终端启动 Frontend。

### 方式 C：手动启动（各平台通用）

**终端 1 — Whisper API:**
```bash
cd ASTRA-quickdemo
PORT=8001 python start.py
```

**终端 2 — ASTRA Backend:**
```bash
cd ASTRA-quickdemo/backend
WHISPER_API_URL=http://127.0.0.1:8001 python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**终端 3 — Frontend:**
```bash
cd ASTRA-quickdemo/frontend
npm run dev
```

### 方式 D：仅运行 realtime_demo（无前端）

```bash
cd ASTRA-quickdemo

# 先启动 Whisper + Backend（方式 A 或 B）

# 再运行 demo
python realtime_demo.py --backend-url http://127.0.0.1:8000
```

---

## 六、端口与访问地址

| 服务 | 端口 | 地址 |
|------|------|------|
| Whisper API | 8001 | http://localhost:8001 |
| ASTRA Backend | 8000 | http://localhost:8000 |
| Frontend | 5173 | http://localhost:5173 |

---

## 七、常见问题

### 1. 找不到 ASTRA Backend

Backend 应位于项目内 `backend/` 目录。若使用自定义路径可显式设置：

```bash
# macOS/Linux
export ASTRA_BACKEND_PATH="/绝对路径/backend"

# Windows (PowerShell)
$env:ASTRA_BACKEND_PATH = "C:\path\to\backend"
```

### 2. 麦克风无权限

浏览器需允许麦克风权限；HTTPS 或 `localhost` 下通常可用。

### 3. 转写一直为 “—”

- 检查 Backend 与 Whisper API 是否都在运行
- 检查浏览器控制台是否有 WebSocket 报错
- 确认说话后停顿约 1.5 秒，VAD 才会发送 chunk

### 4. Windows 下 `start_astra.sh` 无法执行

使用 **方式 B** 手动启动，或安装 Git Bash / WSL 后执行：

```bash
bash scripts/start_astra.sh
```

### 5. Python 依赖安装失败

优先使用 Python 3.10–3.12，并确保已安装 FFmpeg：

```bash
ffmpeg -version
```

---

## 八、依赖清单速查

| 组件 | 依赖文件 |
|------|----------|
| Whisper API | `requirements.txt` |
| realtime_demo | `requirements-realtime.txt` |
| ASTRA Backend | `backend/requirements.txt` |
| Frontend | `frontend/package.json` |

---

## 九、Demo 演示流程建议

1. 启动所有服务（Whisper + Backend + Frontend）
2. 打开 Live Transcription 页面，点击 **Start Recording**
3. 正常语速说 1–2 句英文，停顿约 1.5 秒
4. 观察转写与置信度颜色（绿 / 黄 / 红）
5. 点击 **Stop** 保存 session，在 Structured Notes 中查看

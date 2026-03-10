# ASTRA Frontend

**Advanced System for Testbed Recording and Analysis**
NASA JPL Robotic Testbed AI-Powered Documentation Assistant

[English](#english) | [中文](#中文)

---

<a id="english"></a>

## English

### Overview

ASTRA (Advanced System for Testbed Recording and Analysis) is an AI-powered assistant designed for NASA JPL's robotic testbed operations. This frontend application provides a real-time collaborative interface for operators to interact with the system, view transcriptions, manage structured logs, monitor telemetry data, and access contextual documents.

### Quick Start

```bash
npm install        # Install dependencies
npm run dev        # Start dev server (http://localhost:5173)
npm run build      # Production build
npx tsc --noEmit   # Type-check
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | React 18 + TypeScript | UI components with type safety |
| Build | Vite 7 | Fast HMR dev server |
| Styling | Tailwind CSS v4 | Utility-first CSS |
| State | Zustand | Lightweight global state |
| Routing | React Router v7 | Client-side routing |
| Charts | Recharts | Telemetry visualization |
| Icons | Lucide React | Consistent icon set |

### Project Structure

```
src/
├── components/
│   ├── layout/           # Sidebar, Header, MainLayout
│   ├── session/          # Active session (transcription panel)
│   ├── common/           # Shared UI components
│   ├── dashboard/        # Dashboard widgets
│   ├── documents/        # Document & telemetry data management
│   └── history/          # Session history components
├── hooks/
│   └── useWhisper.ts     # Core hook: mic capture → WebSocket → Whisper STT
├── pages/
│   ├── Dashboard.tsx     # Mission control overview
│   ├── SessionPage.tsx   # Active session (live transcription canvas)
│   ├── HistoryPage.tsx   # Structured notes browser
│   ├── SessionDetailPage.tsx  # View single structured note detail
│   ├── DocumentsPage.tsx # Documents & telemetry data
│   └── SettingsPage.tsx  # User management, general, audio, AI settings
├── store/
│   └── useStore.ts       # Zustand global state
├── types/
│   └── index.ts          # TypeScript interfaces
├── mock/
│   └── data.ts           # Mock data for development
├── App.tsx               # Router setup
├── main.tsx              # Entry point
└── index.css             # Tailwind + custom theme
```

### Pages

#### 1. Dashboard (`/`)
Mission control with KPIs (latency, WER, active streams), recent sessions, and system health.

#### 2. Active Session (`/session`) — Core Page
Full-screen live transcription canvas powered by Whisper STT.

- Browser microphone capture via Web Audio API
- Audio chunks sent to backend via WebSocket
- Real-time transcription results streamed back and displayed
- Speaker identification with color-coded avatars
- Confidence scores per entry
- **Session controls**: Start → Pause / Resume → Stop
- On **Stop**, the session is automatically saved to Structured Notes
- Current local time displayed below the title; recording duration shown in stats bar

#### 3. Structured Notes (`/history`)
Browse saved session recordings. Each note is a structured record of a completed session.

- Search by name, description, or testbed
- Click to view full transcription content (`/history/:id`)
- **Export** individual notes as TXT or JSON
- **Delete** individual notes (double-click confirmation)

#### 4. Documents & Data (`/documents`)
Two tabs:
- **Documents**: Upload system manuals/procedures for RAG contextual awareness (PDF, DOCX, TXT, MD)
- **Telemetry Data**: View live telemetry streams with current values, ranges, thresholds, and status

#### 5. Settings (`/settings`)
- **User**: Profile card, login/logout
- **General**: Language, region/timezone, date format, 24-hour clock, theme
- **Audio & Speech**: STT model, noise suppression, multi-speaker, voice commands, confidence threshold
- **AI & LLM**: Language model, RAG toggle, max tokens, temperature
- Telemetry, Storage, Security (placeholders)

### Whisper Integration Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  FRONTEND (Browser)                                          │
│                                                              │
│  navigator.mediaDevices.getUserMedia()                       │
│       │                                                      │
│       ▼                                                      │
│  AudioContext + ScriptProcessor/AudioWorklet                  │
│       │  PCM 16-bit, 16kHz mono                              │
│       ▼                                                      │
│  useWhisper hook                                             │
│       │  sends audio chunks every ~3 seconds                 │
│       │  supports: start / pause / resume / stop             │
│       ▼                                                      │
│  WebSocket  ──────────────────────────────►  BACKEND         │
│  ws://host/ws/transcribe                                     │
│                                                              │
│  WebSocket  ◄──────────────────────────────  BACKEND         │
│       │  receives JSON: {text, confidence, speaker, ...}     │
│       ▼                                                      │
│  Zustand Store → TranscriptionPanel renders                  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  BACKEND (Python / FastAPI)                                  │
│                                                              │
│  WebSocket /ws/transcribe                                    │
│       │  receives PCM audio chunks                           │
│       ▼                                                      │
│  Whisper Model (whisper-large-v3 / faster-whisper)           │
│       │  transcribes audio → text                            │
│       ▼                                                      │
│  Speaker Diarization (optional, e.g. pyannote)               │
│       │                                                      │
│       ▼                                                      │
│  Returns JSON to frontend via WebSocket                      │
│  { id, text, confidence, speaker_id, timestamp }             │
└──────────────────────────────────────────────────────────────┘
```

#### WebSocket Protocol

**Frontend → Backend (Binary):**
Raw PCM audio bytes, 16-bit signed integer, 16kHz, mono.

**Backend → Frontend (JSON):**
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

**Control Messages:**
```json
{ "type": "start", "config": { "language": "en", "model": "large-v3" } }
{ "type": "pause" }
{ "type": "resume" }
{ "type": "stop" }
```

### Collaboration Guide

#### Team Structure

```
┌─────────────┐    WebSocket / REST API    ┌─────────────────┐
│  Frontend   │ ◄────────────────────────► │    Backend       │
│  Team       │                            │    Team          │
│  (React)    │                            │  (FastAPI/Flask) │
└─────────────┘                            └────────┬────────┘
                                                    │
                                                    ▼
                                           ┌─────────────────┐
                                           │   Model Team     │
                                           │  (Whisper, LLM,  │
                                           │   RAG Pipeline)  │
                                           └─────────────────┘
```

#### API Contract

All teams must agree on interfaces **before** coding. Define them in a shared doc or OpenAPI spec.

| Endpoint | Method | Owner | Description |
|----------|--------|-------|-------------|
| `ws://host/ws/transcribe` | WebSocket | Backend + Model | Real-time audio → text |
| `POST /api/sessions` | REST | Backend | Create a new session |
| `GET /api/sessions` | REST | Backend | List sessions |
| `GET /api/sessions/:id/logs` | REST | Backend | Get session logs |
| `PUT /api/logs/:id` | REST | Backend | Edit a log entry |
| `POST /api/documents` | REST | Backend | Upload document for RAG |
| `GET /api/telemetry/:stream` | REST/WS | Backend | Telemetry data |

#### For Backend Team

1. **WebSocket endpoint for Whisper transcription** — accept binary PCM audio (16kHz, 16-bit, mono), return JSON, support `start`/`pause`/`resume`/`stop` control messages, stream partial results (`is_final: false`)
2. **REST API for sessions & logs CRUD** — consistent JSON envelope `{ data, error, meta }`
3. **CORS** — allow `http://localhost:5173` (and `5174`, etc.) in development

#### For Model Team

1. **Whisper model wrapped behind a WebSocket handler** — frontend sends ~3s audio chunks, model returns text within < 10 seconds
2. **Speaker diarization** (if available) — assign `speaker_id` per utterance
3. **Confidence score** — return per-utterance confidence (0.0–1.0); frontend color-codes: green (>90%), amber (80–90%), red (<80%)

**Recommended setup:**
```python
from faster_whisper import WhisperModel
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
segments, info = model.transcribe(audio_array, beam_size=5, language="en")
```

#### For Frontend Team

1. **Mock mode** (default): works with built-in mock data, no backend needed
2. **Live mode**: set env variables in `.env.local`
3. **`useWhisper` hook** handles all audio/WebSocket logic: `startRecording()`, `pauseRecording()`, `resumeRecording()`, `stopRecording()`

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_WS_URL` | `ws://localhost:8000/ws/transcribe` | Whisper WebSocket URL |
| `VITE_API_URL` | `http://localhost:8000/api` | Backend REST API base URL |

### Design System

Dark "space control" theme inspired by NASA mission control interfaces.

| Token | Value | Usage |
|-------|-------|-------|
| `space-black` | `#0a0e17` | Background |
| `space-panel` | `#131d2a` | Panel backgrounds |
| `accent-cyan` | `#00d4ff` | Primary accent |
| `accent-green` | `#00e676` | Success, nominal |
| `accent-amber` | `#ffab00` | Warning |
| `accent-red` | `#ff5252` | Critical, recording |
| `accent-purple` | `#b388ff` | AI-generated content |
| `font-sans` | Inter | UI text |
| `font-mono` | JetBrains Mono | Data, timestamps |

### Scripts

```bash
npm run dev      # Start dev server
npm run build    # Production build
npm run preview  # Preview production build
```

---

<a id="中文"></a>

## 中文

### 概述

ASTRA（高级测试平台记录与分析系统）是专为 NASA JPL 机器人测试平台操作设计的 AI 助手。本前端应用为操作员提供实时协作界面，支持查看转录、管理结构化日志、监控遥测数据和访问上下文文档。

### 快速开始

```bash
npm install        # 安装依赖
npm run dev        # 启动开发服务器 (http://localhost:5173)
npm run build      # 生产构建
npx tsc --noEmit   # 类型检查
```

### 技术栈

| 层级 | 技术 | 用途 |
|------|-----|------|
| 框架 | React 18 + TypeScript | 带类型安全的 UI 组件 |
| 构建 | Vite 7 | 快速热更新开发服务器 |
| 样式 | Tailwind CSS v4 | 原子化 CSS |
| 状态 | Zustand | 轻量全局状态管理 |
| 路由 | React Router v7 | 客户端路由 |
| 图表 | Recharts | 遥测数据可视化 |
| 图标 | Lucide React | 统一图标库 |

### 项目结构

```
src/
├── components/
│   ├── layout/           # 侧边栏、顶部栏、主布局
│   ├── session/          # 活跃会话组件（转录面板）
│   ├── common/           # 共享 UI 组件
│   ├── dashboard/        # 仪表盘组件
│   ├── documents/        # 文档与遥测数据管理
│   └── history/          # 会话历史组件
├── hooks/
│   └── useWhisper.ts     # 核心 Hook：麦克风采集 → WebSocket → Whisper 语音转文字
├── pages/
│   ├── Dashboard.tsx     # 任务控制总览
│   ├── SessionPage.tsx   # 活跃会话（实时转录画布）
│   ├── HistoryPage.tsx   # 结构化笔记浏览
│   ├── SessionDetailPage.tsx  # 查看单条结构化笔记详情
│   ├── DocumentsPage.tsx # 文档与遥测数据
│   └── SettingsPage.tsx  # 用户管理、通用设置、音频、AI 设置
├── store/
│   └── useStore.ts       # 全局状态
├── types/
│   └── index.ts          # 类型定义
├── mock/
│   └── data.ts           # 开发用模拟数据
├── App.tsx               # 路由配置
├── main.tsx              # 入口文件
└── index.css             # Tailwind + 自定义主题
```

### 页面概览

#### 1. 仪表盘 (`/`)
任务控制中心：KPI 指标（延迟、词错率、活跃流）、最近会话、系统健康状态。

#### 2. 活跃会话 (`/session`) — 核心页面
全屏实时转录画布，由 Whisper 语音转文字驱动。

- 浏览器麦克风采集（Web Audio API）
- 音频分块通过 WebSocket 发送到后端
- 实时转录结果流式返回并显示
- 说话人识别（带颜色标记的头像）
- 每条记录的置信度评分
- **会话控制**：开始 → 暂停 / 恢复 → 停止
- 点击**停止**后，会话自动保存到结构化笔记
- 标题下方显示当前地区时间；统计栏显示录制时长

#### 3. 结构化笔记 (`/history`)
浏览已保存的会话录制。每条笔记是一个完成会话的结构化记录。

- 按名称、描述或测试平台搜索
- 点击查看完整转录内容（`/history/:id`）
- **导出**单条笔记为 TXT 或 JSON
- **删除**单条笔记（双击确认）

#### 4. 文档与数据 (`/documents`)
两个标签页：
- **文档**：上传系统手册/流程文档用于 RAG 上下文感知（PDF、DOCX、TXT、MD）
- **遥测数据**：查看实时遥测数据流，含当前值、范围、阈值和状态

#### 5. 设置 (`/settings`)
- **用户**：个人信息卡片、登录/登出
- **通用**：语言、地区/时区、日期格式、24 小时制、主题
- **音频与语音**：STT 模型、噪音抑制、多说话人、语音命令、置信度阈值
- **AI 与 LLM**：语言模型、RAG 开关、最大 token 数、温度
- 遥测、存储、安全（占位符）

### Whisper 集成架构

```
┌──────────────────────────────────────────────────────────────┐
│  前端 (浏览器)                                                │
│                                                              │
│  navigator.mediaDevices.getUserMedia()                       │
│       │                                                      │
│       ▼                                                      │
│  AudioContext + ScriptProcessor/AudioWorklet                  │
│       │  PCM 16-bit, 16kHz 单声道                             │
│       ▼                                                      │
│  useWhisper hook                                             │
│       │  每 ~3 秒发送一个音频块                                 │
│       │  支持：开始 / 暂停 / 恢复 / 停止                        │
│       ▼                                                      │
│  WebSocket  ──────────────────────────────►  后端             │
│  ws://host/ws/transcribe                                     │
│                                                              │
│  WebSocket  ◄──────────────────────────────  后端             │
│       │  接收 JSON: {text, confidence, speaker, ...}          │
│       ▼                                                      │
│  Zustand Store → TranscriptionPanel 渲染                      │
└──────────────────────────────────────────────────────────────┘
```

#### WebSocket 协议

**前端 → 后端（二进制）：** 原始 PCM 音频字节，16位有符号整数，16kHz，单声道。

**后端 → 前端（JSON）：**
```json
{
  "id": "tr_1739...",
  "text": "正在初始化关节三的校准序列。",
  "confidence": 0.94,
  "speaker_id": "speaker_0",
  "timestamp": "2026-02-16T22:30:00.000Z",
  "is_final": true
}
```

**控制消息：**
```json
{ "type": "start", "config": { "language": "en", "model": "large-v3" } }
{ "type": "pause" }
{ "type": "resume" }
{ "type": "stop" }
```

### 团队协作指南

#### 给后端团队

1. **Whisper 转录 WebSocket 端点** — 接收二进制 PCM 音频、返回 JSON、支持 `start`/`pause`/`resume`/`stop` 控制消息
2. **会话和日志 CRUD 的 REST API** — 统一格式 `{ data, error, meta }`
3. **CORS 配置** — 开发环境允许 `http://localhost:5173`

#### 给模型团队

1. **Whisper 模型封装在 WebSocket 处理器后面** — 前端连续发送约 3 秒的音频分块，模型在 10 秒内返回文本
2. **说话人分离**（如可用）— 为每句话分配 `speaker_id`
3. **置信度评分** — 返回每句话的置信度（0.0–1.0）

**推荐配置：**
```python
from faster_whisper import WhisperModel
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
segments, info = model.transcribe(audio_array, beam_size=5, language="en")
```

#### 给前端团队

1. **模拟模式**（默认）：使用内置模拟数据，无需后端
2. **实时模式**：在 `.env.local` 中设置环境变量
3. **`useWhisper` Hook** 处理所有音频/WebSocket 逻辑：`startRecording()`、`pauseRecording()`、`resumeRecording()`、`stopRecording()`

### 环境变量

| 变量 | 默认值 | 描述 |
|------|-------|------|
| `VITE_WS_URL` | `ws://localhost:8000/ws/transcribe` | Whisper WebSocket 地址 |
| `VITE_API_URL` | `http://localhost:8000/api` | 后端 REST API 基础地址 |

### 脚本命令

```bash
npm run dev      # 启动开发服务器
npm run build    # 生产构建
npm run preview  # 预览生产构建
```

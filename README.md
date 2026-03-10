<div align="center">
<a href="https://github.com/Evil0ctal/Fast-Powerful-Whisper-AI-Services-API" alt="logo" ><img src="https://raw.githubusercontent.com/Evil0ctal/Fast-Powerful-Whisper-AI-Services-API/refs/heads/main/github/logo/logo.jpg" width="150"/></a>
</div>
<h1 align="center">Fast-Powerful-Whisper-AI-Services-API</h1>

<div align="center">

[English](./README.md) | [简体中文](./README-ZH.md)

<hr>
</div>

<div align="left">

🚀 The vision of 「 **[Fast-Powerful-Whisper-AI-Services-API](https://github.com/Evil0ctal/Fast-Powerful-Whisper-AI-Services-API)** 」is to create a powerful, ready-to-use [Whisper](https://github.com/openai/whisper) service API, designed for high performance, scalability, and distributed processing requirements. Built around a producer-consumer model, it is ideal for large-scale, highly efficient automatic speech recognition scenarios. This project leverages the OpenAI Whisper model and the Faster Whisper model, which delivers faster inference with nearly equivalent accuracy. It supports high-quality multilingual transcription and translation tasks. With an integrated crawler module, it easily processes videos from social media platforms like Douyin and TikTok, creating tasks with just a link input.

The system efficiently manages resource scheduling and task management through an asynchronous model pool solution, supporting parallel computation on multiple GPUs for fully localized, scalable, and reliable operations. Additionally, the project plans to support a flexible custom component and workflow design, allowing users to define complex multi-step workflows via JSON files or extend functionality by writing custom components in Python. Built-in modules for high-performance asynchronous HTTP, file I/O, and database operations enable users to develop custom services or task processors, with future plans to integrate with LLM APIs like ChatGPT to realize a complete workflow from automatic speech recognition to natural language processing and analysis.

</div>

## 🌟 Key Features

* **Asynchronous Design** : Built on Python 3.11’s asyncio capabilities, all modules are asynchronous, enabling efficient request handling and enhancing overall system stability and high concurrency.
* **Built-in Document UI** : Leveraging FastAPI’s auto-generated OpenAPI JSON, the project includes an interactive Swagger UI for visual API testing in the browser. Swagger UI provides bilingual descriptions in English and Chinese with default parameter settings, enabling quick start testing for users.
* **High Accuracy** : The latest `large-v3` model ensures accurate output, and Faster Whisper significantly reduces inference time while maintaining high accuracy.
* **Distributed Deployment** : The project can access and store tasks in a shared database and plans seamless integration with Kafka, achieving a harmonious integration of FastAPI and Kafka for building real-time, intelligent Web APIs.
* **Asynchronous Model Pool** : Implements an efficient asynchronous AI model pool that supports multi-instance concurrent processing for OpenAI Whisper and Faster Whisper models under thread-safe conditions. In CUDA-accelerated, multi-GPU environments, intelligent loading mechanisms dynamically assign models to GPUs, balancing load and optimizing task processing. Note: Concurrency is unavailable on single-GPU setups.
* **Asynchronous Database** : Supports MySQL and SQLite databases. It can run locally without MySQL, as SQLite allows for quick setup. When using MySQL, it facilitates distributed computing with multiple nodes accessing the same database for tasks.
* **Asynchronous Web Crawlers** : Equipped with data crawler modules for multiple platforms, currently supporting `Douyin` and `TikTok`. By simply entering the video link, users can quickly process media for speech recognition, with plans for more social media platform support in the future.
* **ChatGPT integration**: This project has integrated ChatGPT as the support for the LLM part, and can use the data in the database to interact with ChatGPT.
* **Workflow and Component Design (Pending)** : With a focus on Whisper transcription tasks, the project will support a highly customizable workflow system. Users can define components, task dependencies, and execution orders in JSON files or write custom components in Python, facilitating complex multi-step processing.
* **Event-Driven Intelligent Workflow (Pending)** : The workflow system supports event-driven triggers, including time-based, manual, or crawler module auto-triggers. More than single-task processing, workflows will offer intelligent, automated control with conditional branching, task dependencies, dynamic parameter passing, and retry strategies.

## 💫 Suitable Scenarios

* **Media Data Processing** : Ideal for large-scale speech-to-text processing, such as transcription, analysis, translation, and subtitle generation of online or local media files.
* **Automated Workflow** : While the project doesn’t yet include workflows, it can integrate with other platforms' workflow systems through the API, enabling complex automated task execution for scenarios requiring multi-step processing and conditional control.
* **Dynamic Data Collection** : Combined with asynchronous crawler modules, the system can automatically collect and process online data, storing processed results for analysis.
* **Distributed Computing Utilization** : When leveraging distributed, fragmented computing resources, the gateway-based structure enables efficient utilization of dispersed computing power.

## 🚩 Implemented Features

* **Create Task** : Supports media file upload (`file_upload`) or specifying a media file link (`file_url`) as the data source for the task, with configurable parameters for fine-grained task control.
* **Set Task Type** : Users can set the task type by adjusting the `task_type` parameter. Currently supports media file transcription (`transcribe`) and automatic translation (`translate`).
* **Set Task Priority** : Users can assign task priority via the `priority` parameter, supporting three priority levels: (`high`, `normal`, `low`).
* **Task Callback Notification** : Users can specify a `callback_url` to receive task completion data. Upon task completion, an HTTP POST request is sent to the specified address, and callback statuses are logged in the database for review.
* **Multi-Platform Support** : Users can create Douyin and TikTok tasks through respective interfaces, or manually specify a video link with the `platform` parameter to mark the platform name.
* **Configure Whisper Parameters** : Users can customize the model’s inference by setting decoding parameters. Supported parameters include (`language`, `temperature`, `compression_ratio_threshold`, `no_speech_threshold`, `condition_on_previous_text`, `initial_prompt`, `word_timestamps`, `prepend_punctuations`, `append_punctuations`, `clip_timestamps`, `hallucination_silence_threshold`).
* **Task Querying** : Users can query the task list with various filters, including task status, priority, creation time, language, and engine name. This endpoint supports pagination, with `limit` and `offset` parameters controlling records per page.
* **Delete Task** : Users can delete tasks by `task_id`, permanently removing task data.
* **Get Task Results** : Users can retrieve results for a specified task by `task_id`.
* **Extract Audio from Video** : Allows users to extract audio from uploaded video files, supporting sample rate (`sample_rate`), bit depth (`bit_depth`), and output format (`output_format`) settings.
* **Generate Subtitle File** : Users can generate subtitles for a task by specifying the `task_id` and output format (`output_format`). Currently supports (`srt`) and (`vtt`) subtitle file formats.
* **Create TikTok Task** : Users can create tasks by crawling TikTok videos through a video link.
* **Create Douyin Task** : Users can create tasks by crawling Douyin videos through a video link.
- **Use ChatGPT to summarize tasks**: Users can use the task ID to give the translated natural language to ChatGPT for content summarization and other interactions, and support selecting models and custom prompt words in the interface.

## 📸 Project Screenshots

![2024_02_16_AM.png](https://github.com/Evil0ctal/Fast-Powerful-Whisper-AI-Services-API/blob/main/github/screenshots/2024_02_16_AM.png?raw=true)

## 🚀 Quick Deployment

Follow these steps to deploy the project quickly.

1. **Clone the Project** : Make sure `git` is installed, then open the console or terminal on your computer to run the following command:
   
   ```bash
   git clone https://github.com/Evil0ctal/Fast-Powerful-Whisper-AI-Services-API.git
   ```
2. **Python Environment** : Recommended Python version is `3.12` or `>=3.8`.
3. **Install FFmpeg** : The project uses [FFmpeg](https://www.ffmpeg.org/) for audio and video encoding and decoding. Install FFmpeg based on your OS:

- **Ubuntu or Debian**
  ```bash
  sudo apt update && sudo apt install ffmpeg
  ```
- **Arch Linux**
  ```bash
  sudo pacman -S ffmpeg
  ```
- **MacOS (Homebrew)**
  ```bash
  brew install ffmpeg
  ```
- **Windows (Chocolatey - Method 1)**
  ```bash
  choco install ffmpeg
  ```
- **Windows (Scoop - Method 2)**
  ```bash
  scoop install ffmpeg
  ```

4. **Install CUDA** : The project uses [CUDA](https://developer.nvidia.com/cuda-toolkit) for GPU-accelerated inference. Skip this step if using only the CPU.

* Download and install the appropriate version for your system:
* [CUDA Downloads](https://developer.nvidia.com/cuda-downloads)

5. **Install PyTorch with CUDA Support** : Ensure the CUDA Toolkit version matches your GPU.

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

6. **Install Project Dependencies** : Navigate to the project directory and install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
7. **Modify Default Configurations** : Most settings are customizable. Review the default configuration file at the following link. Changes to the configuration file may require a project restart.

* Default configuration file: [settings.py](https://github.com/Evil0ctal/Fast-Powerful-Whisper-AI-Services-API/blob/main/config/settings.py)

8. **Start the Project** : Ensure you are in the root project directory.

- Start the API:
  ```bash
  python3 start.py
  ```
- Access the API documentation in your browser at [http://127.0.0.1/](http://127.0.0.1/).

## ⚗️ Tech Stack

* **[OpenAI Whisper](https://github.com/openai/whisper)** - Speech recognition model
* **[Faster Whisper](https://github.com/SYSTRAN/faster-whisper)** - Faster speech recognition model
* **[ffmpeg](https://ffmpeg.org/)** - Audio/video format conversion
* **[torch](https://pytorch.org/)** - Deep learning framework
* **[FastAPI](https://github.com/fastapi/fastapi)** - High-performance API framework
* **[HTTPX](https://www.python-httpx.org/)** - Asynchronous HTTP client
* **[aiofile](https://github.com/Tinche/aiofiles)** - Asynchronous file operations
* **[aiosqlite](https://github.com/omnilib/aiosqlite)** - Asynchronous database operations
* **[aiomysql](https://github.com/aio-libs/aiomysql)** - Asynchronous database operations
* **[moviepy](https://github.com/Zulko/moviepy)** - Video editing
* **[pydub](https://github.com/jiaaro/pydub)** - Audio editing

## 🗃️ Project Structure

```
📂 Fast-Powerful-Whisper-AI-Services-API/
├── 📁 app/
│   ├── 📁 api/ -> API layer containing models and routes
│   │   ├── 📁 models/
│   │   │   ├── 📄 APIResponseModel.py -> Defines API response models
│   │   │   ├── 📄 ChatGPTTaskRequest.py -> Request model for ChatGPT tasks
│   │   │   ├── 📄 DouyinTaskRequest.py -> Request model for Douyin tasks
│   │   │   ├── 📄 TikTokTaskRequest.py -> Request model for TikTok tasks
│   │   │   ├── 📄 WhisperTaskRequest.py -> Request model for Whisper tasks
│   │   │   └── 📄 WorkFlowModels.py -> Workflow data models
│   │   ├── 📁 routers/
│   │   │   ├── 🔍 health_check.py -> Health check endpoint
│   │   │   ├── 📝 whisper_tasks.py -> Routes for Whisper tasks
│   │   │   ├── 🔄 work_flows.py -> Routes for workflow management
│   │   │   ├── 💬 chatgpt_tasks.py -> Routes for ChatGPT-related tasks
│   │   │   ├── 🌐 douyin_tasks.py -> Routes for Douyin-related tasks
│   │   │   └── 🎥 tiktok_tasks.py -> Routes for TikTok-related tasks
│   │   └── 📄 router.py -> Main router module
│   ├── 🕸️ crawlers/ -> Modules for web crawling
│   │   ├── 📁 platforms/
│   │   │   ├── 📁 douyin/
│   │   │   │   ├── 🐛 abogus.py -> (`・ω・´) Whats This? 
│   │   │   │   ├── 🚀 crawler.py -> Douyin data crawler
│   │   │   │   ├── 📡 endpoints.py -> API endpoints for Douyin crawler
│   │   │   │   ├── 🧩 models.py -> Models for Douyin data
│   │   │   │   ├── 🛠️ utils.py -> Utility functions for Douyin crawler
│   │   │   │   └── 📘 README.md -> Douyin module documentation
│   │   │   └── 📁 tiktok/
│   │   │       ├── 🚀 crawler.py -> TikTok data crawler
│   │   │       ├── 📡 endpoints.py -> API endpoints for TikTok crawler
│   │   │       ├── 🧩 models.py -> Models for TikTok data
│   │   │       └── 📘 README.md -> TikTok module documentation
│   ├── 💾 database/ -> Database models and management
│   │   ├── 📁 models/
│   │   │   ├── 📂 TaskModels.py -> Task-related database models
│   │   │   ├── 📂 WorkFlowModels.py -> Workflow-related database models
│   │   │   ├── 🧠 ChatGPTModels.py -> Models for ChatGPT tasks
│   │   │   └── 🕸️ CrawlerModels.py -> Models for crawlers and platforms
│   │   └── 🗄️ DatabaseManager.py -> Handles database connections
│   ├── 🌐 http_client/ -> HTTP client setup
│   │   ├── ⚙️ AsyncHttpClient.py -> Asynchronous HTTP client
│   │   └── ❗ HttpException.py -> Custom HTTP exceptions
│   ├── 🤖 model_pool/ -> Model pooling and management
│   │   └── 🧠 AsyncModelPool.py -> Asynchronous model pool manager
│   ├── 🔄 processors/ -> Task and workflow processors
│   │   ├── 📋 task_processor.py -> Processes Whisper tasks
│   │   └── 🛠️ workflow_processor.py -> Processes workflows
│   ├── 🛎️ services/ -> Service layer for API functions
│   │   ├── 📲 callback_service.py -> Handles callbacks
│   │   ├── 🔄 workflow_service.py -> Workflow handling services
│   │   └── 🗣️ whisper_service.py -> Whisper model-related services
│   ├── 🧰 utils/ -> Utility functions
│   │   ├── 📂 file_utils.py -> File operations and management
│   │   └── 🔍 logging_utils.py -> Logging utilities
│   ├── ⚙️ workflows/ -> Workflow components
│   │   └── 🧩 components/
│   │       ├── 🛠️ base_component.py -> Base workflow component
│   │       ├── 📄 component_a.py -> Custom workflow component A
│   │       └── 📄 component_b.py -> Custom workflow component B
│   └── 🚀 main.py -> Application entry point
├── ⚙️ config/
│   └── 🛠️ settings.py -> Configuration file
├── 📁 temp_files/ -> Temporary files folder
│   └── 📂 -> Default TEMP Files Folder
├── 📁 log_files/ -> Log files folder
│   └── 📂 -> Default LOG Files Folder
├── 📂 WhisperServiceAPI.db -> Default SQLite DB File
├── 📄 requirements.txt -> Python package requirements
└── 📝 start.py -> Run to start the API
```

## 🛠️ Usage Guide

* Navigate to the project directory and use the following command to start the API service:
  * `python3 start.py`
* You can then access `http://localhost` to view the API documentation and test the endpoints on the web.

## 🧵 Directory Structure Overview

### Introduction:

> If you're interested in contributing to this project, I recommend starting with this section to quickly understand the project’s design and the role of each module. The project code includes comprehensive bilingual (Chinese and English) comments, internal explanations, and variable descriptions, with `Typing` annotations throughout. While it's not perfect, I’ve aimed for clarity and elegance to make it easy to follow. I hope everyone also takes the chance to learn asynchronous programming, offers optimization suggestions, and together, we can improve the project to be more efficient and robust!

#### 📁 `app/api/` - API Layer

* **Tech Stack** : Built with the FastAPI framework, providing a high-performance, scalable routing system for API requests.
* **Features** :
  * **APIResponseModel.py** : Defines data models using Pydantic, ensuring consistency in API response structures.
  * **routers/** : Manages API endpoints for various functional modules:
    * `health_check.py` 💓: Quickly checks system health to monitor status.
    * `whisper_tasks.py` 📝: Routes for managing Whisper-related tasks, supporting task creation, querying, deletion, and more.
    * `work_flows.py` 🔄: Routes for workflow management, offering CRUD interfaces for workflows, with future plans for event-driven automated workflows.

#### 📁 `app/crawlers/` - Asynchronous Crawler Module

* **Tech Stack** : Uses `httpx` for asynchronous HTTP requests and Pydantic models for data validation.
* **Features** :
  * **platforms/** contains dedicated modules for platforms like Douyin and TikTok:
    * **douyin/** 🕸️: Handles Douyin video fetching, data extraction, and API integration, including custom models and utility classes.
    * **tiktok/** 🕹️: Supports TikTok data fetching and API data display, with plans to extend support to other social media platforms.
* **Problem-Solving** : Provides automated data scraping capabilities, integrating with the Whisper model for end-to-end media data processing.

#### 📁 `app/database/` - Database Management Module

* **Tech Stack** :
  * Utilizes `SQLAlchemy` with asynchronous support and `AsyncSession` for CRUD operations.
  * Supports `MySQL` and `SQLite` connections, with automatic reconnection, table checks, and initialization.
  * Integrates custom logging and error handling for reliable database operations.
* **Features** :
  * **DatabaseManager** 🗄️: Manages database connections and task CRUD operations, supporting complex queries and batch processing.
    * **Database Connection and Initialization** : Uses `_connect` for automatic retry and dynamic table checks, creating required tables on first connection.
    * **Task Management** : Flexible task management with methods like `add_task`, `get_task`, `update_task`, and `delete_task`, supporting asynchronous batch operations.
    * **Query and Filtering** : `query_tasks` method filters tasks based on conditions, with pagination and a condition builder `_build_query_conditions` for flexible querying.
    * **Callback Status Update** : `update_task_callback_status` method updates task callback information, including status code, message, and callback time.
    * **Workflow Management** : Supports workflow creation and management (`Workflow`), including tasks and notifications for automation flows.
* **Problem-Solving** :
  * **Reliable Database Connection** : Automatic retry and asynchronous context manager (`get_session`) for stable session management, solving disconnection and connection failure issues.
  * **Efficient Batch Operations** : Supports batch updates and deletions, suitable for large-scale task processing to reduce database interactions and improve efficiency.
  * **Flexible Task Querying** : Supports complex conditional querying with pagination, allowing the manager to meet diverse data access needs, facilitating project management and query optimization.

#### 📁 `app/http_client/` - Asynchronous HTTP Client Module

* **Tech Stack** :
  * Uses `httpx` for a high-performance asynchronous HTTP client, with proxy configuration, retry mechanism, and concurrency limits.
  * Custom exception handling for fine-grained error management based on HTTP status codes.
  * Implements network request optimizations like retry, backoff, and rate limiting.
* **Features** :
  * **AsyncHttpClient** 🌐: Provides a robust asynchronous HTTP client tool with:
    * **Request and Data Retrieval** : Supports common HTTP requests (`GET`, `POST`, `HEAD`), with `fetch_get_json` and `fetch_post_json` methods returning structured JSON data.
    * **File Download Support** : `download_file` method asynchronously downloads files, supporting large file chunking with detailed monitoring and error handling.
    * **Automatic Retry and Backoff** : `fetch_data` method offers exponential backoff for specific HTTP statuses, with customizable retry count for resilient network requests.
    * **Error Handling and Custom Exceptions** : Custom exceptions based on HTTP status for automated error type detection and logging, simplifying debugging and tracing.
    * **Proxy and Concurrency Management** : Dynamic proxy configuration and concurrency control, ensuring stability and control under heavy load.
* **Problem-Solving** :
  * **Network Request Optimization** : Automatically handles network interruptions and service unavailability with retry and backoff mechanisms for high availability.
  * **High-Concurrency Support** : Controls concurrency with `asyncio.Semaphore` to prevent overload, ensuring client stability under high-concurrency conditions.
  * **Configurable and Flexible Usage** : Context manager for resource release, dynamic headers for different APIs, and customizable proxy and timeout settings for adaptability.

#### 📁 `app/model_pool/` - Asynchronous Model Pool Module

* **Tech Stack** :
  * Combines `asyncio` with `concurrent.futures` to manage GPU and CPU model instances.
  * Thread-safe singleton design for `AsyncModelPool` to avoid resource competition in multi-threaded environments.
  * Device allocation and pool size optimization based on system hardware resources (e.g., GPU count and CPU threads).
* **Features** :
  * **AsyncModelPool** 🧠: A thread-safe, dynamically adjustable model pool management system with:
    * **Device Allocation and Dynamic Creation** : Automatically assigns devices based on GPU/CPU configuration, supporting multi-GPU concurrency with instance limits for efficient resource use.
    * **Initialization and Bulk Loading** : Asynchronous bulk loading for models through `initialize_pool`, reducing concurrent loading conflicts.
    * **Model Instance Acquisition and Return** : `get_model` and `return_model` methods for concurrent access and return, with options for “existing instance” and “dynamic creation.”
    * **Health Check and Destruction** : `_is_model_healthy` and `_destroy_model` ensure model health before use and resource cleanup after destruction to prevent memory leaks.
    * **Pool Size Adjustment** : `resize_pool` allows dynamic pool size changes, adding or removing instances based on load; further intelligent resizing logic is planned.
* **Problem-Solving** :
  * **Hardware Resource Optimization** : Dynamically adjusts pool size to prevent resource wastage and over-allocation, ensuring model instance count matches actual hardware configuration.
  * **Multi-Task Concurrency** : Efficient model instance allocation for multi-task requests, supporting GPU concurrency with instance limits to avoid resource competition.
  * **Automatic Fault Detection and Handling** : Health check and error handling for damaged/unavailable instances, maintaining stability within the pool.

#### 📁 `app/processors/` - Task and Workflow Processing Module

* **Tech Stack** :
  * Asynchronous processing with `asyncio`, combining thread pools and queues for concurrent task management. Uses `concurrent.futures` for threading efficiency.
  * Coordinates database and file operations for consistency and efficient resource usage under high concurrency.
* **Features** :
  * **task_processor.py** 📋: Implements background processing logic for Whisper tasks, with multi-queue design, event loop management, priority scheduling, parallel processing, database updates, and file operations.
    * **Task Queue and Priority Scheduling** : Multiple queues separate task types (e.g., cleanup, callbacks) with priority scheduling from database pulls, ensuring priority tasks are processed first.
    * **Parallel Task Processing** : Uses `_process_multiple_tasks` with thread pool to handle multiple tasks concurrently, improving throughput.
    * **Event Loop Management** : `run_loop` method starts the background event loop, continuously monitoring and processing task queues.
  * **workflow_processor.py** 🔄: Manages complex workflows with custom task dependencies, conditional checks, and automated scheduling; future plans include event-driven workflows.
* **Problem-Solving** :
  * **High-Concurrency Processing** : Combines event loop and threading for high-throughput, low-latency task processing under high load.
  * **Task Separation and Priority Support** : Multi-queue and priority scheduling ensure independent handling of different task types, with priority tasks processed first for enhanced responsiveness.
  * **Resource Optimization** : Effective GPU, database, and file storage management with `AsyncModelPool`, ensuring smooth processing of large-scale tasks.

#### 📁 `app/services/` - Service Layer Module

* **Tech Stack** :
  * Asynchronous service with `FastAPI` and `asyncio`, supporting audio processing, transcription, callback handling, and workflow control.
  * Integrates `pydub` and `moviepy` for audio and video processing, with `ThreadPoolExecutor` and `BackgroundTasks` for concurrent file processing and background tasks.
* **Features** :
  * **WhisperService** 🗣️: Manages audio extraction, transcription task creation, and subtitle generation.
    * **Audio Extraction** : `extract_audio_from_video` extracts audio from videos (WAV or MP3), with auto-cleanup of temporary files.
    * **Transcription Task Creation** : `create_whisper_task` accepts files or URLs, creates transcription tasks, and saves them to the database, generating output links.
    * **Subtitle Generation** : `generate_subtitle` converts transcription results to subtitle files (SRT or VTT), deleting temporary files upon completion.
  * **CallbackService** 📞: Handles callback notifications for tasks, sending results to predefined URLs and recording status.
    * **Callback Notification** : Uses `task_callback_notification` to send task results to callback URL after completion, logging response status.
    * **Retry Mechanism** : Supports failure retries with exponential backoff, ensuring reliable notification delivery.
  * **WorkflowService** 🔄 (Planned): Manages complex automated workflows.
    * **Workflow Control** : Plans to manage and execute dependent tasks with `WorkflowService`, supporting conditional logic, task dependencies, and callback management for automated bulk tasks.
    * **Task Coordination and Status Tracking** : Future plans include task status tracking and conditional controls, allowing flexible workflow designs.
    * **Extensibility** : Supports custom workflow steps and component configuration for adaptable workflows to fit business needs.
* **Problem-Solving** :
  * **Efficient Task Handling and Callback Notification** : Uses `TaskProcessor` for concurrent task processing and `CallbackService` for reliable post-completion notifications.
  * **Flexible Workflow and Extension Support** : `WorkflowService` offers a forward-looking framework, enabling users to manage and monitor task sequences and dependencies flexibly.
  * **Resource Management and File Cleanup** : `BackgroundTasks` allows for asynchronous file handling and cleanup, optimizing resource management for an efficient file processing experience.

#### 📁 `app/utils/` - Utility Module

* **Tech Stack** : Python native file handling and logging modules, with `aiofiles` for efficient asynchronous file handling and `ConcurrentRotatingFileHandler` for concurrent-safe log rotation.
* **Features** :
  * **file_utils.py** 📂: Provides file download, save, delete, and cleanup operations with file size limits and type checks for secure file handling, ideal for high-concurrency scenarios.
  * **logging_utils.py** 📊: Configures project logging with file and console output, log level control, auto-rotation (10MB), and backups for debugging and long-term storage.
* **Problem-Solving** :
  * **Resource Management** : Cleans up temporary files via asynchronous context manager and auto-delete mechanism, preventing resource leaks for system stability.
  * **File Security and Permission Control** : Strict file size, type, and permission controls to prevent unauthorized access and resource misuse.
  * **Concurrency Optimization** : Controls file operation concurrency using semaphores to improve I/O performance.
  * **Log Rotation and Security** : Ensures log output consistency and stability in high-concurrency environments with rotation and multi-process support for robust logging.

#### 📁 `app/workflows/` - Workflow Components (In Progress)

* **Tech Stack** : Python custom component design, with future support for task flow configuration based on JSON or custom Python.
* **Features** :
  * **components/** : Component modules to extend workflow functionality.
    * `base_component.py` 🛠️: Base class for workflow components, supporting general methods and events.
    * `component_a.py`, `component_b.py`: Examples of custom workflow components with extensible functionality.
* **Problem-Solving** : Highly extensible component design, allowing users to define complex task flows and custom components according to business needs.

#### 📄 `config/settings.py` - Configuration File

* **Tech Stack** : Uses `dotenv` for environment variable parsing, configuring FastAPI, database, and model pool parameters.
* **Features** :
  * Centralizes project configuration for easy management of database, model pool, and service addresses.
* **Problem-Solving** : Enhances configuration flexibility for quick switching between local and production setups.

## 🍱 API Usage Examples

* Adding a TikTok task (CURL Format)

```curl
curl -X 'POST' \
  'http://127.0.0.1/api/tiktok/video_task' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'priority=normal&prepend_punctuations=%22'\''%E2%80%9C%C2%BF(%5B%7B-&no_speech_threshold=0.6&clip_timestamps=0&url=https%3A%2F%2Fwww.tiktok.com%2F%40taylorswift%2Fvideo%2F7359655005701311786&word_timestamps=false&platform=tiktok&temperature=0.8%2C1.0&task_type=transcribe&callback_url=&hallucination_silence_threshold=0&language=&condition_on_previous_text=true&compression_ratio_threshold=1.8&append_punctuations=%22'\''.%E3%80%82%2C%EF%BC%8C!%EF%BC%81%3F%EF%BC%9F%3A%EF%BC%9A%E2%80%9D)%5D%7D%E3%80%81&initial_prompt='
```

- Adding a TikTok task (Python Code)

```python
# pip install httpx
import httpx

url = "http://127.0.0.1/api/tiktok/video_task"
tiktok_url = "https://www.tiktok.com/@taylorswift/video/7359655005701311786"

# Define the form data as a dictionary
data = {
    "url": tiktok_url,
    "priority": "normal",
    "prepend_punctuations": '"\'“¿([{-',
    "no_speech_threshold": "0.6",
    "clip_timestamps": "0",
    "word_timestamps": "false",
    "platform": "tiktok",
    "temperature": "0.8,1.0",
    "task_type": "transcribe",
    "callback_url": "",
    "hallucination_silence_threshold": "0",
    "language": "",
    "condition_on_previous_text": "true",
    "compression_ratio_threshold": "1.8",
    "append_punctuations": '"\'.。,!！?？:：”)]}、',
    "initial_prompt": ""
}


async def make_request():
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        print(response.json())


if __name__ == "__main__":
    # To run the async function
    import asyncio
    # Run the async function
    asyncio.run(make_request())
```

- Response

<div><details><summary>🔎Click to expand response</summary>
<pre><code class="json">
{
   "code":200,
   "router":"http://127.0.0.1/api/tiktok/video_task",
   "params":{
      "language":null,
      "temperature":[
         0.8,
         1
      ],
      "compression_ratio_threshold":1.8,
      "no_speech_threshold":0.6,
      "condition_on_previous_text":true,
      "initial_prompt":"",
      "word_timestamps":false,
      "prepend_punctuations":"\"'“¿([{-",
      "append_punctuations":"\"'.。,，!！?？:：”)]}、",
      "clip_timestamps":"0.0",
      "hallucination_silence_threshold":null,
      "task_type":"transcribe",
      "priority":"normal",
      "callback_url":""
   },
   "data":{
      "id":1,
      "status":"queued",
      "callback_url":"",
      "callback_status_code":null,
      "callback_message":null,
      "callback_time":null,
      "priority":"normal",
      "engine_name":"faster_whisper",
      "task_type":"transcribe",
      "created_at":"2024-11-07T16:43:32.768883",
      "updated_at":"2024-11-07T16:43:32.768883",
      "task_processing_time":null,
      "file_path":null,
      "file_url":"https://api.tiktokv.com/aweme/v1/play/?file_id=3146fc434e4d493c93b78566726b9310&is_play_url=1&item_id=7359655005701311786&line=0&signaturev3=dmlkZW9faWQ7ZmlsZV9pZDtpdGVtX2lkLjA3YTkzYjY0ZTliOWUzMzVmN2VhODgxMTMyMDljYTJk&source=FEED&vidc=useast5&video_id=v12044gd0000cohbuanog65ltpj9jdpg",
      "file_name":null,
      "file_size_bytes":null,
      "file_duration":null,
      "language":null,
      "platform":"tiktok",
      "decode_options":{
         "language":null,
         "temperature":[
            0.8,
            1
         ],
         "compression_ratio_threshold":1.8,
         "no_speech_threshold":0.6,
         "condition_on_previous_text":true,
         "initial_prompt":"",
         "word_timestamps":false,
         "prepend_punctuations":"\"'“¿([{-",
         "append_punctuations":"\"'.。,，!！?？:：”)]}、",
         "clip_timestamps":"0.0",
         "hallucination_silence_threshold":null
      },
      "error_message":null,
      "output_url":"http://127.0.0.1/api/whisper/tasks/result?task_id=1",
      "result":null
   }
}
</code></pre>
</details></div>

**When an audio or video file is included in the request body, the API will return the transcribed text result.**

- Get task result (CURL format)

```curl
curl -X 'GET' \
  'http://127.0.0.1/api/whisper/tasks/result?task_id=1' \
  -H 'accept: application/json'
```

- Get task result (Python code)

```python
# pip install httpx
import httpx

url = "http://127.0.0.1/api/whisper/tasks/result"
task_id = 1

params = {
    "task_id": task_id
}


async def make_request():
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        print(response.json())


if __name__ == "__main__":
    # To run the async function
    import asyncio
    # Run the async function
    asyncio.run(make_request())
```

- Response

<div><details><summary>🔎Click to expand response</summary>
<pre><code class="json">
{
  "code": 200,
  "router": "http://127.0.0.1/api/whisper/tasks/result?task_id=1",
  "params": {
    "task_id": "1"
  },
  "data": {
    "id": 1,
    "status": "completed",
    "callback_url": "",
    "callback_status_code": null,
    "callback_message": null,
    "callback_time": null,
    "priority": "normal",
    "engine_name": "faster_whisper",
    "task_type": "transcribe",
    "created_at": "2024-11-07T16:43:33",
    "updated_at": "2024-11-07T16:43:33",
    "task_processing_time": 6.20258,
    "file_path": "C:\\Users\\Evil0ctal\\PycharmProjects\\Fast-Powerful-Whisper-AI-Services-API\\temp_files\\5accc0958ec7476e81d06f8c3897d768.mp4",
    "file_url": "https://api.tiktokv.com/aweme/v1/play/?file_id=3146fc434e4d493c93b78566726b9310&is_play_url=1&item_id=7359655005701311786&line=0&signaturev3=dmlkZW9faWQ7ZmlsZV9pZDtpdGVtX2lkLjA3YTkzYjY0ZTliOWUzMzVmN2VhODgxMTMyMDljYTJk&source=FEED&vidc=useast5&video_id=v12044gd0000cohbuanog65ltpj9jdpg",
    "file_name": null,
    "file_size_bytes": 2401593,
    "file_duration": 30.071,
    "language": "en",
    "platform": "tiktok",
    "decode_options": {
      "language": null,
      "temperature": [
        0.8,
        1
      ],
      "initial_prompt": "",
      "clip_timestamps": "0.0",
      "word_timestamps": false,
      "append_punctuations": "\"'.。,，!！?？:：”)]}、",
      "no_speech_threshold": 0.6,
      "prepend_punctuations": "\"'“¿([{-",
      "condition_on_previous_text": true,
      "compression_ratio_threshold": 1.8,
      "hallucination_silence_threshold": null
    },
    "error_message": null,
    "output_url": "http://127.0.0.1/api/whisper/tasks/result?task_id=1",
    "result": {
      "info": {
        "duration": 30.07125,
        "language": "en",
        "vad_options": null,
        "all_language_probs": [
          [
            "en",
            0.986328125
          ],
          [
            "es",
            0.0013828277587890625
          ],
          [
            "ja",
            0.00125885009765625
          ],
          [
            "fr",
            0.0012197494506835938
          ],
          [
            "de",
            0.0010852813720703125
          ],
          [
            "la",
            0.0010519027709960938
          ],
          [
            "zh",
            0.00089263916015625
          ],
          [
            "pt",
            0.0008320808410644531
          ],
          [
            "ko",
            0.000751495361328125
          ],
          [
            "cy",
            0.000751495361328125
          ],
          [
            "ru",
            0.00074005126953125
          ],
          [
            "nn",
            0.0005245208740234375
          ],
          [
            "sv",
            0.00036072731018066406
          ],
          [
            "it",
            0.0002853870391845703
          ],
          [
            "vi",
            0.00024580955505371094
          ],
          [
            "tr",
            0.0002310276031494141
          ],
          [
            "nl",
            0.00017440319061279297
          ],
          [
            "pl",
            0.00015997886657714844
          ],
          [
            "jw",
            0.0001480579376220703
          ],
          [
            "hi",
            0.00012755393981933594
          ],
          [
            "ar",
            0.00012362003326416016
          ],
          [
            "km",
            0.00012362003326416016
          ],
          [
            "fi",
            0.0001189112663269043
          ],
          [
            "id",
            0.0001170635223388672
          ],
          [
            "haw",
            0.00009781122207641602
          ],
          [
            "th",
            0.00009119510650634766
          ],
          [
            "hu",
            0.00007158517837524414
          ],
          [
            "tl",
            0.000056624412536621094
          ],
          [
            "el",
            0.00005316734313964844
          ],
          [
            "no",
            0.000051975250244140625
          ],
          [
            "ms",
            0.00003892183303833008
          ],
          [
            "cs",
            0.00003802776336669922
          ],
          [
            "ro",
            0.00003129243850708008
          ],
          [
            "ta",
            0.00002312660217285156
          ],
          [
            "mi",
            0.000023066997528076172
          ],
          [
            "da",
            0.000020802021026611328
          ],
          [
            "br",
            0.000020503997802734375
          ],
          [
            "si",
            0.00001800060272216797
          ],
          [
            "sn",
            0.000017702579498291016
          ],
          [
            "fa",
            0.000015079975128173828
          ],
          [
            "ml",
            0.000014007091522216795
          ],
          [
            "uk",
            0.000012218952178955078
          ],
          [
            "he",
            0.000010371208190917969
          ],
          [
            "ca",
            0.000010371208190917969
          ],
          [
            "ur",
            0.000010251998901367188
          ],
          [
            "sl",
            0.000008881092071533203
          ],
          [
            "sa",
            0.000008821487426757812
          ],
          [
            "bn",
            0.000006258487701416016
          ],
          [
            "te",
            0.0000057220458984375
          ],
          [
            "hr",
            0.000005245208740234375
          ],
          [
            "sw",
            0.000004827976226806641
          ],
          [
            "lt",
            0.000003874301910400391
          ],
          [
            "is",
            0.000003874301910400391
          ],
          [
            "sk",
            0.000003039836883544922
          ],
          [
            "lv",
            0.0000025033950805664062
          ],
          [
            "gl",
            0.000002264976501464844
          ],
          [
            "yo",
            0.00000196695327758789
          ],
          [
            "bg",
            0.0000015497207641601562
          ],
          [
            "eu",
            0.0000015497207641601562
          ],
          [
            "et",
            0.0000015497207641601562
          ],
          [
            "hy",
            0.0000013709068298339844
          ],
          [
            "bs",
            0.0000013709068298339844
          ],
          [
            "ne",
            0.000001132488250732422
          ],
          [
            "az",
            0.000001132488250732422
          ],
          [
            "yue",
            9.5367431640625e-7
          ],
          [
            "ht",
            8.940696716308594e-7
          ],
          [
            "my",
            8.344650268554688e-7
          ],
          [
            "mr",
            5.364418029785156e-7
          ],
          [
            "af",
            4.76837158203125e-7
          ],
          [
            "sq",
            4.76837158203125e-7
          ],
          [
            "sr",
            4.172325134277344e-7
          ],
          [
            "oc",
            4.172325134277344e-7
          ],
          [
            "yi",
            4.172325134277344e-7
          ],
          [
            "mn",
            4.172325134277344e-7
          ],
          [
            "be",
            3.576278686523438e-7
          ],
          [
            "lo",
            3.576278686523438e-7
          ],
          [
            "pa",
            3.576278686523438e-7
          ],
          [
            "kk",
            3.576278686523438e-7
          ],
          [
            "fo",
            2.980232238769531e-7
          ],
          [
            "bo",
            2.980232238769531e-7
          ],
          [
            "sd",
            1.788139343261719e-7
          ],
          [
            "ps",
            1.1920928955078125e-7
          ],
          [
            "kn",
            1.1920928955078125e-7
          ],
          [
            "ka",
            5.960464477539064e-8
          ],
          [
            "gu",
            5.960464477539064e-8
          ],
          [
            "mk",
            5.960464477539064e-8
          ],
          [
            "mt",
            5.960464477539064e-8
          ],
          [
            "as",
            5.960464477539064e-8
          ],
          [
            "tg",
            0
          ],
          [
            "uz",
            0
          ],
          [
            "so",
            0
          ],
          [
            "tk",
            0
          ],
          [
            "lb",
            0
          ],
          [
            "mg",
            0
          ],
          [
            "tt",
            0
          ],
          [
            "ln",
            0
          ],
          [
            "ha",
            0
          ],
          [
            "ba",
            0
          ],
          [
            "su",
            0
          ],
          [
            "am",
            0
          ]
        ],
        "duration_after_vad": 30.07125,
        "language_probability": 0.986328125,
        "transcription_options": {
          "prefix": null,
          "best_of": 5,
          "hotwords": null,
          "patience": 1,
          "beam_size": 5,
          "temperatures": [
            0.8,
            1
          ],
          "initial_prompt": "",
          "length_penalty": 1,
          "max_new_tokens": null,
          "suppress_blank": true,
          "clip_timestamps": "0.0",
          "suppress_tokens": [
            -1
          ],
          "word_timestamps": false,
          "log_prob_threshold": -1,
          "repetition_penalty": 1,
          "without_timestamps": false,
          "append_punctuations": "\"'.。,，!！?？:：”)]}、",
          "no_speech_threshold": 0.6,
          "no_repeat_ngram_size": 0,
          "prepend_punctuations": "\"'“¿([{-",
          "max_initial_timestamp": 1,
          "condition_on_previous_text": true,
          "compression_ratio_threshold": 1.8,
          "prompt_reset_on_temperature": 0.5,
          "hallucination_silence_threshold": null
        }
      },
      "text": " And so I enter into evidence, my tarnished coat of arms,  my muses acquired like bruises, my talismans and charms,  the tick, tick, tick of love bombs, my veins of pitch black ink,  all's fair in love and poetry.  Sincerely, the chairman of the Tortured Poets Department.  The Tortured Poets Department, phantom clear vinyl, only at Target.  Subtitles by the Amara.org community",
      "segments": [
        {
          "id": 1,
          "end": 4.3,
          "seek": 3000,
          "text": " And so I enter into evidence, my tarnished coat of arms,",
          "start": 0,
          "words": null,
          "tokens": [
            50365,
            400,
            370,
            286,
            3242,
            666,
            4467,
            11,
            452,
            256,
            1083,
            4729,
            10690,
            295,
            5812,
            11,
            50580
          ],
          "avg_logprob": -0.2094006643752859,
          "temperature": 0.8,
          "no_speech_prob": 0,
          "compression_ratio": 1.6028708133971292
        },
        {
          "id": 2,
          "end": 10.2,
          "seek": 3000,
          "text": " my muses acquired like bruises, my talismans and charms,",
          "start": 5.12,
          "words": null,
          "tokens": [
            50621,
            452,
            1038,
            279,
            17554,
            411,
            25267,
            3598,
            11,
            452,
            4023,
            1434,
            599,
            293,
            41383,
            11,
            50875
          ],
          "avg_logprob": -0.2094006643752859,
          "temperature": 0.8,
          "no_speech_prob": 0,
          "compression_ratio": 1.6028708133971292
        },
        {
          "id": 3,
          "end": 15.88,
          "seek": 3000,
          "text": " the tick, tick, tick of love bombs, my veins of pitch black ink,",
          "start": 10.54,
          "words": null,
          "tokens": [
            50892,
            264,
            5204,
            11,
            5204,
            11,
            5204,
            295,
            959,
            19043,
            11,
            452,
            29390,
            295,
            7293,
            2211,
            11276,
            11,
            51159
          ],
          "avg_logprob": -0.2094006643752859,
          "temperature": 0.8,
          "no_speech_prob": 0,
          "compression_ratio": 1.6028708133971292
        },
        {
          "id": 4,
          "end": 18.22,
          "seek": 3000,
          "text": " all's fair in love and poetry.",
          "start": 16.76,
          "words": null,
          "tokens": [
            51203,
            439,
            311,
            3143,
            294,
            959,
            293,
            15155,
            13,
            51276
          ],
          "avg_logprob": -0.2094006643752859,
          "temperature": 0.8,
          "no_speech_prob": 0,
          "compression_ratio": 1.6028708133971292
        },
        {
          "id": 5,
          "end": 22.82,
          "seek": 3000,
          "text": " Sincerely, the chairman of the Tortured Poets Department.",
          "start": 19.28,
          "words": null,
          "tokens": [
            51329,
            318,
            4647,
            323,
            356,
            11,
            264,
            22770,
            295,
            264,
            48415,
            3831,
            6165,
            1385,
            5982,
            13,
            51506
          ],
          "avg_logprob": -0.2094006643752859,
          "temperature": 0.8,
          "no_speech_prob": 0,
          "compression_ratio": 1.6028708133971292
        },
        {
          "id": 6,
          "end": 27.04,
          "seek": 3000,
          "text": " The Tortured Poets Department, phantom clear vinyl, only at Target.",
          "start": 23.44,
          "words": null,
          "tokens": [
            51537,
            440,
            48415,
            3831,
            6165,
            1385,
            5982,
            11,
            903,
            25796,
            1850,
            25226,
            11,
            787,
            412,
            24586,
            13,
            51717
          ],
          "avg_logprob": -0.2094006643752859,
          "temperature": 0.8,
          "no_speech_prob": 0,
          "compression_ratio": 1.6028708133971292
        },
        {
          "id": 7,
          "end": 33,
          "seek": 3007,
          "text": " Subtitles by the Amara.org community",
          "start": 30,
          "words": null,
          "tokens": [
            50365,
            8511,
            27689,
            904,
            538,
            264,
            2012,
            2419,
            13,
            4646,
            1768,
            50515
          ],
          "avg_logprob": -0.4202356613599338,
          "temperature": 0.8,
          "no_speech_prob": 0.8740234375,
          "compression_ratio": 0.8181818181818182
        }
      ]
    }
  }
}
</code></pre>
</details></div>

## 🦺 Performance Testing

* Testing Environment and Hardware Configuration
  * CPU: 13th Gen Intel(R) Core(TM) i9-13950HX 24-core 32-thread @ 2.20 GHz
  * GPU: NVIDIA GeForce RTX 4060 Laptop GPU
  * Memory: 64GB
  * System: Windows 11

> Single Queue Test

* We use the `faster whisper` model as the engine with `CUDA` acceleration.
* The inference model used is `large-v3`.
* The asynchronous model pool’s maximum concurrency `MAX_CONCURRENT_TASKS` is set to 1.
* Using a 39-second video for testing, five requests were sent consecutively, and the total processing time for all tasks was 32 seconds.

> Concurrent Mode Testing

* To be added.

## 📝 To-Do List

* Enhance the crawler module with additional platform support.
* Improve task flow system, implementing an automated event- or time-driven workflow system.
* Add LLM support to enable further processing, such as content summarization and semantic analysis, suitable for secondary analysis or text mining.
* Optimize database structure and design, with plans to support Redis and add more fields to store more data.
* Add deployment scripts for a one-click deployment bash script to facilitate easy project setup.
* Containerize the project with Docker and add automated container build scripts.

## 🔧 Default Configuration File

```python
import os
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件 | Load .env file
load_dotenv()


class Settings:

    # FastAPI 设置 | FastAPI settings
    class FastAPISettings:
        # 项目名称 | Project name
        title: str = "Fast-Powerful-Whisper-AI-Services-API"
        # 项目描述 | Project description
        description: str = "⚡ A high-performance asynchronous API for Automatic Speech Recognition (ASR) and translation. No need to purchase the Whisper API—perform inference using a locally running Whisper model with support for multi-GPU concurrency and designed for distributed deployment. It also includes built-in crawlers for social media platforms like TikTok and Douyin, enabling seamless media processing from multiple social platforms. This provides a powerful and scalable solution for automated media content data processing."
        # 项目版本 | Project version
        version: str = "1.0.5"
        # Swagger 文档 URL | Swagger docs URL
        docs_url: str = "/"
        # 是否开启 debug 模式 | Whether to enable debug mode
        debug: bool = False
        # 当检测到项目代码变动时是否自动重载项目 | Whether to automatically reload the project when changes to the project code are detected
        reload_on_file_change: bool = os.getenv("RELOAD_ON_FILE_CHANGE", False)
        # FastAPI 服务 IP | FastAPI service IP
        ip: str = "0.0.0.0"
        # FastAPI 服务端口 | FastAPI service port
        port: int = 80

    # 数据库设置 | Database settings
    class DatabaseSettings:
        # 选择数据库类型，支持 "sqlite" 和 "mysql" | Select the database type, support "sqlite" and "mysql"
        # "sqlite"：适合小规模项目单机运行，无需安装数据库，直接使用文件存储数据 | "sqlite": Suitable for small-scale projects running on a single machine, no need to install a database, directly use file storage data
        # "mysql"：适合大规模项目分布式部署，需要安装 MySQL 数据库 | "mysql": Suitable for large-scale projects distributed deployment, need to install MySQL database
        # 如果你选择 "mysql"，请确保安装了 aiomysql | If you choose "mysql", please make sure aiomysql is installed
        # 如果你选择 "sqlite"，请确保安装了 aiosqlite | If you choose "sqlite", please make sure aiosqlite is installed
        db_type: str = os.getenv("DB_TYPE", "sqlite")

        # SQLite 数据库设置 | SQLite database settings
        # 数据库名字 | Database name
        sqlite_db_name: str = os.getenv("sqlite_db_name", "WhisperServiceAPI.db")
        # 数据库 URL | Database URL
        sqlite_url: str = f"sqlite+aiosqlite:///{sqlite_db_name}"

        # MySQL 数据库设置 | MySQL database settings
        # 数据库名字 | Database name
        mysql_db_name: str = os.getenv("MYSQL_DB_NAME", "")
        # 数据库用户名 | Database username
        mysql_username: str = os.getenv("MYSQL_USERNAME", "")
        # 数据库密码 | Database password
        mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
        # 数据库地址 | Database host
        mysql_host: str = os.getenv("MYSQL_HOST", "")
        # 数据库端口 | Database port
        mysql_port: int = 3306
        # 数据库 URL | Database URL
        mysql_url: str = f"mysql+aiomysql://{mysql_username}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db_name}"

    # Whisper 服务类设置 | Whisper service class settings
    class WhisperServiceSettings:
        # Whisper 服务的最大并发任务数，设置为 1 时为单任务模式 | The maximum number of concurrent tasks for the Whisper service, set to 1 for single task mode
        # 如果你有多个 GPU，可以设置大于 1，在单一 GPU 上运行多个任务无法缩短任务时间，但可以提高任务并发度 | If you have multiple GPUs, you can set it to more than 1. Running multiple tasks on a single GPU cannot shorten the task time, but can increase the task concurrency
        MAX_CONCURRENT_TASKS: int = 1
        # 检查任务状态的时间间隔（秒），如果设置过小可能会导致数据库查询频繁，设置过大可能会导致任务状态更新不及时。
        # Time interval for checking task status (seconds). If set too small, it may cause frequent database queries.
        TASK_STATUS_CHECK_INTERVAL: int = 3

    # OpenAI Whisper 设置 | OpenAI Whisper settings
    class OpenAIWhisperSettings:
        # 模型名称 | Model name
        openai_whisper_model_name: str = "large-v3"
        # 设备名称，如 "cpu" 或 "cuda", 为 None 时自动选择 | Device name, such as "cpu" or "cuda", automatically selected when None
        openai_whisper_device: Optional[str] = None
        # 模型下载根目录 | Model download root directory
        openai_whisper_download_root: Optional[str] = None
        # 是否在内存中加载模型 | Whether to load the model in memory
        openai_whisper_in_memory: bool = False

    # Faster Whisper 设置 | Faster Whisper settings
    class FasterWhisperSettings:
        # 模型名称 | Model name
        faster_whisper_model_size_or_path: str = "large-v3"
        # 设备名称，如 "cpu" 或 "cuda", 为 'auto' 时自动选择 | Device name, such as "cpu" or "cuda", automatically selected when 'auto'
        faster_whisper_device: str = "auto"
        # 设备ID，当 faster_whisper_device 为 "cuda" 时有效 | Device ID, valid when faster_whisper_device is "cuda"
        faster_whisper_device_index: int = 0
        # 模型推理计算类型 | Model inference calculation type
        faster_whisper_compute_type: str = "float16"
        # 模型使用的CPU线程数，设置为 0 时使用所有可用的CPU线程 | The number of CPU threads used by the model, set to 0 to use all available CPU threads
        faster_whisper_cpu_threads: int = 0
        # 模型worker数 | Model worker count
        faster_whisper_num_workers: int = 1
        # 模型下载根目录 | Model download root directory
        faster_whisper_download_root: Optional[str] = None

    # 异步模型池设置 | Asynchronous model pool settings
    class AsyncModelPoolSettings:
        # 引擎名称 | Engine name
        # 目前只支持 "openai_whisper" 和 "faster_whisper" | Currently only supports "openai_whisper" and "faster_whisper"
        engine: str = "faster_whisper"

        # 最小的模型池大小 | Minimum model pool size
        min_size: int = 1

        # 最大的模型池大小，如果你没有多个 GPU，建议设置为 1 | Maximum model pool size, if you don't have multiple GPUs, it is recommended to set it to 1
        # 如果你有多个 GPU，可以设置大于 1，程序会自动为每个 GPU 创建一个模型实例 | If you have multiple GPUs, you can set it to more than 1, and the program will automatically create a model instance for each GPU
        max_size: int = 1

        # 每个 GPU 最多支持的实例数量，如果你的 GPU 内存足够大，可以设置大于 1 | The maximum number of instances supported by each GPU, if your GPU memory is large enough, you can set it to more than 1
        max_instances_per_gpu: int = 1

        # 是否在模型池初始化时以最大的模型池大小创建模型实例 | Whether to create model instances with the maximum model pool size when the model pool is initialized
        init_with_max_pool_size: bool = True

    # 文件设置 | File settings
    class FileSettings:
        # 是否自动删除临时文件 | Whether to automatically delete temporary files
        auto_delete: bool = True
        # 是否限制上传文件大小 | Whether to limit the size of uploaded files
        limit_file_size: bool = True
        # 最大上传文件大小（字节）| Maximum upload file size (bytes)
        max_file_size: int = 2 * 1024 * 1024 * 1024
        # 临时文件目录 | Temporary file directory
        temp_files_dir: str = "./temp_files"
        # 是否在处理后删除临时文件 | Whether to delete temporary files after processing
        delete_temp_files_after_processing: bool = True
        # 允许保存的文件类型，加强服务器安全性，为空列表时不限制 | Allowed file types, enhance server security, no restrictions when the list is empty
        allowed_file_types: list = [
            # （FFmpeg 支持的媒体文件）| (FFmpeg supported media files)
            '.3g2', '.3gp', '.aac', '.ac3', '.aiff', '.alac', '.amr', '.ape', '.asf', '.avi', '.avs', '.cavs', '.dirac',
            '.dts', '.dv', '.eac3', '.f4v', '.flac', '.flv', '.g722', '.g723_1', '.g726', '.g729', '.gif', '.gsm',
            '.h261', '.h263', '.h264', '.hevc', '.jpeg', '.jpg', '.lpcm', '.m4a', '.m4v', '.mkv', '.mlp', '.mmf',
            '.mov', '.mp2', '.mp3', '.mp4', '.mpc', '.mpeg', '.mpg', '.oga', '.ogg', '.ogv', '.opus', '.png', '.rm',
            '.rmvb', '.rtsp', '.sbc', '.spx', '.svcd', '.swf', '.tak', '.thd', '.tta', '.vc1', '.vcd', '.vid', '.vob',
            '.wav', '.wma', '.wmv', '.wv', '.webm', '.yuv',
            # （字幕文件）| (Subtitle files)
            '.srt', '.vtt',
        ]

    # 日志设置 | Log settings
    class LogSettings:
        # 日志级别 | Log level
        """
        CRITICAL = 50
        FATAL = CRITICAL
        ERROR = 40
        WARNING = 30
        WARN = WARNING
        INFO = 20
        DEBUG = 10
        NOTSET = 0
        """
        level: int = 10
        # 日志文件目录 | Log file directory
        log_dir: str = "./log_files"
        # 日志文件前缀 | Log file prefix
        log_file_prefix: str = "app"
        # 日志文件编码 | Log file encoding
        encoding: str = "utf-8"
        # 日志文件备份数 | Log file backup count
        backup_count: int = 7

    # 抖音 API 设置 | Douyin API settings
    class DouyinAPISettings:
        # Douyin Web Cookie
        web_cookie: str = os.getenv("DOUYIN_WEB_COOKIE", "")
        # Proxy
        proxy: str = os.getenv("DOUYIN_PROXY", None)

    # ChatGPT API 设置 | ChatGPT API settings
    class ChatGPTSettings:
        # OpenAI API Key
        API_Key: str = os.getenv("OPENAI_API_KEY", "")
        # OpenAI ChatGPT Model
        GPT_Model: str = "gpt-3.5-turbo"

    # TikHub.io API 设置 | TikHub.io API settings
    class TikHubAPISettings:
        # TikHub.io API URL
        api_domain: str = "https://api.tikhub.io"
        # TikHub.io API Token
        api_key: str = os.getenv("TIKHUB_API_KEY", "")
```

## 🛡️ License

This project is open-sourced under the [Apache2.0](LICENSE) license.

For commercial use and custom cooperation, please contact **Email：[evil0ctal1985@gmail.com](evil0ctal1985@gmail.com)**

## 📬 Contact

For any questions or suggestions, feel free to reach out via [issue](https://github.com/Evil0ctal/Fast-Powerful-Whisper-AI-Services-API/issues).

## 🧑‍💻 Contribution Guide

We highly welcome your feedback and suggestions! Reach out through GitHub issues, or if you wish to contribute code, please fork the project and submit a pull request. We look forward to your participation! 💪

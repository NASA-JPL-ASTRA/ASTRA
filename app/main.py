# ==============================================================================
# Copyright (C) 2024 Evil0ctal
#
# This file is part of the Whisper-Speech-to-Text-API project.
# Github: https://github.com/Evil0ctal/Whisper-Speech-to-Text-API
#
# This project is licensed under the Apache License 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
#                                     ,
#              ,-.       _,---._ __  / \
#             /  )    .-'       `./ /   \
#            (  (   ,'            `/    /|
#             \  `-"             \'\   / |
#              `.              ,  \ \ /  |
#               /`.          ,'-`----Y   |
#              (            ;        |   '
#              |  ,-.    ,-'         |  /
#              |  | (   |  Evil0ctal | /
#              )  |  \  `.___________|/    Whisper API Out of the Box (Where is my ⭐?)
#              `--'   `--'
# ==============================================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.router import router as api_router
from app.database.DatabaseManager import DatabaseManager
from app.model_pool.AsyncModelPool import AsyncModelPool
from app.services.whisper_service import WhisperService
from app.utils.logging_utils import configure_logging
from config.settings import Settings

# 配置日志记录器 | Configure the logger
logger = configure_logging(name=__name__)

# API Tags
tags_metadata = [
    {
        "name": "Health-Check",
        "description": "**(服务器健康检查 / Server Health Check)**",
    },
    {
        "name": "Whisper-Tasks",
        "description": "**(Whisper 任务 / Whisper Tasks)**",
    },
    {
        "name": "Work-Flows",
        "description": "**(工作流 / Work Flows)**",
    },
    {
        "name": "TikTok-Tasks",
        "description": "**(TikTok 任务 / TikTok Tasks)**",
    },
    {
        "name": "Douyin-Tasks",
        "description": "**(抖音 任务 / Douyin Tasks)**",
    },
    {
        "name": "ChatGPT-Tasks",
        "description": "**(ChatGPT 任务 / ChatGPT Tasks)**",
    }
]


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    FastAPI 生命周期上下文管理器 | FastAPI Lifecycle context manager
    :param application: FastAPI 应用实例 | FastAPI application instance
    :return: None
    """
    # 选择数据库管理器并初始化数据库 | Choose the database manager and initialize the database
    if Settings.DatabaseSettings.db_type == "sqlite":
        database_url = Settings.DatabaseSettings.sqlite_url
    elif Settings.DatabaseSettings.db_type == "mysql":
        database_url = Settings.DatabaseSettings.mysql_url
    else:
        raise RuntimeError("Can not recognize the database type, please check the database type in the settings.")

    db_manager = DatabaseManager(
        database_type=Settings.DatabaseSettings.db_type,
        database_url=database_url
    )
    await db_manager.initialize()

    # 实例化异步模型池 | Instantiate the asynchronous model pool
    model_pool = AsyncModelPool(
        # 模型池设置 | Model Pool Settings
        engine=Settings.AsyncModelPoolSettings.engine,
        min_size=Settings.AsyncModelPoolSettings.min_size,
        max_size=Settings.AsyncModelPoolSettings.max_size,
        max_instances_per_gpu=Settings.AsyncModelPoolSettings.max_instances_per_gpu,
        init_with_max_pool_size=Settings.AsyncModelPoolSettings.init_with_max_pool_size,

        # openai_whisper 引擎设置 | openai_whisper Engine Settings
        openai_whisper_model_name=Settings.OpenAIWhisperSettings.openai_whisper_model_name,
        openai_whisper_device=Settings.OpenAIWhisperSettings.openai_whisper_device,
        openai_whisper_download_root=Settings.OpenAIWhisperSettings.openai_whisper_download_root,
        openai_whisper_in_memory=Settings.OpenAIWhisperSettings.openai_whisper_in_memory,

        # faster_whisper 引擎设置 | faster_whisper Engine Settings
        faster_whisper_model_size_or_path=Settings.FasterWhisperSettings.faster_whisper_model_size_or_path,
        faster_whisper_device=Settings.FasterWhisperSettings.faster_whisper_device,
        faster_whisper_device_index=Settings.FasterWhisperSettings.faster_whisper_device_index,
        faster_whisper_compute_type=Settings.FasterWhisperSettings.faster_whisper_compute_type,
        faster_whisper_cpu_threads=Settings.FasterWhisperSettings.faster_whisper_cpu_threads,
        faster_whisper_num_workers=Settings.FasterWhisperSettings.faster_whisper_num_workers,
        faster_whisper_download_root=Settings.FasterWhisperSettings.faster_whisper_download_root
    )
    # 初始化模型池，加载模型，这可能需要一些时间 | Initialize the model pool, load the model, this may take some time
    await model_pool.initialize_pool()

    # 实例化 WhisperService | Instantiate WhisperService
    whisper_service = WhisperService(
        model_pool=model_pool,
        db_manager=db_manager,
        max_concurrent_tasks=Settings.WhisperServiceSettings.MAX_CONCURRENT_TASKS,
        task_status_check_interval=Settings.WhisperServiceSettings.TASK_STATUS_CHECK_INTERVAL,
    )

    # 启动任务处理器 | Start the task processor
    whisper_service.start_task_processor()

    # 将数据库管理器存储在应用的 state 中 | Store db_manager in the app state
    application.state.db_manager = db_manager

    # 将 whisper_service 存储在应用的 state 中 | Store whisper_service in the app state
    application.state.whisper_service = whisper_service

    # 等待生命周期完成 | Wait for the lifecycle to complete
    yield

    # 停止任务处理器 | Stop the task processor
    whisper_service.stop_task_processor()


# 创建 FastAPI 应用实例
app = FastAPI(
    title=Settings.FastAPISettings.title,
    description=Settings.FastAPISettings.description,
    version=Settings.FastAPISettings.version,
    openapi_tags=tags_metadata,
    docs_url=Settings.FastAPISettings.docs_url,
    debug=Settings.FastAPISettings.debug,
    lifespan=lifespan
)

# API 路由 | API Router
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=Settings.FastAPISettings.ip, port=Settings.FastAPISettings.port)

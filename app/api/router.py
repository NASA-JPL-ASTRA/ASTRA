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

from fastapi import APIRouter
from app.api.routers import (
    health_check, whisper_tasks,
    work_flows, tiktok_tasks,
    douyin_tasks, chatgpt_tasks
)

router = APIRouter()

# Health Check routers
router.include_router(health_check.router, prefix="/health", tags=["Health-Check"])

# Whisper Tasks routers
router.include_router(whisper_tasks.router, prefix="/whisper", tags=["Whisper-Tasks"])

# Work Flow routers
router.include_router(work_flows.router, prefix="/workflow", tags=["Work-Flows"])

# TikTok Task API routers
router.include_router(tiktok_tasks.router, prefix="/tiktok", tags=["TikTok-Tasks"])

# Douyin Task API routers
router.include_router(douyin_tasks.router, prefix="/douyin", tags=["Douyin-Tasks"])

# ChatGPT Task API routers
router.include_router(chatgpt_tasks.router, prefix="/chatgpt", tags=["ChatGPT-Tasks"])

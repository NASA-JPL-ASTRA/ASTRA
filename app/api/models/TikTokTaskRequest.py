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

from fastapi import Form
from pydantic import HttpUrl

from app.api.models.WhisperTaskRequest import WhisperTaskRequest


class TikTokVideoTask(WhisperTaskRequest):
    url: HttpUrl = Form(
        description="TikTok 视频的 URL 地址 / URL address of the TikTok video",
        example="https://www.tiktok.com/@example/video/1234567890"
    )
    platform: str = Form(
        default="tiktok",
        description="指定平台为 TikTok / Specify the platform as TikTok"
    )
    save_data_in_db: bool = Form(
        default=True,
        description="是否将视频数据保存到数据库 / Whether to save video data to the database"
    )


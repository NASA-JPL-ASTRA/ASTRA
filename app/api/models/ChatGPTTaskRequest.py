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

from enum import Enum

from fastapi import Form
from pydantic import BaseModel


class SaveToDatabaseEnum(str, Enum):
    true = True
    false = False


class ChatGPTTaskRequest(BaseModel):
    task_id: int = Form(description="任务ID / Task ID")
    chatgpt_api_key: str = Form('', description="ChatGPT API秘钥 / ChatGPT API Key")
    chatgpt_prompt: str = Form('', description="ChatGPT 提示词 / ChatGPT Prompt")
    chatgpt_model: str = Form('', description="ChatGPT 模型 / ChatGPT Model")
    output_language: str = Form("en", description="输出语言 / Output Language")
    save_to_database: bool = Form(True, description="是否保存到数据库 / Whether to save to database")

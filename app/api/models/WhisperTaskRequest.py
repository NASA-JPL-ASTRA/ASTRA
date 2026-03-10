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
from typing import Annotated, Optional

from fastapi import Form, Query
from pydantic import BaseModel


class TaskPriority(str, Enum):
    high = "high"
    normal = "normal"
    low = "low"


class TaskType(str, Enum):
    transcribe: str = "transcribe"
    translate: str = "translate"


class WhisperTaskRequest(BaseModel):
    task_type: TaskType = Form(
        TaskType.transcribe,
        description="任务类型，默认为 'transcribe'，具体取值请参考文档 / Task type, default is 'transcribe', refer to the documentation for specific values"
    )
    callback_url: Optional[str] = Form(
        '',
        description="回调URL，任务完成时通知客户端 / Callback URL to notify the client when the task is completed"
    )
    priority: TaskPriority = Form(
        TaskPriority.normal,
        description="任务优先级 / Task priority"
    )
    platform: Optional[str] = Form(
        '',
        description="指定平台，例如 'tiktok' 或 'douyin'，仅用于区分不同平台的任务方便在数据库中存储 / Specify the platform, e.g., 'tiktok' or 'douyin', only used to distinguish tasks from different platforms for storage in the database"
    )
    language: str = Form(
        "",
        description="指定输出语言，例如 'en' 或 'zh'，留空则自动检测 / Specify the output language, e.g., 'en' or 'zh', leave empty for auto-detection"
    )
    temperature: str = Form(
        "0.8,1.0",
        description="采样温度，控制输出文本的多样性，可以是单个值或使用逗号分隔的多个值 / Sampling temperature, control the diversity of the output text, can be a single value or multiple values separated by commas"
    )
    compression_ratio_threshold: float = Form(
        1.8,
        description="压缩比阈值 / Compression ratio threshold"
    )
    no_speech_threshold: float = Form(
        0.6,
        description="无声部分的概率阈值 / No-speech probability threshold"
    )
    condition_on_previous_text: bool = Form(
        True,
        description="在连续语音中更准确地理解上下文 / Condition on previous text"
    )
    initial_prompt: str = Form(
        "",
        description="初始提示文本 / Initial prompt text"
    )
    word_timestamps: bool = Form(
        False,
        description="是否提取每个词的时间戳信息 / Whether to extract word-level timestamp information"
    )
    prepend_punctuations: str = Form(
        "\"'“¿([{-",
        description="前置标点符号集合 / Prepend punctuation characters"
    )
    append_punctuations: str = Form(
        "\"'.。,，!！?？:：”)]}、",
        description="后置标点符号集合 / Append punctuation characters"
    )
    clip_timestamps: str = Form(
        "0.0",
        description="裁剪时间戳，避免超出范围问题，默认为 '0'，可以是单个值或使用逗号分隔的多个值。 / Clip timestamps to avoid out-of-range issues, default is '0', can be a single value or multiple values separated by commas"
    )
    vad_filter: bool = Form(
        True,
        description="是否使用 VAD 过滤静音，设为 False 可处理安静/低音量音频 / Whether to use VAD to filter silence, set False for quiet audio"
    )
    hallucination_silence_threshold: Optional[float] = Form(
        None,
        description="幻听静音阈值 / Hallucination silence threshold"
    )

    class Config:
        schema_extra = {
            "description": """
            Request model for creating a Whisper transcription task.

            **Usage Notes:**
            - Upload media file or specify URL, and set task type, priority, and callback options as needed.
            - Task processing is asynchronous, with results accessible through `/api/whisper/tasks/result`.
            - See API documentation for callback examples and task type details.

            **Common Parameters:**
            - `file` or `file_url`: Specify a media file directly or provide its URL.
            - `task_type`: Choose transcription or translation as supported by the engine.
            - `priority`, `language`, and other parameters control task behavior and output formatting.
            """
        }


class WhisperTaskFileOption(WhisperTaskRequest):
    file_url: Optional[str] = Form(
        '',
        description="媒体文件的 URL 地址 / URL address of the media file"
    )


class WhisperTaskQueryOption(BaseModel):
    """Query params for task create (used when params sent as URL query string)."""
    task_type: str = "transcribe"
    callback_url: Optional[str] = ""
    priority: str = "normal"
    platform: Optional[str] = ""
    language: str = ""
    temperature: str = "0.8,1.0"
    compression_ratio_threshold: float = 1.8
    no_speech_threshold: float = 0.6
    condition_on_previous_text: bool = True
    initial_prompt: str = ""
    word_timestamps: bool = False
    prepend_punctuations: str = "\"'\"¿([{-"
    append_punctuations: str = "\"'.。,，!！?？:：\")]}、"
    clip_timestamps: str = "0.0"
    vad_filter: bool = True
    hallucination_silence_threshold: Optional[float] = None
    file_url: Optional[str] = ""
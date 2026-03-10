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

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum


# 定义触发类型的枚举 | Define an enum for trigger type
class TriggerType(str, Enum):
    MANUAL = 'MANUAL'
    SCHEDULED = 'SCHEDULED'
    EVENT = 'EVENT'


class WorkflowTaskSchema(BaseModel):
    TASK_ID: str
    COMPONENT: str
    PARAMETERS: Optional[Dict[str, Any]] = None
    RETRY_POLICY: Optional[Dict[str, int]] = None
    TIMEOUT: Optional[int] = 60
    DELAY: Optional[int] = 10
    CONDITION: Optional[Dict[str, Any]] = None
    DEPENDENCIES: Optional[List[str]] = None
    PRIORITY: str = "NORMAL"  # 使用字符串


class NotifyOnCompletionSchema(BaseModel):
    channel: str
    recipient: str
    message: str


class WorkflowSchema(BaseModel):
    WORKFLOW_NAME: str
    DESCRIPTION: Optional[str] = None
    TRIGGER_TYPE: TriggerType  # 使用触发类型枚举
    CALLBACK_URL: Optional[str] = None
    NOTIFY_ON_COMPLETION: Optional[NotifyOnCompletionSchema] = None
    tasks: List[WorkflowTaskSchema]

    def to_dict(self):
        # 将模型转换为字典，并手动转换枚举值为字符串
        data = self.dict()
        data['TRIGGER_TYPE'] = self.TRIGGER_TYPE.value  # 转换为字符串
        return data

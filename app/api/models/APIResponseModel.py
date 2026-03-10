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

from datetime import datetime
from typing import Any, Optional, Dict
from pydantic import BaseModel, Field


# 创建一个通用的响应模型 | Create a common response model
class ResponseModel(BaseModel):
    code: int = Field(default=200, description="HTTP status code | HTTP状态码")
    router: str = Field(default="", description="The endpoint that generated this response | 生成此响应的端点")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict,
                                             description="The parameters used in the request | 请求中使用的参数")
    data: Optional[Any] = Field(default=None, description="The response data | 响应数据")

    class Config:
        schema_extra = {
            "example": {
                "code": 200,
                "router": "/example/endpoint",
                "params": {"query": "example"},
                "data": {"key": "value"}
            }
        }


# 定义错误响应模型 | Define an error response model
class ErrorResponseModel(BaseModel):
    code: int = Field(default=400, description="HTTP status code | HTTP状态码")
    message: str = Field(
        default="An error occurred. | 服务器发生错误。",
        description="Error message | 错误消息")
    time: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      description="The time the error occurred | 发生错误的时间")
    router: str = Field(default="", description="The endpoint that generated this response | 生成此响应的端点")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict,
                                             description="The parameters used in the request | 请求中使用的参数")

    class Config:
        schema_extra = {
            "example": {
                "code": 400,
                "message": "Invalid request parameters. | 请求参数无效。",
                "time": "2024-10-27 14:30:00",
                "router": "/example/endpoint",
                "params": {"param1": "invalid"}
            }
        }

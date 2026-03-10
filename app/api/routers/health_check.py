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

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()


class HealthCheckResponse(BaseModel):
    status: str = "ok"


@router.get(
    "/check",
    summary="检查服务器是否正确响应请求 / Check if the server responds to requests correctly",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "服务器响应成功 / Server responds successfully",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            }
        }
    }
)
async def health_check():
    """
    # [中文]

    ### 用途说明:

    - 检查服务器是否正确响应请求。

    ### 参数说明:

    - 无参数。

    ### 返回结果:

    - `status`: 服务器状态，正常为 `ok`。

    # [English]

    ### Purpose:

    - Check if the server responds to requests correctly.

    ### Parameter Description:

    - No parameters.

    ### Return Result:

    - `status`: Server status, normal is `ok`.
    """
    return HealthCheckResponse()

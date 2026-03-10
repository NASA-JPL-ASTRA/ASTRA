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

import traceback
from typing import Optional, Union, List

from fastapi import APIRouter, Request, HTTPException, Form, BackgroundTasks
from starlette import status

from app.api.models.WorkFlowModels import WorkflowSchema
from app.utils.logging_utils import configure_logging

from app.api.models.APIResponseModel import ResponseModel, ErrorResponseModel

router = APIRouter()

# 配置日志记录器 | Configure the logger
logger = configure_logging(name=__name__)


# 输入一个视频链接，然后创建一个 Whisper 任务 | Input a video link, then create a Whisper task
@router.post("/create_work_flow",
             response_model=ResponseModel,
             summary="创建一个工作流 / Create a work flow",
             response_description="创建工作流的结果信息 / The result information of creating a work flow"
             )
async def create_workflow(request: Request, workflow_data: WorkflowSchema):

    # 2024年11月5日21:18:33 需要重新思考实现方式
    # 2024年11月5日21:18:33 Need to rethink the implementation method
    return ResponseModel(
        data={"message": "This API is not implemented yet."}
    )
    try:
        # 将 Pydantic 模型转换为字典，以便插入数据库
        workflow_dict = workflow_data.dict()

        print(f"workflow_dict: {workflow_dict}")

        # 调用数据库管理器的 create_workflow 方法并插入数据
        workflow_id = await request.app.state.db_manager.create_workflow(workflow_dict)

        return ResponseModel(
            data={"workflow_id": workflow_id}
        )
    except Exception as e:
        # 捕获并处理任何异常
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workflow: {str(e)}"
        )

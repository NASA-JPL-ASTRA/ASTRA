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
from openai import AsyncOpenAI

from fastapi import Request, APIRouter, HTTPException, status, Query
from sqlalchemy.exc import SQLAlchemyError

from app.api.models.APIResponseModel import ResponseModel, ErrorResponseModel
from app.api.models.ChatGPTTaskRequest import ChatGPTTaskRequest
from app.database.models.TaskModels import TaskStatusHttpMessage, TaskStatusHttpCode, TaskStatus
from app.utils.logging_utils import configure_logging
from config.settings import Settings

router = APIRouter()

# 配置日志记录器 | Configure logging
logger = configure_logging(name=__name__)


# 根据任务ID使用ChatGPT进行内容总结 | Summarize content using ChatGPT based on task ID
@router.post("/summary",
             response_model=ResponseModel,
             summary="根据任务ID使用ChatGPT进行内容总结 / Summarize content using ChatGPT based on task ID",
             response_description="根据任务ID使用ChatGPT进行内容总结的结果信息 / Result information of summarizing content using ChatGPT based on task ID"
             )
async def chatgpt_summary(
        request: Request,
        _ChatGPTTaskRequest: ChatGPTTaskRequest = ChatGPTTaskRequest,
):
    """
    # [中文]

    ### 用途说明:
    - 根据任务ID使用ChatGPT进行内容总结。

    ### 请求参数:
    - `task_id`: 任务ID。
    - `chatgpt_api_key`: ChatGPT API秘钥，为空则使用配置文件中的API秘钥。
    - `chatgpt_prompt`: ChatGPT 提示词，为空则使用默认提示词。
    - `chatgpt_model`: ChatGPT 模型，为空则使用配置文件中的模型。
    - `output_language`: 输出语言，默认为英文，你可以自定义输出语言。
    - `save_to_database`: 是否保存到数据库，默认为True，将结果根据任务ID保存到数据库。

    ### 返回结果:
    - 返回根据任务ID使用ChatGPT进行内容总结的结果信息。

    ### 错误代码说明:
    - `202`: 任务处于排队中。
    - `404`: 任务ID不存在。
    - `500`: 任务失败或其他未知错误。
    - `503`: 数据库错误。

    # [English]

    ### Description:
    - Summarize content using ChatGPT based on task ID.

    ### Request parameters:
    - `task_id`: Task ID.
    - `chatgpt_api_key`: ChatGPT API key, empty to use the API key in the configuration file.
    - `chatgpt_prompt`: ChatGPT prompt, empty to use the default prompt.
    - `chatgpt_model`: ChatGPT model, empty to use the model in the configuration file.
    - `output_language`: Output language, default is English, you can customize the output language.
    - `save_to_database`: Whether to save to the database, default is True, save the result to the database according to the task ID.

    ### Return result:
    - Return the result information of summarizing content using ChatGPT based on task ID.

    ### Error code description:
    - `202`: The task is queued.
    - `404`: Task ID does not exist.
    - `500`: Task failed or other unknown errors.
    - `503`: Database error.
    """
    try:
        # 通过任务ID查询任务 | Query task by task ID
        task = await request.app.state.db_manager.get_task(_ChatGPTTaskRequest.task_id)
        if not task:
            # 任务未找到 - 返回404 | Task not found - return 404
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message=TaskStatusHttpMessage.not_found.value,
                    router=str(request.url),
                    params=dict(request.query_params),
                ).model_dump()
            )

        # 任务处于排队中 - 返回202 | Task is queued - return 202
        if task.status == TaskStatus.queued:
            raise HTTPException(
                status_code=TaskStatusHttpCode.queued.value,
                detail=ErrorResponseModel(
                    code=TaskStatusHttpCode.queued.value,
                    message=TaskStatusHttpMessage.queued.value,
                    router=str(request.url),
                    params=dict(request.query_params),
                ).model_dump()
            )
        # 任务正在处理中 - 返回202 | Task is processing - return 202
        elif task.status == TaskStatus.processing:
            raise HTTPException(
                status_code=TaskStatusHttpCode.processing.value,
                detail=ErrorResponseModel(
                    code=TaskStatusHttpCode.processing.value,
                    message=TaskStatusHttpMessage.processing.value,
                    router=str(request.url),
                    params=dict(request.query_params),
                ).model_dump()
            )
        # 任务失败 - 返回500 | Task failed - return 500
        elif task.status == TaskStatus.failed:
            raise HTTPException(
                status_code=TaskStatusHttpCode.failed.value,
                detail=ErrorResponseModel(
                    code=TaskStatusHttpCode.failed.value,
                    message=TaskStatusHttpMessage.failed.value,
                    router=str(request.url),
                    params=dict(request.query_params),
                ).model_dump()
            )

        # 获取任务的结果 | Get the result of the task
        task_result = task.result
        # 获取任务的text字段 | Get the text field of the task
        task_text = task_result.get("text")

        # 请求 ChatGPT API 进行总结

        if not _ChatGPTTaskRequest.chatgpt_prompt:
            _ChatGPTTaskRequest.chatgpt_prompt = f"""
            Summarize and analyze the following content with a natural, conversational tone. Focus on the main points, possible intent, tone, and likely reader reactions. Keep the response thoughtful and engaging, as if discussing with a friend.
            """.replace("\n", "").strip()

        chatgpt_user_content = _ChatGPTTaskRequest.chatgpt_prompt + "\n\n" + f"Contents: {task_text}"

        openai_client = AsyncOpenAI(
            # 配置OpenAI API Key | Configure OpenAI API Key
            api_key=_ChatGPTTaskRequest.chatgpt_api_key if _ChatGPTTaskRequest.chatgpt_api_key else Settings.ChatGPTSettings.API_Key
        )
        openai_gpt_model = _ChatGPTTaskRequest.chatgpt_model if _ChatGPTTaskRequest.chatgpt_model else Settings.ChatGPTSettings.GPT_Model
        chat_completion = await openai_client.chat.completions.create(
            model=openai_gpt_model,
            messages=[
                {"role": "system", "content": f"Please use the language '{_ChatGPTTaskRequest.output_language}' as the output language."},
                {"role": "user", "content": chatgpt_user_content}
            ]
        )
        # summary_text = chat_completion['choices'][0]['message']['content'].strip()

        chatgpt_data = {
            "task_text": task_text,
            "chat_completion": chat_completion.model_dump()
        }

        # 是否保存到数据库 | Whether to save to database
        if _ChatGPTTaskRequest.save_to_database:
            # 保存到数据库 | Save to database
            await request.app.state.db_manager.save_chatgpt_task(
                task_id=_ChatGPTTaskRequest.task_id,
                chatgpt_data=chatgpt_data
            )

        return ResponseModel(
            code=TaskStatusHttpCode.completed.value,
            router=str(request.url),
            params=_ChatGPTTaskRequest.model_dump(),
            data=chatgpt_data
        )

    # 数据库错误 - 返回503 | Database error - return 503
    except SQLAlchemyError as db_error:
        logger.error(f"Database error: {str(db_error)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponseModel(
                code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=TaskStatusHttpMessage.service_unavailable.value,
                router=str(request.url),
                params=_ChatGPTTaskRequest.model_dump()
            ).model_dump()
        )

    except HTTPException as http_error:
        raise http_error

    # 未知错误 - 返回500 | Unknown error - return 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"An unexpected error occurred while retrieving the task result: {str(e)}",
                router=str(request.url),
                params=_ChatGPTTaskRequest.model_dump()
            ).model_dump()
        )

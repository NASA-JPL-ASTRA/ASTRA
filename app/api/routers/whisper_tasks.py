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
from typing import Union, Optional
from urllib.parse import urlparse

from fastapi import Request, APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks, Query, status, Body
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.models.APIResponseModel import ResponseModel, ErrorResponseModel
from app.api.models.WhisperTaskRequest import WhisperTaskFileOption
from app.database.models.TaskModels import (
    TaskStatus,
    TaskStatusHttpCode,
    TaskStatusHttpMessage,
    QueryTasksOptionalFilter
)
from app.utils.logging_utils import configure_logging

router = APIRouter()

# 配置日志记录器
logger = configure_logging(name=__name__)


# 创建任务 | Create task
@router.post(
    "/tasks/create",
    response_model=ResponseModel,
    summary="创建任务 / Create task",
    response_description="创建任务的结果信息 / Result information of creating a task"
)
async def task_create(
        request: Request,
        file_upload: Union[UploadFile, str, None] = File(
            None,
            description="媒体文件（支持的格式：音频和视频，如 MP3, WAV, MP4, MKV 等） / Media file (supported formats: audio and video, e.g., MP3, WAV, MP4, MKV)"
        ),
        task_data: WhisperTaskFileOption = Query()
) -> ResponseModel:
    """
    # [中文]

    ### 用途说明:

    - 上传媒体文件或指定媒体文件的 URL 地址，并创建一个后台处理的 Whisper 任务。
    - 任务的处理优先级可以通过`priority`参数指定。
    - 任务的类型可以通过`task_type`参数指定。
    - 任务的处理不是实时的，这样的好处是可以避免线程阻塞，提高性能。
    - 可以通过`/api/whisper/tasks/result`端点查询任务结果。
    - 此接口提供一个回调参数，用于在任务完成时通知客户端，默认发送一个 POST 请求，你可以在接口文档中回调测试接口查看示例。

    ### 参数说明:

    - `file` (UploadFile): 上传的媒体文件，支持 Ffmpeg 支持的音频和视频格式，与`file_url`参数二选一。
    - `file_url` (Optional[str]): 媒体文件的 URL 地址，与`file`参数二选一。
    - `task_type` (str): 任务类型，默认为 'transcription'，具体取值如下。
        - 当后端使用 `openai_whisper` 引擎时，支持如下取值:
            - `transcribe`: 转录任务。
            - `translate`: 根据`language`参数指定的语言进行翻译任务。
        - 当后端使用 `faster_whisper` 引擎时，支持如下取值:
            - `transcribe`: 转录任务。
            - `translate`: 根据`language`参数指定的语言进行翻译任务。
    - `callback_url` (Optional[str]): 回调URL，任务完成时通知客户端，默认为空。
        - 任务完成后回调程序会发送一个 POST 请求，包含任务数据。
        - 你可以参考接口文档中的回调测试接口在控制台查看回调信息。
        - 例如：`http://localhost/api/whisper/callback/test`
    - `priority` (TaskPriority): 任务优先级，默认为 `normal`，具体取值如下：
        - `low`: 低优先级，使用小写字母。
        - `normal`: 正常优先级，使用小写字母。
        - `high`: 高优先级，使用小写字母。
    - `platform` (Optional[str]): 指定平台，例如 'tiktok' 或 'douyin'，用于方便区分不同平台的任务在数据库进行查询和分类，默认为空，可以根据需要自定义。
    - `language` (str): 指定输出语言，例如 'en' 或 'zh'，留空则自动检测。
    - `temperature` (str): 采样温度，可以是单个值或使用英文逗号分隔的多个值，将在后端转换为列表，例如 "0.8,1.0"。
    - `compression_ratio_threshold` (float): 压缩比阈值，默认为 1.8。
    - `no_speech_threshold` (float): 无声部分的概率阈值，默认为 0.6。
    - `condition_on_previous_text` (bool): 在连续语音中更准确地理解上下文，默认为 True。
    - `initial_prompt` (str): 初始提示文本，默认为空。
    - `word_timestamps` (bool): 是否提取每个词的时间戳信息，默认为 False。
    - `prepend_punctuations` (str): 前置标点符号集合，默认为 "\"'“¿([{-"。
    - `append_punctuations` (str): 后置标点符号集合，默认为 "\"'.。,，!！?？:：”)]}、"。
    - `clip_timestamps` (str): 裁剪时间戳，避免超出范围问题，默认为 "0"，可以是单个值或使用逗号分隔的多个值。
    - `hallucination_silence_threshold` (Optional[float]): 幻听静音阈值，默认为 None。

    ### 返回:

    - 返回一个包含任务信息的响应，包括任务ID、状态、优先级等信息。

    ### 错误代码说明:

    - `400`: 请求参数错误，例如文件或文件URL为空。
    - `500`: 未知错误。

    # [English]

    ### Purpose:

    - Upload a media file or specify the URL address of the media file and create a Whisper task for background processing.
    - The processing priority of the task can be specified using the `priority` parameter.
    - The type of task can be specified using the `task_type` parameter.
    - The processing of the task is not real-time, which avoids thread blocking and improves performance.
    - The task result can be queried using the `/api/whisper/tasks/result` endpoint.
    - This endpoint provides a callback interface to notify the client when the task is completed, which sends a POST request by default. You can view an example in the callback test interface in the API documentation.

    ### Parameters:

    - `file` (UploadFile): The uploaded media file, supporting audio and video formats supported by Ffmpeg, either `file` or `file_url` parameter is required.
    - `file_url` (Optional[str]): URL address of the media file, either `file` or `file_url` parameter is required.
    - `task_type` (str): The type of
    task, default is 'transcription', specific values are as follows.
        - When the backend uses the `openai_whisper` engine, the following values are supported:
            - `transcribe`: Transcription task.
            - `translate`: Translation task based on the language specified by the `language` parameter.
        - When the backend uses the `faster_whisper` engine, the following values are supported:
            - `transcribe`: Transcription task.
            - `translate`: Translation task based on the language specified by the `language` parameter.
    - `callback_url` (Optional[str]): Callback URL to notify the client when the task is completed, default is empty.
        - The callback program will send a POST request containing task data after the task is completed.
        - You can view the callback information in the console by referring to the callback test interface in the API documentation.
        - For example: `http://localhost/api/whisper/callback/test`
    - `priority` (TaskPriority): Task priority, default is `normal`, specific values are as follows:
        - `low`: Low priority, use lowercase letters.
        - `normal`: Normal priority, use lowercase letters.
        - `high`: High priority, use lowercase letters.
    - `platform` (Optional[str]): Specify the platform, e.g., 'tiktok' or 'douyin', for easy query and classification of tasks from different platforms in the database, default is empty, can be customized according to needs.
    - `language` (str): Specify the output language, e.g., 'en' or 'zh', leave empty for auto-detection.
    - `temperature` (str): Sampling temperature, can be a single value or multiple values separated by commas, which will be converted to a list on the backend, e.g., "0.8,1.0".
    - `compression_ratio_threshold` (float): Compression ratio threshold, default is 1.8.
    - `no_speech_threshold` (float): No-speech probability threshold, default is 0.6.
    - `condition_on_previous_text` (bool): Condition on previous text for more accurate understanding of context in continuous speech, default is True.
    - `initial_prompt` (str): Initial prompt text, default is empty.
    - `word_timestamps` (bool): Whether to extract word-level timestamp information, default is False.
    - `prepend_punctuations` (str): Prepend punctuation characters, default is "\"'“¿([{-".
    - `append_punctuations` (str): Append punctuation characters, default is "\"'.。,，!！?？:：”)]}、".
    - `clip_timestamps` (str): Clip timestamps to avoid out-of-range issues, default is "0", can be a single value or multiple values separated by commas.
    - `hallucination_silence_threshold` (Optional[float]): Hallucination silence threshold, default is None.

    ### Returns:

    - Returns a response containing task information, including task ID, status, priority, etc.

    ### Error Code Description:

    - `400`: Request parameter error, such as file or file URL is empty.
    - `500`: Unknown error.
    """

    # 检查文件或文件URL是否为空 | Check if the file or file URL is empty
    if not (file_upload or task_data.file_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="The file or file_url parameter cannot be empty, you must provide one of them",
                router=str(request.url),
                params=dict(request.query_params),
            ).model_dump()
        )

    # 检查文件和文件URL是否同时存在 | Check if both file and file URL are provided
    if file_upload and task_data.file_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="The 'file_upload' and 'file_url' parameters cannot be both provided, you must provide only one of them.",
                router=str(request.url),
                params=dict(request.query_params),
            ).model_dump()
        )

    # 检查 URL 格式是否正确 | Check if the URL format is correct
    if task_data.file_url:
        parsed_url = urlparse(task_data.file_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="The format of the file URL is incorrect",
                    router=str(request.url),
                    params=dict(request.query_params),
                ).model_dump()
            )

    try:
        decode_options = {
            "language": task_data.language if task_data.language else None,
            "temperature": [float(temp) for temp in task_data.temperature.split(",")] if "," in task_data.temperature else float(task_data.temperature),
            "compression_ratio_threshold": task_data.compression_ratio_threshold,
            "no_speech_threshold": task_data.no_speech_threshold,
            "condition_on_previous_text": task_data.condition_on_previous_text,
            "initial_prompt": task_data.initial_prompt,
            "word_timestamps": task_data.word_timestamps,
            "prepend_punctuations": task_data.prepend_punctuations,
            "append_punctuations": task_data.append_punctuations,
            "clip_timestamps": [float(clip) for clip in task_data.clip_timestamps.split(",")] if "," in task_data.clip_timestamps else task_data.clip_timestamps,
            "hallucination_silence_threshold": task_data.hallucination_silence_threshold
        }
        task_info = await request.app.state.whisper_service.create_whisper_task(
            file_upload=file_upload if file_upload else None,
            file_name=file_upload.filename if file_upload else None,
            file_url=task_data.file_url if task_data.file_url else None,
            callback_url=task_data.callback_url,
            platform=task_data.platform,
            decode_options=decode_options,
            task_type=task_data.task_type,
            priority=task_data.priority,
            request=request
        )
        return ResponseModel(code=200,
                             router=str(request.url),
                             params={
                                 **decode_options,
                                 "task_type": task_data.task_type,
                                 "priority": task_data.priority,
                                 "callback_url": task_data.callback_url
                             },
                             data=task_info.to_dict())

    except HTTPException as http_error:
        raise http_error

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"An unexpected error occurred while creating the transcription task: {str(e)}",
                router=str(request.url),
                params=dict(request.query_params),
            ).model_dump()
        )


# 查询任务 | Query task
@router.post("/tasks/query",
             response_model=ResponseModel,
             summary="查询任务 / Query task",
             response_description="查询任务的结果信息 / Result information of querying a task"
             )
async def task_query(
        request: Request,
        params: QueryTasksOptionalFilter
):
    """
    # [中文]

    ### 用途说明:
    - 根据多种筛选条件查询任务列表，包括任务状态、优先级、创建时间、语言、引擎名称等信息。
    - 该接口适用于分页查询，并且通过 `limit` 和 `offset` 参数控制每页显示的记录数，支持客户端逐页加载数据。

    ### 参数说明:
    - `status` (TaskStatus): 筛选任务状态：
        - 例如 `queued`（在队列中）、`processing`（处理中）、`completed`（已完成）或`failed`（失败）。
    - `priority` (TaskPriority): 筛选任务优先级：
        - 例如 `low`、`normal`、`high`。
    - `created_after` (str): 创建时间的起始时间，格式为 `YYYY-MM-DDTHH:MM:SS`，为空时忽略该条件。
    - `created_before` (str): 创建时间的结束时间，格式为 `YYYY-MM-DDTHH:MM:SS`，为空时忽略该条件。
    - `language` (str): 任务的语言代码，例如 `zh`或 `en`。设置为空字符串 `""` 可查询所有语言的任务。
    - `engine_name` (str): 引擎名称，例如 `faster_whisper` 或 `openai_whisper`。
    - `has_result` (bool): 指定是否要求任务有结果数据。
    - `has_error` (bool): 指定是否要求任务有错误信息。
    - `limit` (int): 每页的记录数量，默认值为 `20`，用户可以根据需要自定义每页的记录数。
    - `offset` (int): 数据分页的起始位置，默认值为 `0`，使用响应中的 `next_offset` 值进行下一页查询。

    ### 返回:
    - `tasks` (list): 包含满足条件的任务列表，每个任务记录包括任务ID、状态、优先级、创建时间等详细信息。
    - `total_count` (int): 符合条件的任务总数。
    - `has_more` (bool): 是否还有更多数据。如果为 `True`，则表示存在下一页数据。
    - `next_offset` (int): 下次分页请求的偏移量。用户可以通过此值构建下一页查询请求。

    ### 使用示例:
    - 请求示例：
        ```json
        {
          "status": "completed",
          "priority": "normal",
          "created_after": "",
          "created_before": "",
          "language": "",
          "engine_name": "faster_whisper",
          "has_result": true,
          "has_error": false,
          "limit": 20,
          "offset": 0
        }
        ```
    - 响应示例：
        ```json
        {
            "code": 200,
            "router": "http://localhost/api/whisper/tasks/query",
            "params": { ... },
            "data": {
                "tasks": [
                    {
                        "id": 123,
                        "status": "completed",
                        "priority": "normal",
                        "created_at": "2024-05-15T12:34:56",
                        "language": "en",
                        "engine_name": "faster_whisper",
                        "result": {...},
                        "error_message": None
                    },
                    ...
                ],
                "total_count": 55,
                "has_more": True,
                "next_offset": 10
            }
        }
        ```

    ### 错误代码说明:
    - `500`: 未知错误，通常为内部错误。

    # [English]

    ### Purpose:
    - Query the task list based on multiple filtering conditions, including task status, priority, creation time, language, engine name, etc.
    - This endpoint is suitable for paginated queries, and the number of records displayed per page is controlled by the `limit` and `offset` parameters, supporting clients to load data page by page.

    ### Parameters:
    - `status` (TaskStatus): Filter task status:
        - e.g., 'queued' (in the queue), 'processing' (processing), 'completed' (completed), or 'failed' (failed).
    - `priority` (TaskPriority): Filter task priority:
        - e.g., 'low', 'normal', 'high'.
    - `created_after` (str): Start time of creation time, format is 'YYYY-MM-DDTHH:MM:SS', ignore this condition when empty.
    - `created_before` (str): End time of creation time, format is 'YYYY-MM-DDTHH:MM:SS', ignore this condition when empty.
    - `language` (str): Language code of the task, e.g., `zh` or `en`. Set to an empty string `""` to query tasks in all languages.
    - `engine_name` (str): Engine name, e.g., 'faster_whisper' or 'openai_whisper'.
    - `has_result` (bool): Specify whether the task requires result data.
    - `has_error` (bool): Specify whether the task requires error information.
    - `limit` (int): Number of records per page, default is `20`, users can customize the number of records per page according to their needs.
    - `offset` (int): Starting position of data pagination, default is `0`, use the `next_offset` value in the response for the next page query.

    ### Returns:
    - `tasks` (list): List of tasks that meet the conditions, each task record includes detailed information such as task ID, status, priority, creation time, etc.
    - `total_count` (int): Total number of tasks that meet the conditions.
    - `has_more` (bool): Whether there is more data. If `True`, it means there is more data on the next page.
    - `next_offset` (int): Offset value for the next page request. Users can use this value to construct the next page query request.

    ### Example:
    - Request example:
        ```json
        {
          "status": "completed",
          "priority": "normal",
          "created_after": "",
          "created_before": "",
          "language": "",
          "engine_name": "faster_whisper",
          "has_result": true,
          "has_error": false,
          "limit": 20,
          "offset": 0
        }
        ```
    - Response example:
        ```json
        {
            "code": 200,
            "router": "http://localhost/api/whisper/tasks/query",
            "params": { ... },
            "data": {
                "tasks": [
                    {
                        "id": 123,
                        "status": "completed",
                        "priority": "normal",
                        "created_at": "2024-05-15T12:34:56",
                        "language": "en",
                        "engine_name": "faster_whisper",
                        "result": {...},
                        "error_message": None
                    },
                    ...
                ],
                "total_count": 55,
                "has_more": True,
                "next_offset": 10
            }
        }
        ```

    ### Error Code Description:
    - `500`: Unknown error, usually an internal error.
    """

    try:
        result = await request.app.state.db_manager.query_tasks(params)

        return ResponseModel(
            code=200,
            router=str(request.url),
            params=params.model_dump(),
            data=result
        )

    except HTTPException as http_error:
        raise http_error

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"An unexpected error occurred while creating the transcription task: {str(e)}",
                router=str(request.url),
                params=dict(request.query_params),
            ).model_dump()
        )


# 根据任务ID删除任务 | Delete task by task ID
@router.delete("/tasks/delete",
               summary="根据任务ID删除任务 / Delete task by task ID",
               response_model=ResponseModel,
               response_description="删除任务的结果信息 / Result information of deleting a task"
               )
async def task_delete(
        request: Request,
        task_id: int = Query(description="任务ID / Task ID")
):
    """
    # [中文]

    ### 用途说明:
    - 根据任务ID删除任务，删除后任务数据将被永久删除。

    ### 参数说明:
    - `task_id` (int): 任务ID。

    ### 返回:
    - 返回一个包含删除任务信息的响应，包括任务ID、状态、优先级等信息。

    ### 错误代码说明:
    - `200`: 任务删除成功。
    - `404`: 任务未找到，可能是任务ID不存在。
    - `500`: 未知错误。

    # [English]

    ### Purpose:
    - Delete the task by task ID, and the task data will be permanently deleted after deletion.

    ### Parameters:
    - `task_id` (int): Task ID.

    ### Returns:
    - Returns a response containing the deleted task information, including task ID, status, priority, etc.

    ### Error Code Description:
    - `200`: Task deleted successfully.
    - `404`: Task not found, possibly because the task ID does not exist.
    - `500`: Unknown error.
    """
    try:
        # 通过任务ID删除任务 | Delete task by task ID
        task = await request.app.state.db_manager.delete_task(task_id)
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

        data = {
            "task_id": task_id,
            "message": "Task deleted successfully"
        }

        # 任务删除成功 - 返回200 | Task deleted successfully - return 200
        return ResponseModel(
            code=status.HTTP_200_OK,
            router=str(request.url),
            params=dict(request.query_params),
            data=data
        )

    except HTTPException as http_error:
        raise http_error

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="An unexpected error occurred while deleting the task",
                router=str(request.url),
                params=dict(request.query_params),
            ).model_dump()
        )


# 获取任务结果 | Get task result
@router.get("/tasks/result",
            summary="获取任务结果 / Get task result",
            response_model=ResponseModel,
            response_description="获取任务结果的结果信息 / Result information of getting task result"
            )
async def task_result(
        request: Request,
        task_id: int = Query(description="任务ID / Task ID"),
        format: Optional[str] = Query(
            "default",
            description="输出格式: 'default' 返回完整任务信息, 'astra' 返回 ASTRA/Backend 集成用的简化格式 / Output format: 'default' for full task info, 'astra' for ASTRA Backend integration"
        )
):
    """
    # [中文]

    ### 用途说明:
    - 获取指定任务的结果信息。

    ### 参数说明:
    - `task_id` (int): 任务ID。

    ### 返回:
    - 返回一个包含任务结果信息的响应，包括任务ID、状态、优先级等信息。

    ### 错误代码说明:
    - `200`: 任务已完成，返回任务结果信息。
    - `202`: 任务处于排队中，或正在处理中。
    - `404`: 任务未找到，可能是任务ID不存在。
    - `500`: 任务处理失败，或发生未知错误。
    - `503`: 数据库错误。

    # [English]

    ### Purpose:
    - Get the result information of the specified task.

    ### Parameters:
    - `task_id` (int): Task ID.

    ### Returns:
    - Returns a response containing task result information, including task ID, status, priority, etc.

    ### Error Code Description:
    - `200`: Task is completed, return task result information.
    - `202`: Task is queued or processing.
    - `404`: Task not found, possibly because the task ID does not exist.
    - `500`: Task processing failed or an unknown error occurred.
    - `503`: Database error.
    """
    try:
        # 通过任务ID查询任务 | Query task by task ID
        task = await request.app.state.db_manager.get_task(task_id)
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

        # 任务已完成 - 返回200 | Task is completed - return 200
        # ASTRA 格式: 返回 Backend 集成用的简化结构 | ASTRA format: simplified structure for Backend integration
        if format and format.lower() == "astra":
            result = task.result or {}
            segments = result.get("segments", [])
            astra_data = {
                "session_id": task.platform or f"task-{task.id}",
                "task_id": task.id,
                "transcript": result.get("text", ""),
                "segments": [
                    {"start": s.get("start", 0), "end": s.get("end", 0), "text": s.get("text", "").strip()}
                    for s in segments
                ],
                "language": task.language or result.get("info", {}).get("language", ""),
                "timestamp": task.created_at.isoformat() if task.created_at else None,
            }
            return ResponseModel(
                code=TaskStatusHttpCode.completed.value,
                router=str(request.url),
                params=dict(request.query_params),
                data=astra_data
            )
        return ResponseModel(
            code=TaskStatusHttpCode.completed.value,
            router=str(request.url),
            params=dict(request.query_params),
            data=task.to_dict()
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
                params=dict(request.query_params),
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
                params=dict(request.query_params),
            ).model_dump()
        )


@router.post("/callback/test",
             summary="测试回调接口 / Test callback interface",
             response_model=ResponseModel,
             response_description="测试回调接口的结果信息 / Result information of testing the callback interface"
             )
async def callback_test(
        request: Request,
        callback_data: dict = Body(..., description="回调请求体 / Callback request body")
):
    """
    # [中文]

    ### 用途说明:
    - 测试回调接口，用于测试回调功能是否正常。
    - 在本地测试时，你可以使用此接口来验证回调功能是否正常。
    - 在创建任务时，你可以提供此接口的URL作为回调URL，如：`http://localhost/api/whisper/callback/test`。
    - 你可以参考此接口的设计来实现自己的回调接口。

    ### 参数说明:
    - `callback_data` (dict): 任务完成后发送的回调数据，如果未提供则使用演示数据。

    ### 返回:
    - 返回一个包含回调数据的响应。

    ### 错误代码说明:

    - `500`: 未知错误。

    # [English]

    ### Purpose:
    - Test the callback interface to verify that the callback function works correctly.
    - When testing locally, you can use this endpoint to verify that the callback function works correctly.
    - When creating a task, you can provide the URL of this endpoint as the callback URL, e.g., `http://localhost/api/whisper/callback/test`.
    - You can refer to the design of this endpoint to implement your own callback interface.

    ### Parameters:
    - `callback_data` (dict): Callback data sent after the task is completed, use demo data if not provided.

    ### Returns:
    - Returns a response containing callback data.

    ### Error Code Description:

    - `500`: Unknown error.
    """
    try:
        # 如果未提供回调数据，则使用演示数据 | Use demo data if callback data is not provided
        callback_data = callback_data or {
            "id": 1,
            "status": "completed",
            "callback_url": "",
            "priority": "normal",
            "engine_name": "faster_whisper",
            "task_type": "transcribe",
            "created_at": "2024-11-01T00:37:15.319257",
            "updated_at": "2024-11-01T00:37:18.743966",
            "task_processing_time": 1.784804,
            "file_path": "C:\\Users\\Evil0ctal\\PycharmProjects\\Whisper-Speech-to-Text-API\\temp_files\\e01342d1fdf54d85ad5ed59f0de8c80e.mp4",
            "file_name": "Example.mp4",
            "file_size_bytes": 1244080,
            "file_duration": 11.774,
            "language": "zh",
            "decode_options": {
                "language": None,
                "temperature":
                    [
                        0.2
                    ],
                "compression_ratio_threshold": 1.8,
                "no_speech_threshold": 0.6,
                "condition_on_previous_text": True,
                "initial_prompt": "",
                "word_timestamps": False,
                "prepend_punctuations": "\"'“¿([{-",
                "append_punctuations": "\"'.。,，!！?？:：”)]}、",
                "clip_timestamps":
                    [
                        0
                    ],
                "hallucination_silence_threshold": 0
            },
            "error_message": None,
            "output_url": "http://127.0.0.1/api/whisper/tasks/result?task_id=1",
            "result": {
                "transcription": "吃饭了吗 吃饭了 等我吃完饭再来找你玩哦 好",
                "segments": [],
                "info": {
                    "language": "zh",
                    "language_probability": 0.974609375,
                    "duration": 11.7739375,
                    "duration_after_vad": 11.7739375,
                    "all_language_probs":
                        [
                            [
                                "zh",
                                0.974609375
                            ],
                            [
                                "en",
                                0.006671905517578125
                            ],
                            [
                                "nn",
                                0.00337982177734375
                            ],
                            [
                                "jw",
                                0.003078460693359375
                            ],
                            [
                                "ja",
                                0.001781463623046875
                            ],
                            [
                                "vi",
                                0.0015239715576171875
                            ],
                            [
                                "ko",
                                0.0014314651489257812
                            ],
                            [
                                "ar",
                                0.0006604194641113281
                            ],
                            [
                                "pt",
                                0.0006504058837890625
                            ],
                            [
                                "ms",
                                0.0005559921264648438
                            ],
                            [
                                "th",
                                0.0005025863647460938
                            ],
                            [
                                "cy",
                                0.000453948974609375
                            ],
                            [
                                "pl",
                                0.00042319297790527344
                            ],
                            [
                                "km",
                                0.0004134178161621094
                            ],
                            [
                                "de",
                                0.0003821849822998047
                            ],
                            [
                                "es",
                                0.0003733634948730469
                            ],
                            [
                                "ru",
                                0.0003676414489746094
                            ],
                            [
                                "haw",
                                0.0003094673156738281
                            ],
                            [
                                "fr",
                                0.0002586841583251953
                            ],
                            [
                                "la",
                                0.0002586841583251953
                            ],
                            [
                                "tr",
                                0.00018775463104248047
                            ],
                            [
                                "id",
                                0.00018489360809326172
                            ],
                            [
                                "si",
                                0.0001556873321533203
                            ],
                            [
                                "it",
                                0.00014972686767578125
                            ],
                            [
                                "yue",
                                0.0001270771026611328
                            ],
                            [
                                "tl",
                                0.00012314319610595703
                            ],
                            [
                                "br",
                                0.0000826716423034668
                            ],
                            [
                                "uk",
                                0.00007468461990356445
                            ],
                            [
                                "ro",
                                0.0000718235969543457
                            ],
                            [
                                "sn",
                                0.0000680088996887207
                            ],
                            [
                                "nl",
                                0.00006335973739624023
                            ],
                            [
                                "hu",
                                0.00006145238876342773
                            ],
                            [
                                "my",
                                0.00005817413330078125
                            ],
                            [
                                "sv",
                                0.00004357099533081055
                            ],
                            [
                                "cs",
                                0.0000432133674621582
                            ],
                            [
                                "he",
                                0.00003933906555175781
                            ],
                            [
                                "fa",
                                0.00003236532211303711
                            ],
                            [
                                "mi",
                                0.00003039836883544922
                            ],
                            [
                                "da",
                                0.00002562999725341797
                            ],
                            [
                                "el",
                                0.00002384185791015625
                            ],
                            [
                                "hi",
                                0.000022351741790771484
                            ],
                            [
                                "ur",
                                0.000019311904907226562
                            ],
                            [
                                "ta",
                                0.000016808509826660156
                            ],
                            [
                                "no",
                                0.000014901161193847656
                            ],
                            [
                                "fi",
                                0.000013470649719238281
                            ],
                            [
                                "hr",
                                0.000011324882507324219
                            ],
                            [
                                "gl",
                                0.000010788440704345703
                            ],
                            [
                                "ml",
                                0.000010669231414794922
                            ],
                            [
                                "sa",
                                0.00001043081283569336
                            ],
                            [
                                "bs",
                                0.000009775161743164062
                            ],
                            [
                                "ca",
                                0.000008046627044677734
                            ],
                            [
                                "yo",
                                0.000007450580596923828
                            ],
                            [
                                "sk",
                                0.000006139278411865234
                            ],
                            [
                                "eu",
                                0.000006020069122314453
                            ],
                            [
                                "lo",
                                0.000004231929779052734
                            ],
                            [
                                "oc",
                                0.000004231929779052734
                            ],
                            [
                                "bn",
                                0.000003933906555175781
                            ],
                            [
                                "ht",
                                0.0000036954879760742188
                            ],
                            [
                                "sl",
                                0.0000035762786865234375
                            ],
                            [
                                "yi",
                                0.0000032186508178710938
                            ],
                            [
                                "sw",
                                0.000003159046173095703
                            ],
                            [
                                "fo",
                                0.0000030994415283203125
                            ],
                            [
                                "be",
                                0.0000029206275939941406
                            ],
                            [
                                "bg",
                                0.000002562999725341797
                            ],
                            [
                                "bo",
                                0.0000024437904357910156
                            ],
                            [
                                "ne",
                                0.0000023245811462402344
                            ],
                            [
                                "te",
                                0.000002086162567138672
                            ],
                            [
                                "az",
                                0.0000019073486328125
                            ],
                            [
                                "mn",
                                0.0000016689300537109375
                            ],
                            [
                                "kk",
                                0.0000014901161193847656
                            ],
                            [
                                "pa",
                                0.0000010132789611816406
                            ],
                            [
                                "hy",
                                0.0000010132789611816406
                            ],
                            [
                                "sd",
                                8.940696716308594e-7
                            ],
                            [
                                "ps",
                                8.344650268554688e-7
                            ],
                            [
                                "sr",
                                8.344650268554688e-7
                            ],
                            [
                                "lt",
                                7.152557373046875e-7
                            ],
                            [
                                "lv",
                                7.152557373046875e-7
                            ],
                            [
                                "is",
                                6.556510925292969e-7
                            ],
                            [
                                "mr",
                                5.364418029785156e-7
                            ],
                            [
                                "ln",
                                2.384185791015625e-7
                            ],
                            [
                                "af",
                                1.7881393432617188e-7
                            ],
                            [
                                "et",
                                1.1920928955078125e-7
                            ],
                            [
                                "kn",
                                5.960464477539063e-8
                            ],
                            [
                                "gu",
                                5.960464477539063e-8
                            ],
                            [
                                "sq",
                                5.960464477539063e-8
                            ],
                            [
                                "mk",
                                5.960464477539063e-8
                            ],
                            [
                                "ka",
                                5.960464477539063e-8
                            ],
                            [
                                "as",
                                5.960464477539063e-8
                            ],
                            [
                                "uz",
                                0
                            ],
                            [
                                "so",
                                0
                            ],
                            [
                                "tk",
                                0
                            ],
                            [
                                "mt",
                                0
                            ],
                            [
                                "lb",
                                0
                            ],
                            [
                                "mg",
                                0
                            ],
                            [
                                "tt",
                                0
                            ],
                            [
                                "tg",
                                0
                            ],
                            [
                                "ha",
                                0
                            ],
                            [
                                "ba",
                                0
                            ],
                            [
                                "su",
                                0
                            ],
                            [
                                "am",
                                0
                            ]
                        ],
                    "transcription_options":
                        [
                            5,
                            5,
                            1,
                            1,
                            1,
                            0,
                            -1,
                            0.6,
                            2.4,
                            True,
                            0.5,
                            [
                                0.2
                            ],
                            "",
                            None,
                            True,
                            [
                                -1
                            ],
                            False,
                            1,
                            False,
                            "\"'“¿([{-",
                            "\"'.。,，!！?？:：”)]}、",
                            None,
                            [
                                0
                            ],
                            0,
                            None
                        ],
                    "vad_options": None
                }
            }
        }

        logger.info(f"Callback interface received data: {str(callback_data)[:100]}")

        return ResponseModel(
            code=status.HTTP_200_OK,
            router=str(request.url),
            params=callback_data,
            data={
                "message": "Callback interface test successful.",
                "callback_data": callback_data
            }
        )

    except HTTPException as http_error:
        raise http_error

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"An unexpected error occurred while testing the callback interface: {str(e)}",
                router=str(request.url),
                params=dict(request.query_params),
            ).model_dump()
        )


# 从视频文件中提取音频 | Extract audio from a video file
@router.post("/extract_audio",
             summary="从视频文件中提取音频文件 / Extract audio from a video file",
             response_class=FileResponse,
             response_description="包含音频文件的响应 / Response containing the audio file"
             )
async def extract_audio(
        request: Request,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...,
                                description="视频文件，支持的格式如 MP4, MKV 等 / Video file, supported formats like MP4, MKV etc."),
        sample_rate: int = Form(22050, description="音频的采样率（单位：Hz），例如 22050 或 44100。"),
        bit_depth: int = Form(2, description="音频的位深度（1 或 2 字节），决定音频的质量和文件大小。"),
        output_format: str = Form("wav", description="输出音频的格式，可选 'wav' 或 'mp3'。")
) -> FileResponse:
    """
    # [中文]

    ### 用途说明:

    - 从视频文件中提取音频。

    ### 参数说明:

    - `file` (UploadFile): 上传的视频文件。
    - `sample_rate` (int): 采样率。
    - `bit_depth` (int): 位深度。
    - `output_format` (str): 输出格式，'wav' 或 'mp3'。

    ### 返回:

    - 包含音频文件的响应。

    ### 错误代码说明:

    - `500`: 未知错误。

    # [English]

    ### Purpose:

    - Extract audio from a video file.

    ### Parameters:

    - `file` (UploadFile): The uploaded video file.
    - `sample_rate` (int): The sample rate.
    - `bit_depth` (int): The bit depth.
    - `output_format` (str): The output format, 'wav' or 'mp3'.

    ### Returns:

    - A response containing the audio file.

    ### Error Code Description:

    - `500`: Unknown error.
    """
    try:
        response = await request.app.state.whisper_service.extract_audio_from_video(
            file=file,
            background_tasks=background_tasks,
            sample_rate=sample_rate,
            bit_depth=bit_depth,
            output_format=output_format
        )
        return response

    except HTTPException as http_error:
        raise http_error

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"An unexpected error occurred while extracting audio from the video file: {str(e)}",
                router=str(request.url),
                params=dict(request.query_params),
            ).model_dump()
        )


# 根据任务ID生成字幕文件 | Generate subtitles based on task ID
@router.get("/generate_subtitles",
            summary="生成字幕文件 / Generate subtitles file",
            response_class=FileResponse,
            response_description="包含字幕文件的响应 / Response containing the subtitle file"
            )
async def generate_subtitles(
        request: Request,
        background_tasks: BackgroundTasks,
        task_id: int = Query(description="任务ID / Task ID"),
        output_format: str = Query("srt", description="输出格式，可选 'srt' 或 'vtt'。")
) -> FileResponse:
    """
    # [中文]

    ### 用途说明:
    - 生成指定任务的字幕。

    ### 参数说明:
    - `task_id` (int): 任务ID。
    - `output_format` (str): 输出格式，'srt' 或 'vtt'。

    ### 返回:
    - 返回一个包含字幕文件的响应。

    ### 错误代码说明:
    - `500`: 未知错误。

    # [English]

    ### Purpose:

    - Generate subtitles for the specified task.

    ### Parameters:

    - `task_id` (int): Task ID.
    - `output_format` (str): Output format, 'srt' or 'vtt'.

    ### Returns:

    - A response containing the subtitle file.

    ### Error Code Description:

    - `500`: Unknown error.
    """
    task = await request.app.state.db_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponseModel(
                code=status.HTTP_404_NOT_FOUND,
                message=TaskStatusHttpMessage.not_found.value,
                router=str(request.url),
                params=dict(request.query_params),
            ).model_dump()
        )

    if task.status != TaskStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="This task is not available for generating subtitles.",
                router=str(request.url),
                params=dict(request.query_params),
            ).model_dump()
        )

    try:
        response = await request.app.state.whisper_service.generate_subtitle(
            task=task,
            output_format=output_format,
            background_tasks=background_tasks,
        )
        return response

    except HTTPException as http_error:
        raise http_error

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"An unexpected error occurred while generating subtitles: {str(e)}",
                router=str(request.url),
                params=dict(request.query_params),
            ).model_dump()
        )

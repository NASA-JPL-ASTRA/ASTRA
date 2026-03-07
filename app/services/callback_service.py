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

import datetime
from tenacity import *
from typing import Optional, Dict
from app.database.DatabaseManager import DatabaseManager
from app.http_client.AsyncHttpClient import AsyncHttpClient
from app.utils.logging_utils import configure_logging
from app.database.models.TaskModels import Task

logger = configure_logging(__name__)


class CallbackService:
    def __init__(self):
        self.default_headers = {
            "User-Agent": "Fast-Powerful-Whisper-AI-Services-API/HTTP Callback (https://github.com/Evil0ctal/Fast-Powerful-Whisper-AI-Services-API)",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(3))
    async def task_callback_notification(self,
                                         task: Task,
                                         db_manager: DatabaseManager,
                                         result_override: Optional[Dict] = None,
                                         proxy_settings: Optional[Dict[str, str]] = None,
                                         method: str = "POST",
                                         headers: Optional[dict] = None,
                                         request_timeout: int = 10
                                         ) -> None:
        """
        发送任务处理结果的回调通知。

        Sends a callback notification with the result of the task processing.

        :param task: 要发送回调通知的任务实例 | Task instance to send callback notification for
        :param db_manager: 数据库管理器实例 | Database manager instance
        :param result_override: 可选的处理结果覆盖（避免 DB 更新竞态导致回调无 result）| Optional result override to avoid race where callback runs before DB update
        :param proxy_settings: 可选的代理设置 | Optional proxy settings
        :param method: 可选的请求方法 | Optional request method
        :param headers: 可选的请求头 | Optional request headers
        :param request_timeout: 请求超时时间 | Request timeout
        :return: None
        """
        callback_url = task.callback_url
        headers = headers or self.default_headers
        if callback_url:
            logger.info(f"Sending task callback notification for task {task.id} to: {callback_url}")
            async with AsyncHttpClient(
                    proxy_settings=proxy_settings,
                    headers=headers,
                    request_timeout=request_timeout
            ) as client:

                # 获取任务数据 | Get task data
                task_data = await db_manager.get_task(task.id)
                payload = task_data.to_dict() if task_data else {}

                # 若传入 result_override 且 DB 中 result 为空，使用 override 避免竞态导致回调丢失转写
                if result_override and (not payload.get("result") or not (payload.get("result") or {}).get("text")):
                    payload["result"] = result_override.get("result", result_override)
                    payload["status"] = result_override.get("status", payload.get("status", "completed"))

                response = await client.fetch_data(
                    url=callback_url,
                    method=method,
                    headers=headers,
                    json=payload
                )

                # 更新任务的回调状态码和消息 | Update the callback status code and message of the task
                logger.info(f"Callback response status code for task {task.id}: {response.status_code}")
                await db_manager.update_task_callback_status(
                    task_id=task.id,
                    callback_status_code=response.status_code,
                    callback_message=response.text,
                    callback_time=datetime.datetime.now()
                )
        else:
            logger.info(f"No callback URL provided for task {task.id}, skipping callback notification.")

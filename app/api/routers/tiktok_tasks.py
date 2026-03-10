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
from typing import Union

from fastapi import Request, APIRouter, HTTPException, Form, status

from app.api.models.APIResponseModel import ResponseModel, ErrorResponseModel
from app.api.models.TikTokTaskRequest import TikTokVideoTask
from app.api.models.WhisperTaskRequest import WhisperTaskFileOption
from app.api.routers.whisper_tasks import task_create
from app.crawlers.platforms.tiktok.crawler import TikTokAPPCrawler
from app.utils.logging_utils import configure_logging

TikTokAPPCrawler = TikTokAPPCrawler()

router = APIRouter()

# 配置日志记录器
logger = configure_logging(name=__name__)


# 爬取TikTok视频并创建任务 | Crawl TikTok video and create task
@router.post("/video_task",
             response_model=ResponseModel,
             summary="创建任务 / Create task",
             response_description="创建任务的结果信息 / Result information of creating a task"
             )
async def create_tiktok_video_task(
        request: Request,
        tiktok_video_task: TikTokVideoTask = Form(...),
) -> Union[ResponseModel, ErrorResponseModel]:
    """
    # [中文]

    ### 用途说明:
    - 通过 TikTok 视频链接爬取视频并创建任务。

    ### 请求参数:
    - `url`: TikTok 视频链接，例如: `https://www.tiktok.com/@taylorswift/video/7359655005701311786`。
    - 其他参数与创建任务时的参数相同。

    ### 返回结果:
    - 返回创建任务的结果信息。

    ### 错误代码说明:

    - `400`: TikTok 视频抓取失败。
    - `500`: 未知错误。

    # [English]

    ### Description:
    - Crawl the video through the TikTok video link and create a task.

    ### Request parameters:
    - `url`: TikTok video link, for example: `https://www.tiktok.com/@taylorswift/video/7359655005701311786`.
    - Other parameters are the same as when creating a task.

    ### Return result:
    - Return the result information of creating a task.

    ### Error code description:

    - `400`: TikTok video crawl failed.
    - `500`: Unknown error.
    """
    try:
        url = str(tiktok_video_task.url)
        data = await TikTokAPPCrawler.fetch_one_video_by_url(url)

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid TikTok video URL",
                headers={"X-Error": "Invalid TikTok video URL"}
            )
        else:
            # $.video.play_addr.url_list.[0]
            play_addr = data.get("video", {}).get("play_addr", {}).get("url_list", [])[-1]
            # print(f"Video URL: {url}")

        # 创建任务 | Create task
        task_data = WhisperTaskFileOption(file_url=play_addr, **tiktok_video_task.model_dump())
        task_result = await task_create(
            request=request,
            file_upload=None,
            task_data=task_data
        )

        # 是否保存数据到数据库 | Whether to save data to the database
        if tiktok_video_task.save_data_in_db:
            # 保存数据到数据库 | Save data to database
            await request.app.state.db_manager.save_crawler_task(
                task_id=task_result.data.get("id"),
                url=url,
                data=data
            )

        return task_result

    except HTTPException as http_error:
        raise http_error

    except Exception as error:
        logger.error(f"An error occurred: {error}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"An unexpected error occurred while creating the transcription task: {str(error)}",
                router=str(request.url),
                params=dict(request.query_params),
            ).model_dump()
        )

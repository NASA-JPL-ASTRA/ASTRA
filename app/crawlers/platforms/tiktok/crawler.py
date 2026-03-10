# ==============================================================================
# Copyright (C) 2021 Evil0ctal
#
# This file is part of the Douyin_TikTok_Download_API project.
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
# 　　　　 　　  ＿＿
# 　　　 　　 ／＞　　フ
# 　　　 　　| 　_　 _ l
# 　 　　 　／` ミ＿xノ
# 　　 　 /　　　 　 |       Feed me Stars ⭐ ️
# 　　　 /　 ヽ　　 ﾉ
# 　 　 │　　|　|　|
# 　／￣|　　 |　|　|
# 　| (￣ヽ＿_ヽ_)__)
# 　＼二つ
# ==============================================================================
#
# Contributor Link:
# https://github.com/Evil0ctal]
#
# ==============================================================================

import asyncio
import re
import time
from urllib.parse import urlencode

from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_fixed

from app.crawlers.platforms.tiktok.endpoints import TikTokAPIEndpoints
from app.crawlers.platforms.tiktok.models import FeedVideoDetail
from app.http_client.AsyncHttpClient import AsyncHttpClient


class TikTokAPPCrawler:
    """
    TikTok API 爬虫类，用于获取 TikTok 视频详情 (TikTok API crawler class to fetch TikTok video details)
    """

    @staticmethod
    def get_tiktok_headers() -> dict:
        """
        生成 TikTok API 的请求头 (Generate request headers for TikTok API)
        """
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
            ),
            "Referer": "https://www.tiktok.com/",
            "Cookie": "ExampleCookie=HelloFromEvil0ctal",
            "x-ladon": "Hello From Evil0ctal!",
        }

    @staticmethod
    def model_to_query_string(model: BaseModel) -> str:
        """
        将 Pydantic 模型转换为 URL 查询字符串 (Convert a Pydantic model to a URL query string)
        """
        return urlencode(model.dict())

    # 获取单个作品数据 (Fetch a single TikTok video data)
    @retry(stop=stop_after_attempt(10), retry_error_callback=lambda retry_state: retry_state.outcome.result())
    async def fetch_one_video(self, aweme_id: str) -> dict:
        """
        根据视频 ID (aweme_id) 获取单个 TikTok 视频数据 (Fetch a single TikTok video data by video ID)

        :param aweme_id: 视频 ID (aweme_id) | Video ID (aweme_id)
        :return: 视频数据 (Video data)
        """
        # 构造请求参数和 URL (Construct request parameters and URL)
        headers = self.get_tiktok_headers()
        params = FeedVideoDetail(aweme_id=aweme_id)
        param_str = self.model_to_query_string(params)
        url = f"{TikTokAPIEndpoints.HOME_FEED}?{param_str}"

        # 使用 async with 调用 BaseAsyncHttpClient 进行请求 (Use async with to call BaseAsyncHttpClient for the request)
        async with AsyncHttpClient(headers=headers) as client:
            response = await client.fetch_get_json(url)
            video_data = response.get("aweme_list", [{}])[0]

            # 验证获取的视频 ID 是否与请求的 ID 匹配 (Verify if the fetched video ID matches the requested video ID)
            if video_data.get("aweme_id") != aweme_id:
                raise ValueError("Invalid video ID (作品 ID 错误)")

            return video_data

    # 通过URL获取单个作品数据 (Fetch a single TikTok video data by video URL)
    async def fetch_one_video_by_url(self, url: str) -> dict:
        """
        根据视频 URL 获取单个 TikTok 视频数据 (Fetch a single TikTok video data by video URL)

        :param url: 视频 URL | Video URL
        :return: 视频数据 (Video data)
        """
        # 解析 URL 中的视频 ID (Parse video ID from URL)
        headers = self.get_tiktok_headers()
        async with AsyncHttpClient(headers=headers) as client:
            response = await client.fetch_response(url)
            url = response.headers.get("location", url)

            # 预编译正则表达式
            _TIKTOK_AWEMEID_PATTERN = re.compile(r"video/(\d+)")
            _TIKTOK_PHOTOID_PATTERN = re.compile(r"photo/(\d+)")
            _TIKTOK_NOTFOUND_PATTERN = re.compile(r"notfound")

            # 匹配视频 ID (Match video ID)
            video_match = _TIKTOK_AWEMEID_PATTERN.search(str(url))
            photo_match = _TIKTOK_PHOTOID_PATTERN.search(str(url))

            if not video_match and not photo_match:
                raise ValueError("Invalid video URL (视频 URL 错误)")

            aweme_id = video_match.group(1) if video_match else photo_match.group(1)

        # 调用 fetch_one_video 方法获取视频数据 (Call fetch_one_video method to fetch video data)
        return await self.fetch_one_video(aweme_id)

    async def main(self):
        """
        主函数，用于测试获取单个作品数据 (Main function for testing single video data fetch)
        """
        aweme_id = "7339393672959757570"
        response = await self.fetch_one_video(aweme_id)
        print(response)

        awe_url = "https://www.tiktok.com/t/ZTFcVgx4P/"
        response = await self.fetch_one_video_by_url(awe_url)
        print(response)


if __name__ == "__main__":
    # 初始化 TikTokAPPCrawler 实例并运行主函数 (Initialize TikTokAPPCrawler instance and run main function)
    crawler = TikTokAPPCrawler()

    # 计算获取操作的耗时 (Measure time taken for the fetch operation)
    start_time = time.time()
    asyncio.run(crawler.main())
    end_time = time.time()

    print(f"耗时 (Duration): {end_time - start_time:.2f} 秒")

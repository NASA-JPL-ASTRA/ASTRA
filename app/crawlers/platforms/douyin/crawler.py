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
# - https://github.com/Evil0ctal
# - https://github.com/Johnserf-Seed
#
# ==============================================================================

import asyncio
import re
import time
from tenacity import retry, stop_after_attempt, wait_fixed
from urllib.parse import urlencode

from app.crawlers.platforms.douyin.endpoints import DouyinAPIEndpoints
from app.crawlers.platforms.douyin.models import PostDetail
from app.crawlers.platforms.douyin.utils import BogusManager
from app.http_client.AsyncHttpClient import AsyncHttpClient
from config.settings import Settings


class DouyinWebCrawler:

    # 从配置文件中获取抖音的请求头
    async def get_douyin_headers(self):
        Cookie = Settings.DouyinAPISettings.web_cookie
        if not Cookie:
            raise ValueError("请配置抖音的Web端Cookie (Please configure the Douyin Web Cookie)")
        kwargs = {
            "headers": {
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
                "Referer": "https://www.douyin.com/",
                "Cookie": Cookie,
            },
            "proxies": {
                "http://": Settings.DouyinAPISettings.proxy,
                "https://": Settings.DouyinAPISettings.proxy
            },
        }
        return kwargs

    "-------------------------------------------------------handler接口列表-------------------------------------------------------"

    # 获取单个作品数据 (Fetch a single Douyin video data)
    @retry(stop=stop_after_attempt(3), retry_error_callback=lambda retry_state: retry_state.outcome.result())
    async def fetch_one_video(self, aweme_id: str):
        # 获取抖音的实时Cookie
        kwargs = await self.get_douyin_headers()
        # 创建一个基础爬虫
        base_crawler = AsyncHttpClient(proxy_settings=kwargs["proxies"], headers=kwargs["headers"])
        async with base_crawler as crawler:
            # 创建一个作品详情的BaseModel参数
            params = PostDetail(aweme_id=aweme_id)
            # 生成一个作品详情的带有a_bogus加密参数的Endpoint
            params_dict = params.dict()
            a_bogus = BogusManager.ab_model_2_endpoint(params_dict, kwargs["headers"]["User-Agent"])
            endpoint = f"{DouyinAPIEndpoints.POST_DETAIL}?{urlencode(params_dict)}&a_bogus={a_bogus}"

            response = await crawler.fetch_get_json(endpoint)
        return response

    # 通过URL获取单个作品数据 (Fetch a single Douyin video data by video URL)
    async def fetch_one_video_by_url(self, url: str) -> dict:
        """
        根据视频 URL 获取单个 抖音 视频数据 (Fetch a single Douyin video data by video URL)

        :param url: 视频 URL | Video URL
        :return: 视频数据 (Video data)
        """
        # 解析 URL 中的视频 ID (Parse video ID from URL)
        kwargs = await self.get_douyin_headers()
        async with AsyncHttpClient(headers=kwargs['headers']) as client:
            response = await client.fetch_response(url)
            url = response.headers.get("location", url)

            # 预编译正则表达式
            _DOUYIN_VIDEO_URL_PATTERN = re.compile(r"video/([^/?]*)")
            _DOUYIN_NOTE_URL_PATTERN = re.compile(r"note/([^/?]*)")
            _DOUYIN_DISCOVER_URL_PATTERN = re.compile(r"modal_id=([0-9]+)")

            # 匹配视频 ID (Match video ID)
            video_match = _DOUYIN_VIDEO_URL_PATTERN.search(str(url))
            note_match = _DOUYIN_NOTE_URL_PATTERN.search(str(url))
            discover_match = _DOUYIN_DISCOVER_URL_PATTERN.search(str(url))

            if not video_match and not note_match and not discover_match:
                raise ValueError("Invalid video URL (视频 URL 错误)")

            aweme_id = video_match.group(1) if video_match else note_match.group(1) if note_match else discover_match.group(1)

        # 调用 fetch_one_video 方法获取视频数据 (Call fetch_one_video method to fetch video data)
        return await self.fetch_one_video(aweme_id)

    async def main(self):
        """-------------------------------------------------------handler接口列表-------------------------------------------------------"""

        # 获取单一视频信息
        # aweme_id = "7372484719365098803"
        # result = await self.fetch_one_video(aweme_id)
        # print(result)

        # 获取单一视频信息（通过URL）
        url = "https://v.douyin.com/iANRkr9m/"
        result = await self.fetch_one_video_by_url(url)
        print(result)

        # 占位
        pass


if __name__ == "__main__":
    # 初始化
    DouyinWebCrawler = DouyinWebCrawler()

    # 开始时间
    start = time.time()

    asyncio.run(DouyinWebCrawler.main())

    # 结束时间
    end = time.time()
    print(f"耗时：{end - start}")

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

import asyncio
import traceback
import httpx
import json
import re
from typing import Optional, Dict, Any
from httpx import Response
from app.http_client.HttpException import (
    APIConnectionError,
    APIResponseError,
    APITimeoutError,
    APIUnavailableError,
    APIUnauthorizedError,
    APINotFoundError,
    APIRateLimitError,
    APIRetryExhaustedError, APIFileDownloadError,
)
from app.utils.logging_utils import configure_logging

# Initialize logger instance
logger = configure_logging(__name__)


class AsyncHttpClient:
    """
    异步 HTTP 客户端 (Asynchronous HTTP client)
    """

    def __init__(self, proxy_settings: Optional[Dict[str, str]] = None, retry_limit: int = 3,
                 max_connections: int = 50, request_timeout: int = 10, max_concurrent_tasks: int = 50,
                 headers: Optional[Dict[str, str]] = None, base_backoff: float = 1.0, follow_redirects: bool = False):
        """
        初始化 BaseAsyncHttpClient 实例

        Initialize BaseAsyncHttpClient instance

        :param proxy_settings: 可选的代理设置 | Optional proxy settings
        :param retry_limit: 最大重试次数 | Maximum retry limit
        :param max_connections: 最大连接数 | Maximum connection count
        :param request_timeout: 请求超时时间 | Request timeout in seconds
        :param max_concurrent_tasks: 最大并发任务数 | Maximum concurrent task count
        :param headers: 请求头设置 | Request headers
        :param base_backoff: 重试的基础退避时间 | Base backoff time for retries
        :param follow_redirects: 是否跟踪重定向 | Whether to follow redirects
        """
        self.proxy_settings = proxy_settings if isinstance(proxy_settings, dict) else None
        self.headers = headers or {
            "User-Agent": "Fast-Powerful-Whisper-AI-Services-API/HTTP Client (https://github.com/Evil0ctal/Fast-Powerful-Whisper-AI-Services-API)",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.retry_limit = retry_limit
        self.request_timeout = request_timeout
        self.base_backoff = base_backoff

        # 创建独立的 AsyncClient 实例 (Create an independent AsyncClient instance)
        self.aclient = httpx.AsyncClient(
            headers=self.headers,
            proxies=self.proxy_settings,
            timeout=httpx.Timeout(request_timeout),
            limits=httpx.Limits(max_connections=max_connections),
            transport=httpx.AsyncHTTPTransport(retries=retry_limit),
            follow_redirects=follow_redirects
        )

    async def fetch_response(self, url: str, **kwargs) -> Response:
        """
        获取数据 (Get data)

        :param url: 完整的 URL 地址 | Full URL address
        :param kwargs: 请求的附加参数 | Additional parameters for the request
        :return: 原始响应对象 | Raw response object
        """
        return await self.fetch_data('GET', url, **kwargs)

    async def fetch_get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        获取 JSON 数据 (Get JSON data)

        :param url: 完整的 URL 地址 | Full URL address
        :param kwargs: 请求的附加参数 | Additional parameters for the request
        :return: 解析后的 JSON 数据 | Parsed JSON data
        """
        response = await self.fetch_data('GET', url, **kwargs)
        return self.parse_json(response)

    async def fetch_post_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        获取 POST 请求的 JSON 数据 (Post JSON data)

        :param url: 完整的 URL 地址 | Full URL address
        :param kwargs: 请求的附加参数 | Additional parameters for the request
        :return: 解析后的 JSON 数据 | Parsed JSON data
        """
        response = await self.fetch_data('POST', url, **kwargs)
        return self.parse_json(response)

    async def fetch_data(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        通用请求处理方法 (General request handling method)

        :param method: 请求方法 | HTTP method (e.g., 'GET', 'POST')
        :param url: 完整的 URL 地址 | Full URL
        :param kwargs: 传递给请求的额外参数 | Additional parameters for the request
        :return: 响应对象 | Response object
        """
        backoff = self.base_backoff
        for attempt in range(self.retry_limit):
            try:
                # 使用传递的 kwargs 调用 aclient.request 方法 (Pass kwargs to aclient.request)
                response = await self.aclient.request(
                    method=method,
                    url=url,
                    headers=kwargs.pop("headers", self.headers),
                    **kwargs  # Pass other dynamic parameters
                )
                if not response.text.strip() or not response.content:
                    if attempt == self.retry_limit - 1:
                        logger.error(
                            f"Failed after {self.retry_limit} attempts. Status: {response.status_code}, URL: {url}")
                        raise APIRetryExhaustedError()
                    await asyncio.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                    continue
                # response.raise_for_status()
                return response

            except httpx.RequestError as req_err:
                logger.error(f"Request error on {url}: {req_err}", exc_info=True)
                raise APIConnectionError()
            except httpx.HTTPStatusError as http_error:
                self.handle_http_status_error(http_error, url, attempt + 1)

    async def fetch_data_via_head(self, url: str, **kwargs) -> httpx.Response:
        """
        获取 HEAD 请求的数据 (Get data via HEAD request)

        :param url: 完整的 URL 地址 | Full URL address
        :param kwargs: 请求的附加参数 | Additional parameters for the request
        :return: 响应对象 | Response object
        """
        return await self.fetch_data('HEAD', url, **kwargs)

    async def download_file(self, url: str, save_path: str, chunk_size: int = 1024) -> None:
        """
        下载文件到指定路径 (Download file to specified path)

        :param url: 文件的完整 URL 地址 | Full URL of the file
        :param save_path: 文件保存路径 | Path to save the downloaded file
        :param chunk_size: 下载块的大小（字节） | Size of each download chunk in bytes
        """
        async with self.semaphore:
            try:
                self.aclient.headers["Referer"] = url
                async with self.aclient.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(save_path, "wb") as file:
                        async for chunk in response.aiter_bytes(chunk_size):
                            file.write(chunk)
                    logger.info(f"File downloaded successfully: {save_path}")
            except (httpx.RequestError, httpx.HTTPStatusError) as error:
                logger.error(f"Failed to download file from {url}: {error}", exc_info=True)
                raise APIFileDownloadError(f"Failed to download file from {url}")

    @staticmethod
    def handle_http_status_error(http_error, url: str, attempt):
        """
        处理 HTTP 状态错误 (Handle HTTP status error)

        :param http_error: HTTP 状态错误对象 | HTTP status error object
        :param url: 完整的 URL 地址 | Full URL address
        :param attempt: 当前尝试次数 | Current attempt count
        :raises: 基于 HTTP 状态码的特定异常 | Specific exception based on HTTP status code
        """
        response = getattr(http_error, "response", None)
        status_code = getattr(response, "status_code", None)

        if not response or not status_code:
            logger.error(f"Unexpected HTTP error: {http_error}, URL: {url}, Attempt: {attempt}", exc_info=True)
            raise APIResponseError()

        error_mapping = {
            404: APINotFoundError(),
            503: APIUnavailableError(),
            408: APITimeoutError(),
            401: APIUnauthorizedError(),
            429: APIRateLimitError(),
        }

        error = error_mapping.get(status_code, APIResponseError(status_code=status_code))

        logger.error(f"HTTP status error {status_code} on attempt {attempt}, URL: {url}")
        raise error

    @staticmethod
    def parse_json(response: Response) -> Dict[str, Any]:
        """
        解析 JSON 响应对象 (Parse JSON response object)

        :param response: 原始响应对象 | Raw response object
        :return: 解析后的 JSON 数据 | Parsed JSON data
        """
        if len(response.content) == 0:
            logger.error("Empty response content.")
            raise APIResponseError("Empty response content.")

        try:
            return response.json()
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", response.text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from {response.url}: {e}", exc_info=True)
                    raise APIResponseError("Failed to parse JSON data.", status_code=response.status_code)
            else:
                logger.error("No valid JSON structure found in response.")
                raise APIResponseError("No JSON data found.", status_code=response.status_code)

    async def close(self):
        """
        关闭异步客户端 (Close asynchronous client)
        """
        await self.aclient.aclose()

    async def __aenter__(self):
        """
        异步上下文管理器入口 (Async context manager entry)
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        异步上下文管理器出口 (Async context manager exit)
        """
        await self.close()


if __name__ == "__main__":

    async def main():
        """
        演示 BaseAsyncHttpClient 的基本用法，包括 GET、POST 和 HEAD 请求。
        Demonstrates basic usage of BaseAsyncHttpClient, including GET, POST, and HEAD requests.
        """
        async with AsyncHttpClient(
                headers={"User-Agent": "Demo-Client/1.0"},
                request_timeout=5,
                max_connections=10,
                retry_limit=2
        ) as client:
            # 示例 GET 请求 (Example GET request)
            url_get = "https://jsonplaceholder.typicode.com/posts/1"
            try:
                response = await client.fetch_get_json(url_get)
                print(f"GET request success: {response}")
            except APIResponseError as e:
                print(f"GET request failed: {e}")
                print(traceback.format_exc())

            # 示例 POST 请求 (Example POST request)
            url_post = "https://jsonplaceholder.typicode.com/posts"
            data = {"title": "foo", "body": "bar", "userId": 1}
            try:
                response = await client.fetch_post_json(url_post, json=data)
                print(f"POST request success: {response}")
            except APIResponseError as e:
                print(f"POST request failed: {e}")
                print(traceback.format_exc())

            # 示例带自定义头部的 GET 请求 (Example GET request with custom headers)
            custom_headers = {"Authorization": "Bearer your_token_here"}
            try:
                response = await client.fetch_get_json(url_get, headers=custom_headers)
                print(f"GET request with custom headers success: {response}")
            except APIResponseError as e:
                print(f"GET request with custom headers failed: {e}")
                print(traceback.format_exc())


    # 运行异步主函数 (Run the asynchronous main function)
    asyncio.run(main())

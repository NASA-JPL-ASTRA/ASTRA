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

import os
import traceback
import uuid
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from fastapi import Request, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from moviepy.video.io.VideoFileClip import VideoFileClip
from pydub import AudioSegment

from app.model_pool.AsyncModelPool import AsyncModelPool
from app.database.DatabaseManager import DatabaseManager
from app.database.models.TaskModels import Task
from app.processors.task_processor import TaskProcessor
from app.utils.file_utils import FileUtils
from app.utils.logging_utils import configure_logging
from config.settings import Settings

# 初始化静态线程池，所有实例共享 | Initialize static thread pool, shared by all instances
_executor = ThreadPoolExecutor()


class WhisperService:
    """
    Whisper 服务类，用于处理音频和视频的转录和音频提取。

    Whisper service class for handling transcription and audio extraction of audio and video files.
    """

    def __init__(self,
                 model_pool: AsyncModelPool,
                 db_manager: DatabaseManager,
                 max_concurrent_tasks: int,
                 task_status_check_interval: int
                 ) -> None:

        # 配置日志记录器 | Configure logger
        self.logger = configure_logging(name=__name__)

        # 模型池 | Model pool
        self.model_pool = model_pool

        # 数据库管理器 | Database manager
        self.db_manager = db_manager

        # 最大并发任务数 | Maximum concurrent tasks
        self.max_concurrent_tasks = self.get_optimal_max_concurrent_tasks(max_concurrent_tasks)

        # 任务状态检查间隔 | Task status check interval
        self.task_status_check_interval = task_status_check_interval

        # 初始化 FileUtils 实例 | Initialize FileUtils instance
        self.file_utils = FileUtils(
            auto_delete=Settings.FileSettings.auto_delete,
            limit_file_size=Settings.FileSettings.limit_file_size,
            max_file_size=Settings.FileSettings.max_file_size,
            temp_dir=Settings.FileSettings.temp_files_dir
        )

        # 初始化任务处理器 | Initialize task processor
        self.task_processor = TaskProcessor(
            model_pool=self.model_pool,
            file_utils=self.file_utils,
            database_type=self.db_manager.database_type,
            database_url=self.db_manager.database_url,
            max_concurrent_tasks=self.max_concurrent_tasks,
            task_status_check_interval=self.task_status_check_interval
        )

    def start_task_processor(self) -> None:
        """
        启动任务处理器

        Start the task processor

        :return: None
        """
        self.task_processor.start()

    def stop_task_processor(self):
        """
        停止任务处理器

        Stop the task processor

        :return: None
        """
        self.task_processor.stop()

    def get_optimal_max_concurrent_tasks(self, max_concurrent_tasks: int) -> int:
        """
        根据模型池可用实例数量返回最优的 max_concurrent_tasks。
        Returns the optimal max_concurrent_tasks based on the number of available model pool instances.
        """
        # 检查用户输入是否为有效的正整数 | Validate user input
        if max_concurrent_tasks < 1:
            self.logger.warning("Invalid `max_concurrent_tasks` provided. Setting to 1 to avoid issues.")
            max_concurrent_tasks = 1

        pool_size = self.model_pool.pool.maxsize
        if max_concurrent_tasks > pool_size:
            self.logger.warning(
                f"""
                Detected `MAX_CONCURRENT_TASKS` had been set to {max_concurrent_tasks}, but the model pool size is only {pool_size}.
                Optimal MWhisper Service `max_concurrent_tasks` attribute from user input: {max_concurrent_tasks} -> {pool_size}.
                """)
            return pool_size

        return max_concurrent_tasks

    async def extract_audio_from_video(
            self,
            file: UploadFile,
            sample_rate: int,
            bit_depth: int,
            output_format: str,
            background_tasks: BackgroundTasks
    ) -> FileResponse:
        """
        从视频文件中提取音频。

        Extract audio from a video file.

        :param file: FastAPI 上传的视频文件对象 | FastAPI uploaded video file object
        :param sample_rate: 采样率 | Sample rate
        :param bit_depth: 位深度 | Bit depth
        :param output_format: 输出格式，可选 'wav' 或 'mp3' | Output format, 'wav' or 'mp3'
        :param background_tasks: FastAPI 后台任务对象 | FastAPI background tasks object
        :return: 提取的音频 FastAPI 文件响应对象 | Extracted audio FastAPI file response object
        """
        self.logger.debug(f"Starting audio extraction from video file: {file.filename}")

        if not file.content_type.startswith("video/"):
            error_message = f"Invalid upload file type for audio extraction: {file.content_type}"
            self.logger.error(error_message)
            self.logger.error(traceback.format_exc())
            raise ValueError(error_message)

        temp_video_path = await self.file_utils.save_uploaded_file(file=file, file_name=file.filename)
        self.logger.info(f"Video file saved to temporary path: {temp_video_path}")
        temp_files_to_delete = [temp_video_path]

        try:
            video_clip = VideoFileClip(temp_video_path)

            temp_audio_file_name = f"{uuid.uuid4().hex}.{output_format}"
            temp_audio_path = os.path.join(self.file_utils.TEMP_DIR, temp_audio_file_name)
            wav_temp_file_name = f"{uuid.uuid4().hex}.wav"
            wav_temp_path = os.path.join(self.file_utils.TEMP_DIR, wav_temp_file_name)
            temp_files_to_delete.append(wav_temp_path)

            self.logger.info(f"Extracting audio to WAV file: {wav_temp_path}")
            video_clip.audio.write_audiofile(wav_temp_path, fps=sample_rate, nbytes=bit_depth)
            self.logger.info(f"Audio extracted to WAV file: {wav_temp_path}")

            video_clip.close()

            if output_format == "wav":
                temp_audio_path = wav_temp_path
                self.logger.info("Output format is WAV; using extracted WAV file directly.")
            elif output_format == "mp3":
                self.logger.info(f"Converting WAV to MP3: {temp_audio_path}")
                audio = AudioSegment.from_wav(wav_temp_path)
                audio.export(temp_audio_path, format="mp3")
                self.logger.debug(f"Audio converted to MP3: {temp_audio_path}")
                temp_files_to_delete.append(temp_audio_path)
            else:
                error_message = f"Unsupported audio output format: {output_format}"
                self.logger.error(error_message)
                raise ValueError(error_message)

            # 将文件删除任务添加到后台任务中确保文件在返回响应后被删除
            # Add file deletion tasks to background tasks to ensure files are deleted after response is returned
            if Settings.FileSettings.auto_delete and temp_files_to_delete:
                for temp_file in temp_files_to_delete:
                    background_tasks.add_task(self.file_utils.delete_file, temp_file)
                    self.logger.debug(f"Added file to delete in background task: {temp_file}")

            # 返回提取的音频文件 | Return extracted audio file
            self.logger.info(f"Returning extracted audio file: {temp_audio_path}")
            return FileResponse(
                temp_audio_path,
                media_type=f"audio/{output_format}",
                filename=f"extracted_audio.{output_format}",
            )
        except Exception as e:
            self.logger.error(f"Audio extraction failed: {str(e)}")
            self.logger.error(traceback.format_exc())
        finally:
            if 'video_clip' in locals():
                video_clip.close()
                self.logger.info("Video clip closed.")

    async def create_whisper_task(
            self,
            file_upload: Optional[UploadFile],
            file_name: Optional[str],
            file_url: Optional[str],
            callback_url: Optional[str],
            platform: Optional[str],
            decode_options: dict,
            task_type: str,
            priority: str,
            request: Request
    ) -> Task:
        """
        创建一个 Whisper 任务然后保存到数据库。

        Create a Whisper task and save it to the database.

        :param file_upload: FastAPI 上传的文件对象 | FastAPI uploaded file object
        :param file_name: 文件名称 | File name
        :param file_url: 文件 URL | File URL
        :param callback_url: 回调 URL | Callback URL
        :param platform: 平台名称 | Platform name
        :param decode_options: Whisper 解码选项 | Whisper decode options
        :param task_type: Whisper 任务类型 | Whisper task type
        :param priority: 任务优先级 | Task priority
        :param request: FastAPI 请求对象 | FastAPI request object
        :return: 保存到数据库的任务对象 | Task object saved to the database
        """

        # 如果file是UploadFile对象或者bytes对象，那么就保存到临时文件夹，然后返回临时文件路径
        # If file is an UploadFile object or bytes object, save it to the temporary folder and return the temporary file path
        if file_upload:
            temp_file_path = await self.file_utils.save_uploaded_file(file=file_upload, file_name=file_name)
            self.logger.debug(f"Saved uploaded file to temporary path: {temp_file_path}")
            duration = await self.file_utils.get_audio_duration(temp_file_path)
            file_size_bytes = os.path.getsize(temp_file_path)
        else:
            temp_file_path = None
            duration = None
            file_size_bytes = None

        async with self.db_manager.get_session() as session:
            task = Task(
                engine_name=self.model_pool.engine,
                callback_url=callback_url,
                task_type=task_type,
                file_path=temp_file_path,
                file_url=file_url,
                file_name=file_name,
                file_size_bytes=file_size_bytes,
                platform=platform,
                decode_options=decode_options,
                file_duration=duration,
                priority=priority
            )
            session.add(task)
            await session.commit()
            task_id = task.id
            # 设置任务输出链接 | Set task output URL
            try:
                task.output_url = f"{request.url_for('task_result')}?task_id={task_id}"
            except Exception:
                base = str(request.base_url).rstrip("/")
                task.output_url = f"{base}/api/whisper/tasks/result?task_id={task_id}"
            await session.commit()

        self.logger.info(f"Created transcription task with ID: {task_id}")
        return task

    async def generate_subtitle(self,
                                task: Task,
                                output_format: str,
                                background_tasks: BackgroundTasks
                                ) -> FileResponse:
        """
        生成字幕文件并返回文件路径。

        Generates a subtitle file and returns the file path.

        :param task: 要生成字幕的任务实例 | Task instance to generate subtitles for
        :param output_format: 输出格式，可选 'srt' 或 'vtt' | Output format, 'srt' or 'vtt'
        :param background_tasks: FastAPI 后台任务对象 | FastAPI background tasks object
        :return: 字幕文件路径 | Subtitle file path
        """
        subtitle_file_path = None
        try:
            # 生成字幕内容 | Generate subtitle content
            separator = "," if output_format == "srt" else "."
            subtitle_content = "WEBVTT\n\n" if output_format == "vtt" else ""
            subtitle_content += "\n".join(
                f"{segment['id']}\n{self.format_time(segment['start'], separator)} --> {self.format_time(segment['end'], separator)}\n{segment['text']}\n"
                for segment in task.result["segments"]
            )
            # 保存字幕文件 | Save subtitle file
            subtitle_file_path = await self.file_utils.save_file(
                file=subtitle_content.encode("utf-8"),
                file_name=f"Task_{task.id}_Subtitle.{output_format}",
                check_file_allowed=False
            )

            # 将文件删除任务添加到后台任务中确保文件在返回响应后被删除
            # Add file deletion tasks to background tasks to ensure files are deleted after response is returned
            if Settings.FileSettings.auto_delete and subtitle_file_path:
                background_tasks.add_task(self.file_utils.delete_file, subtitle_file_path)
                self.logger.debug(f"Added subtitle file to delete in background task: {subtitle_file_path}")

            # 返回字幕文件 | Return subtitle file
            self.logger.info(f"Returning subtitle file for Task ID {task.id}: {subtitle_file_path}")
            return FileResponse(
                subtitle_file_path,
                media_type="text/vtt" if output_format == "vtt" else "text/srt",
                filename=os.path.basename(subtitle_file_path)
            )
        except Exception as e:
            self.logger.error(f"Failed to generate subtitle file for Task ID {task.id}: {e}")
            self.logger.error(traceback.format_exc())
            raise RuntimeError("Failed to generate subtitle") from e

    @staticmethod
    def format_time(seconds: float, separator: str) -> str:
        """
        将秒数格式化为 SRT 字幕时间格式。

        Formats seconds as SRT subtitle time format.

        :param seconds: 要格式化的秒数 | Seconds to format
        :param separator: 分隔符 | Separator
        :return: 格式化后的时间字符串 | Formatted time string
        """
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}{separator}{milliseconds:03}"

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

import logging
import logging.handlers
import os
import sys
from typing import Optional

try:
    from concurrent_log_handler import ConcurrentRotatingFileHandler as RotatingFileHandler
except ImportError:
    RotatingFileHandler = logging.handlers.RotatingFileHandler  # type: ignore
from config.settings import Settings


def configure_logging(
    name: Optional[str] = None,
    log_level: int = Settings.LogSettings.level,
    log_dir: Optional[str] = Settings.LogSettings.log_dir,
    log_file_prefix: Optional[str] = Settings.LogSettings.log_file_prefix,
    backup_count: int = Settings.LogSettings.backup_count,
    encoding: str = Settings.LogSettings.encoding
) -> logging.Logger:
    """
    一个日志记录器，支持日志轮转和控制台输出，使用 ConcurrentRotatingFileHandler 处理器。

    A logger that supports log rotation and console output, using the ConcurrentRotatingFileHandler handler.

    :param name: 日志记录器的名称，默认为 None，使用根记录器。 | The name of the logger, default is None, using the root logger.
    :param log_level: 日志级别，默认为 logging.DEBUG。 | The log level, default is logging.DEBUG.
    :param log_dir: 日志文件目录，默认为 './log_files'。 | The log file directory, default is './log_files'.
    :param log_file_prefix: 日志文件前缀，默认为 'app'。 | The log file prefix, default is 'app'.
    :param backup_count: 保留的备份文件数量，默认为 7。 | The number of backup files to keep, default is 7.
    :param encoding: 日志文件编码，默认为 'utf-8'。 | The log file encoding, default is 'utf-8'.
    :return: 配置好的日志记录器。 | The configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # 防止重复添加处理器 | Prevent duplicate handlers
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 创建日志目录 | Create log directory
        if log_dir:
            log_dir = os.path.abspath(log_dir)
            os.makedirs(log_dir, exist_ok=True)

        # 配置并发日志轮转处理器 | Configure concurrent log rotation handler
        if log_file_prefix:
            log_file_name = f"{log_file_prefix}.log"
            log_file_path = os.path.join(log_dir, log_file_name)
            rotating_file_handler = RotatingFileHandler(
                filename=log_file_path,
                # 设置最大文件大小为 10 MB | Set max file size to 10 MB
                maxBytes=10*1024*1024,
                backupCount=backup_count,
                encoding=encoding,
            )
            rotating_file_handler.setFormatter(formatter)
            logger.addHandler(rotating_file_handler)

        # 配置控制台处理器 | Configure console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger



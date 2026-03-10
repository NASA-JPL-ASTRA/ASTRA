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
import datetime
import json
import traceback
from typing import Optional, List, Dict, Union
from sqlalchemy import select, and_, func, case, inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.sql import func
from contextlib import asynccontextmanager
from app.database.models.TaskModels import TaskBase, Task, QueryTasksOptionalFilter, TaskStatus, TaskPriority
from app.database.models.WorkFlowModels import WorkFlowBase, Workflow, WorkflowTask, WorkflowNotification
from app.database.models.CrawlerModels import CrawlerTask
from app.database.models.ChatGPTModels import ChatGPTTask
from app.utils.logging_utils import configure_logging

# 配置日志记录器 | Configure logger
logger = configure_logging(name=__name__)


class DatabaseManager:
    """
    通用数据库管理器，支持MySQL和SQLite数据库，并提供任务的增删查改操作和扩展的功能。

    Generic database manager supporting both MySQL and SQLite databases, with CRUD operations for tasks
    and additional extended functionality.
    """

    def __init__(self,
                 database_type: str,
                 database_url: str,
                 loop: Optional[asyncio.AbstractEventLoop] = None,
                 reconnect_interval: int = 5
                 ) -> None:
        """
        初始化数据库管理器并根据数据库类型动态绑定相应的数据库引擎和会话。

        Initializes the database manager with dynamic binding based on database type.

        :param database_type: 数据库类型 ("sqlite" 或 "mysql") | Database type ("sqlite" or "mysql")
        :param database_url: 数据库 URL | Database URL
        :param loop: 异步事件循环（可选）| Event loop (optional)
        :param reconnect_interval: 重连间隔（秒）| Reconnect interval (seconds)
        """
        self.database_type: str = database_type.lower()
        self.database_url: str = database_url
        self.loop: asyncio.AbstractEventLoop = loop or asyncio.get_running_loop()
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self.reconnect_interval: int = reconnect_interval
        self._is_connected: bool = False
        self._max_retries: int = 5

    async def initialize(self) -> None:
        """
        初始化数据库引擎和会话工厂，并根据数据库类型配置引擎。自动创建缺失的表。

        Initialize the database engine and session factory, configure engine based on database type,
        and automatically create any missing tables.
        """
        await self._connect()

    async def _connect(self) -> None:
        """
        尝试连接数据库，自动重试并根据数据库类型初始化引擎和会话工厂。

        Attempt to connect to the database with automatic retry and initialize engine and session factory based on database type.
        """
        retry_count = 0
        while not self._is_connected:
            try:
                if self.database_type == "mysql":
                    self._engine = create_async_engine(
                        self.database_url,
                        echo=False,
                        pool_pre_ping=True,
                        pool_size=5,
                        max_overflow=10,
                        pool_timeout=30,
                        future=True
                    )
                elif self.database_type == "sqlite":
                    self._engine = create_async_engine(
                        self.database_url,
                        echo=False,
                        future=True
                    )
                self._session_factory = sessionmaker(
                    bind=self._engine,
                    expire_on_commit=False,
                    class_=AsyncSession
                )

                async with self._engine.begin() as conn:
                    # 使用 conn.run_sync 调用 inspect 确认表是否存在
                    def sync_inspect(connection):
                        inspector = inspect(connection)
                        return inspector.get_table_names()

                    existing_tables = await conn.run_sync(sync_inspect)

                    # 检查是否存在表，如果不存在则创建 | Check if tables exist, if not create
                    if 'tasks' not in existing_tables:
                        await conn.run_sync(TaskBase.metadata.create_all)
                    if 'workflow_workflows' not in existing_tables:
                        await conn.run_sync(WorkFlowBase.metadata.create_all)
                    if 'crawler_tasks' not in existing_tables:
                        await conn.run_sync(CrawlerTask.metadata.create_all)
                    if 'chatgpt_tasks' not in existing_tables:
                        await conn.run_sync(ChatGPTTask.metadata.create_all)

                self._is_connected = True
                logger.info(f"{self.database_type.upper()} database connected and tables initialized successfully.")
            except OperationalError as e:
                retry_count += 1
                if retry_count >= self._max_retries:
                    logger.error(f"Failed to connect to database after {retry_count} attempts: {e}")
                    raise
                logger.error(
                    f"Database connection failed: {e}. Retrying in {self.reconnect_interval} seconds... (Attempt {retry_count}/{self._max_retries})")
                await asyncio.sleep(self.reconnect_interval)
            except Exception as e:
                logger.error(f"Unexpected error during database connection: {e}")
                logger.error(traceback.format_exc())
                raise

    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        """
        获取数据库会话生成器

        Get a database session generator.

        :return: 数据库会话 | Database session
        """
        if not self._is_connected:
            await self._connect()
        async with self._session_factory() as session:
            try:
                yield session
            except OperationalError as e:
                logger.error(f"Operational error in session: {e}. Reconnecting to database.")
                self._is_connected = False
                await self._connect()
                yield session  # Re-yield after reconnecting
            except SQLAlchemyError as e:
                logger.error(f"SQLAlchemy error in session: {e}")
                await session.rollback()
                raise

    async def add_task(self, task: Task) -> None:
        """
        异步添加新任务

        Asynchronously add a new task.

        :param task: Task 对象 | Task object
        :return: None
        """
        async with self.get_session() as session:
            try:
                session.add(task)
                await session.commit()
            except OperationalError:
                self._is_connected = False
                logger.error("Connection lost while adding task. Attempting to reconnect.")
                await self.add_task(task)
            except SQLAlchemyError as e:
                logger.error(f"Error adding task: {e}")
                logger.error(traceback.format_exc())
                await session.rollback()
                raise

    async def get_task(self, task_id: int) -> Optional[Task]:
        """
        根据ID异步获取任务

        Asynchronously get a task by ID.

        :param task_id: 任务ID | Task ID
        :return: 任务信息 | Task details
        """
        async with self.get_session() as session:
            try:
                task = await session.get(Task, task_id)
                return task if task else None
            except SQLAlchemyError as e:
                logger.error(f"Error fetching task by ID {task_id}: {e}")
                logger.error(traceback.format_exc())
                return None

    async def get_queued_tasks(self, max_concurrent_tasks: int) -> List[Task]:
        """
        异步获取队列中的任务

        Asynchronously get tasks from the queue.

        :return: 任务信息 | Task details
        """
        async with self.get_session() as session:
            try:
                result = await session.execute(
                    select(Task)
                    .where(Task.status == TaskStatus.queued)
                    .order_by(
                        case(
                            (Task.priority == TaskPriority.high, 1),
                            (Task.priority == TaskPriority.normal, 2),
                            (Task.priority == TaskPriority.low, 3),
                        )
                    )
                    .limit(max_concurrent_tasks)
                )
                return result.scalars().all()
            except OperationalError:
                self._is_connected = False
                logger.error("Connection lost while fetching queued tasks. Attempting to reconnect.")
                return await self.get_queued_tasks(max_concurrent_tasks)
            except SQLAlchemyError as e:
                logger.error(f"Error fetching queued tasks: {e}")
                logger.error(traceback.format_exc())
                raise

    async def update_task(self, task_id: int, **kwargs) -> Optional[dict]:
        """
        异步更新任务信息

        Asynchronously update task details.

        :param task_id: 任务ID | Task ID
        :param kwargs: 需要更新的字段 | Fields to update
        :return: 更新后的任务信息 | Updated task details
        """
        async with self.get_session() as session:
            try:
                task = await session.get(Task, task_id)
                if not task:
                    return None
                for key, value in kwargs.items():
                    setattr(task, key, value)
                await session.commit()
                return task.to_dict()
            except SQLAlchemyError as e:
                logger.error(f"Error updating task ID {task_id}: {e}")
                logger.error(traceback.format_exc())
                await session.rollback()
                return None

    async def delete_task(self, task_id: int) -> bool:
        """
        根据ID异步删除任务

        Asynchronously delete a task by ID.

        :param task_id: 任务ID | Task ID
        :return: 是否删除成功 | Whether deletion was successful
        """
        async with self.get_session() as session:
            try:
                task = await session.get(Task, task_id)
                if task:
                    await session.delete(task)
                    await session.commit()
                    return True
                return False
            except SQLAlchemyError as e:
                logger.error(f"Error deleting task ID {task_id}: {e}")
                logger.error(traceback.format_exc())
                await session.rollback()
                return False

    async def bulk_update_tasks(self, task_ids: List[int], update_data: Dict[str, any]) -> None:
        """
        批量更新多个任务

        Bulk update multiple tasks.

        :param task_ids: 任务ID列表 | List of task IDs
        :param update_data: 更新数据字典 | Dictionary of data to update
        """
        async with self.get_session() as session:
            try:
                for task_id in task_ids:
                    task = await session.get(Task, task_id)
                    if task:
                        for key, value in update_data.items():
                            setattr(task, key, value)
                    await session.commit()
                logger.info(f"Bulk update completed for {len(task_ids)} tasks.")
            except SQLAlchemyError as e:
                logger.error(f"Error during bulk update: {e}")
                logger.error(traceback.format_exc())
                await session.rollback()

    async def bulk_delete_tasks(self, task_ids: List[int]) -> None:
        """
        批量删除多个任务

        Bulk delete multiple tasks.

        :param task_ids: 要删除的任务ID列表 | List of task IDs to delete
        """
        async with self.get_session() as session:
            try:
                for task_id in task_ids:
                    task = await session.get(Task, task_id)
                    if task:
                        await session.delete(task)
                await session.commit()
                logger.info(f"Bulk delete completed for {len(task_ids)} tasks.")
            except SQLAlchemyError as e:
                logger.error(f"Error during bulk delete: {e}")
                logger.error(traceback.format_exc())
                await session.rollback()

    async def query_tasks(self, filters: QueryTasksOptionalFilter) -> Optional[Dict[str, List[Dict]]]:
        """
        根据过滤条件查询任务，使用分页和条件查询。

        Query tasks based on filters with pagination.

        :param filters: QueryTasksOptionalFilter 对象 | QueryTasksOptionalFilter object
        :return: 查询结果 | Query result
        """
        async with self.get_session() as session:
            try:
                conditions = self._build_query_conditions(filters)
                query = (
                    select(Task)
                    .where(and_(*conditions))
                    .order_by(Task.created_at)
                    .offset(filters.offset)
                    .limit(filters.limit)
                )
                result = await session.execute(query)
                tasks = result.scalars().all()

                # 获取总记录数 | Get total count
                count_query = select(func.count()).select_from(Task).where(and_(*conditions))
                total_count = (await session.execute(count_query)).scalar()

                has_more = filters.offset + filters.limit < total_count
                next_offset = filters.offset + filters.limit if has_more else None

                return {
                    "tasks": [task.to_dict() for task in tasks],
                    "total_count": total_count,
                    "has_more": has_more,
                    "next_offset": next_offset
                }
            except SQLAlchemyError as e:
                logger.error(f"Error querying tasks: {e}")
                logger.error(traceback.format_exc())
                raise

    async def update_task_callback_status(self, task_id: int,
                                          callback_status_code: int,
                                          callback_message: Optional[str],
                                          callback_time: Union[str, datetime.datetime]
                                          ) -> None:
        """
        更新任务的回调状态码、回调消息和回调时间

        Update the task's callback status code, callback message, and callback time

        :param task_id: 任务ID | Task ID
        :param callback_status_code: 回调状态码 | Callback status code
        :param callback_message: 回调消息 | Callback message
        :param callback_time: 回调时间 | Callback time
        :return: None
        """
        async with self.get_session() as session:
            try:
                task = await session.get(Task, task_id)
                if task:
                    task.callback_status_code = callback_status_code
                    task.callback_message = callback_message[:512] if callback_message else None
                    task.callback_time = callback_time
                    await session.commit()
            except SQLAlchemyError as e:
                logger.error(f"Error updating task callback status: {e}")
                logger.error(traceback.format_exc())
                await session.rollback()

    def _build_query_conditions(self, filters: QueryTasksOptionalFilter) -> List:
        """
        根据 QueryTasksOptionalFilter 对象构建查询条件。

        Build query conditions based on QueryTasksOptionalFilter.

        :param filters: QueryTasksOptionalFilter 对象 | QueryTasksOptionalFilter object
        :return: 查询条件列表 | List of query conditions
        """
        conditions = []
        if filters.status:
            conditions.append(Task.status == filters.status)
        if filters.priority:
            conditions.append(Task.priority == filters.priority)
        if filters.created_after:
            conditions.append(Task.created_at >= filters.created_after)
        if filters.created_before:
            conditions.append(Task.created_at <= filters.created_before)
        if filters.language:
            conditions.append(Task.language == filters.language)
        if filters.engine_name:
            conditions.append(Task.engine_name == filters.engine_name)
        if filters.has_result is not None:
            conditions.append(Task.result.isnot(None) if filters.has_result else Task.result.is_(None))
        if filters.has_error is not None:
            conditions.append(Task.error_message.isnot(None) if filters.has_error else Task.error_message.is_(None))
        return conditions

    async def create_workflow(self, workflow_data: dict) -> int:
        """
        创建一个新的工作流记录并保存到数据库中
        Create a new workflow record and save it in the database.

        :param workflow_data: 工作流数据字典 | Workflow data dictionary
        :return: 创建的工作流ID | Created workflow ID
        """
        async with self.get_session() as session:
            try:
                # 创建 Workflow 实例并映射字段
                workflow = Workflow(
                    name=workflow_data["WORKFLOW_NAME"],
                    description=workflow_data.get("DESCRIPTION", ""),
                    trigger_type=workflow_data["TRIGGER_TYPE"],
                    callback_url=workflow_data.get("CALLBACK_URL"),
                )

                # 添加到会话并提交
                session.add(workflow)
                await session.commit()
                await session.refresh(workflow)  # 刷新获取 ID

                # 添加通知（如果有）
                if "NOTIFY_ON_COMPLETION" in workflow_data:
                    notify_data = workflow_data["NOTIFY_ON_COMPLETION"]
                    notification = WorkflowNotification(
                        workflow_id=workflow.id,
                        channel=notify_data["channel"],
                        recipient=notify_data["recipient"],
                        message=notify_data["message"]
                    )
                    session.add(notification)

                # 处理任务列表
                for task_data in workflow_data["tasks"]:
                    task = WorkflowTask(
                        workflow_id=workflow.id,
                        task_id=task_data["TASK_ID"],
                        component=task_data["COMPONENT"],
                        parameters=task_data.get("PARAMETERS"),
                        retry_policy=task_data.get("RETRY_POLICY"),
                        timeout=task_data.get("TIMEOUT"),
                        condition=task_data.get("CONDITION"),
                        delay=task_data.get("DELAY")
                    )
                    session.add(task)
                await session.commit()

                return workflow.id

            except SQLAlchemyError as e:
                logger.error(f"Error creating workflow: {e}")
                logger.error(traceback.format_exc())
                await session.rollback()
                raise

    async def save_crawler_task(self, task_id: int, url: str, data: dict) -> None:
        """
        保存爬虫任务的数据到数据库中

        Save crawler task data to the database.

        :param task_id: 任务ID | Task ID
        :param url: 任务的 URL | Task URL
        :param data: 爬虫任务数据 | Crawler task data
        :return: None
        """
        async with self.get_session() as session:
            try:
                crawler_task = CrawlerTask(
                    task_id=task_id,
                    url=url,
                    data=json.dumps(data, ensure_ascii=False)
                )
                session.add(crawler_task)
                await session.commit()
            except SQLAlchemyError as e:
                logger.error(f"Error saving crawler task data: {e}")
                logger.error(traceback.format_exc())
                await session.rollback()
                raise

    async def save_chatgpt_task(self, task_id: int, chatgpt_data: dict) -> None:
        """
        保存 ChatGPT 任务的数据到数据库中

        Save ChatGPT task data to the database.

        :param task_id: 任务ID | Task ID
        :param chatgpt_data: ChatGPT 任务数据 | ChatGPT task data
        :return: None
        """
        async with self.get_session() as session:
            try:
                chatgpt_task = ChatGPTTask(
                    task_id=task_id,
                    data=json.dumps(chatgpt_data, ensure_ascii=False)
                )
                session.add(chatgpt_task)
                await session.commit()
            except SQLAlchemyError as e:
                logger.error(f"Error saving ChatGPT task data: {e}")
                logger.error(traceback.format_exc())
                await session.rollback()
                raise



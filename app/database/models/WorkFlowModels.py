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

from sqlalchemy import Column, Integer, String, Text, JSON, Enum, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

# Define Base class
WorkFlowBase = declarative_base()


# Workflow model
class Workflow(WorkFlowBase):
    __tablename__ = "workflow_workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(Enum("MANUAL", "SCHEDULED", "EVENT", name="workflow_trigger_types"), nullable=False)
    callback_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tasks = relationship("WorkflowTask", back_populates="workflow", cascade="all, delete-orphan")
    notifications = relationship("WorkflowNotification", back_populates="workflow", cascade="all, delete-orphan")


# WorkflowTask model for specific workflow tasks
class WorkflowTask(WorkFlowBase):
    __tablename__ = "workflow_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflow_workflows.id", ondelete="CASCADE"))
    component = Column(String(255), nullable=False)
    parameters = Column(JSON, nullable=True)
    retry_policy = Column(JSON, nullable=True)  # e.g., {"max_retries": 3, "interval": 5}
    timeout = Column(Integer, nullable=True)  # seconds
    delay = Column(Integer, nullable=True)  # seconds
    condition = Column(JSON, nullable=True)  # e.g., {"@IF": {...}, "@THEN": "task_b"}
    status = Column(Enum("PENDING", "RUNNING", "SUCCESS", "FAILED", name="workflow_task_statuses"), nullable=False,
                    server_default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    on_failure = Column(Text, nullable=True)

    # Relationship with Workflow
    workflow = relationship("Workflow", back_populates="tasks")


# WorkflowNotification model for workflow notifications
class WorkflowNotification(WorkFlowBase):
    __tablename__ = "workflow_notifications"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflow_workflows.id", ondelete="CASCADE"))
    channel = Column(String(50), nullable=False)  # Specify length for consistency
    recipient = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)  # Changed to Text for potentially longer messages

    # Relationship with Workflow
    workflow = relationship("Workflow", back_populates="notifications")

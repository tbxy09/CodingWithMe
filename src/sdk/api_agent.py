import os
import pathlib
from io import BytesIO
from uuid import uuid4

import uvicorn
from fastapi import APIRouter, FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from sdk.api_db import AgentDB
from sdk.api_schema import *

import logging
LOG = logging.getLogger(__name__)


class NotFoundError(Exception):
    pass


class ServerAgent:
    def __init__(self, database: AgentDB):
        self.db = database

    def setup_agent(self, llm_task_handler, llm_step_handler, artifact_handler):
        self.llm_task_handler = llm_task_handler
        self.llm_step_handler = llm_step_handler
        self.artifact_handler = artifact_handler

    async def create_task(self, task_request: TaskRequestBody) -> Task:
        """
        Create a task for the agent.
        """
        try:
            task = await self.db.create_task(
                input=task_request.input,
                additional_input=task_request.additional_input,
            )
            response = self.llm_task_handler(task_request.input)
            quit()
            if response["artifact"]:
                await self.create_artifact(task_id=task.id)
            return task
        except Exception as e:
            raise

    async def list_tasks(self, page: int = 1, pageSize: int = 10) -> TaskListResponse:
        """
        List all tasks that the agent has created.
        """
        try:
            tasks, pagination = await self.db.list_tasks(page, pageSize)
            response = TaskListResponse(tasks=tasks, pagination=pagination)
            return response
        except Exception as e:
            raise

    async def get_task(self, task_id: str) -> Task:
        """
        Get a task by ID.
        """
        try:
            task = await self.db.get_task(task_id)
        except Exception as e:
            raise
        return task

    async def list_steps(
        self, task_id: str, page: int = 1, pageSize: int = 10
    ) -> TaskStepsListResponse:
        """
        List the IDs of all steps that the task has created.
        """
        try:
            steps, pagination = await self.db.list_steps(task_id, page, pageSize)
            response = TaskStepsListResponse(
                steps=steps, pagination=pagination)
            return response
        except Exception as e:
            raise

    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        """
        Execute a step for the task.
        """
        try:
            step = await self.db.create_step(
                task_id=task_id,
                name=step_request.name,
                input=step_request.input,
                additional_properties=step_request.additional_properties,
                is_last=step_request.is_last,
            )
            self.llm_step_handler(step_request.input, self.db)
            return step
        except Exception as e:
            raise

    async def get_step(self, task_id: str, step_id: str) -> Step:
        """
        Get a step by ID.
        """
        try:
            step = await self.db.get_step(task_id, step_id)
            return step
        except Exception as e:
            raise

    async def list_artifacts(
        self, task_id: str, page: int = 1, pageSize: int = 10
    ) -> TaskArtifactsListResponse:
        """
        List the artifacts that the task has created.
        """
        try:
            artifacts, pagination = await self.db.list_artifacts(
                task_id, page, pageSize
            )
            return TaskArtifactsListResponse(artifacts=artifacts, pagination=pagination)

        except Exception as e:
            raise
    # create artifact to retrieve the project plugins of llm

    async def create_artifact(
        self, task_id: str
    ) -> Artifact:
        """
        Create an artifact for the task.
        """
        try:

            artifact = await self.db.create_artifact(
                task_id=task_id,
                file_name=self.artifact_handler.get_file_name(),
                relative_path=self.artifact_handler.get_relative_path(),
                agent_created=False,
            )
        except Exception as e:
            raise
        return artifact

    async def get_artifact(self, task_id: str, artifact_id: str) -> Artifact:
        """
        Get an artifact by ID.
        """
        try:
            artifact = await self.db.get_artifact(artifact_id)
            if artifact.file_name not in artifact.relative_path:
                file_path = os.path.join(
                    artifact.relative_path, artifact.file_name)
            else:
                file_path = artifact.relative_path
            retrieved_artifact = self.workspace.read(
                task_id=task_id, path=file_path)
        except NotFoundError as e:
            raise
        except FileNotFoundError as e:
            raise
        except Exception as e:
            raise

        return StreamingResponse(
            BytesIO(retrieved_artifact),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={artifact.file_name}"
            },
        )

import orjson
from dataclasses import asdict
from io import BytesIO
from typing import Generator, List, Optional, cast

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from agno.agent import Agent as agnoAgent
from smolagents import CodeAgent as smolAgent
from crewai import Agent as crewaiAgent

from hibiscus import settings

def get_router(
    agent: Optional[Union[agnoAgent, smolAgent, crewaiAgent]] = None, workflows: Optional[List[Workflow]] = None
) -> APIRouter:
    router = APIRouter(prefix="/pebbling", tags=["Pebbling"])

    @router.get("/status")
    def status():
        return {"playground": "available"}

    return router

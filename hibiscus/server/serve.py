from typing import Any, Union
from urllib.parse import quote

from fastapi import FastAPI
from rich import box
from rich.panel import Panel

from .router import get_router
from ..settings.settings import HibiscusSettings

from agno.agent import Agent as agnoAgent
from smolagents import CodeAgent as smolAgent
from crewai import Agent as crewaiAgent


class HibiscusServer:
    def __init__(
        self,
        agent: Optional[Union[agnoAgent, smolAgent, crewaiAgent]] = None,
    ): 
        if not agent:
            raise ValueError("We only support Agno, SmolAgents and CrewAI agents, More agents coming soon, look the documentation for more details")

        self.agent: Optional[Agent] = agent
        self.settings = PebblingSettings()
        self.endpoints_created: Set[str] = set()
        self.app = FastAPI(
            title=self.settings.title,
            description=self.settings.description,
            version=self.settings.version,
            docs_url="/docs"
        )

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": str(exc.detail)},
            )

        async def general_exception_handler(request: Request, call_next):
            try:
                return await call_next(request)
            except Exception as e:
                return JSONResponse(
                    status_code=e.status_code if hasattr(e, "status_code") else 500,
                    content={"detail": str(e)},
                )

        self.app.middleware("http")(general_exception_handler)

        self.router = APIRouter(prefix="/v1")
        self.router.include_router(
            get_router(self.agent)
        )

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

        return self.api_app

    def serve_app(
        self,
        host: str = "localhost",
        port: int = 8000,
        **kwargs: Any,
    ):
        import uvicorn
        import console

        endpoint = quote(f"{host}:{port}")

        panel = Panel(
            f"[bold green]Playground URL:[/bold green] [link={url}]{url}[/link]",
            title="Agent Playground",
            expand=False,
            border_style="cyan",
            box=box.HEAVY,
            padding=(2, 2),
        )
        console.print(panel)

        uvicorn.run(app=self.app, host=host, port=port, reload=reload, **kwargs)

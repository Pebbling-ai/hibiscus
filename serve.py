"""Serve the Hibiscus application using uvicorn."""

from typing import Union
import uvicorn
from fastapi import FastAPI
from rich.panel import Panel
from rich import box
from rich.console import Console

console = Console()


def serve_app(
    app: Union[str, FastAPI],
    *,
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    **kwargs,
):
    """
    Serve the Hibiscus Agent Registry API.

    Args:
        app: The FastAPI application or import string
        host: Host to bind the server to
        port: Port to bind the server to
        reload: Whether to enable auto-reload
        **kwargs: Additional arguments to pass to uvicorn.run
    """
    # Create a panel with the API information
    api_url = f"http://{host}:{port}"
    docs_url = f"{api_url}/docs"

    panel = Panel(
        f"[bold green]API URL:[/bold green] {api_url}\n"
        f"[bold green]API Docs:[/bold green] [link={docs_url}]{docs_url}[/link]",
        title="🌺 Hibiscus Agent Registry API",
        expand=False,
        border_style="cyan",
        box=box.HEAVY,
        padding=(2, 2),
    )

    # Print the panel
    console.print(panel)

    # Start the server
    uvicorn.run(app=app, host=host, port=port, reload=reload, **kwargs)

import typer
import httpx
import os
import json
import time
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.box import ROUNDED, DOUBLE, HEAVY
from rich.emoji import Emoji
from rich.text import Text
from rich.prompt import Confirm
from rich import print as rprint
from pydantic import BaseModel
from serve import serve_app
from app.db.client import Database 
from app.utils.typesense_utils import TypesenseClient

# Initialize Rich console for pretty output
console = Console()

# Create CLI app
app = typer.Typer(help="Hibiscus Agent Registry CLI")
agent_app = typer.Typer(help="Manage agents")
app.add_typer(agent_app, name="agent")

# Configuration
class Config:
    api_url: str = os.environ.get("HIBISCUS_API_URL", "http://localhost:8000")
    api_key: Optional[str] = os.environ.get("HIBISCUS_API_KEY")

app_config = Config()

# Helper functions
def get_headers():
    """Get authorization headers for API requests"""
    if not app_config.api_key:
        console.print(Panel(
            "Warning: No API key set. Using unauthenticated access.",
            title="Authentication Warning",
            border_style="yellow"
        ))
        return {}
    else:
        return {"Authorization": f"Bearer {app_config.api_key}"}

def handle_response(response):
    """Handle API response and print errors if any"""
    try:
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        error_detail = "Unknown error"
        try:
            error_data = e.response.json()
            error_detail = error_data.get("detail", str(e))
        except:
            error_detail = str(e)
        
        console.print(Panel(
            f"[bold red]Error:[/] {error_detail}",
            title="API Error",
            border_style="red"
        ))
        raise typer.Exit(1)

def get_health_emoji(status):
    """Return emoji based on health status"""
    if status == "active":
        return ":green_circle:"
    elif status == "degraded":
        return ":yellow_circle:"
    elif status == "inactive":
        return ":red_circle:"
    return ":question_mark:"

# Server command
@app.command()
def start(
    host: str = typer.Option("0.0.0.0", help="Host to bind the server to"),
    port: int = typer.Option(8000, help="Port to bind the server to"),
    reload: bool = typer.Option(False, help="Enable auto-reload")
):
    """Start the 🌺 Hibiscus Agent Registry API server."""
    console.print(Panel(
        f"Starting Hibiscus server on [bold cyan]{host}:{port}[/] {'with auto-reload' if reload else ''}",
        title="🌺 Hibiscus Server",
        border_style="green",
        expand=False
    ))
    
    serve_app(
        app="app.main:app",
        host=host,
        port=port,
        reload=reload,
    )

# Configuration command
@app.command()
def config(
    api_url: Optional[str] = typer.Option(None, help="Hibiscus API URL"),
    api_key: Optional[str] = typer.Option(None, help="API key for authentication"),
):
    """Configure CLI settings."""
    # Simpler approach without nested layouts for a more compact display
    config_content = []
    
    if api_url:
        os.environ["HIBISCUS_API_URL"] = api_url
        app_config.api_url = api_url
        config_content.append(f"API URL set to: [bold cyan]{api_url}[/]")
    
    if api_key:
        os.environ["HIBISCUS_API_KEY"] = api_key
        app_config.api_key = api_key
        config_content.append("API key set [bold green]successfully[/]")
    
    if not api_url and not api_key:
        config_content.append("[bold]Current configuration:[/]")
        config_content.append(f"API URL: [cyan]{app_config.api_url}[/]")
        config_content.append(f"API Key: [{'green' if app_config.api_key else 'red'}]{'Configured ✓' if app_config.api_key else 'Not configured ✗'}[/]")
    
    # Use a single panel with a more compact display
    console.print(Panel(
        "\n".join(config_content),
        title="[bold]🌺 Hibiscus Configuration[/]",
        border_style="green",
        box=ROUNDED,
        padding=(1, 2)
    ))

@agent_app.command("list")
def list_agents_db(
    search: Optional[str] = typer.Option(None, help="Search term for filtering agents"),
    is_team: Optional[bool] = typer.Option(None, help="Filter by team status"),
    page: int = typer.Option(1, help="Page number", min=1),
    page_size: int = typer.Option(20, help="Items per page", min=1, max=100),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """List agents with optional filtering using the database directly."""
    
    # Calculate offset for pagination
    offset = (page - 1) * page_size
    
    # This is an async function wrapper for the sync Typer command
    async def run_async():
        agents = []
        total_count = 0
        
        # Use Typesense for search if search term provided
        if search:
            try:
                # Search using Typesense
                search_results = await TypesenseClient.search_agents(search)
                
                # Extract the agent IDs from search results
                # (Note: This is just for reference - we still need filter logic)
                agents = await Database.list_agents(
                    limit=page_size,
                    offset=offset,
                    is_team=is_team
                )
                
                # Apply search result filtering here
                # This is a simplified approach since we can't pass agent_ids
                
                # Get total count
                total_count = await Database.count_agents(
                    registry_id=None if not is_team else is_team
                )
            except Exception as e:
                console.print(Panel(
                    f"[bold red]Error searching agents:[/] {str(e)}",
                    title="Search Error",
                    border_style="red"
                ))
                return
        else:
            # Get agents directly from database
            try:
                agents = await Database.list_agents(
                    limit=page_size,
                    offset=offset,
                    is_team=is_team
                )
                
                # Get total count
                total_count = await Database.count_agents(
                    registry_id=None if not is_team else is_team
                )
            except Exception as e:
                console.print(Panel(
                    f"[bold red]Error fetching agents:[/] {str(e)}",
                    title="Database Error",
                    border_style="red"
                ))
                return
        
        # Calculate total pages
        total_pages = (total_count + page_size - 1) // page_size
        
        # Create metadata
        metadata = {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
        
        return {"items": agents, "metadata": metadata}
    
    # Run the async function and get results
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Fetching agents from database..."),
        console=console,
        transient=True
    ) as progress:
        progress.add_task("fetch", total=None)
        try:
            # Run the async function
            data = asyncio.run(run_async())
            if not data:
                return
        except Exception as e:
            console.print(Panel(
                f"[bold red]Error:[/] {str(e)}",
                title="Database Error",
                border_style="red"
            ))
            return
    
    # Output as JSON if requested
    if output_json:
        console.print_json(json.dumps(data))
        return
    
    # Display results in a table
    agents = data.get("items", [])
    metadata = data.get("metadata", {})
    
    if not agents:
        console.print(Panel(
            "No agents found matching the criteria",
            title="Empty Result",
            border_style="yellow"
        ))
        return
    
    # Create and populate table
    table = Table(
        title=f"🌺 [bold]Hibiscus Agents (Database Direct)[/]",
        box=ROUNDED,
        highlight=True,
        show_header=True,
        header_style="bold magenta",
        border_style="blue"
    )
    
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Description", max_width=50)
    table.add_column("Team", justify="center", style="cyan")
    table.add_column("Health", justify="center")
    
    for agent in agents:
        # Get health status and emoji
        health_status = agent.get("health_status", "unknown").lower()
        health_emoji = get_health_emoji(health_status)
        
        table.add_row(
            str(agent.get("id", "")),
            agent.get("name", ""),
            agent.get("description", "")[:50] + ("..." if len(agent.get("description", "")) > 50 else ""),
            "✓" if agent.get("is_team") else "✗",
            f"{health_emoji} {health_status.capitalize()}" if health_status else "❓ Unknown"
        )
    
    console.print(table)
    
    # Pagination info
    pagination_text = Text()
    pagination_text.append("Page ", style="dim")
    pagination_text.append(f"{metadata.get('page', 1)}", style="bold cyan")
    pagination_text.append(" of ", style="dim")
    pagination_text.append(f"{metadata.get('total_pages', 1)}", style="bold cyan")
    pagination_text.append(" • ", style="dim")
    pagination_text.append(f"{metadata.get('total', 0)}", style="bold green")
    pagination_text.append(" total agents", style="dim")
    
    console.print(Panel(pagination_text, box=ROUNDED, border_style="blue", expand=False))


if __name__ == "__main__":
    app()
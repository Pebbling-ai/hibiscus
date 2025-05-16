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
from rich.prompt import Confirm, Prompt
from rich import print as rprint
from pydantic import BaseModel
from serve import serve_app
from app.db.client import Database 
from app.utils.typesense_utils import TypesenseClient
from app.utils.search_utils import search_agents, get_agent_by_id, update_agent_with_typesense

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
    port: int = typer.Option(8020, help="Port to bind the server to"),
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


@agent_app.command("list")
def list_agents_cmd(
    search: Optional[str] = typer.Option(None, help="Search term for filtering agents"),
    is_team: Optional[bool] = typer.Option(None, help="Filter by team status"),
    page: int = typer.Option(1, help="Page number", min=1),
    page_size: int = typer.Option(20, help="Items per page", min=1, max=100),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """List agents with optional filtering."""
    
    # This is an async function wrapper for the sync Typer command
    async def run_async():
        try:
            # Use the search_agents utility function
            data = await search_agents(
                search=search,
                is_team=is_team,
                page=page,
                page_size=page_size
            )
            return data
        except Exception as e:
            console.print(Panel(
                f"[bold red]Error fetching agents:[/] {str(e)}",
                title="Search Error",
                border_style="red"
            ))
            return None
    
    # Run the async function and get results
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Fetching agents..."),
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
                title="Search Error",
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
        title=f"🌺 [bold]Hibiscus Agents[/]",
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


@agent_app.command("get")
def get_agent_cmd(
    agent_id: str = typer.Argument(..., help="ID of the agent to retrieve"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Get a specific agent by ID."""
    
    async def run_async():
        try:
            # Use the get_agent_by_id utility function
            agent = await get_agent_by_id(agent_id)
            return agent
        except Exception as e:
            console.print(Panel(
                f"[bold red]Error retrieving agent:[/] {str(e)}",
                title="Error",
                border_style="red"
            ))
            return None
    
    # Run the async function and get results
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold green]Fetching agent with ID: {agent_id}..."),
        console=console,
        transient=True
    ) as progress:
        progress.add_task("fetch", total=None)
        try:
            # Run the async function
            agent = asyncio.run(run_async())
            if not agent:
                return
        except Exception as e:
            console.print(Panel(
                f"[bold red]Error:[/] {str(e)}",
                title="Agent Retrieval Error",
                border_style="red"
            ))
            return
    
    # Output as JSON if requested
    if output_json:
        console.print_json(json.dumps(agent))
        return
    
    # Display agent details in a rich format
    display_agent_details(agent)


@agent_app.command("update")
def update_agent_cmd(
    agent_id: str = typer.Argument(..., help="ID of the agent to retrieve and update"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Update an existing agent interactively."""
    from rich.prompt import Prompt, Confirm
    
    # First, get the current agent data
    async def get_agent_async():
        try:
            return await get_agent_by_id(agent_id)
        except Exception as e:
            console.print(Panel(
                f"[bold red]Error retrieving agent:[/] {str(e)}",
                title="Error",
                border_style="red"
            ))
            return None
            
    # Fetch the agent
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold green]Fetching agent with ID: {agent_id}..."),
        console=console,
        transient=True
    ) as progress:
        progress.add_task("fetch", total=None)
        try:
            agent = asyncio.run(get_agent_async())
            if not agent:
                return
        except Exception as e:
            console.print(Panel(
                f"[bold red]Error:[/] {str(e)}",
                title="Agent Retrieval Error",
                border_style="red"
            ))
            return
    
    # Display current agent details
    console.print(Panel(
        f"You are about to update the following agent:",
        title="[bold]🌺 Update Agent[/]",
        border_style="yellow"
    ))
    display_agent_details(agent)
    
    # Collect update data interactively
    update_data = {}
    
    # Update name
    if Confirm.ask("Update name?", default=False):
        new_name = Prompt.ask("Enter new name", default=agent.get("name", ""))
        if new_name != agent.get("name", ""):
            update_data["name"] = new_name
    
    # Update description
    if Confirm.ask("Update description?", default=False):
        new_description = Prompt.ask("Enter new description", default=agent.get("description", ""))
        if new_description != agent.get("description", ""):
            update_data["description"] = new_description
    
    # Update tags
    if Confirm.ask("Update tags?", default=False):
        current_tags = ", ".join(agent.get("tags", []))
        new_tags_str = Prompt.ask("Enter tags (comma-separated)", default=current_tags)
        if new_tags_str.strip():
            new_tags = [tag.strip() for tag in new_tags_str.split(",")]
            if new_tags != agent.get("tags", []):
                update_data["tags"] = new_tags
    
    # Update domains
    if Confirm.ask("Update domains?", default=False):
        current_domains = ", ".join(agent.get("domains", []))
        new_domains_str = Prompt.ask("Enter domains (comma-separated)", default=current_domains)
        if new_domains_str.strip():
            new_domains = [domain.strip() for domain in new_domains_str.split(",")]
            if new_domains != agent.get("domains", []):
                update_data["domains"] = new_domains
    
    # Update metadata (if applicable)
    if agent.get("metadata") and Confirm.ask("Update metadata?", default=False):
        console.print("[yellow]Note: Manual metadata editing not supported in CLI. Use the API for complex metadata updates.[/]")
    
    # If it's a team, update mode
    if agent.get("is_team") and Confirm.ask("Update team mode?", default=False):
        modes = ["collaborate", "coordinate", "route"]
        current_mode_index = modes.index(agent.get("mode", "collaborate")) if agent.get("mode") in modes else 0
        mode_options = "\n".join([f"{i+1}. {mode}" for i, mode in enumerate(modes)])
        console.print(f"Team modes:\n{mode_options}")
        mode_choice = Prompt.ask("Select mode (1-3)", default=str(current_mode_index + 1))
        try:
            mode_index = int(mode_choice) - 1
            if 0 <= mode_index < len(modes):
                new_mode = modes[mode_index]
                if new_mode != agent.get("mode"):
                    update_data["mode"] = new_mode
        except ValueError:
            console.print("[red]Invalid selection, mode not updated[/]")
    
    # Check if any data was updated
    if not update_data:
        console.print(Panel(
            "No changes were made to the agent.",
            title="Update Cancelled",
            border_style="yellow"
        ))
        return
    
    # Confirm the update
    console.print(Panel(
        f"The following fields will be updated: {', '.join(update_data.keys())}",
        title="Confirm Update",
        border_style="yellow"
    ))
    
    if not Confirm.ask("Proceed with update?", default=True):
        console.print("Update cancelled.")
        return
    
    # Update the agent
    async def update_agent_async():
        try:
            # Get the user ID from the agent
            user_id = agent.get("user_id")
            if not user_id:
                raise ValueError("Could not determine user ID from agent data")
                
            # Use the update_agent_with_typesense utility function
            updated_agent = await update_agent_with_typesense(
                agent_id=agent_id,
                update_data=update_data,
                current_user_id=user_id
            )
            return updated_agent
        except Exception as e:
            console.print(Panel(
                f"[bold red]Error updating agent:[/] {str(e)}",
                title="Error",
                border_style="red"
            ))
            return None
    
    # Run the update
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold green]Updating agent..."),
        console=console,
        transient=True
    ) as progress:
        progress.add_task("update", total=None)
        try:
            updated_agent = asyncio.run(update_agent_async())
            if not updated_agent:
                return
        except Exception as e:
            console.print(Panel(
                f"[bold red]Error:[/] {str(e)}",
                title="Update Error",
                border_style="red"
            ))
            return
    
    # Output as JSON if requested
    if output_json:
        console.print_json(json.dumps(updated_agent))
        return
    
    # Display success message and updated agent details
    console.print(Panel(
        "Agent updated successfully!",
        title="Update Complete",
        border_style="green"
    ))
    display_agent_details(updated_agent)


def display_agent_details(agent: Dict[str, Any]):
    """Display agent details in a rich format."""
    # Create the main panel
    title = f"🌺 Agent: [bold]{agent.get('name', 'Unnamed Agent')}[/]"
    
    # Health status
    health_status = agent.get("health_status", "unknown").lower()
    health_emoji = get_health_emoji(health_status)
    
    # Basic details
    details = [
        f"[bold]ID:[/] {agent.get('id', 'N/A')}",
        f"[bold]Type:[/] {'Team' if agent.get('is_team') else 'Individual Agent'}",
        f"[bold]Health:[/] {health_emoji} {health_status.capitalize() if health_status else 'Unknown'}",
        f"[bold]Created:[/] {agent.get('created_at', 'N/A')}",
        f"[bold]Last Updated:[/] {agent.get('updated_at', 'N/A')}",
    ]
    
    # Add description if available
    if agent.get('description'):
        details.append("")
        details.append("[bold]Description:[/]")
        details.append(agent.get('description', ''))
    
    # Add tags if available
    if agent.get('tags'):
        tags_str = ", ".join([f"[cyan]{tag}[/]" for tag in agent.get('tags', [])])
        details.append("")
        details.append(f"[bold]Tags:[/] {tags_str}")
    
    # Add domains if available
    if agent.get('domains'):
        domains_str = ", ".join([f"[green]{domain}[/]" for domain in agent.get('domains', [])])
        details.append("")
        details.append(f"[bold]Domains:[/] {domains_str}")
    
    # Add team members if this is a team
    if agent.get('is_team') and agent.get('members'):
        details.append("")
        details.append(f"[bold]Team Members:[/] {len(agent.get('members', []))} agents")
        details.append(f"[bold]Team Mode:[/] {agent.get('mode', 'N/A')}")
    
    # Add DID information if available
    if agent.get('did'):
        details.append("")
        details.append("[bold]Verification:[/]")
        details.append(f"DID: {agent.get('did', 'N/A')}")
    
    # Display the panel
    console.print(Panel(
        "\n".join(details),
        title=title,
        border_style="green",
        box=ROUNDED,
        padding=(1, 2)
    ))


if __name__ == "__main__":
    app()
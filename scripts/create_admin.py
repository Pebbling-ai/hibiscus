import os
import uuid
import secrets
from datetime import datetime, timedelta, timezone
import asyncio
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text
from supabase import create_client, Client

# Initialize Typer app and Rich console
app = typer.Typer(help="Hibiscus Agent Registry Admin Tools")
console = Console()

# Load environment variables
load_dotenv()

# Table names
USERS_TABLE = "users"
API_KEYS_TABLE = "api_keys"

# Initialize Supabase client
# For admin operations, we need to use the service_role key to bypass RLS
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY"))

if not supabase_url or not supabase_key:
    console.print("[bold red]Error: Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env file.[/bold red]")
    exit(1)

# Connect with service role to bypass RLS
supabase: Client = create_client(supabase_url, supabase_key)

async def create_initial_admin(email: str, name: str, expire_days: int = 365) -> str:
    """
    Create an initial admin user and API key in the database.
    """
    # Generate UUIDs for user and API key
    user_id = str(uuid.uuid4())
    key_id = str(uuid.uuid4())
    
    # Generate API key
    api_key = secrets.token_hex(32)
    now = datetime.now(timezone.utc).isoformat()
    
    # Create user record
    user_data = {
        "id": user_id,
        "email": email,
        "full_name": name,
        "created_at": now,
        "updated_at": None
    }
    
    # Create API key record
    key_data = {
        "id": key_id,
        "user_id": user_id,
        "key": api_key,
        "name": "Initial Admin Key",
        "description": "Auto-generated initial admin key",
        "created_at": now,
        "last_used_at": None,
        "is_active": True,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=expire_days)).isoformat()  # 1 year expiry
    }
    
    # Create progress display
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[bold]{task.fields[status]}"),
        console=console
    ) as progress:
        # Add tasks
        overall_task = progress.add_task("[yellow]Creating admin account...", total=3, status="Starting")
        user_task = progress.add_task("[green]Creating user record", total=1, status="Pending")
        key_task = progress.add_task("[green]Creating API key", total=1, status="Pending")
        
        # Start the process
        progress.update(overall_task, advance=1, status="In progress")
        
        try:
            # Use Supabase - insert user
            progress.update(user_task, status="Inserting...")
            user_response = supabase.table(USERS_TABLE).insert(user_data).execute()
            
            if hasattr(user_response, "error") and user_response.error:
                progress.update(user_task, status="Error")
                progress.update(overall_task, status="Failed")
                raise Exception(f"Error creating user: {user_response.error.message}")
            
            progress.update(user_task, advance=1, status="Complete")
            progress.update(overall_task, advance=1, status="User created")
            
            # Insert API key
            progress.update(key_task, status="Inserting...")
            key_response = supabase.table(API_KEYS_TABLE).insert(key_data).execute()
            
            if hasattr(key_response, "error") and key_response.error:
                progress.update(key_task, status="Error")
                progress.update(overall_task, status="Failed")
                raise Exception(f"Error creating API key: {key_response.error.message}")
            
            progress.update(key_task, advance=1, status="Complete")
            progress.update(overall_task, advance=1, status="Complete")
            
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")
            return None
    
    return api_key

@app.command()
def create_admin(
    email: str = typer.Option("admin@example.com", help="Admin email address"),
    name: str = typer.Option("Admin", help="Admin full name"),
    expire_days: int = typer.Option(365, help="API key expiration in days")
):
    """Create an initial admin user with API key in the Hibiscus database."""
    
    # Show startup banner
    console.print(Panel.fit(
        "[bold green]Hibiscus Agent Registry[/bold green]\nAdmin Creation Tool",
        title="🌺 Hibiscus",
        border_style="green"
    ))
    
    console.print(f"Creating admin with email: [bold]{email}[/bold]")
    
    # Create the admin user
    api_key = asyncio.run(create_initial_admin(email, name, expire_days))
    
    if api_key:
        # Show success message with the API key
        console.print(Panel(
            f"[bold green]Admin user created successfully![/bold green]\n\n"
            f"Email: [bold]{email}[/bold]\n"
            f"API Key: [bold yellow]{api_key}[/bold yellow]\n\n"
            "Keep this key secure - it won't be shown again!",
            title="✅ Success",
            border_style="green"
        ))
        
        # Show example usage
        console.print(Panel(
            f"curl -X POST http://localhost:8000/user/tokens \\\n"
            f"  -H \"Content-Type: application/json\" \\\n"
            f"  -H \"X-API-Key: {api_key}\" \\\n"
            f"  -d '{{\"name\": \"MyAPIToken\", \"expires_in_days\": 30, \"description\": \"Token for testing\"}}'",
            title="📋 Example Usage",
            border_style="blue"
        ))
    else:
        console.print(Panel(
            "[bold red]Failed to create admin user and API key.[/bold red]",
            title="❌ Error",
            border_style="red"
        ))

if __name__ == "__main__":
    app()
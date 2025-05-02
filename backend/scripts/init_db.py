#!/usr/bin/env python3
import os
import asyncio
import asyncpg
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.style import Style
from rich.text import Text
from rich.panel import Panel
from rich.box import HEAVY, ROUNDED, DOUBLE
from app.db.schema import SUPABASE_SCHEMA

# Setup logging to file only (silent console)
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logger.remove()
logger.add(log_dir / "db_init_{time}.log", rotation="10 MB")

# Initialize Rich console
console = Console()

# Load environment variables
load_dotenv()

# Database connection parameters
DB_CONNECTION_STRING = os.getenv("SUPERBASE_CONNECTION_STRING")
DB_HOST = os.getenv("SUPERBASE_HOST")
DB_PASSWORD = os.getenv("SUPERBASE_PASSWORD")
DB_PORT = os.getenv("SUPERBASE_PORT", "5432")
DB_USER = os.getenv("SUPERBASE_USER", "postgres")
DB_NAME = os.getenv("SUPERBASE_DB_NAME", "postgres")

if not DB_CONNECTION_STRING and (not DB_HOST or not DB_PASSWORD):
    raise ValueError("Database connection parameters missing. Set SUPERBASE_CONNECTION_STRING or both SUPERBASE_HOST and SUPERBASE_PASSWORD")


async def create_tables():
    """Create all required tables, indexes and policies in Supabase database."""
    # Display stylish intro
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Hibiscus Agent Registry[/bold cyan]",
        subtitle="[bold green]Database Initialization[/bold green]",
        box=DOUBLE,
        border_style="bright_blue"
    ))
    console.print("\n")
    
    # Establish database connection
    if DB_CONNECTION_STRING:
        conn = await asyncpg.connect(DB_CONNECTION_STRING)
    else:
        conn = await asyncpg.connect(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME,
            host=DB_HOST, port=DB_PORT
        )
    logger.info("Database connection established")

    try:
        # Create tables section
        console.print(Panel(
            "[bold green]Creating Tables[/bold green]",
            box=ROUNDED,
            border_style="bright_blue"
        ))
        results_table = Table(
            title="[bold cyan]Hibiscus Tables[/bold cyan]", 
            show_header=True,
            header_style="bold magenta",
            border_style="bright_blue",
            box=HEAVY
        )
        results_table.add_column("Table", style="bright_green")
        results_table.add_column("Status", justify="center")

        for table in SUPABASE_SCHEMA["tables"]:
            table_name = table["name"]
            
            # Construct column definitions
            columns = []
            for column in table["columns"]:
                column_def = f"{column['name']} {column['type']}"
                
                if column.get("primaryKey"):
                    column_def += " PRIMARY KEY"
                if column.get("notNull"):
                    column_def += " NOT NULL"
                if column.get("unique"):
                    column_def += " UNIQUE"
                
                # Handle DEFAULT expressions
                if column.get("default") is not None:
                    default_value = column["default"]
                    if isinstance(default_value, str) and default_value in ["now()", "gen_random_uuid()"]:
                        column_def += f" DEFAULT {default_value}"
                    elif isinstance(default_value, str) and not default_value.startswith("'") and not default_value.startswith('"'):
                        column_def += f" DEFAULT '{default_value}'"
                    else:
                        column_def += f" DEFAULT {default_value}"
                
                if column.get("references"):
                    ref = column["references"]
                    column_def += f" REFERENCES {ref['table']}({ref['column']})"
                
                columns.append(column_def)
            
            create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)});"
            
            try:
                await conn.execute(create_table_sql)
                results_table.add_row(
                    Text(table_name, style="green"), 
                    Text("✓", style="bold bright_green")
                )
            except Exception as e:
                results_table.add_row(
                    Text(table_name, style="dim"), 
                    Text("✗", style="bold red")
                )
                logger.error(f"Failed to create table {table_name}: {str(e)}")
        console.print(results_table)
        
        # Create indexes section
        console.print("\n")
        console.print(Panel(
            "[bold green]Creating Indexes[/bold green]",
            box=ROUNDED,
            border_style="bright_blue"
        ))
        index_table = Table(
            title="[bold cyan]Indexes[/bold cyan]", 
            show_header=True,
            header_style="bold magenta",
            border_style="bright_blue",
            box=HEAVY
        )
        index_table.add_column("Index", style="bright_yellow")
        index_table.add_column("Table", style="bright_green")
        index_table.add_column("Status", justify="center")
        
        for index in SUPABASE_SCHEMA["indexes"]:
            if "sql" in index:
                create_index_sql = index["sql"]
                index_name = index.get("name", f"custom_index_{index['table']}")
                table_name = index["table"]
            else:
                table_name = index["table"]
                columns = ",".join(index["columns"])
                method = index["method"]
                options = index.get("options", "")
                
                index_name = f"idx_{table_name}_{'_'.join(index['columns'])}"
                create_index_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} USING {method} ({columns})"
                
                if options:
                    create_index_sql += f" {options}"
            
            try:
                await conn.execute(create_index_sql)
                index_table.add_row(
                    Text(index_name, style="yellow"), 
                    Text(table_name, style="green"), 
                    Text("✓", style="bold bright_green")
                )
            except Exception as e:
                index_table.add_row(
                    Text(index_name, style="dim"), 
                    Text(table_name, style="dim"), 
                    Text(f"✗", style="bold red")
                )
                logger.error(f"Failed to create index {index_name}: {str(e)}")
        
        console.print(index_table)
        
        # Create RLS policies section
        console.print("\n")
        console.print(Panel(
            "[bold green]Creating Row Level Security Policies[/bold green]",
            box=ROUNDED,
            border_style="bright_blue"
        ))
        policy_table = Table(
            title="[bold cyan]Row Level Security Policies[/bold cyan]", 
            show_header=True,
            header_style="bold magenta",
            border_style="bright_blue",
            box=HEAVY
        )
        policy_table.add_column("Policy", style="bright_cyan")
        policy_table.add_column("Table", style="bright_green")
        policy_table.add_column("Operation", style="bright_yellow")
        policy_table.add_column("Status", justify="center")
        
        for policy in SUPABASE_SCHEMA["policies"]:
            table_name = policy["table"]
            policy_name = policy["name"]
            definition = policy["definition"]
            using_expr = policy["using"]
            check_expr = policy.get("check")
            
            # Enable RLS on the table
            await conn.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;")
            
            # Drop existing policy if exists
            try:
                await conn.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name};")
            except Exception:
                pass
            
            # Create policy with correct syntax for each operation type
            try:
                if definition == "INSERT":
                    create_policy_sql = f"CREATE POLICY {policy_name} ON {table_name} FOR {definition} WITH CHECK ({check_expr})"
                elif definition == "UPDATE":
                    create_policy_sql = f"CREATE POLICY {policy_name} ON {table_name} FOR {definition} USING ({using_expr}) WITH CHECK ({check_expr})"
                else:
                    create_policy_sql = f"CREATE POLICY {policy_name} ON {table_name} FOR {definition} USING ({using_expr})"
                
                await conn.execute(create_policy_sql)
                policy_table.add_row(
                    Text(policy_name, style="cyan"), 
                    Text(table_name, style="green"), 
                    Text(definition, style="yellow"), 
                    Text("✓", style="bold bright_green")
                )
            except Exception as e:
                policy_table.add_row(
                    Text(policy_name, style="dim"), 
                    Text(table_name, style="dim"), 
                    Text(definition, style="dim"), 
                    Text("✗", style="bold red")
                )
                logger.error(f"Failed to create policy {policy_name}: {str(e)}")
        
        console.print(policy_table)
        
        # Success message at the end
        console.print("\n")
        console.print(Panel.fit(
            "[bold green]Database Initialization Complete![/bold green]",
            subtitle="[bright_cyan]Agent Registry ready for secure agent communication[/bright_cyan]",
            box=DOUBLE,
            border_style="bright_green"
        ))
            
    except Exception as e:
        # Error message
        console.print("\n")
        console.print(Panel(
            f"[bold red]Error:[/bold red] {str(e)}",
            box=HEAVY,
            border_style="red"
        ))
        logger.error(f"Error: {str(e)}")
        raise
    finally:
        # Close the connection
        await conn.close()
        logger.info("Database connection closed")


async def main():
    try:
        await create_tables()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

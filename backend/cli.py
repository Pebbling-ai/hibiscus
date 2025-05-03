import typer
from serve import serve_app

app = typer.Typer(help="Hibiscus Agent Registry CLI")

@app.command()
def start(
    host: str = typer.Option("0.0.0.0", help="Host to bind the server to"),
    port: int = typer.Option(8000, help="Port to bind the server to"),
    reload: bool = typer.Option(False, help="Enable auto-reload")
):
    """Start the 🌺 Hibiscus Agent Registry API server."""
    serve_app(
        app="app.main:app",
        host=host,
        port=port,
        reload=reload,
    )

if __name__ == "__main__":
    app()
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.api.routes import agents, federated_registries, tokens, health, users
from app.core.auth import API_KEY_HEADER

# Load environment variables
load_dotenv()

# Application settings
APP_TITLE = "🌺Hibiscus Agent Registry API"
APP_DESCRIPTION = "Backend API for Hibiscus Agent Registry"
APP_VERSION = "0.1.0"

# CORS settings
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.
    """
    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(agents.router)
    app.include_router(federated_registries.router)
    app.include_router(tokens.router)
    app.include_router(health.router)
    app.include_router(users.router)
    
    # Error handling
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"An unexpected error occurred: {str(exc)}",
            },
        )
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "success": True,
            "message": "Welcome to 🌺 Hibiscus Agent Registry API",
            "data": {
                "version": APP_VERSION,
                "documentation": "/docs",
            }
        }
    
    return app


app = create_application()

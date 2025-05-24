"""Main application module for the Hibiscus service."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from loguru import logger

from app.api.routes import agents, federated_registries, tokens, health
from app.utils.typesense_utils import TypesenseClient

# Load environment variables
load_dotenv()

# Application settings
APP_TITLE = "🌺Hibiscus Agent Registry API"
APP_DESCRIPTION = "Backend API for Hibiscus Agent Registry"
APP_VERSION = "0.1.0"

# CORS settings
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for application startup and shutdown events."""
    # Startup logic
    try:
        # Initialize Typesense collections
        initialized = await TypesenseClient.initialize_collections()
        if initialized:
            logger.info("✅ Typesense collections initialized successfully")
            
            # Sync agents to search index
            await TypesenseClient.sync_agents_to_search_index()
            logger.info("✅ Agents synced to search index")
        else:
            logger.warning("⚠️ Typesense initialization skipped or failed")
    except Exception as e:
        logger.error(f"❌ Error during startup: {str(e)}")
    
    yield  # Application runs here
    
    # Shutdown logic
    try:
        # Add any cleanup logic here if needed
        logger.info("✅ Shutdown complete")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {str(e)}")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        lifespan=lifespan,
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
            },
        }

    return app


app = create_application()

"""
FastAPI Application
Main FastAPI app configuration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.logger import logger
from app.core.config import settings
from app.api.routes import router
from app.api.middleware import logging_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting AgentMesh API...")
    # logger.info(f"Environment: {settings.ENV}")
    # logger.info(f"Debug mode: {settings.DEBUG}")
    
    logger.info("AgentMesh API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AgentMesh API...")
    
    # Close long-term memory connection
    from app.memory.long_term import close_long_term_memory
    close_long_term_memory()
    
    logger.info("Cleanup complete")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    
    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="AgentMesh API",
        description="Agentic AI system for intelligent query processing",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.middleware("http")(logging_middleware)
    
    # Include routes
    app.include_router(router, prefix="/api/v1", tags=["queries"])
    
    # Root endpoint - FIX THIS
    @app.get("/", tags=["root"])
    async def root():
        return {
            "name": "AgentMesh API",
            "version": "1.0.0",
            "status": "operational",  # ← Make sure this field exists
            "docs": "/docs"
        }
    
    logger.info("FastAPI app created successfully")
    
    return app
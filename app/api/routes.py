"""
API Routes
FastAPI route definitions
"""

from fastapi import APIRouter, HTTPException, status
# from fastapi.responses import JSONResponse
import traceback

from app.core.logger import logger
from app.core.exceptions import AgentError, ValidationError
from app.orchestrator.main import get_orchestrator
from app.api.models import (
    QueryRequest,
    QueryResponse,
    HealthResponse,
    StatsResponse,
    ErrorResponse
)

# Create router
router = APIRouter()

# Get orchestrator instance
orchestrator = get_orchestrator()


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Process a query",
    description="Process a user query through the agentic AI pipeline"
)
async def process_query(request: QueryRequest):
    """
    Process a user query and return a comprehensive answer.
    
    This endpoint:
    - Plans the query execution strategy
    - Researches information from the web
    - Verifies facts and source reliability
    - Synthesizes a comprehensive answer
    - Reflects on answer quality (optional)
    
    Returns a detailed response with answer, citations, and quality metrics.
    """
    try:
        logger.info(f"API request received: {request.query[:50]}...")
        
        # Validate query
        if not request.query.strip():
            raise ValidationError("Query cannot be empty")
        
        # Process query
        result = orchestrator.process_query(
            query=request.query,
            enable_reflection=request.enable_reflection
        )
        
        # Format response
        response = QueryResponse(
            query=result["query"],
            answer=result["answer"],
            confidence=result["confidence"],
            citations=[
                {
                    "url": c["url"],
                    "title": c["title"],
                    "reliability": c.get("reliability")
                }
                for c in result.get("citations", [])
            ],
            key_points=result.get("key_points", []),
            query_id=result["query_id"],
            timestamp=result["timestamp"],
            retry_count=result.get("retry_count", 0),
            quality={
                "credibility_level": result["quality"]["credibility_level"],
                "sources_verified": result["quality"]["sources_verified"],
                "answer_style": result["quality"]["answer_style"]
            },
            pipeline={
                "plan_confidence": result["pipeline"]["plan_confidence"],
                "sources_found": result["pipeline"]["sources_found"],
                "sources_analyzed": result["pipeline"]["sources_analyzed"],
                "verification_confidence": result["pipeline"]["verification_confidence"],
                "synthesis_confidence": result["pipeline"]["synthesis_confidence"],
                "reflection_quality": result["pipeline"].get("reflection_quality")
            } if "pipeline" in result else None
        )
        
        logger.info(f"API request completed: {result['query_id']}")
        return response
        
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except AgentError as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the API and all agents are operational"
)
async def health_check():
    """
    Health check endpoint.
    
    Returns the status of the API and loaded agents.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        agents_loaded=["planner", "researcher", "verifier", "synthesizer", "reflector"]
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get statistics",
    description="Get usage statistics for the orchestrator and agents"
)
async def get_statistics():
    """
    Get system statistics.
    
    Returns metrics about query processing, success rates, and agent performance.
    """
    try:
        stats = orchestrator.get_stats()
        
        return StatsResponse(
            total_queries=stats["total_queries"],
            successful_queries=stats["successful_queries"],
            failed_queries=stats["failed_queries"],
            success_rate=stats["success_rate"],
            retries_triggered=stats["retries_triggered"],
            average_execution_time=stats["average_execution_time"],
            agent_stats=stats.get("agent_stats")
        )
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.post(
    "/stats/reset",
    status_code=status.HTTP_200_OK,
    summary="Reset statistics",
    description="Reset all statistics counters"
)
async def reset_statistics():
    """
    Reset all statistics.
    
    Clears all counters for the orchestrator and agents.
    """
    try:
        orchestrator.reset_stats()
        return {"message": "Statistics reset successfully"}
        
    except Exception as e:
        logger.error(f"Failed to reset statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset statistics"
        )
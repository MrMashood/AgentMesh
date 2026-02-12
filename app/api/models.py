"""
API Request/Response Models
Pydantic models for API validation
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ========================
# REQUEST MODELS
# ========================

class QueryRequest(BaseModel):
    """Request model for query endpoint"""
    query: str = Field(..., min_length=1, max_length=1000, description="User query")
    enable_reflection: Optional[bool] = Field(default=True, description="Enable reflection agent")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is machine learning?",
                "enable_reflection": True
            }
        }


# ========================
# RESPONSE MODELS
# ========================

class Citation(BaseModel):
    """Citation model"""
    url: str
    title: str
    reliability: Optional[float] = None


class QualityMetrics(BaseModel):
    """Quality metrics model"""
    credibility_level: str
    sources_verified: int
    answer_style: str


class PipelineMetrics(BaseModel):
    """Pipeline metrics model"""
    plan_confidence: float
    sources_found: int
    sources_analyzed: int
    verification_confidence: float
    synthesis_confidence: float
    reflection_quality: Optional[float] = None


class QueryResponse(BaseModel):
    """Response model for query endpoint"""
    query: str
    answer: str
    confidence: float
    citations: List[Citation]
    key_points: List[str]
    query_id: str
    timestamp: str
    retry_count: int
    quality: QualityMetrics
    pipeline: Optional[PipelineMetrics] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is machine learning?",
                "answer": "Machine learning is a branch of artificial intelligence...",
                "confidence": 0.87,
                "citations": [
                    {
                        "url": "https://example.com",
                        "title": "ML Guide",
                        "reliability": 0.92
                    }
                ],
                "key_points": [
                    "ML is a subset of AI",
                    "Uses data to learn patterns"
                ],
                "query_id": "q_20260205_143022_abc123",
                "timestamp": "2026-02-05T14:30:22",
                "retry_count": 0,
                "quality": {
                    "credibility_level": "high",
                    "sources_verified": 3,
                    "answer_style": "detailed explanation"
                }
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    version: str
    agents_loaded: List[str]


class StatsResponse(BaseModel):
    """Response model for statistics"""
    total_queries: int
    successful_queries: int
    failed_queries: int
    success_rate: float
    retries_triggered: int
    average_execution_time: float
    agent_stats: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    query_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Query processing failed",
                "detail": "LLM service unavailable",
                "query_id": "q_20260205_143022_abc123"
            }
        }
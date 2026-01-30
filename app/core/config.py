from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
import os
from pathlib import Path


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    
    All settings can be overridden by setting environment variables
    with the same name (case-insensitive)
    """
    
    # API Keys 
    TAVILY_API_KEY: str = Field(
        default="",
        description="Tavily API key for web search"
    )
    
    # LLM Settings 
    LLM_PROVIDER: str = Field(
        default="ollama",
        description="LLM provider: ollama, openai, anthropic"
    )
    
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL"
    )
    
    OLLAMA_MODEL: str = Field(
        default="llama3",
        description="Ollama model name"
    )
    
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key"
    )
    
    OPENAI_MODEL: str = Field(
        default="gpt-5-nano",
        description="OpenAI model name"
    )
    
    # Application Settings
    APP_NAME: str = Field(
        default="AgentMesh",
        description="Application name"
    )
    
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Application version"
    )
    
    DEBUG: bool = Field(
        default=False,
        description="Debug mode"
    )
    
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    
    # Tool Settings
    MAX_SEARCH_RESULTS: int = Field(
        default=5,
        description="Maximum number of search results to return"
    )
    
    MAX_TOOL_CALLS_PER_QUERY: int = Field(
        default=20,
        description="Maximum tool calls allowed per query"
    )
    
    URL_FETCH_TIMEOUT: int = Field(
        default=15,
        description="Timeout for URL fetching in seconds"
    )
    
    MAX_PAGE_SIZE_MB: int = Field(
        default=5,
        description="Maximum webpage size to fetch in MB"
    )
    
    # Domain Allowlist
    ALLOWED_DOMAINS: List[str] = Field(
        default=[
            'who.int',
            'cdc.gov',
            'nih.gov',
            'bmj.com',
            'thelancet.com',
            'nejm.org',
            'jamanetwork.com',
            'pubmed.ncbi.nlm.nih.gov',
            'www.who.int',
            'www.cdc.gov',
            'www.nih.gov',
        ],
        description="Allowed domains for URL fetching"
    )
    
    # Agent Settings
    MAX_RETRIES: int = Field(
        default=3,
        description="Maximum retry attempts for failed operations"
    )
    
    CONFIDENCE_THRESHOLD: float = Field(
        default=0.8,
        description="Minimum confidence score to accept answer"
    )
    
    PLANNER_TEMPERATURE: float = Field(
        default=0.3,
        description="Temperature for planner agent"
    )
    
    RESEARCH_TEMPERATURE: float = Field(
        default=0.1,
        description="Temperature for research agent"
    )
    
    VERIFICATION_TEMPERATURE: float = Field(
        default=0.1,
        description="Temperature for verification agent"
    )
    
    SYNTHESIS_TEMPERATURE: float = Field(
        default=0.3,
        description="Temperature for synthesis agent"
    )
    
    REFLECTION_TEMPERATURE: float = Field(
        default=0.1,
        description="Temperature for reflection agent"
    )
    
    # Memory Settings
    MEMORY_DIR: str = Field(
        default="./data/memory",
        description="Directory for long-term memory storage"
    )
    
    LOG_DIR: str = Field(
        default="./data/logs",
        description="Directory for log files"
    )
    
    MAX_MEMORY_ENTRIES: int = Field(
        default=100,
        description="Maximum number of memory entries to store"
    )
    
    # Safety Settings 
    RATE_LIMIT_CALLS_PER_MINUTE: int = Field(
        default=30,
        description="Rate limit for tool calls per minute"
    )
    
    ENABLE_SAFETY_CHECKS: bool = Field(
        default=True,
        description="Enable safety checks and guardrails"
    )
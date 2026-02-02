from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
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
    
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
        self._create_directories()
        
    
    def _create_directories(self):
        """
        Create necessary directories on initialization
        """
        dirs = [self.MEMORY_DIR, self.LOG_DIR]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            
    
    def validate_api_keys(self) -> dict:
        """
        Validate that required API keys are present
        
        Returns:
            dict with validation results
        """
        issues = []
        
        if not self.TAVILY_API_KEY:
            issues.append("TAVILY_API_KEY is not set")
        
        if self.LLM_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            issues.append("OPENAI_API_KEY is not set but LLM_PROVIDER is 'openai'")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
            
            
    def get_llm_config(self) -> dict:
        """
        Get LLM configuration based on provider
        
        Returns:
            dict with LLM settings
        """
        if self.LLM_PROVIDER == "ollama":
            return {
                "provider": "ollama",
                "base_url": self.OLLAMA_BASE_URL,
                "model": self.OLLAMA_MODEL
            }
        elif self.LLM_PROVIDER == "openai":
            return {
                "provider": "openai",
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_MODEL
            }
        else:
            raise ValueError(f"Unsupported LLM provider: {self.LLM_PROVIDER}")
        
    
    def get_agent_config(self, agent_type: str) -> dict:
        """
        Get configuration for a specific agent type
        
        Args:
            agent_type: 'planner', 'research', 'verification', 'synthesis', 'reflection'
            
        Returns:
            dict with agent configuration
        """
        temp_map = {
            "planner": self.PLANNER_TEMPERATURE,
            "research": self.RESEARCH_TEMPERATURE,
            "verification": self.VERIFICATION_TEMPERATURE,
            "synthesis": self.SYNTHESIS_TEMPERATURE,
            "reflection": self.REFLECTION_TEMPERATURE
        }
        
        return {
            "temperature": temp_map.get(agent_type, 0.2),
            "max_retries": self.MAX_RETRIES,
            "max_tool_calls": self.MAX_TOOL_CALLS_PER_QUERY
        }
    
    def display_settings(self) -> str:
        """
        Display current settings (hide sensitive data)
        
        Returns:
            Formatted string with settings
        """
        output = []
        output.append("="*60)
        output.append(f"{self.APP_NAME} v{self.APP_VERSION} - Configuration")
        output.append("="*60)
        
        output.append("\n🔧 Application:")
        output.append(f"  Debug Mode: {self.DEBUG}")
        output.append(f"  Log Level: {self.LOG_LEVEL}")
        
        output.append("\n🤖 LLM:")
        output.append(f"  Provider: {self.LLM_PROVIDER}")
        if self.LLM_PROVIDER == "ollama":
            output.append(f"  Model: {self.OLLAMA_MODEL}")
            output.append(f"  URL: {self.OLLAMA_BASE_URL}")
        
        output.append("\n🔍 Tools:")
        output.append(f"  Max Search Results: {self.MAX_SEARCH_RESULTS}")
        output.append(f"  Max Tool Calls: {self.MAX_TOOL_CALLS_PER_QUERY}")
        output.append(f"  URL Timeout: {self.URL_FETCH_TIMEOUT}s")
        
        output.append("\n👥 Agents:")
        output.append(f"  Confidence Threshold: {self.CONFIDENCE_THRESHOLD}")
        output.append(f"  Max Retries: {self.MAX_RETRIES}")
        
        output.append("\n🔐 API Keys:")
        output.append(f"  Tavily: {'✅ Set' if self.TAVILY_API_KEY else '❌ Missing'}")
        
        output.append("\n" + "="*60)
        
        return "\n".join(output)
    
    
settings = Settings()   


def reload_settings():
    """Reload settings from environment"""
    global settings
    settings = Settings()
    return settings
    

"""
Core module for AgentMesh

Contains configuration, logging, and exception handling.
"""

from .config import settings, reload_settings
from app.core.logger import (
    logger,
    get_agent_logger,
    log_agent_action,
    log_tool_call,
    log_tool_result,
    LogTimer,
    log_execution
)
from .exceptions import (
    # Base
    AgentMeshException,
    
    # Configuration
    ConfigurationError,
    MissingAPIKeyError,
    
    # Tools
    ToolException,
    ToolTimeoutError,
    ToolExecutionError,
    RateLimitError,
    InvalidURLError,
    DomainNotAllowedError,
    
    # Agents
    AgentException,
    PlanningError,
    ResearchError,
    VerificationError,
    SynthesisError,
    LowConfidenceError,
    
    # Memory
    MemoryException,
    MemoryStorageError,
    MemoryRetrievalError,
    
    # LLM
    LLMException,
    LLMConnectionError,
    LLMResponseError,
    
    # Orchestration
    OrchestrationException,
    MaxRetriesExceeded,
    QueryTimeoutError,
    InvalidStateError,
    
    # Validation
    ValidationException,
    InvalidQueryError,
    InvalidParameterError,
    
    # Helpers
    handle_exception,
    is_recoverable
)

__all__ = [
    # Config
    'settings',
    'reload_settings',
    
    # Logging
    'logger',
    'get_agent_logger',
    'log_agent_action',
    'log_tool_call',
    'log_tool_result',
    'LogTimer',
    'log_execution',
    
    # Exceptions - Base
    'AgentMeshException',
    
    # Exceptions - Configuration
    'ConfigurationError',
    'MissingAPIKeyError',
    
    # Exceptions - Tools
    'ToolException',
    'ToolTimeoutError',
    'ToolExecutionError',
    'RateLimitError',
    'InvalidURLError',
    'DomainNotAllowedError',
    
    # Exceptions - Agents
    'AgentException',
    'PlanningError',
    'ResearchError',
    'VerificationError',
    'SynthesisError',
    'LowConfidenceError',
    
    # Exceptions - Memory
    'MemoryException',
    'MemoryStorageError',
    'MemoryRetrievalError',
    
    # Exceptions - LLM
    'LLMException',
    'LLMConnectionError',
    'LLMResponseError',
    
    # Exceptions - Orchestration
    'OrchestrationException',
    'MaxRetriesExceeded',
    'QueryTimeoutError',
    'InvalidStateError',
    
    # Exceptions - Validation
    'ValidationException',
    'InvalidQueryError',
    'InvalidParameterError',
    
    # Helpers
    'handle_exception',
    'is_recoverable'
]
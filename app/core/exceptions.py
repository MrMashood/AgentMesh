from typing import Optional, Dict, Any
from datetime import datetime


class AgentMeshException(Exception):
    """
    Base exception for all AgentMesh errors
    
    All custom exceptions inherit from this class.
    Provides common functionality like error codes and context.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        """
        Initialize base exception
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (e.g., "TOOL_TIMEOUT")
            context: Additional context about the error
            recoverable: Whether the error can be recovered from
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.recoverable = recoverable
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/API responses"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp.isoformat()
        }
    
    def __str__(self) -> str:
        context_str = f" | Context: {self.context}" if self.context else ""
        return f"[{self.error_code}] {self.message}{context_str}"


# ==================== Configuration Exceptions ====================

class ConfigurationError(AgentMeshException):
    """Raised when there's a configuration problem"""
    
    def __init__(self, message: str, missing_key: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        if missing_key:
            ctx['missing_key'] = missing_key
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            context=ctx,
            recoverable=False  # ← Make sure this is False!
        )


class MissingAPIKeyError(ConfigurationError):
    """Raised when a required API key is missing"""
    
    def __init__(self, api_name: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Missing API key for {api_name}. Please set it in .env file.",
            missing_key=f"{api_name.upper()}_API_KEY",
            context=context
        )


# ==================== Tool Exceptions ====================

class ToolException(AgentMeshException):
    """Base exception for tool-related errors"""
    
    def __init__(
        self, 
        tool_name: str, 
        message: str, 
        error_code: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        ctx = context or {}
        ctx['tool_name'] = tool_name
        super().__init__(
            message=message,
            error_code=f"TOOL_{error_code}",
            context=ctx,
            recoverable=recoverable
        )


class ToolTimeoutError(ToolException):
    """Raised when a tool operation times out"""
    
    def __init__(self, tool_name: str, timeout_seconds: int, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx['timeout_seconds'] = timeout_seconds
        super().__init__(
            tool_name=tool_name,
            message=f"Tool '{tool_name}' timed out after {timeout_seconds} seconds",
            error_code="TIMEOUT",
            context=ctx
        )


class ToolExecutionError(ToolException):
    """Raised when a tool fails to execute"""
    
    def __init__(self, tool_name: str, reason: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx['reason'] = reason
        super().__init__(
            tool_name=tool_name,
            message=f"Tool '{tool_name}' execution failed: {reason}",
            error_code="EXECUTION_FAILED",
            context=ctx
        )


class RateLimitError(ToolException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, tool_name: str, retry_after: Optional[int] = None, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        if retry_after:
            ctx['retry_after_seconds'] = retry_after
        super().__init__(
            tool_name=tool_name,
            message=f"Rate limit exceeded for '{tool_name}'",
            error_code="RATE_LIMIT",
            context=ctx
        )


class InvalidURLError(ToolException):
    """Raised when URL is invalid or blocked"""
    
    def __init__(self, url: str, reason: str = "Invalid or blocked URL", context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx.update({'url': url, 'reason': reason})
        super().__init__(
            tool_name="url_fetch",
            message=f"Invalid URL: {url}. {reason}",
            error_code="INVALID_URL",
            context=ctx,
            recoverable=False
        )


class DomainNotAllowedError(InvalidURLError):
    """Raised when domain is not in allowlist"""
    
    def __init__(self, url: str, domain: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            url=url,
            reason=f"Domain '{domain}' is not in the allowed domains list",
            context=context
        )


# ==================== Agent Exceptions ====================

class AgentException(AgentMeshException):
    """Base exception for agent-related errors"""
    
    def __init__(
        self, 
        agent_name: str, 
        message: str, 
        error_code: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        ctx = context or {}
        ctx['agent_name'] = agent_name
        super().__init__(
            message=message,
            error_code=f"AGENT_{error_code}",
            context=ctx,
            recoverable=recoverable
        )


class PlanningError(AgentException):
    """Raised when planner agent fails to create a valid plan"""
    
    def __init__(self, reason: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx['reason'] = reason
        super().__init__(
            agent_name="planner",
            message=f"Failed to create plan: {reason}",
            error_code="PLANNING_FAILED",
            context=ctx
        )


class ResearchError(AgentException):
    """Raised when research agent fails to find information"""
    
    def __init__(self, query: str, reason: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx.update({'query': query, 'reason': reason})
        super().__init__(
            agent_name="research",
            message=f"Research failed for query '{query}': {reason}",
            error_code="RESEARCH_FAILED",
            context=ctx
        )


class VerificationError(AgentException):
    """Raised when verification agent finds inconsistencies"""
    
    def __init__(self, reason: str, claims_checked: int = 0, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx.update({'reason': reason, 'claims_checked': claims_checked})
        super().__init__(
            agent_name="verification",
            message=f"Verification failed: {reason}",
            error_code="VERIFICATION_FAILED",
            context=ctx
        )


class SynthesisError(AgentException):
    """Raised when synthesis agent cannot create answer"""
    
    def __init__(self, reason: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx['reason'] = reason
        super().__init__(
            agent_name="synthesis",
            message=f"Failed to synthesize answer: {reason}",
            error_code="SYNTHESIS_FAILED",
            context=ctx
        )


class LowConfidenceError(AgentException):
    """Raised when answer confidence is too low"""
    
    def __init__(self, confidence: float, threshold: float, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx.update({'confidence': confidence, 'threshold': threshold})
        super().__init__(
            agent_name="reflection",
            message=f"Answer confidence ({confidence:.2f}) below threshold ({threshold:.2f})",
            error_code="LOW_CONFIDENCE",
            context=ctx,
            recoverable=True
        )


# ==================== Memory Exceptions ====================

class MemoryException(AgentMeshException):
    """Base exception for memory-related errors"""
    
    def __init__(
        self, 
        message: str, 
        memory_type: str, 
        error_code: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        ctx = context or {}
        ctx['memory_type'] = memory_type
        super().__init__(
            message=message,
            error_code=f"MEMORY_{error_code}",
            context=ctx,
            recoverable=recoverable
        )


class MemoryStorageError(MemoryException):
    """Raised when memory storage operation fails"""
    
    def __init__(self, memory_type: str, operation: str, reason: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx.update({'operation': operation, 'reason': reason})
        super().__init__(
            message=f"Memory storage failed: {operation} - {reason}",
            memory_type=memory_type,
            error_code="STORAGE_FAILED",
            context=ctx
        )


class MemoryRetrievalError(MemoryException):
    """Raised when memory retrieval fails"""
    
    def __init__(self, memory_type: str, query: str, reason: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx.update({'query': query, 'reason': reason})
        super().__init__(
            message=f"Memory retrieval failed: {reason}",
            memory_type=memory_type,
            error_code="RETRIEVAL_FAILED",
            context=ctx
        )


# ==================== LLM Exceptions ====================

class LLMException(AgentMeshException):
    """Base exception for LLM-related errors"""
    
    def __init__(
        self, 
        message: str, 
        provider: str, 
        error_code: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        ctx = context or {}
        ctx['provider'] = provider
        super().__init__(
            message=message,
            error_code=f"LLM_{error_code}",
            context=ctx,
            recoverable=recoverable
        )


class LLMConnectionError(LLMException):
    """Raised when cannot connect to LLM service"""
    
    def __init__(self, provider: str, url: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx['url'] = url
        super().__init__(
            message=f"Cannot connect to {provider} at {url}",
            provider=provider,
            error_code="CONNECTION_FAILED",
            context=ctx
        )


class LLMResponseError(LLMException):
    """Raised when LLM returns invalid response"""
    
    def __init__(self, provider: str, reason: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx['reason'] = reason
        super().__init__(
            message=f"Invalid LLM response: {reason}",
            provider=provider,
            error_code="INVALID_RESPONSE",
            context=ctx
        )


# ==================== Orchestration Exceptions ====================

class OrchestrationException(AgentMeshException):
    """Base exception for orchestration errors"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        super().__init__(
            message=message,
            error_code=f"ORCHESTRATION_{error_code}",
            context=context or {},
            recoverable=recoverable
        )


class MaxRetriesExceeded(OrchestrationException):
    """Raised when maximum retry attempts are exceeded"""
    
    def __init__(self, operation: str, max_retries: int, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx.update({'operation': operation, 'max_retries': max_retries})
        super().__init__(
            message=f"Maximum retries ({max_retries}) exceeded for operation: {operation}",
            error_code="MAX_RETRIES",
            context=ctx,
            recoverable=False
        )


class QueryTimeoutError(OrchestrationException):
    """Raised when query processing times out"""
    
    def __init__(self, query_id: str, timeout_seconds: int, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx.update({'query_id': query_id, 'timeout_seconds': timeout_seconds})
        super().__init__(
            message=f"Query {query_id} timed out after {timeout_seconds} seconds",
            error_code="QUERY_TIMEOUT",
            context=ctx,
            recoverable=False
        )


class InvalidStateError(OrchestrationException):
    """Raised when system is in invalid state"""
    
    def __init__(self, current_state: str, expected_state: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx.update({'current_state': current_state, 'expected_state': expected_state})
        super().__init__(
            message=f"Invalid state: expected '{expected_state}', got '{current_state}'",
            error_code="INVALID_STATE",
            context=ctx,
            recoverable=False
        )


# ==================== Validation Exceptions ====================

class ValidationException(AgentMeshException):
    """Base exception for validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        if field:
            ctx['field'] = field
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            context=ctx,
            recoverable=False
        )


class InvalidQueryError(ValidationException):
    """Raised when query is invalid"""
    
    def __init__(self, query: str, reason: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx.update({'query': query, 'reason': reason})
        super().__init__(
            message=f"Invalid query: {reason}",
            context=ctx
        )


class InvalidParameterError(ValidationException):
    """Raised when parameter is invalid"""
    
    def __init__(self, param_name: str, param_value: Any, reason: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx.update({'param_name': param_name, 'param_value': str(param_value), 'reason': reason})
        super().__init__(
            message=f"Invalid parameter '{param_name}': {reason}",
            field=param_name,
            context=ctx
        )


# ==================== Helper Functions ====================

def handle_exception(exception: Exception, logger) -> Dict[str, Any]:
    """
    Handle exception and return error info
    
    Args:
        exception: The exception to handle
        logger: Logger instance
        
    Returns:
        Dictionary with error information
    """
    if isinstance(exception, AgentMeshException):
        logger.error(
            f"AgentMesh Error: {exception.message}",
            error_code=exception.error_code,
            **exception.context
        )
        return exception.to_dict()
    else:
        # Unexpected exception
        logger.error(
            f"Unexpected error: {str(exception)}",
            error_type=type(exception).__name__
        )
        return {
            "error_type": type(exception).__name__,
            "error_code": "UNEXPECTED_ERROR",
            "message": str(exception),
            "context": {},
            "recoverable": False,
            "timestamp": datetime.now().isoformat()
        }


def is_recoverable(exception: Exception) -> bool:
    """
    Check if exception is recoverable
    
    Args:
        exception: Exception to check
        
    Returns:
        True if recoverable, False otherwise
    """
    if isinstance(exception, AgentMeshException):
        return exception.recoverable
    return False
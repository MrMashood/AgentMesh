"""
Test exception handling system
"""

from .exceptions import (
    AgentMeshException,
    DomainNotAllowedError,
    MissingAPIKeyError,
    PlanningError,
    ToolTimeoutError,
    LowConfidenceError,
    MemoryStorageError,
    LLMConnectionError,
    MaxRetriesExceeded,
    QueryTimeoutError,
    InvalidQueryError,
    ResearchError,
    ToolException,
    AgentException,
    MemoryException,
    LLMException,
    OrchestrationException,
    ValidationException,
    InvalidURLError,
    handle_exception,
    is_recoverable
)
from .logger import logger

def test_configuration_errors():
    print("TEST 1: Configuration Errors")
    
    try:
        raise MissingAPIKeyError("TAVILY")
    except AgentMeshException as e:
        print(f"Caught: {e}")
        print(f"   Recoverable: {e.recoverable}")
        print(f"   Error dict: {e.to_dict()}")


def test_tool_errors():
    print("TEST 2: Tool Errors")
    
    # Timeout
    try:
        raise ToolTimeoutError("search_web", timeout_seconds=10)
    except ToolException as e:
        print(f"Caught: {e}")
        print(f"   Recoverable: {e.recoverable}")
    
    # Domain not allowed
    try:
        raise DomainNotAllowedError(
            url="https://example.com/page",
            domain="example.com"
        )
    except InvalidURLError as e:
        print(f"Caught: {e}")
        print(f"   Recoverable: {e.recoverable}")


def test_agent_errors():
    print("TEST 3: Agent Errors")
    
    # Planning error
    try:
        raise PlanningError("Could not decompose query into steps")
    except AgentException as e:
        print(f"Caught: {e}")
        print(f"   Agent: {e.context.get('agent_name')}")
    
    # Low confidence
    try:
        raise LowConfidenceError(confidence=0.65, threshold=0.8)
    except AgentException as e:
        print(f"Caught: {e}")
        print(f"   Confidence: {e.context.get('confidence')}")
        print(f"   Recoverable: {e.recoverable}")


def test_memory_errors():
    print("TEST 4: Memory Errors")
    
    try:
        raise MemoryStorageError(
            memory_type="long_term",
            operation="save",
            reason="Disk full"
        )
    except MemoryException as e:
        print(f"Caught: {e}")
        print(f"   Memory type: {e.context.get('memory_type')}")


def test_llm_errors():
    print("TEST 5: LLM Errors")
    
    try:
        raise LLMConnectionError(
            provider="ollama",
            url="http://localhost:11434"
        )
    except LLMException as e:
        print(f"Caught: {e}")
        print(f"   Provider: {e.context.get('provider')}")


def test_orchestration_errors():
    print("TEST 6: Orchestration Errors")
    
    # Max retries
    try:
        raise MaxRetriesExceeded(operation="verify_claims", max_retries=3)
    except OrchestrationException as e:
        print(f"Caught: {e}")
        print(f"   Recoverable: {e.recoverable}")
    
    # Query timeout
    try:
        raise QueryTimeoutError(query_id="query_123", timeout_seconds=120)
    except OrchestrationException as e:
        print(f"Caught: {e}")


def test_validation_errors():
    print("TEST 7: Validation Errors")
    
    try:
        raise InvalidQueryError(
            query="",
            reason="Query cannot be empty"
        )
    except ValidationException as e:
        print(f" Caught: {e}")
        print(f"   Recoverable: {e.recoverable}")


def test_exception_handling():
    print("TEST 8: Exception Handler Function")
    
    # AgentMesh exception
    try:
        raise ResearchError(query="test query", reason="No results found")
    except Exception as e:
        error_info = handle_exception(e, logger)
        print(" Handled AgentMesh exception")
        print(f"   Error type: {error_info['error_type']}")
        print(f"   Error code: {error_info['error_code']}")
    
    # Regular exception
    try:
        raise ValueError("Some unexpected error")
    except Exception as e:
        error_info = handle_exception(e, logger)
        print(" Handled regular exception")
        print(f"   Error type: {error_info['error_type']}")


def test_is_recoverable():
    print("TEST 9: Recoverable Check")
    
    recoverable_errors = [
        ToolTimeoutError("search", 10),
        LowConfidenceError(0.5, 0.8),
        ResearchError("test", "timeout")
    ]
    
    non_recoverable_errors = [
        MissingAPIKeyError("TAVILY"),
        MaxRetriesExceeded("operation", 3),
        InvalidQueryError("", "empty")
    ]
    
    print("Recoverable errors:")
    for error in recoverable_errors:
        print(f"  {error.__class__.__name__}: {is_recoverable(error)}")
    
    print("\nNon-recoverable errors:")
    for error in non_recoverable_errors:
        print(f"  {error.__class__.__name__}: {is_recoverable(error)}")


if __name__ == "__main__":
    print("AgentMesh Exception Handling Test")
    
    test_configuration_errors()
    test_tool_errors()
    test_agent_errors()
    test_memory_errors()
    test_llm_errors()
    test_orchestration_errors()
    test_validation_errors()
    test_exception_handling()
    test_is_recoverable()
    
    print("All exception tests completed!")
from logger import logger, get_agent_logger, LogTimer, log_execution
from config import settings
import time

# Test 1: Basic logging
def test_basic_logging():
    print("\n" + "="*60)
    print("TEST 1: Basic Logging Levels")
    print("="*60)
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")


# Test 2: Agent-specific logging
def test_agent_logging():
    print("\n" + "="*60)
    print("TEST 2: Agent-Specific Logging")
    print("="*60)
    
    planner_logger = get_agent_logger("planner")
    research_logger = get_agent_logger("research")
    
    planner_logger.info("Creating research plan")
    research_logger.info("Executing web search")
    planner_logger.info("Plan completed")


# Test 3: Agent actions
def test_agent_actions():
    print("\n" + "="*60)
    print("TEST 3: Agent Actions")
    print("="*60)
    
    logger.agent_action("Planner", "Creating plan", {"steps": 3, "estimated_time": "30s"})
    logger.agent_action("Research", "Searching web", {"query": "WHO guidelines"})
    logger.agent_action("Verification", "Verifying claims", {"claims_count": 5})


# Test 4: Tool calls
def test_tool_calls():
    print("\n" + "="*60)
    print("TEST 4: Tool Calls")
    print("="*60)
    
    logger.tool_call("search_web", {"query": "heatwave guidelines", "max_results": 5})
    logger.tool_result("search_web", True, {"results_found": 5})
    
    logger.tool_call("open_url", {"url": "https://who.int/..."})
    logger.tool_result("open_url", True, {"content_length": "145KB"})


# Test 5: Query lifecycle
def test_query_lifecycle():
    print("\n" + "="*60)
    print("TEST 5: Query Lifecycle")
    print("="*60)
    
    query_id = "query_12345"
    
    logger.query_start("What are WHO heatwave guidelines?", query_id)
    
    time.sleep(0.5)  # Simulate work
    
    logger.info("Processing query...", step="research")
    logger.info("Verifying results...", step="verification")
    logger.info("Synthesizing answer...", step="synthesis")
    
    logger.query_complete(query_id, confidence=0.92, duration=2.5)


# Test 6: Timing context manager
def test_timing():
    print("\n" + "="*60)
    print("TEST 6: Operation Timing")
    print("="*60)
    
    with LogTimer(logger, "Web search operation"):
        time.sleep(1)  # Simulate work
        logger.info("Found 5 results")
    
    with LogTimer(logger, "URL fetch operation"):
        time.sleep(0.5)  # Simulate work
        logger.info("Fetched page content")


# Test 7: Decorator
@log_execution("test_function")
def sample_function(x, y):
    """Sample function to test decorator"""
    time.sleep(0.3)
    return x + y


def test_decorator():
    print("\n" + "="*60)
    print("TEST 7: Execution Decorator")
    print("="*60)
    
    result = sample_function(5, 10)
    logger.info(f"Function result: {result}")


# Test 8: Error handling
def test_error_handling():
    print("\n" + "="*60)
    print("TEST 8: Error Handling")
    print("="*60)
    
    try:
        with LogTimer(logger, "Operation that fails"):
            logger.info("Starting operation...")
            raise ValueError("Something went wrong!")
    except ValueError:
        logger.error("Caught error", error_type="ValueError")


if __name__ == "__main__":
    print("="*60)
    print("AgentMesh Logging System Test")
    print("="*60)
    
    test_basic_logging()
    test_agent_logging()
    test_agent_actions()
    test_tool_calls()
    test_query_lifecycle()
    test_timing()
    test_decorator()
    test_error_handling()
    
    print("\n" + "="*60)
    print("✅ All logging tests completed!")
    print("="*60)
    print(f"\n📁 Check logs in: {settings.LOG_DIR}")
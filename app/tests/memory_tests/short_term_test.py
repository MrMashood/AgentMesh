# from app.core import logger
# import time
from app.memory.short_term import get_short_term_memory


def test_basic_operations():
    print("TEST 1: Basic Operations")
    
    memory = get_short_term_memory()
    
    # Create query
    query_id = memory.create_query("What are WHO heatwave guidelines?")
    print(f"Created query: {query_id}")
    
    # Get state
    state = memory.get_query_state(query_id)
    print(f"Retrieved state: {state.query}")
    print(f"   Status: {state.status}")
    
    # Update status
    memory.update_status(query_id, "researching")
    print("Updated status to: researching")


def test_store_agent_outputs():
    print("TEST 2: Store Agent Outputs")
    
    memory = get_short_term_memory()
    query_id = memory.create_query("Test query for agent outputs")
    
    # Store plan
    plan = {
        'steps': [
            {'agent': 'research', 'task': 'Search WHO'},
            {'agent': 'verify', 'task': 'Verify claims'},
            {'agent': 'synthesize', 'task': 'Create answer'}
        ]
    }
    memory.store_plan(query_id, plan)
    print(f"Stored plan with {len(plan['steps'])} steps")
    
    # Store research findings
    findings = [
        {'url': 'https://who.int/...', 'content': 'WHO recommends...'},
        {'url': 'https://cdc.gov/...', 'content': 'CDC guidelines...'}
    ]
    memory.store_research_findings(query_id, findings)
    print(f"Stored {len(findings)} research findings")
    
    # Store verification
    verification = {
        'verified_claims_count': 5,
        'confidence': 0.9
    }
    memory.store_verification_results(query_id, verification)
    print("Stored verification results")
    
    # Store draft answer
    draft = "Based on WHO guidelines, hospitals should maintain cooling systems..."
    memory.store_draft_answer(query_id, draft)
    print(f"Stored draft answer ({len(draft)} chars)")
    
    # Store reflection
    reflection = {
        'confidence': 0.92,
        'decision': 'accept',
        'feedback': []
    }
    memory.store_reflection_feedback(query_id, reflection)
    print(f"Stored reflection (confidence: {reflection['confidence']})")
    
    # Get final state
    state = memory.get_query_state(query_id)
    print("\nFinal state:")
    print(f"   Plan steps: {len(state.plan['steps'])}")
    print(f"   Research findings: {len(state.research_findings)}")
    print(f"   Sources: {len(state.sources)}")
    print(f"   Confidence: {state.confidence_score}")


def test_tool_call_tracking():
    print("TEST 3: Tool Call Tracking")
    
    memory = get_short_term_memory()
    query_id = memory.create_query("Test query for tool tracking")
    
    # Record tool calls
    memory.record_tool_call(
        query_id,
        "search_web",
        {"query": "WHO guidelines", "max_results": 5},
        [{"title": "Result 1"}, {"title": "Result 2"}]
    )
    print("Recorded search_web tool call")
    
    memory.record_tool_call(
        query_id,
        "open_url",
        {"url": "https://who.int/..."},
        "<html>...</html>"
    )
    print("Recorded open_url tool call")
    
    state = memory.get_query_state(query_id)
    print(f"\nTool calls recorded: {len(state.tool_calls)}")
    for call in state.tool_calls:
        print(f"   - {call['tool']}: {call['params']}")


def test_error_tracking():
    print("TEST 4: Error Tracking")
    
    memory = get_short_term_memory()
    query_id = memory.create_query("Test query for error tracking")
    
    # Record errors
    try:
        raise ValueError("Test error from research agent")
    except Exception as e:
        memory.record_error(query_id, e, "research")
        print("Recorded error from research agent")
    
    try:
        raise TimeoutError("Test timeout from verification")
    except Exception as e:
        memory.record_error(query_id, e, "verification")
        print("Recorded error from verification agent")
    
    state = memory.get_query_state(query_id)
    print(f"\nErrors recorded: {len(state.errors)}")
    for error in state.errors:
        print(f"   - {error['agent']}: {error['error_type']}")


def test_retry_tracking():
    print("TEST 5: Retry Tracking")
    
    memory = get_short_term_memory()
    query_id = memory.create_query("Test query for retry tracking")
    
    print(f"Initial retry count: {memory.get_query_state(query_id).retry_count}")
    
    memory.increment_retry(query_id)
    print(f"After 1st retry: {memory.get_query_state(query_id).retry_count}")
    
    memory.increment_retry(query_id)
    print(f"After 2nd retry: {memory.get_query_state(query_id).retry_count}")
    
    memory.increment_retry(query_id)
    print(f"After 3rd retry: {memory.get_query_state(query_id).retry_count}")


def test_memory_stats():
    print("TEST 6: Memory Statistics")
    
    memory = get_short_term_memory()
    
    # Get stats
    stats = memory.get_memory_stats()
    
    print("Memory Statistics:")
    print(f"   Total queries: {stats['total_queries']}")
    print(f"   Total tool calls: {stats['total_tool_calls']}")
    print(f"   Total errors: {stats['total_errors']}")
    print("\n   Queries by status:")
    for status, count in stats['queries_by_status'].items():
        print(f"      {status}: {count}")


def test_cleanup():
    print("TEST 7: Memory Cleanup")
    
    memory = get_short_term_memory()
    
    initial_count = len(memory.get_all_queries())
    print(f"Queries before cleanup: {initial_count}")
    
    # Clear one query
    if initial_count > 0:
        query_ids = memory.get_all_queries()
        memory.clear_query(query_ids[0])
        print("Cleared one query")
        print(f"   Queries remaining: {len(memory.get_all_queries())}")
    
    # Clear all
    memory.clear_all()
    print("Cleared all queries")
    print(f"   Queries remaining: {len(memory.get_all_queries())}")


if __name__ == "__main__":
    print("Testing Short-Term Memory System")
    
    test_basic_operations()
    test_store_agent_outputs()
    test_tool_call_tracking()
    test_error_tracking()
    test_retry_tracking()
    test_memory_stats()
    test_cleanup()
    
    print("All tests completed!")
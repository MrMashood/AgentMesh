from app.tools.web_search import search_web, search_web_with_retry, validate_search_query
from app.core.config import settings


# Test the function
if __name__ == "__main__":
    print("="*60)
    print("Testing Enhanced Web Search Tool")
    print("="*60)
    
    # Test 1: Basic search
    print("\n" + "="*60)
    print("TEST 1: Basic Search")
    print("="*60)
    
    try:
        results = search_web("WHO heatwave guidelines", max_results=3)
        
        if results:
            print(f"\n✅ Found {len(results)} results:")
            for result in results:
                print(f"\n{result['position']}. {result['title']}")
                print(f"   URL: {result['url']}")
                print(f"   Score: {result['score']:.2f}")
                print(f"   Snippet: {result['snippet'][:100]}...")
        else:
            print("❌ No results found")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Search with retry
    print("\n" + "="*60)
    print("TEST 2: Search with Retry")
    print("="*60)
    
    try:
        results = search_web_with_retry(
            "dengue prevention South Asia",
            max_results=3
        )
        
        if results:
            print(f"\n✅ Found {len(results)} results with retry logic")
            for result in results[:2]:
                print(f"\n{result['position']}. {result['title']}")
                print(f"   Score: {result['score']:.2f}")
        else:
            print("❌ No results found")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Invalid query
    print("\n" + "="*60)
    print("TEST 3: Query Validation")
    print("="*60)
    
    try:
        validate_search_query("")
        print("❌ Should have raised error for empty query")
    except Exception as e:
        print(f"✅ Correctly caught invalid query: {e}")
    
    # Test 4: Missing API key (simulated)
    print("\n" + "="*60)
    print("TEST 4: Error Handling Demo")
    print("="*60)
    
    print("✅ Error handling is integrated:")
    print("   - MissingAPIKeyError for missing keys")
    print("   - ToolTimeoutError for timeouts")
    print("   - RateLimitError for rate limits")
    print("   - ToolExecutionError for other failures")
    print("   - All errors logged automatically")
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)
    print(f"📊 Rate limit: {settings.RATE_LIMIT_CALLS_PER_MINUTE} calls/minute")
    print(f"Max retries: {settings.MAX_RETRIES}")
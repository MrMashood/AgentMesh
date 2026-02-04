# Test the functions
from app.tools.url_fetch import is_allowed_domain, fetch_and_extract_with_retry, extract_text, open_url, DomainNotAllowedError, InvalidURLError
from app.core.config import settings

if __name__ == "__main__":
    print("Testing Enhanced URL Fetch Tool")
    
    # Test 1: Domain checking
    print("TEST 1: Domain Validation")
    
    test_urls = [
        ("https://www.who.int/news", True),
        ("https://www.cdc.gov/health", True),
        ("https://www.example.com/page", False),
        ("https://www.google.com/search", False),
    ]
    
    for url, should_allow in test_urls:
        allowed = is_allowed_domain(url)
        status = "PASS" if allowed == should_allow else " FAIL"
        action = "ALLOWED" if allowed else "BLOCKED"
        print(f"{status}: {action} - {url}")
    
    # Test 2: Basic URL fetch
    print("TEST 2: Basic URL Fetch")
    
    try:
        test_url = "https://httpbin.org/html"
        html = open_url(test_url)
        
        if html:
            print(f"Successfully fetched HTML ({len(html)} characters)")
            
            text = extract_text(html, max_length=500)
            if text:
                print(f"Successfully extracted {len(text)} characters")
                print(f"Preview: {text[:200]}...")
        else:
            print("Failed to fetch")
    
    except Exception as e:
        print(f"⚠️  Error: {e}")
    
    # Test 3: Domain blocking
    print("\n" + "="*60)
    print("TEST 3: Domain Blocking")
    print("="*60)
    
    try:
        blocked_url = "https://example.com/page"
        html = open_url(blocked_url)
        print("❌ Should have blocked this domain!")
    
    except DomainNotAllowedError as e:
        print(f"✅ Correctly blocked: {e}")
    
    except Exception as e:
        print(f"❌ Wrong exception: {e}")
    
    # Test 4: Invalid URL
    print("\n" + "="*60)
    print("TEST 4: Invalid URL Handling")
    print("="*60)
    
    try:
        invalid_url = "not-a-url"
        html = open_url(invalid_url)
        print("❌ Should have rejected invalid URL!")
    
    except InvalidURLError as e:
        print(f"✅ Correctly rejected: {e}")
    
    except Exception as e:
        print(f"⚠️  Different error: {e}")
    
    # Test 5: Fetch and extract combined
    print("\n" + "="*60)
    print("TEST 5: Fetch and Extract (with retry)")
    print("="*60)
    
    try:
        test_url = "https://httpbin.org/html"
        text = fetch_and_extract_with_retry(test_url, max_text_length=300)
        
        if text:
            print("✅ Successfully fetched and extracted")
            print(f"📄 Text length: {len(text)} characters")
            print(f"📄 Preview: {text[:150]}...")
        else:
            print("❌ Failed")
    
    except Exception as e:
        print(f"⚠️  Error: {e}")
    
    # Test 6: Configuration integration
    print("\n" + "="*60)
    print("TEST 6: Configuration Integration")
    print("="*60)
    
    print("✅ Using configuration:")
    print(f"   - Allowed domains: {len(settings.ALLOWED_DOMAINS)} domains")
    print(f"   - Timeout: {settings.URL_FETCH_TIMEOUT}s")
    print(f"   - Max page size: {settings.MAX_PAGE_SIZE_MB}MB")
    print(f"   - Max retries: {settings.MAX_RETRIES}")
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)
    print(f"\n📁 Check logs in: {settings.LOG_DIR}")
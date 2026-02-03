import requests
from typing import Optional
from bs4 import BeautifulSoup
import time

from app.core import (
    settings,
    logger,
    ToolException,
    ToolTimeoutError,
    ToolExecutionError,
    InvalidURLError,
    DomainNotAllowedError,
    log_tool_call,
    log_tool_result,
    InvalidParameterError
)


def is_allowed_domain(url: str) -> bool:
    """
    Check if URL is from an allowed domain
    
    Args:
        url: URL to check
        
    Returns:
        True if domain is allowed, False otherwise
    """
    if not url:
        return False
    
    url_lower = url.lower()
    
    # Check against configured allowed domains
    for domain in settings.ALLOWED_DOMAINS:
        if domain.lower() in url_lower:
            return True
    
    return False


def extract_domain(url: str) -> str:
    """
    Extract domain from URL
    
    Args:
        url: Full URL
        
    Returns:
        Domain name
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split('/')[0]
    except Exception:
        return "unknown"


def open_url(
    url: str,
    timeout: Optional[int] = None,
    retry_count: int = 0
) -> Optional[str]:
    """
    Fetch the full HTML content of a webpage
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds (default from config)
        retry_count: Current retry attempt (internal use)
        
    Returns:
        HTML content as string, or None if failed
        
    Raises:
        InvalidURLError: If URL is invalid
        DomainNotAllowedError: If domain not in allowlist
        ToolTimeoutError: If request times out
        ToolExecutionError: If fetch fails
    """
    # Use config default if not specified
    if timeout is None:
        timeout = settings.URL_FETCH_TIMEOUT
    
    # Validate URL
    if not url or not url.strip():
        raise InvalidParameterError(
            param_name="url",
            param_value=url,
            reason="URL cannot be empty"
        )
    
    if not url.startswith(('http://', 'https://')):
        raise InvalidURLError(
            url=url,
            reason="URL must start with http:// or https://"
        )
    
    # Security check: only allowed domains
    if not is_allowed_domain(url):
        domain = extract_domain(url)
        logger.warning(
            "Domain not in allowlist",
            url=url,
            domain=domain
        )
        raise DomainNotAllowedError(url=url, domain=domain)
    
    # Log the fetch
    log_tool_call("open_url", url=url, timeout=timeout)
    
    try:
        logger.info("Fetching URL", url=url, timeout=timeout)
        
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        # Fetch the page
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Check size (limit from config)
        content_length = len(response.content)
        max_size_bytes = settings.MAX_PAGE_SIZE_MB * 1024 * 1024
        
        if content_length > max_size_bytes:
            logger.warning(
                "Page too large",
                url=url,
                size_mb=content_length / 1024 / 1024,
                max_mb=settings.MAX_PAGE_SIZE_MB
            )
            raise ToolExecutionError(
                tool_name="open_url",
                reason=f"Page too large: {content_length / 1024 / 1024:.1f}MB (max: {settings.MAX_PAGE_SIZE_MB}MB)",
                context={'url': url, 'size_bytes': content_length}
            )
        
        logger.info(
            "Successfully fetched URL",
            url=url,
            size_kb=content_length / 1024,
            status_code=response.status_code
        )
        log_tool_result("open_url", success=True, size_kb=content_length / 1024)
        
        return response.text
    
    except requests.Timeout:
        logger.error("URL fetch timeout", url=url, timeout=timeout)
        log_tool_result("open_url", success=False, error="timeout")
        raise ToolTimeoutError(
            tool_name="open_url",
            timeout_seconds=timeout,
            context={'url': url}
        )
    
    except requests.HTTPError as e:
        logger.error(
            "HTTP error fetching URL",
            url=url,
            status_code=e.response.status_code,
            error=str(e)
        )
        log_tool_result("open_url", success=False, error=f"HTTP {e.response.status_code}")
        raise ToolExecutionError(
            tool_name="open_url",
            reason=f"HTTP {e.response.status_code}: {str(e)}",
            context={'url': url, 'status_code': e.response.status_code}
        )
    
    except requests.RequestException as e:
        logger.error("Request error fetching URL", url=url, error=str(e))
        log_tool_result("open_url", success=False, error=str(e))
        raise ToolExecutionError(
            tool_name="open_url",
            reason=str(e),
            context={'url': url}
        )
    
    except Exception as e:
        logger.error(
            "Unexpected error fetching URL",
            url=url,
            error=str(e),
            error_type=type(e).__name__
        )
        log_tool_result("open_url", success=False, error=str(e))
        raise ToolExecutionError(
            tool_name="open_url",
            reason=f"Unexpected error: {str(e)}",
            context={'url': url}
        )


def extract_text(html: str, max_length: Optional[int] = None) -> str:
    """
    Extract clean text from HTML
    
    Removes:
    - Scripts and styles
    - Navigation menus
    - Ads
    - Footers
    
    Args:
        html: HTML content
        max_length: Maximum text length to return (default: 10000)
        
    Returns:
        Clean text content
        
    Raises:
        ToolExecutionError: If extraction fails
    """
    if max_length is None:
        max_length = 10000
    
    log_tool_call("extract_text", html_length=len(html), max_length=max_length)
    
    try:
        logger.debug("Extracting text from HTML", html_size=len(html))
        
        # Parse HTML - using html.parser (built-in, no external deps)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button']):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = ' '.join(lines)
        
        # Limit length
        original_length = len(text)
        if len(text) > max_length:
            text = text[:max_length] + "..."
            logger.debug(
                "Text truncated",
                original_length=original_length,
                truncated_length=max_length
            )
        
        logger.info(
            "Text extraction successful",
            extracted_chars=len(text),
            truncated=original_length > max_length
        )
        log_tool_result("extract_text", success=True, text_length=len(text))
        
        return text
    
    except Exception as e:
        logger.error(
            "Error extracting text",
            error=str(e),
            error_type=type(e).__name__
        )
        log_tool_result("extract_text", success=False, error=str(e))
        raise ToolExecutionError(
            tool_name="extract_text",
            reason=f"Text extraction failed: {str(e)}",
            context={'html_length': len(html)}
        )


def fetch_and_extract(
    url: str,
    timeout: Optional[int] = None,
    max_text_length: Optional[int] = None
) -> Optional[str]:
    """
    Convenience function: fetch URL and extract text in one step
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        max_text_length: Maximum text length to return
        
    Returns:
        Extracted text, or None if failed
        
    Raises:
        Same exceptions as open_url and extract_text
    """
    logger.info("Fetch and extract", url=url)
    
    html = open_url(url, timeout=timeout)
    
    if html:
        return extract_text(html, max_length=max_text_length)
    
    return None


def fetch_and_extract_with_retry(
    url: str,
    timeout: Optional[int] = None,
    max_text_length: Optional[int] = None,
    max_retries: Optional[int] = None
) -> Optional[str]:
    """
    Fetch and extract with automatic retry on recoverable failures
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        max_text_length: Maximum text length
        max_retries: Maximum retry attempts (default from config)
        
    Returns:
        Extracted text or None
        
    Raises:
        Same as fetch_and_extract after all retries exhausted
    """
    if max_retries is None:
        max_retries = settings.MAX_RETRIES
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(
                    "Retrying fetch",
                    url=url,
                    attempt=attempt,
                    max_retries=max_retries,
                    wait_seconds=wait_time
                )
                time.sleep(wait_time)
            
            return fetch_and_extract(url, timeout, max_text_length)
        
        except ToolTimeoutError as e:
            # Timeout is recoverable
            last_error = e
            logger.warning(
                "Timeout, will retry",
                url=url,
                attempt=attempt,
                error=str(e)
            )
            
            if attempt == max_retries:
                logger.error(
                    "Max retries exceeded",
                    url=url,
                    attempts=attempt + 1
                )
                raise
        
        except (DomainNotAllowedError, InvalidURLError) as e:
            # These are NOT recoverable
            logger.error("Non-recoverable error", url=url, error=str(e))
            raise
        
        except ToolException as e:
            # Other tool exceptions might be recoverable
            if e.recoverable and attempt < max_retries:
                last_error = e
                logger.warning(
                    "Recoverable error, will retry",
                    url=url,
                    attempt=attempt,
                    error=str(e)
                )
            else:
                logger.error("Non-recoverable error", url=url, error=str(e))
                raise
    
    # Should not reach here, but just in case
    if last_error:
        raise last_error
    
    return None


# Test the functions
if __name__ == "__main__":
    print("="*60)
    print("Testing Enhanced URL Fetch Tool")
    print("="*60)
    
    # Test 1: Domain checking
    print("\n" + "="*60)
    print("TEST 1: Domain Validation")
    print("="*60)
    
    test_urls = [
        ("https://www.who.int/news", True),
        ("https://www.cdc.gov/health", True),
        ("https://www.example.com/page", False),
        ("https://www.google.com/search", False),
    ]
    
    for url, should_allow in test_urls:
        allowed = is_allowed_domain(url)
        status = "✅ PASS" if allowed == should_allow else "❌ FAIL"
        action = "ALLOWED" if allowed else "BLOCKED"
        print(f"{status}: {action} - {url}")
    
    # Test 2: Basic URL fetch
    print("\n" + "="*60)
    print("TEST 2: Basic URL Fetch")
    print("="*60)
    
    try:
        test_url = "https://httpbin.org/html"
        html = open_url(test_url)
        
        if html:
            print(f"✅ Successfully fetched HTML ({len(html)} characters)")
            
            text = extract_text(html, max_length=500)
            if text:
                print(f"✅ Extracted {len(text)} characters")
                print(f"📄 Preview: {text[:200]}...")
        else:
            print("❌ Failed to fetch")
    
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
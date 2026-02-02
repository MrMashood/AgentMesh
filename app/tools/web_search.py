import requests
from typing import List, Dict, Optional
import time
from datetime import datetime, timedelta

from app.core import (
    settings,
    logger,
    ToolException,
    ToolTimeoutError,
    ToolExecutionError,
    RateLimitError,
    MissingAPIKeyError,
    log_tool_call,
    log_tool_result
)


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls_per_minute: int):
        self.max_calls = max_calls_per_minute
        self.calls = []
    
    def can_call(self) -> bool:
        """Check if we can make another call"""
        now = datetime.now()
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < timedelta(minutes=1)]
        return len(self.calls) < self.max_calls
    
    def wait_if_needed(self):
        """Wait if rate limit reached"""
        if not self.can_call():
            wait_time = 60 - (datetime.now() - self.calls[0]).total_seconds()
            logger.warning(f"Rate limit reached. Waiting {wait_time}s...")
            time.sleep(wait_time)
    
    def record_call(self):
        """Record a call"""
        self.calls.append(datetime.now())


# Global rate limiter
rate_limiter = RateLimiter(settings.RATE_LIMIT_CALLS_PER_MINUTE)


def search_web(query: str,max_results: Optional[int] = None, retry_count: int = 0) -> List[Dict]:
    """
    Search the web using Tavily API
    
    Args:
        query: Search query string
        max_results: Maximum number of results (default from config)
        retry_count: Current retry attempt (internal use)
        
    Returns:
        List of dicts with title, url, snippet, score
        
    Raises:
        MissingAPIKeyError: If Tavily API key not configured
        RateLimitError: If rate limit exceeded
        ToolTimeoutError: If request times out
        ToolExecutionError: If search fails
    """
    # Use config default if not specified
    if max_results is None:
        max_results = settings.MAX_SEARCH_RESULTS
    
    # Validate API key
    if not settings.TAVILY_API_KEY:
        logger.error("Tavily API key not configured")
        raise MissingAPIKeyError("TAVILY")
    
    # Log the search
    log_tool_call("search_web", query=query, max_results=max_results)
    
    try:
        # Check rate limit
        rate_limiter.wait_if_needed()
        rate_limiter.record_call()
        
        logger.info("Searching web", query=query, max_results=max_results)
        
        # Call Tavily API
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False
        }
        
        response = requests.post(
            url,
            json=payload,
            timeout=settings.URL_FETCH_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        # Process results
        results = []
        for idx, result in enumerate(data.get('results', []), 1):
            results.append({
                'title': result.get('title', 'No title'),
                'url': result.get('url', ''),
                'snippet': result.get('content', 'No snippet'),
                'score': result.get('score', 0.0),
                'position': idx
            })
        
        logger.info(
            "Search successful",
            query=query,
            results_found=len(results)
        )
        log_tool_result("search_web", success=True, results_count=len(results))
        
        return results
    
    except requests.Timeout:
        logger.error(
            "Search timeout",
            query=query,
            timeout=settings.URL_FETCH_TIMEOUT
        )
        log_tool_result("search_web", success=False, error="timeout")
        raise ToolTimeoutError(
            tool_name="search_web",
            timeout_seconds=settings.URL_FETCH_TIMEOUT,
            context={'query': query}
        )
    
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            logger.error("Rate limit exceeded", query=query)
            log_tool_result("search_web", success=False, error="rate_limit")
            raise RateLimitError(
                tool_name="search_web",
                retry_after=60,
                context={'query': query}
            )
        else:
            logger.error(
                "HTTP error during search",
                query=query,
                status_code=e.response.status_code,
                error=str(e)
            )
            log_tool_result("search_web", success=False, error=str(e))
            raise ToolExecutionError(
                tool_name="search_web",
                reason=f"HTTP {e.response.status_code}: {str(e)}",
                context={'query': query}
            )
    
    except requests.RequestException as e:
        logger.error("Request error during search", query=query, error=str(e))
        log_tool_result("search_web", success=False, error=str(e))
        raise ToolExecutionError(
            tool_name="search_web",
            reason=str(e),
            context={'query': query}
        )
    
    except Exception as e:
        logger.error(
            "Unexpected error during search",
            query=query,
            error=str(e),
            error_type=type(e).__name__
        )
        log_tool_result("search_web", success=False, error=str(e))
        raise ToolExecutionError(
            tool_name="search_web",
            reason=f"Unexpected error: {str(e)}",
            context={'query': query}
        )


def search_web_with_retry(
    query: str,
    max_results: Optional[int] = None,
    max_retries: Optional[int] = None
) -> List[Dict]:
    """
    Search with automatic retry on recoverable failures
    
    Args:
        query: Search query string
        max_results: Maximum number of results
        max_retries: Maximum retry attempts (default from config)
        
    Returns:
        List of search results
        
    Raises:
        Same as search_web after all retries exhausted
    """
    if max_retries is None:
        max_retries = settings.MAX_RETRIES
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(
                    "Retrying search",
                    attempt=attempt,
                    max_retries=max_retries,
                    wait_seconds=wait_time
                )
                time.sleep(wait_time)
            
            return search_web(query, max_results, retry_count=attempt)
        
        except (ToolTimeoutError, RateLimitError) as e:
            # These are recoverable
            last_error = e
            logger.warning(
                "Recoverable error, will retry",
                attempt=attempt,
                error=str(e)
            )
            
            if attempt == max_retries:
                logger.error(
                    "Max retries exceeded",
                    query=query,
                    attempts=attempt + 1
                )
                raise
        
        except ToolException as e:
            # Other tool exceptions might not be recoverable
            if e.recoverable and attempt < max_retries:
                last_error = e
                logger.warning(
                    "Recoverable error, will retry",
                    attempt=attempt,
                    error=str(e)
                )
            else:
                logger.error("Non-recoverable error", error=str(e))
                raise
    
    # Should not reach here, but just in case
    if last_error:
        raise last_error
    
    return []


def validate_search_query(query: str) -> bool:
    """
    Validate search query
    
    Args:
        query: Query to validate
        
    Returns:
        True if valid
        
    Raises:
        InvalidParameterError: If query is invalid
    """
    from app.core import InvalidParameterError
    
    if not query or not query.strip():
        raise InvalidParameterError(
            param_name="query",
            param_value=query,
            reason="Query cannot be empty"
        )
    
    if len(query) > 500:
        raise InvalidParameterError(
            param_name="query",
            param_value=query,
            reason="Query too long (max 500 characters)"
        )
    
    return True

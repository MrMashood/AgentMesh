from .web_search import (
    search_web,
    search_web_with_retry,
    validate_search_query
)

from .url_fetch import (
    open_url,
    extract_text,
    fetch_and_extract,
    fetch_and_extract_with_retry,
    is_allowed_domain
)

__all__ = [
    # Web search
    'search_web',
    'search_web_with_retry',
    'validate_search_query',
    
    # URL fetch
    'open_url',
    'extract_text',
    'fetch_and_extract',
    'fetch_and_extract_with_retry',
    'is_allowed_domain'
]
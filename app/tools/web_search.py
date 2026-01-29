from typing import List, Dict
import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Get Tavily API key
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not TAVILY_API_KEY:
    print("⚠️  WARNING: TAVILY_API_KEY not found in .env file")
    print("   Please add: TAVILY_API_KEY=your_key_here")


def search_web(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search the web using Tavily API
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        List of dicts with title, url, snippet, score
    """
    if not TAVILY_API_KEY:
        print("❌ Tavily API key not initialized. Check your .env file.")
        return []
    
    try:
        print(f"🔍 Searching with Tavily: {query}")
        
        # Call Tavily API
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        results = []
        
        # Process Tavily results
        for idx, result in enumerate(data.get('results', []), 1):
            results.append({
                'title': result.get('title', 'No title'),
                'url': result.get('url', ''),
                'snippet': result.get('content', 'No snippet'),
                'score': result.get('score', 0.0),
                'position': idx
            })
        
        print(f"✅ Found {len(results)} results")
        return results
        
    except Exception as e:
        print(f"❌ Tavily search failed: {str(e)}")
        return []


# Test the function
if __name__ == "__main__":
    print("="*60)
    print("Testing Tavily Web Search Tool")
    print("="*60)
    
    if not TAVILY_API_KEY:
        print("\n❌ ERROR: No Tavily API key found!")
        print("Please:")
        print("1. Get API key from https://tavily.com")
        print("2. Create .env file in project root")
        print("3. Add: TAVILY_API_KEY=your_key_here")
        exit(1)
    
    # Test 1: Basic search
    # print("\n" + "="*60)
    # print("TEST 1: Basic Search - WHO Heatwave Guidelines")
    # print("="*60)
    # results = search_web("WHO heatwave guidelines for hospitals", max_results=3)
    
    # if results:
    #     for result in results:
    #         print(f"\n{result['position']}. {result['title']}")
    #         print(f"   URL: {result['url']}")
    #         print(f"   Score: {result['score']:.2f}")
    #         print(f"   Snippet: {result['snippet'][:150]}...")
    # else:
    #     print("No results found")
    
    
    # Test 2: Another query
    print("\n" + "="*60)
    print("TEST 2: Hospital Infection Control")
    print("="*60)
    results = search_web("hospital infection control protocols", max_results=2)
    
    if results:
        for result in results:
            print(f"\n{result['position']}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Score: {result['score']:.2f}")
            print(f"   Snippet: {result['snippet'][:150]}...")
    else:
        print("No results found")
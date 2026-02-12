"""
Test API Endpoints
"""

from fastapi.testclient import TestClient
from app.api.app import create_app

# Create test client
app = create_app()
client = TestClient(app)


def test_api():
    """Test API endpoints"""
    
    print("Testing API Endpoints")
    
    try:
        # Test 1: Root endpoint
        print("\nTest 1: Root Endpoint")
        response = client.get("/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert response.json()["status"] == "operational"
        print("Root endpoint working")
        
        # Test 2: Health check
        print("\nTest 2: Health Check")
        response = client.get("/api/v1/health")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Health Status: {data['status']}")
        print(f"Version: {data['version']}")
        print(f"Agents: {', '.join(data['agents_loaded'])}")
        assert response.status_code == 200
        assert data["status"] == "healthy"
        assert len(data["agents_loaded"]) == 5
        print("Health check passed")
        
        # Test 3: Query endpoint (simple)
        print("\nTest 3: Simple Query")
        query_data = {
            "query": "What is Python?",
            "enable_reflection": True
        }
        
        print(f"Sending query: '{query_data['query']}'")
        print("Processing... (this may take 15-30 seconds)")
        
        response = client.post("/api/v1/query", json=query_data)
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nQuery processed successfully!")
            print(f"   Query ID: {data['query_id']}")
            print(f"   Confidence: {data['confidence']:.2f}")
            print(f"   Answer: {data['answer'][:150]}...")
            print(f"   Sources: {len(data['citations'])}")
            print(f"   Key points: {len(data['key_points'])}")
            print(f"   Credibility: {data['quality']['credibility_level']}")
            
            assert "answer" in data
            assert data["confidence"] > 0
            assert len(data["citations"]) > 0
        else:
            print(f"Request failed: {response.json()}")
            assert False
        
        # Test 4: Query without reflection
        print("\nTest 4: Query Without Reflection")
        query_data_no_reflection = {
            "query": "What is MongoDB?",
            "enable_reflection": False
        }
        
        print(f"Sending query: '{query_data_no_reflection['query']}'")
        print("Processing without reflection...")
        
        response = client.post("/api/v1/query", json=query_data_no_reflection)
        
        if response.status_code == 200:
            data = response.json()
            print("\nQuery processed (no reflection)!")
            print(f"   Confidence: {data['confidence']:.2f}")
            print(f"   Reflection quality: {data['pipeline']['reflection_quality']}")
            assert data['pipeline']['reflection_quality'] is None
        
        # Test 5: Statistics
        print("\nTest 5: Statistics")
        response = client.get("/api/v1/stats")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Statistics retrieved:")
            print(f"   Total queries: {data['total_queries']}")
            print(f"   Successful: {data['successful_queries']}")
            print(f"   Success rate: {data['success_rate']}")
            print(f"   Avg time: {data['average_execution_time']:.2f}s")
        
        # Test 6: Invalid query (empty)
        print("\nTest 6: Invalid Query (Empty) ---")
        invalid_data = {"query": "", "enable_reflection": True}
        response = client.post("/api/v1/query", json=invalid_data)
        print(f"Status: {response.status_code}")
        assert response.status_code == 400
        print("Validation working - empty query rejected")
        
        # Test 7: Invalid query (too long)
        print("\nTest 7: Invalid Query (Too Long)")
        long_query = "A" * 1001  # Over 1000 char limit
        invalid_data = {"query": long_query, "enable_reflection": True}
        response = client.post("/api/v1/query", json=invalid_data)
        print(f"Status: {response.status_code}")
        assert response.status_code == 422  # Validation error
        print("Validation working - long query rejected")
        
        # Test 8: Reset statistics
        print("\nTest 8: Reset Statistics")
        response = client.post("/api/v1/stats/reset")
        print(f"Status: {response.status_code}")
        assert response.status_code == 200
        print("Statistics reset")
        
        # Verify reset
        response = client.get("/api/v1/stats")
        data = response.json()
        print(f"   Total queries after reset: {data['total_queries']}")
        
        print("\n" + "="*60)
        print("ALL API TESTS PASSED!")
        print("="*60)
        print("\n💡 API Features Tested:")
        print("   Root endpoint")
        print("   Health check")
        print("   Query processing")
        print("   Query without reflection")
        print("   Statistics endpoint")
        print("   Input validation")
        print("   Statistics reset")
        
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    test_api()
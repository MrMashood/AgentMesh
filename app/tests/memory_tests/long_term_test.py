"""
Test Long-Term Memory with MongoDB
"""

from app.memory.long_term import LongTermMemory, close_long_term_memory
# from datetime import datetime, timedelta
import time


def test_mongodb_long_term_memory():
    """Test MongoDB long-term memory operations"""

    print("Testing Long-Term Memory with MongoDB")
    
    try:
        # Initialize
        ltm = LongTermMemory()
        print("Connected to MongoDB")
        
        # Clear any existing test data
        print("\nClearing old test data...")
        ltm.clear_all_data()
        
        # Test 1: Save query
        print("\n Test 1: Save Query")
        ltm.save_query(
            query_id="q1",
            query_text="What is quantum computing?",
            response="Quantum computing uses quantum bits...",
            sources=["https://ibm.com/quantum", "https://nature.com/quantum"],
            confidence=0.92,
            metadata={"agent": "research", "language": "en"}
        )
        print("Query saved to MongoDB")
        
        # Small delay for MongoDB indexing
        time.sleep(0.5)
        
        # Test 2: Get query by ID
        print("\nTest 2: Get Query by ID")
        query = ltm.get_query_by_id("q1")
        if query:
            print(f" Retrieved query: {query['query_text'][:50]}...")
            print(f"   Confidence: {query['confidence']}")
        
        # Test 3: Save multiple queries
        print("\n Test 3: Save Multiple Queries ")
        ltm.save_query(
            query_id="q2",
            query_text="Explain machine learning",
            response="Machine learning is...",
            sources=["https://stanford.edu/ml"],
            confidence=0.88,
            metadata={"agent": "synthesis"}
        )
        ltm.save_query(
            query_id="q3",
            query_text="What is deep learning?",
            response="Deep learning uses neural networks...",
            sources=["https://mit.edu/dl"],
            confidence=0.95,
            metadata={"agent": "research"}
        )
        print("Multiple queries saved")
        
        # Test 4: Get query history
        print("\nTest 4: Get Query History")
        history = ltm.get_query_history(limit=5)
        print(f"Retrieved {len(history)} queries")
        for i, q in enumerate(history, 1):
            print(f"   {i}. {q['query_text'][:40]}... (confidence: {q['confidence']})")
        
        # Test 5: Search history
        print("\nTest 5: Search History")
        time.sleep(0.5)  # Wait for indexing
        results = ltm.search_history("quantum")
        print(f"Found {len(results)} queries matching 'quantum'")
        
        # Test 6: Save learnings
        print("\nTest 6: Save Learnings")
        ltm.save_learning(
            topic="quantum_computing",
            insight="IBM released 1000+ qubit processor in 2024",
            confidence=0.95,
            sources=["https://ibm.com"]
        )
        ltm.save_learning(
            topic="quantum_computing",
            insight="Quantum computers can break RSA encryption",
            confidence=0.88,
            sources=["https://nature.com"]
        )
        ltm.save_learning(
            topic="machine_learning",
            insight="GPT-4 has 1.76 trillion parameters",
            confidence=0.92,
            sources=["https://openai.com"]
        )
        print("Learnings saved")
        
        # Test 7: Get learnings
        print("\nTest 7: Get Learnings")
        learnings = ltm.get_learnings("quantum_computing")
        print(f"Retrieved {len(learnings)} learnings for 'quantum_computing'")
        for i, l in enumerate(learnings, 1):
            print(f"   {i}. {l['insight'][:60]}...")
        
        # Test 8: Get all topics
        print("\nTest 8: Get All Topics")
        topics = ltm.get_all_topics()
        print(f"Topics with learnings: {', '.join(topics)}")
        
        # Test 9: Update source scores
        print("\nTest 9: Update Source Scores")
        ltm.update_source_score("ibm.com", was_helpful=True)
        ltm.update_source_score("ibm.com", was_helpful=True)
        ltm.update_source_score("ibm.com", was_helpful=False)
        ltm.update_source_score("nature.com", was_helpful=True)
        ltm.update_source_score("nature.com", was_helpful=True)
        
        ibm_score = ltm.get_source_score("ibm.com")
        nature_score = ltm.get_source_score("nature.com")
        print(f"IBM.com reliability: {ibm_score:.2f}")
        print(f"Nature.com reliability: {nature_score:.2f}")
        
        # Test 10: Top sources
        print("\nTest 10: Top Sources")
        top_sources = ltm.get_top_sources(limit=5)
        print(f"Top {len(top_sources)} sources:")
        for i, source in enumerate(top_sources, 1):
            print(f"   {i}. {source['domain']}: {source['score']:.2f} ({source['helpful']}/{source['total']})")
        
        # Test 11: Save metrics
        print("\nTest 11: Save Metrics")
        ltm.save_metrics("q1", {
            "confidence": 0.92,
            "response_time": 2.5,
            "sources_used": 2,
            "agents_used": 3
        })
        ltm.save_metrics("q2", {
            "confidence": 0.88,
            "response_time": 3.1,
            "sources_used": 1,
            "agents_used": 4
        })
        print("Metrics saved")
        
        # Test 12: Get metrics summary
        print("\nTest 12: Metrics Summary")
        summary = ltm.get_metrics_summary()
        print(f"Total queries: {summary['total_queries']}")
        print(f"Average confidence: {summary['average_confidence']}")
        print(f"Average response time: {summary['average_response_time']}s")
        
        # Test 13: Storage stats
        print("\nTest 13: Storage Stats")
        stats = ltm.get_storage_stats()
        print(f"Database: {stats['database']}")
        print(f"Total size: {stats['total_size_mb']} MB")
        print("Collections:")
        for col_name, col_stats in stats['collections'].items():
            print(f"   - {col_name}: {col_stats['count']} documents")
        
        # Test 14: Filter by confidence
        print("\nTest 14: High Confidence Queries ---")
        high_conf = ltm.get_query_history(min_confidence=0.90)
        print(f"Found {len(high_conf)} queries with confidence >= 0.90")
        
        # Test 15: Cleanup test (commented out to preserve data)
        # print("\n--- Test 15: Cleanup Old Data ---")
        # ltm.cleanup_old_data(days_to_keep=0)  # Remove all for testing
        # print("Cleanup completed")
        
        print("\n" + "="*60)
        print("ALL MONGODB TESTS PASSED!")
        print("="*60)
        
    except Exception as e:
        print(f"\n TEST FAILED: {e}")
        raise
    
    finally:
        # Close connection
        close_long_term_memory()
        print("\n MongoDB connection closed")


if __name__ == "__main__":
    test_mongodb_long_term_memory()
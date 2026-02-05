"""
Long-Term Memory System using MongoDB
Handles persistent storage of:
- Query history
- Learnings and insights
- Source reliability scores
- User preferences
- Agent performance metrics
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pymongo.errors import ConnectionFailure, PyMongoError
from pymongo import MongoClient, ASCENDING, DESCENDING

from app.core.config import settings
from app.core.logger import logger


class LongTermMemory:
    """
    Persistent memory storage using MongoDB.
    Stores historical data across sessions.
    """
    
    def __init__(
        self,
        connection_uri: Optional[str] = None,
        database_name: Optional[str] = None
    ):
        """
        Initialize long-term memory with MongoDB
        
        Args:
            connection_uri: MongoDB connection URI (defaults to settings)
            database_name: Database name (defaults to settings)
        """
        self.uri = connection_uri or settings.MONGODB_URI
        self.db_name = database_name or settings.MONGODB_DATABASE
        
        # Initialize MongoDB client
        try:
            self.client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT
            )
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {self.db_name}")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise MemoryError(f"Cannot connect to MongoDB: {e}")
        
        # Get database and collections
        self.db = self.client[self.db_name]
        self.queries = self.db["queries"]
        self.learnings = self.db["learnings"]
        self.source_scores = self.db["source_scores"]
        self.metrics = self.db["metrics"]
        
        # Create indexes for better performance
        self._create_indexes()
        
        logger.info(
            "LongTermMemory initialized",
            extra={
                "database": self.db_name,
                "collections": ["queries", "learnings", "source_scores", "metrics"]
            }
        )
    
    def _create_indexes(self):
        """Create indexes for faster queries"""
        try:
            # Query collection indexes
            self.queries.create_index([("timestamp", DESCENDING)])
            self.queries.create_index([("query_text", "text")])
            self.queries.create_index([("confidence", DESCENDING)])
            
            # Learnings collection indexes
            self.learnings.create_index([("topic", ASCENDING)])
            self.learnings.create_index([("timestamp", DESCENDING)])
            self.learnings.create_index([("confidence", DESCENDING)])
            
            # Source scores indexes
            self.source_scores.create_index([("domain", ASCENDING)], unique=True)
            self.source_scores.create_index([("score", DESCENDING)])
            
            # Metrics indexes
            self.metrics.create_index([("timestamp", DESCENDING)])
            self.metrics.create_index([("query_id", ASCENDING)])
            
            logger.debug("MongoDB indexes created successfully")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    # QUERY HISTORY
    
    def save_query(
        self,
        query_id: str,
        query_text: str,
        response: str,
        sources: List[str],
        confidence: float,
        metadata: Optional[Dict] = None
    ):
        """
        Save a completed query to history
        
        Args:
            query_id: Unique query identifier
            query_text: Original user query
            response: Generated response
            sources: List of source URLs used
            confidence: Confidence score (0-1)
            metadata: Additional metadata
        """
        try:
            document = {
                "query_id": query_id,
                "query_text": query_text,
                "response": response,
                "sources": sources,
                "confidence": confidence,
                "metadata": metadata or {},
                "timestamp": datetime.now()
            }
            
            # Upsert (insert or update)
            self.queries.update_one(
                {"query_id": query_id},
                {"$set": document},
                upsert=True
            )
            
            logger.info(
                "Query saved to MongoDB",
                extra={
                    "query_id": query_id,
                    "confidence": confidence,
                    "source_count": len(sources)
                }
            )
        except PyMongoError as e:
            logger.error(f"Failed to save query: {e}")
            raise MemoryError(f"Cannot save query to MongoDB: {e}")
    
    def get_query_history(
        self,
        limit: Optional[int] = None,
        min_confidence: Optional[float] = None
    ) -> List[Dict]:
        """
        Retrieve query history
        
        Args:
            limit: Maximum number of queries to return
            min_confidence: Filter by minimum confidence score
            
        Returns:
            List of query records
        """
        try:
            # Build query filter
            query_filter = {}
            if min_confidence is not None:
                query_filter["confidence"] = {"$gte": min_confidence}
            
            # Execute query
            cursor = self.queries.find(query_filter).sort("timestamp", DESCENDING)
            
            if limit:
                cursor = cursor.limit(limit)
            
            queries = list(cursor)
            
            # Convert ObjectId to string for JSON serialization
            for q in queries:
                q["_id"] = str(q["_id"])
            
            logger.debug(f"Retrieved {len(queries)} queries from MongoDB")
            return queries
            
        except PyMongoError as e:
            logger.error(f"Failed to get query history: {e}")
            raise MemoryError(f"Cannot retrieve history from MongoDB: {e}")
    
    def search_history(self, search_term: str, limit: int = 10) -> List[Dict]:
        """
        Search query history by text
        
        Args:
            search_term: Term to search for
            limit: Maximum results to return
            
        Returns:
            Matching query records
        """
        try:
            # Use MongoDB text search
            results = self.queries.find(
                {"$text": {"$search": search_term}}
            ).limit(limit)
            
            matches = list(results)
            
            # Convert ObjectId to string
            for m in matches:
                m["_id"] = str(m["_id"])
            
            logger.debug(f"Found {len(matches)} matches for '{search_term}'")
            return matches
            
        except PyMongoError as e:
            logger.error(f"Failed to search history: {e}")
            raise MemoryError(f"Cannot search history in MongoDB: {e}")
    
    def get_query_by_id(self, query_id: str) -> Optional[Dict]:
        """
        Get specific query by ID
        
        Args:
            query_id: Query identifier
            
        Returns:
            Query document or None
        """
        try:
            query = self.queries.find_one({"query_id": query_id})
            if query:
                query["_id"] = str(query["_id"])
            return query
        except PyMongoError as e:
            logger.error(f"Failed to get query: {e}")
            return None
    
    # LEARNINGS & INSIGHTS
    
    def save_learning(
        self,
        topic: str,
        insight: str,
        confidence: float,
        sources: List[str]
    ):
        """
        Save a learning or insight
        
        Args:
            topic: Topic of the learning
            insight: The insight or learning
            confidence: Confidence in this learning (0-1)
            sources: Supporting sources
        """
        try:
            document = {
                "topic": topic,
                "insight": insight,
                "confidence": confidence,
                "sources": sources,
                "timestamp": datetime.now()
            }
            
            self.learnings.insert_one(document)
            
            logger.info(
                "Learning saved to MongoDB",
                extra={"topic": topic, "confidence": confidence}
            )
        except PyMongoError as e:
            logger.error(f"Failed to save learning: {e}")
            raise MemoryError(f"Cannot save learning to MongoDB: {e}")
    
    def get_learnings(
        self,
        topic: str,
        min_confidence: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve learnings for a topic
        
        Args:
            topic: Topic to retrieve learnings for
            min_confidence: Minimum confidence threshold
            limit: Maximum results to return
            
        Returns:
            List of learnings
        """
        try:
            query_filter = {"topic": topic}
            if min_confidence is not None:
                query_filter["confidence"] = {"$gte": min_confidence}
            
            cursor = self.learnings.find(query_filter).sort("timestamp", DESCENDING)
            
            if limit:
                cursor = cursor.limit(limit)
            
            learnings = list(cursor)
            
            # Convert ObjectId to string
            for l in learnings:
                l["_id"] = str(l["_id"])
            
            return learnings
            
        except PyMongoError as e:
            logger.error(f"Failed to get learnings: {e}")
            raise MemoryError(f"Cannot retrieve learnings from MongoDB: {e}")
    
    def get_all_topics(self) -> List[str]:
        """
        Get list of all topics with learnings
        
        Returns:
            List of unique topics
        """
        try:
            topics = self.learnings.distinct("topic")
            return sorted(topics)
        except PyMongoError as e:
            logger.error(f"Failed to get topics: {e}")
            return []
    
    # SOURCE RELIABILITY
    
    def update_source_score(self, domain: str, was_helpful: bool):
        """
        Update reliability score for a source domain
        
        Args:
            domain: Domain name (e.g., 'wikipedia.org')
            was_helpful: Whether the source was helpful
        """
        try:
            # Increment counters
            update = {
                "$inc": {
                    "total": 1,
                    "helpful": 1 if was_helpful else 0
                }
            }
            
            # Upsert the document
            result = self.source_scores.update_one(
                {"domain": domain},
                update,
                upsert=True
            )
            
            # Calculate and update score
            source_doc = self.source_scores.find_one({"domain": domain})
            if source_doc:
                score = source_doc["helpful"] / source_doc["total"]
                self.source_scores.update_one(
                    {"domain": domain},
                    {"$set": {"score": score}}
                )
                
                logger.debug(
                    f"Updated source score: {domain}",
                    extra={"score": score}
                )
        except PyMongoError as e:
            logger.error(f"Failed to update source score: {e}")
            raise MemoryError(f"Cannot update source score in MongoDB: {e}")
    
    def get_source_score(self, domain: str) -> Optional[float]:
        """
        Get reliability score for a domain
        
        Args:
            domain: Domain name
            
        Returns:
            Reliability score (0-1) or None if no data
        """
        try:
            source = self.source_scores.find_one({"domain": domain})
            return source.get("score") if source else None
        except PyMongoError as e:
            logger.error(f"Failed to get source score: {e}")
            return None
    
    def get_top_sources(self, limit: int = 10) -> List[Dict]:
        """
        Get most reliable sources
        
        Args:
            limit: Number of sources to return
            
        Returns:
            List of top sources with scores
        """
        try:
            sources = self.source_scores.find().sort("score", DESCENDING).limit(limit)
            result = list(sources)
            
            # Convert ObjectId to string
            for s in result:
                s["_id"] = str(s["_id"])
            
            return result
        except PyMongoError as e:
            logger.error(f"Failed to get top sources: {e}")
            raise MemoryError(f"Cannot retrieve top sources from MongoDB: {e}")
    
    # METRICS & STATISTICS
    
    def save_metrics(self, query_id: str, metrics: Dict[str, Any]):
        """
        Save performance metrics
        
        Args:
            query_id: Query identifier
            metrics: Dictionary of metrics to save
        """
        try:
            document = {
                "query_id": query_id,
                "timestamp": datetime.now(),
                **metrics
            }
            
            self.metrics.insert_one(document)
            
            logger.debug("Metrics saved to MongoDB")
        except PyMongoError as e:
            logger.error(f"Failed to save metrics: {e}")
            raise MemoryError(f"Cannot save metrics to MongoDB: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of all metrics
        
        Returns:
            Aggregated metrics
        """
        try:
            # Count total queries
            total = self.metrics.count_documents({})
            
            if total == 0:
                return {
                    "total_queries": 0,
                    "average_confidence": 0,
                    "average_response_time": 0
                }
            
            # Calculate averages using aggregation
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "avg_confidence": {"$avg": "$confidence"},
                        "avg_response_time": {"$avg": "$response_time"},
                        "total_sources": {"$sum": "$sources_used"}
                    }
                }
            ]
            
            result = list(self.metrics.aggregate(pipeline))
            
            if result:
                summary = {
                    "total_queries": total,
                    "average_confidence": round(result[0].get("avg_confidence", 0), 2),
                    "average_response_time": round(result[0].get("avg_response_time", 0), 2),
                    "total_sources_used": result[0].get("total_sources", 0)
                }
            else:
                summary = {
                    "total_queries": total,
                    "average_confidence": 0,
                    "average_response_time": 0
                }
            
            # Get latest metric
            latest = self.metrics.find_one(sort=[("timestamp", DESCENDING)])
            if latest:
                latest["_id"] = str(latest["_id"])
                summary["latest_metrics"] = latest
            
            return summary
            
        except PyMongoError as e:
            logger.error(f"Failed to get metrics summary: {e}")
            raise MemoryError(f"Cannot retrieve metrics from MongoDB: {e}")
    
    def get_metrics_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Get metrics within a date range
        
        Args:
            start_date: Start datetime
            end_date: End datetime
            
        Returns:
            List of metric documents
        """
        try:
            query = {
                "timestamp": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
            
            results = self.metrics.find(query).sort("timestamp", DESCENDING)
            metrics = list(results)
            
            # Convert ObjectId to string
            for m in metrics:
                m["_id"] = str(m["_id"])
            
            return metrics
        except PyMongoError as e:
            logger.error(f"Failed to get metrics by date: {e}")
            return []
    
    # CLEANUP & MAINTENANCE
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Remove data older than specified days
        
        Args:
            days_to_keep: Number of days of data to keep
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Clean queries
            result_queries = self.queries.delete_many(
                {"timestamp": {"$lt": cutoff_date}}
            )
            
            # Clean learnings
            result_learnings = self.learnings.delete_many(
                {"timestamp": {"$lt": cutoff_date}}
            )
            
            # Clean metrics
            result_metrics = self.metrics.delete_many(
                {"timestamp": {"$lt": cutoff_date}}
            )
            
            total_removed = (
                result_queries.deleted_count +
                result_learnings.deleted_count +
                result_metrics.deleted_count
            )
            
            logger.info(
                f"Cleaned up {total_removed} old documents",
                extra={
                    "queries": result_queries.deleted_count,
                    "learnings": result_learnings.deleted_count,
                    "metrics": result_metrics.deleted_count
                }
            )
            
        except PyMongoError as e:
            logger.error(f"Failed to cleanup old data: {e}")
            raise MemoryError(f"Cannot cleanup MongoDB data: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored data
        
        Returns:
            Storage statistics
        """
        try:
            stats = {
                "database": self.db_name,
                "collections": {
                    "queries": {
                        "count": self.queries.count_documents({}),
                        "size_bytes": self.db.command("collStats", "queries").get("size", 0)
                    },
                    "learnings": {
                        "count": self.learnings.count_documents({}),
                        "size_bytes": self.db.command("collStats", "learnings").get("size", 0)
                    },
                    "source_scores": {
                        "count": self.source_scores.count_documents({}),
                        "size_bytes": self.db.command("collStats", "source_scores").get("size", 0)
                    },
                    "metrics": {
                        "count": self.metrics.count_documents({}),
                        "size_bytes": self.db.command("collStats", "metrics").get("size", 0)
                    }
                }
            }
            
            # Calculate total size
            total_size = sum(
                col["size_bytes"] for col in stats["collections"].values()
            )
            stats["total_size_bytes"] = total_size
            stats["total_size_mb"] = round(total_size / (1024 * 1024), 2)
            
            return stats
            
        except PyMongoError as e:
            logger.error(f"Failed to get storage stats: {e}")
            raise MemoryError(f"Cannot get MongoDB stats: {e}")
    
    def clear_all_data(self):
        """
        Clear all data from all collections (use with caution!)
        """
        try:
            self.queries.delete_many({})
            self.learnings.delete_many({})
            self.source_scores.delete_many({})
            self.metrics.delete_many({})
            
            logger.warning("All MongoDB data cleared!")
        except PyMongoError as e:
            logger.error(f"Failed to clear data: {e}")
            raise MemoryError(f"Cannot clear MongoDB data: {e}")

# Global instance
_long_term_memory = None


def get_long_term_memory() -> LongTermMemory:
    """Get or create global LongTermMemory instance"""
    global _long_term_memory
    if _long_term_memory is None:
        _long_term_memory = LongTermMemory()
    return _long_term_memory


def close_long_term_memory():
    """Close global LongTermMemory instance"""
    global _long_term_memory
    if _long_term_memory is not None:
        _long_term_memory.close()
        _long_term_memory = None
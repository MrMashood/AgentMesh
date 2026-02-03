from typing import Any, Dict, Optional, List
from datetime import datetime
import threading
from dataclasses import dataclass, field
import uuid

from app.core import (
    logger,
    # MemoryException,
    MemoryStorageError,
    MemoryRetrievalError
)


@dataclass
class QueryState:
    """
    Represents the state of a query execution
    """
    query_id: str
    query: str
    status: str  # 'planning', 'researching', 'verifying', 'synthesizing', 'reflecting', 'completed', 'failed'
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    
    # Agent outputs
    plan: Optional[Dict] = None
    research_findings: List[Dict] = field(default_factory=list)
    verification_results: Optional[Dict] = None
    draft_answer: Optional[str] = None
    reflection_feedback: Optional[Dict] = None
    final_answer: Optional[str] = None
    
    # Metadata
    confidence_score: Optional[float] = None
    sources: List[str] = field(default_factory=list)
    tool_calls: List[Dict] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'query_id': self.query_id,
            'query': self.query,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'retry_count': self.retry_count,
            'plan': self.plan,
            'research_findings': self.research_findings,
            'verification_results': self.verification_results,
            'draft_answer': self.draft_answer,
            'reflection_feedback': self.reflection_feedback,
            'final_answer': self.final_answer,
            'confidence_score': self.confidence_score,
            'sources': self.sources,
            'tool_calls': self.tool_calls,
            'errors': self.errors
        }


class ShortTermMemory:
    """
    Short-term memory for runtime query execution
    
    Features:
    - Thread-safe operations
    - Store/retrieve by query_id
    - Track query state
    - Store agent outputs
    - Automatic cleanup
    """
    
    def __init__(self):
        """Initialize short-term memory"""
        self._store: Dict[str, QueryState] = {}
        self._lock = threading.Lock()
        logger.info("Short-term memory initialized")
    
    def create_query(self, query: str, query_id: Optional[str] = None) -> str:
        """
        Create a new query in memory
        
        Args:
            query: User query string
            query_id: Optional query ID (generated if not provided)
            
        Returns:
            Query ID
        """
        if not query_id:
            query_id = str(uuid.uuid4())
        
        with self._lock:
            now = datetime.now()
            state = QueryState(
                query_id=query_id,
                query=query,
                status='planning',
                created_at=now,
                updated_at=now
            )
            
            self._store[query_id] = state
            
            logger.info(
                "Query created in memory",
                query_id=query_id,
                query=query[:100]
            )
            
            return query_id
    
    def get_query_state(self, query_id: str) -> Optional[QueryState]:
        """
        Get query state
        
        Args:
            query_id: Query ID
            
        Returns:
            QueryState or None if not found
        """
        with self._lock:
            state = self._store.get(query_id)
            
            if not state:
                logger.warning("Query not found in memory", query_id=query_id)
            
            return state
    
    def update_status(self, query_id: str, status: str):
        """
        Update query status
        
        Args:
            query_id: Query ID
            status: New status
            
        Raises:
            MemoryStorageError: If query not found
        """
        with self._lock:
            state = self._store.get(query_id)
            
            if not state:
                raise MemoryRetrievalError(
                    memory_type="short_term",
                    query=query_id,
                    reason="Query not found"
                )
            
            state.status = status
            state.updated_at = datetime.now()
            
            logger.info(
                "Query status updated",
                query_id=query_id,
                status=status
            )
    
    def store_plan(self, query_id: str, plan: Dict):
        """
        Store planner agent output
        
        Args:
            query_id: Query ID
            plan: Plan dictionary
        """
        with self._lock:
            state = self._store.get(query_id)
            
            if not state:
                raise MemoryStorageError(
                    memory_type="short_term",
                    operation="store_plan",
                    reason="Query not found"
                )
            
            state.plan = plan
            state.updated_at = datetime.now()
            
            logger.info(
                "Plan stored in memory",
                query_id=query_id,
                steps=len(plan.get('steps', []))
            )
    
    def store_research_findings(self, query_id: str, findings: List[Dict]):
        """
        Store research agent output
        
        Args:
            query_id: Query ID
            findings: List of research findings
        """
        with self._lock:
            state = self._store.get(query_id)
            
            if not state:
                raise MemoryStorageError(
                    memory_type="short_term",
                    operation="store_research",
                    reason="Query not found"
                )
            
            state.research_findings = findings
            state.updated_at = datetime.now()
            
            # Extract sources
            for finding in findings:
                if 'url' in finding and finding['url'] not in state.sources:
                    state.sources.append(finding['url'])
            
            logger.info(
                "Research findings stored",
                query_id=query_id,
                findings_count=len(findings)
            )
    
    def store_verification_results(self, query_id: str, results: Dict):
        """
        Store verification agent output
        
        Args:
            query_id: Query ID
            results: Verification results
        """
        with self._lock:
            state = self._store.get(query_id)
            
            if not state:
                raise MemoryStorageError(
                    memory_type="short_term",
                    operation="store_verification",
                    reason="Query not found"
                )
            
            state.verification_results = results
            state.updated_at = datetime.now()
            
            logger.info(
                "Verification results stored",
                query_id=query_id,
                verified_claims=results.get('verified_claims_count', 0)
            )
    
    def store_draft_answer(self, query_id: str, answer: str):
        """
        Store synthesis agent output
        
        Args:
            query_id: Query ID
            answer: Draft answer
        """
        with self._lock:
            state = self._store.get(query_id)
            
            if not state:
                raise MemoryStorageError(
                    memory_type="short_term",
                    operation="store_draft",
                    reason="Query not found"
                )
            
            state.draft_answer = answer
            state.updated_at = datetime.now()
            
            logger.info(
                "Draft answer stored",
                query_id=query_id,
                answer_length=len(answer)
            )
    
    def store_reflection_feedback(self, query_id: str, feedback: Dict):
        """
        Store reflection agent output
        
        Args:
            query_id: Query ID
            feedback: Reflection feedback with confidence score
        """
        with self._lock:
            state = self._store.get(query_id)
            
            if not state:
                raise MemoryStorageError(
                    memory_type="short_term",
                    operation="store_reflection",
                    reason="Query not found"
                )
            
            state.reflection_feedback = feedback
            state.confidence_score = feedback.get('confidence', 0.0)
            state.updated_at = datetime.now()
            
            logger.info(
                "Reflection feedback stored",
                query_id=query_id,
                confidence=state.confidence_score
            )
    
    def store_final_answer(self, query_id: str, answer: str):
        """
        Store final answer
        
        Args:
            query_id: Query ID
            answer: Final answer
        """
        with self._lock:
            state = self._store.get(query_id)
            
            if not state:
                raise MemoryStorageError(
                    memory_type="short_term",
                    operation="store_final_answer",
                    reason="Query not found"
                )
            
            state.final_answer = answer
            state.status = 'completed'
            state.updated_at = datetime.now()
            
            logger.info(
                "Final answer stored",
                query_id=query_id,
                answer_length=len(answer)
            )
    
    def record_tool_call(self, query_id: str, tool_name: str, params: Dict, result: Any):
        """
        Record a tool call
        
        Args:
            query_id: Query ID
            tool_name: Name of tool
            params: Tool parameters
            result: Tool result
        """
        with self._lock:
            state = self._store.get(query_id)
            
            if state:
                tool_call = {
                    'tool': tool_name,
                    'params': params,
                    'result_type': type(result).__name__,
                    'timestamp': datetime.now().isoformat()
                }
                state.tool_calls.append(tool_call)
    
    def record_error(self, query_id: str, error: Exception, agent: str):
        """
        Record an error
        
        Args:
            query_id: Query ID
            error: Exception that occurred
            agent: Agent that encountered error
        """
        with self._lock:
            state = self._store.get(query_id)
            
            if state:
                error_info = {
                    'agent': agent,
                    'error_type': type(error).__name__,
                    'error_message': str(error),
                    'timestamp': datetime.now().isoformat()
                }
                state.errors.append(error_info)
                
                logger.error(
                    "Error recorded in memory",
                    query_id=query_id,
                    agent=agent,
                    error=str(error)
                )
    
    def increment_retry(self, query_id: str):
        """
        Increment retry count
        
        Args:
            query_id: Query ID
        """
        with self._lock:
            state = self._store.get(query_id)
            
            if state:
                state.retry_count += 1
                logger.info(
                    "Retry count incremented",
                    query_id=query_id,
                    retry_count=state.retry_count
                )
    
    def clear_query(self, query_id: str):
        """
        Clear query from memory
        
        Args:
            query_id: Query ID
        """
        with self._lock:
            if query_id in self._store:
                del self._store[query_id]
                logger.info("Query cleared from memory", query_id=query_id)
    
    def clear_all(self):
        """Clear all queries from memory"""
        with self._lock:
            count = len(self._store)
            self._store.clear()
            logger.info("All queries cleared from memory", count=count)
    
    def get_all_queries(self) -> List[str]:
        """
        Get all query IDs in memory
        
        Returns:
            List of query IDs
        """
        with self._lock:
            return list(self._store.keys())
    
    def get_memory_stats(self) -> Dict:
        """
        Get memory statistics
        
        Returns:
            Dictionary with stats
        """
        with self._lock:
            stats = {
                'total_queries': len(self._store),
                'queries_by_status': {},
                'total_tool_calls': 0,
                'total_errors': 0
            }
            
            for state in self._store.values():
                # Count by status
                status = state.status
                stats['queries_by_status'][status] = stats['queries_by_status'].get(status, 0) + 1
                
                # Count tool calls and errors
                stats['total_tool_calls'] += len(state.tool_calls)
                stats['total_errors'] += len(state.errors)
            
            return stats


# Global instance
_memory_instance = None


def get_short_term_memory() -> ShortTermMemory:
    """
    Get global short-term memory instance
    
    Returns:
        ShortTermMemory instance
    """
    global _memory_instance
    
    if _memory_instance is None:
        _memory_instance = ShortTermMemory()
    
    return _memory_instance
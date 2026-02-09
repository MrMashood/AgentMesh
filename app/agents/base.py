"""
Base Agent Class
Foundation for all specialized agents
"""

from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime

# from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import AgentError, ValidationError
from app.services.llm_service import get_llm_service
from app.memory.short_term import get_short_term_memory
from app.memory.long_term import get_long_term_memory


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Provides common functionality and enforces interface.
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        guidelines: Optional[List[str]] = None
    ):
        """
        Initialize base agent
        
        Args:
            name: Agent name (e.g., "planner", "research")
            role: Agent role description
            guidelines: List of behavioral guidelines
        """
        self.name = name
        self.role = role
        self.guidelines = guidelines or []
        
        # Get service instances
        self.llm = get_llm_service()
        self.short_memory = get_short_term_memory()
        self.long_memory = get_long_term_memory()
        
        # Agent statistics
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_tokens_used": 0,
            "average_execution_time": 0.0
        }
        
        logger.info(
            f"Agent initialized: {self.name}",
            extra={"role": self.role}
        )
    
    @abstractmethod
    def execute(self, query_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent's main task.
        Must be implemented by subclasses.
        
        Args:
            query_id: Current query identifier
            context: Execution context with relevant data
            
        Returns:
            Agent output dictionary
        """
        pass
    
    def _create_system_prompt(
        self,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Create system prompt for this agent
        
        Args:
            additional_context: Extra context to include
            
        Returns:
            Formatted system prompt
        """
        context_parts = [f"You are {self.role}."]
        
        if additional_context:
            context_parts.append(f"\n\nContext:\n{additional_context}")
        
        if self.guidelines:
            context_parts.append("\n\nGuidelines:")
            for i, guideline in enumerate(self.guidelines, 1):
                context_parts.append(f"{i}. {guideline}")
        
        return "\n".join(context_parts)
    
    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call LLM with error handling and logging
        
        Args:
            messages: Conversation messages
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLM response
        """
        try:
            start_time = datetime.now()
            
            response = self.llm.generate_response(
                messages=messages,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update stats
            self.stats["total_tokens_used"] += response["usage"]["total_tokens"]
            
            logger.info(
                f"{self.name} called LLM",
                extra={
                    "execution_time": execution_time,
                    "tokens_used": response["usage"]["total_tokens"]
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"{self.name} LLM call failed: {e}")
            raise AgentError(f"LLM call failed: {e}")
    
    def _get_context_from_memory(self, query_id: str) -> Dict[str, Any]:
        """
        Retrieve relevant context from short-term memory
        
        Args:
            query_id: Query identifier
            
        Returns:
            Context dictionary
        """
        try:
            context = {
                "query": self.short_memory.get_query(query_id),
                "plan": self.short_memory.get_plan(query_id),
                "agent_outputs": self.short_memory.get_all_agent_outputs(query_id),
                "tool_calls": self.short_memory.get_tool_calls(query_id)
            }
            return context
        except Exception as e:
            logger.warning(f"Failed to get context from memory: {e}")
            return {}
    
    def _store_output(
        self,
        query_id: str,
        output: Dict[str, Any]
    ):
        """
        Store agent output in short-term memory
        
        Args:
            query_id: Query identifier
            output: Agent output to store
        """
        try:
            self.short_memory.add_agent_output(
                query_id=query_id,
                agent_name=self.name,
                output=output
            )
            logger.debug(f"{self.name} output stored in memory")
        except Exception as e:
            logger.error(f"Failed to store output: {e}")
            raise AgentError(f"Cannot store output: {e}")
    
    def _get_past_learnings(self, topic: str) -> List[Dict]:
        """
        Retrieve relevant learnings from long-term memory
        
        Args:
            topic: Topic to search for
            
        Returns:
            List of relevant learnings
        """
        try:
            learnings = self.long_memory.get_learnings(topic, limit=5)
            logger.debug(f"Retrieved {len(learnings)} learnings for '{topic}'")
            return learnings
        except Exception as e:
            logger.warning(f"Failed to get learnings: {e}")
            return []
    
    def _save_learning(
        self,
        topic: str,
        insight: str,
        confidence: float,
        sources: List[str]
    ):
        """
        Save a new learning to long-term memory
        
        Args:
            topic: Learning topic
            insight: The insight/learning
            confidence: Confidence score (0-1)
            sources: Supporting sources
        """
        try:
            self.long_memory.save_learning(
                topic=topic,
                insight=insight,
                confidence=confidence,
                sources=sources
            )
            logger.info(f"{self.name} saved learning: {topic}")
        except Exception as e:
            logger.warning(f"Failed to save learning: {e}")
    
    def run(self, query_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run agent with error handling and statistics tracking
        
        Args:
            query_id: Query identifier
            context: Execution context
            
        Returns:
            Agent output
        """
        start_time = datetime.now()
        self.stats["total_executions"] += 1
        
        try:
            logger.info(
                f"Agent {self.name} starting execution",
                extra={"query_id": query_id}
            )
            
            # Execute agent logic
            output = self.execute(query_id, context)
            
            # Store output in memory
            self._store_output(query_id, output)
            
            # Update statistics
            execution_time = (datetime.now() - start_time).total_seconds()
            self.stats["successful_executions"] += 1
            self._update_average_time(execution_time)
            
            logger.info(
                f"Agent {self.name} completed successfully",
                extra={
                    "query_id": query_id,
                    "execution_time": execution_time
                }
            )
            
            return output
            
        except Exception as e:
            self.stats["failed_executions"] += 1
            logger.error(
                f"Agent {self.name} failed",
                extra={
                    "query_id": query_id,
                    "error": str(e)
                }
            )
            raise AgentError(f"{self.name} execution failed: {e}")
    
    def _update_average_time(self, execution_time: float):
        """
        Update average execution time
        
        Args:
            execution_time: Current execution time
        """
        current_avg = self.stats["average_execution_time"]
        total = self.stats["successful_executions"]
        
        # Calculate new average
        self.stats["average_execution_time"] = (
            (current_avg * (total - 1) + execution_time) / total
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics
        
        Returns:
            Statistics dictionary
        """
        success_rate = 0.0
        if self.stats["total_executions"] > 0:
            success_rate = (
                self.stats["successful_executions"] / 
                self.stats["total_executions"]
            )
        
        return {
            **self.stats,
            "success_rate": round(success_rate, 2)
        }
    
    def reset_stats(self):
        """Reset agent statistics"""
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_tokens_used": 0,
            "average_execution_time": 0.0
        }
        logger.info(f"{self.name} statistics reset")
    
    def validate_context(
        self,
        context: Dict[str, Any],
        required_keys: List[str]
    ):
        """
        Validate that context has required keys
        
        Args:
            context: Context dictionary
            required_keys: List of required keys
            
        Raises:
            ValidationError if keys missing
        """
        missing = [key for key in required_keys if key not in context]
        if missing:
            raise ValidationError(
                f"Missing required context keys: {', '.join(missing)}"
            )
    
    def __repr__(self) -> str:
        """String representation"""
        return f"<{self.__class__.__name__}(name='{self.name}', role='{self.role}')>"
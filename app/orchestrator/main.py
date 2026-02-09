"""
Main Orchestrator
Coordinates all agents to process user queries
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid

# from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import AgentError
from app.memory.short_term import get_short_term_memory
from app.memory.long_term import get_long_term_memory
from app.agents.planner import get_planner_agent
from app.agents.research import get_research_agent
from app.agents.verification import get_verification_agent
from app.agents.synthesis import get_synthesis_agent
from app.agents.reflection import get_reflection_agent


class Orchestrator:
    """
    Orchestrates the entire query processing pipeline.
    Coordinates all agents to produce high-quality answers.
    """
    
    def __init__(self):
        """Initialize orchestrator with all agents"""
        
        # Initialize memory systems
        self.short_memory = get_short_term_memory()
        self.long_memory = get_long_term_memory()
        
        # Initialize agents
        self.planner = get_planner_agent()
        self.researcher = get_research_agent()
        self.verifier = get_verification_agent()
        self.synthesizer = get_synthesis_agent()
        self.reflector = get_reflection_agent()
        
        # Orchestrator configuration
        self.max_retries = 2
        self.enable_reflection = True
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "retries_triggered": 0,
            "average_execution_time": 0.0
        }
        
        logger.info("Orchestrator initialized with all agents")
    
    def process_query(
        self,
        query: str,
        query_id: Optional[str] = None,
        enable_reflection: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Process a user query through the entire pipeline
        
        Args:
            query: User query text
            query_id: Optional query identifier (generated if not provided)
            enable_reflection: Whether to use reflection agent (default: True)
            
        Returns:
            Complete response with answer and metadata
        """
        start_time = datetime.now()
        query_id = query_id or self._generate_query_id()
        enable_reflection = enable_reflection if enable_reflection is not None else self.enable_reflection
        
        self.stats["total_queries"] += 1
        
        logger.info(
            f"Processing query: {query[:50]}...",
            extra={"query_id": query_id}
        )
        
        try:
            # Initialize short-term memory for this query
            self.short_memory.set_query(query_id, query)
            
            # Execute pipeline
            result = self._execute_pipeline(
                query_id=query_id,
                query=query,
                enable_reflection=enable_reflection
            )
            
            # Save to long-term memory
            self._save_to_long_term_memory(query_id, query, result)
            
            # Update statistics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(success=True, execution_time=execution_time)
            
            # Clean up short-term memory
            self.short_memory.clear(query_id)
            
            logger.info(
                f"Query processed successfully in {execution_time:.2f}s",
                extra={
                    "query_id": query_id,
                    "confidence": result.get("confidence", 0)
                }
            )
            
            return result
            
        except Exception as e:
            self.stats["failed_queries"] += 1
            logger.error(f"Query processing failed: {e}", extra={"query_id": query_id})
            
            # Clean up on failure
            self.short_memory.clear(query_id)
            
            raise AgentError(f"Failed to process query: {e}")
    
    def _execute_pipeline(
        self,
        query_id: str,
        query: str,
        enable_reflection: bool
    ) -> Dict[str, Any]:
        """
        Execute the agent pipeline
        
        Args:
            query_id: Query identifier
            query: User query
            enable_reflection: Whether to use reflection
            
        Returns:
            Pipeline result
        """
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                # Step 1: Planning
                logger.info(f"Step 1/6: Planning (attempt {retry_count + 1})")
                plan_result = self.planner.run(query_id, {"query": query})
                
                # Step 2: Research
                logger.info("Step 2/6: Research")
                research_context = {
                    "query": query,
                    "plan": plan_result
                }
                research_findings = self.researcher.run(query_id, research_context)
                
                # Step 3: Verification
                logger.info("Step 3/6: Verification")
                verify_context = {
                    "query": query,
                    "research_findings": research_findings
                }
                verification_report = self.verifier.run(query_id, verify_context)
                
                # Step 4: Synthesis
                logger.info("Step 4/6: Synthesis")
                synthesis_context = {
                    "query": query,
                    "research_findings": research_findings,
                    "verification_report": verification_report,
                    "plan": plan_result
                }
                synthesis_result = self.synthesizer.run(query_id, synthesis_context)
                
                # Step 5: Reflection (optional)
                if enable_reflection:
                    logger.info("Step 5/6: Reflection")
                    reflection_context = {
                        "query": query,
                        "synthesis_result": synthesis_result,
                        "verification_report": verification_report,
                        "plan": plan_result
                    }
                    reflection_result = self.reflector.run(query_id, reflection_context)
                    
                    # Check if retry is needed
                    if reflection_result["should_retry"] and retry_count < self.max_retries:
                        logger.warning(
                            f"Reflection suggests retry: {reflection_result.get('retry_reason', 'Quality too low')}"
                        )
                        retry_count += 1
                        self.stats["retries_triggered"] += 1
                        continue
                else:
                    reflection_result = None
                
                # Step 6: Finalize
                logger.info("Step 6/6: Finalization")
                final_result = self._finalize_result(
                    query=query,
                    query_id=query_id,
                    plan=plan_result,
                    research=research_findings,
                    verification=verification_report,
                    synthesis=synthesis_result,
                    reflection=reflection_result,
                    retry_count=retry_count
                )
                
                return final_result
                
            except AgentError as e:
                if retry_count < self.max_retries:
                    logger.warning(f"Agent error, retrying: {e}")
                    retry_count += 1
                    self.stats["retries_triggered"] += 1
                    continue
                else:
                    raise
        
        # If we get here, we've exhausted retries
        raise AgentError(f"Failed to process query after {self.max_retries} retries")
    
    def _finalize_result(
        self,
        query: str,
        query_id: str,
        plan: Dict[str, Any],
        research: Dict[str, Any],
        verification: Dict[str, Any],
        synthesis: Dict[str, Any],
        reflection: Optional[Dict[str, Any]],
        retry_count: int
    ) -> Dict[str, Any]:
        """
        Finalize and package the result
        
        Args:
            query: Original query
            query_id: Query identifier
            plan: Planning results
            research: Research findings
            verification: Verification report
            synthesis: Synthesis results
            reflection: Reflection results (optional)
            retry_count: Number of retries performed
            
        Returns:
            Final packaged result
        """
        # Extract key information
        answer = synthesis["answer"]
        confidence = synthesis["confidence"]
        citations = synthesis.get("citations", [])
        
        # Build comprehensive result
        result = {
            # User-facing
            "query": query,
            "answer": answer,
            "confidence": confidence,
            "citations": citations,
            "key_points": synthesis.get("key_points", []),
            
            # Metadata
            "query_id": query_id,
            "timestamp": datetime.now().isoformat(),
            "retry_count": retry_count,
            
            # Quality indicators
            "quality": {
                "credibility_level": verification["credibility_assessment"]["credibility_level"],
                "sources_verified": verification["credibility_assessment"]["verified_count"],
                "answer_style": synthesis.get("answer_style", "unknown"),
            },
            
            # Pipeline details (optional, can be hidden from user)
            "pipeline": {
                "plan_confidence": plan.get("confidence", 0),
                "sources_found": research.get("sources_found", 0),
                "sources_analyzed": research.get("sources_fetched", 0),
                "verification_confidence": verification.get("overall_confidence", 0),
                "synthesis_confidence": synthesis.get("confidence", 0),
                "reflection_quality": reflection.get("quality_score", 0) if reflection else None,
            },
            
            # Agent outputs (for debugging/transparency)
            "agent_outputs": {
                "planner": {
                    "strategy": plan["plan"]["strategy"],
                    "agents_used": plan["plan"]["agents"]
                },
                "research": {
                    "themes": research.get("main_themes", []),
                    "findings_count": len(research.get("key_findings", []))
                },
                "verification": {
                    "credibility": verification["credibility_assessment"]["credibility_level"],
                    "conflicts": len(verification.get("conflicts", []))
                },
                "synthesis": {
                    "style": synthesis.get("answer_style", ""),
                    "length": len(answer)
                },
                "reflection": {
                    "quality_level": reflection.get("quality_level", "N/A") if reflection else "skipped",
                    "should_retry": reflection.get("should_retry", False) if reflection else False
                } if reflection else None
            }
        }
        
        return result
    
    def _save_to_long_term_memory(
        self,
        query_id: str,
        query: str,
        result: Dict[str, Any]
    ):
        """
        Save query and results to long-term memory
        
        Args:
            query_id: Query identifier
            query: Original query
            result: Final result
        """
        try:
            # Save query
            self.long_memory.save_query(
                query_id=query_id,
                query_text=query,
                response=result["answer"],
                sources=[c["url"] for c in result.get("citations", [])],
                confidence=result["confidence"],
                metadata={
                    "retry_count": result.get("retry_count", 0),
                    "credibility_level": result["quality"]["credibility_level"],
                    "pipeline": result.get("pipeline", {})
                }
            )
            
            # Save metrics
            self.long_memory.save_metrics(
                query_id=query_id,
                metrics={
                    "confidence": result["confidence"],
                    "response_time": 0,  # Calculated elsewhere
                    "sources_used": len(result.get("citations", [])),
                    "retry_count": result.get("retry_count", 0),
                    "credibility_level": result["quality"]["credibility_level"]
                }
            )
            
            logger.info("Results saved to long-term memory")
            
        except Exception as e:
            logger.warning(f"Failed to save to long-term memory: {e}")
    
    def _generate_query_id(self) -> str:
        """Generate unique query ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"q_{timestamp}_{unique_id}"
    
    def _update_stats(self, success: bool, execution_time: float):
        """
        Update orchestrator statistics
        
        Args:
            success: Whether query was successful
            execution_time: Execution time in seconds
        """
        if success:
            self.stats["successful_queries"] += 1
            
            # Update average execution time
            total_successful = self.stats["successful_queries"]
            current_avg = self.stats["average_execution_time"]
            
            self.stats["average_execution_time"] = (
                (current_avg * (total_successful - 1) + execution_time) / total_successful
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get orchestrator statistics
        
        Returns:
            Statistics dictionary
        """
        success_rate = 0.0
        if self.stats["total_queries"] > 0:
            success_rate = self.stats["successful_queries"] / self.stats["total_queries"]
        
        # Get agent statistics
        agent_stats = {
            "planner": self.planner.get_stats(),
            "researcher": self.researcher.get_stats(),
            "verifier": self.verifier.get_stats(),
            "synthesizer": self.synthesizer.get_stats(),
            "reflector": self.reflector.get_stats()
        }
        
        return {
            **self.stats,
            "success_rate": round(success_rate, 2),
            "agent_stats": agent_stats
        }
    
    def reset_stats(self):
        """Reset all statistics"""
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "retries_triggered": 0,
            "average_execution_time": 0.0
        }
        
        # Reset agent stats
        self.planner.reset_stats()
        self.researcher.reset_stats()
        self.verifier.reset_stats()
        self.synthesizer.reset_stats()
        self.reflector.reset_stats()
        
        logger.info("All statistics reset")


# Global instance
_orchestrator = None


def get_orchestrator() -> Orchestrator:
    """Get or create global Orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
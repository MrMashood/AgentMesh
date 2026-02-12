"""
Planner Agent
Creates execution plans for user queries
Determines which agents to use and in what order
"""

from typing import Dict, Any, List
import json

from app.agents.base import BaseAgent
from app.core.logger import logger


class PlannerAgent(BaseAgent):
    """
    Agent responsible for creating query execution plans.
    Analyzes queries and determines the best approach.
    """
    
    def __init__(self):
        super().__init__(
            name="planner",
            role="a strategic planner that creates execution plans for user queries",
            guidelines=[
                "Analyze the query type and complexity",
                "Determine which agents are needed",
                "Create a clear step-by-step plan",
                "Consider available tools and resources",
                "Prioritize accuracy over speed",
                "Be adaptable to different query types"
            ]
        )
    
    def execute(self, query_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create execution plan for a query
        
        Args:
            query_id: Query identifier
            context: Must contain 'query' key
            
        Returns:
            Plan dictionary with steps and strategy
        """
        # Validate context
        self.validate_context(context, ["query"])
        
        query = context["query"]
        
        logger.info(
            f"Planner analyzing query: {query[:50]}...",
            extra={"query_id": query_id}
        )
        
        # Check for similar past queries
        past_learnings = self._check_similar_queries(query)
        
        # Analyze query characteristics
        query_analysis = self._analyze_query(query)
        
        # Create execution plan
        plan = self._create_plan(query, query_analysis, past_learnings)
        
        # Save insights to long-term memory
        self._save_planning_insights(query, query_analysis, plan)
        
        return {
            "plan": plan,
            "query_analysis": query_analysis,
            "past_learnings": past_learnings,
            "confidence": plan["confidence"]
        }
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query characteristics using LLM
        
        Args:
            query: User query
            
        Returns:
            Analysis dictionary
        """
        analysis_prompt = f"""Analyze this user query and provide structured information:

Query: "{query}"

Provide your analysis in the following JSON format:
{{
    "query_type": "factual|analytical|creative|comparison|how-to|opinion",
    "complexity": "simple|moderate|complex",
    "requires_research": true|false,
    "requires_verification": true|false,
    "key_topics": ["topic1", "topic2"],
    "estimated_sources_needed": number,
    "time_sensitivity": "current|recent|historical|timeless",
    "reasoning": "brief explanation of analysis"
}}"""
        
        messages = [{"role": "user", "content": analysis_prompt}]
        system = self._create_system_prompt(
            additional_context="You are analyzing user queries to plan their execution."
        )
        
        response = self._call_llm(
            messages=messages,
            system=system,
            temperature=0.3  # Low temperature for consistent analysis
        )
        
        # Parse JSON response
        try:
            # Extract JSON from response
            text = response["text"].strip()
            
            # Find JSON in response (handle markdown code blocks)
            if "```json" in text:
                json_start = text.index("```json") + 7
                json_end = text.index("```", json_start)
                text = text[json_start:json_end].strip()
            elif "```" in text:
                json_start = text.index("```") + 3
                json_end = text.index("```", json_start)
                text = text[json_start:json_end].strip()
            
            analysis = json.loads(text)
            logger.info(f"Query analysis: {analysis['query_type']}, {analysis['complexity']}")
            return analysis
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse analysis JSON: {e}, using defaults")
            # Return default analysis
            return {
                "query_type": "factual",
                "complexity": "moderate",
                "requires_research": True,
                "requires_verification": True,
                "key_topics": [],
                "estimated_sources_needed": 3,
                "time_sensitivity": "timeless",
                "reasoning": "Default analysis due to parsing error"
            }
    
    def _check_similar_queries(self, query: str) -> List[Dict]:
        """
        Check long-term memory for similar past queries
        
        Args:
            query: Current query
            
        Returns:
            List of relevant past learnings
        """
        try:
            # Search query history
            similar_queries = self.long_memory.search_history(query, limit=3)
            
            if similar_queries:
                logger.info(f"Found {len(similar_queries)} similar past queries")
                return [
                    {
                        "query": q.get("query_text", ""),
                        "confidence": q.get("confidence", 0),
                        "sources_used": len(q.get("sources", []))
                    }
                    for q in similar_queries
                ]
            
            return []
            
        except Exception as e:
            logger.warning(f"Failed to check similar queries: {e}")
            return []
    
    def _create_plan(
        self,
        query: str,
        analysis: Dict[str, Any],
        past_learnings: List[Dict]
    ) -> Dict[str, Any]:
        """
        Create execution plan based on analysis
        
        Args:
            query: User query
            analysis: Query analysis
            past_learnings: Similar past queries
            
        Returns:
            Execution plan
        """
        # Determine which agents to use
        agents_needed = []
        
        # Always use research agent for new information
        if analysis.get("requires_research", True):
            agents_needed.append("research")
        
        # Use verification for factual queries
        if analysis.get("requires_verification", True):
            agents_needed.append("verification")
        
        # Always use synthesis to create answer
        agents_needed.append("synthesis")
        
        # Use reflection for complex queries
        if analysis.get("complexity") in ["complex", "moderate"]:
            agents_needed.append("reflection")
        
        # Create detailed steps
        steps = []
        
        # Step 1: Research
        if "research" in agents_needed:
            steps.append({
                "step": len(steps) + 1,
                "agent": "research",
                "action": "Search for information on: " + ", ".join(analysis.get("key_topics", [query[:30]])),
                "estimated_sources": analysis.get("estimated_sources_needed", 3)
            })
        
        # Step 2: Verification
        if "verification" in agents_needed:
            steps.append({
                "step": len(steps) + 1,
                "agent": "verification",
                "action": "Verify facts from multiple sources and check reliability",
                "priority": "high" if analysis.get("query_type") == "factual" else "medium"
            })
        
        # Step 3: Synthesis
        steps.append({
            "step": len(steps) + 1,
            "agent": "synthesis",
            "action": "Combine findings into comprehensive answer",
            "style": self._determine_answer_style(analysis)
        })
        
        # Step 4: Reflection
        if "reflection" in agents_needed:
            steps.append({
                "step": len(steps) + 1,
                "agent": "reflection",
                "action": "Review answer quality and suggest improvements",
                "threshold": 0.8  # Minimum acceptable quality
            })
        
        # Calculate confidence based on past performance
        confidence = self._estimate_confidence(analysis, past_learnings)
        
        plan = {
            # "query_id": self.short_memory.get_query(query)["query_id"] if self.short_memory.get_query(query) else "unknown",
            "strategy": self._determine_strategy(analysis),
            "agents": agents_needed,
            "steps": steps,
            "estimated_time": len(steps) * 2,  # Rough estimate: 2s per step
            "confidence": confidence,
            "notes": self._generate_plan_notes(analysis, past_learnings)
        }
        
        logger.info(
            f"Plan created with {len(steps)} steps",
            extra={
                "agents": agents_needed,
                "confidence": confidence
            }
        )
        
        return plan
    
    def _determine_strategy(self, analysis: Dict[str, Any]) -> str:
        """
        Determine execution strategy based on analysis
        
        Args:
            analysis: Query analysis
            
        Returns:
            Strategy name
        """
        query_type = analysis.get("query_type", "factual")
        complexity = analysis.get("complexity", "moderate")
        
        if query_type == "factual" and complexity == "simple":
            return "quick_lookup"
        elif query_type in ["analytical", "comparison"]:
            return "deep_research"
        elif complexity == "complex":
            return "comprehensive_analysis"
        else:
            return "standard_research"
    
    def _determine_answer_style(self, analysis: Dict[str, Any]) -> str:
        """
        Determine appropriate answer style
        
        Args:
            analysis: Query analysis
            
        Returns:
            Answer style
        """
        query_type = analysis.get("query_type", "factual")
        
        style_map = {
            "factual": "concise and direct",
            "analytical": "detailed with reasoning",
            "creative": "engaging and narrative",
            "comparison": "structured comparison",
            "how-to": "step-by-step guide",
            "opinion": "balanced with multiple perspectives"
        }
        
        return style_map.get(query_type, "clear and informative")
    
    def _estimate_confidence(
        self,
        analysis: Dict[str, Any],
        past_learnings: List[Dict]
    ) -> float:
        """
        Estimate confidence in plan success
        
        Args:
            analysis: Query analysis
            past_learnings: Similar past queries
            
        Returns:
            Confidence score (0-1)
        """
        base_confidence = 0.7
        
        # Adjust based on complexity
        complexity = analysis.get("complexity", "moderate")
        if complexity == "simple":
            base_confidence += 0.2
        elif complexity == "complex":
            base_confidence -= 0.1
        
        # Adjust based on past success
        if past_learnings:
            avg_past_confidence = sum(
                p.get("confidence", 0) for p in past_learnings
            ) / len(past_learnings)
            base_confidence = (base_confidence + avg_past_confidence) / 2
        
        # Ensure within bounds
        return max(0.5, min(0.95, base_confidence))
    
    def _generate_plan_notes(
        self,
        analysis: Dict[str, Any],
        past_learnings: List[Dict]
    ) -> List[str]:
        """
        Generate helpful notes for plan execution
        
        Args:
            analysis: Query analysis
            past_learnings: Similar past queries
            
        Returns:
            List of notes
        """
        notes = []
        
        # Time sensitivity notes
        if analysis.get("time_sensitivity") == "current":
            notes.append("Focus on most recent information (last 6 months)")
        
        # Complexity notes
        if analysis.get("complexity") == "complex":
            notes.append("This is a complex query - allow extra time for thorough research")
        
        # Past learnings notes
        if past_learnings:
            notes.append(f"Found {len(past_learnings)} similar past queries - check for reusable insights")
        
        # Source recommendations
        estimated_sources = analysis.get("estimated_sources_needed", 3)
        if estimated_sources > 5:
            notes.append("Query requires extensive research - prioritize authoritative sources")
        
        return notes
    
    def _save_planning_insights(
        self,
        query: str,
        analysis: Dict[str, Any],
        plan: Dict[str, Any]
    ):
        """
        Save planning insights to long-term memory
        
        Args:
            query: User query
            analysis: Query analysis
            plan: Execution plan
        """
        try:
            # Extract key topic
            topics = analysis.get("key_topics", [])
            topic = topics[0] if topics else "general_query"
            
            # Create insight
            insight = f"Query type '{analysis.get('query_type')}' with complexity '{analysis.get('complexity')}' requires {len(plan['agents'])} agents"
            
            # Save to long-term memory
            self._save_learning(
                topic=f"planning_{topic}",
                insight=insight,
                confidence=plan["confidence"],
                sources=["planner_agent"]
            )
            
        except Exception as e:
            logger.warning(f"Failed to save planning insights: {e}")


def get_planner_agent() -> PlannerAgent:
    """Get or create PlannerAgent instance"""
    return PlannerAgent()
"""
Reflection Agent
Reviews answer quality and suggests improvements
Ensures the final output meets high standards
"""

from typing import Dict, Any, List
import json

from app.agents.base import BaseAgent
from app.core.logger import logger


class ReflectionAgent(BaseAgent):
    """
    Agent responsible for reflecting on answer quality.
    Reviews synthesis results and suggests improvements.
    """
    
    def __init__(self):
        super().__init__(
            name="reflection",
            role="a quality assurance specialist that reviews answers and ensures they meet high standards",
            guidelines=[
                "Evaluate answer completeness and accuracy",
                "Check if the query was fully addressed",
                "Assess clarity and coherence",
                "Identify gaps or missing information",
                "Suggest specific improvements",
                "Compare against best practices",
                "Consider user perspective",
                "Be constructive and actionable"
            ]
        )
        
        # Quality thresholds
        self.min_acceptable_quality = 0.70
        self.excellent_quality = 0.90
        self.retry_threshold = 0.60
    
    def execute(self, query_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reflect on answer quality
        
        Args:
            query_id: Query identifier
            context: Must contain 'query', 'synthesis_result', 'verification_report'
            
        Returns:
            Reflection results with quality assessment
        """
        # Validate context
        self.validate_context(context, ["query", "synthesis_result"])
        
        query = context["query"]
        synthesis = context["synthesis_result"]
        verification = context.get("verification_report", {})
        plan = context.get("plan", {})
        
        logger.info(
            f"Reflection agent starting for: {query[:50]}...",
            extra={"query_id": query_id}
        )
        
        # Evaluate answer quality
        quality_assessment = self._evaluate_quality(
            query=query,
            answer=synthesis["answer"],
            synthesis=synthesis,
            verification=verification
        )
        
        # Check completeness
        completeness_check = self._check_completeness(
            query=query,
            answer=synthesis["answer"],
            key_points=synthesis.get("key_points", [])
        )
        
        # Identify improvements
        improvements = self._identify_improvements(
            query=query,
            synthesis=synthesis,
            quality_assessment=quality_assessment,
            completeness_check=completeness_check
        )
        
        # Compare with similar past queries
        comparison = self._compare_with_history(query, synthesis)
        
        # Determine if retry is needed
        should_retry = self._should_retry(
            quality_assessment=quality_assessment,
            completeness_check=completeness_check,
            synthesis_confidence=synthesis["confidence"]
        )
        
        # Generate reflection summary
        summary = self._generate_reflection_summary(
            quality_assessment=quality_assessment,
            completeness_check=completeness_check,
            improvements=improvements,
            should_retry=should_retry
        )
        
        # Save reflection insights
        self._save_reflection_insights(
            query=query,
            quality_assessment=quality_assessment,
            improvements=improvements
        )
        
        result = {
            "quality_score": quality_assessment["overall_score"],
            "quality_level": quality_assessment["quality_level"],
            "completeness_score": completeness_check["score"],
            "strengths": quality_assessment["strengths"],
            "weaknesses": quality_assessment["weaknesses"],
            "improvements": improvements,
            "should_retry": should_retry,
            "retry_reason": improvements[0] if should_retry and improvements else None,
            "comparison_with_history": comparison,
            "reflection_summary": summary,
            "detailed_assessment": quality_assessment
        }
        
        logger.info(
            "Reflection completed",
            extra={
                "quality_score": result["quality_score"],
                "should_retry": should_retry
            }
        )
        
        return result
    
    def _evaluate_quality(
        self,
        query: str,
        answer: str,
        synthesis: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate overall answer quality using LLM
        
        Args:
            query: Original query
            answer: Synthesized answer
            synthesis: Synthesis results
            verification: Verification report
            
        Returns:
            Quality assessment
        """
        # Prepare context
        answer_preview = answer[:1000]  # First 1000 chars
        citations_count = len(synthesis.get("citations", []))
        confidence = synthesis.get("confidence", 0)
        
        prompt = f"""Evaluate the quality of this answer to the user's query:

Query: "{query}"

Answer: "{answer_preview}..."

Answer Metadata:
- Confidence: {confidence:.2f}
- Sources cited: {citations_count}
- Verification credibility: {verification.get('credibility_assessment', {}).get('credibility_level', 'unknown')}

Evaluate the answer on these criteria:
1. **Accuracy**: Is the information correct and well-sourced?
2. **Completeness**: Does it fully answer the query?
3. **Clarity**: Is it clear and easy to understand?
4. **Structure**: Is it well-organized?
5. **Relevance**: Does it stay focused on the query?

Provide your evaluation in JSON format:
{{
    "overall_score": 0.0-1.0,
    "quality_level": "excellent|good|acceptable|poor",
    "criteria_scores": {{
        "accuracy": 0.0-1.0,
        "completeness": 0.0-1.0,
        "clarity": 0.0-1.0,
        "structure": 0.0-1.0,
        "relevance": 0.0-1.0
    }},
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "reasoning": "brief explanation of the assessment"
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        system = self._create_system_prompt(
            additional_context="You are evaluating answer quality objectively and constructively."
        )
        
        response = self._call_llm(
            messages=messages,
            system=system,
            temperature=0.3
        )
        
        # Parse response
        try:
            text = response["text"].strip()
            
            # Extract JSON
            if "```json" in text:
                json_start = text.index("```json") + 7
                json_end = text.index("```", json_start)
                text = text[json_start:json_end].strip()
            elif "```" in text:
                json_start = text.index("```") + 3
                json_end = text.index("```", json_start)
                text = text[json_start:json_end].strip()
            
            assessment = json.loads(text)
            
            logger.info(
                f"Quality assessment: {assessment['quality_level']}",
                extra={"score": assessment["overall_score"]}
            )
            
            return assessment
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse quality assessment: {e}")
            
            # Return default assessment
            return {
                "overall_score": 0.7,
                "quality_level": "acceptable",
                "criteria_scores": {
                    "accuracy": 0.7,
                    "completeness": 0.7,
                    "clarity": 0.7,
                    "structure": 0.7,
                    "relevance": 0.7
                },
                "strengths": ["Answer generated successfully"],
                "weaknesses": ["Quality assessment failed"],
                "reasoning": "Default assessment due to parsing error"
            }
    
    def _check_completeness(
        self,
        query: str,
        answer: str,
        key_points: List[str]
    ) -> Dict[str, Any]:
        """
        Check if answer completely addresses the query
        
        Args:
            query: Original query
            answer: Synthesized answer
            key_points: Key points from synthesis
            
        Returns:
            Completeness check results
        """
        prompt = f"""Check if this answer completely addresses the user's query:

Query: "{query}"

Answer (first 800 chars): "{answer[:800]}..."

Key Points Covered:
{chr(10).join(f"- {point}" for point in key_points[:5])}

Questions to answer:
1. Does the answer directly address the main question?
2. Are there any aspects of the query left unanswered?
3. Does it provide sufficient detail?
4. Are there any obvious gaps?

Respond in JSON:
{{
    "score": 0.0-1.0,
    "directly_addresses_query": true|false,
    "missing_aspects": ["aspect1", "aspect2"],
    "sufficient_detail": true|false,
    "gaps": ["gap1", "gap2"],
    "reasoning": "brief explanation"
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        system = self._create_system_prompt(
            additional_context="You are checking answer completeness objectively."
        )
        
        response = self._call_llm(
            messages=messages,
            system=system,
            temperature=0.3
        )
        
        # Parse response
        try:
            text = response["text"].strip()
            
            # Extract JSON
            if "```json" in text:
                json_start = text.index("```json") + 7
                json_end = text.index("```", json_start)
                text = text[json_start:json_end].strip()
            elif "```" in text:
                json_start = text.index("```") + 3
                json_end = text.index("```", json_start)
                text = text[json_start:json_end].strip()
            
            check = json.loads(text)
            
            logger.info(f"Completeness score: {check['score']:.2f}")
            
            return check
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse completeness check: {e}")
            
            return {
                "score": 0.7,
                "directly_addresses_query": True,
                "missing_aspects": [],
                "sufficient_detail": True,
                "gaps": [],
                "reasoning": "Default check due to parsing error"
            }
    
    def _identify_improvements(
        self,
        query: str,
        synthesis: Dict[str, Any],
        quality_assessment: Dict[str, Any],
        completeness_check: Dict[str, Any]
    ) -> List[str]:
        """
        Identify specific improvements for the answer
        
        Args:
            query: Original query
            synthesis: Synthesis results
            quality_assessment: Quality assessment
            completeness_check: Completeness check
            
        Returns:
            List of improvement suggestions
        """
        improvements = []
        
        # Check quality weaknesses
        weaknesses = quality_assessment.get("weaknesses", [])
        for weakness in weaknesses:
            improvements.append(f"Address weakness: {weakness}")
        
        # Check completeness gaps
        gaps = completeness_check.get("gaps", [])
        for gap in gaps:
            improvements.append(f"Fill gap: {gap}")
        
        # Check missing aspects
        missing = completeness_check.get("missing_aspects", [])
        for aspect in missing:
            improvements.append(f"Add information about: {aspect}")
        
        # Check citation count
        if len(synthesis.get("citations", [])) < 2:
            improvements.append("Add more source citations for credibility")
        
        # Check confidence
        if synthesis.get("confidence", 0) < 0.7:
            improvements.append("Strengthen confidence by adding more verified findings")
        
        # Check criteria scores
        criteria = quality_assessment.get("criteria_scores", {})
        for criterion, score in criteria.items():
            if score < 0.7:
                improvements.append(f"Improve {criterion} (current score: {score:.2f})")
        
        # If no specific improvements, note that
        if not improvements:
            improvements.append("No specific improvements needed - answer is satisfactory")
        
        logger.info(f"Identified {len(improvements)} potential improvements")
        
        return improvements[:5]  # Limit to top 5
    
    def _compare_with_history(
        self,
        query: str,
        synthesis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare with similar past queries
        
        Args:
            query: Current query
            synthesis: Synthesis results
            
        Returns:
            Comparison results
        """
        try:
            # Search for similar past queries
            similar = self.long_memory.search_history(query, limit=3)
            
            if not similar:
                return {
                    "similar_queries_found": 0,
                    "comparison": "No similar past queries for comparison"
                }
            
            # Calculate average past confidence
            avg_past_confidence = sum(
                q.get("confidence", 0) for q in similar
            ) / len(similar)
            
            current_confidence = synthesis.get("confidence", 0)
            
            # Determine performance
            if current_confidence >= avg_past_confidence + 0.1:
                performance = "better than average"
            elif current_confidence <= avg_past_confidence - 0.1:
                performance = "below average"
            else:
                performance = "similar to average"
            
            return {
                "similar_queries_found": len(similar),
                "average_past_confidence": round(avg_past_confidence, 2),
                "current_confidence": round(current_confidence, 2),
                "performance": performance,
                "comparison": f"This answer performs {performance} compared to {len(similar)} similar past queries"
            }
            
        except Exception as e:
            logger.warning(f"Failed to compare with history: {e}")
            return {
                "similar_queries_found": 0,
                "comparison": "Comparison unavailable"
            }
    
    def _should_retry(
        self,
        quality_assessment: Dict[str, Any],
        completeness_check: Dict[str, Any],
        synthesis_confidence: float
    ) -> bool:
        """
        Determine if the answer should be regenerated
        
        Args:
            quality_assessment: Quality assessment
            completeness_check: Completeness check
            synthesis_confidence: Synthesis confidence score
            
        Returns:
            True if retry is recommended
        """
        # Check if quality is below retry threshold
        if quality_assessment["overall_score"] < self.retry_threshold:
            logger.warning(
                f"Quality below retry threshold: {quality_assessment['overall_score']:.2f}"
            )
            return True
        
        # Check if completeness is poor
        if completeness_check["score"] < self.retry_threshold:
            logger.warning(
                f"Completeness below retry threshold: {completeness_check['score']:.2f}"
            )
            return True
        
        # Check if synthesis confidence is very low
        if synthesis_confidence < 0.5:
            logger.warning(f"Synthesis confidence very low: {synthesis_confidence:.2f}")
            return True
        
        # Check if answer doesn't address query
        if not completeness_check.get("directly_addresses_query", True):
            logger.warning("Answer does not directly address query")
            return True
        
        return False
    
    def _generate_reflection_summary(
        self,
        quality_assessment: Dict[str, Any],
        completeness_check: Dict[str, Any],
        improvements: List[str],
        should_retry: bool
    ) -> str:
        """
        Generate human-readable reflection summary
        
        Args:
            quality_assessment: Quality assessment
            completeness_check: Completeness check
            improvements: List of improvements
            should_retry: Whether retry is recommended
            
        Returns:
            Summary text
        """
        quality_level = quality_assessment["quality_level"].upper()
        quality_score = quality_assessment["overall_score"]
        completeness = completeness_check["score"]
        
        summary_parts = [
            f"Quality: {quality_level} ({quality_score:.2f}/1.0).",
            f"Completeness: {completeness:.2f}/1.0."
        ]
        
        if should_retry:
            summary_parts.append(
                f"RECOMMENDATION: Retry suggested - {improvements[0] if improvements else 'quality below threshold'}."
            )
        else:
            summary_parts.append("RECOMMENDATION: Answer is acceptable, proceed to user.")
        
        if quality_assessment.get("strengths"):
            summary_parts.append(
                f"Strengths: {', '.join(quality_assessment['strengths'][:2])}."
            )
        
        return " ".join(summary_parts)
    
    def _save_reflection_insights(
        self,
        query: str,
        quality_assessment: Dict[str, Any],
        improvements: List[str]
    ):
        """
        Save reflection insights to long-term memory
        
        Args:
            query: Original query
            quality_assessment: Quality assessment
            improvements: List of improvements
        """
        try:
            # Extract topic
            words = query.lower().split()
            topic = "_".join([w for w in words if len(w) > 4][:2])
            
            if not topic:
                topic = "general"
            
            # Save quality patterns
            quality_level = quality_assessment["quality_level"]
            
            insight = f"Answers of '{quality_level}' quality typically score {quality_assessment['overall_score']:.2f}"
            
            self._save_learning(
                topic=f"reflection_{topic}",
                insight=insight,
                confidence=quality_assessment["overall_score"],
                sources=["reflection_agent"]
            )
            
            logger.info("Reflection insights saved to long-term memory")
            
        except Exception as e:
            logger.warning(f"Failed to save reflection insights: {e}")


def get_reflection_agent() -> ReflectionAgent:
    """Get or create ReflectionAgent instance"""
    return ReflectionAgent()
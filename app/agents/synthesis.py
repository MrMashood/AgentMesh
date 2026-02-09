"""
Synthesis Agent
Combines research and verification results into comprehensive answers
Creates well-structured, accurate responses
"""

from typing import Dict, Any, List
import json

from app.agents.base import BaseAgent
from app.core.logger import logger


class SynthesisAgent(BaseAgent):
    """
    Agent responsible for synthesizing final answers.
    Combines research findings and verification results into coherent responses.
    """
    
    def __init__(self):
        super().__init__(
            name="synthesis",
            role="a synthesis specialist that creates comprehensive, well-structured answers from research findings",
            guidelines=[
                "Combine information from multiple sources coherently",
                "Prioritize verified and high-confidence findings",
                "Structure answers clearly and logically",
                "Cite sources appropriately",
                "Address the original query directly",
                "Acknowledge uncertainties or conflicts",
                "Adapt tone and style to query type",
                "Be concise yet comprehensive"
            ]
        )
    
    def execute(self, query_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize final answer from research and verification
        
        Args:
            query_id: Query identifier
            context: Must contain 'query', 'research_findings', 'verification_report'
            
        Returns:
            Synthesis results with final answer
        """
        # Validate context
        self.validate_context(context, ["query", "research_findings", "verification_report"])
        
        query = context["query"]
        research = context["research_findings"]
        verification = context["verification_report"]
        plan = context.get("plan", {})
        
        logger.info(
            f"Synthesis agent starting for: {query[:50]}...",
            extra={"query_id": query_id}
        )
        
        # Determine answer style from plan
        answer_style = self._determine_answer_style(query, plan)
        
        # Prepare synthesis materials
        synthesis_materials = self._prepare_synthesis_materials(
            research=research,
            verification=verification
        )
        
        # Generate final answer using LLM
        final_answer = self._generate_answer(
            query=query,
            materials=synthesis_materials,
            style=answer_style,
            verification=verification
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            verification=verification,
            answer_quality=final_answer.get("quality_score", 0.8)
        )
        
        # Extract and format citations
        citations = self._format_citations(
            research=research,
            verification=verification
        )
        
        # Create synthesis metadata
        metadata = self._create_metadata(
            research=research,
            verification=verification,
            answer_length=len(final_answer.get("answer", ""))
        )
        
        # Save synthesis insights
        self._save_synthesis_insights(query, final_answer, confidence_score)
        
        result = {
            "answer": final_answer.get("answer", ""),
            "confidence": confidence_score,
            "citations": citations,
            "answer_style": answer_style,
            "key_points": final_answer.get("key_points", []),
            "caveats": final_answer.get("caveats", []),
            "metadata": metadata,
            "quality_indicators": {
                "sources_used": len(citations),
                "verified_findings": verification["credibility_assessment"]["verified_count"],
                "credibility_level": verification["credibility_assessment"]["credibility_level"]
            }
        }
        
        logger.info(
            "Answer synthesized",
            extra={
                "confidence": confidence_score,
                "answer_length": len(result["answer"]),
                "sources": len(citations)
            }
        )
        
        return result
    
    def _determine_answer_style(
        self,
        query: str,
        plan: Dict[str, Any]
    ) -> str:
        """
        Determine appropriate answer style
        
        Args:
            query: Original query
            plan: Execution plan
            
        Returns:
            Answer style string
        """
        # Get style from plan if available
        if plan:
            for step in plan.get("steps", []):
                if step.get("agent") == "synthesis" and "style" in step:
                    return step["style"]
        
        # Infer from query
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["how to", "how do i", "tutorial", "guide"]):
            return "step-by-step guide"
        elif any(word in query_lower for word in ["compare", "difference", "versus", "vs"]):
            return "structured comparison"
        elif any(word in query_lower for word in ["why", "explain", "what is"]):
            return "detailed explanation"
        elif any(word in query_lower for word in ["latest", "recent", "current", "news"]):
            return "current summary"
        else:
            return "clear and informative"
    
    def _prepare_synthesis_materials(
        self,
        research: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare materials for synthesis
        
        Args:
            research: Research findings
            verification: Verification report
            
        Returns:
            Organized synthesis materials
        """
        # Prioritize verified findings
        verified = verification.get("verified_findings", [])
        high_confidence = verification.get("high_confidence_findings", [])
        
        # Extract key themes
        themes = research.get("main_themes", [])
        
        # Get source information
        sources = research.get("search_results", [])
        
        # Identify conflicts that need addressing
        conflicts = verification.get("conflicts", [])
        
        materials = {
            "verified_findings": verified,
            "high_confidence_findings": high_confidence,
            "themes": themes,
            "sources": sources[:5],  # Top 5 sources
            "conflicts": conflicts,
            "research_summary": research.get("summary", ""),
            "credibility_level": verification["credibility_assessment"]["credibility_level"]
        }
        
        return materials
    
    def _generate_answer(
        self,
        query: str,
        materials: Dict[str, Any],
        style: str,
        verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate final answer using LLM
        
        Args:
            query: Original query
            materials: Synthesis materials
            style: Answer style
            verification: Verification report
            
        Returns:
            Generated answer with metadata
        """
        # Prepare verified findings text
        findings_text = self._format_findings_for_llm(
            materials["verified_findings"],
            materials["high_confidence_findings"]
        )
        
        # Prepare conflicts text
        conflicts_text = self._format_conflicts_for_llm(materials["conflicts"])
        
        # Create synthesis prompt
        prompt = f"""Create a comprehensive answer to this question using the verified research findings:

Question: "{query}"

Answer Style: {style}

Verified Research Findings:
{findings_text}

{f"Important Conflicts to Address:\n{conflicts_text}\n" if conflicts_text else ""}

Main Themes: {', '.join(materials['themes'][:5])}

Overall Credibility: {materials['credibility_level'].upper()}

Instructions:
1. Answer the question directly and comprehensively
2. Use ONLY the verified findings provided
3. Structure your answer according to the specified style
4. {"Address the conflicts by presenting different perspectives" if conflicts_text else "Maintain consistency throughout"}
5. Cite sources naturally within the text (e.g., "according to [source]")
6. Be clear about any uncertainties or limitations
7. Keep the answer focused and relevant

Provide your response in JSON format:
{{
    "answer": "the complete answer text with inline citations",
    "key_points": ["main point 1", "main point 2", "main point 3"],
    "caveats": ["any important limitations or uncertainties"],
    "quality_score": 0.0-1.0
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        system = self._create_system_prompt(
            additional_context="You are synthesizing research findings into a clear, accurate answer."
        )
        
        response = self._call_llm(
            messages=messages,
            system=system,
            temperature=0.4,  # Balanced creativity and consistency
            max_tokens=2048
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
            
            answer_data = json.loads(text)
            
            logger.info(
                f"Answer generated: {len(answer_data.get('answer', ''))} characters",
                extra={"quality_score": answer_data.get("quality_score", 0)}
            )
            
            return answer_data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse answer JSON: {e}")
            
            # Return the raw text as answer
            return {
                "answer": response["text"],
                "key_points": [],
                "caveats": ["Answer formatting failed - showing raw response"],
                "quality_score": 0.5
            }
    
    def _format_findings_for_llm(
        self,
        verified: List[Dict],
        high_confidence: List[Dict]
    ) -> str:
        """
        Format findings for LLM input
        
        Args:
            verified: Verified findings
            high_confidence: High confidence findings
            
        Returns:
            Formatted text
        """
        lines = []
        
        # Combine and deduplicate
        all_findings = verified + [f for f in high_confidence if f not in verified]
        
        for i, finding in enumerate(all_findings[:10], 1):  # Limit to 10
            lines.append(
                f"{i}. {finding.get('finding', '')} "
                f"(Confidence: {finding.get('confidence', 0):.2f}, "
                f"Sources: {', '.join(finding.get('supporting_sources', [])[:2])})"
            )
        
        return "\n".join(lines) if lines else "No verified findings available"
    
    def _format_conflicts_for_llm(self, conflicts: List[Dict]) -> str:
        """
        Format conflicts for LLM
        
        Args:
            conflicts: List of conflicts
            
        Returns:
            Formatted text
        """
        if not conflicts:
            return ""
        
        lines = []
        for i, conflict in enumerate(conflicts, 1):
            lines.append(
                f"{i}. {conflict.get('conflict_type', 'Unknown')}: "
                f"{conflict.get('explanation', 'No explanation')}"
            )
        
        return "\n".join(lines)
    
    def _calculate_confidence(
        self,
        verification: Dict[str, Any],
        answer_quality: float
    ) -> float:
        """
        Calculate overall confidence score
        
        Args:
            verification: Verification report
            answer_quality: Quality score from answer generation
            
        Returns:
            Confidence score (0-1)
        """
        # Get verification confidence
        verification_confidence = verification.get("overall_confidence", 0.5)
        
        # Get credibility level
        credibility = verification["credibility_assessment"]["credibility_level"]
        credibility_score = {
            "high": 0.9,
            "medium": 0.7,
            "low": 0.5
        }.get(credibility, 0.5)
        
        # Weighted average
        confidence = (
            verification_confidence * 0.4 +
            credibility_score * 0.4 +
            answer_quality * 0.2
        )
        
        # Ensure within bounds
        return max(0.0, min(1.0, round(confidence, 2)))
    
    def _format_citations(
        self,
        research: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Format citations from sources
        
        Args:
            research: Research findings
            verification: Verification report
            
        Returns:
            List of formatted citations
        """
        citations = []
        seen_urls = set()
        
        # Get sources from verified findings
        for finding in verification.get("verified_findings", []):
            for source in finding.get("supporting_sources", []):
                if source and source not in seen_urls:
                    seen_urls.add(source)
                    
                    # Find matching search result for title
                    title = "Source"
                    for result in research.get("search_results", []):
                        if source in result.get("url", ""):
                            title = result.get("title", "Source")
                            break
                    
                    citations.append({
                        "url": source,
                        "title": title,
                        "reliability": verification["source_reliability"].get(
                            self._extract_domain(source), 0.5
                        )
                    })
        
        # Sort by reliability
        citations.sort(key=lambda x: x["reliability"], reverse=True)
        
        return citations[:10]  # Limit to 10 citations
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc if url.startswith('http') else url
        except Exception:
            return url
    
    def _create_metadata(
        self,
        research: Dict[str, Any],
        verification: Dict[str, Any],
        answer_length: int
    ) -> Dict[str, Any]:
        """
        Create synthesis metadata
        
        Args:
            research: Research findings
            verification: Verification report
            answer_length: Length of generated answer
            
        Returns:
            Metadata dictionary
        """
        return {
            "sources_searched": research.get("sources_found", 0),
            "sources_analyzed": research.get("sources_fetched", 0),
            "findings_verified": verification["credibility_assessment"]["verified_count"],
            "conflicts_resolved": len(verification.get("conflicts", [])),
            "answer_length_chars": answer_length,
            "credibility_level": verification["credibility_assessment"]["credibility_level"]
        }
    
    def _save_synthesis_insights(
        self,
        query: str,
        answer: Dict[str, Any],
        confidence: float
    ):
        """
        Save synthesis insights to long-term memory
        
        Args:
            query: Original query
            answer: Generated answer
            confidence: Confidence score
        """
        try:
            # Extract topic from query
            words = query.lower().split()
            topic = "_".join([w for w in words if len(w) > 4][:2])
            
            if not topic:
                topic = "general"
            
            # Save key points as learnings
            for point in answer.get("key_points", [])[:3]:
                if point:
                    self._save_learning(
                        topic=f"synthesis_{topic}",
                        insight=point,
                        confidence=confidence,
                        sources=["synthesis_agent"]
                    )
            
            logger.info("Synthesis insights saved to long-term memory")
            
        except Exception as e:
            logger.warning(f"Failed to save synthesis insights: {e}")


def get_synthesis_agent() -> SynthesisAgent:
    """Get or create SynthesisAgent instance"""
    return SynthesisAgent()
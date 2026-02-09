"""
Verification Agent
Verifies research findings and checks source reliability
Cross-checks facts from multiple sources
"""

from typing import Dict, Any, List
import json
from collections import Counter

from app.agents.base import BaseAgent
from app.core.logger import logger


class VerificationAgent(BaseAgent):
    """
    Agent responsible for verifying research findings.
    Cross-checks facts, validates sources, and scores confidence.
    """
    
    def __init__(self):
        super().__init__(
            name="verification",
            role="a fact-checker that verifies information accuracy and source reliability",
            guidelines=[
                "Cross-check facts across multiple sources",
                "Evaluate source credibility and authority",
                "Identify conflicting information",
                "Score confidence levels for each claim",
                "Prioritize authoritative sources",
                "Flag unverified or uncertain claims",
                "Check for bias or misinformation"
            ]
        )
        
        # Verification thresholds
        self.min_sources_for_verification = 2
        self.high_confidence_threshold = 0.85
        self.low_confidence_threshold = 0.60
    
    def execute(self, query_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify research findings
        
        Args:
            query_id: Query identifier
            context: Must contain 'query' and 'research_findings'
            
        Returns:
            Verification results dictionary
        """
        # Validate context
        self.validate_context(context, ["query", "research_findings"])
        
        query = context["query"]
        research_findings = context["research_findings"]
        
        logger.info(
            f"Verification agent starting for: {query[:50]}...",
            extra={"query_id": query_id}
        )
        
        # Get source reliability scores from long-term memory
        source_scores = self._get_source_reliability(research_findings)
        
        # Verify key findings
        verified_findings = self._verify_findings(
            findings=research_findings.get("key_findings", []),
            research_data=research_findings,
            source_scores=source_scores
        )
        
        # Check for conflicts
        conflicts = self._identify_conflicts(research_findings)
        
        # Assess overall credibility
        credibility_assessment = self._assess_credibility(
            research_findings=research_findings,
            source_scores=source_scores,
            verified_findings=verified_findings
        )
        
        # Generate verification report
        report = self._generate_verification_report(
            query=query,
            verified_findings=verified_findings,
            conflicts=conflicts,
            credibility_assessment=credibility_assessment,
            source_scores=source_scores
        )
        
        # Update source reliability based on verification
        self._update_source_reliability(report)
        
        return report
    
    def _get_source_reliability(
        self,
        research_findings: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Get reliability scores for sources from long-term memory
        
        Args:
            research_findings: Research findings with sources
            
        Returns:
            Dictionary mapping domains to reliability scores
        """
        source_scores = {}
        
        # Extract domains from extracted content
        for content in research_findings.get("extracted_content", []):
            domain = content.get("domain", "")
            if domain:
                score = self.long_memory.get_source_score(domain)
                source_scores[domain] = score if score is not None else 0.5  # Default neutral
        
        # Extract domains from search results
        for result in research_findings.get("search_results", []):
            url = result.get("url", "")
            if url:
                # Extract domain from URL
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                    if domain and domain not in source_scores:
                        score = self.long_memory.get_source_score(domain)
                        source_scores[domain] = score if score is not None else 0.5
                except Exception:
                    pass
        
        logger.info(f"Retrieved reliability scores for {len(source_scores)} sources")
        return source_scores
    
    def _verify_findings(
        self,
        findings: List[Dict],
        research_data: Dict[str, Any],
        source_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Verify each key finding using LLM
        
        Args:
            findings: List of key findings to verify
            research_data: Full research data
            source_scores: Source reliability scores
            
        Returns:
            List of verified findings with confidence scores
        """
        if not findings:
            logger.warning("No findings to verify")
            return []
        
        # Prepare verification prompt
        findings_text = "\n".join([
            f"{i+1}. {f.get('finding', '')} (Sources: {', '.join(f.get('sources', []))})"
            for i, f in enumerate(findings)
        ])
        
        source_info = "\n".join([
            f"- {domain}: {score:.2f} reliability"
            for domain, score in source_scores.items()
        ])
        
        prompt = f"""Verify these research findings and assess their accuracy:

Findings to verify:
{findings_text}

Source Reliability Scores:
{source_info}

For each finding, evaluate:
1. Is it supported by multiple sources?
2. Are the sources authoritative?
3. Are there any conflicts or contradictions?
4. What is the confidence level?

Provide your verification in JSON format:
{{
    "verified_findings": [
        {{
            "finding": "the finding text",
            "verification_status": "verified|partially_verified|unverified",
            "confidence": 0.0-1.0,
            "supporting_sources": ["source1", "source2"],
            "concerns": ["any concerns or conflicts"],
            "reasoning": "brief explanation"
        }}
    ]
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        system = self._create_system_prompt(
            additional_context="You are verifying research findings for accuracy and reliability."
        )
        
        response = self._call_llm(
            messages=messages,
            system=system,
            temperature=0.2  # Low temperature for consistent verification
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
            
            verification_result = json.loads(text)
            verified = verification_result.get("verified_findings", [])
            
            logger.info(f"Verified {len(verified)} findings")
            return verified
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse verification results: {e}")
            
            # Return findings with default verification
            return [
                {
                    "finding": f.get("finding", ""),
                    "verification_status": "unverified",
                    "confidence": 0.5,
                    "supporting_sources": f.get("sources", []),
                    "concerns": ["Could not verify automatically"],
                    "reasoning": "Verification parsing failed"
                }
                for f in findings
            ]
    
    def _identify_conflicts(
        self,
        research_findings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Identify conflicts or contradictions in research
        
        Args:
            research_findings: Research findings
            
        Returns:
            List of identified conflicts
        """
        # Use LLM to identify conflicts
        findings = research_findings.get("key_findings", [])
        if len(findings) < 2:
            return []
        
        findings_text = "\n".join([
            f"{i+1}. {f.get('finding', '')}"
            for i, f in enumerate(findings)
        ])
        
        prompt = f"""Analyze these findings for conflicts or contradictions:

{findings_text}

Identify any:
- Direct contradictions
- Conflicting data or statistics
- Inconsistent claims
- Ambiguous information

Return as JSON:
{{
    "conflicts": [
        {{
            "finding1": "first conflicting finding",
            "finding2": "second conflicting finding",
            "conflict_type": "contradiction|inconsistency|ambiguity",
            "severity": "high|medium|low",
            "explanation": "brief explanation"
        }}
    ]
}}

If no conflicts found, return: {{"conflicts": []}}"""
        
        messages = [{"role": "user", "content": prompt}]
        system = self._create_system_prompt(
            additional_context="You are analyzing research findings for conflicts and contradictions."
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
            
            result = json.loads(text)
            conflicts = result.get("conflicts", [])
            
            if conflicts:
                logger.warning(f"Identified {len(conflicts)} conflicts in research")
            
            return conflicts
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse conflict analysis: {e}")
            return []
    
    def _assess_credibility(
        self,
        research_findings: Dict[str, Any],
        source_scores: Dict[str, float],
        verified_findings: List[Dict]
    ) -> Dict[str, Any]:
        """
        Assess overall credibility of research
        
        Args:
            research_findings: Research findings
            source_scores: Source reliability scores
            verified_findings: Verified findings
            
        Returns:
            Credibility assessment
        """
        # Calculate average source reliability
        avg_source_score = (
            sum(source_scores.values()) / len(source_scores)
            if source_scores else 0.5
        )
        
        # Count verification statuses
        status_counts = Counter(
            f.get("verification_status", "unverified")
            for f in verified_findings
        )
        
        # Calculate average finding confidence
        avg_confidence = (
            sum(f.get("confidence", 0) for f in verified_findings) / len(verified_findings)
            if verified_findings else 0.5
        )
        
        # Determine overall credibility level
        if avg_confidence >= self.high_confidence_threshold and avg_source_score >= 0.8:
            credibility_level = "high"
        elif avg_confidence >= self.low_confidence_threshold and avg_source_score >= 0.6:
            credibility_level = "medium"
        else:
            credibility_level = "low"
        
        assessment = {
            "credibility_level": credibility_level,
            "average_source_reliability": round(avg_source_score, 2),
            "average_finding_confidence": round(avg_confidence, 2),
            "verified_count": status_counts.get("verified", 0),
            "partially_verified_count": status_counts.get("partially_verified", 0),
            "unverified_count": status_counts.get("unverified", 0),
            "total_sources": len(source_scores),
            "high_quality_sources": sum(1 for s in source_scores.values() if s >= 0.8)
        }
        
        logger.info(
            f"Credibility assessment: {credibility_level}",
            extra={
                "avg_confidence": avg_confidence,
                "verified": status_counts.get("verified", 0)
            }
        )
        
        return assessment
    
    def _generate_verification_report(
        self,
        query: str,
        verified_findings: List[Dict],
        conflicts: List[Dict],
        credibility_assessment: Dict[str, Any],
        source_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive verification report
        
        Args:
            query: Original query
            verified_findings: Verified findings
            conflicts: Identified conflicts
            credibility_assessment: Credibility assessment
            source_scores: Source reliability scores
            
        Returns:
            Verification report
        """
        # Separate findings by verification status
        verified = [f for f in verified_findings if f.get("verification_status") == "verified"]
        partial = [f for f in verified_findings if f.get("verification_status") == "partially_verified"]
        unverified = [f for f in verified_findings if f.get("verification_status") == "unverified"]
        
        # Identify high-confidence findings
        high_confidence = [f for f in verified_findings if f.get("confidence", 0) >= self.high_confidence_threshold]
        
        # Create recommendations
        recommendations = []
        
        if conflicts:
            recommendations.append(
                "Conflicts detected - synthesis agent should address contradictions"
            )
        
        if unverified:
            recommendations.append(
                f"{len(unverified)} findings lack sufficient verification - consider additional research"
            )
        
        if credibility_assessment["average_source_reliability"] < 0.7:
            recommendations.append(
                "Source reliability below threshold - prioritize more authoritative sources"
            )
        
        # Generate summary
        summary = self._generate_verification_summary(
            verified_findings=verified_findings,
            credibility_assessment=credibility_assessment,
            conflicts=conflicts
        )
        
        report = {
            "query": query,
            "verification_summary": summary,
            "credibility_assessment": credibility_assessment,
            "verified_findings": verified,
            "partially_verified_findings": partial,
            "unverified_findings": unverified,
            "high_confidence_findings": high_confidence,
            "conflicts": conflicts,
            "source_reliability": source_scores,
            "recommendations": recommendations,
            "overall_confidence": credibility_assessment["average_finding_confidence"]
        }
        
        logger.info(
            "Verification report generated",
            extra={
                "verified": len(verified),
                "conflicts": len(conflicts),
                "overall_confidence": report["overall_confidence"]
            }
        )
        
        return report
    
    def _generate_verification_summary(
        self,
        verified_findings: List[Dict],
        credibility_assessment: Dict[str, Any],
        conflicts: List[Dict]
    ) -> str:
        """
        Generate human-readable verification summary
        
        Args:
            verified_findings: Verified findings
            credibility_assessment: Credibility assessment
            conflicts: Identified conflicts
            
        Returns:
            Summary text
        """
        verified_count = credibility_assessment["verified_count"]
        total_count = len(verified_findings)
        credibility = credibility_assessment["credibility_level"]
        
        summary_parts = [
            f"Verification complete: {verified_count}/{total_count} findings fully verified.",
            f"Overall credibility: {credibility.upper()}."
        ]
        
        if conflicts:
            summary_parts.append(f"{len(conflicts)} conflict(s) identified.")
        
        if credibility_assessment["high_quality_sources"] > 0:
            summary_parts.append(
                f"{credibility_assessment['high_quality_sources']} high-quality sources used."
            )
        
        return " ".join(summary_parts)
    
    def _update_source_reliability(self, report: Dict[str, Any]):
        """
        Update source reliability scores based on verification results
        
        Args:
            report: Verification report
        """
        try:
            # Update scores for verified findings
            for finding in report.get("verified_findings", []):
                sources = finding.get("supporting_sources", [])
                for source_url in sources:
                    # Extract domain
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(source_url).netloc if source_url.startswith('http') else source_url
                        if domain:
                            # Verified finding = helpful source
                            self.long_memory.update_source_score(domain, was_helpful=True)
                    except Exception:
                        pass
            
            # Penalize sources with unverified findings
            for finding in report.get("unverified_findings", []):
                sources = finding.get("supporting_sources", [])
                for source_url in sources:
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(source_url).netloc if source_url.startswith('http') else source_url
                        if domain:
                            # Unverified finding = less helpful
                            self.long_memory.update_source_score(domain, was_helpful=False)
                    except Exception:
                        pass
            
            logger.debug("Source reliability scores updated")
            
        except Exception as e:
            logger.warning(f"Failed to update source reliability: {e}")


def get_verification_agent() -> VerificationAgent:
    """Get or create VerificationAgent instance"""
    return VerificationAgent()
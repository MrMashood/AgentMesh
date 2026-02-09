"""
Research Agent
Conducts web research to gather information
Uses web search and URL fetching tools
"""

from typing import Dict, Any, List
import json

from app.agents.base import BaseAgent
from app.core.logger import logger
from app.tools.web_search import search_web
from app.tools.url_fetch import fetch_and_extract


class ResearchAgent(BaseAgent):
    """
    Agent responsible for conducting web research.
    Searches for information and extracts relevant content.
    """
    
    def __init__(self):
        super().__init__(
            name="research",
            role="a research specialist that finds and extracts information from the web",
            guidelines=[
                "Search for high-quality, authoritative sources",
                "Extract relevant information from web pages",
                "Organize findings clearly",
                "Track source reliability",
                "Focus on recent and accurate information",
                "Verify source credibility"
            ]
        )
        
        # Research configuration
        self.max_search_results = 5
        self.max_urls_to_fetch = 3
    
    def execute(self, query_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct research for a query
        
        Args:
            query_id: Query identifier
            context: Must contain 'query' and optionally 'plan'
            
        Returns:
            Research findings dictionary
        """
        # Validate context
        self.validate_context(context, ["query"])
        
        query = context["query"]
        plan = context.get("plan", {})
        
        logger.info(
            f"Research agent starting for: {query[:50]}...",
            extra={"query_id": query_id}
        )
        
        # Check if we have relevant past research
        past_research = self._check_past_research(query)
        
        # Generate search queries
        search_queries = self._generate_search_queries(query, plan)
        
        # Conduct searches
        search_results = self._conduct_searches(search_queries)
        
        # Fetch and extract content from top URLs
        extracted_content = self._fetch_content(search_results)
        
        # Organize findings
        findings = self._organize_findings(
            query=query,
            search_results=search_results,
            extracted_content=extracted_content,
            past_research=past_research
        )
        
        # Update source reliability scores
        self._update_source_scores(findings)
        
        # Save research insights
        self._save_research_insights(query, findings)
        
        return findings
    
    def _generate_search_queries(
        self,
        query: str,
        plan: Dict[str, Any]
    ) -> List[str]:
        """
        Generate effective search queries using LLM
        
        Args:
            query: Original user query
            plan: Execution plan (optional)
            
        Returns:
            List of search queries
        """
        # Get key topics from plan if available
        key_topics = []
        if plan:
            query_analysis = plan.get("query_analysis", {})
            key_topics = query_analysis.get("key_topics", [])
        
        # Create prompt for LLM
        prompt = f"""Generate 2-3 effective web search queries to research this question:

Question: "{query}"

{f'Key topics: {", ".join(key_topics)}' if key_topics else ''}

Requirements:
- Keep queries concise (3-6 words each)
- Focus on finding authoritative sources
- Include specific terms that will find relevant results
- Avoid overly broad queries

Return your response as a JSON array of strings:
["query1", "query2", "query3"]"""
        
        messages = [{"role": "user", "content": prompt}]
        system = self._create_system_prompt(
            additional_context="You are creating web search queries to find relevant information."
        )
        
        response = self._call_llm(
            messages=messages,
            system=system,
            temperature=0.5
        )
        
        # Parse response
        try:
            text = response["text"].strip()
            
            # Extract JSON from response
            if "```json" in text:
                json_start = text.index("```json") + 7
                json_end = text.index("```", json_start)
                text = text[json_start:json_end].strip()
            elif "```" in text:
                json_start = text.index("```") + 3
                json_end = text.index("```", json_start)
                text = text[json_start:json_end].strip()
            elif "[" in text:
                # Extract just the JSON array
                json_start = text.index("[")
                json_end = text.rindex("]") + 1
                text = text[json_start:json_end]
            
            queries = json.loads(text)
            
            if isinstance(queries, list):
                logger.info(f"Generated {len(queries)} search queries")
                return queries[:3]  # Limit to 3
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse search queries: {e}")
        
        # Fallback: use original query
        return [query]
    
    def _conduct_searches(self, queries: List[str]) -> List[Dict[str, Any]]:
        """
        Conduct web searches for all queries
        
        Args:
            queries: List of search queries
            
        Returns:
            Combined search results
        """
        all_results = []
        seen_urls = set()
        
        for query in queries:
            try:
                logger.info(f"Searching: {query}")
                results = search_web(query, max_results=self.max_search_results)
                
                # Deduplicate by URL
                for result in results:
                    url = result.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "query": query,
                            "title": result.get("title", ""),
                            "url": url,
                            "snippet": result.get("snippet", ""),
                            "score": result.get("score", 0.5)
                        })
                
            except Exception as e:
                logger.error(f"Search failed for '{query}': {e}")
                continue
        
        # Sort by score
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        logger.info(f"Found {len(all_results)} unique search results")
        return all_results
    
    def _fetch_content(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fetch and extract content from top URLs
        
        Args:
            search_results: Search results with URLs
            
        Returns:
            List of extracted content
        """
        extracted = []
        urls_fetched = 0
        
        for result in search_results:
            if urls_fetched >= self.max_urls_to_fetch:
                break
            
            url = result.get("url", "")
            if not url:
                continue
            
            try:
                logger.info(f"Fetching content from: {url[:50]}...")
                
                content = fetch_and_extract(url)
                
                if content and content.get("text"):
                    extracted.append({
                        "url": url,
                        "title": result.get("title", ""),
                        "domain": content.get("domain", ""),
                        "text": content.get("text", ""),
                        "word_count": content.get("word_count", 0),
                        "snippet": result.get("snippet", "")
                    })
                    urls_fetched += 1
                    logger.info(f"Extracted {content.get('word_count', 0)} words from {content.get('domain', '')}")
                
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                continue
        
        logger.info(f"Successfully fetched content from {len(extracted)} URLs")
        return extracted
    
    def _organize_findings(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        extracted_content: List[Dict[str, Any]],
        past_research: List[Dict]
    ) -> Dict[str, Any]:
        """
        Organize research findings using LLM
        
        Args:
            query: Original query
            search_results: Search results
            extracted_content: Extracted content from URLs
            past_research: Past research on similar topics
            
        Returns:
            Organized findings
        """
        # Prepare content summary for LLM
        content_summary = self._prepare_content_summary(extracted_content)
        
        # Create organization prompt
        prompt = f"""Analyze and organize these research findings:

Original Question: "{query}"

Research Content:
{content_summary}

{"Past Research Available: Yes" if past_research else ""}

Please provide a structured summary in JSON format:
{{
    "key_findings": [
        {{"finding": "main finding 1", "sources": ["url1"], "confidence": 0.9}},
        {{"finding": "main finding 2", "sources": ["url2"], "confidence": 0.85}}
    ],
    "main_themes": ["theme1", "theme2"],
    "source_quality": {{"high": 2, "medium": 1, "low": 0}},
    "information_gaps": ["gap1", "gap2"],
    "summary": "brief overall summary"
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        system = self._create_system_prompt(
            additional_context="You are organizing research findings into a structured format."
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
            
            organized = json.loads(text)
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse organized findings: {e}")
            organized = {
                "key_findings": [],
                "main_themes": [],
                "source_quality": {"high": 0, "medium": 0, "low": 0},
                "information_gaps": [],
                "summary": "Research completed but organization failed"
            }
        
        # Add metadata
        findings = {
            **organized,
            "search_results": search_results[:5],  # Top 5 only
            "extracted_content": extracted_content,
            "sources_found": len(search_results),
            "sources_fetched": len(extracted_content),
            "past_research_available": len(past_research) > 0
        }
        
        logger.info(
            f"Research organized: {len(findings.get('key_findings', []))} key findings",
            extra={
                "sources_found": len(search_results),
                "sources_fetched": len(extracted_content)
            }
        )
        
        return findings
    
    def _prepare_content_summary(
        self,
        extracted_content: List[Dict[str, Any]]
    ) -> str:
        """
        Prepare a summary of extracted content for LLM
        
        Args:
            extracted_content: Extracted content list
            
        Returns:
            Formatted summary string
        """
        summaries = []
        
        for i, content in enumerate(extracted_content[:3], 1):  # Top 3 only
            # Truncate text to first 500 words
            text = content.get("text", "")
            words = text.split()[:500]
            truncated_text = " ".join(words)
            
            summary = f"""
Source {i}: {content.get('domain', 'Unknown')}
URL: {content.get('url', '')}
Title: {content.get('title', 'No title')}
Content: {truncated_text}...
---"""
            summaries.append(summary)
        
        return "\n".join(summaries) if summaries else "No content extracted"
    
    def _check_past_research(self, query: str) -> List[Dict]:
        """
        Check for past research on similar topics
        
        Args:
            query: Current query
            
        Returns:
            List of relevant past research
        """
        try:
            # Extract potential topics from query
            words = query.lower().split()
            topics = [w for w in words if len(w) > 4][:3]
            
            past_research = []
            for topic in topics:
                learnings = self._get_past_learnings(topic)
                if learnings:
                    past_research.extend(learnings)
            
            if past_research:
                logger.info(f"Found {len(past_research)} past research items")
            
            return past_research
            
        except Exception as e:
            logger.warning(f"Failed to check past research: {e}")
            return []
    
    def _update_source_scores(self, findings: Dict[str, Any]):
        """
        Update source reliability scores in long-term memory
        
        Args:
            findings: Research findings with source information
        """
        try:
            # Get sources that were used
            for content in findings.get("extracted_content", []):
                domain = content.get("domain", "")
                if domain:
                    # Assume sources were helpful if they provided content
                    self.long_memory.update_source_score(domain, was_helpful=True)
            
            logger.debug("Source scores updated")
            
        except Exception as e:
            logger.warning(f"Failed to update source scores: {e}")
    
    def _save_research_insights(self, query: str, findings: Dict[str, Any]):
        """
        Save research insights to long-term memory
        
        Args:
            query: Original query
            findings: Research findings
        """
        try:
            # Extract main themes as topics
            themes = findings.get("main_themes", [])
            
            # Save key findings as learnings
            for finding_data in findings.get("key_findings", [])[:3]:  # Top 3
                finding = finding_data.get("finding", "")
                sources = finding_data.get("sources", [])
                confidence = finding_data.get("confidence", 0.7)
                
                if finding and themes:
                    topic = themes[0].replace(" ", "_").lower()
                    self._save_learning(
                        topic=f"research_{topic}",
                        insight=finding,
                        confidence=confidence,
                        sources=sources
                    )
            
            logger.info("Research insights saved to long-term memory")
            
        except Exception as e:
            logger.warning(f"Failed to save research insights: {e}")


def get_research_agent() -> ResearchAgent:
    """Get or create ResearchAgent instance"""
    return ResearchAgent()
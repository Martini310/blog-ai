import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TavilyService:
    def __init__(self) -> None:
        self.api_key = settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com"

    async def search(self, query: str) -> list[dict[str, Any]]:
        """
        Call Tavily API, perform search queries, and return structured results.
        Returns a list of dictionaries with 'title', 'url', and 'content'.
        """
        if not self.api_key:
            logger.warning("Tavily API key is missing. Skipping search.")
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "search_depth": "basic",
                        "include_answer": False,
                        "include_images": False,
                        "include_raw_content": False,
                        "max_results": 3,
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                
                # Extract only necessary fields as per requirement
                formatted_results = []
                for res in results:
                    formatted_results.append({
                        "title": res.get("title", ""),
                        "url": res.get("url", ""),
                        "content": res.get("content", ""),
                    })
                return formatted_results
        except Exception as e:
            logger.warning(f"Tavily search failed for query '{query}': {e}")
            return []

    async def get_context(self, query: str, max_results: int = 3) -> str:
        """
        Call search(), combine results into a single cleaned text context,
        limit total length to avoid too many tokens, and remove duplicates.
        """
        results = await self.search(query)
        if not results:
            return ""

        context_parts = []
        seen_urls = set()
        
        for res in results[:max_results]:
            url = res.get("url")
            if url:
                if url in seen_urls:
                    continue
                seen_urls.add(url)

            title = res.get("title", "")
            content = res.get("content", "")
            if title and content:
                context_parts.append(f"Source: {title} ({url})\nContent: {content}\n")

        combined_text = "\n".join(context_parts)
        # Assuming ~4 chars per token, limit to 3000 chars to avoid large context overhead
        return combined_text[:3000]

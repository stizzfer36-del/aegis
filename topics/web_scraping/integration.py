"""Web Scraping — Playwright / Crawl4AI / Scrapy integrations."""
from __future__ import annotations


class WebScrapingTopic:
    name = "web_scraping"
    tools = ["playwright", "puppeteer", "browser-use", "crawl4ai", "scrapy", "firecrawl", "stagehand"]

    async def fetch_markdown(self, url: str) -> str:
        try:
            from crawl4ai import AsyncWebCrawler
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                return result.markdown
        except ImportError:
            return "crawl4ai not installed — pip install crawl4ai"

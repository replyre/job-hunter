"""HTML career page scraper — fallback for companies without a standard ATS.
Fetches the careers URL and extracts links that look like job postings."""

import httpx
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from sources.base import BaseSource
from core.models import Job
from config.settings import TITLE_KEYWORDS_POSITIVE


class HTMLCareerSource(BaseSource):
    name = "html"

    def __init__(self, company: dict):
        self.company = company

    async def fetch(self) -> list[Job]:
        url = self.company.get("careers_url", "")
        if not url:
            return []

        headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        seen_urls = set()

        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            if not text or len(text) < 5 or len(text) > 200:
                continue
            if not any(kw in text.lower() for kw in TITLE_KEYWORDS_POSITIVE):
                continue
            full_url = urljoin(url, href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            job = Job(
                title=text,
                company=self.company["name"],
                location="Remote",
                description="",
                url=full_url,
                source=f"html:{self.company.get('id', '')}",
                company_domain=self.company.get("domain", ""),
            )
            jobs.append(job)
        return jobs

"""Lever ATS — free public API, no auth needed.
API: GET https://api.lever.co/v0/postings/{slug}?mode=json
"""

import httpx
from datetime import datetime
from sources.base import BaseSource
from core.models import Job


class LeverSource(BaseSource):
    name = "lever"

    def __init__(self, company: dict):
        self.company = company
        self.slug = company["ats_slug"]

    async def fetch(self) -> list[Job]:
        url = f"https://api.lever.co/v0/postings/{self.slug}"
        params = {"mode": "json"}

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if not isinstance(data, list):
            return []

        jobs = []
        for item in data:
            posted = ""
            created_at = item.get("createdAt")
            if created_at and isinstance(created_at, (int, float)):
                posted = datetime.utcfromtimestamp(created_at / 1000).isoformat()

            categories = item.get("categories", {})
            location = ""
            if isinstance(categories, dict):
                location = categories.get("location", "")

            job = Job(
                title=item.get("text", ""),
                company=self.company["name"],
                location=location or "Remote",
                description=item.get("descriptionPlain", "") or item.get("description", ""),
                url=item.get("hostedUrl", ""),
                source=f"lever:{self.slug}",
                posted_date=posted,
                company_domain=self.company.get("domain", ""),
            )
            jobs.append(job)
        return jobs

"""Greenhouse ATS — free public API, no auth needed.
API: GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
"""

import httpx
from sources.base import BaseSource
from core.models import Job


class GreenhouseSource(BaseSource):
    name = "greenhouse"

    def __init__(self, company: dict):
        self.company = company
        self.slug = company["ats_slug"]

    async def fetch(self) -> list[Job]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.slug}/jobs"
        params = {"content": "true"}

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs = []
        for item in data.get("jobs", []):
            location = ""
            loc_data = item.get("location", {})
            if isinstance(loc_data, dict):
                location = loc_data.get("name", "")
            elif isinstance(loc_data, str):
                location = loc_data

            job = Job(
                title=item.get("title", ""),
                company=self.company["name"],
                location=location or "Remote",
                description=item.get("content", ""),
                url=item.get("absolute_url", ""),
                source=f"greenhouse:{self.slug}",
                posted_date=item.get("updated_at", ""),
                company_domain=self.company.get("domain", ""),
            )
            jobs.append(job)
        return jobs

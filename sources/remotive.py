"""Remotive.com — fully free, no API key needed.
Docs: https://remotive.com/api/remote-jobs (public API)
"""

import httpx
from sources.base import BaseSource
from core.models import Job


class RemotiveSource(BaseSource):
    name = "remotive"
    BASE_URL = "https://remotive.com/api/remote-jobs"

    async def fetch(self) -> list[Job]:
        jobs = []
        params = {"category": "software-dev", "limit": 100}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        for item in data.get("jobs", []):
            job = Job(
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                location=item.get("candidate_required_location", "Anywhere"),
                description=item.get("description", ""),
                url=item.get("url", ""),
                source=self.name,
                posted_date=item.get("publication_date", ""),
                salary=item.get("salary", "") or "",
                job_type=item.get("job_type", ""),
            )
            jobs.append(job)

        return jobs

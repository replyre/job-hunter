"""Arbeitnow — fully free, no API key needed.
Docs: https://arbeitnow.com/api
"""

import httpx
from sources.base import BaseSource
from core.models import Job


class ArbeitnowSource(BaseSource):
    name = "arbeitnow"
    BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

    async def fetch(self) -> list[Job]:
        jobs = []

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.BASE_URL)
            resp.raise_for_status()
            data = resp.json()

        for item in data.get("data", []):
            tags = item.get("tags", [])
            if isinstance(tags, list):
                tags = ", ".join(tags)

            created = item.get("created_at", "")
            if isinstance(created, int):
                from datetime import datetime
                created = datetime.utcfromtimestamp(created).isoformat()

            job = Job(
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                location=item.get("location", "Remote"),
                description=item.get("description", ""),
                url=item.get("url", ""),
                source=self.name,
                posted_date=str(created),
                job_type="full-time" if item.get("remote", False) else "on-site",
                tech_stack=tags if isinstance(tags, str) else "",
            )
            jobs.append(job)

        return jobs

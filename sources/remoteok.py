"""RemoteOK — fully free, no API key needed.
Endpoint: https://remoteok.com/api
"""

import httpx
from sources.base import BaseSource
from core.models import Job


class RemoteOKSource(BaseSource):
    name = "remoteok"
    BASE_URL = "https://remoteok.com/api"

    async def fetch(self) -> list[Job]:
        jobs = []
        headers = {"User-Agent": "JobScraper/1.0"}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.BASE_URL, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # First item is metadata, skip it
        for item in data[1:]:
            tags = item.get("tags", [])
            if isinstance(tags, list):
                tags = ", ".join(tags)

            job = Job(
                title=item.get("position", ""),
                company=item.get("company", ""),
                location=item.get("location", "Remote"),
                description=item.get("description", ""),
                url=item.get("url", f"https://remoteok.com/l/{item.get('id', '')}"),
                source=self.name,
                posted_date=item.get("date", ""),
                salary=self._parse_salary(item),
                job_type="full-time",
                tech_stack=tags if isinstance(tags, str) else "",
            )
            jobs.append(job)

        return jobs

    def _parse_salary(self, item: dict) -> str:
        sal_min = item.get("salary_min")
        sal_max = item.get("salary_max")
        if sal_min and sal_max:
            return f"${sal_min:,} - ${sal_max:,}"
        if sal_min:
            return f"${sal_min:,}+"
        return ""

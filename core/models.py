from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import hashlib
import re


class Job(BaseModel):
    title: str
    company: str
    location: str = "Remote"
    description: str = ""
    url: str = ""
    source: str = ""
    posted_date: Optional[str] = None
    discovered_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    tech_stack: str = ""  # comma-separated
    experience_level: str = ""  # junior/mid/senior
    relevance_score: int = 0
    status: str = "new"  # new/reviewed/applied/stale
    company_domain: str = ""
    salary: str = ""
    job_type: str = ""  # full-time/part-time/contract
    india_friendly: str = "unknown"  # yes/no/maybe/unknown
    location_note: str = ""  # explanation of location check

    @property
    def fingerprint(self) -> str:
        """Generate dedup fingerprint from company + title + location."""
        raw = f"{self.company.lower().strip()}|{self.title.lower().strip()}|{self.location.lower().strip()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def extract_domain(self) -> str:
        """Extract company domain from job URL."""
        if not self.url:
            return ""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.url)
            domain = parsed.netloc.replace("www.", "")
            # Skip job board domains
            skip = ["remotive.com", "remoteok.com", "arbeitnow.com",
                     "linkedin.com", "indeed.com", "glassdoor.com"]
            if any(s in domain for s in skip):
                return ""
            return domain
        except Exception:
            return ""


class Company(BaseModel):
    id: str = ""
    name: str
    domain: str = ""
    careers_url: str = ""
    ats_platform: str = "unknown"  # greenhouse/lever/ashby/html/unknown
    ats_slug: str = ""
    founded_year: int = 0
    employee_count: str = ""
    tags: str = ""
    india_friendly: str = "unknown"
    last_crawled: str = ""
    crawl_status: str = "active"  # active/paused/failed
    notes: str = ""

    @staticmethod
    def make_id(name: str) -> str:
        return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

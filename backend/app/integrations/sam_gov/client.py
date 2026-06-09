"""SAM.gov Opportunities API client (public).

Docs: https://open.gsa.gov/api/get-opportunities-public-api/
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError


class SamGovClient:
    """Async wrapper around the SAM.gov Opportunities v2 API."""

    def __init__(self, *, api_key: str | None = None, base_url: str | None = None) -> None:
        s = get_settings()
        self.api_key = api_key or s.sam_gov_api_key
        self.base_url = base_url or s.sam_gov_base_url

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def search_opportunities(
        self,
        *,
        q: str | None = None,
        agency: str | None = None,
        naics: str | None = None,
        posted_after: datetime | None = None,
        posted_before: datetime | None = None,
        due_before: datetime | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self.api_key:
            raise AppError(
                "SAM.gov API key not configured. Set SAM_GOV_API_KEY in your environment.",
                status_code=503,
                code="integration.sam_gov.not_configured",
            )
        params: dict[str, Any] = {
            "api_key": self.api_key,
            "limit": min(max(limit, 1), 100),
            "offset": max(offset, 0),
        }
        if q:
            params["title"] = q
        if agency:
            params["organizationName"] = agency
        if naics:
            params["ncode"] = naics
        if posted_after:
            params["postedFrom"] = posted_after.strftime("%m/%d/%Y")
        if posted_before:
            params["postedTo"] = posted_before.strftime("%m/%d/%Y")
        if due_before:
            params["rdlto"] = due_before.strftime("%m/%d/%Y")
        url = f"{self.base_url.rstrip('/')}/opportunities/v2/search"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
        if resp.status_code >= 400:
            raise AppError(
                f"SAM.gov upstream error: {resp.status_code}",
                status_code=502,
                code="integration.sam_gov.upstream_error",
            )
        data = resp.json()
        return list(data.get("opportunitiesData") or data.get("results") or [])

    @staticmethod
    def to_record_dict(item: dict[str, Any]) -> dict[str, Any]:
        """Map a SAM.gov item to a MarketIntelRecord row payload."""

        def _parse_date(s: str | None) -> datetime | None:
            if not s:
                return None
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None

        award = item.get("award") or {}
        amount = None
        if amt := award.get("amount"):
            try:
                amount = int(round(float(amt) * 100))
            except (TypeError, ValueError):
                amount = None

        return {
            "source_id": "sam_gov",
            "external_id": item.get("noticeId") or item.get("solicitationNumber") or "",
            "source_url": item.get("uiLink"),
            "title": item.get("title") or "(untitled)",
            "agency": (item.get("department") or item.get("organizationName")),
            "sub_agency": item.get("subTier") or item.get("office"),
            "notice_type": item.get("type"),
            "naics_code": item.get("naicsCode"),
            "psc_code": item.get("classificationCode"),
            "set_aside": item.get("typeOfSetAsideDescription") or item.get("typeOfSetAside"),
            "estimated_value_cents": amount,
            "posted_date": _parse_date(item.get("postedDate")),
            "due_date": _parse_date(item.get("responseDeadLine")),
            "incumbent": None,
            "raw_json": item,
        }

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


@dataclass
class MetaAd:
    ad_id: str
    ad_text: str
    headline: str
    call_to_action: str
    media_type: str
    start_date: datetime | None
    end_date: datetime | None
    is_active: bool
    publisher_platform: str
    raw_json: dict[str, Any]


class MetaAdLibraryClient:
    def __init__(self) -> None:
        self.base_url = f"{settings.meta_base_url}/{settings.meta_api_version}/ads_archive"
        self._resolved_page_cache: dict[str, str] = {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        response = requests.get(
            self.base_url,
            params=params,
            timeout=settings.request_timeout_seconds,
        )
        if response.status_code in {429, 500, 502, 503, 504}:
            response.raise_for_status()
        response.raise_for_status()
        return response.json()

    def fetch_ads(
        self,
        page_id: str,
        country: str | None = None,
        active_status: str = "ALL",
        ad_type: str | None = None,
        limit: int = 200,
    ) -> list[MetaAd]:
        country = country or settings.default_country
        ad_type = ad_type or settings.default_ad_type
        resolved_page_id = self._resolve_page_id(page_id)

        fields = [
            "id",
            "ad_creative_bodies",
            "ad_creative_link_titles",
            "ad_creative_link_captions",
            "ad_delivery_start_time",
            "ad_delivery_stop_time",
            "ad_snapshot_url",
            "publisher_platforms",
            "page_id",
            "is_active",
            "call_to_action_type",
            "media_type",
        ]

        params = {
            "access_token": settings.meta_access_token,
            # Meta Ad Library expects JSON-encoded arrays for these filters.
            "search_page_ids": json.dumps([resolved_page_id]),
            "ad_reached_countries": json.dumps([country]),
            "ad_active_status": active_status,
            "ad_type": ad_type,
            "fields": ",".join(fields),
            "limit": 100,
        }

        ads: list[MetaAd] = []
        next_url: str | None = None

        while len(ads) < limit:
            if next_url:
                response = requests.get(next_url, timeout=settings.request_timeout_seconds)
                response.raise_for_status()
                payload = response.json()
            else:
                payload = self._request(params)

            for item in payload.get("data", []):
                ads.append(self._normalize(item))
                if len(ads) >= limit:
                    break

            next_url = payload.get("paging", {}).get("next")
            if not next_url:
                break

        return ads

    def _resolve_page_id(self, page_ref: str) -> str:
        if page_ref in self._resolved_page_cache:
            return self._resolved_page_cache[page_ref]

        raw = (page_ref or "").strip()
        if raw.isdigit():
            self._resolved_page_cache[page_ref] = raw
            return raw

        candidate = raw
        if raw.startswith("http://") or raw.startswith("https://"):
            parsed = urlparse(raw)
            if parsed.path.rstrip("/").endswith("/profile.php"):
                profile_id = parse_qs(parsed.query).get("id", [None])[0]
                if profile_id and profile_id.isdigit():
                    self._resolved_page_cache[page_ref] = profile_id
                    return profile_id
            parts = [p for p in parsed.path.split("/") if p]
            if parts:
                candidate = parts[0]

        candidate = candidate.lstrip("@")
        if candidate.isdigit():
            self._resolved_page_cache[page_ref] = candidate
            return candidate

        resolved = self._lookup_page_id(candidate)
        self._resolved_page_cache[page_ref] = resolved
        return resolved

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    def _lookup_page_id(self, handle: str) -> str:
        # Try Graph lookup first; this may fail without metadata permissions.
        if settings.meta_access_token:
            url = f"{settings.meta_base_url}/{settings.meta_api_version}/{handle}"
            response = requests.get(
                url,
                params={"access_token": settings.meta_access_token, "fields": "id"},
                timeout=settings.request_timeout_seconds,
            )
            if response.status_code < 400:
                payload = response.json()
                resolved = str(payload.get("id") or "").strip()
                if resolved.isdigit():
                    return resolved

        # Fallback: scrape page HTML and extract numeric user/page identifier.
        page_url = f"https://www.facebook.com/{handle}"
        try:
            html = requests.get(
                page_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=settings.request_timeout_seconds,
            ).text
            for pattern in (
                r'"userID":"(\d+)"',
                r'"profile_id":"(\d+)"',
                r'"pageID":"(\d+)"',
                r'"page_id":"(\d+)"',
            ):
                match = re.search(pattern, html)
                if match and match.group(1).isdigit() and match.group(1) != "0":
                    return match.group(1)
        except requests.RequestException:
            pass

        return handle

    def _normalize(self, item: dict[str, Any]) -> MetaAd:
        text_items = item.get("ad_creative_bodies") or []
        title_items = item.get("ad_creative_link_titles") or []

        start = self._parse_date(item.get("ad_delivery_start_time"))
        end = self._parse_date(item.get("ad_delivery_stop_time"))
        media_type = (item.get("media_type") or "image").lower()
        platforms = item.get("publisher_platforms") or ["facebook"]

        return MetaAd(
            ad_id=str(item.get("id", "")),
            ad_text=(text_items[0] if text_items else "") or "",
            headline=(title_items[0] if title_items else "") or "",
            call_to_action=item.get("call_to_action_type", "") or "",
            media_type=media_type if media_type in {"video", "image", "carousel"} else "image",
            start_date=start,
            end_date=end,
            is_active=bool(item.get("is_active", True)),
            publisher_platform=",".join(platforms),
            raw_json=item,
        )

    def connection_status(self) -> dict[str, Any]:
        if not settings.meta_access_token:
            return {"ok": False, "message": "META_ACCESS_TOKEN is missing"}

        me_url = f"{settings.meta_base_url}/{settings.meta_api_version}/me"
        me_resp = requests.get(me_url, params={"access_token": settings.meta_access_token}, timeout=settings.request_timeout_seconds)
        me_payload: dict[str, Any] = {}
        try:
            me_payload = me_resp.json()
        except ValueError:
            pass

        probe_params = {
            "access_token": settings.meta_access_token,
            "search_terms": "wellness",
            "ad_reached_countries": json.dumps([settings.default_country]),
            "ad_active_status": "ALL",
            "ad_type": settings.default_ad_type,
            "fields": "id,page_id",
            "limit": 1,
        }
        ads_resp = requests.get(self.base_url, params=probe_params, timeout=settings.request_timeout_seconds)
        ads_payload: dict[str, Any] = {}
        try:
            ads_payload = ads_resp.json()
        except ValueError:
            pass

        ok = me_resp.status_code == 200 and ads_resp.status_code == 200
        status: dict[str, Any] = {
            "ok": ok,
            "app_id": settings.meta_app_id,
            "me_status": me_resp.status_code,
            "ads_archive_status": ads_resp.status_code,
            "me": me_payload if me_resp.status_code == 200 else {"error": me_payload.get("error", me_payload)},
            "ads_archive": ads_payload if ads_resp.status_code == 200 else {"error": ads_payload.get("error", ads_payload)},
        }
        return status

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

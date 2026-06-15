"""Supabase Storage upload helper.

Uploads image bytes to a Supabase Storage public bucket via the REST API
(no extra SDK dependency — uses httpx which is already in requirements).

Usage
-----
Configure three env vars in Render:
  SUPABASE_URL            = https://<project>.supabase.co
  SUPABASE_ANON_KEY       = eyJ...  (or service-role key for private buckets)
  SUPABASE_STORAGE_BUCKET = images  (default; must be a public bucket)

When SUPABASE_URL or SUPABASE_ANON_KEY are absent, ``upload_to_supabase``
returns ``None`` so the caller can fall back to local disk.
"""

from __future__ import annotations

import mimetypes
from typing import Optional

import httpx

from backend.logging_config import get_logger
from backend.settings import settings

logger = get_logger("backend.supabase_storage")

BUCKET = "images"


def _storage_base() -> Optional[str]:
    url = (settings.supabase_url or "").rstrip("/")
    key = settings.supabase_anon_key
    if not url or not key:
        return None
    return url


def upload_to_supabase(object_name: str, content: bytes, suffix: str) -> Optional[str]:
    """Upload *content* to Supabase Storage and return its public URL.

    Returns ``None`` when Supabase is not configured, so callers can fall
    back to local-disk storage gracefully.
    """
    base = _storage_base()
    if not base:
        return None

    key = settings.supabase_anon_key
    content_type = mimetypes.types_map.get(suffix.lower(), "application/octet-stream")

    endpoint = f"{base}/storage/v1/object/{BUCKET}/{object_name}"
    try:
        resp = httpx.post(
            endpoint,
            content=content,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            timeout=30,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("supabase_storage.upload_failed", object=object_name, error=str(exc))
        return None

    public_url = f"{base}/storage/v1/object/public/{BUCKET}/{object_name}"
    logger.info("supabase_storage.uploaded", object=object_name, url=public_url)
    return public_url

"""Pure helpers shared by ingestion and GraphQL mutations."""

from hashlib import sha256
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def normalize_topic(value: str) -> str:
    normalized = " ".join(value.strip().casefold().split())
    if not normalized:
        raise ValueError("A topic name is required")
    return normalized


def canonicalize_url(value: str) -> str:
    """Remove fragments and common tracking parameters from a source URL."""
    parsed = urlparse(value.strip())
    query = urlencode(
        [(key, item) for key, item in parse_qsl(parsed.query) if not key.startswith("utm_")]
    )
    return urlunparse((parsed.scheme, parsed.netloc.casefold(), parsed.path, "", query, ""))


def content_fingerprint(title: str, body: str = "") -> str:
    text = re.sub(r"\s+", " ", f"{title} {body}".casefold()).strip()
    return sha256(text.encode("utf-8")).hexdigest()

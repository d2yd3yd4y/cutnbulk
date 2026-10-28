from urllib.parse import urlparse


def safe_next_path(raw: str | None, default: str = "/") -> str:
    """Allow only same-site relative paths; reject open redirects."""
    if not raw:
        return default
    value = raw.strip()
    if not value.startswith("/") or value.startswith("//"):
        return default
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return default
    if "\\" in value or ":" in value.split("?", 1)[0]:
        return default
    return value

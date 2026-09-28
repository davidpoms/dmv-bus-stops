"""External photo references; submitted URLs are never fetched by the server."""
from urllib.parse import urlsplit


SCHEMA = """CREATE TABLE IF NOT EXISTS observation_attachments (
    id INTEGER PRIMARY KEY,
    observation_id INTEGER NOT NULL REFERENCES stop_observations(id),
    attachment_type TEXT NOT NULL,
    external_url TEXT,
    storage_key TEXT,
    provider TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (external_url IS NOT NULL OR storage_key IS NOT NULL)
)"""


def validate_photo_url(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Photo links must be at most 2048 characters.")
    value = value.strip()
    if not value:
        return None
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme.lower() in ("http", "https") and parsed.hostname
                 and not parsed.username and not parsed.password)
        parsed.port
    except ValueError:
        valid = False
    if not valid or any(ord(c) <= 32 for c in value) or "\\" in value:
        raise ValueError("Use a valid HTTP or HTTPS photo link without credentials.")
    return value


def attach_photo(conn, observation_id, url):
    """Insert into the migrated schema within the caller's evidence transaction."""
    if url:
        conn.execute("""INSERT INTO observation_attachments
            (observation_id, attachment_type, external_url)
            VALUES (?, 'photo', ?)""", (observation_id, validate_photo_url(url)))


def observation_attachments(conn, observation_id):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='observation_attachments'").fetchone():
        return []
    return [dict(zip(("id", "attachment_type", "external_url", "created_at"), row))
            for row in conn.execute("""SELECT id, attachment_type, external_url, created_at
                FROM observation_attachments WHERE observation_id=? ORDER BY id""",
                (observation_id,))]

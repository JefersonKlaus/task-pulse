"""Reading git repository URLs (web or SSH)."""

import re
from urllib.parse import urlsplit


def project_name_from_url(url):
    """Default project name: the repository name at the end of a git URL.

    "https://github.com/acme/task-pulse.git" -> "task-pulse"
    "git@github.com:acme/task-pulse.git"     -> "task-pulse"
    Falls back to the host when the URL has no path.
    """
    parts = urlsplit(url.strip())
    path = parts.path.strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    return re.split(r"[/:]", path)[-1] or parts.netloc


def is_web_url(url):
    """True for http(s) URLs, the only ones safe to render as links."""
    return url.lower().startswith(("http://", "https://"))

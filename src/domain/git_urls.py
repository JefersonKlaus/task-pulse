"""Reading git repository URLs (web or SSH)."""

import re
from urllib.parse import urlsplit

# GitHub's short form of a repository: "owner/repository".
_GITHUB_SHORT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+$")
# SSH in scp style: "git@github.com:acme/portal.git".
_SCP_RE = re.compile(r"^[\w.-]+@([\w.-]+):(.+)$")
_URL_SCHEMES = ("http", "https", "ssh", "git")


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


def repository_key(url):
    """What identifies a repository, however its URL is written; or None.

    The host and path, lowercased, without "www.", ".git" or slashes, so
    "https://GitHub.com/Acme/Portal.git/" and "git@github.com:acme/portal"
    are both "github.com/acme/portal" (GitHub names ignore case). None when
    ``url`` isn't a repository URL.
    """
    url = url.strip()
    if not url or any(char.isspace() for char in url):
        return None
    scp = _SCP_RE.match(url)
    if scp:
        host, path = scp.groups()
    else:
        parts = urlsplit(url)
        if parts.scheme.lower() not in _URL_SCHEMES:
            return None
        host, path = parts.hostname or "", parts.path
    path = path.strip("/").removesuffix(".git").strip("/")
    if not host or not path:
        return None
    return f"{host.lower().removeprefix('www.')}/{path.lower()}"


def repository_url(value):
    """The URL of a repository written as a URL or as GitHub's "owner/repo".

    "acme/portal" -> "https://github.com/acme/portal"; a URL is kept as
    written. Raises ValueError for anything else.
    """
    value = value.strip()
    if _GITHUB_SHORT_RE.match(value):
        return f"https://github.com/{value.removesuffix('.git')}"
    if repository_key(value) is None:
        raise ValueError(f"Not a repository: {value!r}")
    return value

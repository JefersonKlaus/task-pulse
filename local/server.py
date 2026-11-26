"""Local server to try the frontend without AWS: serves the built site (frontend/public) and the API (the
SAME code as the Lambdas, one per action, routed like API Gateway) with an in-memory database, and NO
login (no Cognito): every request is the same user.

    python local/server.py [--port 8765] [--empty]

It starts with demo data (local/seed.py). `--empty` starts with nothing registered. The frontend must be
built first (`python dev.py build`, which `python dev.py serve` already does).

Data lives in memory and is lost when the server stops. It only listens on 127.0.0.1: never expose
it, since it has no authentication. The deployed app is not affected: there, API Gateway still
requires a valid Cognito token for every request.

`start(require_login=True)` is used by local/e2e.py to test the login screen: the site then logs in
through Cognito (which the test simulates) and the server accepts the simulated tokens "token-<user>"."""
import argparse
import os
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "frontend" / "public"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_gateway import dispatch                    # noqa: E402  (also puts the backend on the path)
from memory_repository import MemoryRepository     # noqa: E402
from pulse_core.ports import Dependencies           # noqa: E402
from seed import seed as load_demo_data             # noqa: E402

LOCAL_OWNER = "local-user"                          # the user every request belongs to without login
# Same as CloudFront's (infra/frontend.tf): if the site breaks with it, the test catches it before deploy.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; "
       "connect-src 'self' https://cognito-idp.sa-east-1.amazonaws.com; frame-ancestors 'none'; "
       "base-uri 'none'; form-action 'self'")
CONTENT_TYPES = {".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml",
                 ".map": "application/json"}


class RequestHandler(BaseHTTPRequestHandler):
    def _claims(self):
        """Plays the part of API Gateway's JWT authorizer: decides which user the request is from."""
        if not self.server.require_login:
            return {"sub": LOCAL_OWNER}
        authorization = self.headers.get("Authorization", "")
        if not authorization.startswith("Bearer token-"):
            return None
        return {"sub": authorization[len("Bearer token-"):]}

    def _api(self):
        url = urlparse(self.path)
        event = {"rawPath": url.path[len("/api"):], "requestContext": {"http": {"method": self.command}},
                 "queryStringParameters": {k: v[0] for k, v in parse_qs(url.query).items()} or None,
                 "body": self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()}
        claims = self._claims()
        if claims:
            event["requestContext"]["authorizer"] = {"jwt": {"claims": claims}}
        response = dispatch(event, self.server.deps)
        body = response["body"].encode()
        self.send_response(response["statusCode"])
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _config(self):
        api_url = f"http://{self.headers['Host']}/api"
        if self.server.require_login:
            return f'export const CONFIG = {{region:"sa-east-1",clientId:"local",apiUrl:"{api_url}"}};'
        return f'export const CONFIG = {{region:"",clientId:"",apiUrl:"{api_url}",skipLogin:true}};'

    def _static(self):
        path = urlparse(self.path).path.lstrip("/") or "index.html"
        file = (SITE / path).resolve()
        if path == "js/config.js":
            body = self._config().encode()
        elif SITE.resolve() in file.parents and file.is_file():
            body = file.read_bytes()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(file.suffix, "text/plain") + "; charset=utf-8")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Cache-Control", "no-store")       # edits to the frontend show up on reload
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._api() if self.path.startswith("/api") else self._static()

    do_POST = do_PUT = do_DELETE = _api

    def log_message(self, *args):
        pass


class LocalServer(ThreadingHTTPServer):
    # On Windows, "reuse address" lets a second server take a port that is already in use, and the
    # requests then go to the other one. Here a busy port is an error instead ("address already in use").
    allow_reuse_address = os.name != "nt"


def start(port=8765, require_login=False, demo_data=False):
    """A server with its own in-memory database, empty unless `demo_data`. Call `serve_forever()` on it."""
    server = LocalServer(("127.0.0.1", port), RequestHandler)    # port 0: any free one (the tests)
    server.require_login = require_login
    server.deps = Dependencies(MemoryRepository())
    if demo_data:
        load_demo_data(server.deps, LOCAL_OWNER, date.today())
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--empty", action="store_true", help="start with no data")
    args = parser.parse_args()
    if not (SITE / "js" / "app.js").exists():
        sys.exit("The frontend is not built: run `python dev.py build` (or `python dev.py serve`).")
    print(f"http://127.0.0.1:{args.port}  (in memory, {'empty' if args.empty else 'demo data'}, no login; Ctrl+C to stop)")
    server = start(args.port, demo_data=not args.empty)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

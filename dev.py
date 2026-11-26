#!/usr/bin/env python3
"""Development tasks, the same on Windows, macOS and Linux. Needs Python 3.12+ and Node 22 (the frontend is
TypeScript, compiled by tsc). Python tools go inside .venv/, Node's inside frontend/node_modules/.

    python dev.py setup     create .venv with the test tools, install TypeScript and download Chromium
    python dev.py build     compile the frontend (frontend/src/*.ts -> frontend/public/js/*.js)
    python dev.py serve     build, then the site + in-memory API at http://127.0.0.1:8765, no login, with demo data (--port, --empty)
    python dev.py test      backend tests and the TypeScript type check (quick)
    python dev.py e2e       the browser test (a real Chromium)
    python dev.py all       test + e2e: what CI runs, except Terraform
    python dev.py screenshots   the README's pictures (docs/screenshots), with the demo data
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
NODE_HINT = "Node 22 is needed to build the frontend: https://nodejs.org."
FRONTEND = ROOT / "frontend"


def python() -> str:
    """The .venv's Python when it exists (after `setup`), otherwise the one running this script."""
    return str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def run(*command: str, cwd: Path = ROOT) -> int:
    print("\n$", " ".join(str(c) for c in command), flush=True)
    return subprocess.call([str(c) for c in command], cwd=cwd)


def npm(*args: str) -> int:
    """npm in frontend/ (npm.cmd on Windows). Installs the pinned packages first when they are missing."""
    executable = shutil.which("npm")
    if not executable:
        print(f"\nERROR: {NODE_HINT}")
        return 1
    if not (FRONTEND / "node_modules").exists() and args[0] != "ci":
        code = run(executable, "ci", cwd=FRONTEND)
        if code:
            return code
    return run(executable, *args, cwd=FRONTEND)


def setup(args: argparse.Namespace) -> int:
    if sys.version_info < (3, 12):
        sys.exit(f"Python 3.12 or newer is needed (this is {sys.version.split()[0]}).")
    if not VENV_PYTHON.exists():
        print(f"Creating {VENV.name}/ ...")
        venv.create(VENV, with_pip=True)
    install = [python(), "-m", "playwright", "install", *(["--with-deps"] if args.with_deps else []), "chromium"]
    code = run(python(), "-m", "pip", "install", "--upgrade", "-r", "requirements-dev.txt") or run(*install)
    code = code or npm("ci")
    if code:
        return code
    print("\nReady. Try:  python dev.py serve   (then open http://127.0.0.1:8765)   or   python dev.py test")
    return 0


def build(_: argparse.Namespace) -> int:
    return npm("run", "build")


def serve(args: argparse.Namespace) -> int:
    if build(args):
        return 1
    try:
        return run(python(), "local/server.py", "--port", str(args.port), *(["--empty"] if args.empty else []))
    except KeyboardInterrupt:
        return 0


def test(_: argparse.Namespace) -> int:
    results = {"backend tests": run(python(), "-m", "pytest", "-q", "local/tests"),
               "TypeScript types": npm("run", "typecheck")}
    print("\n" + "\n".join(f"  {'ok     ' if code == 0 else 'FAILED '} {name}" for name, code in results.items()))
    return 1 if any(results.values()) else 0


def e2e(args: argparse.Namespace) -> int:
    return build(args) or run(python(), "local/e2e.py")


def screenshots(args: argparse.Namespace) -> int:
    return build(args) or run(python(), "local/screenshots.py")


def all_checks(args: argparse.Namespace) -> int:
    return test(args) or e2e(args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    setup_parser = commands.add_parser("setup", help="create .venv, install the tools, TypeScript and Chromium")
    setup_parser.add_argument("--with-deps", action="store_true",
                              help="also install Chromium's system libraries (Linux; uses sudo/apt)")
    commands.add_parser("build", help="compile the frontend")
    serve_parser = commands.add_parser("serve", help="build, then the site + in-memory API, no login")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--empty", action="store_true", help="start with no data (default: demo data)")
    commands.add_parser("test", help="backend tests and TypeScript type check")
    commands.add_parser("e2e", help="the browser test")
    commands.add_parser("all", help="test + e2e")
    commands.add_parser("screenshots", help="the README's pictures, in docs/screenshots")
    args = parser.parse_args()
    handlers = {"setup": setup, "build": build, "serve": serve, "test": test, "e2e": e2e, "all": all_checks,
                "screenshots": screenshots}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

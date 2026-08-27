"""CLI for Lattice publish soak."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from .client import LatticeClient
from .runner import run_soak


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="soak",
        description=(
            "Firehose Lattice entity PUT soak (5k/10k). Door-level only. "
            "No publish throttle. HTTP 403 counted as Lattice-side evidence."
        ),
    )
    p.add_argument(
        "--n",
        type=int,
        default=5000,
        help="Number of entities to PUT (default 5000)",
    )
    p.add_argument(
        "--target",
        choices=("mock", "live"),
        default="mock",
        help="mock = local mock-lattice; live = LATTICE_* sandbox",
    )
    p.add_argument(
        "--mock-url",
        default="",
        help="Mock base URL (default start embedded or http://127.0.0.1:8765)",
    )
    p.add_argument(
        "--prefix",
        default="polybolos-soak",
        help="entityId prefix",
    )
    p.add_argument(
        "--progress-every",
        type=int,
        default=500,
        help="Stderr progress interval (0=off)",
    )
    p.add_argument(
        "--auth-only",
        action="store_true",
        help="OAuth only, then exit",
    )
    p.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON report",
    )
    return p


def _start_embedded_mock():
    """Start sibling anduril-mock-lattice if importable."""
    import sys as _sys
    from pathlib import Path

    parents = Path(__file__).resolve().parents[2]
    for name in ("mock-lattice", "anduril-mock-lattice"):
        root = parents / name
        if root.is_dir():
            _sys.path.insert(0, str(root))
            break
    from mock_lattice import STATE, start_background

    STATE.reset()
    # Optional: simulate sandbox cliff for demos
    fail_after = int(os.environ.get("SOAK_MOCK_FAIL_AFTER_N", "0") or "0")
    STATE.fail_after_n = fail_after
    httpd, _ = start_background(host="127.0.0.1", port=0)
    host, port = httpd.server_address[:2]
    base = f"http://{host}:{port}"
    return httpd, base


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    httpd = None

    if args.target == "mock":
        if args.mock_url:
            endpoint = args.mock_url.replace("http://", "").replace("https://", "")
            os.environ.setdefault("LATTICE_ENDPOINT", endpoint)
        else:
            try:
                httpd, base = _start_embedded_mock()
            except Exception as exc:
                sys.stderr.write(
                    f"[soak] could not start embedded mock-lattice: {exc}\n"
                    "Clone Polybolos-Institute/anduril-mock-lattice as sibling "
                    "or pass --mock-url http://127.0.0.1:8765\n"
                )
                return 2
            endpoint = base.replace("http://", "")
            os.environ["LATTICE_ENDPOINT"] = endpoint
        os.environ.setdefault("LATTICE_CLIENT_ID", "test-client-id")
        os.environ.setdefault("LATTICE_CLIENT_SECRET", "test-client-secret")
        os.environ.setdefault("LATTICE_ENV_TOKEN", "test-sandbox-token")

    client = LatticeClient()
    missing = client.missing_config()
    if missing:
        sys.stderr.write("[soak] missing env: " + " ".join(missing) + "\n")
        return 1

    try:
        client.fetch_token()
        sys.stderr.write(f"[soak] OAuth OK endpoint={client._host}\n")
        if args.auth_only:
            print(json.dumps({"ok": True, "endpoint": client._host}))
            return 0

        if args.n < 1:
            sys.stderr.write("[soak] --n must be >= 1\n")
            return 1

        sys.stderr.write(
            f"[soak] firehose n={args.n} target={args.target} "
            f"(no throttle)\n"
        )
        report = run_soak(
            client,
            args.n,
            prefix=args.prefix,
            progress_every=args.progress_every,
        )
        indent = 2 if args.pretty else None
        print(json.dumps(report.as_dict(), indent=indent))
        # Exit 0 even if live sandbox returned 403s - that is measured evidence.
        # Exit 1 only if mock target got zero ok when n>0 (harness broken).
        if args.target == "mock" and report.ok == 0 and args.n > 0:
            return 1
        return 0
    finally:
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    raise SystemExit(main())

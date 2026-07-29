"""Minimal Lattice REST client (stdlib urllib)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PutResult:
    status_code: int
    ok: bool
    entity_id: str
    latency_ms: float
    error: str = ""


class LatticeClient:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        env_token: Optional[str] = None,
        timeout_s: float = 30.0,
    ) -> None:
        host = (endpoint or os.environ.get("LATTICE_ENDPOINT", "")).strip()
        scheme = "https"
        if host.startswith("http://"):
            scheme = "http"
            host = host[len("http://") :]
        elif host.startswith("https://"):
            host = host[len("https://") :]
        self._host = host.rstrip("/")
        bare = self._host.split(":")[0].lower()
        if scheme == "https" and bare in ("127.0.0.1", "localhost", "::1"):
            scheme = "http"
        self._base = f"{scheme}://{self._host}" if self._host else ""
        self._client_id = (client_id or os.environ.get("LATTICE_CLIENT_ID", "")).strip()
        self._client_secret = (
            client_secret or os.environ.get("LATTICE_CLIENT_SECRET", "")
        ).strip()
        self._env_token = (env_token or os.environ.get("LATTICE_ENV_TOKEN", "")).strip()
        self._timeout = timeout_s
        self._access_token: Optional[str] = None
        self._token_expires_at = 0.0

    def missing_config(self) -> List[str]:
        missing = []
        if not self._host:
            missing.append("LATTICE_ENDPOINT")
        if not self._client_id:
            missing.append("LATTICE_CLIENT_ID")
        if not self._client_secret:
            missing.append("LATTICE_CLIENT_SECRET")
        if not self._env_token:
            missing.append("LATTICE_ENV_TOKEN")
        return missing

    def fetch_token(self) -> str:
        url = f"{self._base}/api/v1/oauth/token"
        form = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=form,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Anduril-Sandbox-Authorization": f"Bearer {self._env_token}",
            },
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        token = body.get("access_token")
        if not token:
            raise RuntimeError("oauth response missing access_token")
        expires_in = float(body.get("expires_in", 1800))
        self._access_token = str(token)
        self._token_expires_at = time.time() + max(60.0, expires_in - 60.0)
        return self._access_token

    def ensure_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        return self.fetch_token()

    def put_entity(self, entity: Dict[str, Any]) -> PutResult:
        entity_id = str(entity.get("entityId") or "")
        url = f"{self._base}/api/v1/entities"
        data = json.dumps(entity).encode("utf-8")
        t0 = time.perf_counter()
        try:
            token = self.ensure_token()
            req = urllib.request.Request(
                url,
                data=data,
                method="PUT",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                    "Anduril-Sandbox-Authorization": f"Bearer {self._env_token}",
                },
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                code = int(resp.status)
                resp.read()
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return PutResult(
                status_code=code,
                ok=200 <= code < 300,
                entity_id=entity_id,
                latency_ms=latency_ms,
            )
        except urllib.error.HTTPError as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            try:
                err_body = exc.read().decode("utf-8", errors="replace")[:200]
            except Exception:
                err_body = str(exc)
            return PutResult(
                status_code=int(exc.code),
                ok=False,
                entity_id=entity_id,
                latency_ms=latency_ms,
                error=err_body,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return PutResult(
                status_code=0,
                ok=False,
                entity_id=entity_id,
                latency_ms=latency_ms,
                error=str(exc),
            )

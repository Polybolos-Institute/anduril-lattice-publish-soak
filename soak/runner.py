"""Firehose publish runner + stats."""

from __future__ import annotations

import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .client import LatticeClient, PutResult
from .entities import make_entity


@dataclass
class SoakReport:
    n_requested: int
    ok: int = 0
    fail: int = 0
    http_403: int = 0
    http_other_fail: int = 0
    wall_s: float = 0.0
    puts_per_sec: float = 0.0
    latency_ms: List[float] = field(default_factory=list)
    status_counts: Counter = field(default_factory=Counter)
    first_fail_index: Optional[int] = None
    first_fail_code: Optional[int] = None

    def percentile(self, p: float) -> Optional[float]:
        if not self.latency_ms:
            return None
        xs = sorted(self.latency_ms)
        if len(xs) == 1:
            return xs[0]
        k = (len(xs) - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, len(xs) - 1)
        if f == c:
            return xs[f]
        return xs[f] + (xs[c] - xs[f]) * (k - f)

    def as_dict(self) -> Dict[str, Any]:
        p50 = self.percentile(50)
        p95 = self.percentile(95)
        return {
            "n_requested": self.n_requested,
            "ok": self.ok,
            "fail": self.fail,
            "http_403": self.http_403,
            "http_other_fail": self.http_other_fail,
            "wall_s": round(self.wall_s, 3),
            "puts_per_sec": round(self.puts_per_sec, 2),
            "latency_ms_p50": None if p50 is None else round(p50, 2),
            "latency_ms_p95": None if p95 is None else round(p95, 2),
            "latency_ms_mean": (
                None
                if not self.latency_ms
                else round(statistics.fmean(self.latency_ms), 2)
            ),
            "status_counts": dict(self.status_counts),
            "first_fail_index": self.first_fail_index,
            "first_fail_code": self.first_fail_code,
            "policy": "firehose (no publish throttle); 403 is Lattice-side evidence",
            "disclaimer": (
                "Door-level publish soak only. Not C2 / ROE / Core. "
                "Independent sample - not an Anduril product."
            ),
        }


def run_soak(
    client: LatticeClient,
    n: int,
    *,
    prefix: str = "polybolos-soak",
    progress_every: int = 500,
) -> SoakReport:
    """Sequential firehose. No sleep between PUTs."""
    report = SoakReport(n_requested=n)
    t0 = time.perf_counter()
    for i in range(n):
        entity = make_entity(i, prefix=prefix)
        result: PutResult = client.put_entity(entity)
        report.status_counts[result.status_code] += 1
        report.latency_ms.append(result.latency_ms)
        if result.ok:
            report.ok += 1
        else:
            report.fail += 1
            if result.status_code == 403:
                report.http_403 += 1
            else:
                report.http_other_fail += 1
            if report.first_fail_index is None:
                report.first_fail_index = i
                report.first_fail_code = result.status_code
        if progress_every > 0 and (i + 1) % progress_every == 0:
            elapsed = time.perf_counter() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0.0
            sys.stderr.write(
                f"[soak] {i + 1}/{n} ok={report.ok} fail={report.fail} "
                f"403={report.http_403} rate={rate:.1f}/s\n"
            )
            sys.stderr.flush()
    report.wall_s = time.perf_counter() - t0
    report.puts_per_sec = (n / report.wall_s) if report.wall_s > 0 else 0.0
    return report

# anduril-lattice-publish-soak

Firehose **Lattice entity PUT** soak at 5 000 / 10 000 scale.

Door-level only. Measures ok / fail / HTTP **403**, wall time, PUTs/sec,
latency p50/p95. **No publish throttle** - 403 is treated as Lattice-side
evidence, not a bug to paper over with sleeps.

Built by [Polybolos Institute](https://www.polybolos.org).
**Independent sample - not an Anduril product.**

## What this is

A **door-level publish load harness**. It authenticates (OAuth + Sandboxes
Bearer), firehoses `PUT /api/v1/entities` for N synthetic AIR tracks, and
prints a JSON scoreboard (ok / fail / HTTP 403, wall time, PUTs/sec,
latency p50/p95).

It measures the **Lattice REST publish path only**.

**Why publish it:** Sandbox swarm injects often hit an HTTP **403** intake
cliff. Teams that paper over that with client-side sleeps look like they
misread the platform. This repo documents the honest method: firehose,
count accepts and 403s, report `first_fail_index`. That is how you show you
actually understand Lattice Sandboxes behavior under load.

## Expectations (read results this way)

| Target | What you should expect | How to read it |
|--------|------------------------|----------------|
| `--target mock` | Clean **5k / 10k** accepts when mock-lattice is healthy | Proves the **harness** and your machine loop |
| `--target live` | Often a mid-swarm **HTTP 403 cliff** (ok > 0, then rejects) | Proves you hit a **real Sandboxes intake limit** |
| Live with many 403s | Exit code still **0** | 403 is **evidence**, not a failed tool run |
| Mock with **0** ok | Exit code **1** | Harness / mock wiring is broken |

**Correct use:** publish the scoreboard, including `http_403` and
`first_fail_index`. That shows you exercised Lattice honestly.

**Incorrect use:** adding permanent PUT throttling so live always shows
10k/10k green. That hides the sandbox cliff this repo is meant to surface.

## Targets

| Target | Behavior |
|--------|----------|
| `--target mock` | Embedded [anduril-mock-lattice](https://github.com/Polybolos-Institute/anduril-mock-lattice) (default CI path) |
| `--target live` | Real Sandboxes via `LATTICE_*` env |

Optional: `SOAK_MOCK_FAIL_AFTER_N=109` simulates a sandbox-style 403 cliff on mock.

## Run

```powershell
# needs sibling anduril-mock-lattice (or --mock-url)
python -m soak --target mock --n 5000 --pretty
python -m soak --target mock --n 10000 --pretty

# live sandbox (load LATTICE_ENDPOINT CLIENT_ID CLIENT_SECRET ENV_TOKEN)
python -m soak --target live --n 5000 --pretty
python -m soak --auth-only --target live
```

## Report shape

```json
{
  "n_requested": 5000,
  "ok": 5000,
  "fail": 0,
  "http_403": 0,
  "wall_s": 12.3,
  "puts_per_sec": 406.5,
  "latency_ms_p50": 2.1,
  "latency_ms_p95": 4.0,
  "policy": "firehose (no publish throttle); 403 is Lattice-side evidence"
}
```

## Not in scope

- HOTL / Core / ThreatQueue / kin-checksum / Apollonius  
- Inbound stream soak  
- Permanent client-side rate limiting  

## Test

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Related doors

- [anduril-mock-lattice](https://github.com/Polybolos-Institute/anduril-mock-lattice)
- [anduril-lattice-rest-winhttp](https://github.com/Polybolos-Institute/anduril-lattice-rest-winhttp)
- [anduril-lattice-sandbox-dx](https://github.com/Polybolos-Institute/anduril-lattice-sandbox-dx)



## License
MIT - see [LICENSE](LICENSE).

## Contact

Polybolos Institute builds integrated C2 systems for contested operations.

For production deployment, integration guidance, and commercial licensing:

mark.brown@polybolos.org · https://www.polybolos.org

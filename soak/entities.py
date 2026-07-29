"""Synthetic swarm entities for publish soak."""

from __future__ import annotations

import math
import time
from typing import Any, Dict


def make_entity(index: int, prefix: str = "polybolos-soak") -> Dict[str, Any]:
    """Build a minimal AIR track around Dallas. Door-only shape."""
    now = time.time()
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    expiry = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + 3600))
    # Fan out in a spiral so IDs/positions are unique.
    angle = (index % 360) * (math.pi / 180.0)
    radius = 0.01 + (index % 500) * 0.00005
    lat = 32.7767 + radius * math.cos(angle)
    lon = -96.7970 + radius * math.sin(angle)
    alt = 500.0 + (index % 50) * 20.0
    eid = f"{prefix}-{index:05d}"
    return {
        "entityId": eid,
        "description": f"Soak swarm track {index}",
        "isLive": True,
        "createdTime": created,
        "expiryTime": expiry,
        "aliases": {"name": f"SOAK-{index:05d}"},
        "milView": {
            "disposition": "DISPOSITION_UNKNOWN",
            "environment": "ENVIRONMENT_AIR",
        },
        "location": {
            "position": {
                "latitudeDegrees": lat,
                "longitudeDegrees": lon,
                "altitudeHaeMeters": alt,
            }
        },
        "ontology": {
            "template": "TEMPLATE_TRACK",
            "platformType": "UNKNOWN AIR VEHICLE",
        },
        "provenance": {
            "dataType": "soak",
            "integrationName": "polybolos-lattice-publish-soak",
            "sourceUpdateTime": created,
        },
        "dataClassification": {
            "default": {"level": "CLASSIFICATION_LEVELS_UNCLASSIFIED"}
        },
    }

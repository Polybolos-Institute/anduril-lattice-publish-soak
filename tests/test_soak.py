"""Soak tests against embedded mock-lattice."""

from __future__ import annotations

import json

from soak.cli import main
from soak.entities import make_entity
from soak.runner import run_soak
from soak.client import LatticeClient


def test_make_entity_unique():
    a = make_entity(0)
    b = make_entity(1)
    assert a["entityId"] != b["entityId"]


def test_soak_mock_small(capsys):
    code = main(["--target", "mock", "--n", "25", "--progress-every", "0", "--pretty"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["n_requested"] == 25
    assert data["ok"] == 25
    assert data["fail"] == 0
    assert data["http_403"] == 0
    assert data["puts_per_sec"] > 0


def test_soak_mock_fail_after(monkeypatch, capsys):
    monkeypatch.setenv("SOAK_MOCK_FAIL_AFTER_N", "10")
    code = main(["--target", "mock", "--n", "20", "--progress-every", "0"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] == 10
    assert data["fail"] == 10
    assert data["http_403"] == 10

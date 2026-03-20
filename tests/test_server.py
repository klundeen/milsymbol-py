"""Tests for the FastAPI comparison server.

Requires the [server] optional dependency (fastapi, uvicorn).
Run separately from the core library tests:

    pytest tests/test_server.py -v
"""

import pytest

try:
    from fastapi.testclient import TestClient

    from server import app

    client = TestClient(app)
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")


class TestHealth:
    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_body(self):
        r = client.get("/health")
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestSymbolEndpoint:
    def test_requires_sidc(self):
        r = client.get("/symbol")
        assert r.status_code == 422  # validation error

    def test_valid_number_sidc(self):
        r = client.get("/symbol", params={"sidc": "10031000001211000000"})
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is True
        assert data["svg"].startswith("<svg")
        assert "anchor" in data
        assert "x" in data["anchor"]
        assert "y" in data["anchor"]
        assert "size" in data
        assert "width" in data["size"]
        assert "height" in data["size"]

    def test_valid_letter_sidc(self):
        r = client.get("/symbol", params={"sidc": "SFG-UCI----D"})
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is True
        assert "<svg" in data["svg"]

    def test_invalid_sidc_returns_placeholder(self):
        r = client.get("/symbol", params={"sidc": "ZZZZZZZZ"})
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is False
        assert "<svg" in data["svg"]  # still returns SVG placeholder

    def test_size_parameter(self):
        r40 = client.get("/symbol", params={"sidc": "10031000001211000000", "size": 40})
        r80 = client.get("/symbol", params={"sidc": "10031000001211000000", "size": 80})
        sz40 = r40.json()["size"]
        sz80 = r80.json()["size"]
        assert abs(sz80["width"] - sz40["width"] * 2) < 0.1

    def test_quantity_passthrough(self):
        r = client.get("/symbol", params={"sidc": "10031000001211000000", "quantity": "200"})
        data = r.json()
        assert ">200<" in data["svg"]

    def test_type_passthrough(self):
        r = client.get("/symbol", params={"sidc": "SFG-UCI----", "type": "MACHINE GUN"})
        data = r.json()
        assert ">MACHINE GUN<" in data["svg"]

    def test_designation_passthrough(self):
        r = client.get("/symbol", params={"sidc": "SFG-UCI----", "designation": "A CO"})
        data = r.json()
        assert ">A CO<" in data["svg"]

    def test_staff_comments_passthrough(self):
        r = client.get("/symbol", params={"sidc": "SFG-UCI----", "staffComments": "EN ROUTE"})
        data = r.json()
        assert ">EN ROUTE<" in data["svg"]

    def test_multiple_text_fields(self):
        r = client.get(
            "/symbol",
            params={
                "sidc": "SFG-UCI----D",
                "quantity": "50",
                "type": "RIFLE",
                "designation": "B CO",
                "staffComments": "MOVING",
            },
        )
        data = r.json()
        assert data["valid"] is True
        svg = data["svg"]
        assert ">50<" in svg
        assert ">RIFLE<" in svg
        assert ">B CO<" in svg
        assert ">MOVING<" in svg

    def test_metadata_structure(self):
        r = client.get("/symbol", params={"sidc": "10031000001211000000"})
        meta = r.json()["metadata"]
        assert meta["affiliation"] == "Friend"
        assert meta["dimension"] == "Ground"

    def test_hostile_affiliation(self):
        r = client.get("/symbol", params={"sidc": "10061000001211000000"})
        data = r.json()
        assert data["valid"] is True
        assert "rgb(255,128,128)" in data["svg"]  # hostile red fill

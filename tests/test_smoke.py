"""Smoke tests — verify Python SVG output matches JS reference exactly."""

import json
from pathlib import Path

import pytest

from milsymbol import Symbol

SMOKE_FILE = Path(__file__).parent.parent / "milsymbol" / "data" / "smoke-tests.json"


def _load_smoke_tests():
    if not SMOKE_FILE.exists():
        # Try alternate location
        alt = Path(__file__).parent.parent / "smoke-tests.json"
        if alt.exists():
            with open(alt) as f:
                return json.load(f)
        pytest.skip("smoke-tests.json not found")
    with open(SMOKE_FILE) as f:
        return json.load(f)


SMOKE_TESTS = _load_smoke_tests()


@pytest.mark.parametrize(
    "test_case",
    SMOKE_TESTS,
    ids=[t["name"] for t in SMOKE_TESTS],
)
def test_svg_exact_match(test_case):
    """SVG output must match JS reference character-for-character."""
    sym = Symbol(test_case["sidc"], size=80)
    assert sym.is_valid() == test_case["valid"]
    if test_case["valid"]:
        assert sym.as_svg() == test_case["svg"]


@pytest.mark.parametrize(
    "test_case",
    SMOKE_TESTS,
    ids=[t["name"] for t in SMOKE_TESTS],
)
def test_anchor(test_case):
    """Anchor points must match JS reference."""
    sym = Symbol(test_case["sidc"], size=80)
    if not test_case["valid"]:
        return
    anchor = sym.get_anchor()
    js_anchor = test_case["anchor"]
    assert abs(anchor["x"] - js_anchor["x"]) < 0.01
    assert abs(anchor["y"] - js_anchor["y"]) < 0.01


@pytest.mark.parametrize(
    "test_case",
    SMOKE_TESTS,
    ids=[t["name"] for t in SMOKE_TESTS],
)
def test_size(test_case):
    """Symbol size must match JS reference."""
    sym = Symbol(test_case["sidc"], size=80)
    if not test_case["valid"]:
        return
    size = sym.get_size()
    js_size = test_case["symbolSize"]
    assert abs(size["width"] - js_size["width"]) < 0.01
    assert abs(size["height"] - js_size["height"]) < 0.01


class TestBasicAPI:
    def test_number_sidc(self):
        sym = Symbol("10031000001211000000")
        assert sym.is_valid()
        assert "<svg" in sym.as_svg()

    def test_letter_sidc(self):
        sym = Symbol("SFG-UCI----D")
        assert sym.is_valid()
        assert "<svg" in sym.as_svg()

    def test_invalid_sidc(self):
        sym = Symbol("ZZZZZZZZZZZZZZZZZZZZ")
        assert not sym.is_valid()

    def test_hostile_number(self):
        sym = Symbol("10061000001211000000")
        assert sym.is_valid()
        assert "rgb(255,128,128)" in sym.as_svg()  # hostile fill

    def test_friendly_number(self):
        sym = Symbol("10031000001211000000")
        assert sym.is_valid()
        assert "rgb(128,224,255)" in sym.as_svg()  # friendly fill

    def test_size_scaling(self):
        s40 = Symbol("10031000001211000000", size=40)
        s80 = Symbol("10031000001211000000", size=80)
        sz40 = s40.get_size()
        sz80 = s80.get_size()
        assert abs(sz80["width"] - sz40["width"] * 2) < 0.1

    def test_metadata(self):
        sym = Symbol("10031000001211000000")
        meta = sym.get_metadata()
        assert meta["affiliation"] == "Friend"
        assert meta["dimension"] == "Ground"
        assert meta["symbolset"] == "10"

    def test_all_affiliations_valid(self):
        for aff in "0123456":
            sidc = f"100{aff}1000001211000000"
            sym = Symbol(sidc)
            assert sym.is_valid(), f"Affiliation {aff} should be valid"

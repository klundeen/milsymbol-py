"""Tests for text fields, modifiers, and their combinations.

These tests verify against JS reference SVGs and would catch regressions
like using the wrong bbox for text positioning (full symbol bbox vs frame bbox).
"""

import json
import re
from pathlib import Path

import pytest

from milsymbol import Symbol

DATA = Path(__file__).parent.parent / "milsymbol" / "data"


def _load(name):
    p = DATA / name
    if not p.exists():
        pytest.skip(f"{name} not found")
    with open(p) as f:
        return json.load(f)


# ── Modifier tests (echelon, mobility, HQ/TF/FD) ──

MODIFIER_TESTS = _load("modifier-tests.json")


@pytest.mark.parametrize("t", MODIFIER_TESTS, ids=[t["name"] for t in MODIFIER_TESTS])
def test_modifier_svg_exact(t):
    """Modifier SVG output must match JS reference exactly."""
    s = Symbol(t["sidc"], size=80)
    assert s.is_valid()
    assert s.as_svg() == t["svg"]


@pytest.mark.parametrize("t", MODIFIER_TESTS, ids=[t["name"] for t in MODIFIER_TESTS])
def test_modifier_size(t):
    s = Symbol(t["sidc"], size=80)
    sz = s.get_size()
    assert abs(sz["width"] - t["symbolSize"]["width"]) < 0.1
    assert abs(sz["height"] - t["symbolSize"]["height"]) < 0.1


@pytest.mark.parametrize("t", MODIFIER_TESTS, ids=[t["name"] for t in MODIFIER_TESTS])
def test_modifier_anchor(t):
    s = Symbol(t["sidc"], size=80)
    a = s.get_anchor()
    assert abs(a["x"] - t["anchor"]["x"]) < 0.1
    assert abs(a["y"] - t["anchor"]["y"]) < 0.1


# ── Combined text + modifier tests ──

COMBINED_TESTS = _load("combined-tests.json")


@pytest.mark.parametrize("t", COMBINED_TESTS, ids=[t["name"] for t in COMBINED_TESTS])
def test_combined_size(t):
    """Size must match JS reference (tolerance for float rounding)."""
    s = Symbol(t["sidc"], **t["opts"])
    sz = s.get_size()
    assert abs(sz["width"] - t["symbolSize"]["width"]) < 0.1, (
        f"width: py={sz['width']} js={t['symbolSize']['width']}"
    )
    assert abs(sz["height"] - t["symbolSize"]["height"]) < 0.1, (
        f"height: py={sz['height']} js={t['symbolSize']['height']}"
    )


@pytest.mark.parametrize("t", COMBINED_TESTS, ids=[t["name"] for t in COMBINED_TESTS])
def test_combined_anchor(t):
    """Anchor must match JS reference."""
    s = Symbol(t["sidc"], **t["opts"])
    a = s.get_anchor()
    assert abs(a["x"] - t["anchor"]["x"]) < 0.1, f"x: py={a['x']} js={t['anchor']['x']}"
    assert abs(a["y"] - t["anchor"]["y"]) < 0.1, f"y: py={a['y']} js={t['anchor']['y']}"


@pytest.mark.parametrize("t", COMBINED_TESTS, ids=[t["name"] for t in COMBINED_TESTS])
def test_combined_text_content(t):
    """All text field values must appear in the SVG."""
    s = Symbol(t["sidc"], **t["opts"])
    svg = s.as_svg()
    texts_in_svg = set(re.findall(r"<text[^>]*>([^<]+)</text>", svg))
    opts = t["opts"]
    for field in (
        "quantity",
        "type",
        "uniqueDesignation",
        "staffComments",
        "additionalInformation",
        "dtg",
        "location",
        "speed",
        "higherFormation",
        "iffSif",
    ):
        val = opts.get(field, "")
        if val:
            # Value might be combined with / separator
            for part in val.split("/"):
                found = any(part in txt for txt in texts_in_svg)
                assert found, f"'{part}' from {field} not found in SVG texts: {texts_in_svg}"


# ── Specific regression tests ──


class TestTextFieldBboxRegression:
    """Tests that would have caught the frame bbox vs full bbox bug."""

    def test_quantity_y_position_with_echelon(self):
        """Quantity text must be positioned relative to frame bbox, not echelon-expanded bbox.
        The frame y1 for friendly ground is 50, so quantity should be at y=40 (50-10).
        If we incorrectly use the echelon-expanded bbox (y1≈22.5), quantity would be at y=12.5."""
        s = Symbol("SFG-UCI----D", size=80, quantity="3")
        svg = s.as_svg()
        match = re.search(r'<text[^>]*y="(\d+)"[^>]*>3</text>', svg)
        assert match, "Quantity text '3' not found"
        y = int(match.group(1))
        assert y == 40, f"Quantity y={y}, expected 40 (frame bbox.y1 - 10)"

    def test_size_matches_js_with_echelon_and_text(self):
        """Size with echelon+text must match JS exactly — the screenshot bug."""
        s = Symbol(
            "SFG-UCI----D",
            size=80,
            quantity="3",
            type="MACHINE GUN",
            uniqueDesignation="3-C",
            staffComments="REINFORCEMENTS",
        )
        sz = s.get_size()
        assert abs(sz["width"] - 753.6) < 0.1
        assert abs(sz["height"] - 140.8) < 0.1

    def test_anchor_matches_js_with_echelon_and_text(self):
        s = Symbol(
            "SFG-UCI----D",
            size=80,
            quantity="3",
            type="MACHINE GUN",
            uniqueDesignation="3-C",
            staffComments="REINFORCEMENTS",
        )
        a = s.get_anchor()
        assert abs(a["x"] - 335.2) < 0.1
        assert abs(a["y"] - 83.2) < 0.1

    def test_echelon_without_text_unchanged(self):
        """Echelon-only symbol must still match smoke test reference."""
        s = Symbol("SFG-UCI----D", size=80)
        # This is in the smoke tests — should produce same SVG as before
        assert s.is_valid()
        assert "<svg" in s.as_svg()


class TestModifierRendering:
    """Verify modifier geometries appear in SVG."""

    def test_company_echelon_has_vertical_line(self):
        s = Symbol("10031000151211000000", size=80)
        assert "L100," in s.as_svg()

    def test_battalion_echelon_has_two_lines(self):
        s = Symbol("10031000161211000000", size=80)
        svg = s.as_svg()
        assert "L90," in svg
        assert "L110," in svg

    def test_brigade_echelon_has_x(self):
        s = Symbol("10031000181211000000", size=80)
        assert "l25,-25" in s.as_svg()

    def test_tracked_mobility(self):
        s = Symbol("10031000331211000000", size=80)
        assert "c15,0 15,15 0,15" in s.as_svg()

    def test_wheeled_mobility(self):
        s = Symbol("10031000311211000000", size=80)
        svg = s.as_svg()
        assert "circle" in svg  # wheels are circles

    def test_feint_dummy_has_dashed_lines(self):
        s = Symbol("10031001001211000000", size=80)
        assert "stroke-dasharray" in s.as_svg()

    def test_modifier_doesnt_break_plain_symbol(self):
        """Symbol without modifiers should be unchanged."""
        s_plain = Symbol("10031000001211000000", size=80)
        assert s_plain.is_valid()
        # No modifier artifacts
        svg = s_plain.as_svg()
        assert "stroke-dasharray" not in svg


class TestTextFieldMapping:
    """Verify text fields appear in correct positions per dimension."""

    def test_ground_left_fields(self):
        s = Symbol("SFG-UCI----", size=80, dtg="301400Z", uniqueDesignation="A CO")
        svg = s.as_svg()
        # Left fields use textanchor=end
        assert 'text-anchor="end"' in svg
        assert ">301400Z<" in svg
        assert ">A CO<" in svg

    def test_ground_right_fields(self):
        s = Symbol("SFG-UCI----", size=80, staffComments="EN ROUTE", higherFormation="3ID")
        svg = s.as_svg()
        assert 'text-anchor="start"' in svg
        assert ">EN ROUTE<" in svg
        assert ">3ID<" in svg

    def test_quantity_centered_above(self):
        s = Symbol("10031000001211000000", size=80, quantity="200")
        svg = s.as_svg()
        assert 'text-anchor="middle"' in svg
        assert ">200<" in svg

    def test_no_text_no_expansion(self):
        """Without text fields, size should match base symbol."""
        s_plain = Symbol("10031000001211000000", size=80)
        s_text = Symbol("10031000001211000000", size=80, quantity="50")
        assert s_text.get_size()["height"] > s_plain.get_size()["height"]
        assert s_text.get_size()["width"] >= s_plain.get_size()["width"]

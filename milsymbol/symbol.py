"""Symbol class - main entry point for milsymbol Python port.

Uses pre-extracted draw instructions from the JS library for all affiliations.
Supports both number-based (2525D/E) and letter-based (2525B/C, APP6B) SIDCs.
"""

import gzip
import json
from pathlib import Path
from typing import Optional

from .renderer import render_svg

_DATA_DIR = Path(__file__).parent / "data"

_number_data: Optional[dict] = None
_letter_data: Optional[dict] = None


def _load_number_data() -> dict:
    global _number_data
    if _number_data is None:
        with gzip.open(_DATA_DIR / "number-data.json.gz", "rt", encoding="utf-8") as f:
            _number_data = json.load(f)
    return _number_data


def _load_letter_data() -> dict:
    global _letter_data
    if _letter_data is None:
        with gzip.open(_DATA_DIR / "letter-data.json.gz", "rt", encoding="utf-8") as f:
            _letter_data = json.load(f)
    return _letter_data


_NUMBER_AFFILIATIONS = {
    "0": "Pending", "1": "Unknown", "2": "AssumedFriend",
    "3": "Friend", "4": "Neutral", "5": "Suspect", "6": "Hostile",
}

_LETTER_AFFILIATIONS = {
    "P": "Pending", "U": "Unknown", "A": "AssumedFriend",
    "F": "Friend", "N": "Neutral", "S": "Suspect", "H": "Hostile",
    "G": "Friend", "W": "Unknown", "D": "Friend",
    "L": "Hostile", "M": "AssumedFriend", "J": "Friend", "K": "Friend",
}

_SS_DIMENSION = {
    "01": "Air", "02": "Air", "05": "Air", "06": "Air",
    "10": "Ground", "11": "Ground", "15": "Ground",
    "20": "Sea", "25": "Ground", "27": "Ground", "30": "Ground",
    "35": "Subsurface", "36": "Subsurface",
    "40": "Ground", "45": "Ground",
    "50": "Air", "51": "Air", "52": "Air",
    "60": "Ground",
}

_LETTER_DIMENSION = {
    "P": "Air", "A": "Air",
    "G": "Ground", "U": "Ground",
    "S": "Sea", "F": "Sea",
    "Z": "Unknown",
}


def _is_number_sidc(sidc: str) -> bool:
    return sidc.isdigit() and len(sidc) >= 20


class Symbol:
    """Military symbol generator.

    Usage:
        sym = Symbol("10031000001211000000", size=80)
        svg = sym.as_svg()
    """

    def __init__(self, sidc: str, **kwargs):
        self.sidc = str(sidc).strip()
        self.size = kwargs.get("size", 100)
        self.stroke_width = kwargs.get("stroke_width", 4)
        self.outline_width = kwargs.get("outline_width", 0)
        self.quantity = kwargs.get("quantity", "")
        self.type = kwargs.get("type", "")
        self.unique_designation = kwargs.get("unique_designation", "")
        self.staff_comments = kwargs.get("staff_comments", "")
        self.additional_information = kwargs.get("additional_information", "")
        self.direction = kwargs.get("direction")
        self.dtg = kwargs.get("dtg", "")
        self.location = kwargs.get("location", "")

        self._number_sidc = _is_number_sidc(self.sidc)
        self._draw_instructions = None
        self._bbox = None
        self._valid = None
        self._metadata = {}
        self._svg_cache = None
        self._resolve()

    def _resolve(self):
        if self._number_sidc:
            self._resolve_number()
        else:
            self._resolve_letter()

    def _resolve_number(self):
        data = _load_number_data()
        sidc = self.sidc.ljust(20, "0")

        self._metadata = {
            "version": sidc[0:2],
            "context": sidc[2],
            "affiliation_code": sidc[3],
            "affiliation": _NUMBER_AFFILIATIONS.get(sidc[3], "Unknown"),
            "symbolset": sidc[4:6],
            "dimension": _SS_DIMENSION.get(sidc[4:6], "Ground"),
            "status": sidc[6],
            "hq_tf_fd": sidc[7],
            "echelon": sidc[8:10],
            "entity": sidc[10:16],
            "modifier1": sidc[16:18],
            "modifier2": sidc[18:20],
        }

        if sidc in data:
            entry = data[sidc]
            self._draw_instructions = entry["di"]
            self._bbox = entry["bb"]
            self._valid = True
        else:
            self._valid = False

    def _resolve_letter(self):
        data = _load_letter_data()
        sidc = self.sidc

        aff_code = sidc[1].upper() if len(sidc) >= 2 else ""
        bd_code = sidc[2].upper() if len(sidc) >= 3 else ""

        self._metadata = {
            "affiliation": _LETTER_AFFILIATIONS.get(aff_code, "Unknown"),
            "affiliation_code": aff_code,
            "dimension": _LETTER_DIMENSION.get(bd_code, "Ground"),
            "battle_dimension": bd_code,
            "coding_scheme": sidc[0] if len(sidc) > 0 else "",
        }

        # Direct lookup
        if sidc in data:
            entry = data[sidc]
            self._draw_instructions = entry["di"]
            self._bbox = entry["bb"]
            self._valid = True
            return

        # Try padding/truncating dashes
        padded = sidc.ljust(15, "-")[:15]
        if padded in data:
            entry = data[padded]
            self._draw_instructions = entry["di"]
            self._bbox = entry["bb"]
            self._valid = True
            return

        stripped = sidc.rstrip("-")
        for key in data:
            if key.rstrip("-") == stripped:
                entry = data[key]
                self._draw_instructions = entry["di"]
                self._bbox = entry["bb"]
                self._valid = True
                return

        # For letter SIDCs longer than 10 chars, try the 10-char base
        # (extra chars are echelon/mobility modifiers handled separately by JS)
        if len(sidc) > 10:
            base10 = sidc[:10]
            if base10 in data:
                entry = data[base10]
                self._draw_instructions = entry["di"]
                self._bbox = entry["bb"]
                self._valid = True
                return
            # Also try padding base to match stored format
            for key in data:
                if key.rstrip("-") == base10.rstrip("-"):
                    entry = data[key]
                    self._draw_instructions = entry["di"]
                    self._bbox = entry["bb"]
                    self._valid = True
                    return

        self._valid = False

    def is_valid(self) -> bool:
        return self._valid is True

    def get_anchor(self) -> dict:
        if not self._bbox:
            return {"x": 50, "y": 50}
        sw = float(self.stroke_width)
        ow = float(self.outline_width)
        return {
            "x": (100 - self._bbox["x1"] + sw + ow) * self.size / 100,
            "y": (100 - self._bbox["y1"] + sw + ow) * self.size / 100,
        }

    def get_size(self) -> dict:
        if not self._bbox:
            return {"width": 0, "height": 0}
        sw = float(self.stroke_width)
        ow = float(self.outline_width)
        bw = (self._bbox["x2"] - self._bbox["x1"]) + sw * 2 + ow * 2
        bh = (self._bbox["y2"] - self._bbox["y1"]) + sw * 2 + ow * 2
        return {
            "width": bw * self.size / 100,
            "height": bh * self.size / 100,
        }

    def get_metadata(self) -> dict:
        return dict(self._metadata)

    def as_svg(self) -> str:
        if self._svg_cache:
            return self._svg_cache
        if not self._draw_instructions or not self._bbox:
            return (
                '<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 200 200">'
                '<text x="100" y="110" text-anchor="middle" font-size="60" fill="red">?</text>'
                '</svg>'
            )
        self._svg_cache = render_svg(
            draw_instructions=self._draw_instructions,
            bbox=self._bbox,
            stroke_width=self.stroke_width,
            outline_width=self.outline_width,
            size=self.size,
        )
        return self._svg_cache

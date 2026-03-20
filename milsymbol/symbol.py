"""Symbol class - main entry point for milsymbol Python port.

Uses pre-extracted draw instructions from the JS library for all affiliations.
Supports both number-based (2525D/E) and letter-based (2525B/C, APP6B) SIDCs.
"""

import gzip
import json
from pathlib import Path
from typing import Optional

from .renderer import render_svg
from .textfields import compute_text_fields
from .modifiers import compute_modifiers, parse_modifiers

_DATA_DIR = Path(__file__).parent / "data"

_number_data: Optional[dict] = None
_letter_data: Optional[dict] = None
_geometries: Optional[dict] = None


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


def _load_geometries() -> dict:
    global _geometries
    if _geometries is None:
        with open(_DATA_DIR / "geometries.json") as f:
            _geometries = json.load(f)
    return _geometries


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

# baseDimension determines text field layout (from JS metadata)
_SS_BASE_DIMENSION = {
    "01": "Air", "02": "Air", "05": "Air", "06": "Air",
    "10": "Ground", "11": "Ground", "15": "Ground",
    "20": "Ground", "25": "Ground", "27": "Ground", "30": "Sea",
    "35": "Subsurface", "36": "Subsurface",
    "40": "Ground", "45": "Ground",
    "50": "Air", "51": "Air", "52": "Ground",
    "60": "Ground",
}

# Whether the symbol set represents a "unit" (affects text field mapping)
_SS_IS_UNIT = {
    "10": True, "11": True, "27": True, "40": True,
}

# Map (dimension, affiliation) → geometry key for frame bbox lookup
_FRAME_GEO_MAP = {
    ("Ground", "Friend"): "GroundFriend", ("Ground", "Hostile"): "GroundHostile",
    ("Ground", "Neutral"): "GroundNeutral", ("Ground", "Unknown"): "GroundUnknown",
    ("Ground", "AssumedFriend"): "GroundFriend", ("Ground", "Suspect"): "GroundHostile",
    ("Ground", "Pending"): "GroundUnknown",
    ("Air", "Friend"): "AirFriend", ("Air", "Hostile"): "AirHostile",
    ("Air", "Neutral"): "AirNeutral", ("Air", "Unknown"): "AirUnknown",
    ("Air", "AssumedFriend"): "AirFriend", ("Air", "Suspect"): "AirHostile",
    ("Air", "Pending"): "AirUnknown",
    ("Sea", "Friend"): "SeaFriend", ("Sea", "Hostile"): "SeaHostile",
    ("Sea", "Neutral"): "SeaNeutral", ("Sea", "Unknown"): "SeaUnknown",
    ("Sea", "AssumedFriend"): "SeaFriend", ("Sea", "Suspect"): "SeaHostile",
    ("Sea", "Pending"): "SeaUnknown",
    ("Subsurface", "Friend"): "SubsurfaceFriend", ("Subsurface", "Hostile"): "SubsurfaceHostile",
    ("Subsurface", "Neutral"): "SubsurfaceNeutral", ("Subsurface", "Unknown"): "SubsurfaceUnknown",
    ("Subsurface", "AssumedFriend"): "SubsurfaceFriend", ("Subsurface", "Suspect"): "SubsurfaceHostile",
    ("Subsurface", "Pending"): "SubsurfaceUnknown",
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

        # Text fields (matching JS option names)
        self.quantity = kwargs.get("quantity", "")
        self.type = kwargs.get("type", "")
        self.unique_designation = kwargs.get("unique_designation",
                                    kwargs.get("uniqueDesignation", ""))
        self.staff_comments = kwargs.get("staff_comments",
                                kwargs.get("staffComments", ""))
        self.additional_information = kwargs.get("additional_information",
                                        kwargs.get("additionalInformation", ""))
        self.direction = kwargs.get("direction")
        self.dtg = kwargs.get("dtg", "")
        self.location = kwargs.get("location", "")
        self.speed = kwargs.get("speed", "")
        self.reinforced_reduced = kwargs.get("reinforced_reduced",
                                    kwargs.get("reinforcedReduced", ""))
        self.higher_formation = kwargs.get("higher_formation",
                                  kwargs.get("higherFormation", ""))
        self.evaluation_rating = kwargs.get("evaluation_rating",
                                   kwargs.get("evaluationRating", ""))
        self.combat_effectiveness = kwargs.get("combat_effectiveness",
                                      kwargs.get("combatEffectiveness", ""))
        self.signature_equipment = kwargs.get("signature_equipment",
                                     kwargs.get("signatureEquipment", ""))
        self.hostile = kwargs.get("hostile", "")
        self.iff_sif = kwargs.get("iff_sif", kwargs.get("iffSif", ""))
        self.sigint = kwargs.get("sigint", "")
        self.altitude_depth = kwargs.get("altitude_depth",
                                kwargs.get("altitudeDepth", ""))
        self.special_headquarters = kwargs.get("special_headquarters",
                                      kwargs.get("specialHeadquarters", ""))
        self.country = kwargs.get("country", "")
        self.platform_type = kwargs.get("platform_type",
                               kwargs.get("platformType", ""))
        self.equipment_teardown_time = kwargs.get("equipment_teardown_time",
                                         kwargs.get("equipmentTeardownTime", ""))
        self.common_identifier = kwargs.get("common_identifier",
                                   kwargs.get("commonIdentifier", ""))
        self.auxiliary_equipment_indicator = kwargs.get("auxiliary_equipment_indicator",
                                               kwargs.get("auxiliaryEquipmentIndicator", ""))
        self.headquarters_element = kwargs.get("headquarters_element",
                                      kwargs.get("headquartersElement", ""))
        self.installation_composition = kwargs.get("installation_composition",
                                          kwargs.get("installationComposition", ""))
        self.guarded_unit = kwargs.get("guarded_unit",
                              kwargs.get("guardedUnit", ""))
        self.special_designator = kwargs.get("special_designator",
                                    kwargs.get("specialDesignator", ""))

        # Style
        self.font_family = kwargs.get("font_family",
                              kwargs.get("fontfamily", "Arial"))
        self.info_size = kwargs.get("info_size", kwargs.get("infoSize", 40))
        self.info_color = kwargs.get("info_color", kwargs.get("infoColor", ""))

        self._number_sidc = _is_number_sidc(self.sidc)
        self._draw_instructions = None
        self._bbox = None
        self._valid = None
        self._metadata = {}
        self._svg_cache = None
        self._composed = False
        self._final_di = None
        self._final_bbox = None
        self._resolve()

    def _resolve(self):
        if self._number_sidc:
            self._resolve_number()
        else:
            self._resolve_letter()

    def _resolve_number(self):
        data = _load_number_data()
        sidc = self.sidc.ljust(20, "0")
        ss = sidc[4:6]

        self._metadata = {
            "version": sidc[0:2],
            "context": sidc[2],
            "affiliation_code": sidc[3],
            "affiliation": _NUMBER_AFFILIATIONS.get(sidc[3], "Unknown"),
            "symbolset": ss,
            "dimension": _SS_DIMENSION.get(ss, "Ground"),
            "baseDimension": _SS_BASE_DIMENSION.get(ss, "Ground"),
            "unit": _SS_IS_UNIT.get(ss, False),
            "dismounted": ss == "27",
            "activity": ss == "40",
            "numberSIDC": True,
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
            # Try normalizing modifier fields (pos 7=HQ/TF/FD, pos 8-9=echelon/mobility) to zero
            base_sidc = sidc[:7] + "0" + "00" + sidc[10:]
            if base_sidc in data:
                entry = data[base_sidc]
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
            "baseDimension": _LETTER_DIMENSION.get(bd_code, "Ground"),
            "battle_dimension": bd_code,
            "coding_scheme": sidc[0] if len(sidc) > 0 else "",
            "numberSIDC": False,
            "unit": False,
            "dismounted": False,
            "activity": False,
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

    def _get_frame_bbox(self) -> dict:
        """Get the frame geometry bbox (without echelon/modifier expansion)."""
        dim = self._metadata.get("dimension", "Ground")
        aff = self._metadata.get("affiliation", "Unknown")
        geo_key = _FRAME_GEO_MAP.get((dim, aff))
        if geo_key:
            geos = _load_geometries()
            if geo_key in geos:
                return geos[geo_key]["bbox"]
        return self._bbox

    def _compose(self):
        """Compose final draw instructions and bbox, including modifiers and text fields."""
        if self._composed:
            return
        self._composed = True

        if not self._draw_instructions or not self._bbox:
            return

        # Build options dict matching JS field names
        opts = {
            "sidc": self.sidc,
            "quantity": self.quantity,
            "type": self.type,
            "uniqueDesignation": self.unique_designation,
            "staffComments": self.staff_comments,
            "additionalInformation": self.additional_information,
            "dtg": self.dtg,
            "location": self.location,
            "speed": self.speed,
            "reinforcedReduced": self.reinforced_reduced,
            "higherFormation": self.higher_formation,
            "evaluationRating": self.evaluation_rating,
            "combatEffectiveness": self.combat_effectiveness,
            "signatureEquipment": self.signature_equipment,
            "hostile": self.hostile,
            "iffSif": self.iff_sif,
            "altitudeDepth": self.altitude_depth,
            "specialHeadquarters": self.special_headquarters,
            "platformType": self.platform_type,
            "equipmentTeardownTime": self.equipment_teardown_time,
            "commonIdentifier": self.common_identifier,
            "auxiliaryEquipmentIndicator": self.auxiliary_equipment_indicator,
            "headquartersElement": self.headquarters_element,
            "installationComposition": self.installation_composition,
            "guardedUnit": self.guarded_unit,
            "specialDesignator": self.special_designator,
            "country": self.country,
        }

        style = {
            "fontfamily": self.font_family,
            "info_size": self.info_size,
            "info_color": self.info_color,
        }

        text_draw, text_bbox = compute_text_fields(
            opts, self._metadata, self._get_frame_bbox(), style
        )

        # Compute modifiers (echelon, mobility, HQ/TF/FD) using frame bbox
        mod_style = {
            "stroke_width": self.stroke_width,
            "hq_staff_length": style.get("hq_staff_length", 0),
        }
        mod_draw, mod_bbox = compute_modifiers(
            self._metadata, self._get_frame_bbox(), mod_style
        )

        # Merge: base draw instructions + modifiers + text fields
        self._final_di = list(self._draw_instructions)
        if mod_draw:
            self._final_di.extend(mod_draw)
        if text_draw:
            self._final_di.extend(text_draw)

        # Merge bounding boxes
        self._final_bbox = dict(self._bbox)
        for extra_bbox in (mod_bbox, text_bbox):
            if extra_bbox:
                self._final_bbox = {
                    "x1": min(self._final_bbox["x1"], extra_bbox["x1"]),
                    "y1": min(self._final_bbox["y1"], extra_bbox["y1"]),
                    "x2": max(self._final_bbox["x2"], extra_bbox["x2"]),
                    "y2": max(self._final_bbox["y2"], extra_bbox["y2"]),
                }

    def get_anchor(self) -> dict:
        self._compose()
        bb = self._final_bbox or self._bbox
        if not bb:
            return {"x": 50, "y": 50}
        sw = float(self.stroke_width)
        ow = float(self.outline_width)

        # HQ symbols: anchor at base of HQ staff line
        if self._metadata.get("numberSIDC") and self._metadata.get("hq_tf_fd") in ("2", "3", "6", "7"):
            frame_bb = self._get_frame_bbox()
            hq_staff = 100  # default HQ staff length
            ax = frame_bb["x1"]
            ay = frame_bb["y2"] + hq_staff
            return {
                "x": (ax - bb["x1"] + sw + ow) * self.size / 100,
                "y": (ay - bb["y1"] + sw + ow) * self.size / 100,
            }

        return {
            "x": (100 - bb["x1"] + sw + ow) * self.size / 100,
            "y": (100 - bb["y1"] + sw + ow) * self.size / 100,
        }

    def get_size(self) -> dict:
        self._compose()
        bb = self._final_bbox or self._bbox
        if not bb:
            return {"width": 0, "height": 0}
        sw = float(self.stroke_width)
        ow = float(self.outline_width)
        bw = (bb["x2"] - bb["x1"]) + sw * 2 + ow * 2
        bh = (bb["y2"] - bb["y1"]) + sw * 2 + ow * 2
        return {
            "width": bw * self.size / 100,
            "height": bh * self.size / 100,
        }

    def get_metadata(self) -> dict:
        return dict(self._metadata)

    def as_svg(self) -> str:
        if self._svg_cache:
            return self._svg_cache
        self._compose()
        di = self._final_di or self._draw_instructions
        bb = self._final_bbox or self._bbox
        if not di or not bb:
            return (
                '<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 200 200">'
                '<text x="100" y="110" text-anchor="middle" font-size="60" fill="red">?</text>'
                '</svg>'
            )
        self._svg_cache = render_svg(
            draw_instructions=di,
            bbox=bb,
            stroke_width=self.stroke_width,
            outline_width=self.outline_width,
            size=self.size,
        )
        return self._svg_cache

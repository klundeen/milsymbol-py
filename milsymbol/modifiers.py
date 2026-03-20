"""Symbol modifiers — echelon, mobility, HQ/TF/FD, installation, feint/dummy.

Ports modifier.js from the JS library. These are computed at render time
from SIDC metadata fields, not extracted from the data files.
"""

# Echelon code (SIDC pos 8-9) → name
_ECHELON_CODES = {
    "11": "Team/Crew", "12": "Squad", "13": "Section",
    "14": "Platoon/detachment", "15": "Company/battery/troop",
    "16": "Battalion/squadron", "17": "Regiment/group",
    "18": "Brigade", "21": "Division", "22": "Corps/MEF",
    "23": "Army", "24": "Army Group/front", "25": "Region/Theater",
    "26": "Command",
}

# Mobility code (SIDC pos 8-9) → name
_MOBILITY_CODES = {
    "31": "Wheeled limited cross country", "32": "Wheeled cross country",
    "33": "Tracked", "34": "Wheeled and tracked combination",
    "35": "Towed", "36": "Rail", "37": "Pack animals",
    "41": "Over snow (prime mover)", "42": "Sled",
    "51": "Barge", "52": "Amphibious",
    "61": "Short towed array", "62": "Long towed Array",
}

# HQ/TF/FD code (SIDC pos 7) → flags
_HQTFFD = {
    "0": (False, False, False),
    "1": (False, False, True),   # feint/dummy
    "2": (True,  False, False),  # HQ
    "3": (True,  False, True),   # HQ + feint/dummy
    "4": (False, True,  False),  # task force
    "5": (False, True,  True),   # TF + feint/dummy
    "6": (True,  True,  False),  # HQ + TF
    "7": (True,  True,  True),   # HQ + TF + feint/dummy
}


def _n(v):
    """Format number for SVG path data: strip .0 from integers."""
    f = float(v)
    return str(int(f)) if f == int(f) else str(f)


def parse_modifiers(metadata: dict) -> dict:
    """Parse modifier flags from SIDC metadata.

    Returns dict with echelon, mobility, headquarters, taskForce,
    feintDummy, installation keys.
    """
    result = {
        "echelon": None,
        "mobility": None,
        "headquarters": False,
        "taskForce": False,
        "feintDummy": False,
        "installation": False,
    }

    if not metadata.get("numberSIDC"):
        return result

    ec = metadata.get("echelon", "00")
    result["echelon"] = _ECHELON_CODES.get(ec)
    result["mobility"] = _MOBILITY_CODES.get(ec)

    hqtffd = metadata.get("hq_tf_fd", "0")
    hq, tf, fd = _HQTFFD.get(hqtffd, (False, False, False))
    result["headquarters"] = hq
    result["taskForce"] = tf
    result["feintDummy"] = fd

    # Installation is determined by symbol set (SS 30 = land installation)
    result["installation"] = metadata.get("symbolset") == "30"

    return result


def compute_modifiers(metadata: dict, bbox: dict, style: dict) -> tuple:
    """Compute modifier draw instructions and expanded bounding box.

    Args:
        metadata: Parsed SIDC metadata
        bbox: Frame bounding box {x1, y1, x2, y2}
        style: Style settings

    Returns:
        (draw_instructions, modifier_bbox) or ([], None)
    """
    mods = parse_modifiers(metadata)
    if not any([mods["echelon"], mods["mobility"], mods["headquarters"],
                mods["taskForce"], mods["feintDummy"], mods["installation"]]):
        return [], None

    draw = []
    color = "black"  # frame/icon color
    stroke_width = style.get("stroke_width", 4)
    gbbox = {"x1": 100, "y1": 100, "x2": 100, "y2": 100}
    hq_staff_length = style.get("hq_staff_length") or 100  # JS default is 100

    bx1, by1, bx2, by2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
    bw = bx2 - bx1

    # ── Headquarters ──
    if mods["headquarters"] and hq_staff_length > 0:
        dim_aff = metadata.get("dimension", "") + metadata.get("affiliation", "")
        y = 100
        if dim_aff in ("AirFriend", "AirNeutral", "GroundFriend",
                        "GroundNeutral", "SeaNeutral", "SubsurfaceNeutral"):
            y = by2
        geom = {
            "type": "path",
            "d": f"M{_n(bx1)},{_n(y)} L{_n(bx1)},{_n(by2 + hq_staff_length)}",
            "fill": False, "stroke": color, "strokewidth": stroke_width,
        }
        draw.append(geom)
        gbbox["y2"] = by2 + hq_staff_length

    # ── Task Force ──
    if mods["taskForce"]:
        width_map = {"Corps/MEF": 110, "Army": 145,
                     "Army Group/front": 180, "Region/Theater": 215}
        w = width_map.get(mods["echelon"], 90)
        geom = {
            "type": "path",
            "d": (f"M{_n(100 - w/2)},{_n(by1)} L{_n(100 - w/2)},{_n(by1 - 40)} "
                  f"{_n(100 + w/2)},{_n(by1 - 40)} {_n(100 + w/2)},{_n(by1)}"),
            "fill": False, "stroke": color, "strokewidth": stroke_width,
        }
        draw.append(geom)
        gbbox["x1"] = min(gbbox["x1"], bx1, 100 - w/2)
        gbbox["x2"] = max(gbbox["x2"], bx2, 100 + w/2)
        gbbox["y1"] = min(gbbox["y1"], by1 - 40)

    # ── Installation ──
    if mods["installation"]:
        dim_aff = metadata.get("dimension", "") + metadata.get("affiliation", "")
        gap = 0
        if dim_aff in ("AirHostile", "GroundHostile", "SeaHostile"):
            gap = 14
        elif dim_aff in ("AirUnknown", "GroundUnknown", "SeaUnknown",
                         "AirFriend", "SeaFriend"):
            gap = 2
        geom = {
            "type": "path",
            "fill": color,
            "d": (f"M85,{_n(by1 + gap - stroke_width/2)} "
                  f"85,{_n(by1 - 10)} 115,{_n(by1 - 10)} "
                  f"115,{_n(by1 + gap - stroke_width/2)} "
                  f"100,{_n(by1 - stroke_width)} Z"),
            "stroke": color, "strokewidth": stroke_width,
        }
        draw.append(geom)
        gbbox["y1"] = min(gbbox["y1"], by1 - 10)

    # ── Feint/Dummy ──
    if mods["feintDummy"]:
        top = by1 - bw / 2
        geom = {
            "type": "path",
            "strokedasharray": "8,8",
            "d": (f"M100,{_n(top)} L{_n(bx1)},{_n(by1)} "
                  f"M100,{_n(top)} L{_n(bx2)},{_n(by1)}"),
            "fill": False, "stroke": color, "strokewidth": stroke_width,
        }
        draw.append(geom)
        gbbox["y1"] = min(gbbox["y1"], top)

    # ── Echelon ──
    inst_pad = 15 if mods["installation"] else 0
    if mods["echelon"]:
        ec_draw, ec_bbox = _echelon_geometry(
            mods["echelon"], by1, bx1, bx2, color, inst_pad
        )
        if ec_draw:
            draw.append({
                "type": "translate", "x": 0, "y": -inst_pad,
                "draw": ec_draw,
                "fill": False, "stroke": color, "strokewidth": stroke_width,
            })
            if ec_bbox:
                for k in ec_bbox:
                    if k in ("x1", "y1"):
                        gbbox[k] = min(gbbox[k], ec_bbox[k])
                    else:
                        gbbox[k] = max(gbbox[k], ec_bbox[k])

    # ── Mobility ──
    if mods["mobility"]:
        # Adjust bbox.y2 for neutral affiliation
        mob_y2 = by2
        if metadata.get("affiliation") == "Neutral":
            mob = mods["mobility"]
            if mob in ("Towed", "Short towed array", "Long towed Array"):
                mob_y2 += 8
            elif mob in ("Over snow (prime mover)", "Sled"):
                mob_y2 += 18
            elif mob == "Barge":
                mob_y2 += 5

        mob_draw, mob_bbox = _mobility_geometry(
            mods["mobility"], mob_y2, bx1, bx2, color
        )
        if mob_draw:
            draw.append({
                "type": "translate", "x": 0, "y": mob_y2,
                "draw": mob_draw,
                "fill": False, "stroke": color, "strokewidth": stroke_width,
            })
            if mob_bbox:
                for k in mob_bbox:
                    if k in ("x1", "y1"):
                        gbbox[k] = min(gbbox[k], mob_bbox[k])
                    else:
                        gbbox[k] = max(gbbox[k], mob_bbox[k])

    if not draw:
        return [], None

    return draw, gbbox


def _echelon_geometry(echelon: str, by1: float, bx1: float, bx2: float,
                      color: str, inst_pad: float) -> tuple:
    """Generate draw instructions for echelon indicator."""
    y = by1  # top of frame

    defs = {
        "Team/Crew": {
            "g": [
                {"type": "circle", "cx": 100, "cy": y - 20, "r": 15},
                {"type": "path", "d": f"M80,{y - 10}L120,{y - 30}"},
            ],
            "bbox": {"y1": y - 40 - inst_pad},
        },
        "Squad": {
            "g": [{"type": "circle", "fill": color, "cx": 100, "cy": y - 20, "r": 7.5}],
            "bbox": {"y1": y - 27.5 - inst_pad},
        },
        "Section": {
            "g": [
                {"type": "circle", "fill": color, "cx": 115, "cy": y - 20, "r": 7.5},
                {"type": "circle", "fill": color, "cx": 85, "cy": y - 20, "r": 7.5},
            ],
            "bbox": {"y1": y - 27.5 - inst_pad},
        },
        "Platoon/detachment": {
            "g": [
                {"type": "circle", "fill": color, "cx": 100, "cy": y - 20, "r": 7.5},
                {"type": "circle", "fill": color, "cx": 70, "cy": y - 20, "r": 7.5},
                {"type": "circle", "fill": color, "cx": 130, "cy": y - 20, "r": 7.5},
            ],
            "bbox": {"y1": y - 27.5 - inst_pad},
        },
        "Company/battery/troop": {
            "g": [{"type": "path", "d": f"M100,{y - 10}L100,{y - 35}"}],
            "bbox": {"y1": y - 40 - inst_pad},
        },
        "Battalion/squadron": {
            "g": [
                {"type": "path", "d": f"M90,{y - 10}L90,{y - 35}"},
                {"type": "path", "d": f"M110,{y - 10}L110,{y - 35}"},
            ],
            "bbox": {"y1": y - 40 - inst_pad},
        },
        "Regiment/group": {
            "g": [
                {"type": "path", "d": f"M100,{y - 10}L100,{y - 35}"},
                {"type": "path", "d": f"M120,{y - 10}L120,{y - 35}"},
                {"type": "path", "d": f"M80,{y - 10}L80,{y - 35}"},
            ],
            "bbox": {"y1": y - 40 - inst_pad},
        },
        "Brigade": {
            "g": [{"type": "path", "d": f"M87.5,{y - 10} l25,-25 m0,25 l-25,-25"}],
            "bbox": {"y1": y - 40 - inst_pad},
        },
        "Division": {
            "g": [{"type": "path",
                   "d": f"M70,{y - 10} l25,-25 m0,25 l-25,-25   M105,{y - 10} l25,-25 m0,25 l-25,-25"}],
            "bbox": {"y1": y - 40 - inst_pad, "x1": 70, "x2": 130},
        },
        "Corps/MEF": {
            "g": [{"type": "path",
                   "d": (f"M52.5,{y - 10} l25,-25 m0,25 l-25,-25    "
                         f"M87.5,{y - 10} l25,-25 m0,25 l-25,-25    "
                         f"M122.5,{y - 10} l25,-25 m0,25 l-25,-25")}],
            "bbox": {"y1": y - 40 - inst_pad, "x1": 52.5, "x2": 147.5},
        },
        "Army": {
            "g": [{"type": "path",
                   "d": (f"M35,{y - 10} l25,-25 m0,25 l-25,-25   "
                         f"M70,{y - 10} l25,-25 m0,25 l-25,-25   "
                         f"M105,{y - 10} l25,-25 m0,25 l-25,-25    "
                         f"M140,{y - 10} l25,-25 m0,25 l-25,-25")}],
            "bbox": {"y1": y - 40 - inst_pad, "x1": 35, "x2": 165},
        },
        "Army Group/front": {
            "g": [{"type": "path",
                   "d": (f"M17.5,{y - 10} l25,-25 m0,25 l-25,-25    "
                         f"M52.5,{y - 10} l25,-25 m0,25 l-25,-25    "
                         f"M87.5,{y - 10} l25,-25 m0,25 l-25,-25    "
                         f"M122.5,{y - 10} l25,-25 m0,25 l-25,-25       "
                         f"M157.5,{y - 10} l25,-25 m0,25 l-25,-25")}],
            "bbox": {"y1": y - 40 - inst_pad, "x1": 17.5, "x2": 182.5},
        },
        "Region/Theater": {
            "g": [{"type": "path",
                   "d": (f"M0,{y - 10} l25,-25 m0,25 l-25,-25   "
                         f"M35,{y - 10} l25,-25 m0,25 l-25,-25   "
                         f"M70,{y - 10} l25,-25 m0,25 l-25,-25   "
                         f"M105,{y - 10} l25,-25 m0,25 l-25,-25    "
                         f"M140,{y - 10} l25,-25 m0,25 l-25,-25     "
                         f"M175,{y - 10} l25,-25 m0,25 l-25,-25")}],
            "bbox": {"y1": y - 40 - inst_pad, "x1": 0, "x2": 200},
        },
        "Command": {
            "g": [{"type": "path",
                   "d": (f"M70,{y - 22.5} l25,0 m-12.5,12.5 l0,-25   "
                         f"M105,{y - 22.5} l25,0 m-12.5,12.5 l0,-25")}],
            "bbox": {"y1": y - 40 - inst_pad, "x1": 70, "x2": 130},
        },
    }

    if echelon not in defs:
        return [], None
    return defs[echelon]["g"], defs[echelon]["bbox"]


def _mobility_geometry(mobility: str, by2: float, bx1: float, bx2: float,
                       color: str) -> tuple:
    """Generate draw instructions for mobility indicator."""
    defs = {
        "Wheeled limited cross country": {
            "g": [
                {"type": "path", "d": "M 53,1 l 94,0"},
                {"type": "circle", "cx": 58, "cy": 8, "r": 8},
                {"type": "circle", "cx": 142, "cy": 8, "r": 8},
            ],
            "bbox": {"y2": by2 + 16},
        },
        "Wheeled cross country": {
            "g": [
                {"type": "path", "d": "M 53,1 l 94,0"},
                {"type": "circle", "cx": 58, "cy": 8, "r": 8},
                {"type": "circle", "cx": 142, "cy": 8, "r": 8},
                {"type": "circle", "cx": 100, "cy": 8, "r": 8},
            ],
            "bbox": {"y2": by2 + 16},
        },
        "Tracked": {
            "g": [{"type": "path", "d": "M 53,1 l 100,0 c15,0 15,15 0,15 l -100,0 c-15,0 -15,-15 0,-15"}],
            "bbox": {"y2": by2 + 18, "x1": 42, "x2": 168},
        },
        "Wheeled and tracked combination": {
            "g": [
                {"type": "circle", "cx": 58, "cy": 8, "r": 8},
                {"type": "path", "d": "M 83,1 l 70,0 c15,0 15,15 0,15 l -70,0 c-15,0 -15,-15 0,-15"},
            ],
            "bbox": {"y2": by2 + 16, "x2": 168},
        },
        "Towed": {
            "g": [
                {"type": "path", "d": "M 63,1 l 74,0"},
                {"type": "circle", "cx": 58, "cy": 3, "r": 8},
                {"type": "circle", "cx": 142, "cy": 3, "r": 8},
            ],
            "bbox": {"y2": by2 + 10},
        },
        "Rail": {
            "g": [
                {"type": "path", "d": "M 53,1 l 96,0"},
                {"type": "circle", "cx": 58, "cy": 8, "r": 8},
                {"type": "circle", "cx": 73, "cy": 8, "r": 8},
                {"type": "circle", "cx": 127, "cy": 8, "r": 8},
                {"type": "circle", "cx": 142, "cy": 8, "r": 8},
            ],
            "bbox": {"y2": by2 + 16},
        },
        "Over snow (prime mover)": {
            "g": [{"type": "path", "d": "M 50,-9 l10,10 90,0"}],
            "bbox": {"y2": by2 + 9},
        },
        "Sled": {
            "g": [{"type": "path", "d": "M 145,-12  c15,0 15,15 0,15 l -90,0 c-15,0 -15,-15 0,-15"}],
            "bbox": {"y2": by2 + 15, "x1": 42, "x2": 168},
        },
        "Pack animals": {
            "g": [{"type": "path", "d": "M 80,20 l 10,-20 10,20 10,-20 10,20"}],
            "bbox": {"y2": by2 + 20},
        },
        "Barge": {
            "g": [{"type": "path", "d": "M 50,1 l 100,0 c0,10 -100,10 -100,0"}],
            "bbox": {"y2": by2 + 10},
        },
        "Amphibious": {
            "g": [{"type": "path",
                   "d": ("M 65,10 c 0,-10 10,-10 10,0 0,10 10,10 10,0"
                         "\t0,-10 10,-10 10,0 0,10 10,10 10,0"
                         "\t0,-10 10,-10 10,0 0,10 10,10 10,0"
                         "\t0,-10 10,-10 10,0")}],
            "bbox": {"y2": by2 + 20},
        },
        "Short towed array": {
            "g": [{"type": "path", "fill": color,
                   "d": ("M 50,5 l 100,0 M50,0 l10,0 0,10 -10,0 z "
                         "M150,0 l-10,0 0,10 10,0 z M100,0 l5,5 -5,5 -5,-5 z")}],
            "bbox": {"y2": by2 + 10},
        },
        "Long towed Array": {
            "g": [{"type": "path", "fill": color,
                   "d": ("M 50,5 l 100,0 M50,0 l10,0 0,10 -10,0 z "
                         "M150,0 l-10,0 0,10 10,0 z M105,0 l-10,0 0,10 10,0 z "
                         "M75,0 l5,5 -5,5 -5,-5 z  M125,0 l5,5 -5,5 -5,-5 z")}],
            "bbox": {"y2": by2 + 10},
        },
    }

    if mobility not in defs:
        return [], None
    return defs[mobility]["g"], defs[mobility]["bbox"]

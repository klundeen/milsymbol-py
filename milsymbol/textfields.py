"""Text field placement for milsymbol symbols.

Ports textfields.js and string-width.js from the JS library.
Text fields (quantity, type, designation, etc.) are placed around the
symbol frame in positions L1-L5 (left) and R1-R5 (right), with layout
varying by dimension (Ground, Air, Sea, Subsurface).
"""

# Character width table for Arial at font-size 30 (from string-width.js)
_CHAR_WIDTHS = {
    "0": 19,
    "1": 19,
    "2": 19,
    "3": 19,
    "4": 19,
    "5": 19,
    "6": 19,
    "7": 19,
    "8": 19,
    "9": 19,
    " ": 10,
    "!": 10,
    '"': 12,
    "#": 19,
    "$": 19,
    "%": 30,
    "&": 23,
    "'": 7,
    "(": 11,
    ")": 11,
    "*": 13,
    "+": 20,
    ",": 10,
    "-": 11,
    ".": 10,
    "/": 10,
    ":": 10,
    ";": 10,
    "<": 20,
    "=": 20,
    ">": 20,
    "?": 19,
    "@": 34,
    "{": 12,
    "|": 9,
    "}": 12,
    "~": 20,
    "[": 10,
    "]": 10,
    "^": 16,
    "_": 19,
    "`": 11,
    "A": 23,
    "B": 23,
    "C": 24,
    "D": 24,
    "E": 23,
    "F": 21,
    "G": 26,
    "H": 24,
    "I": 10,
    "J": 17,
    "K": 23,
    "L": 19,
    "M": 28,
    "N": 24,
    "O": 26,
    "P": 23,
    "Q": 26,
    "R": 24,
    "S": 23,
    "T": 21,
    "U": 24,
    "V": 23,
    "W": 32,
    "X": 23,
    "Y": 23,
    "Z": 21,
    "a": 19,
    "b": 19,
    "c": 17,
    "d": 19,
    "e": 19,
    "f": 10,
    "g": 19,
    "h": 19,
    "i": 8,
    "j": 8,
    "k": 17,
    "l": 8,
    "m": 28,
    "n": 19,
    "o": 19,
    "p": 19,
    "q": 19,
    "r": 11,
    "s": 17,
    "t": 10,
    "u": 19,
    "v": 17,
    "w": 24,
    "x": 17,
    "y": 17,
    "z": 17,
}


def str_width(s: str, font_size: float, space_text_icon: float) -> float:
    """Calculate pixel width of a string at a given font size."""
    if not s:
        return 0
    w = sum((font_size / 30) * _CHAR_WIDTHS.get(ch, 28.5) for ch in s)
    w += space_text_icon
    return w


def compute_text_fields(options: dict, metadata: dict, bbox: dict, style: dict) -> tuple:
    """Compute text field draw instructions and expanded bounding box.

    Args:
        options: Symbol options (quantity, type, uniqueDesignation, etc.)
        metadata: Parsed SIDC metadata (affiliation, dimension, etc.)
        bbox: Frame bounding box {x1, y1, x2, y2}
        style: Style settings (infoSize, fontfamily, etc.)

    Returns:
        (draw_instructions, text_bbox) where draw_instructions is a list
        of draw instruction dicts and text_bbox is {x1, y1, x2, y2} or None.
    """
    font_color = style.get("info_color") or "black"
    font_family = style.get("fontfamily", "Arial")
    font_size = style.get("info_size", 40)
    space = 20  # distance between icon and labels

    # Check if any text fields are set
    text_field_names = [
        "quantity",
        "reinforcedReduced",
        "staffComments",
        "additionalInformation",
        "evaluationRating",
        "combatEffectiveness",
        "signatureEquipment",
        "higherFormation",
        "hostile",
        "iffSif",
        "sigint",
        "uniqueDesignation",
        "type",
        "dtg",
        "altitudeDepth",
        "location",
        "speed",
        "specialHeadquarters",
        "platformType",
        "equipmentTeardownTime",
        "commonIdentifier",
        "auxiliaryEquipmentIndicator",
        "headquartersElement",
        "installationComposition",
        "guardedUnit",
        "specialDesignator",
    ]

    has_text = any(options.get(f) for f in text_field_names)
    if not has_text:
        return [], None

    draw = []
    gbbox = {"x1": bbox["x1"], "y1": bbox["y1"], "x2": bbox["x2"], "y2": bbox["y2"]}

    # Quantity above symbol (except dismounted)
    dismounted = metadata.get("dismounted", False)
    if options.get("quantity") and not dismounted:
        draw.append(
            {
                "type": "text",
                "text": options["quantity"],
                "x": 100,
                "y": bbox["y1"] - 10,
                "textanchor": "middle",
                "fontsize": font_size,
                "fontfamily": font_family,
                "fill": font_color,
                "stroke": False,
            }
        )
        gbbox["y1"] = bbox["y1"] - 10 - font_size

    # Special headquarters text in center
    if options.get("specialHeadquarters"):
        # Render centered text
        _sz = 45
        sh = options["specialHeadquarters"]
        if len(sh) == 3:
            _sz = 39
        elif len(sh) >= 4:
            _sz = 33
        draw.append(
            {
                "type": "text",
                "text": sh,
                "stroke": False,
                "textanchor": "middle",
                "alignmentBaseline": "middle",
                "x": 100,
                "y": 103,
                "fontsize": _sz,
                "fontweight": "bold",
                "fontfamily": font_family,
                "fill": font_color,
            }
        )

    # Headquarters element below symbol
    if options.get("headquartersElement"):
        draw.append(
            {
                "type": "text",
                "text": options["headquartersElement"],
                "x": 100,
                "y": bbox["y2"] + 35,
                "textanchor": "middle",
                "fontsize": 35,
                "fontfamily": font_family,
                "fontweight": "bold",
                "fill": font_color,
                "stroke": False,
            }
        )
        gbbox["y2"] = bbox["y2"] + 35

    # Build L1-L5, R1-R5 field mapping based on dimension
    g = {
        "L1": "",
        "L2": "",
        "L3": "",
        "L4": "",
        "L5": "",
        "R1": "",
        "R2": "",
        "R3": "",
        "R4": "",
        "R5": "",
    }

    sidc = options.get("sidc", "")
    is_number = sidc.isdigit() if sidc else False
    base_dim = metadata.get("baseDimension", metadata.get("dimension", "Ground"))
    is_unit = metadata.get("unit", False)

    if is_number and base_dim == "Air":
        _map_air(g, options)
    elif is_number and base_dim == "Sea":
        _map_sea(g, options)
    elif is_number and base_dim == "Subsurface":
        _map_subsurface(g, options)
    elif dismounted:
        # Dismounted individual quantity goes below
        if options.get("quantity"):
            draw.append(
                {
                    "type": "text",
                    "text": options["quantity"],
                    "x": 100,
                    "y": bbox["y2"] + font_size,
                    "textanchor": "middle",
                    "fontsize": font_size,
                    "fontfamily": font_family,
                    "fill": font_color,
                    "stroke": False,
                }
            )
            gbbox["y2"] = bbox["y2"] + font_size
        _map_dismounted(g, options)
    else:
        # Ground / letter-based SIDCs
        _map_ground(g, options, is_number, is_unit, metadata)

    # Compute bbox expansion from text widths
    stack = options.get("stack", 0) * 15 if options.get("stack") else 0
    flag = 0  # country flag offset (not implemented yet)

    gbbox["x1"] = bbox["x1"] - max(
        _centered_overflow(options.get("specialHeadquarters", ""), font_size, space, bbox),
        _centered_overflow(
            options.get("quantity", "") if not dismounted else "",
            font_size,
            space,
            bbox,
        ),
        str_width(g["L1"], font_size, space),
        str_width(g["L2"], font_size, space),
        str_width(g["L3"], font_size, space),
        str_width(g["L4"], font_size, space),
        str_width(g["L5"], font_size, space),
    )

    gbbox["x2"] = bbox["x2"] + max(
        _centered_overflow(options.get("specialHeadquarters", ""), font_size, space, bbox),
        _centered_overflow(
            options.get("quantity", "") if not dismounted else "",
            font_size,
            space,
            bbox,
        ),
        str_width(g["R1"], font_size, space + stack),
        str_width(g["R2"], font_size, space + stack),
        str_width(g["R3"], font_size, space + stack),
        str_width(g["R4"], font_size, space + stack + flag * 1.5),
        str_width(g["R5"], font_size, space + stack + flag * 1.5),
    )

    # Vertical expansion
    if g["L1"] or g["R1"]:
        gbbox["y1"] = min(gbbox["y1"], 100 - 2.5 * font_size)
    if g["L2"] or g["R2"]:
        gbbox["y1"] = min(gbbox["y1"], 100 - 1.5 * font_size)
    if g["L4"] or g["R4"]:
        gbbox["y2"] = max(gbbox["y2"], 100 + 1.7 * font_size)
    if g["L5"] or g["R5"]:
        gbbox["y2"] = max(gbbox["y2"], 100 + 2.7 * font_size)

    # Render left fields L1-L5
    for i, key in enumerate(["L1", "L2", "L3", "L4", "L5"]):
        if g[key]:
            draw.append(
                {
                    "type": "text",
                    "text": g[key],
                    "x": bbox["x1"] - space,
                    "y": 100 + (i - 2) * font_size + 0.5 * font_size,
                    "textanchor": "end",
                    "fontsize": font_size,
                    "fontfamily": font_family,
                    "fill": font_color,
                    "stroke": False,
                }
            )

    # Render right fields R1-R5
    for i, key in enumerate(["R1", "R2", "R3", "R4", "R5"]):
        if g[key]:
            x_offset = space + stack
            if i >= 3:  # R4, R5 get flag offset
                x_offset += flag
            draw.append(
                {
                    "type": "text",
                    "text": g[key],
                    "x": bbox["x2"] + x_offset,
                    "y": 100 + (i - 2) * font_size + 0.5 * font_size,
                    "textanchor": "start",
                    "fontsize": font_size,
                    "fontfamily": font_family,
                    "fill": font_color,
                    "stroke": False,
                }
            )

    return draw, gbbox


def _centered_overflow(text: str, font_size: float, space: float, bbox: dict) -> float:
    """How much a centered text overflows beyond the frame on each side."""
    if not text:
        return 0
    bbox_width = bbox["x2"] - bbox["x1"]
    return max(0, (str_width(text, font_size, space) - bbox_width) / 2)


def _join_fields(*fields) -> str:
    """Join non-empty fields with /."""
    return "/".join(f for f in fields if f)


def _map_ground(g: dict, opts: dict, is_number: bool, is_unit: bool, metadata: dict):
    """Map text fields to L/R positions for Ground dimension."""
    g["L1"] = opts.get("dtg", "")
    g["L2"] = _join_fields(opts.get("altitudeDepth", ""), opts.get("location", ""))
    g["L4"] = opts.get("uniqueDesignation", "")
    g["L5"] = opts.get("speed", "")
    g["R2"] = opts.get("staffComments", "")
    g["R4"] = opts.get("higherFormation", "")

    # R5: evaluation/combat/signature/hostile/iff
    g["R5"] = _join_fields(
        opts.get("evaluationRating", ""),
        opts.get("combatEffectiveness", ""),
        opts.get("signatureEquipment", ""),
        opts.get("hostile", ""),
        opts.get("iffSif", ""),
    )

    if not is_number or is_unit:
        # Unit layout
        g["L3"] = _join_fields(
            opts.get("type", ""),
            opts.get("platformType", ""),
            opts.get("equipmentTeardownTime", ""),
        )
        g["R1"] = opts.get("reinforcedReduced", "")
        if metadata.get("activity"):
            g["R1"] = opts.get("country", "")
        g["R3"] = _join_fields(
            opts.get("additionalInformation", ""), opts.get("commonIdentifier", "")
        )
    else:
        # Equipment/installation layout
        g["L3"] = _join_fields(
            opts.get("type", ""),
            opts.get("platformType", ""),
            opts.get("commonIdentifier", ""),
            opts.get("installationComposition", ""),
        )
        g["R1"] = opts.get("country", "")
        g["R3"] = _join_fields(
            opts.get("additionalInformation", ""), opts.get("equipmentTeardownTime", "")
        )


def _map_air(g: dict, opts: dict):
    """Map text fields to L/R positions for Air dimension."""
    g["R1"] = opts.get("uniqueDesignation", "")
    g["R2"] = opts.get("iffSif", "")
    g["R3"] = opts.get("type", "")
    g["R4"] = _join_fields(opts.get("speed", ""), opts.get("altitudeDepth", ""))
    g["R5"] = _join_fields(opts.get("staffComments", ""), opts.get("additionalInformation", ""))


def _map_sea(g: dict, opts: dict):
    """Map text fields to L/R positions for Sea dimension."""
    g["L1"] = _join_fields(opts.get("guardedUnit", ""), opts.get("specialDesignator", ""))
    g["R1"] = opts.get("uniqueDesignation", "")
    g["R2"] = opts.get("type", "")
    g["R3"] = opts.get("iffSif", "")
    g["R4"] = _join_fields(opts.get("staffComments", ""), opts.get("additionalInformation", ""))
    g["R5"] = _join_fields(opts.get("location", ""), opts.get("speed", ""))


def _map_subsurface(g: dict, opts: dict):
    """Map text fields to L/R positions for Subsurface dimension."""
    g["L1"] = opts.get("specialDesignator", "")
    g["R1"] = opts.get("uniqueDesignation", "")
    g["R2"] = opts.get("type", "")
    g["R3"] = opts.get("altitudeDepth", "")
    g["R4"] = opts.get("staffComments", "")
    g["R5"] = opts.get("additionalInformation", "")


def _map_dismounted(g: dict, opts: dict):
    """Map text fields for dismounted individual."""
    g["L1"] = opts.get("dtg", "")
    g["L2"] = _join_fields(opts.get("altitudeDepth", ""), opts.get("location", ""))
    g["L3"] = _join_fields(
        opts.get("type", ""),
        opts.get("platformType", ""),
        opts.get("commonIdentifier", ""),
    )
    g["L4"] = opts.get("uniqueDesignation", "")
    g["L5"] = opts.get("speed", "")
    g["R1"] = opts.get("country", "")
    g["R2"] = opts.get("staffComments", "")
    g["R3"] = _join_fields(opts.get("additionalInformation", ""))
    g["R4"] = opts.get("higherFormation", "")
    g["R5"] = _join_fields(
        opts.get("evaluationRating", ""),
        opts.get("combatEffectiveness", ""),
        opts.get("signatureEquipment", ""),
        opts.get("hostile", ""),
        opts.get("iffSif", ""),
    )

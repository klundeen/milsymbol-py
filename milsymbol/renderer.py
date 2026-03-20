"""SVG renderer for milsymbol draw instructions.

Converts the JSON draw instruction format used by milsymbol into SVG markup.
Draw instructions are objects with a 'type' field (path, circle, text, translate,
rotate, scale, clip, svg) and associated properties.
"""

import re

_ATTR_ESCAPE = str.maketrans({"&": "&amp;", '"': "&quot;", "'": "&apos;", "<": "&lt;", ">": "&gt;"})
_TEXT_ESCAPE = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})
_RAW_SVG_BLOCKLIST = re.compile(
    r"<\s*(script|foreignObject|iframe|object|embed)[\s>]|on[a-z]+\s*=|javascript:",
    re.I,
)
_DASHARRAY_RE = re.compile(r"^[0-9.,\s-]+$")
_FONT_FAMILY_RE = re.compile(r'^[a-zA-Z0-9 ,"\'_:-]+$')
_FONT_WEIGHT_RE = re.compile(r"^(normal|bold|bolder|lighter|[1-9]00)$")
_LINECAP_VALUES = {"butt", "round", "square"}
_TEXT_ANCHOR_VALUES = {"start", "middle", "end"}
_BASELINE_VALUES = {
    "auto",
    "text-bottom",
    "alphabetic",
    "ideographic",
    "middle",
    "central",
    "mathematical",
    "hanging",
    "text-top",
    "text-before-edge",
    "text-after-edge",
}


def _escape_attr(value: str) -> str:
    return (
        str(value).translate(_ATTR_ESCAPE).replace("\r", " ").replace("\n", " ").replace("\t", " ")
    )


def _escape_text(value: str) -> str:
    return str(value).translate(_TEXT_ESCAPE)


def _attr(name: str, value) -> str:
    if value is None:
        return ""
    # Format numbers: strip trailing .0 for integers
    if isinstance(value, float):
        value = _fmt_num(value)
    elif isinstance(value, int):
        value = str(value)
    return f' {name}="{_escape_attr(str(value))}"'


def _safe_number(value, fallback=0) -> float:
    try:
        n = float(value)
        if n != n:  # NaN
            return fallback
        return n
    except (TypeError, ValueError):
        return fallback


def _sanitize_dash_array(value) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return s if _DASHARRAY_RE.match(s) else ""


def _sanitize_linecap(value) -> str:
    s = str(value or "").lower()
    return s if s in _LINECAP_VALUES else ""


def _sanitize_font_weight(value) -> str:
    s = str(value or "").lower()
    return s if _FONT_WEIGHT_RE.match(s) else ""


def _sanitize_text_anchor(value) -> str:
    s = str(value or "").lower()
    return s if s in _TEXT_ANCHOR_VALUES else ""


def _sanitize_baseline(value) -> str:
    s = str(value or "").lower()
    return s if s in _BASELINE_VALUES else ""


def _sanitize_font_family(value, fallback="sans-serif") -> str:
    if value is None:
        return fallback
    s = str(value).strip()
    return s if s and _FONT_FAMILY_RE.match(s) else fallback


def _sanitize_color(value, fallback="none") -> str:
    if value is None:
        return fallback
    s = str(value).strip()
    if not s:
        return fallback
    if (
        re.search(r"url\s*\(", s, re.I)
        or re.search(r"javascript:", s, re.I)
        or s.lower().startswith("data:")
    ):
        return fallback
    return s


def _sanitize_svg_fragment(value) -> str:
    if value is None:
        return ""
    s = str(value)
    return "" if _RAW_SVG_BLOCKLIST.search(s) else s


def _sanitize_id(value, fallback="") -> str:
    if value is None:
        return fallback
    s = str(value).strip()
    if not s:
        return fallback
    s = re.sub(r"[^A-Za-z0-9._:-]", "_", s)
    if not re.match(r"^[A-Za-z_]", s):
        s = f"id_{s}"
    return s or fallback


def render_instructions(instructions, stroke_width: float = 4, style_fill: bool = False) -> str:
    """Render a list of draw instructions to SVG XML fragment."""
    clip_counter = [0]

    def process(instr_list) -> str:
        if not isinstance(instr_list, (list, tuple)):
            if isinstance(instr_list, dict):
                instr_list = [instr_list]
            else:
                return ""

        out = []
        for item in instr_list:
            if isinstance(item, (list, tuple)):
                if item:
                    out.append(process(item))
            elif isinstance(item, dict):
                svg = ""
                itype = item.get("type")

                if itype == "svg":
                    svg += _sanitize_svg_fragment(item.get("svg"))
                else:
                    # Handle inline clipPath
                    inline_clip_id = ""
                    if "clipPath" in item and itype != "clip":
                        inline_clip_id = f"clip-inline-{clip_counter[0]}"
                        clip_counter[0] += 1
                        svg += f"<clipPath{_attr('id', inline_clip_id)}>"
                        clip_d = item["clipPath"]
                        svg += f"<path{_attr('d', clip_d)}{_attr('clip-rule', 'nonzero')} />"
                        svg += "</clipPath>"

                    if itype == "path":
                        svg += f"<path{_attr('d', item.get('d'))}"
                        if inline_clip_id:
                            svg += _attr("clip-path", f"url(#{inline_clip_id})")
                    elif itype == "circle":
                        svg += (
                            f"<circle"
                            f"{_attr('cx', _safe_number(item.get('cx')))}"
                            f"{_attr('cy', _safe_number(item.get('cy')))}"
                            f"{_attr('r', _safe_number(item.get('r')))}"
                        )
                        if inline_clip_id:
                            svg += _attr("clip-path", f"url(#{inline_clip_id})")
                    elif itype == "text":
                        ta = _sanitize_text_anchor(item.get("textanchor")) or "start"
                        ff = _sanitize_font_family(item.get("fontfamily"))
                        svg += (
                            f"<text"
                            f"{_attr('x', _safe_number(item.get('x')))}"
                            f"{_attr('y', _safe_number(item.get('y')))}"
                            f"{_attr('text-anchor', ta)}"
                            f"{_attr('font-size', _safe_number(item.get('fontsize'), 12))}"
                            f"{_attr('font-family', ff)}"
                        )
                        fw = _sanitize_font_weight(item.get("fontweight"))
                        if fw:
                            svg += _attr("font-weight", fw)
                        bl = _sanitize_baseline(item.get("alignmentBaseline"))
                        if bl:
                            svg += _attr("dominant-baseline", bl)
                        if inline_clip_id:
                            svg += _attr("clip-path", f"url(#{inline_clip_id})")
                    elif itype == "translate":
                        tx = _fmt_num(_safe_number(item.get("x")))
                        ty = _fmt_num(_safe_number(item.get("y")))
                        svg += f"<g{_attr('transform', f'translate({tx},{ty})')}"
                        if inline_clip_id:
                            svg += _attr("clip-path", f"url(#{inline_clip_id})")
                    elif itype == "rotate":
                        rd = _fmt_num(_safe_number(item.get("degree")))
                        rx = _fmt_num(_safe_number(item.get("x")))
                        ry = _fmt_num(_safe_number(item.get("y")))
                        svg += f"<g{_attr('transform', f'rotate({rd},{rx},{ry})')}"
                        if inline_clip_id:
                            svg += _attr("clip-path", f"url(#{inline_clip_id})")
                    elif itype == "scale":
                        sf = _fmt_num(_safe_number(item.get("factor"), 1))
                        svg += f"<g{_attr('transform', f'scale({sf})')}"
                        if inline_clip_id:
                            svg += _attr("clip-path", f"url(#{inline_clip_id})")
                    elif itype == "clip":
                        resolved_id = (
                            _sanitize_id(item.get("clipId")) or f"clip-custom-{clip_counter[0]}"
                        )
                        clip_counter[0] += 1
                        svg += f"<clipPath{_attr('id', resolved_id)}>"
                        svg += f"<path{_attr('d', item.get('d'))}{_attr('clip-rule', 'nonzero')} />"
                        svg += "</clipPath>"
                        svg += f"<g{_attr('clip-path', f'url(#{resolved_id})')}"
                    else:
                        continue

                    # Stroke attributes
                    if "stroke" in item:
                        nss = _safe_number(item.get("non_scaling_stroke", 1))
                        sw_setting = (
                            _safe_number(item["strokewidth"], stroke_width)
                            if "strokewidth" in item
                            else stroke_width
                        )
                        computed_sw = _safe_number(nss * sw_setting, stroke_width)
                        svg += _attr("stroke-width", computed_sw)

                        da = _sanitize_dash_array(item.get("strokedasharray"))
                        if da:
                            svg += _attr("stroke-dasharray", da)

                        lc = _sanitize_linecap(item.get("linecap"))
                        if lc:
                            svg += _attr("stroke-linecap", lc)
                            svg += _attr("stroke-linejoin", lc)

                        stroke_color = (
                            _sanitize_color(item.get("stroke"), "none")
                            if item.get("stroke")
                            else "none"
                        )
                        svg += _attr("stroke", stroke_color)

                    # Fill attributes
                    if "fill" in item:
                        fill = item["fill"]
                        if item.get("styleFill") and style_fill:
                            fill = "rgba(255,255,255,0.4)"
                        svg += _attr("fill", _sanitize_color(fill, "none") if fill else "none")

                    if "fillopacity" in item:
                        fo = max(0, min(1, _safe_number(item["fillopacity"], 1)))
                        svg += _attr("fill-opacity", fo)

                    svg += " >"

                    # Closing tags
                    if itype == "path":
                        svg += "</path>"
                    elif itype == "circle":
                        svg += "</circle>"
                    elif itype == "text":
                        svg += f"{_escape_text(item.get('text', ''))}</text>"
                    elif itype in ("translate", "rotate", "scale"):
                        svg += process(item.get("draw", []))
                        svg += "</g>"
                    elif itype == "clip":
                        svg += process(item.get("draw", []))
                        svg += "</g>"

                out.append(svg)
        return "".join(out)

    return process(instructions)


def _fmt_num(value) -> str:
    """Format a number matching JS behavior: no trailing .0 for integers."""
    n = float(value)
    if n == int(n):
        return str(int(n))
    return str(n)


def render_svg(
    draw_instructions,
    bbox: dict,
    stroke_width: float = 4,
    outline_width: float = 0,
    size: float = 100,
    style_fill: bool = False,
) -> str:
    """Render a complete SVG from draw instructions and bounding box.

    Args:
        draw_instructions: The draw instruction tree (list of dicts/lists).
        bbox: Dict with x1, y1, x2, y2 keys.
        stroke_width: Frame stroke width.
        outline_width: Outline width.
        size: Symbol size (scaling factor, 100 = 1x).

    Returns:
        Complete SVG XML string.
    """
    sw = _safe_number(stroke_width)
    ow = _safe_number(outline_width)
    x1 = _safe_number(bbox.get("x1")) - sw - ow
    y1 = _safe_number(bbox.get("y1")) - sw - ow

    base_width = (_safe_number(bbox.get("x2")) - _safe_number(bbox.get("x1"))) + sw * 2 + ow * 2
    base_height = (_safe_number(bbox.get("y2")) - _safe_number(bbox.get("y1"))) + sw * 2 + ow * 2

    width = base_width * size / 100
    height = base_height * size / 100

    viewbox = f"{_fmt_num(x1)} {_fmt_num(y1)} {_fmt_num(base_width)} {_fmt_num(base_height)}"

    body = render_instructions(draw_instructions, stroke_width=sw, style_fill=style_fill)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny"'
        f' width="{_fmt_num(width)}" height="{_fmt_num(height)}" viewBox="{viewbox}">'
        f"{body}"
        f"</svg>"
    )

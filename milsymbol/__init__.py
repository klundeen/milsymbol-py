"""milsymbol — Military Symbols in Python.

A reference implementation and test harness for porting milsymbol.js,
with a usable frozen renderer.  Generates SVG military symbols per
MIL-STD-2525 (B/C/D/E) and STANAG APP-6 (B/D/E).

Usage:
    from milsymbol import Symbol

    sym = Symbol("10031000001211000000", size=80)
    svg = sym.as_svg()
"""

from .renderer import render_svg
from .symbol import Symbol

__version__ = "0.1.0"
__all__ = ["Symbol", "render_svg"]

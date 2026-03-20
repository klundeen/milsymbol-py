"""milsymbol - Military Symbols in Python

Port of the milsymbol JavaScript library.
Phase 1: SVG rendering from pre-extracted draw instructions.
"""

from .symbol import Symbol
from .renderer import render_svg

__version__ = "0.1.0"
__all__ = ["Symbol", "render_svg"]

# milsymbol-py

[![Tests](https://github.com/klundeen/milsymbol-py/actions/workflows/tests.yml/badge.svg)](https://github.com/klundeen/milsymbol-py/actions/workflows/tests.yml)

A reference implementation and test harness for porting
[milsymbol](https://github.com/spatialillusions/milsymbol) (JavaScript)
to Python — with a usable frozen renderer as a side effect.

Generates SVG military symbols per **MIL-STD-2525** (B/C/D/E) and
**STANAG APP-6** (B/D/E).

```python
from milsymbol import Symbol

sym = Symbol("10031000001211000000", size=80)   # friendly infantry
svg = sym.as_svg()                               # → SVG string

sym = Symbol("SHG-UCI----", size=80)             # hostile infantry
svg = sym.as_svg()
```

---

## The porting problem

Milsymbol is 33,000 lines of JavaScript. A naïve port — translate the
JS to Python line by line — is what most people attempt, and it tends
to fail. The codebase looks deceptively simple: one main class, a
handful of methods, clean SVG output. But ~27,000 of those lines are
**data** — hand-tuned SVG path coordinates for hundreds of military
symbol icons, each positioned to fit precisely inside affiliation-
specific frame shapes (rectangle for friendly, diamond for hostile,
quatrefoil for unknown, etc.). The remaining ~5,000 lines of logic
compose those icon parts based on a parsed SIDC code and render them
to SVG.

An LLM (or a mid-level engineer) can translate the 5,000 lines of
composition logic reasonably well. The problem is the 27,000 lines of
icon geometry. Every path coordinate matters. A misplaced decimal in a
single `d="M 85,140 30,0 c 0,-20 -30,-20 -30,0 z"` produces a
visually broken symbol, and you can't verify correctness without
domain expertise in the military standards.

## Our approach: extraction, not translation

Instead of translating code, we treat the JS library as an **oracle**:

1. **Extract at build time.** A Node.js tool runs the original
   milsymbol library and creates every valid symbol across all
   affiliations. For each one, it captures the fully-composed draw
   instruction tree (the intermediate representation milsymbol uses
   before SVG serialization) and the bounding box. This produces
   ~109,000 symbol variants serialized as gzipped JSON (~2 MB).

2. **Look up at runtime.** When `Symbol(sidc)` is called in Python,
   it does a dictionary lookup on the SIDC to get the pre-composed
   draw instructions and bounding box. No parsing, no composition
   logic, no icon geometry — just a key lookup.

3. **Render.** A compact Python renderer (~250 lines) walks the draw
   instruction tree and emits SVG markup, matching the JS output
   character-for-character.

The result: **pixel-identical SVG output** verified by exact string
comparison against the JS reference, with a Python codebase of ~400
lines instead of 33,000.

### What Phase 1 actually is

To be direct: this is not yet a port of milsymbol. It's three things:

1. **A test oracle.** 109K pre-computed reference symbols that any
   future port — Python, Rust, Go, whatever — can verify against,
   character by character. This is the hard part that didn't exist
   before.

2. **A frozen renderer.** It works today for every symbol in
   MIL-STD-2525E / APP-6 as of milsymbol 3.0.3. If you just need
   military symbols in Python and don't need extensibility, it's a
   perfectly functional library. But it's frozen at extraction time.

3. **Scaffolding for the real port.** The project structure, FastAPI
   comparison server, visual playground, and smoke tests. When
   someone ports the actual composition logic (Phase 2), all the
   verification infrastructure is already in place.

The extracted data approach **cannot** handle:

- **Runtime extensions** — milsymbol's `addSymbolPart()` /
  `addIconParts()` API lets users register custom symbology. The
  extracted data only covers built-in symbols.
- **Novel SIDC combinations** — modifier combinations not covered
  during extraction produce no output.

This is a deliberate tradeoff, not an oversight. Phase 2 — porting
the ~5,000 lines of composition logic — is dramatically easier
because Phase 1 exists. You port one function, run the full
comparison, and know immediately what broke.

### Analogy

Think of it as the difference between porting a compiler and shipping
pre-compiled object files. We ran the JS "compiler" on every valid
input at build time, shipped the results, and wrote a Python "linker"
to assemble them into SVG. The linker is trivial; the compiler port
comes later — and when it does, we already have the full test corpus.

### A note on process

This project was built entirely through 3-hour conversation between Kevin
Lundeen (a computer science professor at Seattle University) and
Claude Opus 4.6. Kevin directed the architecture, asked the right
questions, and pressure-tested the approach — but never read the
milsymbol JS source code or the generated Python code directly.
Claude analyzed the 33,000-line codebase, devised the extraction
strategy, wrote the tooling, ported the renderer, and built the
test harness. The project is a demonstration of what's possible
when a senior engineer uses an LLM as a tool: the human provides
judgment and direction, the machine provides the throughput and
detail work. The comment that inspired this project observed that
LLMs fail at tasks like porting JS libraries to Python. We didn't
port the library — we found a way around the problem entirely.

---

## Install

```bash
pip install milsymbol          # core library (no dependencies)
pip install milsymbol[server]  # adds FastAPI comparison server
```

Or from source:

```bash
git clone https://github.com/klundeen/milsymbol-py.git
cd milsymbol-py
pip install -e ".[dev]"
pytest
```

## API

### `Symbol(sidc, **kwargs)`

| Argument | Default | Description |
|---|---|---|
| `sidc` | *(required)* | SIDC string — number (20-digit) or letter format |
| `size` | `100` | Symbol size (scaling factor; 100 = base size) |
| `stroke_width` | `4` | Frame stroke width |
| `outline_width` | `0` | Outline width around the symbol |

### Methods

| Method | Returns | Description |
|---|---|---|
| `as_svg()` | `str` | Complete SVG markup |
| `is_valid()` | `bool` | Whether the SIDC resolved to a known symbol |
| `get_anchor()` | `dict` | `{"x": float, "y": float}` — placement anchor |
| `get_size()` | `dict` | `{"width": float, "height": float}` — rendered size |
| `get_metadata()` | `dict` | Parsed SIDC fields |

### Affiliations

Number SIDCs encode affiliation at position 3:

| Code | Affiliation | Frame |
|---|---|---|
| `3` | Friend | Rectangle (blue) |
| `6` | Hostile | Diamond (red) |
| `4` | Neutral | Square (green) |
| `1` | Unknown | Quatrefoil (yellow) |

Letter SIDCs encode affiliation at position 1 (`F`/`H`/`N`/`U`/etc.).

## Playground

A browser-based comparison tool shows JS and Python output side by
side. The render areas use a parchment background so the symbols'
black text labels are visible.

```bash
# Start the Python backend
pip install milsymbol[server]
uvicorn server:app --port 8000

# Serve the playground
cd playground && python -m http.server 3000
# Open http://localhost:3000/playground.html
```

## Coverage

| Category | Count |
|---|---|
| Number SIDCs (all affiliations) | 37,828 |
| Letter SIDCs (all affiliations + echelons) | 71,388 |
| Symbol sets | 19 |
| Tests (fast) | 157 |
| Tests (full corpus, vs JS reference) | 403 |
| Corpus match rate | 109,216 / 109,216 (100%) |
| Python source lines | ~800 |
| Data (gzipped) | 2 MB |

## Can I use this in production?

Yes. The library produces **pixel-identical SVG** to the JS library
for all 109,216 symbols in the MIL-STD-2525 / STANAG APP-6 set,
verified by exact string comparison against JS-generated reference
SVGs. Every affiliation, every symbol set, every echelon.

**Caveats:**

- Frozen to milsymbol 3.0.3's built-in symbol set — no runtime
  extensions or custom icon registration.
- Text fields and modifiers are computed in Python. The core symbols
  are extracted from JS; the composition logic around them is ported.
- SVG output only (pipe through `cairosvg` for PNG if needed).

**Wheel size:** 1.8 MB, zero runtime dependencies.

## Regenerating data

If the upstream JS library updates:

```bash
git clone https://github.com/spatialillusions/milsymbol.git
cd milsymbol && npm install && npm run build && cd ..
node tools/extract_data.mjs ./milsymbol ./milsymbol-py/milsymbol/data
```

## Development

```bash
git clone https://github.com/klundeen/milsymbol-py.git
cd milsymbol-py
pip install -e ".[dev]"

pytest                                              # 143 tests
ruff check milsymbol/ tests/ server.py              # lint
ruff format --check milsymbol/ tests/ server.py     # format check
mypy milsymbol/ server.py --ignore-missing-imports  # type check
```

### CI/CD

Every push to `main` and every PR runs:
- **ruff** lint + format check
- **mypy** type checking
- **pytest** across Python 3.10, 3.11, 3.12, 3.13

Creating a GitHub Release triggers automatic publishing to PyPI via
trusted publishing.

### Publishing to PyPI

> **TODO (Kevin):** Configure trusted publishing on pypi.org:
> Project → Settings → Publishing → add GitHub publisher with
> `klundeen/milsymbol-py` and workflow `publish.yml`.

Then: create a GitHub Release tagged `v0.1.0` and the package
publishes automatically.

## Known upstream quirks

These behaviors are inherited from the JS library and reproduced
faithfully by the Python port:

- **Quantity / echelon collision.** The quantity text field is
  positioned relative to the frame bounding box, not the full symbol
  including echelon dots. At larger sizes, quantity text can overlap
  the echelon modifier.

## Roadmap

- [x] Extract test oracle (109K reference symbols)
- [x] Frozen renderer with exact SVG match
- [x] Visual comparison playground
- [x] Port text field placement (quantity, type, designation, etc.)
- [x] Port echelon / mobility / HQ / TF / feint-dummy modifiers
- [x] Comprehensive test fixture (109K symbols vs JS reference)
- [ ] Port composition logic (Phase 2 — real port)
- [ ] Extension API
- [ ] PNG rasterization (via cairosvg or similar)

## License

MIT — same as the original
[milsymbol](https://github.com/spatialillusions/milsymbol) library.

## Credits

- **[milsymbol](https://github.com/spatialillusions/milsymbol)** by
  Måns Beckman — the original JS library.
- Symbol geometry and icon data derived from MIL-STD-2525 and STANAG
  APP-6.
# milsymbol-py

Military unit symbols in Python — a port of [milsymbol](https://github.com/spatialillusions/milsymbol) (JavaScript) by Måns Beckman.

Generates SVG military symbols per **MIL-STD-2525** (B/C/D/E) and **STANAG APP-6** (B/D/E).

## Quick start

```python
from milsymbol import Symbol

sym = Symbol("10031000001211000000", size=80)   # friendly infantry (number SIDC)
svg = sym.as_svg()                               # → SVG string

sym = Symbol("SHG-UCI----", size=80)             # hostile infantry (letter SIDC)
svg = sym.as_svg()
```

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
| `sidc` | (required) | SIDC string — number (20-digit 2525D/E) or letter (2525B/C, APP6) format |
| `size` | `100` | Symbol size (scaling factor; 100 = base size) |
| `stroke_width` | `4` | Frame stroke width |
| `outline_width` | `0` | Outline width around the symbol |

### Methods

| Method | Returns | Description |
|---|---|---|
| `as_svg()` | `str` | Complete SVG markup |
| `is_valid()` | `bool` | Whether the SIDC resolved to a known symbol |
| `get_anchor()` | `dict` | `{"x": float, "y": float}` — placement anchor point |
| `get_size()` | `dict` | `{"width": float, "height": float}` — rendered dimensions |
| `get_metadata()` | `dict` | Parsed SIDC fields (affiliation, dimension, entity, etc.) |

### Affiliations

Number SIDCs encode affiliation at position 3:

| Code | Affiliation |
|---|---|
| `0` | Pending |
| `1` | Unknown |
| `2` | Assumed Friend |
| `3` | Friend |
| `4` | Neutral |
| `5` | Suspect |
| `6` | Hostile |

Letter SIDCs encode affiliation at position 1 (`F`=Friend, `H`=Hostile, `N`=Neutral, `U`=Unknown, etc.).

## Playground

A browser-based comparison tool is included for visual verification against the JS reference library.

```bash
# Terminal 1 — start the Python backend
pip install milsymbol[server]
cd milsymbol-py
uvicorn server:app --port 8000

# Terminal 2 — serve the playground
cd milsymbol-py/playground
python -m http.server 3000
# Open http://localhost:3000/playground.html
```

The playground shows JS (milsymbol.js) output on the left and Python output on the right, with a gallery of all symbols per symbol set and the full SVG source for diffing.

## How it works

### Architecture

This port takes a **data extraction** approach rather than a line-by-line code translation:

1. **Extract**: A Node.js tool (`tools/extract_data.mjs`) runs the original milsymbol JS library and captures the fully-composed draw instructions for every valid SIDC across all affiliations. These are serialized as gzipped JSON (~2 MB).

2. **Look up**: When `Symbol(sidc)` is called, it looks up the SIDC in the extracted data to get the draw instruction tree and bounding box.

3. **Render**: The `renderer.py` module walks the draw instruction tree and emits SVG markup, matching the JS output character-for-character.

This means the Python port produces **pixel-identical SVG** to the JS library for all supported symbols — verified by the smoke test suite.

### Coverage

| Category | Count |
|---|---|
| Number SIDCs (all affiliations) | 37,828 |
| Letter SIDCs (all affiliations + echelons) | 71,388 |
| Smoke tests (exact SVG match) | 12 |
| Symbol sets | 19 |

### Data files

| File | Size | Contents |
|---|---|---|
| `number-data.json.gz` | 549 KB | Draw instructions for 37,828 number-format symbols |
| `letter-data.json.gz` | 1.5 MB | Draw instructions for 71,388 letter-format symbols |
| `geometries.json` | 4.5 KB | Frame geometry definitions (paths + bounding boxes) |
| `colormodes.json` | 661 B | Light/Medium/Dark color definitions per affiliation |

## Regenerating data

If the upstream JS library updates, regenerate the data files:

```bash
# Clone and build the JS library
git clone https://github.com/spatialillusions/milsymbol.git
cd milsymbol && npm install && npm run build && cd ..

# Extract data
node tools/extract_data.mjs ./milsymbol ./milsymbol-py/milsymbol/data
```

## Current limitations (Phase 1)

- **Text fields** — `quantity`, `type`, `uniqueDesignation`, `staffComments`, and other text annotations are not yet rendered. The text placement logic (~900 lines of JS) needs porting.
- **Echelon/HQ/TF modifiers for number SIDCs** — only base symbols are covered; modifier combinations need additional extraction.
- **Extension API** — `addSymbolPart()`, `addIconParts()`, custom label overrides are not yet supported.
- **Canvas output** — only SVG rendering is implemented.
- **Size parameter** — scales the output SVG dimensions but does not re-derive stroke widths or layout (matches JS behavior).

## Roadmap

- [ ] Port text field placement (`textfields.js`, 893 lines)
- [ ] Port echelon/mobility/HQ modifiers for number SIDCs
- [ ] Comprehensive test fixture (all symbols at all sizes)
- [ ] Optimize data loading (indexed binary format)
- [ ] Extension API
- [ ] Canvas/PNG output via cairosvg or Pillow

## License

MIT — same as the original [milsymbol](https://github.com/spatialillusions/milsymbol) library.

## Credits

- **[milsymbol](https://github.com/spatialillusions/milsymbol)** by Måns Beckman — the original JavaScript library that this project ports.
- Symbol geometry and icon data derived from **MIL-STD-2525** and **STANAG APP-6** military standards.

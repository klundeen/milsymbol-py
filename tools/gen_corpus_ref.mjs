/**
 * Generate corpus-reference.json.gz — JS reference SVGs for every SIDC.
 *
 * Usage:
 *   cd milsymbol && npm install && npm run build && cd ..
 *   node tools/gen_corpus_ref.mjs ./milsymbol ./milsymbol-py/milsymbol/data
 *
 * Reads number-data.json.gz and letter-data.json.gz from the data dir,
 * renders each SIDC through the JS library at size=100, and writes
 * corpus-reference.json.gz with the resulting SVGs.
 */

import { readFileSync, writeFileSync } from "fs";
import { gunzipSync, gzipSync } from "zlib";
import { join } from "path";

const msPath = process.argv[2] || "./milsymbol";
const dataDir = process.argv[3] || "./milsymbol-py/milsymbol/data";

// Dynamic import of the built library
const ms = (await import(join(process.cwd(), msPath, "dist/milsymbol.js"))).default;

// Number SIDCs
const nBuf = gunzipSync(readFileSync(join(dataDir, "number-data.json.gz")));
const numberData = JSON.parse(nBuf.toString());
const numberSvgs = {};
let nc = 0;
for (const sidc of Object.keys(numberData)) {
  const s = new ms.Symbol(sidc, { size: 100 });
  if (s.isValid()) {
    numberSvgs[sidc] = s.asSVG();
    nc++;
  }
}
process.stderr.write(`Number: ${nc} SVGs\n`);

// Letter SIDCs
const lBuf = gunzipSync(readFileSync(join(dataDir, "letter-data.json.gz")));
const letterData = JSON.parse(lBuf.toString());
const letterSvgs = {};
let lc = 0;
for (const sidc of Object.keys(letterData)) {
  const s = new ms.Symbol(sidc, { size: 100 });
  if (s.isValid()) {
    letterSvgs[sidc] = s.asSVG();
    lc++;
  }
}
process.stderr.write(`Letter: ${lc} SVGs\n`);

const ref = JSON.stringify({ number: numberSvgs, letter: letterSvgs });
const gz = gzipSync(Buffer.from(ref));
const outPath = join(dataDir, "corpus-reference.json.gz");
writeFileSync(outPath, gz);
process.stderr.write(
  `Wrote ${outPath}: ${(gz.length / 1024 / 1024).toFixed(1)} MB, ${nc + lc} symbols\n`
);

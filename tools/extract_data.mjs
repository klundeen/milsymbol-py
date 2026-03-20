#!/usr/bin/env node
/**
 * extract_data.mjs — Extract draw instructions from milsymbol JS library.
 *
 * Prerequisites:
 *   cd /path/to/milsymbol && npm install && npm run build
 *
 * Usage:
 *   node extract_data.mjs /path/to/milsymbol /path/to/output_dir
 *
 * Generates:
 *   number-data.json.gz  — Draw instructions for all number-based SIDCs × affiliations
 *   letter-data.json.gz  — Draw instructions for all letter-based SIDCs × affiliations + echelons
 *   colormodes.json      — Color mode definitions
 *   dasharrays.json      — Dash array definitions
 *   geometries.json      — Frame geometry definitions
 *   smoke-tests.json     — Reference SVGs for smoke testing
 */

import { createWriteStream, writeFileSync, readFileSync, readdirSync } from "fs";
import { join } from "path";
import { createGzip } from "zlib";

const milsymbolPath = process.argv[2] || ".";
const outputDir = process.argv[3] || ".";

// Dynamic import from the milsymbol repo
const { ms, app6b, std2525b, std2525c, app6d, std2525d } = await import(
  join(milsymbolPath, "index.mjs")
);

ms.reset();
ms.addIcons(app6b);
ms.addIcons(std2525b);
ms.addIcons(std2525c);
ms.addIcons(app6d);
ms.addIcons(std2525d);

function writeGzJson(filepath, data) {
  const json = JSON.stringify(data);
  const { execSync } = await import("child_process");
  writeFileSync(filepath.replace(/\.gz$/, ""), json);
  execSync(`gzip -f ${filepath.replace(/\.gz$/, "")}`);
  const size = readFileSync(filepath).length;
  console.log(`  ${filepath}: ${(size / 1024 / 1024).toFixed(1)} MB`);
}

// ── 1. Number SIDCs ──
console.log("Extracting number SIDCs...");
const symbolSets = [
  "01","02","05","06","10","11","15","20","25","27",
  "30","35","36","40","45","50","51","52","60",
];
const affiliations = ["0", "1", "2", "3", "4", "5", "6"];
const numberData = {};
let nCount = 0;

for (const ss of symbolSets) {
  // Find valid entities using friendly affiliation
  const validEntities = [];
  for (let e = 0; e < 100; e++) {
    for (let t = 0; t < 100; t++) {
      for (let st = 0; st < 100; st++) {
        const entity =
          String(e).padStart(2, "0") +
          String(t).padStart(2, "0") +
          String(st).padStart(2, "0");
        const sidc = "1003" + ss + "0000" + entity + "0000";
        if (new ms.Symbol(sidc, { size: 100 }).isValid()) {
          validEntities.push(entity);
        }
      }
    }
  }
  // Extract all affiliations for each valid entity
  for (const entity of validEntities) {
    for (const aff of affiliations) {
      const sidc = "100" + aff + ss + "0000" + entity + "0000";
      const s = new ms.Symbol(sidc, { size: 100 });
      if (s.isValid()) {
        numberData[sidc] = {
          di: s.drawInstructions,
          bb: { x1: s.bbox.x1, y1: s.bbox.y1, x2: s.bbox.x2, y2: s.bbox.y2 },
        };
        nCount++;
      }
    }
  }
  process.stderr.write(`  SS ${ss}: ${nCount} total\n`);
}
console.log(`Total number SIDCs: ${nCount}`);

// Write gzipped
const nJson = JSON.stringify(numberData);
writeFileSync(join(outputDir, "number-data.json"), nJson);
const { execSync } = await import("child_process");
execSync(`gzip -f ${join(outputDir, "number-data.json")}`);
console.log(
  `  number-data.json.gz: ${(readFileSync(join(outputDir, "number-data.json.gz")).length / 1024 / 1024).toFixed(1)} MB`
);

// ── 2. Letter SIDCs ──
console.log("Extracting letter SIDCs...");
const letterPatterns = new Set();
const srcDir = join(milsymbolPath, "src/lettersidc/sidc");
for (const f of readdirSync(srcDir)) {
  const content = readFileSync(join(srcDir, f), "utf8");
  const matches = content.matchAll(/sId\["([^"]+)"\]/g);
  for (const m of matches) letterPatterns.add(m[1]);
}

const letterAff = ["F", "H", "N", "U", "A", "S"];
const echelons = ["-", "A", "B", "C", "D", "E", "F", "G", "H"];
const letterData = {};
let lCount = 0;

for (const pattern of letterPatterns) {
  for (const aff of letterAff) {
    let sidc = pattern;
    if (sidc.length >= 2) sidc = sidc[0] + aff + sidc.slice(2);
    const s = new ms.Symbol(sidc, { size: 100 });
    if (s.isValid()) {
      letterData[sidc] = {
        di: s.drawInstructions,
        bb: { x1: s.bbox.x1, y1: s.bbox.y1, x2: s.bbox.x2, y2: s.bbox.y2 },
      };
      lCount++;
    }
    // Echelon variants
    if (sidc.length >= 10) {
      const base10 = sidc.substring(0, 10);
      for (const e of echelons) {
        if (e === "-") continue;
        const withEch = base10 + "-" + e;
        if (!(withEch in letterData)) {
          const se = new ms.Symbol(withEch, { size: 100 });
          if (se.isValid() && se.drawInstructions.length > 0) {
            letterData[withEch] = {
              di: se.drawInstructions,
              bb: { x1: se.bbox.x1, y1: se.bbox.y1, x2: se.bbox.x2, y2: se.bbox.y2 },
            };
            lCount++;
          }
        }
      }
    }
  }
}
console.log(`Total letter SIDCs: ${lCount}`);

const lJson = JSON.stringify(letterData);
writeFileSync(join(outputDir, "letter-data.json"), lJson);
execSync(`gzip -f ${join(outputDir, "letter-data.json")}`);
console.log(
  `  letter-data.json.gz: ${(readFileSync(join(outputDir, "letter-data.json.gz")).length / 1024 / 1024).toFixed(1)} MB`
);

// ── 3. Metadata files ──
console.log("Extracting metadata...");
const colorModes = {};
for (const mode of ["Light", "Medium", "Dark"]) {
  try { colorModes[mode] = ms.getColorMode(mode); } catch (e) {}
}
writeFileSync(join(outputDir, "colormodes.json"), JSON.stringify(colorModes, null, 2));
writeFileSync(join(outputDir, "dasharrays.json"), JSON.stringify(ms.getDashArrays(), null, 2));

import symbolGeometries from `${milsymbolPath}/src/ms/symbolgeometries.js`;
const geoExport = {};
for (const [key, val] of Object.entries(symbolGeometries)) {
  geoExport[key] = {
    g: val.g,
    bbox: { x1: val.bbox.x1, y1: val.bbox.y1, x2: val.bbox.x2, y2: val.bbox.y2 },
  };
}
writeFileSync(join(outputDir, "geometries.json"), JSON.stringify(geoExport, null, 2));

// ── 4. Smoke tests ──
console.log("Generating smoke tests...");
const smokeTests = [
  { sidc: "10031000001211000000", name: "Friendly Infantry (Num)" },
  { sidc: "SFG-UCI----D", name: "Friendly Infantry (Let)" },
  { sidc: "10061000001211000000", name: "Hostile Infantry (Num)" },
  { sidc: "SHG-UCI----", name: "Hostile Infantry (Let)" },
  { sidc: "10041500001101000000", name: "Neutral Fixed Wing (Num)" },
  { sidc: "SNA-MFQ----", name: "Neutral Fighter (Let)" },
  { sidc: "10011000001211000000", name: "Unknown Infantry (Num)" },
  { sidc: "SUG-UCI----", name: "Unknown Infantry (Let)" },
  { sidc: "10032000001100000000", name: "Friendly Ship (Num)" },
  { sidc: "10031000001205000000", name: "Friendly Armor (Num)" },
  { sidc: "SFG-UCA----", name: "Friendly Armor (Let)" },
  { sidc: "10031000001206000000", name: "Friendly Artillery (Num)" },
];
const smokeResults = [];
for (const test of smokeTests) {
  const sym = new ms.Symbol(test.sidc, { size: 80 });
  smokeResults.push({
    sidc: test.sidc,
    name: test.name,
    valid: sym.isValid(),
    svg: sym.asSVG(),
    anchor: sym.getAnchor(),
    symbolSize: sym.getSize(),
  });
}
writeFileSync(join(outputDir, "smoke-tests.json"), JSON.stringify(smokeResults, null, 2));
console.log(`  ${smokeResults.length} smoke tests`);

console.log("\nDone!");

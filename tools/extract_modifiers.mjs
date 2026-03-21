#!/usr/bin/env node
/**
 * extract_modifiers.mjs — Extract modifier (m1/m2) draw instructions from milsymbol.
 *
 * Prerequisites:
 *   cd /path/to/milsymbol && npm install && npm run build
 *
 * Usage:
 *   node extract_modifiers.mjs /path/to/milsymbol /path/to/output_dir
 *
 * Generates:
 *   modifier-data.json.gz — Modifier draw instructions keyed by symbol set + affiliation
 */

import { writeFileSync, readFileSync } from "fs";
import { join } from "path";

import { resolve } from "path";
import { pathToFileURL } from "url";

const milsymbolPath = process.argv[2] || ".";
const outputDir = process.argv[3] || ".";

const indexPath = pathToFileURL(resolve(milsymbolPath, "index.mjs")).href;
const milsymbolModule = await import(indexPath);
const { ms } = milsymbolModule;
const app6b = milsymbolModule.app6b;
const std2525b = milsymbolModule.std2525b;
const std2525c = milsymbolModule.std2525c;
const app6d = milsymbolModule.app6d;
const std2525d = milsymbolModule.std2525d;

ms.reset();
ms.addIcons(app6b);
ms.addIcons(std2525b);
ms.addIcons(std2525c);
ms.addIcons(app6d);
ms.addIcons(std2525d);

const symbolSets = [
  "01","02","05","06","10","11","15","20","25","27",
  "30","35","36","40","45","50","51","52","60",
];
const affiliations = ["0", "1", "2", "3", "4", "5", "6"];

const modData = {};
let totalEntries = 0;

for (const ss of symbolSets) {
  for (const aff of affiliations) {
    // Create a symbol to prime the icon cache for this ss+aff combo
    const sidc = "100" + aff + ss + "0000" + "000000" + "0000";
    const sym = new ms.Symbol(sidc, { size: 100 });

    // Now call getIcons.number to get the m1/m2 dictionaries
    // We need to reach into the internals the same way icon.js does
    const fillColor = sym.colors.fillColor[sym.metadata.affiliation];
    const neutralColor = sym.colors.fillColor.Neutral;
    const iconColor = sym.colors.iconColor[sym.metadata.affiliation];
    const iconFillColor = sym.colors.iconFillColor[sym.metadata.affiliation];
    const none = sym.colors.none[sym.metadata.affiliation];
    const black = sym.colors.black[sym.metadata.affiliation];
    const white = sym.colors.white[sym.metadata.affiliation];

    const icnet =
      "standard:" + (sym.metadata.STD2525 ? "2525" : "APP6") +
      ",edition:" + (sym.metadata.edition || "") + "," +
      sym.metadata.dimension + sym.metadata.affiliation +
      sym.metadata.notpresent + sym.metadata.numberSIDC +
      ",frame:" + sym.style.frame +
      ",alternateMedal:" + sym.style.alternateMedal +
      ",colors:{fillcolor:" + fillColor +
      ",neutralColor" + neutralColor +
      ",iconColor:" + iconColor +
      ",iconFillColor:" + iconFillColor +
      ",none:" + none +
      ",black:" + black +
      ",white:" + white + "}";

    // Get icon parts (may be cached)
    let iconParts;
    if (ms._iconCache.hasOwnProperty(icnet)) {
      iconParts = ms._iconCache[icnet].iconParts;
    } else {
      ms._iconCache[icnet] = {};
      iconParts = ms._iconCache[icnet].iconParts = ms._getIconParts(
        sym.metadata, sym.colors, sym.metadata.STD2525,
        sym.style.monoColor, sym.style.alternateMedal
      );
    }

    // Call getIcons for this symbol set
    let result;
    if (ms._iconCache[icnet].hasOwnProperty("numberSIDC") &&
        ms._iconCache[icnet].numberSIDC.symbolSet.hasOwnProperty(ss)) {
      result = ms._iconCache[icnet].numberSIDC.symbolSet[ss];
    } else {
      if (!ms._iconCache[icnet].hasOwnProperty("numberSIDC")) {
        ms._iconCache[icnet].numberSIDC = { symbolSet: {} };
      }
      result = ms._iconCache[icnet].numberSIDC.symbolSet[ss] =
        ms._getIcons.number(ms, ss, iconParts, sym.metadata.STD2525, sym.metadata.edition);
    }

    const m1Dict = result.m1 || {};
    const m2Dict = result.m2 || {};

    const ssAffKey = ss + "_" + aff;

    // Store m1 entries
    for (const [code, drawInstr] of Object.entries(m1Dict)) {
      if (drawInstr && (Array.isArray(drawInstr) ? drawInstr.length > 0 : true)) {
        const key = ssAffKey + "_m1_" + code;
        modData[key] = drawInstr;
        totalEntries++;
      }
    }

    // Store m2 entries
    for (const [code, drawInstr] of Object.entries(m2Dict)) {
      if (drawInstr && (Array.isArray(drawInstr) ? drawInstr.length > 0 : true)) {
        const key = ssAffKey + "_m2_" + code;
        modData[key] = drawInstr;
        totalEntries++;
      }
    }
  }
  process.stderr.write(`  SS ${ss}: ${totalEntries} total modifier entries\n`);
}

console.log(`Total modifier entries: ${totalEntries}`);

const json = JSON.stringify(modData);
const outPath = join(outputDir, "modifier-data.json");
writeFileSync(outPath, json);
const { execSync } = await import("child_process");
execSync(`gzip -f ${outPath}`);
const gzPath = outPath + ".gz";
const size = readFileSync(gzPath).length;
console.log(`  ${gzPath}: ${(size / 1024).toFixed(0)} KB`);

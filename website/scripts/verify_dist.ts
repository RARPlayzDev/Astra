/**
 * Post-build verification: the production bundles must still contain the
 * class hooks and copy the smoke test asserts on, and every asset referenced
 * by the built HTML must exist on disk. Run: npm run verify:dist
 */
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";

const DIST = resolve("dist");
const ASSETS = join(DIST, "assets");

/** asset filenames are content-hashed, so discover them instead of hardcoding */
function findAsset(prefix: string): string {
  const file = readdirSync(ASSETS).find((f) => f.startsWith(prefix) && f.endsWith(".js"));
  if (!file) throw new Error(`no built asset starting with "${prefix}" in dist/assets`);
  return join(ASSETS, file);
}

const MUST: [string, string[]][] = [
  [findAsset("index-"), ["tl-rail", "arch-col", "road-col", "Mission Walkthrough", "0.527"]],
  [findAsset("results-"), ["res-kpi", "Monte Carlo", "96.9"]],
  [findAsset("console-"), ["sr-only", "doc-topbar"]],
  [findAsset("documentation-"), ["doc-h1", "doc-sidebar"]],
];

/**
 * Hooks shared by more than one page get hoisted by Rollup into a common
 * chunk, and which chunk that is changes as pages gain/lose shared imports
 * (e.g. PageWipe became landing-only), so search *all* bundles rather than
 * hardcoding one — the guard is "the copy survived the build", not "it sits
 * in styles-*.js".
 */
const SHARED = ["sec-dots", "Page sections"];

let failed = 0;

for (const [file, needles] of MUST) {
  const text = readFileSync(file, "utf8");
  const missing = needles.filter((n) => !text.includes(n));
  const name = file.split(/[\\/]/).pop();
  if (missing.length) {
    failed++;
    console.log(`FAIL ${name}  missing: ${missing.join(", ")}`);
  } else {
    console.log(`ok   ${name}  (${needles.length} hooks)`);
  }
}

const bundles = readdirSync(ASSETS)
  .filter((f) => f.endsWith(".js"))
  .map((f) => join(ASSETS, f));
const bundleText = new Map(bundles.map((b) => [b, readFileSync(b, "utf8")]));

for (const needle of SHARED) {
  const hit = [...bundleText.values()].find((t) => t.includes(needle));
  if (!hit) {
    failed++;
    console.log(`FAIL shared hook "${needle}" missing from every bundle`);
  } else {
    const name = [...bundleText].find(([, t]) => t === hit)![0].split(/[\\/]/).pop();
    console.log(`ok   shared hook "${needle}" in ${name}`);
  }
}

for (const page of ["index.html", "console.html", "documentation.html", "results.html"]) {
  const html = readFileSync(join(DIST, page), "utf8");

  const refs = [...html.matchAll(/(?:src|href)="(\/(?:assets|data|docs|figures)\/[^"]+)"/g)].map(
    (m) => m[1],
  );
  const broken = refs.filter((r) => !existsSync(join(DIST, r.replace(/^\//, ""))));

  if (broken.length) {
    failed++;
    console.log(`FAIL ${page}  broken refs: ${broken.join(", ")}`);
  } else {
    console.log(`ok   ${page.padEnd(20)} ${refs.length} ref(s) resolve`);
  }

  // no-flash theme bootstrap must survive the build: it sets dataset.theme
  // on <html> from localStorage before first paint.
  if (!html.includes("dataset.theme") || !html.includes("astra.theme")) {
    failed++;
    console.log(`FAIL ${page}  missing no-flash theme bootstrap`);
  }
}

console.log(failed === 0 ? "DIST VERIFY PASSED" : `DIST VERIFY FAILED (${failed})`);
process.exit(failed === 0 ? 0 : 1);

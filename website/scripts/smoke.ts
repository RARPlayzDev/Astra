/**
 * Render-time smoke test: server-renders each page to catch runtime crashes
 * (type errors don't catch null-derefs at render time), asserts that the
 * headline content of each page is present in the markup, and audits the
 * markup structure (unique ids, resolvable in-page links, one <h1>).
 *
 * Pages only — the engine parity check is `node scripts/_bundle.cjs &&
 * node scripts/_smoke.cjs` (see HOW_TO_TEST.md, Level 7).
 *
 * Run: npm run smoke
 */
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import Home from "../src/pages/Home";
import Documentation from "../src/pages/Documentation";
import Console from "../src/pages/Console";
import Results from "../src/pages/Results";

/** Substrings that must appear in the rendered markup of each page. */
const REQUIRED: Record<string, string[]> = {
  Home: [
    "ASTRA",
    "By the numbers",
    "Finding a needle",
    "Mission Walkthrough",
    "tl-rail",
    "Four layers, one decision per cycle",
    "arch-col",
    "A complete Electronic Support pipeline",
    "0.527",
    "Run the loop yourself",
    "road-col vision",
    "sec-dots",
    "Frequently asked queries",
    "Straight answers to common questions",
    // the KPP gate on Home must also render from the baked data
    "CAPABLE",
    "DISQUALIFIED",
  ],
  Documentation: ["Download .md", "Architecture reference", "doc-h1"],
  Console: ["ASTRA", "doc-topbar"],
  Results: [
    "Verified Results",
    "Reproducible by construction",
    "Monte Carlo",
    "sec-dots",
    "res-kpi",
    // real metrics must be in the first paint, not fetched: the page used to
    // render "Loading..." forever whenever /data/results.json was unreachable
    "CAPABLE",
    "DISQUALIFIED",
    "90.3",
    "0.475",
    "96.9",
    "Gated-MES paired tests",
  ],
};

const pages: [string, () => unknown][] = [
  ["Home", Home as () => unknown],
  ["Documentation", Documentation as () => unknown],
  ["Console", Console as () => unknown],
  ["Results", Results as () => unknown],
];

/**
 * The console is a client-only app (it drives a canvas inside useLayoutEffect),
 * so React prints the known "useLayoutEffect does nothing on the server"
 * warning during this render pass. It is expected — filter just that one line.
 */
const CLIENT_ONLY = new Set(["Console"]);
const EXPECTED_WARNING = "useLayoutEffect does nothing on the server";

/**
 * Structural audit of the rendered markup:
 *  · ids must be unique (the chapter rail and in-page links rely on them)
 *  · every `href="#id"` must resolve inside the same document
 *  · each page must expose at least one <h1>
 */
function audit(html: string): string[] {
  const problems: string[] = [];

  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]);
  const dupes = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))];
  if (dupes.length) problems.push(`duplicate ids: ${dupes.join(", ")}`);

  const targets = [...html.matchAll(/href="#([^"]+)"/g)].map((m) => m[1]);
  const dead = [...new Set(targets.filter((t) => !ids.includes(t)))];
  if (dead.length) problems.push(`dead in-page links: ${dead.join(", ")}`);

  if (!/<h1[ >]/.test(html)) problems.push("no <h1>");

  return problems;
}

let failed = 0;
for (const [name, Comp] of pages) {
  try {
    // silence the expected client-only SSR warning, but never swallow anything else
    const realError = console.error;
    const swallowed: string[] = [];
    if (CLIENT_ONLY.has(name)) {
      console.error = (...args: unknown[]) => {
        const text = args.map(String).join(" ");
        if (text.includes(EXPECTED_WARNING)) return;
        swallowed.push(text);
        realError(...args);
      };
    }
    let html = "";
    try {
      html = renderToString(createElement(Comp));
    } finally {
      console.error = realError;
    }

    const thin = html.length <= 2000;
    const missing = (REQUIRED[name] ?? []).filter((s) => !html.includes(s));
    const structural = audit(html);
    const ok = !thin && missing.length === 0 && structural.length === 0 && swallowed.length === 0;
    console.log(`${ok ? "ok  " : "FAIL"} ${name.padEnd(15)} ${html.length} chars`);
    if (thin) console.error(`     too thin (${html.length} chars)`);
    for (const m of missing) console.error(`     missing: ${m}`);
    for (const p of structural) console.error(`     ${p}`);
    if (!ok) failed++;
  } catch (e) {
    failed++;
    console.error(`FAIL ${name}:`, e);
  }
}
console.log(failed === 0 ? "SMOKE PASSED" : `SMOKE FAILED (${failed})`);
process.exit(failed === 0 ? 0 : 1);

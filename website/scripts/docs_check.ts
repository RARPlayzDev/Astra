/**
 * Sanity test for the Documentation page's section engine — mirrors the
 * exact logic in src/pages/Documentation.tsx against the generated HTML.
 * Run: npm run docs:check
 */
import { DOCS_HTML } from "../src/content/docsHtml";

type Section = { id: string; num: string; title: string };

function deriveSections(html: string): Section[] {
  const out: Section[] = [];
  const re = /<h2[^>]*\bid="([^"]+)"[^>]*>([\s\S]*?)<\/h2>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) {
    const id = m[1];
    if (id === "contents") continue;
    const raw = m[2].replace(/<[^>]*>/g, "").replace(/&amp;/g, "&").trim();
    const num = (raw.match(/^(\d+)\./) ?? [])[1] ?? "";
    const title = raw.replace(/^\d+\.\s*/, "");
    out.push({ id, num, title });
  }
  return out;
}

function sliceFrom(html: string, start: number): string {
  const next = html.indexOf("<h2", start + 4);
  const end = next === -1 ? html.length : next;
  return html.slice(start, end).replace(/<hr\s*\/?>/g, "").trim();
}

function extractSection(html: string, id: string): string {
  const start = html.indexOf(`<h2 id="${id}"`);
  if (start === -1) {
    const loose = html.indexOf(`id="${id}"`);
    if (loose === -1) return "";
    const h2 = html.lastIndexOf("<h2", loose);
    return sliceFrom(html, h2 === -1 ? loose : h2);
  }
  return sliceFrom(html, start);
}

const sections = deriveSections(DOCS_HTML);
console.log(`sections derived: ${sections.length}`);

let failures = 0;
for (const s of sections) {
  const body = extractSection(DOCS_HTML, s.id);
  const ok = body.includes(`id="${s.id}"`) && body.length > 200;
  if (!ok) {
    failures++;
    console.error(`FAIL  ${s.id}  (len=${body.length})`);
  } else {
    console.log(`ok    ${s.num.padStart(2)} ${s.title.padEnd(34)} ${body.length} chars`);
  }
}

// mojibake guard
const mojibake = (DOCS_HTML.match(/[ÂÃâ][€€™™]|â€|Â·|Ã—/g) ?? []).length;
if (mojibake > 0) { failures++; console.error(`FAIL  mojibake sequences found: ${mojibake}`); }
else console.log("ok    no mojibake sequences");

if (sections.length < 20) { failures++; console.error(`FAIL  expected >= 20 sections, got ${sections.length}`); }

console.log(failures === 0 ? "DOCS CHECK PASSED" : `DOCS CHECK FAILED (${failures})`);
process.exit(failures === 0 ? 0 : 1);

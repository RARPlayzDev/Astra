import { useEffect, useMemo, useRef, useState } from "react";
import { DOCS_HTML } from "../content/docsHtml";
import { DOWNLOAD_URL, Logo, SITE_VERSION, ThemeToggle } from "../shared";

type Section = { id: string; num: string; title: string };

/**
 * Derive the table of contents from the generated HTML itself — no
 * hand-maintained list, so it can never drift from the manual again.
 * (The old page matched literal `<h2>…</h2>` headings, which never existed —
 * the exporter emits `<h2 id="…">`, so every section showed
 * "Section content not available.")
 */
function deriveSections(html: string): Section[] {
  const out: Section[] = [];
  const re = /<h2[^>]*\bid="([^"]+)"[^>]*>([\s\S]*?)<\/h2>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) {
    const id = m[1];
    if (id === "contents") continue;          // the meta TOC is not a section
    const raw = m[2].replace(/<[^>]*>/g, "").replace(/&amp;/g, "&").trim();
    const num = (raw.match(/^(\d+)\./) ?? [])[1] ?? "";
    const title = raw.replace(/^\d+\.\s*/, "");
    out.push({ id, num, title });
  }
  return out;
}

/** Slice one section out of the full HTML: from its <h2> to the next <h2>. */
function sliceFrom(html: string, start: number): string {
  const next = html.indexOf("<h2", start + 4);
  const end = next === -1 ? html.length : next;
  return html.slice(start, end).replace(/<hr\s*\/?>/g, "").trim();
}

function extractSection(html: string, id: string): string {
  const start = html.indexOf(`<h2 id="${id}"`);
  if (start === -1) {
    const loose = html.indexOf(`id="${id}"`);
    if (loose === -1) return "<p>Section not found — regenerate docs with <code>python -m tools.export_docs</code>.</p>";
    const h2 = html.lastIndexOf("<h2", loose);
    return sliceFrom(html, h2 === -1 ? loose : h2);
  }
  return sliceFrom(html, start);
}

export default function Documentation() {
  const sections = useMemo(() => deriveSections(DOCS_HTML), []);
  const [active, setActive] = useState(0);
  const [query, setQuery] = useState("");
  const [tocOpen, setTocOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sections.map((s, i) => ({ s, i }));
    return sections
      .map((s, i) => ({ s, i }))
      .filter(({ s }) => s.title.toLowerCase().includes(q) || s.num.includes(q));
  }, [sections, query]);

  // deep link: /documentation.html#12-evaluation-methodology
  useEffect(() => {
    const hash = decodeURIComponent(window.location.hash.replace(/^#/, ""));
    if (!hash) return;
    const idx = sections.findIndex((s) => s.id === hash);
    if (idx >= 0) setActive(idx);
  }, [sections]);

  // reset scroll + keep URL hash in sync + install code-copy buttons
  useEffect(() => {
    window.scrollTo(0, 0);
    const section = sections[active];
    if (section) {
      history.replaceState(null, "", "#" + section.id);
      document.title = `${section.num ? section.num + ". " : ""}${section.title} — ASTRA Docs`;
    }
    const root = contentRef.current;
    if (!root) return;
    root.querySelectorAll("pre").forEach((pre) => {
      if (pre.querySelector(".code-copy")) return;
      const btn = document.createElement("button");
      btn.className = "code-copy";
      btn.type = "button";
      btn.textContent = "copy";
      btn.addEventListener("click", () => {
        const code = pre.querySelector("code")?.textContent ?? pre.textContent ?? "";
        navigator.clipboard?.writeText(code).then(() => {
          btn.textContent = "copied ✓";
          setTimeout(() => (btn.textContent = "copy"), 1400);
        }).catch(() => (btn.textContent = "Ctrl+C"));
      });
      (pre as HTMLElement).appendChild(btn);
    });
  }, [active, sections]);

  // keyboard paging
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "ArrowRight" && active < sections.length - 1) setActive(active + 1);
      if (e.key === "ArrowLeft" && active > 0) setActive(active - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, sections.length]);

  const section = sections[active];
  const sectionHtml = section ? extractSection(DOCS_HTML, section.id) : "";
  const prev = sections[active - 1];
  const next = sections[active + 1];

  const go = (i: number) => {
    setActive(i);
    setTocOpen(false);
  };

  return (
    <div className="docs-page">
      {/* top bar */}
      <header className="doc-topbar">
        <div className="doc-topbar-inner">
          <a href="/" aria-label="ASTRA home"><Logo size={24} /></a>
          <a href="/" className="brand-txt">ASTRA</a>
          <span className="crumb">/ <b>Documentation</b></span>
          <span className="doc-ver">{SITE_VERSION}</span>
          <div className="doc-actions">
            <button
              className="doc-mobile-toc"
              type="button"
              onClick={() => setTocOpen(!tocOpen)}
            >
              ☰ Contents
            </button>
            <a className="btn ghost" href="/docs/manual.md" download>Download .md</a>
            <a className="btn ghost" href={DOWNLOAD_URL} download>Get the app</a>
            <ThemeToggle />
            <a className="btn primary" href="/">Back to site</a>
          </div>
        </div>
      </header>

      <div className="doc-body">
        {/* sidebar */}
        <aside className={"doc-sidebar" + (tocOpen ? " open" : "")}>
          <h3>Table of Contents</h3>
          <div className="dsearch">
            <input
              type="search"
              placeholder="Filter sections…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Filter documentation sections"
            />
          </div>
          <nav>
            {filtered.map(({ s, i }) => (
              <button
                key={s.id}
                className={i === active ? "on" : ""}
                onClick={() => go(i)}
                type="button"
              >
                <span className="n">{s.num || "·"}</span>
                <span>{s.title}</span>
              </button>
            ))}
            {filtered.length === 0 && (
              <div className="no-res">No section matches “{query}”.</div>
            )}
          </nav>
        </aside>

        {/* content */}
        <main className="docpage">
          <div
            className="doc-content"
            ref={contentRef}
            dangerouslySetInnerHTML={{ __html: sectionHtml }}
          />

          <div className="doc-pager">
            {prev ? (
              <button onClick={() => go(active - 1)} type="button">
                <span className="dir">← Previous</span>
                {prev.num}. {prev.title}
              </button>
            ) : <span />}
            {next ? (
              <button className="next" onClick={() => go(active + 1)} type="button">
                <span className="dir">Next →</span>
                {next.num}. {next.title}
              </button>
            ) : <span />}
          </div>
        </main>
      </div>
    </div>
  );
}
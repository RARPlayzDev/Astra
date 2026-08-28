import { useState, useEffect, useRef } from "react";
import { DOCS_HTML } from "../content/docsHtml";
import { Logo } from "../shared";

type Section = { id: string; title: string; heading: string };

const SECTIONS: Section[] = [
  { id: "1-introduction", title: "Introduction", heading: "1. Introduction" },
  { id: "2-installation", title: "Installation", heading: "2. Installation" },
  { id: "3-quick-start", title: "Quick Start", heading: "3. Quick start" },
  { id: "4-interface-tour", title: "Interface Tour", heading: "4. Interface tour" },
  { id: "5-operations-perspective", title: "Operations", heading: "5. Operations perspective" },
  { id: "6-analysis-perspective", title: "Analysis", heading: "6. Analysis perspective" },
  { id: "7-data--sources-perspective", title: "Data & Sources", heading: "7. Data &amp; Sources perspective" },
  { id: "8-radar-and-sensor-integration", title: "Sensor Integration", heading: "8. Radar and sensor integration" },
  { id: "9-scenarios", title: "Scenarios", heading: "9. Scenarios" },
  { id: "10-datasets-and-calibration", title: "Datasets & Calibration", heading: "10. Datasets and calibration" },
  { id: "11-scheduling-policies", title: "Scheduling Policies", heading: "11. Scheduling policies" },
  { id: "12-evaluation-methodology", title: "Evaluation", heading: "12. Evaluation methodology" },
  { id: "13-diagnostics-and-troubleshooting", title: "Diagnostics", heading: "13. Diagnostics and troubleshooting" },
  { id: "14-testing-without-a-radar", title: "Testing", heading: "14. Testing without a radar" },
  { id: "15-architecture-reference", title: "Architecture", heading: "15. Architecture reference" },
  { id: "16-local-api-reference", title: "API Reference", heading: "16. Local API reference" },
  { id: "17-command-line-tools", title: "CLI Tools", heading: "17. Command-line tools" },
  { id: "18-file-formats", title: "File Formats", heading: "18. File formats" },
  { id: "19-frequently-asked-questions", title: "FAQ", heading: "19. Frequently asked questions" },
  { id: "20-glossary", title: "Glossary", heading: "20. Glossary" },
];

/** Find a section by matching h2 heading text */
function extractSection(html: string, section: Section): string {
  // Try matching by heading text content
  const patterns = [
    `<h2>${section.heading}</h2>`,
    `<h2>${section.heading.replace(/&amp;/g, "&")}</h2>`,
  ];
  let idx = -1;
  for (const p of patterns) {
    idx = html.indexOf(p);
    if (idx !== -1) break;
  }
  if (idx === -1) {
    // Fallback: find the heading by partial text match
    const plainHeading = section.heading.replace(/&amp;/g, "&").replace(/^\d+\.\s*/, "");
    const h2Regex = /<h2>([^<]+)<\/h2>/g;
    let m;
    while ((m = h2Regex.exec(html)) !== null) {
      if (m[1].includes(plainHeading) || m[1] === section.heading) {
        idx = m.index;
        break;
      }
    }
  }
  if (idx === -1) return "<p>Section content not available.</p>";

  // Find the next <h2 that starts a new section
  const nextH2 = html.indexOf("<h2>", idx + 10);
  const end = nextH2 !== -1 ? nextH2 : html.length;
  return html.slice(idx, end).replace(/<hr\s*\/?>/g, "").trim();
}

export default function Documentation() {
  const [active, setActive] = useState(0);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (contentRef.current) contentRef.current.scrollTop = 0;
  }, [active]);

  const section = SECTIONS[active];
  const sectionHtml = extractSection(DOCS_HTML, section);
  const prev = active > 0 ? SECTIONS[active - 1] : null;
  const next = active < SECTIONS.length - 1 ? SECTIONS[active + 1] : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#1e1e1e" }}>
      {/* Top bar */}
      <div style={{
        display: "flex", alignItems: "center", gap: 16,
        background: "#252526", borderBottom: "1px solid #3c3c3c",
        padding: "10px 24px", flexShrink: 0,
      }}>
        <a href="/" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none" }}>
          <Logo size={22} />
          <span style={{ fontFamily: "monospace", fontWeight: 700, color: "#ccc", letterSpacing: 2, fontSize: 13 }}>ASTRA</span>
        </a>
        <span style={{ color: "#858585", fontSize: 13 }}>Documentation &mdash; v2.0.0</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 10 }}>
          <a href="/docs/manual.md" download style={{
            padding: "6px 14px", fontSize: 12, border: "1px solid #3c3c3c",
            borderRadius: 3, color: "#ccc", textDecoration: "none", background: "#2d2d30",
          }}>Download (.md)</a>
          <a href="/" style={{
            padding: "6px 14px", fontSize: 12, background: "#264f78",
            borderRadius: 3, color: "#fff", textDecoration: "none",
          }}>Back to site</a>
        </div>
      </div>

      {/* Body */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Sidebar */}
        <nav style={{
          width: 220, flexShrink: 0, background: "#252526",
          borderRight: "1px solid #3c3c3c", overflowY: "auto", padding: "12px 0",
        }}>
          <div style={{
            fontSize: 10, fontWeight: 700, letterSpacing: 1.5,
            textTransform: "uppercase", color: "#858585",
            padding: "4px 16px 10px",
          }}>
            Table of Contents
          </div>
          {SECTIONS.map((s, i) => (
            <button
              key={s.id}
              onClick={() => setActive(i)}
              style={{
                display: "block", width: "100%", textAlign: "left",
                background: active === i ? "#264f78" : "transparent",
                border: "none", color: active === i ? "#fff" : "#999",
                padding: "7px 16px", fontSize: 13, cursor: "pointer",
                fontFamily: "inherit",
                borderLeft: active === i ? "2px solid #5aa0e9" : "2px solid transparent",
              }}
            >
              {s.title}
            </button>
          ))}
        </nav>

        {/* Content */}
        <div ref={contentRef} style={{
          flex: 1, overflowY: "auto", padding: "28px 44px 60px", maxWidth: 800,
        }}>
          <div
            className="doc-content"
            dangerouslySetInnerHTML={{ __html: sectionHtml }}
          />

          {/* Prev / Next */}
          <div style={{
            display: "flex", justifyContent: "space-between",
            marginTop: 48, paddingTop: 20, borderTop: "1px solid #3c3c3c",
          }}>
            {prev ? (
              <button onClick={() => setActive(active - 1)} style={{
                background: "none", border: "1px solid #3c3c3c", borderRadius: 4,
                padding: "8px 18px", color: "#999", cursor: "pointer", fontSize: 13,
              }}>
                &larr; {prev.title}
              </button>
            ) : <div />}
            {next ? (
              <button onClick={() => setActive(active + 1)} style={{
                background: "#264f78", border: "none", borderRadius: 4,
                padding: "8px 18px", color: "#fff", cursor: "pointer", fontSize: 13,
              }}>
                {next.title} &rarr;
              </button>
            ) : <div />}
          </div>
        </div>
      </div>
    </div>
  );
}

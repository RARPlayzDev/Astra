import { DOCS_HTML } from "../content/docsHtml";
import { Logo } from "../shared";

export default function Documentation() {
  const sections = [
    { id: "1-introduction", title: "1. Introduction" },
    { id: "2-installation", title: "2. Installation" },
    { id: "3-quick-start", title: "3. Quick start" },
    { id: "4-interface-tour", title: "4. Interface tour" },
    { id: "5-operations-perspective", title: "5. Operations perspective" },
    { id: "6-analysis-perspective", title: "6. Analysis perspective" },
    { id: "7-data--sources-perspective", title: "7. Data & Sources" },
    { id: "8-radar-and-sensor-integration", title: "8. Sensor integration" },
    { id: "9-scenarios", title: "9. Scenarios" },
    { id: "10-datasets-and-calibration", title: "10. Datasets & Calibration" },
    { id: "11-scheduling-policies", title: "11. Scheduling policies" },
    { id: "12-evaluation-methodology", title: "12. Evaluation methodology" },
    { id: "13-diagnostics-and-troubleshooting", title: "13. Diagnostics" },
    { id: "14-testing-without-a-radar", title: "14. Testing without a radar" },
    { id: "15-architecture-reference", title: "15. Architecture" },
    { id: "16-local-api-reference", title: "16. Local API reference" },
    { id: "17-command-line-tools", title: "17. Command-line tools" },
    { id: "18-file-formats", title: "18. File formats" },
    { id: "19-frequently-asked-questions", title: "19. FAQ" },
    { id: "20-glossary", title: "20. Glossary" },
  ];

  return (
    <>
      <div className="doc-topbar">
        <div className="wrap" style={{ display: "flex", alignItems: "center", gap: 20, padding: "12px 28px" }}>
          <a className="brand" href="/"><Logo size={30} /><b>ASTRA</b></a>
          <span style={{ color: "var(--muted)", fontSize: 14 }}>Software documentation - v1.0.0</span>
          <div className="doc-actions" style={{ marginLeft: "auto" }}>
            <a className="btn ghost" style={{ padding: "8px 16px", fontSize: 13.5 }}
               href="/docs/manual.md" download>Download manual (.md)</a>
            <a className="btn primary" style={{ padding: "8px 16px", fontSize: 13.5 }}
               href="/">Back to site</a>
          </div>
        </div>
      </div>
      <div className="doc-layout">
        <aside className="doc-sidebar">
          <h3>Table of Contents</h3>
          <nav>
            {sections.map(s => <a key={s.id} href={`#${s.id}`}>{s.title}</a>)}
          </nav>
        </aside>
        <div className="docpage">
          <article dangerouslySetInnerHTML={{ __html: DOCS_HTML }} />
        </div>
      </div>
      <footer className="site">
        <div className="wrap">
          <p>ASTRA v1.0.0 - SIH 2026 prototype. This page is generated from the
             same source that ships inside the desktop application.</p>
        </div>
      </footer>
    </>
  );
}

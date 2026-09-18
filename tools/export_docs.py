"""Single-source-of-truth documentation pipeline (manual -> website + desktop).

The user manual ``docs/ASTRA_Software_Documentation.md`` is the one document
the desktop application serves at ``/manual`` (bundled by ``astra.spec``) and
the one the evaluation report cites.  Until now the website carried a
*separately maintained* copy of that content, which had already drifted (the
downloadable ``website/public/docs/manual.md`` was stale and the TypeScript
bundle was hand-edited).

This tool makes the manual the only source:

* converts the markdown to HTML and writes ``website/src/content/docsHtml.ts``
  (``export const DOCS_HTML = "..."``), which the website's Documentation page
  renders section by section;
* copies the markdown to ``website/public/docs/manual.md`` so the
  "Download (.md)" button always serves exactly what the app serves;
* writes ``website/public/docs/manual_sections.json`` (headings + anchors) so
  the site's table of contents is generated, not hand-maintained.

Run:  python -m tools.export_docs
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUAL = ROOT / "docs" / "ASTRA_Software_Documentation.md"
DOCS_TS = ROOT / "website" / "src" / "content" / "docsHtml.ts"
PUBLIC_MD = ROOT / "website" / "public" / "docs" / "manual.md"
PUBLIC_SECTIONS = ROOT / "website" / "public" / "docs" / "manual_sections.json"


def _inline(text: str) -> str:
    """Inline markdown -> HTML (code, bold, italics, links)."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def sections_of(md: str) -> list[dict]:
    """Level-2 headings with anchors, for the site's table of contents."""
    secs = []
    for m in re.finditer(r"^##\s+(.*)$", md, re.MULTILINE):
        title = m.group(1).strip()
        secs.append({"id": re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"),
                     "title": title})
    return secs


def _ts_escape(html: str) -> str:
    """Escape HTML for a single-line TypeScript string literal."""
    return (html.replace("\\", "\\\\").replace('"', '\\"')
            .replace("\r", "").replace("\n", "\\n"))


def markdown_to_html(md: str) -> str:
    """Convert the manual's markdown subset to HTML.

    Supports headings, tables, fenced code, unordered/ordered lists,
    block quotes, horizontal rules, paragraphs and inline emphasis - the
    subset the manual actually uses.
    """
    out: list[str] = []
    lines = md.splitlines()
    i = 0
    state = {"list": None}
    code_buf: list[str] = []
    table_buf: list[str] = []
    in_code = False

    def flush_list() -> None:
        if state["list"]:
            out.append(f"</{state['list']}>")
            state["list"] = None

    def flush_table() -> None:
        if not table_buf:
            return
        rows = [r for r in table_buf
                if not re.match(r"^\s*\|[\s:|-]+\|\s*$", r)]
        out.append("<table>")
        for idx, row in enumerate(rows):
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            tag = "th" if idx == 0 else "td"
            out.append("<tr>" + "".join(
                f"<{tag}>{_inline(c)}</{tag}>" for c in cells) + "</tr>")
        out.append("</table>")
        table_buf.clear()

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            if in_code:
                out.append("<pre><code>" + "\n".join(code_buf)
                           + "</code></pre>")
                code_buf, in_code = [], False
            else:
                flush_list()
                flush_table()
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line.replace("&", "&amp;").replace("<", "&lt;"))
            i += 1
            continue
        if line.strip().startswith("|"):
            flush_list()
            table_buf.append(line)
            i += 1
            continue
        flush_table()
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            flush_list()
            level = len(m.group(1))
            title = m.group(2).strip()
            anchor = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            out.append(f'<h{level} id="{anchor}">{_inline(title)}</h{level}>')
            i += 1
            continue
        if re.match(r"^\s*[-*]\s+", line):
            if state["list"] != "ul":
                flush_list()
                out.append("<ul>")
                state["list"] = "ul"
            out.append("<li>" + _inline(re.sub(r"^\s*[-*]\s+", "", line))
                       + "</li>")
            i += 1
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            if state["list"] != "ol":
                flush_list()
                out.append("<ol>")
                state["list"] = "ol"
            out.append("<li>" + _inline(re.sub(r"^\s*\d+\.\s+", "", line))
                       + "</li>")
            i += 1
            continue
        if line.strip() in ("---", "***"):
            flush_list()
            out.append("<hr />")
            i += 1
            continue
        if line.strip().startswith(">"):
            flush_list()
            out.append("<blockquote>" + _inline(
                line.strip().lstrip("> ").strip()) + "</blockquote>")
            i += 1
            continue
        if not line.strip():
            flush_list()
            i += 1
            continue
        flush_list()
        out.append("<p>" + _inline(line.strip()) + "</p>")
        i += 1
    flush_list()
    flush_table()
    if in_code and code_buf:
        out.append("<pre><code>" + "\n".join(code_buf) + "</code></pre>")
    return "\n".join(out)


@dataclass
class DocExportResult:
    html_chars: int
    sections: int
    outputs: list[str]


def export_docs(manual: Path = MANUAL) -> DocExportResult:
    """Regenerate the website documentation bundle from the manual."""
    md = Path(manual).read_text(encoding="utf-8")
    html = markdown_to_html(md)
    DOCS_TS.parent.mkdir(parents=True, exist_ok=True)
    DOCS_TS.write_text(
        "// AUTO-GENERATED from docs/ASTRA_Software_Documentation.md by\n"
        "// tools/export_docs.py -- do not edit by hand.\n"
        f'export const DOCS_HTML = "{_ts_escape(html)}";\n',
        encoding="utf-8")
    PUBLIC_MD.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_MD.write_text(md, encoding="utf-8")
    secs = sections_of(md)
    PUBLIC_SECTIONS.write_text(json.dumps(secs, indent=2), encoding="utf-8")
    return DocExportResult(len(html), len(secs),
                           [str(DOCS_TS), str(PUBLIC_MD),
                            str(PUBLIC_SECTIONS)])


if __name__ == "__main__":
    res = export_docs()
    print(f"docs exported: {res.html_chars} chars of HTML, "
          f"{res.sections} sections")
    for p in res.outputs:
        print("  ->", p)
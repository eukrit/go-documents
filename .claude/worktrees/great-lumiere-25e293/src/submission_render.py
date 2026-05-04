"""Render a submission record into a filled HTML string and a PDF.

HTML: fills the material/drawing template with real data via straight string
replacement (templates contain placeholder spans — we swap the .placeholder
blocks and inject real rows).

PDF: uses WeasyPrint (pure-Python, no Chromium needed).
"""
from __future__ import annotations

import html
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = {
    "material": BASE_DIR / "material-submission-template.html",
    "drawing": BASE_DIR / "drawing-submission-template.html",
}


def _esc(v) -> str:
    return html.escape("" if v is None else str(v))


def _material_rows(items: list[dict]) -> str:
    rows = []
    for i, it in enumerate(items, 1):
        rows.append(
            f"<tr><td>{i}</td>"
            f"<td>{_esc(it.get('description'))}</td>"
            f"<td>{_esc(it.get('manufacturer'))}</td>"
            f"<td>{_esc(it.get('model'))}</td>"
            f"<td>{_esc(it.get('qty'))}</td>"
            f"<td>{_esc(it.get('unit'))}</td></tr>"
        )
    # Pad to at least 5 rows
    while len(rows) < 5:
        i = len(rows) + 1
        rows.append(f"<tr><td>{i}</td><td></td><td></td><td></td><td></td><td></td></tr>")
    return "\n".join(rows)


def _drawing_rows(items: list[dict]) -> str:
    rows = []
    for i, it in enumerate(items, 1):
        rows.append(
            f"<tr><td>{i}</td>"
            f"<td>{_esc(it.get('drawingNo'))}</td>"
            f"<td>{_esc(it.get('drawingTitle'))}</td>"
            f"<td>{_esc(it.get('revision'))}</td>"
            f"<td>{_esc(it.get('scale'))}</td>"
            f"<td>{_esc(it.get('sheetSize'))}</td></tr>"
        )
    while len(rows) < 8:
        i = len(rows) + 1
        rows.append(f"<tr><td>{i}</td><td></td><td></td><td></td><td></td><td></td></tr>")
    return "\n".join(rows)


def _attachment_list(attachments: list[dict], fallback_html: str) -> str:
    if not attachments:
        return fallback_html
    lis = []
    for a in attachments:
        lis.append(
            '<li><span class="att-check">&#10004;</span> '
            f'<span class="att-label">{_esc(a.get("filename"))}</span></li>'
        )
    return "\n".join(lis)


def _fill_placeholders(html_text: str, pairs: list[tuple[str, str]]) -> str:
    """Replace the first occurrence of each placeholder value with real data.

    Each placeholder in the template is a `<div class="field-value placeholder">…</div>`.
    We replace by matching the literal placeholder content string.
    """
    out = html_text
    for placeholder_content, real in pairs:
        needle = (
            f'<div class="field-value placeholder">{placeholder_content}</div>'
        )
        if needle in out:
            out = out.replace(
                needle,
                f'<div class="field-value">{_esc(real) or "&nbsp;"}</div>',
                1,
            )
    return out


def render_html(submission: dict) -> str:
    kind = submission["type"]
    tpl_path = TEMPLATES[kind]
    html_text = tpl_path.read_text(encoding="utf-8")

    # Shared field placeholders (order matches template line-for-line)
    pairs = [
        ("MS-XXXXX-001" if kind == "material" else "DS-XXXXX-001", submission["submissionId"]),
        ("DD / MM / YYYY", submission.get("date", "")),
        ("Project name", submission.get("projectName", "")),
        ("SO2X-XXX", submission.get("soRef", "")),
        ("Client or owner name", submission.get("client", "")),
        ("Consultant or architect name", submission.get("consultant", "")),
        ("Full site address", submission.get("siteLocation", "")),
        ("Initial / Resubmission (Rev. __)",
         f"{submission.get('submissionType', 'Initial')} (Rev. {submission.get('revision', '00')})"),
    ]
    if kind == "drawing":
        pairs += [
            ("Architectural / Structural / MEP / Shop", submission.get("discipline", "")),
            ("For Approval / For Construction / For Record", submission.get("issuePurpose", "")),
            ("Name / Initials", submission.get("drawnBy", "")),
            ("Name / Initials", submission.get("checkedBy", "")),
        ]
    html_text = _fill_placeholders(html_text, pairs)

    # Item rows — replace the full tbody section
    items = submission.get("items", [])
    if kind == "material":
        # find the five empty rows block by matching the opening tbody area
        old = "\n".join([
            "        <tbody>",
        ] + [
            "          <tr>\n            <td>%d</td>\n            <td></td>\n            <td></td>\n            <td></td>\n            <td></td>\n            <td></td>\n          </tr>" % i
            for i in range(1, 6)
        ] + ["        </tbody>"])
        new = f"        <tbody>\n{_material_rows(items)}\n        </tbody>"
        html_text = html_text.replace(old, new, 1)
    else:
        old_lines = ["        <tbody>"] + [
            f"          <tr><td>{i}</td><td></td><td></td><td></td><td></td><td></td></tr>"
            for i in range(1, 9)
        ] + ["        </tbody>"]
        old = "\n".join(old_lines)
        new = f"        <tbody>\n{_drawing_rows(items)}\n        </tbody>"
        html_text = html_text.replace(old, new, 1)

    # Notes
    notes = submission.get("notes", "").strip()
    if notes:
        for placeholder in (
            "Key specifications, finishes, colours, dimensions, standards compliance, or other technical details relevant to the submitted materials.",
            "Key design intent, coordination items, setting-out references, tolerances, or callouts relevant to the drawings submitted.",
        ):
            html_text = html_text.replace(
                f'<span style="color: #999; font-style: italic;">{placeholder}</span>',
                _esc(notes),
                1,
            )

    # Reviewer remarks
    remarks = submission.get("reviewerRemarks", "").strip()
    if remarks:
        html_text = html_text.replace(
            '<div class="section-title">Reviewer Remarks</div>\n      <div class="remarks-box">\n        <span style="color: #999; font-style: italic;"></span>\n      </div>',
            f'<div class="section-title">Reviewer Remarks</div>\n      <div class="remarks-box">{_esc(remarks)}</div>',
            1,
        )

    return html_text


def render_pdf(submission: dict) -> bytes:
    """Render submission HTML to PDF bytes via WeasyPrint."""
    from weasyprint import HTML  # lazy import

    html_text = render_html(submission)
    base_url = str(BASE_DIR)
    return HTML(string=html_text, base_url=base_url).write_pdf()

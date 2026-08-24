from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

from .state import StateStore


def _register_body_font() -> str:
    requested = os.getenv("SSOPHIZ_PDF_FONT", "").strip()
    candidates = [
        requested,
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/gulim.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont("LedgerBody", candidate, subfontIndex=0))
            return "LedgerBody"
        except Exception:
            continue
    return "Helvetica"


def _task_rows(store: StateStore, task_ids: Iterable[str] | None) -> list[dict[str, Any]]:
    selected = set(task_ids or [])
    rows: list[dict[str, Any]] = []
    for row in store.list_tasks():
        if selected and str(row["id"]) not in selected:
            continue
        payload = json.loads(str(row["payload"]))
        rows.append(
            {
                "id": str(row["id"]),
                "name": str(payload["name"]),
                "category": str(row["category"]),
                "status": str(row["status"]),
                "entries": store.list_ledger_entries(str(row["id"])),
                "findings": store.list_findings(str(row["id"])),
                "candidates": store.list_candidates(str(row["id"])),
            }
        )
    missing = selected - {row["id"] for row in rows}
    if missing:
        raise KeyError(f"Unknown tasks: {', '.join(sorted(missing))}")
    return rows


def build_evidence_pdf(
    store: StateStore,
    destination: str | Path,
    *,
    task_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Render all compact challenge ledgers into one end-of-event PDF."""

    tasks = _task_rows(store, task_ids)
    if not tasks:
        raise ValueError("No tasks are available for the evidence report")

    target = Path(destination).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    body_font = _register_body_font()
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "LedgerTitle",
        parent=styles["Title"],
        fontName=body_font,
        fontSize=21,
        leading=26,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#14213D"),
        spaceAfter=8,
    )
    task_heading = ParagraphStyle(
        "TaskHeading",
        parent=styles["Heading1"],
        fontName=body_font,
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#14213D"),
        spaceAfter=4,
    )
    entry_heading = ParagraphStyle(
        "EntryHeading",
        parent=styles["Heading2"],
        fontName=body_font,
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#B45309"),
        spaceBefore=7,
        spaceAfter=3,
    )
    body = ParagraphStyle(
        "LedgerText",
        parent=styles["BodyText"],
        fontName=body_font,
        fontSize=8.7,
        leading=12,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=3,
    )
    label = ParagraphStyle(
        "LedgerLabel",
        parent=body,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#4B5563"),
        spaceBefore=3,
        spaceAfter=1,
    )
    code = ParagraphStyle(
        "LedgerCode",
        parent=styles["Code"],
        fontName=body_font,
        fontSize=7.2,
        leading=9.2,
        leftIndent=7,
        rightIndent=7,
        borderColor=colors.HexColor("#D1D5DB"),
        borderWidth=0.5,
        borderPadding=5,
        backColor=colors.HexColor("#F8FAFC"),
        spaceAfter=4,
    )

    story: list[Any] = [
        Spacer(1, 14 * mm),
        Paragraph("CTF Evidence Ledger", title),
        Paragraph(
            escape(datetime.now(UTC).strftime("Generated %Y-%m-%d %H:%M UTC")),
            ParagraphStyle("Subtitle", parent=body, alignment=TA_CENTER),
        ),
        Spacer(1, 9 * mm),
        Paragraph(
            f"{len(tasks)} challenges - compact commands, PoCs, outputs, candidates, and reproduction paths.",
            ParagraphStyle("Intro", parent=body, alignment=TA_CENTER),
        ),
        PageBreak(),
    ]

    def add_list(section: str, values: list[str], *, preformatted: bool = False) -> None:
        if not values:
            return
        story.append(Paragraph(escape(section), label))
        if preformatted:
            story.append(Preformatted(escape("\n\n".join(values)), code, maxLineLength=110))
        else:
            for index, value in enumerate(values, start=1):
                story.append(Paragraph(f"{index}. {escape(value)}", body))

    for task_index, task in enumerate(tasks):
        if task_index:
            story.append(PageBreak())
        story.extend(
            [
                Paragraph(f"{task_index + 1}. {escape(task['name'])}", task_heading),
                Paragraph(
                    escape(
                        f"Task {task['id']} | {task['category']} | status: {task['status']}"
                    ),
                    label,
                ),
                HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1")),
            ]
        )
        entries = task["entries"]
        candidate_status = {
            str(candidate["value"]): str(candidate["status"])
            for candidate in task["candidates"]
        }
        if not entries:
            story.append(Paragraph("No structured ledger entries were recorded.", body))
        for entry_index, entry in enumerate(entries, start=1):
            story.append(
                Paragraph(
                    f"Evidence {entry_index}: {escape(str(entry['summary']))}",
                    entry_heading,
                )
            )
            story.append(
                Paragraph(
                    escape(f"worker: {entry['worker']} | recorded: {entry['created_at']}"),
                    label,
                )
            )
            add_list("Commands", list(entry.get("commands") or []), preformatted=True)
            add_list("PoC / artifact paths", list(entry.get("poc_paths") or []))
            add_list("Key output", list(entry.get("key_outputs") or []), preformatted=True)
            add_list("Reproduction", list(entry.get("reproduction_steps") or []))
            add_list(
                "Flag candidates",
                [
                    f"{value} | status: {candidate_status.get(str(value), 'not queued')}"
                    for value in entry.get("flag_candidates") or []
                ],
                preformatted=True,
            )

        if task["findings"]:
            story.append(Paragraph("Legacy findings", entry_heading))
            for finding in task["findings"]:
                story.append(
                    Paragraph(
                        f"{escape(str(finding['summary']))} "
                        f"(worker {escape(str(finding['worker']))}, confidence {finding['confidence']})",
                        body,
                    )
                )
                add_list("Evidence", list(finding.get("evidence") or []), preformatted=True)

        unlinked = [candidate for candidate in task["candidates"] if not candidate.get("evidence_id")]
        if unlinked:
            story.append(Paragraph("Unlinked candidate queue", entry_heading))
            for candidate in unlinked:
                story.append(
                    Paragraph(
                        escape(
                            f"{candidate['value']} | worker {candidate['worker']} | status {candidate['status']}"
                        ),
                        body,
                    )
                )

    def footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFont(body_font, 7.5)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(18 * mm, 11 * mm, "SSophiz CTF - Evidence Ledger")
        canvas.drawRightString(A4[0] - 18 * mm, 11 * mm, f"Page {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="CTF Evidence Ledger",
        author="SSophiz CTF Harness",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return {
        "output": str(target),
        "tasks": len(tasks),
        "entries": sum(len(task["entries"]) for task in tasks),
        "bytes": target.stat().st_size,
    }

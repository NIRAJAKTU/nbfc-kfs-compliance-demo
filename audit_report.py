"""Build a downloadable PDF summary for an AI-generated demo assessment."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DISCLAIMER = (
    "This is an independent AI/GenAI portfolio demonstration using synthetic regulatory reference "
    "documents and sample financial documents. It is not an official RBI compliance system, does not "
    "establish regulatory compliance and is not intended for production financial decision-making."
)

CATEGORY_COLORS = {
    "Compliant": colors.HexColor("#16794A"),
    "Potential Gap": colors.HexColor("#A85B00"),
    "Insufficient Evidence": colors.HexColor("#5B6472"),
}


def _paragraph_text(value: Any) -> str:
    text = str(value or "Not provided")
    return escape(text).replace("\n", "<br/>")


def build_audit_pdf(filename: str, report: dict[str, Any]) -> bytes:
    """Return a compact A4 PDF report. All user/model text is HTML-escaped."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=17 * mm,
        title="AI Financial Document Intelligence Assessment",
        author="Independent AI/GenAI Portfolio Demonstration",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=20, leading=24, textColor=colors.HexColor("#102A43"), alignment=TA_LEFT,
        spaceAfter=5 * mm,
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, textColor=colors.HexColor("#102A43"), spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="BodySmall", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9, leading=12, textColor=colors.HexColor("#334E68"),
    ))
    styles.add(ParagraphStyle(
        name="Disclaimer", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=8, leading=10, textColor=colors.HexColor("#7C2D12"),
    ))

    overall = str(report.get("overall_assessment", "Insufficient Evidence"))
    accent = CATEGORY_COLORS.get(overall, CATEGORY_COLORS["Insufficient Evidence"])
    story = [
        Paragraph("AI-Powered Financial Document Intelligence", styles["ReportTitle"]),
        Paragraph("AI-generated demonstration assessment · Human review required", styles["BodySmall"]),
        Spacer(1, 4 * mm),
    ]

    summary = Table([
        [Paragraph("DOCUMENT", styles["BodySmall"]), Paragraph("OVERALL ASSESSMENT", styles["BodySmall"]), Paragraph("GENERATED (UTC)", styles["BodySmall"])],
        [Paragraph(_paragraph_text(filename), styles["BodyText"]),
         Paragraph(f'<font color="{accent.hexval()}"><b>{escape(overall)}</b></font>', styles["BodyText"]),
         Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), styles["BodyText"])],
    ], colWidths=[68 * mm, 55 * mm, 50 * mm])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F6")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([summary, Spacer(1, 4 * mm)])

    for check in report.get("checks", []):
        category = str(check.get("category", "Insufficient Evidence"))
        category_color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["Insufficient Evidence"])
        story.append(Paragraph(
            f'{escape(str(check.get("check", "Assessment check")))} · '
            f'<font color="{category_color.hexval()}"><b>{escape(category)}</b></font>',
            styles["SectionTitle"],
        ))
        story.append(Paragraph(f'<b>Finding:</b> {_paragraph_text(check.get("finding"))}', styles["BodySmall"]))

        document_evidence = check.get("document_details", [])
        if document_evidence:
            story.append(Paragraph("<b>KFS evidence:</b>", styles["BodySmall"]))
            for item in document_evidence:
                story.append(Paragraph(
                    f'{_paragraph_text(item.get("reference"))}: {_paragraph_text(item.get("excerpt"))}',
                    styles["BodySmall"],
                ))

        rule_evidence = check.get("source_details", [])
        if rule_evidence:
            story.append(Paragraph("<b>Retrieved rule evidence:</b>", styles["BodySmall"]))
            for item in rule_evidence:
                story.append(Paragraph(
                    f'{_paragraph_text(item.get("source"))}, page {_paragraph_text(item.get("page"))}: '
                    f'{_paragraph_text(item.get("text"))}',
                    styles["BodySmall"],
                ))

        story.append(Paragraph(
            f'<b>Recommended action:</b> {_paragraph_text(check.get("recommended_action"))}',
            styles["BodySmall"],
        ))
        story.append(Spacer(1, 2 * mm))

    disclaimer_table = Table([[Paragraph(_paragraph_text(DISCLAIMER), styles["Disclaimer"])]], colWidths=[173 * mm])
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7ED")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#FDBA74")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([Spacer(1, 5 * mm), disclaimer_table])
    document.build(story)
    return buffer.getvalue()

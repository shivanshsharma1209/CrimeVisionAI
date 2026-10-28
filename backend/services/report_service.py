import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.units import inch

from config import Config
from backend.utils.hashing import calculate_sha256

logger = logging.getLogger("crimevision.report")


class ReportService:
    """
    Forensic PDF Report Generation Service using ReportLab.
    Produces court-ready, professional forensic intelligence documents.
    """

    def generate_forensic_report(
        self,
        case_data: Dict[str, Any],
        evidence_list: List[Dict[str, Any]],
        timeline_list: List[Dict[str, Any]],
        transcripts_list: List[Dict[str, Any]],
        output_filename: str,
    ) -> Dict[str, Any]:
        """
        Generate a multi-page PDF forensic analysis report.
        Saves to storage/reports/ and calculates its SHA-256 hash.
        """
        reports_dir = Config.REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = reports_dir / output_filename

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Custom Forensic Styles
        header_dark = colors.HexColor("#0f172a")
        accent_blue = colors.HexColor("#0284c7")
        slate_gray = colors.HexColor("#475569")
        light_bg = colors.HexColor("#f8fafc")

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=header_dark,
            alignment=1,  # Center
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=accent_blue,
            alignment=1,
        )

        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=header_dark,
            spaceBefore=12,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=slate_gray,
        )

        body_bold = ParagraphStyle(
            "DocBodyBold",
            parent=body_style,
            fontName="Helvetica-Bold",
            textColor=header_dark,
        )

        table_header = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.whitesmoke,
            alignment=1,
        )

        table_cell = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=header_dark,
        )

        table_cell_code = ParagraphStyle(
            "TableCellCode",
            parent=table_cell,
            fontName="Courier",
            fontSize=7,
            leading=9,
        )

        disclaimer_style = ParagraphStyle(
            "DisclaimerStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#dc2626"),
            alignment=1,
        )

        story = []

        # ==================== 1. COVER / HEADER ====================
        story.append(Spacer(1, 10))
        story.append(Paragraph("CRIMEVISION AI", title_style))
        story.append(
            Paragraph("INTELLIGENT MULTIMODAL FORENSIC ANALYSIS PLATFORM", subtitle_style)
        )
        story.append(
            Paragraph("FORENSIC EVIDENCE ANALYSIS & DECISION-SUPPORT REPORT", ParagraphStyle(
                "Sub2", parent=subtitle_style, fontSize=10, textColor=slate_gray
            ))
        )
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=2, color=accent_blue, spaceBefore=4, spaceAfter=14))

        # ==================== 2. CASE INFORMATION ====================
        now_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        case_info_data = [
            [
                Paragraph("<b>Case Number:</b>", body_style),
                Paragraph(str(case_data.get("case_number", "N/A")), body_bold),
                Paragraph("<b>Investigation Status:</b>", body_style),
                Paragraph(str(case_data.get("status", "Open")), body_bold),
            ],
            [
                Paragraph("<b>Case Title:</b>", body_style),
                Paragraph(str(case_data.get("title", "Untitled")), body_bold),
                Paragraph("<b>Lead Investigator:</b>", body_style),
                Paragraph(str(case_data.get("investigator", "Unassigned")), body_bold),
            ],
            [
                Paragraph("<b>Report Generated:</b>", body_style),
                Paragraph(now_utc_str, body_style),
                Paragraph("<b>Total Evidence Files:</b>", body_style),
                Paragraph(str(len(evidence_list)), body_bold),
            ],
        ]
        info_table = Table(case_info_data, colWidths=[1.3 * inch, 2.3 * inch, 1.4 * inch, 2.0 * inch])
        info_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), light_bg),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(info_table)
        story.append(Spacer(1, 14))

        # ==================== 3. EVIDENCE INVENTORY & INTEGRITY ====================
        story.append(Paragraph("1. Forensic Evidence Inventory & Cryptographic Integrity", section_heading))
        story.append(
            Paragraph(
                "Chain of custody integrity is preserved via immutable SHA-256 cryptographic hashes calculated upon evidence ingestion.",
                body_style,
            )
        )
        story.append(Spacer(1, 6))

        inventory_rows = [
            [
                Paragraph("ID", table_header),
                Paragraph("Filename", table_header),
                Paragraph("Type", table_header),
                Paragraph("Size", table_header),
                Paragraph("SHA-256 Hash", table_header),
                Paragraph("Status", table_header),
            ]
        ]
        for ev in evidence_list:
            inventory_rows.append(
                [
                    Paragraph(f"EV-{ev.get('id')}", table_cell),
                    Paragraph(ev.get("filename", "unknown"), table_cell),
                    Paragraph(ev.get("file_type", "").upper(), table_cell),
                    Paragraph(f"{ev.get('file_size', 0)/1024:.1f} KB", table_cell),
                    Paragraph(ev.get("sha256_hash", "")[:24] + "...", table_cell_code),
                    Paragraph(ev.get("analysis_status", "QUEUED"), table_cell),
                ]
            )

        if len(inventory_rows) > 1:
            inv_table = Table(
                inventory_rows,
                colWidths=[0.6 * inch, 1.8 * inch, 0.7 * inch, 0.8 * inch, 2.3 * inch, 0.8 * inch],
            )
            inv_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), header_dark),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(inv_table)
        else:
            story.append(Paragraph("No evidence items registered.", body_style))
        story.append(Spacer(1, 14))

        # ==================== 4. COMPUTER VISION & VISUAL FINDINGS ====================
        story.append(Paragraph("2. Computer Vision & Scene Intelligence", section_heading))
        for ev in evidence_list:
            if ev.get("file_type") in ["image", "video"]:
                meta = ev.get("metadata", {})
                scene_desc = meta.get("scene_description", {}).get("description", "None provided.")
                objs = meta.get("objects_detected", [])
                cat = meta.get("scene_classification", {}).get("primary_category", "unspecified")

                story.append(
                    Paragraph(
                        f"<b>[EV-{ev.get('id')}] {ev.get('filename')}</b> ({ev.get('file_type').upper()}):",
                        body_bold,
                    )
                )
                story.append(
                    Paragraph(
                        f"• <b>Scene Classification (CLIP):</b> {cat.title()}<br/>"
                        f"• <b>Scene Description (BLIP):</b> {scene_desc}<br/>"
                        f"• <b>Detections (RT-DETR):</b> {', '.join(objs) if objs else 'No entities exceeding threshold'}",
                        body_style,
                    )
                )
                story.append(Spacer(1, 4))
        story.append(Spacer(1, 10))

        # ==================== 5. SPEECH & AUDIO FINDINGS ====================
        story.append(Paragraph("3. Multilingual Speech & Auditory Evidence", section_heading))
        if transcripts_list:
            tr_rows = [
                [
                    Paragraph("Time", table_header),
                    Paragraph("Lang", table_header),
                    Paragraph("Confidence", table_header),
                    Paragraph("Transcript Content", table_header),
                ]
            ]
            for tr in transcripts_list:
                tr_rows.append(
                    [
                        Paragraph(f"{tr.get('start_time', 0.0):.1f}s - {tr.get('end_time', 0.0):.1f}s", table_cell),
                        Paragraph(tr.get("language", "en").upper(), table_cell),
                        Paragraph(f"{tr.get('confidence', 1.0)*100:.0f}%", table_cell),
                        Paragraph(f"\"{tr.get('text', '')}\"", table_cell),
                    ]
                )
            tr_table = Table(tr_rows, colWidths=[1.1 * inch, 0.7 * inch, 0.9 * inch, 4.3 * inch])
            tr_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), header_dark),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(tr_table)
        else:
            story.append(Paragraph("No auditory speech transcripts registered.", body_style))
        story.append(Spacer(1, 14))

        # ==================== 6. UNIFIED CHRONOLOGICAL TIMELINE ====================
        story.append(Paragraph("4. Unified Chronological Forensic Timeline", section_heading))
        story.append(
            Paragraph(
                "Chronological fusion of visual frame events, speech events, and scene transitions:",
                body_style,
            )
        )
        story.append(Spacer(1, 6))

        tl_rows = [
            [
                Paragraph("Timestamp", table_header),
                Paragraph("Source", table_header),
                Paragraph("Event Category", table_header),
                Paragraph("Conf", table_header),
                Paragraph("Event Forensic Description", table_header),
            ]
        ]
        for tl in timeline_list:
            tl_rows.append(
                [
                    Paragraph(tl.get("timestamp_str", "undated"), table_cell_code),
                    Paragraph(tl.get("source", "unknown").upper(), table_cell),
                    Paragraph(tl.get("event_type", "").replace("_", " ").title(), table_cell),
                    Paragraph(f"{tl.get('confidence', 1.0)*100:.0f}%", table_cell),
                    Paragraph(tl.get("description", ""), table_cell),
                ]
            )

        if len(tl_rows) > 1:
            tl_table = Table(
                tl_rows,
                colWidths=[1.0 * inch, 0.8 * inch, 1.4 * inch, 0.6 * inch, 3.2 * inch],
            )
            tl_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), header_dark),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(tl_table)
        else:
            story.append(Paragraph("No timeline events generated.", body_style))
        story.append(Spacer(1, 14))

        # ==================== 7. AI REASONING & LIMITATIONS ====================
        story.append(Paragraph("5. AI Synthesis & Uncertainty Limitations", section_heading))
        story.append(
            Paragraph(
                "• <b>Objective Evidence Summary:</b> Multimodal synthesis extracted structured observations across visual and acoustic domains without manual alteration of source files.<br/>"
                "• <b>Identification Boundaries:</b> Bounding box object detections indicate category likelihoods and must not be conflated with positive facial, individual, or vehicle registration identification.<br/>"
                "• <b>Uncertainty Disclosure:</b> Detections below 0.60 confidence require corroborating evidence. Pretrained object detectors reflect dataset statistical distributions and require expert human review.",
                body_style,
            )
        )
        story.append(Spacer(1, 16))

        # ==================== 8. MANDATORY LEGAL DISCLAIMER ====================
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=4, spaceAfter=8))
        story.append(
            Paragraph(
                "FORENSIC DECISION-SUPPORT DISCLAIMER:<br/>"
                "\"This report is an AI-assisted analytical summary and should not be treated as a definitive "
                "determination of identity, intent, guilt, or legal responsibility. Findings should be "
                "independently reviewed by qualified investigators or forensic professionals.\"",
                disclaimer_style,
            )
        )

        doc.build(story)

        # Calculate report file hash
        report_hash = calculate_sha256(pdf_path)

        return {
            "filename": output_filename,
            "path": str(pdf_path),
            "sha256_hash": report_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

from io import BytesIO
import re
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
)

SECTION_NAMES = {
    "summary", "professional summary", "profile", "objective",
    "skills", "technical skills", "core skills", "key skills",
    "experience", "work experience", "professional experience",
    "employment", "projects", "academic projects", "personal projects",
    "education", "certifications", "certificates", "achievements",
    "publications", "awards", "internships", "volunteer experience",
    "languages", "interests", "activities", "coursework"
}

def render_text(original, changes):
    text = original
    # Longest original snippets first avoids a shorter replacement consuming part
    # of a longer approved change.
    approved = [c for c in changes if c.status == "approved" and c.original_text]
    approved.sort(key=lambda c: len(c.original_text), reverse=True)
    for c in approved:
        text = text.replace(c.original_text, c.proposed_text, 1)
    return text

def _clean_lines(text):
    lines = []
    for raw in text.replace("\r", "").split("\n"):
        line = re.sub(r"[\t ]+", " ", raw).strip()
        if line:
            lines.append(line)
    return lines

def _heading(line):
    normalized = re.sub(r"[:\s]+$", "", line.lower()).strip()
    return normalized in SECTION_NAMES or (
        len(normalized) < 32 and normalized.isupper() and any(ch.isalpha() for ch in normalized)
    )

def _name_line(line):
    return len(line) <= 64 and not any(mark in line for mark in ("@", "http://", "https://")) and len(line.split()) <= 6

def _is_bullet(line):
    return bool(re.match(r"^(?:[•●▪◦*\-]|\d+[.)])\s+", line))

def _bullet_text(line):
    return re.sub(r"^(?:[•●▪◦*\-]|\d+[.)])\s+", "", line).strip()

def docx_bytes(text):
    d = Document()
    sec = d.sections[0]
    sec.top_margin = Inches(0.55)
    sec.bottom_margin = Inches(0.55)
    sec.left_margin = Inches(0.68)
    sec.right_margin = Inches(0.68)

    normal = d.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor(48, 57, 69)
    normal.paragraph_format.space_after = Pt(3)
    normal.paragraph_format.line_spacing = 1.05

    title_style = d.styles["Title"]
    title_style.font.name = "Aptos Display"
    title_style.font.size = Pt(23)
    title_style.font.bold = True
    title_style.font.color.rgb = RGBColor(24, 55, 82)
    title_style.paragraph_format.space_after = Pt(2)

    for style_name in ("Heading 1", "Heading 2"):
        st = d.styles[style_name]
        st.font.name = "Aptos Display"
        st.font.bold = True
        st.font.color.rgb = RGBColor(24, 91, 105)
        st.font.size = Pt(11 if style_name == "Heading 1" else 10)
        st.paragraph_format.space_before = Pt(9)
        st.paragraph_format.space_after = Pt(3)
        st.paragraph_format.keep_with_next = True

    lines = _clean_lines(text)
    if not lines:
        d.add_paragraph("Resume")
    else:
        first_idx = next((i for i, line in enumerate(lines) if _name_line(line)), 0)
        name = lines[first_idx]
        p = d.add_paragraph(style="Title")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(name)
        for i, line in enumerate(lines):
            if i == first_idx:
                continue
            if i < first_idx + 4 and ("@" in line or "linkedin" in line.lower() or "github" in line.lower() or re.search(r"\+?\d[\d ()-]{7,}", line)):
                p = d.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run(line)
                run.font.size = Pt(8.5)
                run.font.color.rgb = RGBColor(85, 101, 116)
                continue
            if _heading(line):
                p = d.add_paragraph(style="Heading 1")
                p.add_run(line.rstrip(":"))
                pPr = p._p.get_or_add_pPr()
                from docx.oxml import OxmlElement
                from docx.oxml.ns import qn
                borders = OxmlElement("w:pBdr")
                bottom = OxmlElement("w:bottom")
                bottom.set(qn("w:val"), "single")
                bottom.set(qn("w:sz"), "5")
                bottom.set(qn("w:space"), "2")
                bottom.set(qn("w:color"), "B9D4D9")
                borders.append(bottom)
                pPr.append(borders)
            elif _is_bullet(line):
                p = d.add_paragraph(style="List Bullet")
                p.paragraph_format.left_indent = Inches(0.2)
                p.paragraph_format.first_line_indent = Inches(-0.12)
                p.add_run(_bullet_text(line))
            else:
                p = d.add_paragraph()
                p.add_run(line)
    b = BytesIO()
    d.save(b)
    return b.getvalue()

def pdf_bytes(text):
    b = BytesIO()
    doc = SimpleDocTemplate(
        b, pagesize=letter, rightMargin=0.62*inch, leftMargin=0.62*inch,
        topMargin=0.52*inch, bottomMargin=0.52*inch,
        title="Resume", author="ResumePilot AI"
    )
    navy = colors.HexColor("#183752")
    teal = colors.HexColor("#1B6975")
    grey = colors.HexColor("#536171")
    base = getSampleStyleSheet()
    name_style = ParagraphStyle(
        "ResumeName", parent=base["Title"], fontName="Helvetica-Bold",
        fontSize=21, leading=24, textColor=navy, alignment=TA_CENTER,
        spaceAfter=4
    )
    contact_style = ParagraphStyle(
        "ResumeContact", parent=base["Normal"], fontName="Helvetica",
        fontSize=8.5, leading=11, textColor=grey, alignment=TA_CENTER,
        spaceAfter=3
    )
    section_style = ParagraphStyle(
        "ResumeSection", parent=base["Heading2"], fontName="Helvetica-Bold",
        fontSize=10.5, leading=13, textColor=teal, spaceBefore=9,
        spaceAfter=3, keepWithNext=True
    )
    body_style = ParagraphStyle(
        "ResumeBody", parent=base["BodyText"], fontName="Helvetica",
        fontSize=9, leading=12, textColor=colors.HexColor("#303945"),
        spaceAfter=3
    )
    bullet_style = ParagraphStyle(
        "ResumeBullet", parent=body_style, leftIndent=12, firstLineIndent=-8,
        bulletIndent=0, spaceAfter=2.5
    )
    story = []
    lines = _clean_lines(text)
    if not lines:
        lines = ["Resume"]
    first_idx = next((i for i, line in enumerate(lines) if _name_line(line)), 0)
    story.append(Paragraph(escape(lines[first_idx]), name_style))
    for i, line in enumerate(lines):
        if i == first_idx:
            continue
        if i < first_idx + 4 and ("@" in line or "linkedin" in line.lower() or "github" in line.lower() or re.search(r"\+?\d[\d ()-]{7,}", line)):
            story.append(Paragraph(escape(line), contact_style))
            continue
        if _heading(line):
            story.append(KeepTogether([
                Spacer(1, 2),
                Paragraph(escape(line.rstrip(":").title()), section_style),
                HRFlowable(width="100%", thickness=0.55, color=colors.HexColor("#B9D4D9"), spaceAfter=4)
            ]))
        elif _is_bullet(line):
            story.append(Paragraph("• " + escape(_bullet_text(line)), bullet_style))
        else:
            story.append(Paragraph(escape(line), body_style))
    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#E2E8ED"))
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, 0.36*inch, letter[0]-doc.rightMargin, 0.36*inch)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(grey)
        canvas.drawRightString(letter[0]-doc.rightMargin, 0.22*inch, f"Page {doc_obj.page}")
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return b.getvalue()

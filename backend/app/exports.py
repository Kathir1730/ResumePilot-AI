from io import BytesIO
from xml.sax.saxutils import escape
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def render_text(original, changes):
    text = original
    for c in changes:
        if c.status == "approved" and c.original_text:
            text = text.replace(c.original_text, c.proposed_text, 1)
    return text

def docx_bytes(text):
    d = Document()
    for line in text.splitlines():
        if line.strip(): d.add_paragraph(line.strip())
    b = BytesIO(); d.save(b); return b.getvalue()

def pdf_bytes(text):
    b = BytesIO(); d = SimpleDocTemplate(b, pagesize=letter, rightMargin=48, leftMargin=48, topMargin=45, bottomMargin=45)
    styles = getSampleStyleSheet(); story = []
    for line in text.splitlines():
        if line.strip(): story += [Paragraph(escape(line.strip()), styles["BodyText"]), Spacer(1, 5)]
    d.build(story); return b.getvalue()

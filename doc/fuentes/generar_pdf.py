#!/usr/bin/env python3
"""Genera doc/Taller5_ASM_Bareiss_XS3.pdf (y las figuras en doc/figuras).

Requiere: reportlab, matplotlib (solo por las fuentes DejaVu) y Graphviz (dot).
Uso (desde la raiz del repositorio):  python3 doc/fuentes/generar_pdf.py
"""
import os
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Preformatted, Spacer, Table,
                                TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(RAIZ / "sim"))
import diagramas                                   # noqa: E402

FIG = RAIZ / "doc" / "figuras"
SALIDA = RAIZ / "doc" / "Taller5_ASM_Bareiss_XS3.pdf"

# ---------------------------------------------------------------------------
# Fuentes y estilos
# ---------------------------------------------------------------------------
TTF = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DV", str(TTF / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", str(TTF / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DV-I", str(TTF / "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("DV-BI", str(TTF / "DejaVuSans-BoldOblique.ttf")))
pdfmetrics.registerFont(TTFont("DVM", str(TTF / "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")

AZUL = colors.HexColor("#1f3d7a")
GRIS = colors.HexColor("#f2f2f2")

E = {
    "titulo": ParagraphStyle("titulo", fontName="DV-B", fontSize=20, leading=26, alignment=TA_CENTER,
                             textColor=AZUL, spaceAfter=10),
    "subtitulo": ParagraphStyle("subtitulo", fontName="DV", fontSize=12, leading=17, alignment=TA_CENTER),
    "h1": ParagraphStyle("h1", fontName="DV-B", fontSize=15, leading=20, textColor=AZUL,
                         spaceBefore=12, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="DV-B", fontSize=12, leading=16, textColor=AZUL,
                         spaceBefore=9, spaceAfter=4),
    "p": ParagraphStyle("p", fontName="DV", fontSize=9.6, leading=13.6, spaceAfter=5),
    "vi": ParagraphStyle("vi", fontName="DV", fontSize=9.6, leading=13.4, leftIndent=14,
                         bulletIndent=4, spaceAfter=2),
    "celda": ParagraphStyle("celda", fontName="DV", fontSize=8.3, leading=10.6),
    "celda_m": ParagraphStyle("celda_m", fontName="DV", fontSize=8.0, leading=10.0),
    "celda_b": ParagraphStyle("celda_b", fontName="DV-B", fontSize=8.3, leading=10.6, textColor=colors.white),
    "pie": ParagraphStyle("pie", fontName="DV-I", fontSize=8.5, leading=11, alignment=TA_CENTER,
                          spaceBefore=3, spaceAfter=8, textColor=colors.HexColor("#444444")),
    "codigo": ParagraphStyle("codigo", fontName="DVM", fontSize=7.6, leading=9.6, leftIndent=6,
                             backColor=GRIS, borderPadding=5, spaceBefore=4, spaceAfter=8),
    "anexo": ParagraphStyle("anexo", fontName="DVM", fontSize=6.3, leading=7.6),
    "nota": ParagraphStyle("nota", fontName="DV", fontSize=9.2, leading=13, backColor=colors.HexColor("#fff4dd"),
                           borderColor=colors.HexColor("#d9822b"), borderWidth=0.8, borderPadding=7,
                           spaceBefore=6, spaceAfter=10),
    "toc1": ParagraphStyle("toc1", fontName="DV-B", fontSize=9.2, leading=11.5, leftIndent=10, spaceBefore=1),
    "toc2": ParagraphStyle("toc2", fontName="DV", fontSize=8.5, leading=10, leftIndent=26),
    "h1_sin_indice": ParagraphStyle("h1_sin_indice", fontName="DV-B", fontSize=15, leading=20,
                                    textColor=colors.HexColor("#1f3d7a"), spaceAfter=8),
}


def fmt(t):
    """Escapa el texto y traduce marcas simples: [b] [i] [c] [sup] [sub] [br]."""
    t = escape(t)
    reemplazos = {
        "[b]": "<b>", "[/b]": "</b>", "[i]": "<i>", "[/i]": "</i>",
        "[c]": '<font name="DVM">', "[/c]": "</font>",
        "[sup]": "<super>", "[/sup]": "</super>", "[sub]": "<sub>", "[/sub]": "</sub>",
        "[br]": "<br/>",
    }
    for a, b in reemplazos.items():
        t = t.replace(a, b)
    return t


def P(t, estilo="p"):
    return Paragraph(fmt(t), E[estilo])


def viñetas(items):
    return [Paragraph(fmt(x), E["vi"], bulletText="•") for x in items]


def tabla(filas, anchos, cabecera=True, fondo=AZUL):
    datos = []
    for r, fila in enumerate(filas):
        est = "celda_b" if (cabecera and r == 0) else "celda"
        datos.append([Paragraph(fmt(str(c)), E[est]) for c in fila])
    t = Table(datos, colWidths=[w * inch for w in anchos], repeatRows=1 if cabecera else 0)
    estilo = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    if cabecera:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), fondo))
    for r in range(1 if cabecera else 0, len(filas)):
        if r % 2 == 0:
            estilo.append(("BACKGROUND", (0, r), (-1, r), GRIS))
    t.setStyle(TableStyle(estilo))
    return t


def figura(nombre, pie, max_ancho=6.9, max_alto=8.3):
    from PIL import Image as PILImage
    ruta = FIG / f"{nombre}.png"
    w, h = PILImage.open(ruta).size
    escala = min(max_ancho * inch / w, max_alto * inch / h, 72.0 / 170 * 1.0)
    img = Image(str(ruta), width=w * escala, height=h * escala)
    return KeepTogether([img, P(pie, "pie")])


def codigo(t):
    return Preformatted(t, E["codigo"])


class Documento(BaseDocTemplate):
    def __init__(self, archivo):
        super().__init__(str(archivo), pagesize=letter, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                         topMargin=0.75 * inch, bottomMargin=0.75 * inch,
                         title="Taller 5 - ASM Bareiss + XS3", author="Equipo Taller 5")
        marco = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="m")
        self.addPageTemplates([PageTemplate(id="p", frames=[marco], onPage=self.pie)])

    @staticmethod
    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("DV", 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.8 * inch, 0.45 * inch, "Taller 5 · Determinante por Bareiss con salida BCD (XS3)")
        canvas.drawRightString(letter[0] - 0.8 * inch, 0.45 * inch, f"Página {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ("h1", "h2"):
            nivel = 0 if f.style.name == "h1" else 1
            texto = f.getPlainText()
            clave = f"s{self.seq.nextf('sec')}"
            self.canv.bookmarkPage(clave)
            self.canv.addOutlineEntry(texto, clave, level=nivel)
            self.notify("TOCEntry", (nivel, texto, self.page, clave))


# ---------------------------------------------------------------------------
# Datos calculados
# ---------------------------------------------------------------------------
def traza_xs3(valor):
    """Reproduce los estados S22-S25 para 'valor' (32 bits)."""
    bcd = [0] * 10
    b = valor
    filas = []

    def reg():
        return " ".join(f"{bcd[d]:04b}" for d in (2, 1, 0))

    def ventana():
        return f"{(b >> 23) & 0x1FF:09b}"

    for cont in range(32):
        bcd[0] = (bcd[0] & 0b1110) | ((b >> 31) & 1)
        if cont >= 23:
            filas.append([str(cont), "S23 (2)", reg(), ventana(),
                          "último PASO 2 = PASO 5, va a S26" if cont == 31 else ""])
        if cont == 31:
            break
        notas = []
        for d in range(10):
            if bcd[d] > 4:
                notas.append(f"BCD({d}) = {bcd[d]:04b} > 0100: +3 = {bcd[d] + 3:04b}")
                bcd[d] += 3
        if cont >= 23:
            filas.append(["", "S24 (3)", reg(), ventana(), "; ".join(notas) if notas else "ningún dígito > 4"])
        acarreo = 0
        for d in range(10):
            nuevo = ((bcd[d] << 1) | acarreo) & 0xF
            acarreo = (bcd[d] >> 3) & 1
            bcd[d] = nuevo
        b = (b << 1) & 0xFFFFFFFF
        if cont >= 23:
            filas.append(["", "S25 (4)", reg(), ventana(), "corrimiento a la izquierda"])
    return filas, bcd


if __name__ == "__main__":
    for nombre, f in diagramas.DIAGRAMAS.items():
        diagramas.render(nombre, f(), FIG)
    for dot in FIG.glob("*.dot"):
        dot.unlink()
    from contenido_doc import contenido
    doc = Documento(SALIDA)
    doc.multiBuild(contenido())
    print("PDF generado:", SALIDA)

#!/usr/bin/env python3
"""Genera el informe del Taller 5 (informe/Informe_Taller5_Bareiss.docx).

Las figuras se toman de informe/figuras (generar_figuras.py y ondas.py). El
texto marcado con ==...== queda resaltado en amarillo: son datos que se deben
revisar con el reporte nuevo de ISE. El PDF se saca con LibreOffice:

  soffice --headless --convert-to pdf --outdir informe informe/Informe_Taller5_Bareiss.docx
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_COLOR_INDEX
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(RAIZ / "sim"))

import modelo_referencia as M  # noqa: E402
import uc_cd as U  # noqa: E402

FIG = RAIZ / "informe" / "figuras"
SALIDA = RAIZ / "informe" / "Informe_Taller5_Bareiss.docx"
FUENTE = "Calibri"
MONO = "Courier New"
AZUL = RGBColor(0x1F, 0x38, 0x64)
ANCHO = 16.5        # ancho útil en cm (carta, márgenes de 2,5 cm)

ESTUDIANTES = [
    ("Juan Felipe Delgado Arciniegas", "20241005088", "jfdelgadoa@udistrital.edu.co"),
    ("Juan Camilo Cupasachoa Gómez", "20241005087", "jccupasachoag@udistrital.edu.co"),
    ("Sergio Gómez Vera", "20241005063", "segomezv@udistrital.edu.co"),
]


# ===========================================================================
# Utilidades de python-docx
# ===========================================================================
def fuente_run(run, nombre=FUENTE, tam=None, negrita=None, cursiva=None, color=None):
    run.font.name = nombre
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), nombre)
    if tam:
        run.font.size = Pt(tam)
    if negrita is not None:
        run.bold = negrita
    if cursiva is not None:
        run.italic = cursiva
    if color is not None:
        run.font.color.rgb = color


def sombrear(celda, color):
    tcpr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcpr.append(shd)


def fila_encabezado(fila):
    trpr = fila._tr.get_or_add_trPr()
    for etiqueta in ("w:tblHeader", "w:cantSplit"):
        e = OxmlElement(etiqueta)
        e.set(qn("w:val"), "true")
        trpr.append(e)


def sin_partir(fila):
    trpr = fila._tr.get_or_add_trPr()
    e = OxmlElement("w:cantSplit")
    e.set(qn("w:val"), "true")
    trpr.append(e)


def margenes_celda(tabla, cm=0.1):
    tblpr = tabla._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for lado in ("left", "right"):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:w"), str(int(cm * 567)))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblpr.append(mar)


def anchos_tabla(tabla, anchos):
    """Anchos de columna en la grilla (LibreOffice usa tblGrid) y en cada celda."""
    tbl = tabla._tbl
    cols = tbl.tblGrid.findall(qn("w:gridCol"))
    for c, w in zip(cols, anchos):
        c.set(qn("w:w"), str(int(w * 567)))
    tblpr = tbl.tblPr
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    tblpr.append(lay)
    tw = tblpr.find(qn("w:tblW"))
    if tw is None:
        tw = OxmlElement("w:tblW")
        tblpr.append(tw)
    tw.set(qn("w:w"), str(int(sum(anchos) * 567)))
    tw.set(qn("w:type"), "dxa")
    for fila in tabla.rows:
        for k, c in enumerate(fila.cells):
            c.width = Cm(anchos[k])
    ordenar_tblpr(tabla)


ORDEN_TBLPR = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize",
               "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
               "tblCaption", "tblDescription"]


def ordenar_tblpr(tabla):
    """Word exige el orden del esquema dentro de w:tblPr."""
    tblpr = tabla._tbl.tblPr
    hijos = list(tblpr)
    for h in hijos:
        tblpr.remove(h)
    clave = {qn(f"w:{n}"): k for k, n in enumerate(ORDEN_TBLPR)}
    for h in sorted(hijos, key=lambda e: clave.get(e.tag, 99)):
        tblpr.append(h)


def campo_pagina(parrafo):
    for tipo, texto in (("begin", None), (None, " PAGE "), ("separate", None), (None, "1"), ("end", None)):
        r = OxmlElement("w:r")
        if tipo:
            f = OxmlElement("w:fldChar")
            f.set(qn("w:fldCharType"), tipo)
            r.append(f)
        elif texto.strip() == "PAGE":
            t = OxmlElement("w:instrText")
            t.set(qn("xml:space"), "preserve")
            t.text = texto
            r.append(t)
        else:
            t = OxmlElement("w:t")
            t.text = texto
            r.append(t)
        parrafo._p.append(r)


MARCAS = re.compile(r"(==.+?==|\*\*.+?\*\*|\*.+?\*|`.+?`|\^.+?\^|_\{.+?\})")


def texto_rico(parrafo, texto, tam=None, color=None):
    """**negrita**, *cursiva*, `código`, ^superíndice^, _{subíndice}."""
    for parte in MARCAS.split(texto):
        if not parte:
            continue
        if parte.startswith("=="):
            r = parrafo.add_run(parte[2:-2])
            fuente_run(r, tam=tam, color=color)
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
        elif parte.startswith("**"):
            r = parrafo.add_run(parte[2:-2])
            fuente_run(r, tam=tam, negrita=True, color=color)
        elif parte.startswith("`"):
            r = parrafo.add_run(parte[1:-1])
            fuente_run(r, MONO, tam=(tam or 11) - 1.5, color=color)
        elif parte.startswith("^"):
            r = parrafo.add_run(parte[1:-1])
            fuente_run(r, tam=tam, color=color)
            r.font.superscript = True
        elif parte.startswith("_{"):
            r = parrafo.add_run(parte[2:-1])
            fuente_run(r, tam=tam, color=color)
            r.font.subscript = True
        elif parte.startswith("*"):
            r = parrafo.add_run(parte[1:-1])
            fuente_run(r, tam=tam, cursiva=True, color=color)
        else:
            r = parrafo.add_run(parte)
            fuente_run(r, tam=tam, color=color)


# ===========================================================================
# Documento
# ===========================================================================
class Informe:
    def __init__(self):
        self.num = {}
        self.cont = {"Figura": 0, "Tabla": 0}

    # -- numeración (dos pasadas) ------------------------------------------
    def _numerar(self, tipo, clave):
        self.cont[tipo] += 1
        self.num[clave] = f"{tipo} {self.cont[tipo]}"
        return self.num[clave]

    def F(self, clave):
        return self.num.get(clave, "Figura ?")

    def T(self, clave):
        return self.num.get(clave, "Tabla ?")

    # -- bloques -----------------------------------------------------------
    def nuevo(self):
        self.cont = {"Figura": 0, "Tabla": 0}
        d = Document()
        sec = d.sections[0]
        sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
        for lado in ("left_margin", "right_margin"):
            setattr(sec, lado, Cm(2.5))
        sec.top_margin, sec.bottom_margin = Cm(2.3), Cm(2.3)
        st = d.styles["Normal"]
        st.font.name = FUENTE
        st.font.size = Pt(11)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.line_spacing = 1.12
        for nivel, tam, color in ((1, 14, AZUL), (2, 12, RGBColor(0x2E, 0x55, 0x97)), (3, 11, RGBColor(0x33, 0x33, 0x33))):
            h = d.styles[f"Heading {nivel}"]
            h.font.name = FUENTE
            h.font.size = Pt(tam)
            h.font.bold = True
            h.font.italic = False
            h.font.color.rgb = color
            rpr = h.element.get_or_add_rPr()
            rf = rpr.find(qn("w:rFonts"))
            if rf is None:
                rf = OxmlElement("w:rFonts")
                rpr.insert(0, rf)
            for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                rf.set(qn(a), FUENTE)
            for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
                if rf.get(qn(a)) is not None:
                    del rf.attrib[qn(a)]
            h.paragraph_format.space_before = Pt(14 if nivel == 1 else 10)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.keep_with_next = True
        pie = sec.footer.paragraphs[0]
        pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
        campo_pagina(pie)
        enc = sec.header.paragraphs[0]
        enc.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = enc.add_run("Taller 5 · Determinante por Bareiss con visualización XS3")
        fuente_run(r, tam=8.5, cursiva=True, color=RGBColor(0x80, 0x80, 0x80))
        self.d = d
        return d

    def H1(self, t, pagina_nueva=False):
        h = self.d.add_heading(t, 1)
        h.paragraph_format.page_break_before = pagina_nueva
        return h

    def H2(self, t):
        self.d.add_heading(t, 2)

    def H3(self, t):
        self.d.add_heading(t, 3)

    def P(self, t, alin=WD_ALIGN_PARAGRAPH.JUSTIFY, tam=None, antes=None, despues=None, sangria=None):
        p = self.d.add_paragraph()
        p.alignment = alin
        texto_rico(p, t, tam)
        if antes is not None:
            p.paragraph_format.space_before = Pt(antes)
        if despues is not None:
            p.paragraph_format.space_after = Pt(despues)
        if sangria is not None:
            p.paragraph_format.left_indent = Cm(sangria)
        return p

    def lista(self, items, numerada=False):
        """Viñetas, o lista numerada desde 1 (el número se escribe en el texto para
        que cada lista empiece en 1)."""
        for k, t in enumerate(items, 1):
            if numerada:
                p = self.d.add_paragraph()
                pf = p.paragraph_format
                pf.left_indent = Cm(0.75)
                pf.first_line_indent = Cm(-0.5)
                pf.tab_stops.add_tab_stop(Cm(0.75))
                texto_rico(p, f"{k}.\t{t}")
            else:
                p = self.d.add_paragraph(style="List Bullet")
                texto_rico(p, t)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(3)

    def salto(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def seccion(self, margen):
        """Sección nueva (página nueva) con márgenes laterales de 'margen' cm."""
        sec = self.d.add_section(WD_SECTION.NEW_PAGE)
        sec.left_margin = sec.right_margin = Cm(margen)
        sec.top_margin = sec.bottom_margin = Cm(min(2.3, margen + 0.2))
        return sec

    def leyenda(self, tipo, clave, texto):
        etq = self._numerar(tipo, clave)
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(10 if tipo == "Figura" else 4)
        if tipo == "Tabla":
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(6)
        r = p.add_run(etq + ". ")
        fuente_run(r, tam=9.5, negrita=True)
        texto_rico(p, texto, tam=9.5)
        return p

    def figura(self, clave, archivo, texto, ancho=ANCHO, alto_max=21.0, nativo=True):
        ruta = FIG / archivo
        w, h = Image.open(ruta).size
        ancho_nat = w / 3 * 2.54 / 96 * 1.0            # PNG de draw.io a escala 3
        a = min(ancho, ancho_nat * 1.05) if nativo else ancho
        if a * h / w > alto_max:
            a = alto_max * w / h
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_after = Pt(2)
        p.add_run().add_picture(str(ruta), width=Cm(a))
        self.leyenda("Figura", clave, texto)

    def hueco(self, clave, texto, indicacion, alto=6.5):
        """Recuadro para pegar una captura de ISE."""
        t = self.d.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.style = "Table Grid"
        c = t.cell(0, 0)
        anchos_tabla(t, [14])
        sombrear(c, "F2F2F2")
        tr = t.rows[0]._tr
        trpr = tr.get_or_add_trPr()
        alto_el = OxmlElement("w:trHeight")
        alto_el.set(qn("w:val"), str(int(alto * 567)))
        alto_el.set(qn("w:hRule"), "atLeast")
        trpr.append(alto_el)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(alto * 12)
        p.paragraph_format.keep_with_next = True
        texto_rico(p, indicacion, tam=10, color=RGBColor(0x80, 0x80, 0x80))
        self.leyenda("Figura", clave, texto)

    def tabla(self, clave, texto, enc, filas, anchos, tam=9, mono=(), centrar=(), negrita_col0=False,
              colores=None):
        if texto:
            self.leyenda("Tabla", clave, texto)
        t = self.d.add_table(rows=1, cols=len(enc))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        margenes_celda(t, 0.08)
        fila_encabezado(t.rows[0])
        for k, e in enumerate(enc):
            c = t.rows[0].cells[k]
            sombrear(c, "DAE8FC")
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            texto_rico(p, f"**{e}**" if "**" not in e else e, tam=tam)
        for ifila, fila in enumerate(filas):
            celdas = t.add_row().cells
            sin_partir(t.rows[-1])
            for k, v in enumerate(fila):
                p = celdas[k].paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                if k in centrar:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                v = str(v)
                if k in mono:
                    r = p.add_run(v)
                    fuente_run(r, MONO, tam=tam - 1)
                else:
                    texto_rico(p, f"**{v}**" if (negrita_col0 and k == 0 and v) else v, tam=tam)
                if colores and colores(ifila, k):
                    sombrear(celdas[k], colores(ifila, k))
        anchos_tabla(t, anchos)
        if len(filas) <= 18:
            for fila in t.rows[:-1]:
                for c in fila.cells:
                    for p in c.paragraphs:
                        p.paragraph_format.keep_with_next = True
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)
        return t

    def codigo(self, texto, tam=8, titulo=None):
        t = self.d.add_table(rows=1, cols=1)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        c = t.cell(0, 0)
        anchos_tabla(t, [ANCHO])
        sombrear(c, "F7F7F7")
        lineas = texto.rstrip("\n").split("\n")
        p = c.paragraphs[0]
        for k, linea in enumerate(lineas):
            if k:
                p = c.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(linea if linea else " ")
            fuente_run(r, MONO, tam=tam)
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)


# ===========================================================================
# Datos que se calculan
# ===========================================================================
def matriz_txt(a):
    return "; ".join(" ".join(str(x) for x in f) for f in a)


def transiciones(filas):
    """Transiciones de la FSM como las cuenta XST: se juntan los caminos que solo
    cambian salidas condicionales y van al mismo estado."""
    total = 0
    for lista in filas.values():
        usadas = set()
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                c1, s1, _ = lista[i]
                c2, s2, _ = lista[j]
                dif = [k for k in set(c1) & set(c2) if c1[k] != c2[k]]
                if len(dif) == 1 and s1 != s2:
                    usadas.add(dif[0])
        total += len({(tuple(sorted((k, v) for k, v in c.items() if k in usadas)), s) for c, s, _ in lista})
    return total


def ciclos_tb():
    """Ciclos hasta final = 1 que midió tb_procesador.vhd (sim/resultado_ghdl.txt)."""
    texto = (RAIZ / "sim" / "resultado_ghdl.txt").read_text(encoding="utf-8")
    res = {}
    for bloque in re.split(r"== Matriz ", texto)[1:]:
        m = re.search(r"Corrida 1: final = 1 en (\d+) ciclos", bloque)
        if m:
            res[int(bloque.split()[0])] = int(m.group(1))
    return res


def miles(n):
    return f"{n:,}".replace(",", " ")


# Señales de estado del procesador: (nombre, pregunta del ASM, estados)
ESTADO_P = [
    ("inicio", "INICIO (entrada externa)", "S0, S13"),
    ("z_b", "RAM(K,K) = 0", "S2"),
    ("z_a", "RAM(I,K) = 0", "S3"),
    ("i_n", "I = N", "S1, S3, S12"),
    ("j_n", "J = N", "S1, S5, S12"),
    ("k1_n", "K + 1 = N", "S11, S12"),
    ("ms", "R(49) = S(49)", "S11"),
    ("sg", "SIGNO = 1", "S11"),
    ("rt", "R = T", "S12"),
    ("sq", "SQ", "S12"),
]
ESTADO_V = [
    ("final", "FINAL (salida del procesador)", "X0"),
    ("val_neg", "VAL(31)", "X0"),
    ("cont_31", "CONT = 31", "X2"),
    ("dig_4", "DÍGITO(D) > 4", "X3"),
    ("d_9", "D = 9", "X3"),
]


# ===========================================================================
# Contenido
# ===========================================================================
def contenido(inf):
    d = inf.nuevo()
    ciclos = ciclos_tb()
    n_trans = transiciones(U.FILAS_P)
    n_trans_v = transiciones(U.FILAS_V)
    det1, piv1, _ = M.bareiss(M.MATRICES[1])
    det2, piv2, _ = M.bareiss(M.MATRICES[2])
    det3, piv3, _ = M.bareiss(M.MATRICES[3])

    # ---------------------------------------------------------------- título
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    fuente_run(p.add_run("Universidad Distrital Francisco José de Caldas · Análisis y Diseño de Microprocesadores"),
               tam=10, color=RGBColor(0x55, 0x55, 0x55))
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(8)
    fuente_run(p.add_run("Taller 5: Determinante de una matriz por el algoritmo de Bareiss con visualización "
                         "decimal (XS3)"), tam=15, negrita=True, color=AZUL)
    for nombre, codigo, correo in ESTUDIANTES:
        q = d.add_paragraph(style="List Bullet")
        q.paragraph_format.space_after = Pt(1)
        fuente_run(q.add_run(f"{nombre} – {codigo} – "), tam=10.5, cursiva=True)
        fuente_run(q.add_run(correo), tam=10.5, cursiva=True, color=RGBColor(0x1F, 0x4E, 0x9A))
    inf.P("Profesor: Ing. Gaona · Bogotá D. C., noviembre de 2026", tam=10, antes=4)

    inf.P("El problema planteado solicita el diseño de un microprocesador dedicado que calcule el determinante de "
          "una matriz cuadrada de 2 × 2 a 5 × 5 con el algoritmo de Bareiss y que muestre el resultado en decimal "
          "en el display de la tarjeta Nexys A7-100T. En cada paso *k* = 1 … *n* − 1, y para cada *i*, *j* = "
          "*k* + 1 … *n*, el algoritmo calcula:")
    inf.P("a(i,j) ← [ a(k,k) · a(i,j) − a(i,k) · a(k,j) ] / p", alin=WD_ALIGN_PARAGRAPH.CENTER, tam=12.5)
    inf.P("donde *p* = 1 en el primer paso y *p* = a(k−1,k−1) en los demás. Todas las divisiones son exactas, así "
          "que se trabaja solo con enteros, y al final a(n,n) es el determinante. La matriz está en una ROM: la "
          "posición 00h tiene el tamaño *n* y desde la 01h están los elementos por columnas (a11, a21, …), en "
          "complemento a 2 de 6 bits. Además del determinante, el sistema guarda los pivotes a(1,1), …, "
          "a(n−1,n−1) y a(n,n) = det, y con los switches SW2..SW0 (`DIR_P`) se elige cuál se muestra.")
    inf.P("Restricciones del taller y del curso: un solo multiplicador y un solo sumador/restador para las "
          "operaciones de Bareiss; división por restas sucesivas, sin valor absoluto; memoria RAM con el modelo "
          "del curso (`RAM_memory.vhd`) sin cambios; solo tipos `std_logic` y `std_logic_vector`, con la librería "
          "`std_logic_unsigned` únicamente en la RAM; y descripción en alto nivel con el estilo de los ejemplos "
          "`ASM_Sumax` y `ASM_contador_unos`.")

    # =========================================================== planteamiento
    inf.H1("Planteamiento general de la solución")
    inf.H2("1. Caja negra")
    inf.P(f"El primer paso fue definir la caja negra del circuito que se implementa en la FPGA "
          f"({inf.F('cn_sis')}).")
    inf.figura("cn_sis", "caja_negra_sistema.png", "Caja negra del circuito a implementar en la FPGA "
               "(entidad `det_bareiss`)", ancho=15)
    inf.P(f"Las entradas son el reloj de 100 MHz (`CLK`), el reinicio (`RST`, botón BTNU), el botón de inicio "
          f"(`INICIO`, BTNC) y los tres switches `DIR_P` que eligen el valor que se muestra: 0 para el "
          f"determinante y 1 a *n* para el pivote *k*. Los datos no entran por switches porque la matriz está "
          f"guardada en la ROM. Las salidas son los segmentos `SEG` y los ánodos `AN` del display de 8 dígitos, el "
          f"punto decimal `DP` (siempre apagado), `FINAL` (LED LD0), que indica que el cálculo terminó, y "
          f"`DESBORDE` (LED LD1), que se enciende si el valor mostrado tiene más de 7 dígitos. La {inf.T('pines')} "
          f"da los pines de la tarjeta.")
    inf.tabla("pines", "Puertos del sistema y pines de la Nexys A7-100T (archivo `nexys_a7.ucf`)",
              ["Puerto", "Dir.", "Bits", "Pines", "Elemento de la tarjeta"],
              [["CLK", "E", "1", "E3", "Reloj de 100 MHz"],
               ["RST", "E", "1", "M18", "BTNU"],
               ["INICIO", "E", "1", "N17", "BTNC"],
               ["DIR_P[2:0]", "E", "3", "J15, L16, M13", "SW0, SW1, SW2"],
               ["SEG[6:0]", "S", "7", "T10, R10, K16, K13, P15, T11, L18", "Segmentos CA … CG"],
               ["AN[7:0]", "S", "8", "J17, J18, T9, J14, P14, T14, K2, U13", "Ánodos (AN7 = signo)"],
               ["DP", "S", "1", "H15", "Punto decimal"],
               ["FINAL", "S", "1", "H17", "LD0"],
               ["DESBORDE", "S", "1", "K15", "LD1"]],
              [2.4, 1.0, 1.0, 6.6, 5.5], tam=9, centrar=(1, 2), negrita_col0=True)
    inf.P(f"Dentro de esa caja está el microprocesador dedicado de Bareiss, cuya caja negra se muestra en la "
          f"{inf.F('cn_proc')}. Sus entradas son `clk`, `rst`, `inicio` (un pulso de un ciclo que entrega el "
          f"antirrebote) y `dir_p`; sus salidas son `det` y `pivote` (32 bits, complemento a 2) y `final`.")
    inf.figura("cn_proc", "caja_negra_procesador.png", "Caja negra del microprocesador dedicado "
               "(entidad `procesador_bareiss`)", ancho=13.5)

    # ------------------------------------------------------ análisis
    inf.H2("2. Análisis del algoritmo y del hardware disponible")
    inf.P("Con la matriz del documento del taller, A = [2 1 3; 1 4 2; 3 2 5], el cálculo queda así:")
    inf.tabla("ej3", "Cálculo de Bareiss para la matriz de ejemplo",
              ["Paso", "p", "Pivote", "Operaciones", "Resultado"],
              [["k = 1", "1", "2", "a22 = (2·4 − 1·1)/1 = 7;  a23 = (2·2 − 1·3)/1 = 1;<br>"
                "a32 = (2·2 − 3·1)/1 = 1;  a33 = (2·5 − 3·3)/1 = 1", "[2 1 3; 1 7 1; 3 1 1]"],
               ["k = 2", "2", "7", "a33 = (7·1 − 1·1)/2 = 6/2 = 3", "[2 1 3; 1 7 1; 3 1 3]"]],
              [1.3, 0.8, 1.4, 8.3, 4.7], tam=9, centrar=(0, 1, 2))
    inf.P("El determinante es a33 = 3 y los pivotes son 2, 7 y 3 (por cofactores también da 3).")
    inf.P("**Pivote cero.** Si a(k,k) = 0, se busca la primera fila *i* > *k* con a(i,k) ≠ 0 y se intercambian "
          "las filas *i* y *k* desde la columna *k*. Cada intercambio cambia el signo del determinante, por eso "
          "se lleva el registro `SIGNO`. Si ninguna fila sirve, la columna es cero desde la diagonal y el "
          "determinante es 0.")
    inf.P("**División por restas sucesivas sin valor absoluto.** El numerador queda en *R* y el divisor *p* en "
          "*S*. Si los dos tienen el mismo signo, se resta *S* hasta que *R* llegue a 0 y el cociente cuenta "
          "+1; si tienen signos distintos, *R* empieza en 0, se resta *S* hasta llegar al numerador (guardado en "
          "*T*) y el cociente cuenta −1. Por ejemplo, −6 / 2: *T* = −6 y *R* = 0 → −2 → −4 → −6, cociente = −3. "
          "Como la división de Bareiss es exacta, *R* siempre llega a *T*. En el último paso, si hubo un número "
          "impar de intercambios, el cociente cuenta al revés y a(n,n) sale directamente con el signo del "
          "determinante.")
    inf.P("**Hardware disponible.** ROM de 32 × 6 bits con la matriz; dos RAM de 32 × 32 bits con el modelo del "
          "curso (escritura síncrona, lectura asíncrona) que se escriben siempre juntas, así se leen a(i,j) en la "
          "RAM A y a(k,j) en la RAM B en el mismo ciclo; un multiplicador de 25 × 25 bits; un restador de 50 "
          "bits; los contadores de índices y el contador del cociente. En las RAM, a(f,c) se guarda en la "
          "dirección `f & c(1..0)` para las columnas 1 a 4 y en `\"11\" & f` para la columna 5, así la dirección "
          "se arma juntando bits, sin sumadores.")
    inf.tabla("bits", "Tamaño de los datos",
              ["Dato", "Bits", "Razón"],
              [["Elementos de la ROM", "6", "Complemento a 2, de −32 a 31"],
               ["RAM, PIV, P, AIK, TMP, COCIENTE, DET, banco de pivotes", "32",
                "Cada valor es un menor de hasta 5 × 5; por la cota de Hadamard |det| ≤ (√5 · 32)^5^ ≈ "
                "1,9 × 10^9^ < 2^31^"],
               ["X, Y (entradas del multiplicador)", "25", "Menores de tamaño 4 o menos: |menor| ≤ (2 · 32)^4^ = 2^24^"],
               ["R, S, T (restador y división)", "50", "Producto de dos números de 25 bits"],
               ["N, I, J, K", "3", "Valores de 1 a 5"],
               ["DIRA", "5", "Direcciones 00h a 19h de la ROM"]],
              [5.6, 1.1, 9.8], tam=9, centrar=(1,))

    # ------------------------------------------------------ pseudoalgoritmo
    inf.H2("3. Pseudoalgoritmo")
    inf.P(f"Después se planteó el pseudoalgoritmo con el hardware disponible: los nombres son los de los "
          f"registros del procesador, cada producto se hace con el único multiplicador (`X * Y`) y cada resta con "
          f"el único restador (`R − S`). Se presenta en la {inf.F('pseudo')}.")
    inf.figura("pseudo", "pseudo_bareiss.png", "Pseudoalgoritmo propuesto para el cálculo del determinante")
    inf.P(f"Como se ve en la {inf.F('pseudo')}, el pseudoalgoritmo tiene seis bloques:")
    inf.lista([
        "El **rectángulo rosa** es el procedimiento previo al cálculo: pone `FINAL` en 0 y, cuando llega "
        "`INICIO`, lee *N* de la posición 0 de la ROM y copia la matriz en la RAM por columnas. Al final deja "
        "*P* = 1 (pivote inicial) y `SIGNO` = 0.",
        "El **rectángulo rojo** es un paso *K* de Bareiss: lee el pivote `PIV` = a(K,K), lo guarda en el banco de "
        "pivotes y, al terminar las filas, deja *P* = `PIV` para el paso siguiente.",
        "El **rectángulo azul** trata el pivote cero: busca una fila con a(I,K) ≠ 0, intercambia las filas con "
        "ayuda de `TMP` y cambia `SIGNO`. Si llega a la fila *N* sin encontrarla, el determinante es 0 y termina.",
        "El **rectángulo verde** recorre las filas *I* y las columnas *J* de la submatriz. Para cada elemento "
        "calcula los dos productos con el mismo multiplicador (`R = X * Y` y `S = X * Y`, cambiando *X* e *Y*) y "
        "el numerador con el restador (`R = R − S`).",
        "El **rectángulo amarillo** es la división del numerador entre *P* por restas sucesivas: escoge el valor "
        "de llegada *T* y el sentido del contador (`SQ`) según los signos y resta *S* = *P* hasta que *R* = *T*. "
        "No usa valor absoluto. El cociente se guarda en la RAM como el nuevo a(I,J).",
        "El **rectángulo naranja** entrega el resultado: el último cociente es a(N,N) = det y `FINAL` = 1.",
    ], numerada=True)

    # ------------------------------------------------------ ASM
    inf.H2("4. Diagrama ASM")
    inf.P(f"Posteriormente, se tradujo el pseudoalgoritmo al diagrama ASM de la {inf.F('asm')}, en la página "
          f"siguiente. Cada caja rectangular es un estado con todas las operaciones que se hacen en él, los rombos "
          f"son las decisiones (salidas 1 y 0) y las cajas redondeadas son las salidas condicionales. El recuadro "
          f"rojo punteado encierra cada bloque ASM: un estado con sus decisiones y sus salidas condicionales.")
    inf.P("El diagrama tiene 14 estados (S0 a S13). Como tiene cajas de salida condicional, describe una máquina "
          "de estados tipo Mealy: algunas asignaciones dependen de una decisión dentro del mismo estado. La "
          "relación con el pseudoalgoritmo es directa:")
    inf.lista([
        "S0 y S1 son el bloque rosa: S0 espera `INICIO` con `FINAL` = 0 y S1 copia un elemento de la ROM por "
        "ciclo. S1 avanza *I* y *J* por columnas y, al terminar, inicia *K*, *P* y `SIGNO`.",
        "S2 a S5 son el bloque rojo y el azul: S2 lee el pivote y lo guarda en el banco; si es cero, S3 busca la "
        "fila y S4 y S5 intercambian una columna por ciclo. Al terminar el intercambio se vuelve a S2 para leer "
        "el pivote nuevo.",
        "S6 a S10 son el bloque verde: S6 toma a(I,K); S7 y S8 cargan *X* e *Y*; el multiplicador aparece solo en "
        "S8 y S9, siempre como `X * Y`, y el restador en S10 y S12, siempre como `R − S`. Por eso la síntesis "
        "arma un solo multiplicador y un solo restador.",
        "S11 y S12 son el bloque amarillo: S11 prepara la división (*T* y `SQ`) y S12 resta hasta que *R* = *T*; "
        "luego guarda el cociente y avanza *J*, *I* o *K*.",
        "S13 es el bloque naranja: `FINAL` = 1. Si llega otro `INICIO`, el cálculo empieza de nuevo en S1.",
    ])
    inf.P(f"Las reglas del ASM se revisaron con un programa (`informe/fuentes/fig_asm.py`) que recorre el dibujo: "
          f"cada rombo tiene una salida 1 y una 0, y para todas las combinaciones de las señales de estado el "
          f"camino que sale de cada estado llega a un solo estado siguiente, el mismo que en el VHDL. Si se juntan "
          f"los caminos de S11, que siempre van a S12, el ASM tiene {n_trans} transiciones.")
    inf.seccion(1.4)
    inf.figura("asm", "asm_bareiss.png", "Diagrama ASM del microprocesador de Bareiss", ancho=18.8, alto_max=22.8,
               nativo=False)
    inf.seccion(2.5)
    inf.P("Con esta representación en diagrama ASM es posible identificar las señales de estado. Sin embargo, no "
          "es posible deducir el tamaño ni las especificaciones de la palabra de control, pues el microprocesador "
          "dedicado se describe en alto nivel: no hay un diseño de camino de datos del cual deducir el tamaño y "
          "los campos de la palabra de control. El diagrama de caja gris queda de la siguiente manera:")

    # ------------------------------------------------------ caja gris
    inf.H2("5. Caja gris del microprocesador")
    inf.figura("cg_proc", "caja_gris_procesador.png", "Diagrama de caja gris del microprocesador dedicado",
               ancho=15)
    inf.P(f"En la {inf.F('cg_proc')} se puede apreciar que para la unidad de control (UC) las entradas son:")
    inf.lista(["`inicio` (1 bit)",
               "Señales de estado (z_b, z_a, i_n, j_n, k1_n, ms, sg, rt, sq) (9 bits)",
               "`clk` y `rst`"])
    inf.P("y las salidas:", despues=2)
    inf.lista(["`final` (1 bit)", "Palabra de control (bits desconocidos)"])
    inf.P("Para el camino de datos (CD) las entradas son la palabra de control (bits desconocidos), `dir_p` "
          "(3 bits), `clk` y `rst`, y las salidas son `det` (32 bits), `pivote` (32 bits) y las 9 señales de "
          f"estado, que se describen en la {inf.T('senales')}.")
    inf.tabla("senales", "Señales de estado del microprocesador",
              ["Señal", "Pregunta en el ASM", "Estados que la usan"],
              [list(x) for x in ESTADO_P], [2.0, 6.5, 4.0], tam=9.5, centrar=(2,), negrita_col0=True)

    # ------------------------------------------------------ UC
    inf.H2("6. Unidad de control")
    inf.figura("uc", "uc_procesador.png", "Unidad de control del microprocesador", ancho=15)
    inf.P(f"La UC de la {inf.F('uc')} tiene la estructura del curso. El registro de estado es de 4 bits, porque "
          f"guarda 14 estados (con 4 bits se pueden codificar hasta 16).")
    inf.P("La ROM de entrada determina el próximo estado. Sus entradas son el estado actual, codificado en 4 bits "
          "(realimentación), y las condiciones que cambian el estado siguiente: `inicio`, z_b, z_a, i_n, j_n, "
          "k1_n y rt. Las señales ms, sg y sq no cambian el estado siguiente, porque en S11 siempre se va a S12 y "
          "en S12 la decisión SQ siempre vuelve a S12; solo eligen salidas condicionales. En total la ROM recibe "
          "11 bits de dirección (4 del estado y 7 de condiciones) y entrega el próximo estado en 4 bits, así que "
          "su dimensión teórica es de 2^11^ × 4, es decir, una ROM de 2048 × 4 bits.")
    inf.P("La ROM de salida genera las señales de control del camino de datos. Como la máquina es de tipo Mealy, "
          "necesita el estado actual (4 bits) y también las 10 condiciones de las que dependen las salidas "
          "condicionales (`inicio` y las 9 señales de estado), es decir, 14 bits de dirección. Su salida es la "
          "palabra de control, cuyo número de bits es desconocido, más la señal `final`. Por tanto, su dimensión "
          "es de 2^14^ × (XX + 1), es decir, una ROM de 16 384 × (XX + 1) bits.")

    # ------------------------------------------------------ visualizador
    inf.H2("7. Módulo de visualización (XS3) y display de la Nexys A7")
    inf.P("La Nexys A7-100T tiene un display de 8 dígitos de siete segmentos, de ánodo común, con los segmentos "
          "compartidos: en cada momento se enciende un dígito y se recorren los ocho rápidamente. El módulo de "
          "visualización no participa en el cálculo del determinante; toma el valor binario de 32 bits elegido "
          "con `dir_p` (det si `dir_p` = 0, o el pivote), lo pasa a decimal con el algoritmo XS3 y lo muestra: "
          "AN7 lleva el signo menos y AN6..AN0 los 7 dígitos de menor peso.")
    inf.P("El algoritmo XS3 (sumar 3 y correr) parte del registro decimal en cero. En cada iteración entra un bit "
          "del binario por la derecha, a cada dígito BCD mayor que 4 se le suma 3 y los dos registros se corren a "
          "la izquierda. Sumar 3 antes de correr equivale a sumar 6 después, que es la corrección de un dígito que "
          "pasa de 9. Antes de empezar se toma el valor absoluto (0 − VAL si es negativo) y el signo se guarda "
          f"aparte. La {inf.F('pseudo_xs3')} muestra el pseudoalgoritmo con los pasos del método.")
    inf.figura("pseudo_xs3", "pseudo_xs3.png", "Pseudoalgoritmo del algoritmo XS3", ancho=10.5)
    inf.lista([
        "El **rectángulo rosa** espera `FINAL` = 1, guarda el signo en `NEG` y deja en `BIN` el valor absoluto.",
        "El **rectángulo rojo** hace los pasos del método: borra `DEC` (paso 1), mete el bit más significativo de "
        "`BIN` (paso 2), corre los dos registros (paso 4) y repite hasta que entran los 32 bits (paso 5).",
        "El **rectángulo azul** es el paso 3: revisa los 10 dígitos y suma 3 a los mayores que 4.",
        "El **rectángulo naranja** pasa el resultado a los registros del display (`DISP` y `DISP_NEG`).",
    ], numerada=True)
    inf.P(f"El ASM del visualizador ({inf.F('asm_xs3')}) tiene 6 estados, uno por cada paso. También es de tipo "
          f"Mealy. Mientras `FINAL` = 0 espera en X0 y el display conserva el último valor; cuando el procesador "
          f"termina, convierte una y otra vez el valor elegido, así el display sigue a los switches. Cada "
          f"conversión tarda 376 ciclos (3,76 µs): X0 y X1 (2), 31 iteraciones de X2, diez veces X3 y X4 "
          f"(31 × 12 = 372) y la última pasada por X2 y X5 (2).")
    inf.figura("asm_xs3", "asm_xs3.png", "Diagrama ASM del visualizador (algoritmo XS3)", ancho=11.5, nativo=False)
    inf.tabla("senales_v", "Señales de estado del visualizador",
              ["Señal", "Pregunta en el ASM", "Estado"],
              [list(x) for x in ESTADO_V], [2.0, 6.5, 2.5], tam=9.5, centrar=(2,), negrita_col0=True)
    inf.figura("uc_v", "uc_visualizador.png", "Unidad de control del visualizador", ancho=15)
    inf.P(f"Igual que en el procesador, el ASM permite identificar las señales de estado "
          f"({inf.T('senales_v')}), pero no el tamaño de la palabra de control. La UC del visualizador "
          f"({inf.F('uc_v')}) tiene un registro de estado de 3 bits (6 estados), una ROM de entrada de 2^6^ × 3 = "
          f"64 × 3 bits (estado y las condiciones `final`, cont_31 y d_9) y una ROM de salida de 2^8^ × XX = "
          f"256 × XX bits (estado y las 5 condiciones). Las unidades del visualizador (restador 0 − VAL, sumador "
          f"+3 y comparador > 4) son propias: no comparte el multiplicador ni el restador de Bareiss. El "
          f"comparador > 4 recibe el dígito con un 0 adelante, porque con `std_logic_signed` los valores 8 y 9 "
          f"de 4 bits se leerían como negativos.")
    inf.P("El barrido del display lo hace un contador de 3 bits (`dsel`) que avanza con cada pulso de 1 ms del "
          "divisor de frecuencia: un barrido completo dura 8 ms, sin parpadeo visible. Los ánodos y los segmentos "
          "son activos en bajo. `DESBORDE` vale 1 cuando alguno de los tres dígitos de mayor peso del registro "
          "del display es distinto de cero.")

    # ------------------------------------------------------ bloques
    inf.H2("8. Bloques auxiliares y caja gris del sistema")
    inf.P(f"El sistema completo tiene cuatro bloques, conectados en la entidad `det_bareiss` ({inf.F('cg_sis')}):")
    inf.figura("cg_sis", "caja_gris_sistema.png", "Diagrama de caja gris del sistema completo", ancho=16)
    inf.lista([
        "**divisor_frecuencia**: cuenta 100 000 ciclos del reloj de 100 MHz y entrega `tick_1ms`, un pulso de un "
        "ciclo cada 1 ms. El pulso se usa como habilitación: todo el diseño trabaja con el mismo reloj.",
        "**antirrebote**: sincroniza BTNC con dos flip-flops, lo muestrea cada 1 ms y solo cambia el nivel "
        "estable con 8 muestras iguales. Entrega un pulso de un ciclo por pulsación.",
        "**procesador_bareiss**: el microprocesador dedicado de las secciones 1 a 6.",
        "**visualizador**: el ASM XS3 y el display de la sección 7, en paralelo con el procesador.",
    ])
    inf.P("El procesador no usa el divisor de frecuencia: trabaja a 100 MHz, porque con un reloj de 1 Hz la matriz "
          "de 3 × 3 tardaría casi un minuto y la de 5 × 5 más de una hora.")

    # ------------------------------------------------------ VHDL
    inf.H2("9. Descripción en VHDL")
    inf.tabla("archivos", "Archivos del proyecto (carpeta `src/`)",
              ["Archivo", "Contenido", "Librería"],
              [["det_bareiss.vhd", "Tope: solo conecta los cuatro bloques (port map)", "std_logic_1164"],
               ["procesador_bareiss.vhd", "ASM de Bareiss (un process con case st), ROM (with dira select) y las "
                "dos instancias de RAM_memory", "std_logic_signed"],
               ["RAM_memory.vhd", "Modelo de RAM del curso, sin cambios", "std_logic_unsigned"],
               ["visualizador.vhd", "ASM XS3 y display de 8 dígitos", "std_logic_signed"],
               ["divisor_frecuencia.vhd", "Pulso de 1 ms", "std_logic_signed"],
               ["antirrebote.vhd", "Antirrebote del botón de inicio", "std_logic_1164"],
               ["nexys_a7.ucf", "Pines y restricción de reloj de 10 ns", "—"]],
              [4.0, 9.3, 3.2], tam=9)
    inf.P("Cada estado del `case st is` tiene las operaciones de su caja del ASM y las decisiones se escriben con "
          "`if`. Por ejemplo, el estado S12, con la división y el avance de los índices:")
    inf.codigo("""\
when s12 =>                         -- division por restas sucesivas: r = r - p
    if r /= t then
        r <= r - s;
        if sq = '0' then
            cociente <= cociente + 1;
        else
            cociente <= cociente - 1;
        end if;
        st <= s12;
    elsif j /= n then               -- RAM(i,j) = cociente ; siguiente columna
        j  <= j + 1;
        st <= s7;
    elsif i /= n then               -- siguiente fila
        i  <= i + 1;
        j  <= k;
        st <= s6;
    elsif k + 1 /= n then           -- siguiente paso: p = piv
        p  <= piv;
        k  <= k + 1;
        j  <= k + 1;
        st <= s2;
    else                            -- ultimo paso: det = a(n,n)
        deter <= cociente;
        st <= s13;
    end if;""", tam=8)
    inf.P("Las escrituras en las RAM (`we`, `wr_add` y `data`) se describen fuera del process con asignaciones "
          "que dependen del estado, porque la RAM del curso es una entidad aparte. El código completo está en el "
          "Anexo A.")

    # ============================================================ resultados
    inf.H1("Resultados")
    inf.H2("1. Caja negra del circuito generada por ISE")
    inf.hueco("rtl_top", "Caja negra del circuito final generada por ISE (RTL de `det_bareiss`)",
              "[ Pegar aquí la captura: Synthesize – XST → View RTL Schematic → det_bareiss ]", alto=6)
    inf.P(f"La caja negra generada por ISE debe tener los mismos puertos de la {inf.F('cn_sis')}: `clk`, `rst`, "
          f"`inicio` y `dir_p[2:0]` como entradas, y `seg[6:0]`, `an[7:0]`, `dp`, `final` y `desborde` como "
          f"salidas.")
    inf.H2("2. Caja gris del procesador generada por ISE")
    inf.P(f"El esquema RTL de `procesador_bareiss` (Synthesize – XST → View RTL Schematic) es demasiado grande "
          f"para leerlo en una página. Por eso, en la {inf.T('rtl_bloques')} se listan los bloques que XST "
          f"infirió, tomados del reporte de síntesis del procesador (secciones HDL Synthesis y Advanced HDL "
          f"Synthesis).")
    inf.tabla("rtl_bloques", "Bloques del procesador según el reporte de síntesis de XST",
              ["Bloque", "Tamaño", "Línea del VHDL", "Uso"],
              [["ROM de la matriz (`a`)", "32 × 6, solo lectura", "107", "Matriz en complemento a 2 (S0, S1)"],
               ["RAM A y RAM B (`RAM_memory`)", "2 de 32 × 32, lectura asíncrona", "140–143",
                "Leer a(i,j) y a(k,j) en el mismo ciclo"],
               ["Multiplicador", "25 × 25 → 50 bits", "275", "`X * Y` en S8 y S9"],
               ["Restador", "50 bits", "306", "`R − S` en S10 y S12"],
               ["Contador ascendente/descendente", "32 bits", "308, 310", "Cociente de la división (S12)"],
               ["Sumador de `dira`", "5 bits", "208", "Dirección de la ROM (S1)"],
               ["Sumadores de K, J e I", "3 bits", "226, 314, 317", "Índices"],
               ["Comparador R = T", "50 bits", "150", "Fin de la división (rt)"],
               ["Comparadores DIR_P = N, I = N, J = N, K + 1 = N", "3 bits", "165, 243, 256, 297",
                "Señales de estado y selección del pivote"],
               ["Multiplexor de `pivote`", "32 bits, 7 a 1", "165", "Elige det o un pivote con `dir_p`"],
               ["Registros", "539 flip-flops en 22 registros", "—",
                "Camino de datos; XST quita 7 (aik_25 … aik_31) y quedan 532"],
               ["FSM_0 (`st`)", "14 estados, 4 flip-flops", "50", "Unidad de control"]],
              [5.0, 3.9, 2.6, 5.0], tam=8.5, centrar=(2,))
    inf.P("El multiplicador y el restador de 50 bits aparecen una sola vez: los dos productos y todas las restas "
          "de Bareiss usan las mismas unidades.")
    inf.hueco("rtl_fsm", "FSM de la unidad de control en el esquema RTL de ISE (bloque `FSM_0-parent`). El RTL "
              "dibuja un flip-flop por estado (FFd1 a FFd14); la implementación final usa 4 flip-flops "
              "(`st[1:4]`)",
              "[ Pegar aquí la captura de la FSM del procesador (bloque FSM dentro de U_PROC) ]", alto=6)
    inf.P(f"El reporte de síntesis de XST reconoció la FSM del procesador (FSM_0, señal `st`) con 14 estados, "
          f"{n_trans} transiciones, 7 entradas y 9 salidas, con reloj por flanco de subida y reset asíncrono que "
          f"lleva a s0. Las 7 entradas son `inicio` y las seis señales de estado que cambian el estado siguiente "
          f"(z_b, z_a, i_n, j_n, k1_n y rt), las mismas de la ROM de entrada de la sección 6.")
    inf.P(f"En la {inf.F('rtl_fsm')} se ven 14 flip-flops (FFd1 a FFd14, uno por estado) porque ISE dibuja el "
          f"esquema RTL antes de elegir la codificación de la FSM. Después, en la optimización, el reporte dice "
          f"`Optimizing FSM <FSM_0> on signal <st[1:4]> with user encoding`: XST usa la codificación del "
          f"usuario, que es el orden en que se declararon los estados en el tipo `estados_asm` (s0 = 0000, "
          f"s1 = 0001 … s13 = 1101). Así, el registro de estado queda de 4 flip-flops, como en la UC de la "
          f"sección 6. El conteo de registros lo confirma: el Final Register Report da 536 flip-flops para el "
          f"procesador, 532 del camino de datos y 4 del estado; si el estado usara 14 flip-flops serían 546. "
          f"Según el reporte, ISE genera para la FSM una palabra de control de ==9== bits de salida.")
    inf.P(f"En la síntesis del diseño completo (`det_bareiss`), XST reconoció además la FSM del visualizador "
          f"(FSM_1, señal `xs`) con 6 estados, {n_trans_v} transiciones, 3 entradas y 3 salidas.")

    inf.H2("3. Estadísticas de ISE")
    inf.leyenda("Tabla", "ise", "Recursos y tiempos según los reportes de síntesis, Map y Place & Route de ISE "
                "(XC7A100T-1CSG324)")
    filas_ise = [
        ["Slice Registers (flip-flops)", "702", "126 800", "0,6 %"],
        ["Slice LUTs", "878", "63 400", "1,4 %"],
        ["LUT usadas como RAM (RAM A y RAM B)", "48", "19 000", "0,3 %"],
        ["Slices ocupados", "303", "15 850", "1,9 %"],
        ["IOB", "24", "210", "11,4 %"],
        ["BUFG", "1", "32", "3,1 %"],
        ["DSP48E1 (multiplicador 25 × 25)", "2", "240", "0,8 %"],
        ["Periodo mínimo estimado por XST", "7,012 ns (142,6 MHz)", "10 ns (reloj de 100 MHz)",
         "70,1 % del periodo"],
        ["Holgura de setup después de Place & Route", "1,206 ns", "—", "—"],
        ["Holgura de hold", "0,058 ns", "—", "—"],
        ["Restricción TS_sys_clk = 10 ns", "Cumplida", "—", "—"],
    ]
    inf.tabla(None, None, ["Parámetro", "Usado", "Disponible", "Porcentaje de uso"],
              filas_ise, [6.3, 3.7, 3.7, 2.8], tam=9, centrar=(1, 2, 3), negrita_col0=True)
    inf.P("Según los reportes, el diseño ocupa menos del 2 % de los slices de la FPGA; el recurso que más usa son "
          "los pines (11,4 % de los IOB). Los flip-flops de la tabla son los que cuenta Map (702). El Final "
          "Register Report de XST da 694 para el diseño completo; son reportes de etapas distintas y Map puede "
          "añadir o duplicar registros al mapear el diseño en la FPGA.")
    inf.P("XST reconoció una sola FSM de 14 estados para el procesador, que corresponde al ASM, e infirió un solo "
          "multiplicador de 25 × 25 bits (en la Artix-7 ocupa 2 bloques DSP48E1) y un solo restador de 50 bits "
          "para los datos de la matriz. Los demás sumadores son de 3 y 5 bits, para los índices y la dirección de "
          "la ROM, y el cociente usa un contador ascendente/descendente de 32 bits. Las dos RAM quedan como RAM "
          "distribuida (con LUT), porque el modelo del curso tiene lectura asíncrona. Así se confirma que se "
          "cumple la restricción de un solo multiplicador y un solo sumador/restador.")
    inf.P("En cuanto al desempeño temporal, XST estima un periodo mínimo de 7,012 ns. Su camino crítico va del "
          "registro X al registro R a través del multiplicador (los dos DSP48E1 en cascada), y el 88 % de ese "
          "retardo es lógica, porque XST solo estima 0,83 ns de rutas. Después de Place & Route la holgura de "
          "setup es de 1,206 ns, es decir, el camino más lento tarda unos 8,8 ns (10 − 1,206): los retardos "
          "reales de las rutas alargan el camino. Aun así se cumple la restricción TS_sys_clk = 10 ns y la "
          "holgura de hold (0,058 ns) es positiva, así que el diseño funciona con el reloj de 100 MHz de la "
          "tarjeta.")
    inf.tabla("avisos", "Advertencias e informaciones de ISE y su explicación",
              ["Mensaje", "Explicación"],
              [["Xst:2677: aik_25 … aik_31 sin conexión", "El multiplicador solo usa los 25 bits bajos de AIK; XST "
                "quita los 7 flip-flops de los bits altos. No afecta el resultado."],
               ["Par:288 y PhysDesignRules:367 (señales RAMD_D1_O sin carga)", "La salida de lectura del puerto D "
                "de cada RAM32M no se usa, porque las RAM solo leen por los otros puertos. Sale un aviso por cada "
                "uno de los 10 RAM32M de las dos RAM."],
               ["INFO HDLCompiler:679: `others` nunca se selecciona", "En el visualizador los 6 estados ya están en "
                "el case; el `when others` sobra pero no hace daño."],
               ["INFO Xst:3218: RAM distribuida", "Aparece para las dos RAM (`Mram_ram_blk`) y para la ROM "
                "(`Mram_a`): como tienen lectura asíncrona, XST las arma con LUT y no con bloques de RAM."],
               ["Security:42", "Aviso de licencia de ISE; no tiene que ver con el diseño."]],
              [6.0, 10.5], tam=8.5)

    # ------------------------------------------------------ simulaciones
    inf.H2("4. Simulaciones – banco de prueba")
    inf.P("Para la simulación se usó el banco de prueba `sim/tb_informe.vhd`, que conecta el procesador con el "
          "visualizador: pone `rst` en 1 durante 20 ns, da un pulso de `inicio` de un ciclo, espera `final` = 1 y "
          "después recorre `dir_p` = 1 … *n* para leer los pivotes. El reloj es de 10 ns (100 MHz). El cursor "
          "amarillo marca el instante de los valores de la columna *Value*.")
    inf.P(f"Con el primer banco de prueba, la matriz del ejemplo [{matriz_txt(M.MATRICES[1])}], se obtuvo:")
    inf.figura("sim1", "sim_3x3.png", "Primera simulación: matriz 3 × 3 del ejemplo", nativo=False)
    inf.P(f"En la {inf.F('sim1')} se aprecia el funcionamiento del sistema: al activarse `inicio`, el ASM pasa por "
          f"S1 (copia de la ROM) y luego por los estados del cálculo, con S12 repetido en cada división. `final` "
          f"sube a los 615 ns ({ciclos[1]} ciclos) con `det` = {det1}. Al mover `dir_p` de 1 a 3, `pivote` "
          f"muestra {', '.join(map(str, piv1))}, igual que el cálculo a mano de la {inf.T('ej3')}.")
    inf.P(f"Con el segundo banco de prueba se usó una matriz con pivote cero en el primer paso, "
          f"[{matriz_txt(M.MATRICES[2])}]:")
    inf.figura("sim2", "sim_4x4_cero.png", "Segunda simulación: matriz 4 × 4 con a(1,1) = 0", nativo=False)
    inf.P(f"En la {inf.F('sim2')} `signo` pasa a 1 cuando el ASM encuentra a(2,1) ≠ 0 e intercambia las filas 1 y "
          f"2. Por eso la última división cuenta hacia abajo y el resultado sale con el signo correcto: `det` = "
          f"{det2}, con los pivotes {', '.join(map(str, piv2))}.")
    inf.P(f"El tercer banco de prueba usa la matriz 5 × 5 que queda en la ROM del proyecto, "
          f"[{matriz_txt(M.MATRICES[3])}]:")
    inf.figura("sim3", "sim_5x5.png", "Tercera simulación: matriz 5 × 5 de la ROM", nativo=False)
    inf.P(f"En la parte a) de la {inf.F('sim3')} se ve el cálculo completo, que tarda {miles(ciclos[3])} ciclos "
          f"(37,7 µs): la mayor parte del tiempo está en S12, porque las divisiones de los últimos pasos tienen "
          f"cocientes de cientos. En la parte b) se ve el final: `det` = {det3} y los pivotes "
          f"{', '.join(map(str, piv3))}.")
    inf.P("La última simulación muestra el visualizador con el mismo banco de prueba:")
    inf.figura("sim4", "sim_xs3.png", "Cuarta simulación: conversión XS3 del determinante 362", nativo=False)
    inf.P(f"En la {inf.F('sim4')} el ASM XS3 arranca cuando `final` sube; `cont` avanza de 0 a 31 (un bit por "
          f"iteración) y al terminar el valor pasa a `disp` = 0000000362, que el display muestra como 0000362. "
          f"La conversión dura 376 ciclos. Después el ASM vuelve a empezar, por eso `cont` comienza otra vez en 0.")
    inf.P("Además de estas simulaciones, el proyecto tiene bancos de prueba que comparan los resultados con un "
          "modelo de referencia: `tb_procesador.vhd` (det y todos los pivotes de 8 matrices de prueba, entre ellas "
          "una con la columna 1 en cero y otra con valores extremos), `tb_visualizador.vhd` (XS3 y display con "
          "valores positivos, negativos y con desborde) y `tb_det_bareiss.vhd` (circuito completo con un botón con "
          "rebotes). Todas las pruebas pasaron.")
    filas_t = []
    notas = {0: "", 1: "ejemplo del taller", 2: "a11 = 0", 3: "ROM del proyecto", 4: "intercambio en k = 2",
             5: "pivote cero en k = 2", 6: "columna 1 en cero", 7: "valores extremos"}
    for num, a in enumerate(M.MATRICES):
        det, piv, _ = M.bareiss(a)
        filas_t.append([str(num), f"{len(a)} × {len(a)}" + (f" ({notas[num]})" if notas[num] else ""),
                        ", ".join(map(str, piv)), str(det), miles(ciclos.get(num, 0)), "PASA"])
    inf.tabla("pruebas", "Resultados de `tb_procesador.vhd` con las matrices de prueba",
              ["Matriz", "Tamaño", "Pivotes (dir_p = 1 … n)", "det", "Ciclos", "Resultado"],
              filas_t, [1.3, 4.0, 5.6, 1.9, 2.1, 1.6], tam=8.5, centrar=(0, 3, 4, 5))

    # ------------------------------------------------------ conclusiones
    inf.H1("Conclusiones")
    inf.lista([
        "El planteamiento del ASM en alto nivel permitió pasar del pseudoalgoritmo al VHDL casi línea por línea: "
        "cada caja de estado es un `when` del `case` y cada rombo es un `if`. Las operaciones repetitivas (la "
        "copia de la ROM, el intercambio de filas y la división por restas sucesivas) quedaron en estados que se "
        "repiten varios ciclos hasta que se cumple su condición, así el ASM queda en 14 estados.",
        "Escribir siempre `X * Y` y `R − S` sobre los mismos registros hizo que la síntesis armara un solo "
        "multiplicador y un solo restador, como pide el taller. El costo son los estados S7 a S10, que preparan "
        "las entradas de esas dos unidades.",
        "La división por restas sucesivas se resolvió sin valor absoluto, cambiando el valor de llegada *T* y el "
        "sentido del contador según los signos. El tiempo de cálculo depende del tamaño de los cocientes: "
        f"{ciclos[1]} ciclos para la matriz de ejemplo y {miles(ciclos[3])} para la matriz 5 × 5 de la ROM.",
        "La caja gris y las ROM de la unidad de control muestran que el ASM basta para conocer las señales de "
        "estado y el tamaño del registro de estado y de la ROM de entrada, pero no la palabra de control, que "
        "solo aparece al sintetizar la descripción de alto nivel. El reporte de ISE confirmó la FSM de 14 estados "
        "con 4 flip-flops, un multiplicador y un restador, y el cumplimiento del reloj de 100 MHz.",
    ], numerada=True)

    inf.H1("Referencias")
    inf.lista([
        "E. H. Bareiss, “Sylvester's identity and multistep integer-preserving Gaussian elimination”, "
        "*Mathematics of Computation*, vol. 22, n.º 103, pp. 565–578, 1968.",
        "Digilent, *Nexys A7 Reference Manual*.",
        "Xilinx, *XST User Guide for Virtex-6, Spartan-6, and 7 Series Devices* (UG687), ISE 14.7.",
        "Guía y ejemplos del curso Análisis y Diseño de Microprocesadores (ASM_Sumax, ASM_contador_unos y "
        "modelo de RAM), Universidad Distrital.",
    ])

    # -------------------------------------------------------------- anexo
    inf.H1("Anexo A. Código VHDL", pagina_nueva=True)
    for archivo in ("procesador_bareiss.vhd", "visualizador.vhd", "det_bareiss.vhd", "RAM_memory.vhd",
                    "divisor_frecuencia.vhd", "antirrebote.vhd"):
        inf.H2(f"src/{archivo}")
        inf.codigo((RAIZ / "src" / archivo).read_text(encoding="utf-8"), tam=7)
    return d


def arreglar_saltos(doc):
    """Convierte '<br>' de los textos de las tablas en saltos de línea."""
    for t in doc.tables:
        for f in t.rows:
            for c in f.cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        if "<br>" in r.text:
                            partes = r.text.split("<br>")
                            r.text = partes[0]
                            for parte in partes[1:]:
                                r.add_break()
                                r.add_text(parte)


def main():
    inf = Informe()
    contenido(inf)                      # primera pasada: numeración
    doc = contenido(inf)
    arreglar_saltos(doc)
    doc.core_properties.title = "Taller 5: determinante por Bareiss con visualización XS3"
    doc.core_properties.author = ", ".join(e[0] for e in ESTUDIANTES)
    doc.save(SALIDA)
    print("Guardado", SALIDA)
    texto = "\n".join(p.text for p in doc.paragraphs)
    for f in ("Figura ?", "Tabla ?"):
        if f in texto:
            print("AVISO: referencia sin resolver:", f)


if __name__ == "__main__":
    main()

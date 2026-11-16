#!/usr/bin/env python3
"""Genera el informe del Taller 5 (informe/Informe_Taller5_Bareiss.docx).

Las figuras se toman de informe/figuras (generar_figuras.py y ondas.py) y las
tablas de la UC y del CD de uc_cd.py, para que el informe y el diseño no se
separen. El PDF se saca con LibreOffice:

  soffice --headless --convert-to pdf --outdir informe informe/Informe_Taller5_Bareiss.docx
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT  # noqa: F401
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


MARCAS = re.compile(r"(\*\*.+?\*\*|\*.+?\*|`.+?`|\^.+?\^|_\{.+?\})")


def texto_rico(parrafo, texto, tam=None, color=None):
    """**negrita**, *cursiva*, `código`, ^superíndice^, _{subíndice}."""
    for parte in MARCAS.split(texto):
        if not parte:
            continue
        if parte.startswith("**"):
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

    def H1(self, t):
        self.d.add_heading(t, 1)

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
        for k, t in enumerate(items, 1):
            p = self.d.add_paragraph(style="List Number" if numerada else "List Bullet")
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(3)
            texto_rico(p, t)

    def salto(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

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
    """Caminos de salida distintos del ASM si se juntan los que solo cambian
    salidas condicionales y llevan al mismo estado (como cuenta XST)."""
    total = 0
    for e, lista in filas.items():
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


def cond_txt(cond):
    return ", ".join(f"{k} = {v}" for k, v in cond.items()) if cond else "—"


GRUPOS_P = [
    ("Índices", ["ld_dira", "sel_dira", "ld_n", "ld_i", "sel_i", "ld_j", "sel_j", "ld_k", "sel_k"]),
    ("Registros de datos", ["ld_piv", "ld_p", "sel_p", "ld_aik", "ld_tmp", "ld_sg", "sel_sg", "we_b", "ld_det",
                            "sel_det"]),
    ("Multiplicador, restador y división", ["ld_x", "sel_x", "ld_y", "sel_y", "ld_r", "sel_r", "ld_s", "sel_s",
                                           "ld_t", "sel_t", "ld_c", "sel_c", "ld_sq", "sel_sq"]),
    ("RAM", ["we", "sel_w", "sel_d"]),
]
GRUPOS_V = [("bin y neg", ["ld_bin", "sel_bin", "ld_neg"]), ("dec", ["ld_dec", "sel_dec"]),
            ("cont y d", ["ld_cont", "sel_cont", "ld_d", "sel_d"]), ("display", ["ld_disp"])]


def tabla_rom_entrada(inf, clave, texto, filas, campos, senales, estados):
    orden, rom = U.proyectar(filas, campos, senales, "sig")
    enc = ["Estado", "Q"] + list(orden) + ["Siguiente", "D"]
    datos = []
    for e, cl, sig in rom:
        datos.append([e, U.codigo(estados, e)] + [str(cl[s]) if s in cl else "–" for s in orden]
                     + [sig, U.codigo(estados, sig)])
    n = len(orden)
    w_s = min(1.25, (ANCHO - 1.5 - 1.3 - 1.7 - 1.3) / n)
    anchos = [1.5, 1.3] + [w_s] * n + [1.7, 1.3]
    inf.tabla(clave, texto, enc, datos, anchos, tam=8.5, mono=(1, n + 3), centrar=tuple(range(len(enc))))
    return orden, rom


def tabla_rom_salida(inf, clave, texto, filas, campos, senales, grupos, final, estados, anchos):
    orden, rom = U.proyectar(filas, campos, senales, "pc")
    enc = ["Estado", "Condiciones"] + [f"{g}" for g, _ in grupos] + (["final"] if final is not None else [])
    datos = []
    for e, cl, pc in rom:
        fila = [e, cond_txt(cl)] + [" ".join(pc[c] for c in campos_g) for _, campos_g in grupos]
        if final is not None:
            fila.append("1" if e in final else "0")
        datos.append(fila)
    inf.tabla(clave, texto, enc, datos, anchos, tam=8, mono=tuple(range(2, len(enc))),
              centrar=(0,) + tuple(range(2, len(enc))))
    return orden, rom


# ===========================================================================
# Contenido
# ===========================================================================
def contenido(inf):
    d = inf.nuevo()
    ghdl = U.ciclos_ghdl()
    n_trans = transiciones(U.FILAS_P)
    n_trans_v = transiciones(U.FILAS_V)
    filas_p = sum(len(v) for v in U.FILAS_P.values())
    o_sig, r_sig = U.proyectar(U.FILAS_P, U.CAMPOS_P, U.SENALES_P, "sig")
    o_pc, r_pc = U.proyectar(U.FILAS_P, U.CAMPOS_P, U.SENALES_P, "pc")
    ov_sig, rv_sig = U.proyectar(U.FILAS_V, U.CAMPOS_V, U.SENALES_V, "sig")
    ov_pc, rv_pc = U.proyectar(U.FILAS_V, U.CAMPOS_V, U.SENALES_V, "pc")
    bits_e = 2 ** (4 + len(o_sig))
    bits_s = 2 ** (4 + len(o_pc))
    bits_ev = 2 ** (3 + len(ov_sig))
    bits_sv = 2 ** (3 + len(ov_pc))
    ff_p = sum(r[1] for r in U.REGISTROS_P) + 4
    ff_v = sum(r[1] for r in U.REGISTROS_V) + 3 + 3      # estado del XS3 y dsel
    ff_total = ff_p + ff_v + 27 + 12                      # divisor: 17 + 9 + 1; antirrebote: 2 + 8 + 2

    # ---------------------------------------------------------------- portada
    for t, tam, neg in (("Universidad Distrital Francisco José de Caldas", 13, True),
                        ("Facultad de Ingeniería · Análisis y Diseño de Microprocesadores", 11, False)):
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(t)
        fuente_run(r, tam=tam, negrita=neg)
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run("Taller 5: determinante de una matriz por el algoritmo de Bareiss con visualización decimal (XS3)")
    fuente_run(r, tam=17, negrita=True, color=AZUL)
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Diseño del procesador con diagramas ASM, camino de datos y unidad de control · "
                  "VHDL en ISE 14.7 · Nexys A7-100T")
    fuente_run(r, tam=10.5, cursiva=True)

    inf.H2("Estudiantes")
    inf.tabla(None, None, ["Nombre", "Código", "Correo"], ESTUDIANTES, [6.6, 3.2, 6.7], tam=10,
              centrar=(1,))
    inf.P("Profesor: Ing. Gaona · Bogotá D. C., noviembre de 2026", alin=WD_ALIGN_PARAGRAPH.CENTER, tam=10)

    # ---------------------------------------------------------- 1 descripción
    inf.H1("1. Descripción del problema")
    inf.P("Se diseña un microprocesador de propósito específico que calcula el determinante de una matriz "
          "cuadrada de 2 × 2 a 5 × 5 con el algoritmo de Bareiss. La matriz está guardada en una ROM: la "
          "posición 00h tiene el tamaño *n* y desde la 01h están los elementos por columnas (a11, a21, …, an1, "
          "a12, …), en complemento a 2 de 6 bits (−32 a 31). El procesador copia la matriz en memoria RAM, "
          "hace la eliminación de Bareiss y guarda los pivotes en un banco de registros. El resultado se "
          "muestra en decimal en el display de 8 dígitos de la tarjeta Nexys A7-100T: con los switches "
          "SW2..SW0 (`dir_p`) se elige el determinante (`dir_p` = 0) o el pivote *k* (`dir_p` = 1 a *n*). "
          "La conversión de binario a decimal la hace un segundo ASM con el algoritmo XS3 (sumar 3 y correr).")
    inf.P("Condiciones del taller y del curso que se cumplieron en el diseño:")
    inf.lista([
        "Un solo multiplicador y un solo sumador/restador para las operaciones de Bareiss.",
        "División por restas sucesivas, sin valor absoluto.",
        "Memoria RAM con el modelo del curso (`RAM_memory.vhd`), sin cambios.",
        "Solo tipos `std_logic` y `std_logic_vector`. La librería `std_logic_unsigned` solo se usa en la RAM; "
        "el resto del diseño usa `std_logic_signed`, porque los datos son con signo.",
        "Diagramas ASM en alto nivel y VHDL con el estilo de los ejemplos `ASM_Sumax` y `ASM_contador_unos`: "
        "un solo `process` con `case st is` y, en cada estado, las operaciones de su caja.",
        "Herramienta Xilinx ISE 14.7; FPGA Artix-7 XC7A100T-1CSG324 de la Nexys A7-100T; reloj de 100 MHz.",
    ])

    # ------------------------------------------------------------ 2 análisis
    inf.H1("2. Análisis del problema y planteamiento de la solución")
    inf.H2("2.1 Algoritmo de Bareiss")
    inf.P("El método de Bareiss es una eliminación gaussiana en la que todas las divisiones son exactas, así que "
          "se trabaja solo con enteros. Para cada paso *k* = 1 … *n* − 1 y para cada *i*, *j* = *k* + 1 … *n*:"
          ).paragraph_format.keep_with_next = True
    inf.P("a(i,j)  ←  [ a(k,k) · a(i,j)  −  a(i,k) · a(k,j) ]  /  p", alin=WD_ALIGN_PARAGRAPH.CENTER, tam=12)
    inf.P("donde *p* = 1 en el primer paso y *p* = a(k−1,k−1), el pivote del paso anterior, en los demás. Cada "
          "a(i,j) nuevo es un menor de la matriz original, por eso la división da exacta. Al terminar, a(n,n) es "
          "el determinante. Los pivotes a(1,1), a(2,2), …, a(n−1,n−1) y a(n,n) = det son los valores que se "
          "guardan en el banco de pivotes y que se pueden ver con `dir_p`.")
    inf.H2("2.2 Ejemplo con la matriz 3 × 3 del documento del taller")
    inf.P("Con A = [2 1 3; 1 4 2; 3 2 5] el cálculo queda así:")
    inf.tabla("ej3", "Cálculo de Bareiss para la matriz de ejemplo",
              ["Paso", "p", "Pivote a(k,k)", "Operaciones", "Resultado"],
              [["k = 1", "1", "2", "a22 = (2·4 − 1·1)/1 = 7;  a23 = (2·2 − 1·3)/1 = 1;<br>"
                "a32 = (2·2 − 3·1)/1 = 1;  a33 = (2·5 − 3·3)/1 = 1", "[2 1 3; 1 7 1; 3 1 1]"],
               ["k = 2", "2", "7", "a33 = (7·1 − 1·1)/2 = 6/2 = 3", "[2 1 3; 1 7 1; 3 1 3]"]],
              [1.4, 0.9, 2.1, 7.6, 4.5], tam=9, centrar=(0, 1, 2))
    # python-docx no interpreta <br>: se reemplaza después
    inf.P("El determinante es a33 = 3 y los pivotes son 2, 7 y 3. Por cofactores: 2(20 − 4) − 1(5 − 6) + "
          "3(2 − 12) = 3. Los elementos de la fila *k* y de la columna *k* no cambian; el ASM no los pone en cero "
          "porque no los vuelve a usar.")
    inf.H2("2.3 Pivote cero")
    inf.P("Si a(k,k) = 0 no se puede usar como pivote. El ASM busca la primera fila *i* > *k* con a(i,k) ≠ 0 e "
          "intercambia las filas *i* y *k* (columnas *k* a *n*; las anteriores ya no se usan). Cada intercambio "
          "cambia el signo del determinante, por eso se lleva el registro `signo`. Si ninguna fila sirve, la "
          "columna *k* es cero desde la diagonal hacia abajo y el determinante es 0. En el último paso, si hubo "
          "un número impar de intercambios, la última división se hace con el sentido del cociente invertido, "
          "así a(n,n) sale con el signo correcto y es directamente el determinante.")
    inf.P("Ejemplo: la matriz de prueba 2, [" + matriz_txt(M.MATRICES[2]) + "], tiene a11 = 0. Se intercambian "
          "las filas 1 y 2, `signo` queda en 1 y el resultado es det = −22 (pivotes 2, 4, 13, −22).")
    inf.H2("2.4 División por restas sucesivas")
    inf.P("El numerador queda en el registro *r* y el divisor *p* en el registro *s*. En lugar de tomar el valor "
          "absoluto, se escoge el valor *t* al que debe llegar *r* y el sentido del contador `cociente`:")
    inf.tabla("div", "Casos de la división r / p por restas sucesivas (r ← r − p en cada ciclo)",
              ["Signos de r y p", "t", "r inicial", "Recorrido de r", "cociente"],
              [["iguales (ms = 1)", "0", "r", "baja (o sube) hasta 0", "+1 por resta"],
               ["distintos (ms = 0)", "r", "0", "va de 0 hasta el numerador", "−1 por resta"]],
              [3.6, 1.2, 2.0, 5.7, 3.0], centrar=(1, 2, 4))
    inf.P("Ejemplos: 6 / 2: *r* = 6 → 4 → 2 → 0, cociente = 3. −6 / 2: *t* = −6 y *r* = 0 → −2 → −4 → −6, "
          "cociente = −3. 6 / −2: *t* = 6 y *r* = 0 → 2 → 4 → 6, cociente = −3. Como la división de Bareiss es "
          "exacta, *r* siempre llega a *t*. La división tarda tantos ciclos como el valor absoluto del cociente.")
    inf.H2("2.5 Hardware disponible y tamaño de los datos")
    inf.P("El procesador tiene una ROM de 32 × 6 bits con la matriz, dos RAM de 32 × 32 bits (modelo del curso: "
          "escritura síncrona y lectura asíncrona), un multiplicador de 25 × 25 bits, un restador de 50 bits, "
          "los contadores de índices y el contador del cociente. Las dos RAM se escriben siempre juntas (mismo "
          "`data`, `wr_add` y `we`), así que guardan lo mismo: la RAM A se lee con la dirección de a(i,j) y la "
          "RAM B con la de a(k,j). Así se leen dos elementos en el mismo ciclo, lo que necesita el intercambio "
          "de filas (s4), sin poner un MUX en la dirección de lectura.")
    inf.tabla("bits", "Tamaño de los datos",
              ["Dato", "Bits", "Razón"],
              [["Elementos de la ROM", "6", "Complemento a 2, de −32 a 31"],
               ["a(i,j) en las RAM, piv, p, aik, tmp, cociente, det, b1..b4", "32",
                "Cada valor es un menor de hasta 5 × 5. Por la cota de Hadamard, |det| ≤ (√5 · 32)^5^ ≈ "
                "1,88 × 10^9^ < 2^31^"],
               ["x, y (entradas del multiplicador)", "25",
                "Los factores son menores de tamaño k ≤ 4: |menor| ≤ (2 · 32)^4^ = 2^24^, y la cota no se "
                "alcanza porque +32 no existe en 6 bits"],
               ["r, s, t (restador y división)", "50", "Producto de dos números de 25 bits; la resta de dos "
                "productos también cabe en 50 bits con signo"],
               ["n, i, j, k", "3", "Valores de 1 a 5"],
               ["dira", "5", "Direcciones 00h a 19h de la ROM"]],
              [5.4, 1.2, 9.9], centrar=(1,))
    inf.H2("2.6 Organización de la ROM y de las RAM")
    inf.P("La ROM sigue la Figura 1 del taller: 00h = *n*, 01h = a11, 02h = a21, …, es decir, por columnas. En "
          "las RAM, a(f,c) se guarda en la dirección `f & c(1..0)` para las columnas 1 a 4 y en `\"11\" & f` "
          "para la columna 5. La dirección se arma juntando bits, sin sumadores, y las dos zonas no se cruzan "
          "(04h a 17h y 19h a 1Dh):")
    filas_dir = []
    for f in range(1, 6):
        filas_dir.append([f"fila {f}"] + [f"{U.dir_ram(f, c):02X}h" for c in range(1, 6)])
    inf.tabla("ram", "Dirección de a(f,c) en la RAM A y en la RAM B", ["", "c = 1", "c = 2", "c = 3", "c = 4",
                                                                       "c = 5"],
              filas_dir, [2.2] + [2.0] * 5, centrar=tuple(range(1, 6)), negrita_col0=True)

    # --------------------------------------------------------- 3 caja negra
    inf.H1("3. Caja negra")
    inf.P(f"La {inf.F('cn_sis')} muestra el sistema completo en la tarjeta y la {inf.F('cn_proc')}, el "
          f"procesador de Bareiss solo. Los puertos y los pines están en la {inf.T('pines')} y la "
          f"{inf.T('puertos_p')}.")
    inf.figura("cn_sis", "caja_negra_sistema.png", "Caja negra del sistema (entidad `det_bareiss`)", ancho=15)
    inf.tabla("pines", "Puertos del sistema y pines de la Nexys A7-100T (archivo `nexys_a7.ucf`)",
              ["Puerto", "Dir.", "Bits", "Pin (elemento)", "Descripción"],
              [["CLK", "E", "1", "E3", "Reloj de 100 MHz"],
               ["RST", "E", "1", "M18 (BTNU)", "Reinicio asíncrono de todo el diseño"],
               ["INICIO", "E", "1", "N17 (BTNC)", "Comienza el cálculo; pasa por el antirrebote"],
               ["DIR_P[2:0]", "E", "3", "J15, L16, M13 (SW0..SW2)", "0: determinante; 1 a n: pivote k"],
               ["SEG[6:0]", "S", "7", "T10, R10, K16, K13, P15, T11, L18 (CA..CG)", "Segmentos, activos en bajo"],
               ["AN[7:0]", "S", "8", "J17, J18, T9, J14, P14, T14, K2, U13", "Ánodos, activos en bajo; AN7 = signo"],
               ["DP", "S", "1", "H15", "Punto decimal, siempre apagado"],
               ["FINAL", "S", "1", "H17 (LD0)", "Fin del cálculo"],
               ["DESBORDE", "S", "1", "K15 (LD1)", "El valor mostrado tiene más de 7 dígitos"],
               ["LATIDO", "S", "1", "V11 (LD15)", "Onda de 1 s: muestra que el diseño está funcionando"]],
              [2.3, 0.9, 1.0, 5.6, 6.7], tam=8.5, centrar=(1, 2), negrita_col0=True)
    inf.figura("cn_proc", "caja_negra_procesador.png", "Caja negra del procesador de Bareiss "
               "(entidad `procesador_bareiss`)", ancho=13.5)
    inf.tabla("puertos_p", "Puertos del procesador de Bareiss",
              ["Puerto", "Dir.", "Bits", "Descripción"],
              [["clk", "E", "1", "Reloj de 100 MHz"],
               ["rst", "E", "1", "Reinicio asíncrono: lleva el ASM a s0 y borra los registros"],
               ["inicio", "E", "1", "Pulso de un ciclo (del antirrebote) que arranca el cálculo en s0 o en s13"],
               ["dir_p", "E", "3", "Pivote que sale por `pivote`: 1 a n; el pivote n es el determinante"],
               ["det", "S", "32", "Determinante en complemento a 2"],
               ["pivote", "S", "32", "Pivote elegido con `dir_p` (0 si dir_p = 0 o dir_p > n)"],
               ["final", "S", "1", "1 en el estado s13: el cálculo terminó y det es válido"]],
              [2.0, 1.0, 1.0, 12.5], centrar=(1, 2), negrita_col0=True)

    # ----------------------------------------------------- 4 pseudoalgoritmo
    inf.H1("4. Pseudoalgoritmo")
    inf.P("El pseudoalgoritmo ya usa el hardware disponible: los nombres son los de los registros y las "
          "operaciones de multiplicación y resta son las del multiplicador y del restador.")
    inf.codigo("""\
espera:   final = 0;  esperar inicio = 1
          n ← ROM(00h);  dira ← 1
          para j = 1..n, i = 1..n:  RAM(i,j) ← ROM(dira);  dira ← dira + 1
          p ← 1;  signo ← 0
para k = 1 .. n−1:
     piv ← a(k,k)
     si piv = 0:
          buscar la primera fila i > k con a(i,k) ≠ 0
          si no existe:  det ← 0;  ir a fin
          para j = k..n:  intercambiar a(i,j) y a(k,j)       (con tmp)
          signo ← not signo;  volver a leer piv ← a(k,k)
     banco(k) ← piv
     para i = k+1 .. n:
          aik ← a(i,k)
          para j = k+1 .. n:
               x ← piv;  y ← a(i,j);   r ← x·y               (multiplicador)
               x ← aik;  y ← a(k,j);   s ← x·y               (multiplicador)
               r ← r − s;  s ← p;  cociente ← 0              (restador)
               si r y s tienen el mismo signo:  t ← 0
               si no:                           t ← r;  r ← 0
               sq ← signo(r) xor signo(s)        (invertido si k+1 = n y signo = 1)
               mientras r ≠ t:  r ← r − s;  cociente ← cociente ± 1   (− si sq = 1)
               a(i,j) ← cociente
     p ← piv
det ← a(n,n) = último cociente
fin:      final = 1;  si inicio = 1 volver a copiar la ROM y calcular""", tam=8.3)

    # ------------------------------------------------------------- 5 ASM
    inf.H1("5. Diagrama ASM del procesador")
    inf.P(f"El ASM tiene 14 estados (s0 a s13) y se dibuja en cuatro hojas. Las cajas rectangulares son los "
          f"estados con sus operaciones, los rombos las decisiones y las cajas redondeadas naranjas las "
          f"salidas condicionales. El recuadro punteado agrupa cada bloque ASM (un estado con sus decisiones y "
          f"salidas condicionales) y los conectores blancos indican de qué estado viene o a cuál va una flecha. "
          f"La {inf.T('estados')} resume lo que hace cada estado.")
    inf.tabla("estados", "Estados del ASM del procesador", ["Estado", "Operaciones"],
              [[e, U.OPERACIONES_P[e]] for e in U.ESTADOS_P], [1.5, 15.0], tam=9, centrar=(0,),
              negrita_col0=True)
    inf.figura("asm1", "asm_bareiss_1.png", "ASM del procesador, hoja 1: espera de inicio (s0) y copia de la "
               "ROM en las RAM (s1)", ancho=12)
    inf.figura("asm2", "asm_bareiss_2.png", "ASM del procesador, hoja 2: pivote (s2), búsqueda de fila (s3) e "
               "intercambio de filas (s4 y s5)", ancho=13.5)
    inf.figura("asm3", "asm_bareiss_3.png", "ASM del procesador, hoja 3: productos (s6 a s9), numerador (s10) y "
               "preparación de la división (s11)", ancho=12.5)
    inf.figura("asm4", "asm_bareiss_4.png", "ASM del procesador, hoja 4: división por restas sucesivas, avance "
               "de j, i y k (s12) y fin (s13)", ancho=13.5)
    inf.P("**Verificación de las reglas del ASM.** El script `informe/fuentes/fig_asm.py` recorre los caminos de "
          "cada bloque del dibujo y los compara con la tabla de transiciones de la unidad de control "
          "(`uc_cd.py`). Se comprobó que (1) para cada combinación de las decisiones de un estado hay un solo "
          "camino, (2) ningún registro se asigna dos veces en el mismo camino, (3) todos los caminos terminan "
          "en un estado y (4) los estados siguientes del dibujo son los de la tabla y los del VHDL. El ASM tiene "
          f"{filas_p} caminos de salida; si se juntan los de s11, que solo cambian salidas condicionales y "
          f"siempre van a s12, quedan {n_trans} transiciones, el mismo número que reporta XST "
          f"(`Transitions {n_trans}`).")

    # ------------------------------------------------------------ 6 señales
    inf.H1("6. Señales de la unidad de control y del camino de datos")
    inf.P(f"A partir del ASM se separan la unidad de control (UC) y el camino de datos (CD). La UC recibe "
          f"`inicio` y las señales de estado del CD ({inf.T('estado_p')}) y entrega la palabra de control PC "
          f"de {U.BITS_PC_P} bits ({inf.T('pc_p')}) y la salida `final`. El CD tiene los registros de la "
          f"{inf.T('regs_p')} y las señales internas de la {inf.T('internas_p')}.")
    inf.tabla("estado_p", "Señales de estado (del CD a la UC)",
              ["Señal", "Pregunta del ASM", "Bloque del CD que la genera", "Estados"],
              [list(s) for s in U.SENALES_P], [1.5, 3.0, 9.3, 2.7], tam=9, negrita_col0=True)
    inf.tabla("pc_p", f"Campos de la palabra de control del procesador ({U.BITS_PC_P} bits, de la UC al CD)",
              ["Campo", "Bits", "Controla", "Códigos"],
              [[c[0], c[1], c[3], c[4]] for c in U.CAMPOS_P], [1.9, 0.9, 4.4, 9.3], tam=8.5, centrar=(1,),
              negrita_col0=True)
    inf.tabla("regs_p", "Registros del camino de datos del procesador",
              ["Registro", "Bits", "Carga", "Selector", "Contenido", "Estados que lo escriben"],
              [[r[0], r[1], r[2], r[3] or "—", r[4], r[5]] for r in U.REGISTROS_P],
              [1.8, 1.0, 1.6, 1.6, 6.2, 4.3], tam=8.5, centrar=(1, 2, 3), negrita_col0=True)
    inf.tabla("internas_p", "Señales internas (combinacionales) del camino de datos y de la UC",
              ["Señal", "Bits", "Descripción"],
              [["a", "6", "Salida de la ROM en la dirección dira"],
               ["data", "32", "Dato que se escribe en las dos RAM (MUX sel_d: a con extensión de signo, qb, tmp o "
                "cociente)"],
               ["wr_add", "5", "Dirección de escritura (MUX sel_w: dir_ij o dir_kj)"],
               ["dir_ij, dir_kj", "5", "Direcciones de lectura de a(i,j) (RAM A) y de a(k,j) (RAM B)"],
               ["qa, qb", "32", "Salidas de la RAM A y de la RAM B"],
               ["x·y", "50", "Salida del multiplicador"],
               ["r − s", "50", "Salida del restador"],
               ["i+1, j+1, k+1, dira+1", "3 / 5", "Salidas de los incrementadores"],
               ["cociente ± 1", "32", "Salida del contador ascendente/descendente"],
               ["Q, D", "4", "Estado actual y estado siguiente de la UC (registro de estado)"]],
              [3.4, 1.3, 11.8], tam=9, centrar=(1,), negrita_col0=True)

    # ------------------------------------------------------- 7 camino de datos
    inf.H1("7. Camino de datos")
    inf.P("El camino de datos sale de las operaciones de las cajas del ASM: cada registro que se asigna en alguna "
          "caja tiene una carga `ld_` y, si recibe más de un valor, un MUX con su selector `sel_`. Las figuras "
          "siguientes lo dibujan como circuito, por partes. Los cables con el mismo nombre en dos figuras son el "
          "mismo cable; los controles en rojo vienen de la palabra de control y las señales en azul van a la UC.")
    inf.figura("cd_ind", "cd_indices.png", "Camino de datos: dirección de la ROM, índices y direcciones de lectura")
    inf.P("Los índices i, j y k se cargan desde un MUX con las constantes y los incrementos que pide el ASM (por "
          "ejemplo, j recibe 1, j + 1, k o k + 1). Los comparadores dan i_n, j_n y k1_n; este último usa la "
          "salida del incrementador de k, así no se necesita otro sumador. El comparador j = 5 elige el formato "
          "de las direcciones de lectura: dir_ij va a la RAM A y dir_kj a la RAM B.")
    inf.figura("cd_mem", "cd_memorias.png", "Camino de datos: ROM, RAM A, RAM B y registros que se cargan desde "
               "las RAM")
    inf.P("La ROM entrega el elemento de 6 bits; la extensión de signo lo pasa a 32 bits para escribirlo en las "
          "RAM en s1. El MUX sel_d escoge el dato de escritura y sel_w la dirección; las dos RAM comparten data, "
          "wr_add y we. Las salidas qa y qb van a los comparadores con cero (z_a, z_b) y a los registros aik, "
          "tmp y piv.")
    inf.figura("cd_arit", "cd_aritmetica.png", "Camino de datos: multiplicador, restador y valor final de la "
               "división")
    inf.P("Hay un solo multiplicador y un solo restador. Los registros x e y son sus entradas: en s7 reciben piv "
          "y a(i,j) y en s8, aik y a(k,j). El producto entra a r (s8) o a s (s9). El restador siempre calcula "
          "r − s y su salida vuelve a r: en s10 da el numerador y en s12 hace las restas de la división, con "
          "s = p extendido a 50 bits. El registro t guarda el valor al que debe llegar r; el comparador r = t "
          "genera rt y la compuerta XNOR de los bits de signo genera ms.")
    inf.figura("cd_div", "cd_division.png", "Camino de datos: sentido del cociente, contador cociente, signo, "
               "banco de pivotes y salidas")
    inf.P("El registro sq guarda el sentido del contador: r(49) ⊕ s(49), o su negación en el último paso si "
          "hubo un número impar de intercambios. El contador cociente suma 1 si sq = 0 y resta 1 si sq = 1. El "
          "banco b1..b4 se escribe con qb en s2, en la posición que indica k (decodificador habilitado por "
          "we_b). La salida pivote es det cuando dir_p = n, el registro b(dir_p) para dir_p = 1..4 y 0 en otro "
          "caso.")

    # ----------------------------------------------------------- 8 caja gris
    inf.H1("8. Caja gris")
    inf.P(f"La {inf.F('cg_sis')} muestra los cuatro bloques del diseño y cómo se conectan dentro de "
          f"`det_bareiss`. La {inf.F('cg_proc')} separa el procesador en su UC y su CD.")
    inf.figura("cg_sis", "caja_gris_sistema.png", "Caja gris del sistema: divisor de frecuencia, antirrebote, "
               "procesador y visualizador")
    inf.lista([
        "**divisor_frecuencia**: genera `tick_1ms` (un pulso de un ciclo cada 100 000 ciclos) y `onda_1s`. Los "
        "pulsos se usan como habilitación: todo el diseño trabaja con el mismo reloj de 100 MHz.",
        "**antirrebote**: sincroniza BTNC, lo muestrea cada 1 ms y entrega un solo pulso de inicio por "
        "pulsación (8 muestras iguales para cambiar de nivel).",
        "**procesador_bareiss**: el ASM de Bareiss; entrega det, pivote y final en binario.",
        "**visualizador**: ASM XS3 y display; trabaja en paralelo con el procesador y tiene sus propias "
        "unidades (no comparte el restador ni el multiplicador).",
    ])
    inf.figura("cg_proc", "caja_gris_procesador.png", "Caja gris del procesador: unidad de control y camino de "
               "datos", ancho=14)

    # ------------------------------------------------------------- 9 UC
    inf.H1("9. Diseño de la unidad de control")
    inf.P(f"La UC es una máquina de Mealy con la estructura del curso ({inf.F('uc_p')}): un registro de estado "
          f"de 4 flip-flops (14 estados), una ROM de entrada que calcula el estado siguiente y una ROM de salida "
          f"que entrega la palabra de control. Las salidas condicionales del ASM dependen de las señales de "
          f"estado, por eso la ROM de salida también las recibe.")
    inf.figura("uc_p", "uc_procesador.png", "Unidad de control del procesador", ancho=16)
    inf.lista([
        f"**ROM de entrada**: dirección = Q (4 bits) + {len(o_sig)} señales ({', '.join(o_sig)}) = "
        f"{4 + len(o_sig)} bits → {bits_e} × 4. Se dejaron solo las señales que cambian el estado siguiente "
        f"en algún estado; ms y sg no lo cambian (en s11 siempre se va a s12).",
        f"**ROM de salida**: dirección = Q + {len(o_pc)} señales = {4 + len(o_pc)} bits → {bits_s} × "
        f"{U.BITS_PC_P + 1} ({U.BITS_PC_P} bits de PC y final).",
    ])
    inf.P(f"La {inf.T('rom_e')} y la {inf.T('rom_s')} tienen una fila por cada camino del ASM. Un guion (–) "
          f"indica que la señal no importa en ese estado: esa fila llena todas las direcciones de la ROM con "
          f"cualquier valor de la señal. Los códigos de estado son binarios en orden (s0 = 0000 … s13 = 1101), "
          f"la misma codificación que eligió XST.")
    tabla_rom_entrada(inf, "rom_e", f"ROM de entrada de la UC del procesador ({len(r_sig)} filas)", U.FILAS_P,
                      U.CAMPOS_P, U.SENALES_P, U.ESTADOS_P)
    orden_campos = " · ".join(f"**{g}**: " + ", ".join(c) for g, c in GRUPOS_P)
    inf.P(f"Orden de los campos en la {inf.T('rom_s')} (los selectores de 2 bits se escriben juntos; X = no "
          f"importa): {orden_campos}.", tam=9.5)
    tabla_rom_salida(inf, "rom_s", f"ROM de salida de la UC del procesador ({len(r_pc)} filas)", U.FILAS_P,
                     U.CAMPOS_P, U.SENALES_P, GRUPOS_P, U.FINAL_P, U.ESTADOS_P,
                     [1.0, 3.0, 3.1, 3.1, 4.4, 1.1, 0.8])
    inf.P("**Comprobación.** `informe/fuentes/uc_cd.py` simula ciclo a ciclo este CD manejado solo por las "
          "tablas de la UC. Con las matrices de prueba 0 a 6 da el mismo determinante, los mismos pivotes y el "
          "mismo número de ciclos que la simulación del VHDL (el modelo cuenta 2 ciclos más porque empieza a "
          "contar un flanco antes y termina un flanco después).")

    # ------------------------------------------------------- 10 visualizador
    inf.H1("10. Visualizador XS3 y bloques auxiliares")
    inf.H2("10.1 Algoritmo XS3")
    inf.P("Para pasar el valor binario de 32 bits a 10 dígitos BCD se usa el algoritmo de sumar 3 (XS3): el "
          "registro decimal empieza en 0; en cada iteración entra un bit del binario por la derecha, a cada "
          "dígito mayor que 4 se le suma 3 y luego los dos registros se corren a la izquierda. Sumar 3 antes de "
          "correr equivale a sumar 6 después, que es la corrección de un dígito BCD que pasa de 9. El "
          "visualizador primero toma el valor absoluto (0 − val si es negativo) y guarda el signo aparte.")
    inf.tabla("xs3_ej", "Ejemplo del XS3 con 4 bits: 1101 (13)",
              ["Iteración", "Bit que entra", "Decimal después de entrar el bit", "Dígito > 4", "Después de correr"],
              [["1", "1", "0000 0001", "no", "0000 0010"],
               ["2", "1", "0000 0011", "no", "0000 0110"],
               ["3", "0", "0000 0110", "6 + 3 = 9 → 0000 1001", "0001 0010"],
               ["4", "1", "0001 0011 = 13", "—", "fin (último bit)"]],
              [1.7, 2.0, 4.6, 4.2, 4.0], tam=9, centrar=(0, 1), mono=())
    inf.H2("10.2 ASM del XS3")
    inf.P("El ASM tiene 6 estados, uno por cada paso del algoritmo. Mientras `final` = 0 espera en x0; cuando "
          "el procesador termina, convierte una y otra vez el valor elegido con `dir_p`, así el display sigue "
          "a los switches. Cada conversión tarda 376 ciclos: x0 y x1 (2), 31 iteraciones de x2, diez veces x3 "
          "y x4 (31 × 12 = 372) y la última pasada por x2 y x5 (2).")
    inf.figura("asm_xs3", "asm_xs3.png", "ASM del visualizador (algoritmo XS3)", ancho=12.5)
    inf.tabla("estados_v", "Estados del ASM XS3", ["Estado", "Operaciones"],
              [[e, U.OPERACIONES_V[e]] for e in U.ESTADOS_V], [1.5, 15.0], tam=9, centrar=(0,),
              negrita_col0=True)
    inf.tabla("estado_v", "Señales de estado del visualizador",
              ["Señal", "Pregunta del ASM", "Bloque del CD que la genera", "Estados"],
              [list(s) for s in U.SENALES_V], [1.7, 2.8, 10.0, 2.0], tam=9, negrita_col0=True)
    inf.tabla("pc_v", f"Campos de la palabra de control del visualizador ({U.BITS_PC_V} bits)",
              ["Campo", "Bits", "Controla", "Códigos"],
              [[c[0], c[1], c[3], c[4]] for c in U.CAMPOS_V], [1.9, 0.9, 3.4, 10.3], tam=8.5, centrar=(1,),
              negrita_col0=True)
    inf.tabla("regs_v", "Registros del visualizador",
              ["Registro", "Bits", "Carga", "Selector", "Contenido", "Estados"],
              [[r[0], r[1], r[2], r[3] or "—", r[4], r[5]] for r in U.REGISTROS_V],
              [2.4, 1.0, 1.6, 1.7, 6.0, 3.8], tam=8.5, centrar=(1, 2, 3), negrita_col0=True)
    inf.H2("10.3 Camino de datos y unidad de control del visualizador")
    inf.figura("cd_xs3", "cd_xs3.png", "Camino de datos del XS3")
    inf.P("El MUX de entrada elige det (dir_p = 0) o pivote. El restador 0 − val, el sumador +3, el comparador "
          "> 4 y el MUX de dígitos son unidades propias del visualizador. El comparador > 4 recibe el dígito con "
          "un 0 adelante, porque con `std_logic_signed` los valores 8 y 9 de 4 bits se leerían como negativos.")
    inf.figura("cd_disp", "cd_display.png", "Barrido del display de 8 dígitos")
    inf.P("El display se barre con el contador `dsel`, que avanza con cada `tick` de 1 ms (8 ms por barrido "
          "completo). AN7 muestra el signo menos o queda apagado y AN6..AN0 muestran los 7 dígitos de menor "
          "peso. Si el valor tiene más de 7 dígitos (dígitos 8 a 10 distintos de cero) se enciende DESBORDE.")
    inf.figura("uc_v", "uc_visualizador.png", "Unidad de control del visualizador", ancho=16)
    inf.P(f"El registro de estado tiene 3 flip-flops. La ROM de entrada tiene {3 + len(ov_sig)} bits de "
          f"dirección ({bits_ev} × 3) y la ROM de salida {3 + len(ov_pc)} ({bits_sv} × {U.BITS_PC_V}):")
    tabla_rom_entrada(inf, "rom_ev", f"ROM de entrada de la UC del visualizador ({len(rv_sig)} filas)",
                      U.FILAS_V, U.CAMPOS_V, U.SENALES_V, U.ESTADOS_V)
    tabla_rom_salida(inf, "rom_sv", f"ROM de salida de la UC del visualizador ({len(rv_pc)} filas). Campos: "
                     + " · ".join(f"{g}: " + ", ".join(c) for g, c in GRUPOS_V), U.FILAS_V, U.CAMPOS_V,
                     U.SENALES_V, GRUPOS_V, None, U.ESTADOS_V, [1.3, 5.2, 2.9, 2.6, 2.6, 1.9])
    inf.H2("10.4 Divisor de frecuencia y antirrebote")
    inf.P("El divisor cuenta 100 000 ciclos para el pulso de 1 ms y 500 de esos pulsos para cambiar la onda de "
          "1 s. El antirrebote pasa BTNC por dos flip-flops (sincronización), guarda las últimas 8 muestras "
          "tomadas cada 1 ms y cambia el nivel estable solo con 8 muestras iguales; el pulso de inicio dura un "
          "ciclo y sale en el flanco de subida del nivel estable. El procesador no usa el divisor: con un "
          "reloj de 1 Hz una matriz de 3 × 3 tardaría casi un minuto y la de 5 × 5 más de una hora.")

    # -------------------------------------------------------------- 11 VHDL
    inf.H1("11. Descripción en VHDL")
    inf.tabla("archivos", "Archivos del proyecto (carpeta `src/`)",
              ["Archivo", "Entidad", "Contenido", "Librerías"],
              [["det_bareiss.vhd", "det_bareiss", "Tope: solo conecta los cuatro bloques (port map)",
                "std_logic_1164"],
               ["procesador_bareiss.vhd", "procesador_bareiss", "ASM de Bareiss (process con case st), ROM "
                "(with dira select) y dos instancias de RAM_memory", "std_logic_signed"],
               ["RAM_memory.vhd", "RAM_memory", "Modelo de RAM del curso, sin cambios", "std_logic_unsigned"],
               ["visualizador.vhd", "visualizador", "ASM XS3 y display de 8 dígitos", "std_logic_signed"],
               ["divisor_frecuencia.vhd", "divisor_frecuencia", "Pulso de 1 ms y onda de 1 s",
                "std_logic_signed"],
               ["antirrebote.vhd", "antirrebote", "Antirrebote del botón de inicio", "std_logic_1164"],
               ["nexys_a7.ucf", "—", "Pines y restricción de reloj de 10 ns", "—"]],
              [3.7, 3.2, 6.6, 3.0], tam=8.5)
    inf.P("Cada estado del `case st is` tiene las operaciones de su caja del ASM. El multiplicador se escribe "
          "siempre como `x * y` (en s8 y s9) y el restador como `r <= r - s` (en s10 y s12), sobre los mismos "
          "registros, así XST arma una sola unidad de cada una. Por ejemplo, el estado s12:")
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
    inf.P("La escritura en las RAM (`we`, `wr_add` y `data`) se describe fuera del process, con asignaciones "
          "concurrentes que dependen del estado, porque la RAM del curso es una entidad aparte. El código "
          "completo está en el Anexo A.")
    inf.tabla("xst", "Lo que se esperaba del diseño y lo que reconoció XST",
              ["Bloque", "Se esperaba", "XST / Map reconoció"],
              [["ASM del procesador", f"14 estados, {n_trans} transiciones, 7 entradas (inicio, z_b, z_a, i_n, "
                "j_n, k1_n, rt)", f"FSM de 14 estados, {n_trans} transiciones, 7 entradas; codificación "
                "binaria s0 = 0000 … s13 = 1101"],
               ["Multiplicador", "Uno de 25 × 25 bits", "1 multiplicador 25x25-bit; en Map, 2 DSP48E1"],
               ["Sumador/restador", "Uno de 50 bits (r − s)", "1 restador de 50 bits"],
               ["Contador cociente", "Ascendente/descendente de 32 bits", "1 contador updown de 32 bits"],
               ["RAM A y RAM B", "Dos RAM de 32 × 32, lectura asíncrona", "RAM distribuida (INFO Xst:3218); "
                "en Map, 48 LUT como RAM de doble puerto"],
               ["ASM del XS3", f"6 estados, {n_trans_v} transiciones, 3 entradas (final, cont_31, d_9)",
                f"FSM de 6 estados, {n_trans_v} transiciones, 3 entradas"],
               ["Flip-flops", f"{ff_total} bits de registro en el VHDL: {ff_p} del procesador (con 4 de "
                "estado), {ff_v} del visualizador, 27 del divisor y 12 del antirrebote",
                f"702 = {ff_total} − 7 (aik(31..25), sin uso) − 2 (dsel(1..0), iguales a cuenta_ms(1..0))"]],
              [3.0, 6.3, 7.2], tam=8.5, negrita_col0=True)
    inf.P("Las capturas del esquema RTL de ISE (*View RTL Schematic*) van en las figuras siguientes.")
    inf.hueco("rtl_top", "Esquema RTL del tope `det_bareiss` en ISE",
              "[ Pegar aquí la captura de ISE: Synthesize – XST → View RTL Schematic → det_bareiss ]")
    inf.hueco("rtl_proc", "Esquema RTL de `procesador_bareiss` en ISE",
              "[ Pegar aquí la captura del RTL de procesador_bareiss (doble clic sobre el bloque U_PROC) ]")
    inf.hueco("rtl_vis", "Esquema RTL de `visualizador` en ISE",
              "[ Pegar aquí la captura del RTL del visualizador (bloque U_VIS) ]")

    # ---------------------------------------------------- 12 síntesis
    inf.H1("12. Resultados de síntesis e implementación")
    inf.P("Proyecto en ISE 14.7 para la XC7A100T-1CSG324 (Artix-7, velocidad −1) con la restricción de reloj "
          "`TS_sys_clk` de 10 ns (100 MHz). La síntesis, Translate, Map, Place & Route y la generación del "
          "archivo .bit terminaron sin errores y se cumplieron todas las restricciones.")
    inf.tabla("recursos", "Resultados de síntesis (XST), Map y Place & Route",
              ["Etapa", "Dato", "Valor"],
              [["Síntesis", "Flip-flops", "702"],
               ["Síntesis", "Periodo mínimo estimado", "7,012 ns (142,613 MHz)"],
               ["Map", "Slice Registers", "702 de 126 800 (1 %)"],
               ["Map", "Slice LUTs", "878 de 63 400 (1 %)"],
               ["Map", "LUT usadas como RAM de doble puerto", "48 (RAM A y RAM B)"],
               ["Map", "Slices ocupados", "303 de 15 850"],
               ["Map", "IOB", "25 de 210 (11 %)"],
               ["Map", "BUFG", "1"],
               ["Map", "DSP48E1", "2 de 240 (el multiplicador 25 × 25)"],
               ["PAR", "TS_sys_clk = 10 ns", "Cumplida: peor holgura de setup 1,206 ns"],
               ["PAR", "Mejor periodo alcanzable", "8,794 ns (≈ 113,7 MHz)"],
               ["PAR", "Holgura de hold", "0,058 ns"],
               ["PAR", "Resultado", "All constraints were met"]],
              [2.2, 6.2, 8.1], tam=9, centrar=(0,))
    inf.P("El diseño ocupa cerca del 1 % de la FPGA. El camino más lento después de Place & Route deja 1,2 ns "
          "de holgura con el reloj de 100 MHz. La síntesis estimaba 7,0 ns; la diferencia es el retardo de "
          f"las rutas, que XST no conoce. Los 702 flip-flops coinciden con la cuenta de las tablas de registros: "
          f"{ff_total} bits en el VHDL, menos los 7 bits altos de aik que no se usan y los 2 bits de dsel que XST "
          f"une con los de cuenta_ms ({inf.T('avisos')}).")
    inf.tabla("avisos", "Advertencias e informaciones de ISE y su explicación",
              ["Mensaje", "Explicación"],
              [["Xst:2677: aik<31:25> sin conexión", "El multiplicador solo usa los 25 bits bajos de aik; los "
                "7 bits altos no van a ningún lado y XST los quita. No afecta el resultado."],
               ["Par:288 y PhysDesignRules:367 (10 señales RAMD_D1_O sin carga)", "Salidas de las primitivas "
                "RAM32M de la RAM distribuida que no se usan; se quedan sin conectar."],
               ["INFO HDLCompiler:679 (línea 186): `others` nunca se selecciona", "En el visualizador los 6 "
                "estados ya están en el case; el `when others` sobra pero no hace daño."],
               ["INFO Xst:3218: RAM distribuida", "La RAM del curso tiene lectura asíncrona, así que XST la "
                "arma con LUT y no con bloques de RAM. Era lo esperado."],
               ["Xst:2261: dsel_0/1 equivalentes a cuenta_ms_0/1", "El contador del display y el de "
                "milisegundos avanzan con el mismo tick desde el reset; como 500 es múltiplo de 4, sus dos "
                "bits bajos son iguales y XST deja un solo par de flip-flops."],
               ["Security:42", "Aviso de licencia de ISE; no tiene que ver con el diseño."]],
              [5.6, 10.9], tam=8.5)

    # ---------------------------------------------------- 13 simulación
    inf.H1("13. Simulación")
    inf.P("Para las figuras se usó el testbench sencillo `sim/tb_informe.vhd`: conecta el procesador con el "
          "visualizador, pone `rst` = 1 durante 20 ns, da un pulso de `inicio` de un ciclo, espera `final` = 1 "
          "y recorre `dir_p` = 1 … n. El reloj es de 10 ns (100 MHz). Las ondas se simularon con GHDL 4.1 y se "
          "dibujaron con el formato de la ventana de ondas de ISim; se pueden reemplazar por capturas de ISim "
          "con el mismo testbench.")
    s3 = M.bareiss(M.MATRICES[1])
    inf.H2("13.1 Matriz 3 × 3 del ejemplo")
    inf.figura("sim3", "sim_3x3.png", "Simulación con la matriz [2 1 3; 1 4 2; 3 2 5]", nativo=False, alto_max=22)
    inf.P(f"En la {inf.F('sim3')} se ve la copia de la ROM en s1 (i recorre 1, 2, 3 para cada j), los dos "
          f"pasos de Bareiss (k = 1 y k = 2) y las divisiones en s12, donde el cociente cuenta 7, 1, 1, 1 y "
          f"por último 3. `final` sube a los {ghdl[1]} ciclos del pulso de inicio y `det` = {s3[0]}. Al mover "
          f"`dir_p` de 1 a 3, `pivote` muestra {', '.join(map(str, s3[1]))}, igual que el cálculo a mano de la "
          f"{inf.T('ej3')}.")
    inf.H2("13.2 Matriz 4 × 4 con pivote cero")
    s4 = M.bareiss(M.MATRICES[2])
    inf.figura("sim4", "sim_4x4_cero.png", "Simulación con la matriz [" + matriz_txt(M.MATRICES[2]) +
               "], que tiene a11 = 0", nativo=False, alto_max=22)
    inf.P(f"En la parte a) de la {inf.F('sim4')}, después de la copia, s2 lee qb = a(1,1) = 0 y pasa a s3, que "
          f"encuentra a(2,1) = 2 en el primer intento; `signo` sube a 1 y s4 y s5 se repiten cuatro veces para "
          f"intercambiar las columnas 1 a 4 de las filas 1 y 2. En la parte b), la última división cuenta hacia "
          f"abajo porque `signo` = 1, así que a(4,4) queda directamente en {s4[0]}. Los pivotes son "
          f"{', '.join(map(str, s4[1]))}.")
    inf.H2("13.3 Matriz 5 × 5")
    s5 = M.bareiss(M.MATRICES[3])
    inf.figura("sim5", "sim_5x5.png", "Simulación con la matriz 5 × 5 de la ROM [" + matriz_txt(M.MATRICES[3]) +
               "]", nativo=False, alto_max=22)
    inf.P(f"Esta es la matriz que queda en la ROM del proyecto. El cálculo tarda {ghdl[3]} ciclos (37,7 µs); "
          f"la mayor parte del tiempo está en s12, porque las divisiones de los últimos pasos tienen cocientes "
          f"de cientos. Al final det = {s5[0]} y los pivotes son {', '.join(map(str, s5[1]))}.")
    inf.H2("13.4 Visualizador")
    inf.figura("simxs3", "sim_xs3.png", "Conversión XS3 del determinante 362", nativo=False, alto_max=22)
    inf.P(f"En la {inf.F('simxs3')} el ASM XS3 arranca cuando `final` sube: x1 borra el registro decimal y "
          f"después cont avanza de 0 a 31, con diez pasadas por x3 (d = 0 … 9) en cada bit. En b) se ven los "
          f"últimos bits: dec (en hexadecimal) pasa por 0x48 y 0x1B1 hasta 0x362, y en x5 ese valor pasa a disp, "
          f"que el display muestra como 0000362. Entre la suma de 3 y el corrimiento un dígito puede valer más "
          f"de 9 (la C de 0xC0 o la B de 0x1B1); el corrimiento lo devuelve a BCD. La conversión dura 376 ciclos.")
    inf.H2("13.5 Pruebas automáticas")
    inf.P("Además de las figuras, el proyecto tiene testbench que comparan los resultados con un modelo de "
          "referencia: `tb_procesador.vhd` (det y todos los pivotes, con dos corridas seguidas), "
          "`tb_visualizador.vhd` (XS3 y display con valores positivos, negativos y con desborde) y "
          "`tb_det_bareiss.vhd` (tope completo con un botón con rebotes). Los resultados de las 8 matrices de "
          "prueba están en la tabla siguiente; todas pasaron.")
    filas_t = []
    for num, a in enumerate(M.MATRICES):
        det, piv, inter = M.bareiss(a)
        filas_t.append([str(num), f"{len(a)} × {len(a)}", ", ".join(map(str, piv)), str(det),
                        f"{ghdl.get(num, 0):,}".replace(",", " "), "PASA"])
    notas = {0: "", 1: "ejemplo del taller", 2: "a11 = 0", 3: "ROM del proyecto", 4: "intercambio en k = 2",
             5: "pivote cero en k = 2", 6: "columna 1 en cero", 7: "valores extremos"}
    for k, f in enumerate(filas_t):
        if notas[k]:
            f[1] += f" ({notas[k]})"
    inf.tabla("pruebas", "Resultados de `tb_procesador.vhd` con las matrices de prueba (GHDL)",
              ["Matriz", "Tamaño", "Pivotes (dir_p = 1 … n)", "det", "Ciclos", "Resultado"],
              filas_t, [1.3, 4.0, 5.6, 1.9, 2.1, 1.6], tam=8.5, centrar=(0, 3, 4, 5))
    inf.P("La matriz 7 tiene un determinante de 8 dígitos (−17 121 828): el display muestra los 7 de menor peso "
          "y enciende DESBORDE (LD1). Sus divisiones tienen cocientes de millones, por eso tarda 0,19 s.")
    inf.P("**Para repetir la simulación en ISim:** agregar `src/RAM_memory.vhd`, `src/procesador_bareiss.vhd`, "
          "`src/visualizador.vhd` y `sim/tb_informe.vhd` como fuentes de simulación, escoger `tb_informe` y "
          "correr 45 µs (`run 45 us`). Para ver las señales internas se agregan a la ventana de ondas `st`, `k`, "
          "`i`, `j` y `cociente` de `uut`, y `xs`, `bin`, `dec`, `cont` y `disp` de `uvis`. Para otra matriz se "
          "cambia la ROM con `python3 sim/modelo_referencia.py rom 1` (o `rom 2`) y después se deja otra vez la "
          "matriz 3 con `rom 3`.")

    # -------------------------------------------------- 14 conclusiones
    inf.H1("14. Conclusiones")
    inf.lista([
        "Seguir el procedimiento del curso (pseudoalgoritmo con el hardware disponible, ASM, señales, camino "
        "de datos y unidad de control) llevó a un VHDL en el que cada estado del `case` es una caja del ASM. "
        f"XST encontró la misma máquina del diagrama: 14 estados, {n_trans} transiciones y 7 entradas.",
        "Escribir siempre `x * y` y `r - s` sobre los mismos registros hizo que la síntesis armara un solo "
        "multiplicador (2 DSP48E1) y un solo restador de 50 bits, como pide el taller. El costo son los estados "
        "s7 a s10 y los registros de entrada x, y, r y s.",
        "La división por restas sucesivas sin valor absoluto se resolvió cambiando el valor de llegada *t* y el "
        "sentido del contador según los signos. El tiempo depende del cociente: "
        f"{ghdl[1]} ciclos para la matriz 3 × 3 y unos 19 millones (0,19 s) para la matriz de valores extremos.",
        "Con dos RAM del modelo del curso escritas al mismo tiempo se tienen dos puertos de lectura, y con "
        "direcciones armadas por concatenación de bits no hace falta ningún sumador para direccionar la matriz.",
        "El visualizador trabaja en paralelo con el procesador y convierte en 376 ciclos (3,76 µs), así que el "
        "display cambia en cuanto se mueven los switches. El diseño ocupa cerca del 1 % de la FPGA y cumple el "
        "reloj de 100 MHz con 1,2 ns de holgura.",
    ])

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
    inf.salto()
    inf.H1("Anexo A. Código VHDL")
    for archivo in ("procesador_bareiss.vhd", "visualizador.vhd", "det_bareiss.vhd", "RAM_memory.vhd",
                    "divisor_frecuencia.vhd", "antirrebote.vhd"):
        inf.H2(f"src/{archivo}")
        inf.codigo((RAIZ / "src" / archivo).read_text(encoding="utf-8"), tam=7)
    return d


def arreglar_saltos(doc):
    """Convierte '<br>' de los textos en saltos de línea."""
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
    faltan = [k for k in ("Figura ?", "Tabla ?")]
    texto = "\n".join(p.text for p in doc.paragraphs)
    for f in faltan:
        if f in texto:
            print("AVISO: referencia sin resolver:", f)


if __name__ == "__main__":
    main()

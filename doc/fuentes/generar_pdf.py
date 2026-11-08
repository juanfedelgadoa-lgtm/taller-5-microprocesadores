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
from modelo_referencia import MATRICES, bareiss   # noqa: E402

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


def resultados_sim():
    texto = (RAIZ / "sim" / "resultado_ghdl.txt").read_text(encoding="utf-8")
    res = {}
    for m in re.finditer(r"Matriz (\d) \((\dx\d)\): det  display='(.{8})' desborde='(.)'  ciclos=(\d+)  OK", texto):
        res[int(m.group(1))] = (m.group(2), m.group(3), m.group(4), int(m.group(5)))
    return res


def mat_txt(a):
    return "[br]".join("[c]" + " ".join(f"{x:3d}" for x in fila).replace(" ", "\u00a0") + "[/c]" for fila in a)


# ---------------------------------------------------------------------------
# Contenido
# ---------------------------------------------------------------------------
def contenido():
    h = []
    A = h.append

    # Portada -----------------------------------------------------------------
    A(Spacer(1, 1.2 * inch))
    A(P("Universidad Distrital Francisco José de Caldas[br]Ingeniería Electrónica · Análisis y Diseño de Microprocesadores", "subtitulo"))
    A(Spacer(1, 0.5 * inch))
    A(P("TALLER 5", "titulo"))
    A(P("Microprocesador de propósito específico:[br]determinante por el algoritmo de Bareiss[br]con salida BCD (algoritmo XS3)", "titulo"))
    A(Spacer(1, 0.3 * inch))
    A(P("Explicación del diagrama ASM, del camino de datos y del código VHDL", "subtitulo"))
    A(Spacer(1, 0.15 * inch))
    A(P("Herramienta: Xilinx ISE 14.7 (XST, ISim) · Tarjeta: Digilent Nexys A7-100T (XC7A100T-1CSG324C)", "subtitulo"))
    A(Spacer(1, 0.9 * inch))
    A(P("[b]Nota para el equipo.[/b] Este documento explica un diseño de referencia. El enunciado advierte que "
        "los diseños parecidos entre equipos no se califican, así que revisen cada estado, entiendan por qué está "
        "ahí y adáptenlo antes de entregarlo. Las conclusiones del informe son responsabilidad del equipo.", "nota"))
    A(PageBreak())

    toc = TableOfContents()
    toc.levelStyles = [E["toc1"], E["toc2"]]
    toc.tableStyle = TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                 ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)])
    A(P("Contenido", "h1_sin_indice"))
    A(toc)
    A(PageBreak())

    # 1 -----------------------------------------------------------------------
    A(P("1. Resumen del diseño", "h1"))
    A(P("El procesador lee de una ROM una matriz simétrica de 2×2 a 5×5, la copia a una RAM de trabajo y calcula su "
        "determinante con el algoritmo de Bareiss. Usa un multiplicador, un sumador/restador y una división por "
        "restas sucesivas. Guarda los pivotes en un banco de registros y convierte a BCD el valor que se va a mostrar "
        "con el algoritmo XS3 (sumar 3 y desplazar). La unidad de control es un ASM de 27 estados, S0 a S26, "
        "descrito en un solo proceso VHDL con el mismo estilo de los ejemplos de clase ([c]ASM_contador_unos[/c] y "
        "[c]ASM_Sumax[/c]): un [c]type estados_asm[/c], un [c]case st is[/c] y solo señales."))
    A(tabla([
        ["Requisito del taller", "Cómo lo cumple el diseño"],
        ["ASM descrito en VHDL de alto nivel, con señal de inicio y señal de final",
         "Un proceso con [c]case st is[/c] (S0 a S26). [c]final = '1'[/c] solo en S26. El cálculo arranca con [c]inicio[/c] (BTNC)."],
        ["Matriz en ROM: posición 00h = n, luego los a(i,j) como en la Figura 1",
         "ROM de 256 × 6 bits con 8 páginas de 32 palabras. En cada página, 00h = n y los elementos van por columnas "
         "(a11, a21, …, an1, a12, …). [c]dira[/c] de 5 bits; datos en complemento a 2 (−32 a 31)."],
        ["Multiplicador, sumador/restador y división por restas sucesivas",
         "Un multiplicador con signo de 25 × 25 bits, un sumador/restador de 50 bits compartido por todos los estados y "
         "una división por restas sucesivas (estados S16 y S17) que usa ese restador."],
        ["Memoria RAM para las iteraciones", "RAM de 64 × 32 bits; la dirección es fila & columna (3 + 3 bits)."],
        ["Diseño basado en señales", "No hay variables en el diseño (el testbench sí usa variables)."],
        ["Pivotes en un banco de registros, visibles con los switches",
         "Banco de 4 × 32 bits. SW2..SW0 = 0 muestra el determinante; SW2..SW0 = k (1 a 4) muestra el pivote k."],
        ["Determinante en los displays",
         "8 displays: AN7 = signo, AN6..AN0 = 7 dígitos. LD1 se enciende si el valor tiene más de 7 dígitos."],
        ["XS3 evidenciado paso a paso en el ASM",
         "Estados S22 a S25: un estado por cada paso del documento XS3 (paso 1 = S22, paso 2 = S23, paso 3 = S24, "
         "paso 4 = S25, paso 5 = última pasada por S23)."],
    ], [2.2, 4.7]))
    A(Spacer(1, 6))
    A(P("Archivos del repositorio", "h2"))
    A(tabla([
        ["Archivo", "Contenido"],
        ["src/det_bareiss.vhd", "Diseño completo en un solo archivo: ROM, RAM, banco, unidades funcionales, ASM, XS3 y display."],
        ["src/nexys_a7.ucf", "Pines y restricción de reloj (100 MHz) para ISE."],
        ["sim/tb_det_bareiss.vhd", "Testbench: prueba las 8 matrices de la ROM leyendo el display y compara con los valores esperados."],
        ["sim/modelo_referencia.py", "Modelo en Python: calcula det y pivotes esperados, cuenta ciclos y genera líneas de ROM."],
        ["sim/resultado_ghdl.txt", "Salida de la simulación completa (GHDL)."],
        ["doc/figuras/*.png", "Diagramas ASM y de bloques en imagen."],
        ["doc/fuentes/*.py", "Scripts que generan las figuras y este PDF."],
    ], [1.9, 5.0]))

    # 2 -----------------------------------------------------------------------
    A(P("2. Repaso del algoritmo de Bareiss", "h1"))
    A(P("Bareiss es una eliminación gaussiana sin fracciones. En el paso k, cada elemento de la submatriz que está "
        "debajo y a la derecha del pivote se actualiza con la fórmula (1) del enunciado:"))
    A(codigo("a(i,j) = ( a(k,k)·a(i,j) − a(i,k)·a(k,j) ) / p        para k < i ≤ n,  k < j ≤ n\n"
             "p = pivote del paso anterior (p = 1 en el primer paso)"))
    A(P("Después del paso k, el pivote actual a(k,k) pasa a ser p. Tras n − 1 pasos, el determinante queda en a(n,n). "
        "La división siempre es exacta: por la identidad de Sylvester, después del paso k cada a(i,j) es el determinante "
        "de una submatriz de (k+1)×(k+1) de A, que es un entero. En la simulación el residuo R siempre termina en 0."))
    A(P("Durante el paso k solo cambian los elementos con i > k y j > k. La fila k y la columna k no se modifican, "
        "por eso el cálculo se hace sobre la misma RAM, sin una segunda copia de la matriz."))
    A(P("Ejemplo 3×3 (página 1 de la ROM)", "h2"))
    A(codigo("A = | 2 1 3 |      k = 1, p = 1:  a22 = (2·4 − 1·1)/1 = 7    a23 = (2·2 − 1·3)/1 = 1\n"
             "    | 1 4 2 |                     a32 = (2·2 − 3·1)/1 = 1    a33 = (2·5 − 3·3)/1 = 1\n"
             "    | 3 2 5 |      k = 2, p = 2:  a33 = (7·1 − 1·1)/2 = 3   →   det = 3\n"
             "Pivotes guardados en el banco: pivote(1) = 2, pivote(2) = 7"))
    A(P("Pivote cero", "h2"))
    A(P("Si a(k,k) = 0, el ASM busca la primera fila i > k con a(i,k) ≠ 0 (estado S5), intercambia las filas k e i en "
        "las columnas k a n (S6 a S9) y cambia el bit [c]signo[/c]. Al final, det = −a(n,n) si hubo un número impar de "
        "intercambios. Si no hay ninguna fila con a(i,k) ≠ 0, la columna es cero debajo del pivote y det = 0. Las "
        "columnas menores que k no se intercambian porque el algoritmo no las vuelve a leer."))

    # 3 -----------------------------------------------------------------------
    A(P("3. Algoritmo XS3 dentro del ASM", "h1"))
    A(P("El documento XS3 describe 5 pasos. En el ASM cada paso es un estado propio, de modo que el diagrama muestra "
        "la conversión completa y no una caja que diga «convertir a BCD»."))
    A(tabla([
        ["Paso del documento XS3", "Estado", "Operación en el hardware"],
        ["1. Inicializar el registro decimal en ceros", "S22", "BCD ← 0 (10 dígitos); cont ← 0"],
        ["2. Colocar el MSB del registro binario en el LSB del registro decimal", "S23", "BCD(0)(0) ← bin(31)"],
        ["3. Revisar cada dígito: si es ≥ 5 (> 0100), sumarle 3 (0011)", "S24",
         "Un dígito por ciclo: d = 0 a 9. Si BCD(d) > 4, BCD(d) ← BCD(d) + 3 usando el sumador/restador."],
        ["4. Correr a la izquierda y descartar el bit que sale; repetir desde el paso 2 (bits − 1) veces", "S25",
         "BCD ← BCD << 1 (entra 0, que el paso 2 reemplaza), bin ← bin << 1, cont ← cont + 1; vuelve a S23."],
        ["5. Realizar únicamente el paso 2", "S23 con cont = 31",
         "En la pasada 32 por S23 se inserta el último bit y la decisión cont = 31 lleva a S26 sin pasar por S24 ni S25."],
    ], [2.6, 0.9, 3.4]))
    A(Spacer(1, 6))
    A(P("Por qué se suma 3: si un dígito vale 5 o más, al correrlo a la izquierda quedaría en 10 o más, que no es un "
        "dígito BCD válido. Sumar 3 antes del corrimiento equivale a sumar 6 después, que es la corrección BCD, y "
        "hace que el exceso pase como acarreo al dígito siguiente."))
    A(P("Tamaños: el registro binario [c]bin[/c] tiene 32 bits, así que el registro decimal necesita 10 dígitos "
        "(2[sup]32[/sup] − 1 = 4 294 967 295) y el lazo da 32 pasadas por el paso 2 (cont = 0 a 31). El signo no entra "
        "al XS3: el estado S21 convierte |valor| y guarda el signo en [c]neg[/c], que luego enciende el segmento g del "
        "display AN7."))
    A(P("Traza del XS3 para 362 (determinante de la página 3)", "h2"))
    A(P("362 = 1 0110 1010[sub]2[/sub] tiene 9 bits significativos. En las pasadas cont = 0 a 22 solo entran ceros y el "
        "registro decimal sigue en 0, por eso la tabla empieza en cont = 23. La columna «bin(31..23)» muestra los 9 bits "
        "de arriba del registro binario; el bit de la izquierda, bin(31), es el que copia el paso 2. El registro decimal "
        "se muestra con sus tres dígitos bajos: centenas, decenas y unidades."))
    filas, bcd_fin = traza_xs3(362)
    A(tabla([["cont", "Estado (paso)", "BCD: C D U", "bin(31..23)", "Comentario"]] + filas,
            [0.45, 0.85, 1.25, 0.95, 3.4]))
    A(Spacer(1, 4))
    A(P(f"Resultado: BCD = {bcd_fin[2]:04b} {bcd_fin[1]:04b} {bcd_fin[0]:04b} = {bcd_fin[2]} {bcd_fin[1]} {bcd_fin[0]}. "
        "La simulación del VHDL muestra « 0000362» en el display para esta matriz."))

    # 4 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("4. Caja negra", "h1"))
    A(figura("caja_negra", "Figura 1. Caja negra del procesador (entidad det_bareiss).", max_ancho=5.5))
    A(tabla([
        ["Puerto", "Dir.", "Bits", "Pin Nexys A7", "Función"],
        ["clk", "in", "1", "E3", "Reloj de 100 MHz"],
        ["rst", "in", "1", "BTNU (M18)", "Reinicio asíncrono, activo en alto"],
        ["inicio", "in", "1", "BTNC (N17)", "Comienza el cálculo"],
        ["sw_mat", "in", "3", "SW15..SW13", "Elige la matriz de prueba (página de la ROM)"],
        ["sw_piv", "in", "3", "SW2..SW0", "0: muestra el determinante; 1 a 4: muestra el pivote k"],
        ["final", "out", "1", "LD0", "'1' cuando el valor ya está en el display (estado S26)"],
        ["desborde", "out", "1", "LD1", "El valor mostrado tiene más de 7 dígitos"],
        ["an", "out", "8", "AN7..AN0", "Ánodos del display (activos en bajo)"],
        ["seg", "out", "7", "CA..CG", "Segmentos; seg(0) = CA … seg(6) = CG (activos en bajo)"],
        ["dp", "out", "1", "DP", "Punto decimal, siempre apagado"],
    ], [0.8, 0.45, 0.45, 1.2, 4.0]))
    A(P("5. Cajas grises: unidad de control y camino de datos", "h1"))
    A(P("La unidad de control (UC) es el ASM: su registro de estado [c]st[/c] y la lógica de estado siguiente. El "
        "camino de datos (CD) contiene memorias, registros y unidades funcionales. La UC le entrega al CD el estado "
        "actual; con él se forman las señales de control (escritura y dirección de la RAM, operandos del "
        "sumador/restador, carga de registros). El CD le devuelve a la UC las señales de estado que aparecen en las "
        "cajas de decisión (sección 8)."))
    A(figura("cajas_grises", "Figura 2. Cajas grises: señales de control (UC → CD) y señales de estado (CD → UC)."))

    # 6 -----------------------------------------------------------------------
    A(P("6. Pseudocódigo con el hardware disponible", "h1"))
    A(P("Cada línea indica el estado del ASM que la ejecuta. Las operaciones del mismo estado ocurren en el mismo "
        "ciclo de reloj."))
    A(codigo(
        "S0 :  final = 0;  esperar inicio = 1;  pag = sw_mat\n"
        "S1 :  n = ROM(00h)\n"
        "S2 :  para j = 1..n, i = 1..n:  M(i,j) = ROM(dira);  dira = dira + 1     (orden por columnas)\n"
        "S3 :  k = 1;  p = 1;  |p| = 1;  signo = 0;  banco = 0\n"
        "mientras k <= n-1:\n"
        "  S4 :  piv = M(k,k)\n"
        "        si piv = 0:\n"
        "  S5 :     buscar i = k+1..n con M(i,k) /= 0\n"
        "           si no existe:  det = 0;  ir a VISUALIZAR\n"
        "  S6-S9:   intercambiar filas k e i (columnas k..n);  signo = not signo;  volver a S4\n"
        "  S10:  banco(k) = piv\n"
        "        para i = k+1..n, j = k+1..n:\n"
        "  S11-S14:  t1 = piv · M(i,j);   t2 = M(i,k) · M(k,j)        (un multiplicador, dos usos)\n"
        "  S15:      t3 = t1 - t2                                     (sumador/restador)\n"
        "  S16-S17:  Q = |t3| / |p|  por restas sucesivas            (sumador/restador)\n"
        "  S18:      M(i,j) = +Q  o  -Q   (signo = signo(t3) xor signo(p))\n"
        "  S19:  p = piv;  |p| = |piv|;  k = k + 1\n"
        "S20:  det = M(n,n);  si signo = 1 entonces det = -det\n"
        "VISUALIZAR:\n"
        "S21:  val = det si sw_piv = 0, si no banco(sw_piv);  bin = |val|;  neg = signo(val)\n"
        "S22:  XS3 paso 1:  BCD = 0;  cont = 0\n"
        "repetir:\n"
        "  S23:  XS3 paso 2:  BCD(0)(0) = bin(31);   si cont = 31 salir   (paso 5)\n"
        "  S24:  XS3 paso 3:  para d = 0..9:  si BCD(d) > 4 entonces BCD(d) = BCD(d) + 3\n"
        "  S25:  XS3 paso 4:  BCD = BCD << 1;  bin = bin << 1;  cont = cont + 1\n"
        "S26:  final = 1;  display = BCD;  si inicio = 1 ir a S1;  si cambia sw_piv ir a S21"))

    # 7 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("7. Diagrama ASM", "h1"))
    A(P("Convenciones", "h2"))
    A(tabla([
        ["Elemento", "Significado"],
        ["Caja de estado (rectángulo azul)", "Operaciones que se hacen en todo el estado (salidas tipo Moore)."],
        ["Caja de decisión (rombo)", "Pregunta sobre una señal de estado. La salida 1 es la condición verdadera."],
        ["Caja de salida condicional (rectángulo redondeado naranja)",
         "Operación que solo ocurre si se toma ese camino (tipo Mealy), como en el ejemplo «ASM Mealy» de clase."],
        ["Bloque ASM (recuadro punteado)", "Caja de estado más sus decisiones y salidas condicionales: dura un ciclo de reloj."],
        ["Conector (círculo verde)", "Une hojas del diagrama: A → S1, B → S4, C → S11, D → S21, E → S20, F → S17, G → S22."],
        ["x ← expresión", "Asignación a un registro; se hace efectiva al final del ciclo (flanco de subida)."],
        ["x = expresión", "Valor combinacional (no se guarda), por ejemplo final = 1 o la selección val."],
        ["M(i,j)", "Palabra de la RAM en la dirección fila i, columna j."],
    ], [2.3, 4.6]))
    A(Spacer(1, 4))
    A(P("Todas las decisiones de un bloque usan los valores que tienen los registros al comenzar el ciclo. Por "
        "ejemplo, en S19 la pregunta k = n − 1 usa el k anterior al incremento. El diagrama cumple las dos reglas "
        "vistas en clase: cada combinación de estado y decisiones lleva a un solo estado siguiente, y todo camino de "
        "decisiones termina en un estado."))
    A(P("Vista general", "h2"))
    A(figura("vista_general", "Figura 3. Diagrama de estados de la unidad de control (27 estados), agrupado por función.",
             max_alto=3.0))

    descripciones = [
        ("S0", "final = 0; dira ← 0", "inicio = 1: pag ← sw_mat, S1. Si no: S0."),
        ("S1", "n ← ROM(00h); dira ← 1; i ← 1; j ← 1", "S2"),
        ("S2", "M(i,j) ← ROM(dira) con extensión de signo a 32 bits; dira ← dira + 1. i es el índice que cambia más "
               "rápido, como en la Figura 1 del taller.", "i ≠ n: i ← i + 1, S2. i = n y j ≠ n: i ← 1, j ← j + 1, S2. "
               "i = n y j = n: S3."),
        ("S3", "k ← 1; p ← 1 (pivote inicial a(0,0) = 1); |p| ← 1; signo ← 0; banco ← 0", "S4"),
        ("S4", "piv ← M(k,k)", "M(k,k) = 0: i ← k + 1, S5. Si no: S10."),
        ("S5", "Lee M(i,k) buscando una fila con elemento distinto de cero en la columna k.",
               "M(i,k) ≠ 0: j ← k, signo ← not signo, S6. M(i,k) = 0 e i = n: det ← 0, S21 (singular). "
               "Si no: i ← i + 1, S5."),
        ("S6", "tmp1 ← M(k,j)", "S7"),
        ("S7", "tmp2 ← M(i,j)", "S8"),
        ("S8", "M(k,j) ← tmp2", "S9"),
        ("S9", "M(i,j) ← tmp1", "j ≠ n: j ← j + 1, S6. j = n: S4 (vuelve a leer el pivote)."),
        ("S10", "banco(k) ← piv; i ← k + 1; j ← k + 1", "S11"),
        ("S11", "mul_a ← piv; mul_b ← M(i,j)", "S12"),
        ("S12", "t1 ← mul_a × mul_b (= a(k,k)·a(i,j)); mul_a ← M(i,k)", "S13"),
        ("S13", "mul_b ← M(k,j)", "S14"),
        ("S14", "t2 ← mul_a × mul_b (= a(i,k)·a(k,j))", "S15"),
        ("S15", "t3 ← t1 − t2", "S16"),
        ("S16", "Q ← 0; sq ← signo(t3) xor signo(p); R ← |t3| (0 − t3 si t3 < 0)", "S17"),
        ("S17", "El restador calcula R − |p| (resta de prueba).", "R − |p| ≥ 0: R ← R − |p|, Q ← Q + 1, S17. "
                "Si no: S18 (R queda en 0 porque la división es exacta)."),
        ("S18", "M(i,j) ← Q, o 0 − Q si sq = 1", "j ≠ n: j ← j + 1, S11. j = n e i ≠ n: i ← i + 1, j ← k + 1, S11. "
                "i = n y j = n: S19."),
        ("S19", "p ← piv; |p| ← |piv|; k ← k + 1", "k = n − 1: S20. Si no: S4."),
        ("S20", "det ← M(n,n), o 0 − M(n,n) si signo = 1", "S21"),
        ("S21", "val = det si sw_piv = 0, banco(sw_piv) si no; neg ← signo(val); bin ← |val|; sel_ant ← sw_piv", "S22"),
        ("S22", "XS3 paso 1: BCD ← 0; cont ← 0", "S23"),
        ("S23", "XS3 paso 2: BCD(0)(0) ← bin(31)", "cont = 31: S26 (paso 5 cumplido). Si no: d ← 0, S24."),
        ("S24", "XS3 paso 3 sobre el dígito d: si BCD(d) > 4, BCD(d) ← BCD(d) + 3 (en el sumador/restador)",
                "d ≠ 9: d ← d + 1, S24. d = 9: S25."),
        ("S25", "XS3 paso 4: BCD ← BCD << 1 (entra 0); bin ← bin << 1; cont ← cont + 1", "S23"),
        ("S26", "final = 1; display ← BCD; signo del display ← neg; dira ← 0",
                "inicio = 1: pag ← sw_mat, S1. sw_piv ≠ sel_ant: S21. Si no: S26."),
    ]

    hojas = [
        ("asm_hoja1", "Hoja 1: espera y carga de la matriz (S0 a S3)", ["S0", "S1", "S2", "S3"],
         "S2 recorre la ROM con un solo contador de direcciones ([c]dira[/c]) y dos contadores de fila y columna. La "
         "dirección de la RAM es fila & columna, así que no hace falta multiplicar para ubicar a(i,j)."),
        ("asm_hoja2", "Hoja 2: pivote, búsqueda de fila e intercambio (S4 a S10)",
         ["S4", "S5", "S6", "S7", "S8", "S9", "S10"],
         "La RAM tiene un solo puerto: cada lectura o escritura ocupa un estado, por eso el intercambio usa cuatro "
         "estados por columna. Después del intercambio se vuelve a S4 para leer el pivote nuevo, que ya no es cero."),
        ("asm_hoja3", "Hoja 3: productos y numerador (S11 a S16)", ["S11", "S12", "S13", "S14", "S15", "S16"],
         "Con un solo multiplicador, los dos productos de la fórmula (1) se hacen en estados distintos. Los operandos "
         "se cargan en los registros mul_a y mul_b un estado antes de usar el producto, para que el camino crítico "
         "sea registro → multiplicador → registro."),
        ("asm_hoja4", "Hoja 4: división por restas sucesivas y avance (S17 a S19)", ["S17", "S18", "S19"],
         "S17 es el bloque de división: en cada ciclo el restador calcula R − |p|; si el resultado no es negativo "
         "(bit 49 en 0) se guarda en R y el cociente Q aumenta en 1. La división se hace con magnitudes y el signo se "
         "aplica al escribir en S18."),
        ("asm_hoja5", "Hoja 5: determinante y valor a mostrar (S20 y S21)", ["S20", "S21"],
         "S21 es la entrada a la conversión. Se llega desde S20 (cálculo normal), desde S5 (matriz singular, det = 0) y "
         "desde S26 cuando cambian los switches del banco de pivotes."),
        ("asm_hoja6", "Hoja 6: algoritmo XS3 paso a paso y fin (S22 a S26)", ["S22", "S23", "S24", "S25", "S26"],
         "S26 se queda esperando con final = 1 y el valor en el display. Si el usuario mueve SW2..SW0, el ASM vuelve a "
         "S21 y repite el XS3 con el pivote elegido (unos 375 ciclos, invisibles para el ojo)."),
    ]
    for i, (fig, titulo, estados, texto) in enumerate(hojas, start=1):
        A(PageBreak())
        A(P(titulo, "h2"))
        A(P(texto))
        A(figura(fig, f"Figura {3 + i}. {titulo}.", max_alto=7.9))
    A(PageBreak())
    A(P("Tabla de estados", "h2"))
    A(P("Resumen de cada bloque ASM: lo que hace la caja de estado y las salidas condicionales, y a qué estado va "
        "según las decisiones. Es la misma información de las figuras 4 a 9, en el orden del código VHDL."))
    A(tabla([["Estado", "Operaciones", "Siguiente estado"]] +
            [[d[0], d[1], d[2]] for d in descripciones], [0.62, 3.35, 2.93]))

    # 8 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("8. Señales del procesador", "h1"))
    A(P("8.1 Señales de estado (CD → UC)", "h2"))
    A(tabla([
        ["Señal de estado", "Cómo se obtiene", "Se pregunta en"],
        ["inicio", "Botón BTNC sincronizado con dos flip-flops", "S0, S26"],
        ["M(k,k) = 0", "Comparador de dout_ram con 0", "S4"],
        ["M(i,k) = 0", "Comparador de dout_ram con 0", "S5"],
        ["i = n", "Comparador de 3 bits", "S2, S5, S18"],
        ["j = n", "Comparador de 3 bits", "S2, S9, S18"],
        ["k = n − 1", "Comparador de 3 bits", "S19"],
        ["signo(t3)", "Bit t3(49)", "S16"],
        ["R − |p| ≥ 0", "Bit 49 de la salida del sumador/restador en 0", "S17"],
        ["sq", "Registro de signo del cociente", "S18"],
        ["signo(piv)", "Bit piv(31)", "S19"],
        ["signo", "Registro con la paridad de intercambios de filas", "S20"],
        ["signo(val)", "Bit val(31)", "S21"],
        ["cont = 31", "Comparador de 5 bits", "S23"],
        ["BCD(d) > 4", "Comparador de 4 bits sobre el dígito elegido por d", "S24"],
        ["d = 9", "Comparador de 4 bits", "S24"],
        ["sw_piv ≠ sel_ant", "Comparador de 3 bits (switches sincronizados)", "S26"],
    ], [1.5, 3.6, 1.8]))
    A(P("8.2 Señales de control por estado (UC → CD)", "h2"))
    A(P("Además de cargar los registros que aparecen en cada caja, el estado controla la RAM, el multiplicador y el "
        "sumador/restador. Los estados que no aparecen no usan estas unidades."))
    A(tabla([
        ["Estado", "Dirección RAM (fila, col)", "Escribe en RAM", "Sumador/restador", "Multiplicador"],
        ["S2", "(i, j)", "ROM con extensión de signo", "—", "—"],
        ["S4", "(k, k)", "—", "—", "—"],
        ["S5", "(i, k)", "—", "—", "—"],
        ["S6", "(k, j)", "—", "—", "—"],
        ["S7", "(i, j)", "—", "—", "—"],
        ["S8", "(k, j)", "tmp2", "—", "—"],
        ["S9", "(i, j)", "tmp1", "—", "—"],
        ["S11", "(i, j)", "—", "—", "carga mul_a, mul_b"],
        ["S12", "(i, k)", "—", "—", "t1 ← producto; carga mul_a"],
        ["S13", "(k, j)", "—", "—", "carga mul_b"],
        ["S14", "—", "—", "—", "t2 ← producto"],
        ["S15", "—", "—", "t1 − t2", "—"],
        ["S16", "—", "—", "0 − t3", "—"],
        ["S17", "—", "—", "R − |p|", "—"],
        ["S18", "(i, j)", "Q, o la salida del restador si sq = 1", "0 − Q", "—"],
        ["S19", "—", "—", "0 − piv", "—"],
        ["S20", "(n, n)", "—", "0 − M(n,n)", "—"],
        ["S21", "—", "—", "0 − val", "—"],
        ["S24", "—", "—", "BCD(d) + 3 (suma)", "—"],
    ], [0.62, 1.4, 1.98, 1.35, 1.55]))
    A(P("En el VHDL estas señales están en la sección «CAMINO DE DATOS» como asignaciones concurrentes que dependen "
        "de [c]st[/c]: [c]fila_ram[/c], [c]col_ram[/c], [c]we_ram[/c], [c]din_ram[/c], [c]sr_a[/c], [c]sr_b[/c] y "
        "[c]sr_op[/c]. Si en el informe implementan la UC con ROM de entrada, registro y ROM de salida, como en el "
        "ejemplo del contador de unos, esta tabla es la base de la ROM de salida (palabra de control)."))

    A(P("8.3 Registros internos y tamaños", "h2"))
    A(tabla([
        ["Registro", "Bits", "Uso"],
        ["st", "27 estados", "Estado del ASM"],
        ["pag, dira", "3, 5", "Página y dirección de la ROM"],
        ["n, i, j, k", "3 c/u", "Tamaño de la matriz y contadores de fila, columna y paso"],
        ["piv, p, |p|", "32 c/u", "Pivote actual, pivote anterior (divisor) y su magnitud"],
        ["tmp1, tmp2", "32 c/u", "Intercambio de filas"],
        ["mul_a, mul_b", "25 c/u", "Registros de entrada del multiplicador"],
        ["t1, t2, t3", "50 c/u", "Productos y numerador de la fórmula (1)"],
        ["R, Q, sq", "50, 32, 1", "Residuo, cociente y signo del cociente"],
        ["signo", "1", "Paridad de intercambios de filas"],
        ["det", "32", "Determinante"],
        ["banco", "4 × 32", "Pivotes 1 a 4"],
        ["bin, BCD", "32, 10 × 4", "Registros binario y decimal del XS3"],
        ["cont, d", "5, 4", "Bits procesados y dígito revisado en el XS3"],
        ["neg, sel_ant", "1, 3", "Signo del valor convertido y selección ya convertida"],
        ["display, signo display", "10 × 4, 1", "Valor que se ve en los 8 displays"],
        ["refresco", "18", "Contador de barrido del display (2,6 ms por barrido completo)"],
    ], [1.6, 1.1, 4.2]))
    A(P("Por qué estos anchos", "h2"))
    A(P("Por la identidad de Sylvester, cada valor guardado en la RAM es el determinante de una submatriz m×m de A. La "
        "desigualdad de Hadamard lo acota: |det| ≤ (32·√m)[sup]m[/sup] cuando |a(i,j)| ≤ 32."))
    h.extend(viñetas([
        "Operandos del multiplicador: en el paso k son submatrices de k×k con k ≤ 4, así que |x| < 2[sup]24[/sup] = "
        "16 777 216. Caben en 25 bits con signo. (La cota no se alcanza porque +32 no existe en 6 bits.)",
        "Determinante 5×5: |det| ≤ 1,88 × 10[sup]9[/sup] < 2[sup]31[/sup]. Por eso la RAM, det, Q y bin son de 32 bits.",
        "Numerador: t3 = p · a(k), con |p| ≤ 170 268 (submatriz 3×3), así que |t3| ≤ 3,2 × 10[sup]14[/sup] < "
        "2[sup]49[/sup]. t1, t2, t3, R y el sumador/restador son de 50 bits.",
        "BCD: 32 bits binarios necesitan 10 dígitos decimales. El display muestra los 7 de abajo; si los dígitos 7 a 9 "
        "no son cero, LD1 (desborde) se enciende.",
    ]))

    # 9 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("9. Camino de datos", "h1"))
    A(P("El camino de datos se organiza alrededor de dos buses: la salida de la RAM ([c]dout_ram[/c]) y la salida del "
        "sumador/restador ([c]sr_s[/c]). Los multiplexores de la figura los controla el estado del ASM (sección 8.2)."))
    A(figura("camino_datos", "Figura 10. Diagrama de bloques simplificado del camino de datos.", max_alto=5.0))
    A(tabla([
        ["Unidad", "Detalle", "Estados"],
        ["Multiplicador", "Con signo, 25 × 25 → 50 bits. [c]mul_p <= signed(mul_a) * signed(mul_b);[/c]", "S12, S14"],
        ["Sumador/restador", "50 bits. [c]sr_s <= sr_a + sr_bx + sr_op;[/c] con sr_bx = not sr_b en resta: un solo "
                             "sumador con acarreo de entrada, como el bloque «+/−» de las notas de clase.", "S15 a S21, S24"],
        ["División por restas sucesivas", "Registros R, Q y |p|, incrementador Q + 1 y el bit de signo de la resta R − |p| "
                                          "como señal de estado. Usa el sumador/restador.", "S16 a S18"],
        ["ROM", "256 × 6 bits, lectura combinacional: [c]a <= ROM(conv_integer(pag & dira));[/c]", "S1, S2"],
        ["RAM", "64 × 32 bits, escritura síncrona y lectura asíncrona; dirección fila & columna", "S2 a S20"],
        ["Banco de pivotes", "4 × 32 bits; escritura en S10, lectura con sw_piv", "S3, S10, S21"],
        ["Contadores", "dira, i, j, k, Q, cont, d y refresco", "varios"],
        ["Comparadores", "= 0, i = n, j = n, k = n − 1, cont = 31, d = 9, BCD(d) > 4, sw_piv ≠ sel_ant", "varios"],
        ["Display", "Registro de 10 dígitos, multiplexor de 8 a 1 y decodificador de 7 segmentos", "S26 y siempre"],
    ], [1.5, 4.3, 1.1]))
    A(P("La síntesis genérica con GHDL ([c]ghdl --synth[/c]) confirma que el diseño tiene un solo multiplicador "
        "(25 × 25) y un solo sumador de 50 bits, y que infiere la ROM (256 × 6) y la RAM (64 × 32) como memorias."))

    # 10 ----------------------------------------------------------------------
    A(P("10. Tiempo de ejecución", "h1"))
    h.extend(viñetas([
        "Carga de la matriz (S0 a S3): n² + 3 ciclos.",
        "Paso k: S4, S10 y S19 (3 ciclos) más, por cada uno de los (n − k)² elementos, 8 ciclos fijos (S11 a S16 y S18) "
        "y |cociente| + 1 ciclos de división en S17.",
        "Intercambio de filas: hasta n − k ciclos de búsqueda, 4 ciclos por columna y una nueva lectura del pivote.",
        "XS3: 375 ciclos (S21 y S22, 31 pasadas de 12 ciclos por S23, S24 × 10 y S25, y la última pasada por S23).",
    ]))
    A(P("La división por restas sucesivas domina el tiempo cuando los valores son grandes, porque tarda tantos ciclos "
        "como vale el cociente. En la página 7 (5×5 con valores cercanos a ±32) el cálculo tarda 19 013 425 ciclos, "
        "0,19 s a 100 MHz. En el peor caso teórico el último cociente se acerca a 1,9 × 10[sup]9[/sup], unos 19 s. Si "
        "el profesor acepta otra forma de división, una división con corrimiento y resta (restauración) haría lo mismo "
        "en 50 ciclos; aquí se dejó la de restas sucesivas porque es la que pide el enunciado."))

    # 11 ----------------------------------------------------------------------
    A(P("11. Implementación en ISE 14.7 y la Nexys A7", "h1"))
    A(P("11.1 Proyecto", "h2"))
    h.extend(viñetas([
        "File → New Project. Top-level source type: HDL.",
        "Family: Artix7 · Device: XC7A100T · Package: CSG324 · Speed: −1 · Synthesis: XST · Simulator: ISim · "
        "Preferred language: VHDL. ISE solo soporta la Nexys A7-100T; la variante 50T exige Vivado.",
        "Add Source: src/det_bareiss.vhd y src/nexys_a7.ucf (Implementation), sim/tb_det_bareiss.vhd (Simulation).",
        "Synthesize → Implement Design → Generate Programming File. Revisen en el reporte de tiempos que se cumpla la "
        "restricción de 10 ns (TS_sys_clk).",
        "Programación: según el manual de la tarjeta, la Nexys A7 no funciona con Digilent Adept. Usen iMPACT de ISE o "
        "el Hardware Manager de Vivado (Lab Edition) con el archivo .bit.",
    ]))
    A(P("11.2 Operación en la tarjeta", "h2"))
    h.extend(viñetas([
        "Pulsar BTNU (rst).",
        "Elegir la matriz con SW15..SW13 (0 a 7, tabla 11.3) y dejar SW2..SW0 en 000.",
        "Pulsar BTNC (inicio). Cuando termina, LD0 (final) se enciende y el display muestra el signo en AN7 y 7 dígitos.",
        "Poner SW2..SW0 en 1 a n − 1 para ver cada pivote; volver a 000 para ver el determinante.",
        "Si LD1 (desborde) está encendido, el valor tiene más de 7 dígitos y el display muestra los 7 de abajo.",
        "Para calcular otra matriz: cambiar SW15..SW13 y pulsar BTNC de nuevo.",
    ]))
    A(P("11.3 Matrices de prueba en la ROM", "h2"))
    filas = [["Pág.", "n", "Matriz A", "det", "Pivotes", "Qué prueba"]]
    queprueba = ["Caso básico 2×2", "Ejemplo del documento", "a11 = 0: intercambio en k = 1",
                 "5×5 general, pivotes negativos", "Pivote negativo; intercambio en k = 2",
                 "Pivote cero en k = 2 (p ≠ 1)", "Columna 1 en cero: singular, det = 0",
                 "Valores extremos; desborde del display"]
    for pag, a in enumerate(MATRICES):
        d, piv, _, _ = bareiss(a)
        filas.append([str(pag), str(len(a)), mat_txt(a), f"{d:,}".replace(",", " "),
                      ", ".join(str(x) for x in piv) or "—", queprueba[pag]])
    A(tabla(filas, [0.45, 0.25, 1.95, 0.9, 1.45, 1.9]))
    A(Spacer(1, 4))
    A(P("Para cambiar o agregar matrices, editen la lista MATRICES en sim/modelo_referencia.py y ejecútenlo: imprime "
        "el det y los pivotes esperados y las líneas de la ROM listas para pegar en det_bareiss.vhd. Cada página "
        "empieza en la dirección 32 × página."))
    A(P("11.4 Pines (src/nexys_a7.ucf)", "h2"))
    A(tabla([
        ["Señal", "Pines"],
        ["clk", "E3 (100 MHz)"],
        ["rst / inicio", "M18 (BTNU) / N17 (BTNC)"],
        ["sw_piv(0..2)", "J15 (SW0), L16 (SW1), M13 (SW2)"],
        ["sw_mat(0..2)", "U12 (SW13), U11 (SW14), V10 (SW15)"],
        ["final / desborde", "H17 (LD0) / K15 (LD1)"],
        ["seg(0..6) = CA..CG, dp", "T10, R10, K16, K13, P15, T11, L18; DP = H15"],
        ["an(0..7)", "J17, J18, T9, J14, P14, T14, K2, U13"],
    ], [1.8, 5.1]))

    # 12 ----------------------------------------------------------------------
    A(P("12. Simulación", "h1"))
    A(P("El testbench pulsa inicio para cada matriz, espera final = 1 y lee el display decodificando las señales an y "
        "seg, igual que lo haría el ojo. Después recorre los pivotes con sw_piv = 1 a n − 1. Con [c]N_REF = 5[/c] el "
        "barrido del display es rápido en simulación. El genérico MAX_MATRIZ del testbench vale 6 por defecto "
        "(matrices 0 a 6, unos 0,2 ms simulados); con 7 incluye la matriz extrema, que en ISim tarda bastante."))
    res = resultados_sim()
    filas = [["Pág.", "Tamaño", "Display esperado", "Display simulado", "LD1", "Ciclos", "Resultado"]]
    for pag, a in enumerate(MATRICES):
        d, _, _, _ = bareiss(a)
        signo = "-" if d < 0 else " "
        esperado = signo + str(abs(d) % 10 ** 7).zfill(7)
        tam, visto, desb, ciclos = res[pag]
        filas.append([str(pag), tam, f"[c]'{esperado}'[/c]".replace(" ", "\u00a0"),
                      f"[c]'{visto}'[/c]".replace(" ", "\u00a0"), desb, f"{ciclos:,}".replace(",", " "),
                      "OK" if visto == esperado else "ERROR"])
    A(tabla(filas, [0.45, 0.65, 1.35, 1.35, 0.45, 1.05, 0.8]))
    A(Spacer(1, 4))
    A(P("Todos los pivotes también coinciden (ver sim/resultado_ghdl.txt). Para comprobar que el testbench detecta "
        "errores, se cambió en una copia del diseño el «+3» del XS3 por «+2»: el testbench reportó 7 errores en las "
        "matrices 0 a 3. Los ciclos se cuentan desde que se suelta inicio hasta final = 1."))

    # 13 ----------------------------------------------------------------------
    A(P("13. Limitaciones y verificación pendiente", "h1"))
    h.extend(viñetas([
        "[b]No se ejecutó ISE.[/b] El diseño se verificó con GHDL 4.1 (simulación con [c]-fsynopsys -fexplicit[/c] y "
        "síntesis genérica), no con XST ni ISim. Hay que sintetizar en ISE 14.7 y revisar el reporte de tiempos a "
        "100 MHz. Si la restricción de 10 ns no se cumpliera, la salida es generar un reloj de 50 MHz con el Clocking "
        "Wizard y poner PERIOD = 20 ns.",
        "[b]Display de 7 dígitos.[/b] Con signo en AN7 caben valores hasta ±9 999 999; para valores mayores se "
        "enciende LD1 y se ven los 7 dígitos de abajo.",
        "[b]Tiempo de la división.[/b] Proporcional al cociente (sección 10).",
        "[b]Modelo de RAM.[/b] Se usó lectura asíncrona. Si el modelo del aula tiene lectura síncrona, cada lectura "
        "(S4, S5, S6, S7, S11, S12, S13, S20) necesita un estado de espera antes de usar el dato.",
        "[b]Valor de n.[/b] El diseño supone 2 ≤ n ≤ 5 en la ROM y no lo valida.",
        "[b]ROM con 8 páginas.[/b] Se agregó la selección de página con SW15..SW13 para mostrar varios tamaños sin "
        "volver a sintetizar. Si el profesor quiere una sola matriz, usen la página 0 con los switches en 0.",
    ]))

    # Anexo -------------------------------------------------------------------
    A(PageBreak())
    A(P("Anexo A. Código VHDL completo (src/det_bareiss.vhd)", "h1"))
    vhdl = (RAIZ / "src" / "det_bareiss.vhd").read_text(encoding="utf-8")
    numeradas = "\n".join(f"{n:4d}  {l}" for n, l in enumerate(vhdl.splitlines(), start=1))
    A(Preformatted(numeradas, E["anexo"]))
    return h


if __name__ == "__main__":
    for nombre, f in diagramas.DIAGRAMAS.items():
        diagramas.render(nombre, f(), FIG)
    for dot in FIG.glob("*.dot"):
        dot.unlink()
    doc = Documento(SALIDA)
    doc.multiBuild(contenido())
    print("PDF generado:", SALIDA)

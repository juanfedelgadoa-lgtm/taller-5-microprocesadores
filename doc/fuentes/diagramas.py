#!/usr/bin/env python3
"""Genera los diagramas (ASM, caja negra/gris, camino de datos) con Graphviz.

Requiere el programa `dot` en el PATH.  Uso:  python3 diagramas.py <carpeta_salida>
"""
import subprocess
import sys
from pathlib import Path

FUENTE = "DejaVu Sans"
C_ESTADO = "#dbe8fb"      # caja de estado
C_COND = "#fde3c4"        # caja de salida condicional
C_DEC = "#ffffff"         # caja de decision
C_BLOQUE = "#d9822b"      # borde punteado del bloque ASM
C_CONECTOR = "#c8f0c8"
SPLINES = "ortho"

CABECERA = f"""digraph G {{
  graph [rankdir=TB, splines={SPLINES}, nodesep=0.35, ranksep=0.32, fontname="{FUENTE}",
         newrank=true, pad=0.2];
  node  [fontname="{FUENTE}", fontsize=11, penwidth=1.2];
  edge  [fontname="{FUENTE}", fontsize=10, arrowsize=0.7, penwidth=1.1];
"""


def esc(t):
    return t.replace('"', '\\"')


class ASM:
    """Pequeno constructor de diagramas ASM en lenguaje DOT."""

    def __init__(self):
        self.lineas = []
        self.bloque_abierto = False

    def bloque(self, nombre):
        self.cerrar()
        self.lineas.append(
            f'  subgraph cluster_{nombre} {{ style="dashed,rounded"; color="{C_BLOQUE}"; penwidth=1.4; '
            f'label="{nombre}"; labeljust=r; fontcolor="{C_BLOQUE}"; fontsize=13;')
        self.bloque_abierto = True

    def cerrar(self):
        if self.bloque_abierto:
            self.lineas.append("  }")
            self.bloque_abierto = False

    def estado(self, id_, texto):
        self.lineas.append(f'    {id_} [shape=box, style=filled, fillcolor="{C_ESTADO}", '
                           f'label="{esc(texto)}", margin="0.15,0.07"];')

    def decision(self, id_, texto):
        self.lineas.append(f'    {id_} [shape=diamond, style=filled, fillcolor="{C_DEC}", '
                           f'label="{esc(texto)}", margin="0.02,0.02"];')

    def cond(self, id_, texto):
        self.lineas.append(f'    {id_} [shape=box, style="rounded,filled", fillcolor="{C_COND}", '
                           f'label="{esc(texto)}", margin="0.15,0.05"];')

    def conector(self, id_, letra):
        self.cerrar()
        self.lineas.append(f'  {id_} [shape=circle, style=filled, fillcolor="{C_CONECTOR}", '
                           f'label="{letra}", width=0.38, fixedsize=true, fontsize=12];')

    def flecha(self, a, b, etiqueta=None, sale=None, entra="n", **extra):
        """Flecha de a hacia b.

        sale/entra son los puertos (n, s, e, w).  Por defecto: sale por abajo
        y entra por arriba; en una decision, la rama 1 sale por la izquierda y
        la rama 0 por la derecha."""
        attrs = []
        # Con splines=ortho Graphviz ignora los puertos; solo se usan si se
        # cambia a splines=polyline.
        if SPLINES != "ortho":
            if sale is None:
                sale = {"1": "w", "0": "e"}.get(etiqueta, "s")
            attrs.append(f"tailport={sale}")
            attrs.append(f"headport={entra}")
        if etiqueta is not None:
            # La etiqueta 1/0 se dibuja pegada a la caja de decision
            attrs.append(f'taillabel="{esc(etiqueta)}", labeldistance=1.6, labelangle=-40, '
                         f'labelfontcolor="#b00000", labelfontsize=11')
        for k, v in extra.items():
            attrs.append(f'{k}={v}')
        sufijo = f" [{', '.join(attrs)}]" if attrs else ""
        self.lineas.append(f"  {a} -> {b}{sufijo};")

    def dot(self):
        self.cerrar()
        return CABECERA + "\n".join(self.lineas) + "\n}\n"


# ---------------------------------------------------------------------------
# Hoja 1: espera, lectura de n, copia ROM -> RAM, inicializacion
# ---------------------------------------------------------------------------
def asm_hoja1():
    g = ASM()
    g.conector("cA", "A")
    g.bloque("S0")
    g.estado("S0", "final = 0\ndira ← 0")
    g.decision("D0", "inicio")
    g.cond("C0", "pag ← sw_mat")
    g.bloque("S1")
    g.estado("S1", "n ← ROM(00h)\ndira ← 1\ni ← 1 ;  j ← 1")
    g.bloque("S2")
    g.estado("S2", "M(i,j) ← ROM(dira)\ndira ← dira + 1")
    g.decision("D2a", "i = n\n(i_eq_n)")
    g.cond("C2a", "i ← i + 1")
    g.cond("C2b", "i ← 1")
    g.decision("D2b", "j = n\n(j_eq_n)")
    g.cond("C2c", "j ← j + 1")
    g.bloque("S3")
    g.estado("S3", "k ← 1\np ← 1 ;  |p| ← 1\nsigno ← 0\nbanco ← 0")
    g.conector("cB", "B")
    g.flecha("S0", "D0")
    g.flecha("D0", "S0", "0", entra="e")
    g.flecha("D0", "C0", "1")
    g.flecha("C0", "S1")
    g.flecha("cA", "S1", sale="s", entra="e")
    g.flecha("S1", "S2")
    g.flecha("S2", "D2a")
    g.flecha("D2a", "C2a", "0")
    g.flecha("C2a", "S2", sale="w", entra="w")
    g.flecha("D2a", "C2b", "1")
    g.flecha("C2b", "D2b")
    g.flecha("D2b", "C2c", "0")
    g.flecha("C2c", "S2", sale="e", entra="e")
    g.flecha("D2b", "S3", "1")
    g.flecha("S3", "cB")
    return g.dot()


# ---------------------------------------------------------------------------
# Hoja 2: pivote, busqueda de fila, intercambio, banco de pivotes
# ---------------------------------------------------------------------------
def asm_hoja2():
    g = ASM()
    g.conector("cB", "B")
    g.bloque("S4")
    g.estado("S4", "piv ← M(k,k)")
    g.decision("D4", "M(k,k) = 0\n(z_dout)")
    g.cond("C4", "i ← k + 1")
    g.bloque("S5")
    g.estado("S5", "RAM: lee M(i,k)")
    g.decision("D5a", "M(i,k) = 0\n(z_dout)")
    g.cond("C5a", "j ← k\nsigno ← not signo")
    g.decision("D5b", "i = n\n(i_eq_n)")
    g.cond("C5b", "det ← 0\n(singular)")
    g.cond("C5c", "i ← i + 1")
    g.bloque("S6")
    g.estado("S6", "tmp1 ← M(k,j)")
    g.bloque("S7")
    g.estado("S7", "tmp2 ← M(i,j)")
    g.bloque("S8")
    g.estado("S8", "M(k,j) ← tmp2")
    g.bloque("S9")
    g.estado("S9", "M(i,j) ← tmp1")
    g.decision("D9", "j = n\n(j_eq_n)")
    g.cond("C9", "j ← j + 1")
    g.bloque("S10")
    g.estado("S10", "banco(k) ← piv\ni ← k + 1 ;  j ← k + 1")
    g.conector("cC", "C")
    g.conector("cD", "D")
    g.flecha("cB", "S4")
    g.flecha("S4", "D4")
    g.flecha("D4", "S10", "0")
    g.flecha("D4", "C4", "1")
    g.flecha("C4", "S5")
    g.flecha("S5", "D5a")
    g.flecha("D5a", "C5a", "0")
    g.flecha("D5a", "D5b", "1")
    g.flecha("D5b", "C5b", "1")
    g.flecha("D5b", "C5c", "0")
    g.flecha("C5c", "S5", sale="e", entra="e")
    g.flecha("C5b", "cD")
    g.flecha("C5a", "S6")
    g.flecha("S6", "S7")
    g.flecha("S7", "S8")
    g.flecha("S8", "S9")
    g.flecha("S9", "D9")
    g.flecha("D9", "C9", "0")
    g.flecha("C9", "S6", sale="e", entra="e")
    g.flecha("D9", "S4", "1", entra="w")
    g.flecha("S10", "cC")
    return g.dot()


# ---------------------------------------------------------------------------
# Hoja 3: productos y numerador t3 = a(k,k)*a(i,j) - a(i,k)*a(k,j)
# ---------------------------------------------------------------------------
def asm_hoja3():
    g = ASM()
    g.conector("cC", "C")
    g.bloque("S11")
    g.estado("S11", "mul_a ← piv\nmul_b ← M(i,j)")
    g.bloque("S12")
    g.estado("S12", "t1 ← mul_a × mul_b\nmul_a ← M(i,k)")
    g.bloque("S13")
    g.estado("S13", "mul_b ← M(k,j)")
    g.bloque("S14")
    g.estado("S14", "t2 ← mul_a × mul_b")
    g.bloque("S15")
    g.estado("S15", "t3 ← t1 − t2")
    g.bloque("S16")
    g.estado("S16", "Q ← 0\nsq ← signo(t3) ⊕ signo(p)")
    g.decision("D16", "t3 < 0\n(t3_neg)")
    g.cond("C16a", "R ← 0 − t3")
    g.cond("C16b", "R ← t3")
    g.conector("cF", "F")
    g.flecha("cC", "S11")
    g.flecha("S11", "S12")
    g.flecha("S12", "S13")
    g.flecha("S13", "S14")
    g.flecha("S14", "S15")
    g.flecha("S15", "S16")
    g.flecha("S16", "D16")
    g.flecha("D16", "C16a", "1")
    g.flecha("D16", "C16b", "0")
    g.flecha("C16a", "cF")
    g.flecha("C16b", "cF")
    return g.dot()


# ---------------------------------------------------------------------------
# Hoja 4: division por restas sucesivas, escritura de a(i,j), avance de k
# ---------------------------------------------------------------------------
def asm_hoja4():
    g = ASM()
    g.conector("cF", "F")
    g.bloque("S17")
    g.estado("S17", "restador: R − |p|")
    g.decision("D17", "R − |p| ≥ 0\n(r_ge)")
    g.cond("C17", "R ← R − |p|\nQ ← Q + 1")
    g.bloque("S18")
    g.estado("S18", "RAM: escribe M(i,j)")
    g.decision("D18a", "sq")
    g.cond("C18a", "M(i,j) ← 0 − Q")
    g.cond("C18b", "M(i,j) ← Q")
    g.decision("D18b", "j = n\n(j_eq_n)")
    g.cond("C18c", "j ← j + 1")
    g.decision("D18c", "i = n\n(i_eq_n)")
    g.cond("C18d", "i ← i + 1\nj ← k + 1")
    g.bloque("S19")
    g.estado("S19", "p ← piv\nk ← k + 1")
    g.decision("D19a", "piv < 0\n(piv_neg)")
    g.cond("C19a", "|p| ← 0 − piv")
    g.cond("C19b", "|p| ← piv")
    g.decision("D19b", "k = n − 1\n(k1_eq_n)")
    g.conector("cC1", "C")
    g.conector("cC2", "C")
    g.conector("cB", "B")
    g.conector("cE", "E")
    g.flecha("cF", "S17")
    g.flecha("S17", "D17")
    g.flecha("D17", "C17", "1")
    g.flecha("C17", "S17", sale="w", entra="w")
    g.flecha("D17", "S18", "0")
    g.flecha("S18", "D18a")
    g.flecha("D18a", "C18a", "1")
    g.flecha("D18a", "C18b", "0")
    g.flecha("C18a", "D18b")
    g.flecha("C18b", "D18b")
    g.flecha("D18b", "C18c", "0")
    g.flecha("C18c", "cC1")
    g.flecha("D18b", "D18c", "1")
    g.flecha("D18c", "C18d", "0")
    g.flecha("C18d", "cC2")
    g.flecha("D18c", "S19", "1")
    g.flecha("S19", "D19a")
    g.flecha("D19a", "C19a", "1")
    g.flecha("D19a", "C19b", "0")
    g.flecha("C19a", "D19b")
    g.flecha("C19b", "D19b")
    g.flecha("D19b", "cE", "1")
    g.flecha("D19b", "cB", "0")
    return g.dot()


# ---------------------------------------------------------------------------
# Hoja 5: determinante y seleccion del valor que se muestra
# ---------------------------------------------------------------------------
def asm_hoja5():
    g = ASM()
    g.conector("cE", "E")
    g.bloque("S20")
    g.estado("S20", "RAM: lee M(n,n)")
    g.decision("D20", "signo")
    g.cond("C20a", "det ← 0 − M(n,n)")
    g.cond("C20b", "det ← M(n,n)")
    g.conector("cD", "D")
    g.bloque("S21")
    g.estado("S21", "val = det si sw_piv = 0\nval = banco(sw_piv) si sw_piv ≠ 0\nneg ← signo(val)\nsel_ant ← sw_piv")
    g.decision("D21", "val < 0\n(val_neg)")
    g.cond("C21a", "bin ← 0 − val")
    g.cond("C21b", "bin ← val")
    g.conector("cG", "G")
    g.flecha("cE", "S20")
    g.flecha("S20", "D20")
    g.flecha("D20", "C20a", "1")
    g.flecha("D20", "C20b", "0")
    g.flecha("C20a", "S21")
    g.flecha("C20b", "S21")
    g.flecha("cD", "S21", sale="s", entra="e")
    g.flecha("S21", "D21")
    g.flecha("D21", "C21a", "1")
    g.flecha("D21", "C21b", "0")
    g.flecha("C21a", "cG")
    g.flecha("C21b", "cG")
    return g.dot()


# ---------------------------------------------------------------------------
# Hoja 6: algoritmo XS3 paso a paso y estado final
# ---------------------------------------------------------------------------
def asm_hoja6():
    g = ASM()
    g.conector("cG", "G")
    g.bloque("S22")
    g.estado("S22", "XS3 PASO 1\nBCD ← 0  (10 dígitos)\ncont ← 0")
    g.bloque("S23")
    g.estado("S23", "XS3 PASO 2\nBCD(0)(0) ← bin(31)\n(MSB binario → LSB decimal)")
    g.decision("D23", "cont = 31\n(cont_31)")
    g.cond("C23", "d ← 0")
    g.bloque("S24")
    g.estado("S24", "XS3 PASO 3\nrevisa el dígito BCD(d)")
    g.decision("D24a", "BCD(d) > 4\n(dig_gt4)")
    g.cond("C24a", "BCD(d) ← BCD(d) + 3")
    g.decision("D24b", "d = 9\n(d_9)")
    g.cond("C24b", "d ← d + 1")
    g.bloque("S25")
    g.estado("S25", "XS3 PASO 4\nBCD ← BCD << 1\nbin ← bin << 1\ncont ← cont + 1")
    g.bloque("S26")
    g.estado("S26", "final = 1\ndisplay ← BCD ;  signo display ← neg\ndira ← 0")
    g.decision("D26a", "inicio")
    g.cond("C26", "pag ← sw_mat")
    g.decision("D26b", "sw_piv ≠ sel_ant\n(sel_dif)")
    g.conector("cA", "A")
    g.conector("cD", "D")
    g.flecha("cG", "S22")
    g.flecha("S22", "S23")
    g.flecha("S23", "D23")
    g.flecha("D23", "C23", "0")
    g.flecha("D23", "S26", "1")
    g.flecha("C23", "S24")
    g.flecha("S24", "D24a")
    g.flecha("D24a", "C24a", "1")
    g.flecha("D24a", "D24b", "0")
    g.flecha("C24a", "D24b")
    g.flecha("D24b", "C24b", "0")
    g.flecha("C24b", "S24", sale="e", entra="e")
    g.flecha("D24b", "S25", "1")
    g.flecha("S25", "S23", sale="w", entra="w")
    g.flecha("S26", "D26a")
    g.flecha("D26a", "C26", "1")
    g.flecha("C26", "cA")
    g.flecha("D26a", "D26b", "0")
    g.flecha("D26b", "cD", "1")
    g.flecha("D26b", "S26", "0", entra="e")
    return g.dot()


# ---------------------------------------------------------------------------
# Vista general: diagrama de estados de la unidad de control
# ---------------------------------------------------------------------------
def vista_general():
    grupos = [
        ("Carga de la matriz", "#eef4ff", ["s0", "s1", "s2", "s3"]),
        ("Pivote e intercambio", "#fff3e6", ["s4", "s5", "s6", "s7", "s8", "s9", "s10"]),
        ("Actualización de a(i,j)", "#eefaf0", ["s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20"]),
        ("XS3 y visualización", "#f6eefc", ["s21", "s22", "s23", "s24", "s25", "s26"]),
    ]
    trans = [
        ("s0", "s0", "inicio=0"), ("s0", "s1", "inicio=1"), ("s1", "s2", ""),
        ("s2", "s2", "copia"), ("s2", "s3", "i=n, j=n"), ("s3", "s4", ""),
        ("s4", "s10", "piv≠0"), ("s4", "s5", "piv=0"),
        ("s5", "s5", "M(i,k)=0, i≠n"), ("s5", "s6", "M(i,k)≠0"), ("s5", "s21", "i=n (det=0)"),
        ("s6", "s7", ""), ("s7", "s8", ""), ("s8", "s9", ""), ("s9", "s6", "j≠n"), ("s9", "s4", "j=n"),
        ("s10", "s11", ""), ("s11", "s12", ""), ("s12", "s13", ""), ("s13", "s14", ""),
        ("s14", "s15", ""), ("s15", "s16", ""), ("s16", "s17", ""),
        ("s17", "s17", "R≥|p|"), ("s17", "s18", "R<|p|"),
        ("s18", "s11", "falta (i,j)"), ("s18", "s19", "i=n, j=n"),
        ("s19", "s4", "k≠n−1"), ("s19", "s20", "k=n−1"), ("s20", "s21", ""),
        ("s21", "s22", ""), ("s22", "s23", ""), ("s23", "s24", "cont≠31"), ("s23", "s26", "cont=31"),
        ("s24", "s24", "d≠9"), ("s24", "s25", "d=9"), ("s25", "s23", ""),
        ("s26", "s1", "inicio=1"), ("s26", "s21", "cambio sw_piv"), ("s26", "s26", "espera"),
    ]
    out = [f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.25, ranksep=0.35, pad=0.2];
  node [shape=circle, fontname="{FUENTE}", fontsize=11, width=0.5, fixedsize=true, style=filled];
  edge [fontname="{FUENTE}", fontsize=8, arrowsize=0.6];"""]
    for i, (nombre, color, estados) in enumerate(grupos):
        pos = "b" if i == 3 else "t"
        out.append(f'  subgraph cluster_{i} {{ label="{nombre}"; labelloc={pos}; style="rounded,filled"; fillcolor="{color}"; color="#999999"; fontsize=11;')
        for e in estados:
            out.append(f'    {e} [label="{e.upper()}", fillcolor="white"];')
        out.append("  }")
    for a, b, t in trans:
        out.append(f'  {a} -> {b} [label="{esc(t)}"];')
    out.append("}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Caja negra y cajas grises
# ---------------------------------------------------------------------------
def caja_negra():
    return f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.15, ranksep=0.6, pad=0.2];
  node [fontname="{FUENTE}", fontsize=11];
  edge [fontname="{FUENTE}", fontsize=10, arrowsize=0.7];
  subgraph entradas {{ rank=same; node [shape=plaintext];
    clk; rst [label="rst (BTNU)"]; inicio [label="inicio (BTNC)"];
    sw_mat [label="sw_mat (SW15..13)"]; sw_piv [label="sw_piv (SW2..0)"]; }}
  P [shape=box, style=filled, fillcolor="#333333", fontcolor=white, fontsize=14,
     label="DETERMINANTE\\nBAREISS + XS3\\n(det_bareiss)", width=2.4, height=2.2];
  subgraph salidas {{ rank=same; node [shape=plaintext];
    final [label="final (LD0)"]; desborde [label="desborde (LD1)"];
    an [label="an (AN7..0)"]; seg [label="seg (CA..CG)"]; dp; }}
  clk -> P; rst -> P; inicio -> P; sw_mat -> P [label="3"]; sw_piv -> P [label="3"];
  P -> final; P -> desborde; P -> an [label="8"]; P -> seg [label="7"]; P -> dp;
}}
"""


def cajas_grises():
    return f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.5, ranksep=1.6, pad=0.2];
  node [fontname="{FUENTE}", fontsize=11];
  edge [fontname="{FUENTE}", fontsize=8.5, arrowsize=0.7];
  in1 [shape=plaintext, label="inicio_s\\nclk, rst"];
  in2 [shape=plaintext, label="sw_mat_s, sw_piv_s\\nclk, rst"];
  UC [shape=box, style=filled, fillcolor="#dbe8fb", label="UNIDAD DE\\nCONTROL\\nunidad_control\\n(FSM, 27 estados)", width=1.9, height=3.2];
  CD [shape=box, style=filled, fillcolor="#fde3c4", label="CAMINO DE\\nDATOS\\ncamino_datos\\n(registros, muxes,\\nROM, RAM,\\nmultiplicador,\\nsumador/restador)", width=2.0, height=3.2];
  o1 [shape=plaintext, label="final"];
  o2 [shape=plaintext, label="disp_bcd (28)\\ndisp_neg\\ndesborde"];
  in1 -> UC; in2 -> CD; UC -> o1; CD -> o2;
  UC -> CD [label="control (54 señales, 66 bits)\\nld_pag clr_dira inc_dira  we_ram sel_fila sel_col sel_din\\nld_n ld_i sel_i ld_j sel_j ld_k sel_k  ld_piv ld_p sel_p ld_pabs sel_pabs\\nclr_signo tog_signo clr_banco ld_banco ld_tmp1 ld_tmp2\\nld_ma sel_ma ld_mb ld_t1 ld_t2 ld_t3  ld_r sel_r clr_q inc_q ld_sq\\nld_det sel_det  sel_sra sel_srb op_sr  ld_selant ld_neg ld_bin sel_bin\\nclr_bcd ins_bcd aj_bcd sh_bcd clr_cont inc_cont clr_d inc_d ld_disp"];
  CD -> UC [label="estado (14 bits)\\nz_dout i_eq_n j_eq_n k1_eq_n\\nt3_neg r_ge sq piv_neg signo val_neg\\ncont_31 dig_gt4 d_9 sel_dif"];
}}
"""


def jerarquia():
    return f"""digraph G {{
  graph [rankdir=TB, fontname="{FUENTE}", nodesep=0.25, ranksep=0.4, pad=0.2];
  node [fontname="{FUENTE}", fontsize=10, shape=box, style="rounded,filled", fillcolor="#ffffff"];
  edge [arrowsize=0.6];
  top [label="det_bareiss\\n(tope, estructural)", fillcolor="#e9e9e9"];
  sinc [label="U_SINC: sincronizador\\n(2 flip-flops por entrada)"];
  proc [label="U_PROC: procesador\\n(estructural)", fillcolor="#e9e9e9"];
  disp [label="U_DISP: display_8dig\\n(refresco + mux + decodificador)"];
  uc [label="U_UC: unidad_control\\n(FSM, 2 procesos)", fillcolor="#dbe8fb"];
  cd [label="U_CD: camino_datos\\n(registros + muxes)", fillcolor="#fde3c4"];
  rom [label="U_ROM: rom_matrices\\n256 × 6"]; ram [label="U_RAM: ram_trabajo\\n64 × 32"];
  mul [label="U_MUL: multiplicador\\n25 × 25 → 50"]; sr [label="U_SR: sumador_restador\\n50 bits"];
  top -> sinc; top -> proc; top -> disp; proc -> uc; proc -> cd;
  cd -> rom; cd -> ram; cd -> mul; cd -> sr;
}}
"""


def camino_datos():
    """Camino de datos organizado alrededor de dos buses:
    dout (salida de la RAM) y sr_s (salida del sumador/restador).
    Entre corchetes van las senales de control de cada bloque."""
    return f"""digraph G {{
  graph [rankdir=TB, fontname="{FUENTE}", nodesep=0.2, ranksep=0.42, pad=0.2, splines=ortho, newrank=true];
  node [fontname="{FUENTE}", fontsize=9.5, shape=box, style=filled, fillcolor="#ffffff", height=0.45];
  edge [fontname="{FUENTE}", fontsize=8, arrowsize=0.6];

  ROM [fillcolor="#e9e9e9", label="ROM 256 × 6\\ndir = pag & dira\\n[ld_pag, clr_dira, inc_dira]"];
  SXT [label="extensión de\\nsigno 6 → 32"];
  MUXDIN [shape=invtrapezium, label="mux din [sel_din]\\nROM, tmp1, tmp2, Q, −Q"];
  RAM [fillcolor="#e9e9e9", label="RAM 64 × 32 [we_ram]\\ndir = fila & col\\n[sel_fila, sel_col]"];
  BUSD [shape=box, height=0.12, width=9, fillcolor="#4a78c2", fontcolor=white, fontsize=9, label="bus dout (32)"];

  PIV [label="piv (32)\\n[ld_piv]"]; TMP [label="tmp1, tmp2 (32)\\n[ld_tmp1, ld_tmp2]"];
  MA [label="mul_a (25)\\n[ld_ma, sel_ma]"]; MB [label="mul_b (25)\\n[ld_mb]"];
  BANCO [fillcolor="#e9e9e9", label="banco b1..b4 (32)\\n[clr_banco, ld_banco]"];
  P [label="p, |p| (32)\\n[ld_p, sel_p, ld_pabs, sel_pabs]"];
  MUL [fillcolor="#fde3c4", label="MULTIPLICADOR\\n25 × 25 → 50"];
  T12 [label="t1, t2 (50)\\n[ld_t1, ld_t2]"];
  T3 [label="t3 (50)\\n[ld_t3]"];
  RQ [label="R (50) [ld_r, sel_r]\\nQ (32) [clr_q, inc_q]\\nsq [ld_sq]"];
  DET [label="det (32)\\n[ld_det, sel_det]"];
  VAL [shape=invtrapezium, label="mux val\\n(sw_piv)"];
  BCDR [label="BCD 40 bits = 10 dígitos\\n[clr_bcd, ins_bcd, aj_bcd, sh_bcd]\\nd [clr_d, inc_d]"];
  MUXA [shape=invtrapezium, label="mux A [sel_sra]\\n0, t1, R, BCD(d)"];
  MUXB [shape=invtrapezium, label="mux B [sel_srb]\\nt2, t3, |p|, Q, piv,\\nM(n,n), val, 3"];
  SR [fillcolor="#fde3c4", label="SUMADOR / RESTADOR 50 bits [op_sr]\\nA + B   ó   A + not(B) + 1"];
  BUSS [shape=box, height=0.12, width=9, fillcolor="#c2554a", fontcolor=white, fontsize=9, label="bus sr_s (50)"];
  BIN [label="bin (32), neg\\n[ld_bin, sel_bin, ld_neg]\\ncont [clr_cont, inc_cont]"];
  DISP [label="disp (40), disp_neg\\n[ld_disp]\\n→ display_8dig"];

  {{ rank=same; ROM; SXT; MUXDIN; RAM; }}
  {{ rank=same; PIV; TMP; MA; MB; DET; }}
  {{ rank=same; MUL; BANCO; P; T3; RQ; }}
  {{ rank=same; MUXA; MUXB; VAL; }}
  {{ rank=same; BIN; BCDR; DISP; }}

  ROM -> SXT -> MUXDIN -> RAM;
  RAM -> BUSD;
  BUSD -> PIV; BUSD -> TMP; BUSD -> MA; BUSD -> MB;
  PIV -> MA; PIV -> BANCO; PIV -> P;
  TMP -> MUXDIN;
  MA -> MUL; MB -> MUL; MUL -> T12;
  T12 -> MUXA; T12 -> MUXB; T3 -> MUXB; RQ -> MUXA; RQ -> MUXB; P -> MUXB; PIV -> MUXB;
  BUSD -> MUXB [xlabel="M(n,n)"];
  DET -> VAL; BANCO -> VAL; VAL -> MUXB;
  BCDR -> MUXA [xlabel="BCD(d)"];
  MUXA -> SR; MUXB -> SR; SR -> BUSS;
  BUSS -> T3; BUSS -> RQ; BUSS -> P; BUSS -> DET; BUSS -> BIN; BUSS -> BCDR; BUSS -> MUXDIN [xlabel="−Q"];
  RQ -> MUXDIN [xlabel="Q"];
  BIN -> BCDR [xlabel="MSB"]; BCDR -> DISP;
}}
"""


def render(nombre, dot_txt, salida, dpi=170):
    salida.mkdir(parents=True, exist_ok=True)
    dot_file = salida / f"{nombre}.dot"
    dot_file.write_text(dot_txt, encoding="utf-8")
    png = salida / f"{nombre}.png"
    subprocess.run(["dot", "-Tpng", f"-Gdpi={dpi}", str(dot_file), "-o", str(png)], check=True)
    return png


DIAGRAMAS = {
    "asm_hoja1": asm_hoja1,
    "asm_hoja2": asm_hoja2,
    "asm_hoja3": asm_hoja3,
    "asm_hoja4": asm_hoja4,
    "asm_hoja5": asm_hoja5,
    "asm_hoja6": asm_hoja6,
    "vista_general": vista_general,
    "caja_negra": caja_negra,
    "cajas_grises": cajas_grises,
    "jerarquia": jerarquia,
    "camino_datos": camino_datos,
}

if __name__ == "__main__":
    destino = Path(sys.argv[1] if len(sys.argv) > 1 else "figuras")
    for nombre, f in DIAGRAMAS.items():
        print(render(nombre, f(), destino))

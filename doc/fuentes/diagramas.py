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
# ASM principal, hoja 1: espera, lectura de n, copia ROM -> RAM, inicializacion
# ---------------------------------------------------------------------------
def asm_hoja1():
    g = ASM()
    g.conector("cA", "A")
    g.bloque("s0")
    g.estado("S0", "final = 0\ndira ← 0")
    g.decision("D0", "inicio")
    g.bloque("s1")
    g.estado("S1", "n ← a   (ROM 00h)\ndira ← 1\ni ← 1 ;  j ← 1")
    g.bloque("s2")
    g.estado("S2", "RAM(i,j) ← a\ndira ← dira + 1")
    g.decision("D2a", "i = n")
    g.cond("C2a", "i ← i + 1")
    g.cond("C2b", "i ← 1")
    g.decision("D2b", "j = n")
    g.cond("C2c", "j ← j + 1")
    g.bloque("s3")
    g.estado("S3", "k ← 1 ;  p ← 1 ;  |p| ← 1\nsigno ← 0 ;  conv_piv ← 0\nbanco ← 0  (clr_banco = 1)")
    g.conector("cB", "B")
    g.flecha("S0", "D0")
    g.flecha("D0", "S0", "0")
    g.flecha("D0", "S1", "1")
    g.flecha("cA", "S1")
    g.flecha("S1", "S2")
    g.flecha("S2", "D2a")
    g.flecha("D2a", "C2a", "0")
    g.flecha("C2a", "S2")
    g.flecha("D2a", "C2b", "1")
    g.flecha("C2b", "D2b")
    g.flecha("D2b", "C2c", "0")
    g.flecha("C2c", "S2")
    g.flecha("D2b", "S3", "1")
    g.flecha("S3", "cB")
    return g.dot()


# ---------------------------------------------------------------------------
# Hoja 2: pivote, busqueda de fila, intercambio, banco(k)
# ---------------------------------------------------------------------------
def asm_hoja2():
    g = ASM()
    g.conector("cB", "B")
    g.bloque("s4")
    g.estado("S4", "piv ← RAM(k,k)")
    g.decision("D4", "RAM(k,k) = 0")
    g.cond("C4", "i ← k + 1")
    g.bloque("s5")
    g.estado("S5", "lee RAM(i,k)")
    g.decision("D5a", "RAM(i,k) = 0")
    g.cond("C5a", "j ← k\nsigno ← not signo")
    g.decision("D5b", "i = n")
    g.cond("C5b", "det_bin ← 0\n(singular)")
    g.cond("C5c", "i ← i + 1")
    g.bloque("s6")
    g.estado("S6", "tmp1 ← RAM(k,j)")
    g.bloque("s7")
    g.estado("S7", "tmp2 ← RAM(i,j)\nRAM(i,j) ← tmp1")
    g.bloque("s8")
    g.estado("S8", "RAM(k,j) ← tmp2")
    g.decision("D8", "j = n")
    g.cond("C8", "j ← j + 1")
    g.bloque("s9")
    g.estado("S9", "banco(k) ← piv\ni ← k + 1 ;  j ← k + 1")
    g.conector("cC", "C")
    g.conector("cD", "D")
    g.flecha("cB", "S4")
    g.flecha("S4", "D4")
    g.flecha("D4", "S9", "0")
    g.flecha("D4", "C4", "1")
    g.flecha("C4", "S5")
    g.flecha("S5", "D5a")
    g.flecha("D5a", "C5a", "0")
    g.flecha("D5a", "D5b", "1")
    g.flecha("D5b", "C5b", "1")
    g.flecha("D5b", "C5c", "0")
    g.flecha("C5c", "S5")
    g.flecha("C5b", "cD")
    g.flecha("C5a", "S6")
    g.flecha("S6", "S7")
    g.flecha("S7", "S8")
    g.flecha("S8", "D8")
    g.flecha("D8", "C8", "0")
    g.flecha("C8", "S6")
    g.flecha("D8", "S4", "1")
    g.flecha("S9", "cC")
    return g.dot()


# ---------------------------------------------------------------------------
# Hoja 3: productos, resta e inicio de la division
# ---------------------------------------------------------------------------
def asm_hoja3():
    g = ASM()
    g.conector("cC", "C")
    g.bloque("s10")
    g.estado("S10", "mul_a ← piv\nmul_b ← RAM(i,j)")
    g.bloque("s11")
    g.estado("S11", "t1 ← producto\nmul_a ← RAM(i,k)")
    g.bloque("s12")
    g.estado("S12", "mul_b ← RAM(k,j)")
    g.bloque("s13")
    g.estado("S13", "t2 ← producto")
    g.bloque("s14")
    g.estado("S14", "t3 ← t1 − t2\n(sumador/restador)")
    g.bloque("s15")
    g.estado("S15", "ini_div = 1\ndividendo = |t3| ;  divisor = |p|\nsq ← signo(t3) ⊕ signo(p)")
    g.conector("cE", "E")
    g.flecha("cC", "S10")
    g.flecha("S10", "S11")
    g.flecha("S11", "S12")
    g.flecha("S12", "S13")
    g.flecha("S13", "S14")
    g.flecha("S14", "S15")
    g.flecha("S15", "cE")
    return g.dot()


# ---------------------------------------------------------------------------
# Hoja 4: espera de la division, escritura de a(i,j), avance, ultimo pivote
# ---------------------------------------------------------------------------
def asm_hoja4():
    g = ASM()
    g.conector("cE", "E")
    g.bloque("s16")
    g.estado("S16", "espera el bloque\nde división")
    g.decision("D16a", "fin_div")
    g.decision("D16b", "sq")
    g.cond("C16a", "RAM(i,j) ← 0 − cociente")
    g.cond("C16b", "RAM(i,j) ← cociente")
    g.decision("D16c", "j = n")
    g.cond("C16c", "j ← j + 1")
    g.decision("D16d", "i = n")
    g.cond("C16d", "i ← i + 1\nj ← k + 1")
    g.bloque("s17")
    g.estado("S17", "p ← piv\nk ← k + 1")
    g.decision("D17a", "piv < 0")
    g.cond("C17a", "|p| ← 0 − piv")
    g.cond("C17b", "|p| ← piv")
    g.decision("D17b", "k + 1 = n")
    g.bloque("s18")
    g.estado("S18", "lee RAM(n,n)")
    g.decision("D18", "signo")
    g.cond("C18a", "det_bin ← 0 − RAM(n,n)\nbanco(n) ← 0 − RAM(n,n)")
    g.cond("C18b", "det_bin ← RAM(n,n)\nbanco(n) ← RAM(n,n)")
    g.conector("cC1", "C")
    g.conector("cC2", "C")
    g.conector("cB", "B")
    g.conector("cD", "D")
    g.flecha("cE", "S16")
    g.flecha("S16", "D16a")
    g.flecha("D16a", "S16", "0")
    g.flecha("D16a", "D16b", "1")
    g.flecha("D16b", "C16a", "1")
    g.flecha("D16b", "C16b", "0")
    g.flecha("C16a", "D16c")
    g.flecha("C16b", "D16c")
    g.flecha("D16c", "C16c", "0")
    g.flecha("C16c", "cC1")
    g.flecha("D16c", "D16d", "1")
    g.flecha("D16d", "C16d", "0")
    g.flecha("C16d", "cC2")
    g.flecha("D16d", "S17", "1")
    g.flecha("S17", "D17a")
    g.flecha("D17a", "C17a", "1")
    g.flecha("D17a", "C17b", "0")
    g.flecha("C17a", "D17b")
    g.flecha("C17b", "D17b")
    g.flecha("D17b", "cB", "0")
    g.flecha("D17b", "S18", "1")
    g.flecha("S18", "D18")
    g.flecha("D18", "C18a", "1")
    g.flecha("D18", "C18b", "0")
    g.flecha("C18a", "cD")
    g.flecha("C18b", "cD")
    return g.dot()


# ---------------------------------------------------------------------------
# Hoja 5: conversion XS3 de det y del pivote, final
# ---------------------------------------------------------------------------
def asm_hoja5():
    g = ASM()
    g.conector("cD", "D")
    g.bloque("s19")
    g.estado("S19", "val = det_bin si conv_piv = 0\nval = banco(dir_p) si conv_piv = 1\n"
                    "ini_xs3 = 1 ;  bin_xs3 = |val|\nneg ← signo(val) ;  dir_ant ← dir_p")
    g.bloque("s20")
    g.estado("S20", "espera el bloque XS3")
    g.decision("D20a", "fin_xs3")
    g.decision("D20b", "conv_piv")
    g.cond("C20a", "det ← bcd_xs3\ndet_neg ← neg\nconv_piv ← 1")
    g.cond("C20b", "pivote ← bcd_xs3\npiv_neg ← neg")
    g.bloque("s21")
    g.estado("S21", "final = 1\ndira ← 0")
    g.decision("D21a", "inicio")
    g.decision("D21b", "dir_p ≠ dir_ant")
    g.conector("cA", "A")
    g.flecha("cD", "S19")
    g.flecha("S19", "S20")
    g.flecha("S20", "D20a")
    g.flecha("D20a", "S20", "0")
    g.flecha("D20a", "D20b", "1")
    g.flecha("D20b", "C20a", "0")
    g.flecha("D20b", "C20b", "1")
    g.flecha("C20a", "S19")
    g.flecha("C20b", "S21")
    g.flecha("S21", "D21a")
    g.flecha("D21a", "cA", "1")
    g.flecha("D21a", "D21b", "0")
    g.flecha("D21b", "S19", "1")
    g.flecha("D21b", "S21", "0")
    return g.dot()


# ---------------------------------------------------------------------------
# ASM del bloque XS3 (un estado por paso del documento XS3)
# ---------------------------------------------------------------------------
def asm_xs3():
    g = ASM()
    g.bloque("x0")
    g.estado("X0", "final = 0\n(espera)")
    g.decision("DX0", "inicio")
    g.cond("CX0", "bin ← bin_in")
    g.bloque("x1")
    g.estado("X1", "PASO 1\ndec ← 0  (10 dígitos)\ncont ← 0")
    g.bloque("x2")
    g.estado("X2", "PASO 2\ndec(0) ← bin(31)\n(MSB binario → LSB decimal)")
    g.decision("DX2", "cont = 31")
    g.cond("CX2", "d ← 0")
    g.bloque("x3")
    g.estado("X3", "PASO 3\nrevisa el dígito d")
    g.decision("DX3a", "dígito(d) > 4")
    g.cond("CX3a", "dígito(d) ← dígito(d) + 3")
    g.decision("DX3b", "d = 9")
    g.cond("CX3b", "d ← d + 1")
    g.bloque("x4")
    g.estado("X4", "PASO 4\ndec ← dec << 1\nbin ← bin << 1\ncont ← cont + 1")
    g.bloque("x5")
    g.estado("X5", "PASO 5 cumplido\nfinal = 1")
    g.flecha("X0", "DX0")
    g.flecha("DX0", "X0", "0")
    g.flecha("DX0", "CX0", "1")
    g.flecha("CX0", "X1")
    g.flecha("X1", "X2")
    g.flecha("X2", "DX2")
    g.flecha("DX2", "CX2", "0")
    g.flecha("DX2", "X5", "1")
    g.flecha("CX2", "X3")
    g.flecha("X3", "DX3a")
    g.flecha("DX3a", "CX3a", "1")
    g.flecha("DX3a", "DX3b", "0")
    g.flecha("CX3a", "DX3b")
    g.flecha("DX3b", "CX3b", "0")
    g.flecha("CX3b", "X3")
    g.flecha("DX3b", "X4", "1")
    g.flecha("X4", "X2")
    g.flecha("X5", "X0")
    return g.dot()


# ---------------------------------------------------------------------------
# ASM del bloque de division por restas sucesivas
# ---------------------------------------------------------------------------
def asm_division():
    g = ASM()
    g.bloque("d0")
    g.estado("D0", "final = 0\n(espera)")
    g.decision("DD0", "inicio")
    g.cond("CD0", "R ← dividendo\nD ← divisor\nQ ← 0")
    g.bloque("d1")
    g.estado("D1", "restador: R − D")
    g.decision("DD1", "R − D ≥ 0")
    g.cond("CD1", "R ← R − D\nQ ← Q + 1")
    g.bloque("d2")
    g.estado("D2", "final = 1\ncociente = Q")
    g.flecha("D0", "DD0")
    g.flecha("DD0", "D0", "0")
    g.flecha("DD0", "CD0", "1")
    g.flecha("CD0", "D1")
    g.flecha("D1", "DD1")
    g.flecha("DD1", "CD1", "1")
    g.flecha("CD1", "D1")
    g.flecha("DD1", "D2", "0")
    g.flecha("D2", "D0")
    return g.dot()


# ---------------------------------------------------------------------------
# Vista general del ASM principal
# ---------------------------------------------------------------------------
def vista_general():
    grupos = [
        ("Carga de la matriz", "#eef4ff", ["s0", "s1", "s2", "s3"]),
        ("Pivote e intercambio", "#fff3e6", ["s4", "s5", "s6", "s7", "s8", "s9"]),
        ("Actualización de a(i,j)", "#eefaf0", ["s10", "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18"]),
        ("Conversión XS3 y final", "#f6eefc", ["s19", "s20", "s21"]),
    ]
    trans = [
        ("s0", "s0", "inicio=0"), ("s0", "s1", "inicio=1"), ("s1", "s2", ""),
        ("s2", "s2", "copia"), ("s2", "s3", "i=n, j=n"), ("s3", "s4", ""),
        ("s4", "s9", "piv≠0"), ("s4", "s5", "piv=0"),
        ("s5", "s5", "RAM(i,k)=0, i≠n"), ("s5", "s6", "RAM(i,k)≠0"), ("s5", "s19", "i=n (det=0)"),
        ("s6", "s7", ""), ("s7", "s8", ""), ("s8", "s6", "j≠n"), ("s8", "s4", "j=n"),
        ("s9", "s10", ""), ("s10", "s11", ""), ("s11", "s12", ""), ("s12", "s13", ""),
        ("s13", "s14", ""), ("s14", "s15", ""), ("s15", "s16", ""),
        ("s16", "s16", "fin_div=0"), ("s16", "s10", "falta (i,j)"), ("s16", "s17", "i=n, j=n"),
        ("s17", "s4", "k+1≠n"), ("s17", "s18", "k+1=n"), ("s18", "s19", ""),
        ("s19", "s20", ""), ("s20", "s20", "fin_xs3=0"),
        ("s20", "s19", "conv_piv=0"), ("s20", "s21", "conv_piv=1"),
        ("s21", "s1", "inicio=1"), ("s21", "s19", "cambio dir_p"), ("s21", "s21", "espera"),
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
# Caja negra del procesador (apuntes del profesor)
# ---------------------------------------------------------------------------
def caja_negra():
    return f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.2, ranksep=0.8, pad=0.2];
  node [fontname="{FUENTE}", fontsize=11];
  edge [fontname="{FUENTE}", fontsize=10, arrowsize=0.7];
  subgraph entradas {{ rank=same; node [shape=plaintext]; clk; rst; inicio; dir_p; }}
  P [shape=box, style=filled, fillcolor="#333333", fontcolor=white, fontsize=14,
     label="PROCESADOR\\n(algoritmo de Bareiss)\\n\\nROM, RAM, división\\ny XS3 internos", width=2.6, height=2.4];
  subgraph salidas {{ rank=same; node [shape=plaintext];
    det [label="det  (BCD) + det_neg"]; pivote [label="pivote  (BCD) + piv_neg"]; final; }}
  clk -> P; rst -> P; inicio -> P; dir_p -> P [label="3"];
  P -> det [label="40"]; P -> pivote [label="40"]; P -> final;
}}
"""


# ---------------------------------------------------------------------------
# Caja gris del procesador: ASM + bloques del camino de datos
# ---------------------------------------------------------------------------
def cajas_grises():
    bloque = 'shape=box, style="filled", fillcolor="#fde3c4", width=2.0'
    return f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.28, ranksep=1.5, pad=0.2];
  node [fontname="{FUENTE}", fontsize=10];
  edge [fontname="{FUENTE}", fontsize=8, arrowsize=0.6];
  subgraph cluster_proc {{ label="procesador"; style="rounded"; color="#555555"; fontsize=12;
    UC [shape=box, style=filled, fillcolor="#dbe8fb", fontsize=12,
        label="UNIDAD DE CONTROL\\nasm_bareiss\\n(ASM s0 a s21)\\n\\nregistros: n, i, j, k,\\npiv, p, |p|, signo,\\ntmp1, tmp2, mul_a, mul_b,\\nt1, t2, t3, sq, det_bin,\\nconv_piv, dir_ant, neg,\\ndet, pivote", width=2.4, height=6.2];
    ROM [{bloque}, label="ROM\\nrom_matriz\\n32 × 6"];
    RAM [{bloque}, label="RAM\\nRAM_memory\\n64 × 32"];
    MUL [{bloque}, label="MULTIPLICADOR\\n25 × 25 → 50"];
    SR  [{bloque}, label="SUMADOR /\\nRESTADOR 50 bits"];
    DIV [{bloque}, label="BLOQUE DE DIVISIÓN\\nrestas sucesivas\\n(ASM d0 a d2)"];
    XS3 [{bloque}, label="BLOQUE XS3\\nbinario → BCD\\n(ASM x0 a x5)"];
    BAN [{bloque}, label="BANCO DE PIVOTES\\n5 × 32"];
  }}
  ent [shape=plaintext, label="clk, rst\\ninicio\\ndir_p"];
  sal [shape=plaintext, label="det, det_neg\\npivote, piv_neg\\nfinal"];
  ent -> UC; UC -> sal;
  ent -> BAN [label="dir_p (lectura)", style=dashed];
  UC -> ROM [label="dira"];          ROM -> UC [label="a"];
  UC -> RAM [label="rd_add, wr_add, we, data"]; RAM -> UC [label="q"];
  UC -> MUL [label="mul_a, mul_b"];  MUL -> UC [label="producto"];
  UC -> SR  [label="sr_a, sr_b, sr_op"]; SR -> UC [label="resultado"];
  UC -> DIV [label="ini_div, dividendo, divisor"]; DIV -> UC [label="cociente, fin_div"];
  UC -> XS3 [label="ini_xs3, bin_xs3"]; XS3 -> UC [label="bcd_xs3, fin_xs3"];
  UC -> BAN [label="clr_banco, we_banco,\\ndir_banco, dato_banco"]; BAN -> UC [label="piv_banco"];
}}
"""


def grises_bloques():
    return f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.4, ranksep=1.1, pad=0.2];
  node [fontname="{FUENTE}", fontsize=10];
  edge [fontname="{FUENTE}", fontsize=8, arrowsize=0.6];
  subgraph cluster_x {{ label="bloque XS3"; style="rounded"; color="#555555";
    xin [shape=plaintext, label="inicio\\nbin_in (32)"];
    xuc [shape=box, style=filled, fillcolor="#dbe8fb", label="UC\\n(x0 a x5)"];
    xcd [shape=box, style=filled, fillcolor="#fde3c4", label="CD\\nregistro binario (32)\\nregistro decimal (40)\\ncontadores cont, d\\nmux de dígitos\\nsumador +3 (4 bits)\\ncomparador > 4\\ndesplazadores"];
    xout [shape=plaintext, label="bcd (40)\\nfinal"];
    xin -> xuc; xin -> xcd; xuc -> xcd [label="estado"]; xcd -> xuc [label="cont = 31\\ndígito > 4\\nd = 9"];
    xcd -> xout; xuc -> xout;
  }}
  subgraph cluster_d {{ label="bloque de división"; style="rounded"; color="#555555";
    din [shape=plaintext, label="inicio\\ndividendo (50)\\ndivisor (32)"];
    duc [shape=box, style=filled, fillcolor="#dbe8fb", label="UC\\n(d0 a d2)"];
    dcd [shape=box, style=filled, fillcolor="#fde3c4", label="CD\\nresiduo R (50)\\ndivisor D (32)\\ncociente Q (32)\\nrestador R − D\\ncontador Q + 1"];
    dout [shape=plaintext, label="cociente (32)\\nfinal"];
    din -> duc; din -> dcd; duc -> dcd [label="estado"]; dcd -> duc [label="R − D ≥ 0"];
    dcd -> dout; duc -> dout;
  }}
}}
"""


# ---------------------------------------------------------------------------
# Tope para la tarjeta
# ---------------------------------------------------------------------------
def tope():
    blq = 'shape=box, style=filled, fillcolor="#ffffff"'
    return f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.3, ranksep=0.7, pad=0.2];
  node [fontname="{FUENTE}", fontsize=10];
  edge [fontname="{FUENTE}", fontsize=8, arrowsize=0.6];
  clk [shape=plaintext, label="clk 100 MHz\\n(E3)"]; btn [shape=plaintext, label="inicio\\n(BTNC)"];
  sw [shape=plaintext, label="dir_p\\n(SW2..SW0)"]; rst [shape=plaintext, label="rst (BTNU):\\nva a todos los bloques"];
  subgraph cluster_t {{ label="det_bareiss (tope)"; style="rounded"; color="#555555";
    FREC [{blq}, label="divisor_frecuencia"];
    ANTI [{blq}, label="antirrebote"];
    SINC [{blq}, label="sincronizador"];
    PROC [shape=box, style=filled, fillcolor="#333333", fontcolor=white, label="procesador"];
    MUX [shape=invtrapezium, style=filled, fillcolor="#ffffff", label="det si dir_p = 0\\npivote si no"];
    DISP [{blq}, label="display_8dig"];
  }}
  leds [shape=plaintext, label="final (LD0)\\ndesborde (LD1)\\nlatido (LD15)"];
  seg7 [shape=plaintext, label="an, seg, dp\\n(8 displays)"];
  clk -> FREC; rst -> FREC [style=invis];
  FREC -> ANTI [label="tick_1ms"]; FREC -> DISP [label="tick_1ms"]; FREC -> leds [label="onda_1s"];
  btn -> ANTI; ANTI -> PROC [label="pulso de inicio"];
  sw -> SINC; SINC -> PROC [label="dir_p"]; SINC -> MUX [label="dir_p"];
  PROC -> MUX [label="det, pivote"]; MUX -> DISP; MUX -> leds [label="desborde"];
  PROC -> leds [label="final"]; DISP -> seg7;
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
    "caja_negra": caja_negra,
    "cajas_grises": cajas_grises,
    "grises_bloques": grises_bloques,
    "tope": tope,
    "vista_general": vista_general,
    "asm_hoja1": asm_hoja1,
    "asm_hoja2": asm_hoja2,
    "asm_hoja3": asm_hoja3,
    "asm_hoja4": asm_hoja4,
    "asm_hoja5": asm_hoja5,
    "asm_xs3": asm_xs3,
    "asm_division": asm_division,
}

if __name__ == "__main__":
    destino = Path(sys.argv[1] if len(sys.argv) > 1 else "figuras")
    for nombre, f in DIAGRAMAS.items():
        print(render(nombre, f(), destino))

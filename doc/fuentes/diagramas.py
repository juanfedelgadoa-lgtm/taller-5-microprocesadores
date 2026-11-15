#!/usr/bin/env python3
"""Genera los diagramas del Taller 5 con Graphviz y verifica los diagramas ASM.

  * ASM de Bareiss (5 hojas) y ASM del XS3 (1 hoja).
  * Arquitectura, cajas negras, cajas grises (UC / CD) y caminos de datos.
  * Verificacion de las reglas ASM del curso:
      1. Para cada estado presente y conjunto de decisiones solo se define un
         estado siguiente.
      2. Un camino de cajas de decision debe llegar a un estado (sin ciclos).
    y comparacion de las transiciones de cada diagrama con el "case" del VHDL.

Requiere el programa `dot` en el PATH.
Uso:  python3 diagramas.py <carpeta_salida>      (dibuja y verifica)
      python3 diagramas.py --verificar           (solo verifica)
"""
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

FUENTE = "DejaVu Sans"
C_ESTADO = "#dbe8fb"      # caja de estado
C_COND = "#fde3c4"        # caja de salida condicional
C_DEC = "#ffffff"         # caja de decision
C_BLOQUE = "#d9822b"      # borde punteado del bloque ASM
C_CONECTOR = "#c8f0c8"
C_UF = "#fde3c4"          # unidades funcionales
C_MEM = "#e4f2e4"         # memorias
C_REG = "#ffffff"         # registros
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
    """Constructor de diagramas ASM en DOT que guarda tambien su estructura
    (nodos y flechas) para poder verificar las reglas."""

    def __init__(self):
        self.lineas = []
        self.bloque_abierto = None
        self.nodos = {}          # id -> (tipo, texto, bloque)
        self.flechas = []        # (origen, destino, etiqueta)
        self.textos_dec = {}     # id -> (texto si 1, texto si 0)

    def bloque(self, nombre):
        self.cerrar()
        self.lineas.append(
            f'  subgraph cluster_{nombre} {{ style="dashed,rounded"; color="{C_BLOQUE}"; penwidth=1.4; '
            f'label="{nombre}"; labeljust=r; fontcolor="{C_BLOQUE}"; fontsize=13;')
        self.bloque_abierto = nombre

    def cerrar(self):
        if self.bloque_abierto:
            self.lineas.append("  }")
            self.bloque_abierto = None

    def estado(self, id_, texto):
        self.nodos[id_] = ("estado", texto, self.bloque_abierto)
        self.lineas.append(f'    {id_} [shape=box, style=filled, fillcolor="{C_ESTADO}", '
                           f'label="{esc(texto)}", margin="0.15,0.07"];')

    def decision(self, id_, texto, si=None, no=None):
        self.nodos[id_] = ("decision", texto, self.bloque_abierto)
        plano = texto.replace("\n", " ")
        self.textos_dec[id_] = (si or plano, no or f"no ({plano})")
        self.lineas.append(f'    {id_} [shape=diamond, style=filled, fillcolor="{C_DEC}", '
                           f'label="{esc(texto)}", margin="0.02,0.02"];')

    def cond(self, id_, texto):
        self.nodos[id_] = ("cond", texto, self.bloque_abierto)
        self.lineas.append(f'    {id_} [shape=box, style="rounded,filled", fillcolor="{C_COND}", '
                           f'label="{esc(texto)}", margin="0.15,0.05"];')

    def conector(self, id_, letra):
        self.cerrar()
        self.nodos[id_] = ("conector", letra, None)
        self.lineas.append(f'  {id_} [shape=circle, style=filled, fillcolor="{C_CONECTOR}", '
                           f'label="{letra}", width=0.38, fixedsize=true, fontsize=12];')

    def flecha(self, a, b, etiqueta=None):
        """Flecha de a hacia b. En una decision la etiqueta es 1 o 0."""
        self.flechas.append((a, b, etiqueta))
        attrs = []
        if etiqueta is not None:
            attrs.append(f'taillabel="{esc(etiqueta)}", labeldistance=1.6, labelangle=-40, '
                         f'labelfontcolor="#b00000", labelfontsize=11')
        sufijo = f" [{', '.join(attrs)}]" if attrs else ""
        self.lineas.append(f"  {a} -> {b}{sufijo};")

    def dot(self):
        self.cerrar()
        return CABECERA + "\n".join(self.lineas) + "\n}\n"


# ===========================================================================
# ASM DE BAREISS (14 estados)
# Conectores: A -> s1, B -> s2, C -> s6, D -> s7, E -> s11, F -> s13
# ===========================================================================
CONECTORES_BAREISS = {"A": "s1", "B": "s2", "C": "s6", "D": "s7", "E": "s11", "F": "s13"}


def asm_hoja1():
    g = ASM()
    g.bloque("s0")
    g.estado("S0", "final = 0")
    g.decision("D0", "inicio", "inicio = 1", "inicio = 0")
    g.cond("C0", "n ← a   (ROM 00h)\ndira ← 1\ni ← 1 ;  j ← 1")
    g.conector("cA", "A")
    g.bloque("s1")
    g.estado("S1", "RAM(i,j) ← a\ndira ← dira + 1")
    g.decision("D1a", "i = n", "i = n", "i ≠ n")
    g.cond("C1a", "i ← i + 1")
    g.decision("D1b", "j = n", "j = n", "j ≠ n")
    g.cond("C1b", "i ← 1 ;  j ← j + 1")
    g.cond("C1c", "k ← 1 ;  j ← 1\np ← 1 ;  signo ← 0")
    g.conector("cB", "B")
    g.flecha("S0", "D0")
    g.flecha("D0", "S0", "0")
    g.flecha("D0", "C0", "1")
    g.flecha("C0", "S1")
    g.flecha("cA", "S1")
    g.flecha("S1", "D1a")
    g.flecha("D1a", "C1a", "0")
    g.flecha("C1a", "S1")
    g.flecha("D1a", "D1b", "1")
    g.flecha("D1b", "C1b", "0")
    g.flecha("C1b", "S1")
    g.flecha("D1b", "C1c", "1")
    g.flecha("C1c", "cB")
    return g


def asm_hoja2():
    g = ASM()
    g.conector("cB", "B")
    g.bloque("s2")
    g.estado("S2", "piv ← a(k,k)   (qb, con j = k)\ni ← k + 1")
    g.decision("D2", "a(k,k) = 0", "a(k,k) = 0", "a(k,k) ≠ 0")
    g.cond("C2", "banco(k) ← a(k,k)")
    g.bloque("s3")
    g.estado("S3", "lee a(i,k)   (qa, con j = k)")
    g.decision("D3a", "a(i,k) = 0", "a(i,k) = 0", "a(i,k) ≠ 0")
    g.cond("C3a", "signo ← not signo")
    g.decision("D3b", "i = n", "i = n", "i ≠ n")
    g.cond("C3b", "det ← 0\n(singular)")
    g.cond("C3c", "i ← i + 1")
    g.bloque("s4")
    g.estado("S4", "RAM(i,j) ← a(k,j)\ntmp ← a(i,j)")
    g.bloque("s5")
    g.estado("S5", "RAM(k,j) ← tmp")
    g.decision("D5", "j = n", "j = n", "j ≠ n")
    g.cond("C5a", "j ← k")
    g.cond("C5b", "j ← j + 1")
    g.conector("cC", "C")
    g.conector("cF", "F")
    g.flecha("cB", "S2")
    g.flecha("S2", "D2")
    g.flecha("D2", "C2", "0")
    g.flecha("C2", "cC")
    g.flecha("D2", "S3", "1")
    g.flecha("S3", "D3a")
    g.flecha("D3a", "C3a", "0")
    g.flecha("C3a", "S4")
    g.flecha("D3a", "D3b", "1")
    g.flecha("D3b", "C3b", "1")
    g.flecha("C3b", "cF")
    g.flecha("D3b", "C3c", "0")
    g.flecha("C3c", "S3")
    g.flecha("S4", "S5")
    g.flecha("S5", "D5")
    g.flecha("D5", "C5a", "1")
    g.flecha("C5a", "S2")
    g.flecha("D5", "C5b", "0")
    g.flecha("C5b", "S4")
    return g


def asm_hoja3():
    g = ASM()
    g.conector("cC", "C")
    g.bloque("s6")
    g.estado("S6", "aik ← a(i,k)   (qa, con j = k)\nj ← k + 1")
    g.conector("cD", "D")
    g.bloque("s7")
    g.estado("S7", "mul_a ← piv\nmul_b ← a(i,j)")
    g.bloque("s8")
    g.estado("S8", "sr_a ← producto   (t1 = piv · a(i,j))\nmul_a ← aik\nmul_b ← a(k,j)")
    g.bloque("s9")
    g.estado("S9", "sr_b ← producto   (t2 = a(i,k) · a(k,j))\nop ← 1   (resta)")
    g.bloque("s10")
    g.estado("S10", "sr_a ← resultado   (residuo = t1 − t2)\nsr_b ← p ;  cociente ← 0\n"
                    "sq ← signo(t1 − t2) ⊕ signo(p)\nop ← not sq   (mismo signo: resta)")
    g.conector("cE", "E")
    g.flecha("cC", "S6")
    g.flecha("S6", "S7")
    g.flecha("cD", "S7")
    g.flecha("S7", "S8")
    g.flecha("S8", "S9")
    g.flecha("S9", "S10")
    g.flecha("S10", "cE")
    return g


def asm_hoja4():
    g = ASM()
    g.conector("cE", "E")
    g.bloque("s11")
    g.estado("S11", "DIVISIÓN\nresultado = residuo − p   (op = 1)\no residuo + p   (op = 0)")
    g.decision("D11", "residuo = 0\n(sr_a = 0)", "residuo = 0", "residuo ≠ 0")
    g.cond("C11a", "sr_a ← resultado\ncociente ← cociente + 1")
    g.cond("C11b", "sr_b ← cociente ;  op ← 1\n(prepara 0 − cociente)")
    g.bloque("s12")
    g.estado("S12", "RAM(i,j) ← cociente si sq = 0\nRAM(i,j) ← 0 − cociente si sq = 1")
    g.decision("D12a", "j = n", "j = n", "j ≠ n")
    g.cond("C12a", "j ← j + 1")
    g.decision("D12b", "i = n", "i = n", "i ≠ n")
    g.cond("C12b", "i ← i + 1 ;  j ← k")
    g.decision("D12c", "k + 1 = n", "k + 1 = n", "k + 1 ≠ n")
    g.cond("C12c", "p ← piv ;  k ← k + 1\nj ← k + 1")
    g.decision("D12d", "sq ⊕ signo", "sq ⊕ signo = 1", "sq ⊕ signo = 0")
    g.cond("C12d", "det ← 0 − cociente")
    g.cond("C12e", "det ← cociente")
    g.conector("cD", "D")
    g.conector("cC", "C")
    g.conector("cB", "B")
    g.conector("cF", "F")
    g.bloque("s13")
    g.estado("S13", "final = 1")
    g.decision("D13", "inicio", "inicio = 1", "inicio = 0")
    g.cond("C13", "dira ← 1\ni ← 1 ;  j ← 1")
    g.conector("cA", "A")
    g.flecha("cE", "S11")
    g.flecha("S11", "D11")
    g.flecha("D11", "C11a", "0")
    g.flecha("C11a", "S11")
    g.flecha("D11", "C11b", "1")
    g.flecha("C11b", "S12")
    g.flecha("S12", "D12a")
    g.flecha("D12a", "C12a", "0")
    g.flecha("C12a", "cD")
    g.flecha("D12a", "D12b", "1")
    g.flecha("D12b", "C12b", "0")
    g.flecha("C12b", "cC")
    g.flecha("D12b", "D12c", "1")
    g.flecha("D12c", "C12c", "0")
    g.flecha("C12c", "cB")
    g.flecha("D12c", "D12d", "1")
    g.flecha("D12d", "C12d", "1")
    g.flecha("D12d", "C12e", "0")
    g.flecha("C12d", "S13")
    g.flecha("C12e", "S13")
    g.flecha("cF", "S13")
    g.flecha("S13", "D13")
    g.flecha("D13", "S13", "0")
    g.flecha("D13", "C13", "1")
    g.flecha("C13", "cA")
    return g


# ===========================================================================
# ASM DEL XS3 (visualizador)
# ===========================================================================
def asm_xs3():
    g = ASM()
    g.bloque("x0")
    g.estado("X0", "espera\n(el display muestra disp)")
    g.decision("Dx0a", "final", "final = 1", "final = 0")
    g.decision("Dx0b", "val < 0\n(val = det o pivote\nsegún dir_p)", "val < 0", "val ≥ 0")
    g.cond("Cx0a", "bin ← 0 − val\nneg ← 1")
    g.cond("Cx0b", "bin ← val\nneg ← 0")
    g.bloque("x1")
    g.estado("X1", "PASO 1\ndec ← 0  (10 dígitos)\ncont ← 0")
    g.bloque("x2")
    g.estado("X2", "PASO 2\ndec(0) ← bin(31)\n(MSB binario → LSB decimal)")
    g.decision("Dx2", "cont = 31\n(PASO 5)", "cont = 31", "cont ≠ 31")
    g.cond("Cx2", "d ← 0")
    g.bloque("x3")
    g.estado("X3", "PASO 3\nrevisa dígito(d)")
    g.decision("Dx3a", "dígito(d) > 4", "dígito(d) > 4", "dígito(d) ≤ 4")
    g.cond("Cx3a", "dígito(d) ← dígito(d) + 3")
    g.decision("Dx3b", "d = 9", "d = 9", "d ≠ 9")
    g.cond("Cx3b", "d ← d + 1")
    g.bloque("x4")
    g.estado("X4", "PASO 4\ndec ← dec << 1\nbin ← bin << 1\ncont ← cont + 1")
    g.bloque("x5")
    g.estado("X5", "disp ← dec\ndisp_neg ← neg")
    g.flecha("X0", "Dx0a")
    g.flecha("Dx0a", "X0", "0")
    g.flecha("Dx0a", "Dx0b", "1")
    g.flecha("Dx0b", "Cx0a", "1")
    g.flecha("Dx0b", "Cx0b", "0")
    g.flecha("Cx0a", "X1")
    g.flecha("Cx0b", "X1")
    g.flecha("X1", "X2")
    g.flecha("X2", "Dx2")
    g.flecha("Dx2", "Cx2", "0")
    g.flecha("Dx2", "X5", "1")
    g.flecha("Cx2", "X3")
    g.flecha("X3", "Dx3a")
    g.flecha("Dx3a", "Cx3a", "1")
    g.flecha("Dx3a", "Dx3b", "0")
    g.flecha("Cx3a", "Dx3b")
    g.flecha("Dx3b", "Cx3b", "0")
    g.flecha("Cx3b", "X3")
    g.flecha("Dx3b", "X4", "1")
    g.flecha("X4", "X2")
    g.flecha("X5", "X0")
    return g


HOJAS_BAREISS = ["asm_hoja1", "asm_hoja2", "asm_hoja3", "asm_hoja4"]
CONSTRUCTORES = {"asm_hoja1": asm_hoja1, "asm_hoja2": asm_hoja2, "asm_hoja3": asm_hoja3,
                 "asm_hoja4": asm_hoja4, "asm_xs3": asm_xs3}


# ===========================================================================
# VERIFICACION DE LAS REGLAS ASM
# ===========================================================================
def caminos(g, conectores):
    """Para cada estado de la hoja g devuelve (transiciones, errores).
    transiciones: {estado: [(condiciones, estado_siguiente), ...]}"""
    errores = []
    salidas = {}
    for a, b, et in g.flechas:
        salidas.setdefault(a, []).append((b, et))

    # Reglas locales: decision = 2 salidas (1 y 0); estado y cond = 1 salida sin etiqueta
    for id_, (tipo, texto, _) in g.nodos.items():
        s = salidas.get(id_, [])
        if tipo == "decision":
            etiquetas = sorted(et for _, et in s)
            if etiquetas != ["0", "1"]:
                errores.append(f"decision {id_} ({texto!r}) tiene salidas {etiquetas}; debe tener 1 y 0")
        elif tipo in ("estado", "cond"):
            if len(s) != 1 or s[0][1] is not None:
                errores.append(f"{tipo} {id_} debe tener una sola salida sin etiqueta; tiene {s}")
        elif tipo == "conector" and len(s) > 1:
            errores.append(f"conector {id_} tiene {len(s)} salidas")

    trans = {}
    for id_, (tipo, _, bloque) in g.nodos.items():
        if tipo != "estado":
            continue
        resultado = []

        def recorrer(nodo, conds, visitados):
            tipo_n, texto_n, bloque_n = g.nodos[nodo]
            if tipo_n == "estado":
                resultado.append((conds, bloque_n))
                return
            if tipo_n == "conector":
                if nodo in salidas:          # conector de entrada en medio de un camino
                    errores.append(f"camino de {bloque} entra al conector de entrada {nodo}")
                    return
                resultado.append((conds, conectores[texto_n]))
                return
            if nodo in visitados:
                errores.append(f"regla 2: ciclo de decisiones sin estado desde {bloque} (nodo {nodo})")
                return
            if tipo_n in ("decision", "cond") and bloque_n != bloque:
                errores.append(f"{nodo} pertenece al bloque {bloque_n} pero se alcanza desde {bloque}")
            for sig, et in salidas.get(nodo, []):
                c = conds
                if tipo_n == "decision":
                    c = conds + [g.textos_dec[nodo][0] if et == "1" else g.textos_dec[nodo][1]]
                recorrer(sig, c, visitados | {nodo})
            if not salidas.get(nodo):
                errores.append(f"regla 2: el camino desde {bloque} termina en {nodo} sin llegar a un estado")

        for sig, _ in salidas.get(id_, []):
            recorrer(sig, [], frozenset())
        trans[bloque] = resultado
    return trans, errores


def transiciones_vhdl(ruta, var):
    """{estado: conjunto de estados siguientes} leido del 'case' del VHDL."""
    texto = Path(ruta).read_text(encoding="utf-8")
    ini = texto.index(f"case {var} is")
    fin = ini + re.search(r"\n {4}end case;", texto[ini:]).start()     # "end case;" del case principal
    partes = re.split(r"\n\s*when ([sx]\d+)\s*=>", texto[ini:fin])
    res = {}
    for estado, bloque in zip(partes[1::2], partes[2::2]):
        res[estado] = set(re.findall(rf"\b{var}\s*<=\s*(\w+)", bloque))
    return res


def verificar():
    """Verifica todas las hojas. Devuelve (tabla_transiciones, errores)."""
    errores = []
    tabla = {}
    entradas = {}
    for nombre in HOJAS_BAREISS:
        g = CONSTRUCTORES[nombre]()
        t, e = caminos(g, CONECTORES_BAREISS)
        errores += [f"{nombre}: {x}" for x in e]
        tabla.update(t)
        for id_, (tipo, letra, _) in g.nodos.items():
            if tipo == "conector":
                destino = [b for a, b, _ in g.flechas if a == id_]
                if destino:
                    entradas[letra] = g.nodos[destino[0]][2]
    for letra, estado in CONECTORES_BAREISS.items():
        if entradas.get(letra) != estado:
            errores.append(f"el conector {letra} debe entrar a {estado}; entra a {entradas.get(letra)}")
    g = asm_xs3()
    t, e = caminos(g, {})
    errores += [f"asm_xs3: {x}" for x in e]
    tabla.update(t)

    # Comparacion con el VHDL
    vhdl = transiciones_vhdl(RAIZ / "src" / "procesador_bareiss.vhd", "st")
    vhdl.update(transiciones_vhdl(RAIZ / "src" / "visualizador.vhd", "xs"))
    for estado in sorted(set(vhdl) | set(tabla), key=lambda s: (s[0], int(s[1:]))):
        dib = {d for _, d in tabla.get(estado, [])}
        if dib != vhdl.get(estado, set()):
            errores.append(f"{estado}: el diagrama va a {sorted(dib)} y el VHDL a {sorted(vhdl.get(estado, set()))}")
    return tabla, errores


# ===========================================================================
# VISTA GENERAL DEL ASM DE BAREISS
# ===========================================================================
GRUPOS_BAREISS = [
    ("Carga de la matriz", "#eef4ff", ["s0", "s1"]),
    ("Pivote e intercambio de filas", "#fff3e6", ["s2", "s3", "s4", "s5"]),
    ("Actualización de a(i,j)", "#eefaf0", ["s6", "s7", "s8", "s9", "s10"]),
    ("División, escritura y final", "#f6eefc", ["s11", "s12", "s13"]),
]
TRANS_GENERAL = [
    ("s0", "s0", "inicio=0"), ("s0", "s1", "inicio=1"),
    ("s1", "s1", "copia"), ("s1", "s2", "i=n, j=n"),
    ("s2", "s3", "a(k,k)=0"), ("s2", "s6", "a(k,k)≠0"),
    ("s3", "s3", "a(i,k)=0, i≠n"), ("s3", "s4", "a(i,k)≠0"), ("s3", "s13", "i=n (det=0)"),
    ("s4", "s5", ""), ("s5", "s4", "j≠n"), ("s5", "s2", "j=n"),
    ("s6", "s7", ""), ("s7", "s8", ""), ("s8", "s9", ""), ("s9", "s10", ""), ("s10", "s11", ""),
    ("s11", "s11", "residuo≠0"), ("s11", "s12", "residuo=0"),
    ("s12", "s7", "j≠n"), ("s12", "s6", "j=n, i≠n"), ("s12", "s2", "k+1≠n"), ("s12", "s13", "k+1=n"),
    ("s13", "s13", "inicio=0"), ("s13", "s1", "inicio=1"),
]


def vista_general():
    out = [f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.25, ranksep=0.35, pad=0.2];
  node [shape=circle, fontname="{FUENTE}", fontsize=11, width=0.5, fixedsize=true, style=filled];
  edge [fontname="{FUENTE}", fontsize=8, arrowsize=0.6];"""]
    for i, (nombre, color, estados) in enumerate(GRUPOS_BAREISS):
        out.append(f'  subgraph cluster_{i} {{ label="{nombre}"; style="rounded,filled"; fillcolor="{color}"; '
                   f'color="#999999"; fontsize=11;')
        for e in estados:
            out.append(f'    {e} [label="{e.upper()}", fillcolor="white"];')
        out.append("  }")
    for a, b, t in TRANS_GENERAL:
        out.append(f'  {a} -> {b} [label="{esc(t)}"];')
    out.append("}")
    return "\n".join(out) + "\n"


# ===========================================================================
# ARQUITECTURA (como el esquema del equipo)
# ===========================================================================
def arquitectura():
    uf = f'shape=box, style=filled, fillcolor="{C_UF}", fontsize=11'
    mem = f'shape=box, style=filled, fillcolor="{C_MEM}"'
    blq = 'shape=box, style=filled, fillcolor="#ffffff"'
    return f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.35, ranksep=0.5, pad=0.2, newrank=true];
  node [fontname="{FUENTE}", fontsize=10];
  edge [fontname="{FUENTE}", fontsize=8, arrowsize=0.6];
  clk [shape=plaintext, label="clk\\n100 MHz"];
  btn [shape=plaintext, label="inicio\\n(BTNC)"];
  FREC [{blq}, label="divisor_frecuencia.vhd"];
  ANTI [{blq}, label="antirrebote.vhd"];
  subgraph cluster_p {{ label="procesador_bareiss.vhd"; labelloc=b; style="dashed,rounded"; color="{C_BLOQUE}";
    penwidth=1.6; fontcolor="{C_BLOQUE}"; fontsize=12;
    ROM [{mem}, label="ROM\\n(matriz)"];
    ASM [shape=box, style=filled, fillcolor="{C_ESTADO}", fontsize=11, label="ASM\\nBareiss", height=0.9];
    RAMA [{mem}, label="RAM A"];
    RAMB [{mem}, label="RAM B"];
    MUL [{uf}, label="×\\nmultiplicador"];
    SR [{uf}, label="+/−\\nsumador/restador"];
    BAN [{mem}, label="banco de\\npivotes"];
  }}
  subgraph cluster_v {{ label="visualizador.vhd"; labelloc=b; style="dashed,rounded"; color="#5b7fbf";
    penwidth=1.6; fontcolor="#5b7fbf"; fontsize=12;
    XS3 [shape=box, style=filled, fillcolor="{C_ESTADO}", fontsize=11, label="ASM XS3\\n(dir_p elige\\ndet o pivote)"];
    DISP [{blq}, label="display\\n8 dígitos"];
  }}
  seg7 [shape=plaintext, label="an, seg, dp\\ndesborde"];
  dp1 [shape=plaintext, label="dir_p"];
  {{ rank=same; clk; btn; }}
  {{ rank=same; FREC; ANTI; }}
  {{ rank=same; RAMA; RAMB; SR; }}
  {{ rank=same; MUL; BAN; }}
  clk -> FREC; btn -> ANTI; FREC -> ANTI [label="tick"];
  ANTI -> ASM [label="inicio"];
  ROM -> ASM;
  ASM -> RAMA [dir=both]; ASM -> RAMB [dir=both]; ASM -> SR [dir=both];
  RAMA -> MUL; RAMB -> MUL;
  MUL -> ASM [label="producto", constraint=false];
  ASM -> BAN; dp1 -> BAN;
  {{ rank=same; dp1; BAN; }}
  BAN -> XS3 [label="pivote"];
  ASM -> XS3 [label="det, final"];
  FREC -> DISP [label="tick 1 ms"];
  XS3 -> DISP -> seg7;
}}
"""


# ===========================================================================
# CAJAS NEGRAS
# ===========================================================================
def _caja_negra(titulo, entradas, salidas, alto):
    ent = "; ".join(f'e{i} [label="{esc(t)}"]' for i, (t, _) in enumerate(entradas))
    sal = "; ".join(f's{i} [label="{esc(t)}"]' for i, (t, _) in enumerate(salidas))
    fl = [f'e{i} -> P [label="{b}"];' if b else f"e{i} -> P;" for i, (_, b) in enumerate(entradas)]
    fl += [f'P -> s{i} [label="{b}"];' if b else f"P -> s{i};" for i, (_, b) in enumerate(salidas)]
    return f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.2, ranksep=0.9, pad=0.2];
  node [fontname="{FUENTE}", fontsize=11];
  edge [fontname="{FUENTE}", fontsize=10, arrowsize=0.7];
  subgraph entradas {{ rank=same; node [shape=plaintext]; {ent}; }}
  P [shape=box, style=filled, fillcolor="#333333", fontcolor=white, fontsize=13,
     label="{esc(titulo)}", width=2.6, height={alto}];
  subgraph salidas {{ rank=same; node [shape=plaintext]; {sal}; }}
  {chr(10).join(fl)}
}}
"""


def caja_negra():
    return _caja_negra("PROCESADOR DE BAREISS\n(procesador_bareiss)\n\nROM, RAM A, RAM B,\nmultiplicador y\nsumador/restador internos",
                       [("clk", ""), ("rst", ""), ("inicio", ""), ("dir_p", "3")],
                       [("det", "32"), ("pivote", "32"), ("final", "")], 2.3)


def caja_negra_vis():
    return _caja_negra("VISUALIZADOR\n(visualizador)\n\nASM XS3 +\ndisplay de 8 dígitos",
                       [("clk", ""), ("rst", ""), ("tick (1 ms)", ""), ("final", ""), ("dir_p", "3"),
                        ("det", "32"), ("pivote", "32")],
                       [("an", "8"), ("seg", "7"), ("dp", ""), ("desborde", "")], 2.6)


# ===========================================================================
# CAJAS GRISES (unidad de control / camino de datos, como en clase)
# ===========================================================================
def _caja_gris(uc, cd, ent_uc, pc, est, sal_uc, ent_cd, sal_cd):
    salida_uc = (f'  su [shape=plaintext, label="{esc(sal_uc)}"];\n  {{ rank=same; su; sc; }}\n  UC -> su;\n'
                 if sal_uc else "")
    return f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.5, ranksep=0.8, pad=0.2];
  node [fontname="{FUENTE}", fontsize=13];
  edge [fontname="{FUENTE}", fontsize=12, arrowsize=0.8];
  eu [shape=plaintext, label="{esc(ent_uc)}"];
  ec [shape=plaintext, label="{esc(ent_cd)}"];
  UC [shape=box, style=filled, fillcolor="{C_ESTADO}", fontsize=13, width=2.4, height=2.0, label="{esc(uc)}"];
  CD [shape=box, style=filled, fillcolor="{C_UF}", fontsize=13, width=2.8, height=2.0, label="{esc(cd)}"];
  sc [shape=plaintext, label="{esc(sal_cd)}"];
  {{ rank=same; eu; ec; }}
  eu -> UC;
  UC -> CD [label="{esc(pc)}"];
  CD -> UC [label="{esc(est)}", constraint=false, color="#b00000", fontcolor="#b00000"];
  ec -> CD;
  CD -> sc;
{salida_uc}}}
"""


def gris_proc():
    return _caja_gris(
        "UNIDAD DE CONTROL\n\nregistro de estado st\n(s0 a s13, 4 bits)\nROM de entrada 2048 × 4\nROM de salida 4096 × 41",
        "CAMINO DE DATOS\n\nROM, RAM A, RAM B,\nmultiplicador, sumador/restador,\n"
        "banco de pivotes (b1 a b4),\nregistros y sus MUX",
        "clk\nrst\ninicio",
        "PC: palabra de control (40 bits)\n18 cargas (ld_x) + 17 bits de MUX\n+ 4 de las RAM + 1 del banco",
        "señales de estado (7)\nz_b, z_a, i_n, j_n,\nk1_n, z_res, sqs",
        "final", "clk, rst\ndir_p (3)", "det (32)\npivote (32)")


def gris_vis():
    return _caja_gris(
        "UNIDAD DE CONTROL\n\nregistro de estado xs\n(x0 a x5, 3 bits)\nROM de entrada 64 × 3\nROM de salida 256 × 12",
        "CAMINO DE DATOS\n\nMUX det/pivote, restador 0 − val,\nregistros bin, dec, cont, d, disp,\n"
        "sumador +3, comparadores,\ndisplay de 8 dígitos",
        "clk\nrst\nfinal",
        "PC: palabra de control (12 bits)\n6 cargas (ld_x)\n+ 6 bits de MUX",
        "señales de estado (4)\nval_neg, cont_31, dig_4, d_9",
        "", "clk, rst, tick\ndir_p, det, pivote", "an (8), seg (7)\ndp, desborde")


# ===========================================================================
# CAMINOS DE DATOS
# ===========================================================================
def camino_datos_proc():
    uf = f'shape=box, style=filled, fillcolor="{C_UF}", fontsize=17'
    mem = f'shape=box, style=filled, fillcolor="{C_MEM}"'
    reg = f'shape=box, style=filled, fillcolor="{C_REG}"'
    mux = 'shape=invtrapezium, style=filled, fillcolor="#f2f2f2"'
    return f"""digraph G {{
  graph [rankdir=TB, splines=spline, fontname="{FUENTE}", nodesep=0.25, ranksep=0.4, pad=0.2];
  node [fontname="{FUENTE}", fontsize=16];
  edge [fontname="{FUENTE}", fontsize=13, arrowsize=0.8];
  CNT [{reg}, label="contadores\\ndira, n, i, j, k"];
  ROM [{mem}, label="ROM\\n32 × 6"];
  DIR [shape=box, label="dir_ij, dir_kj\\n(direcciones)"];
  MD [{mux}, label="data\\na | qb | tmp | ±cociente"];
  RAMA [{mem}, label="RAM A\\nlee a(i,j)"]; RAMB [{mem}, label="RAM B\\nlee a(k,j)"];
  PIV [{reg}, label="piv"]; AIK [{reg}, label="aik"]; TMP [{reg}, label="tmp"]; P [{reg}, label="p"];
  BAN [{mem}, label="banco b1..b4"];
  MA [{mux}, label="mul_a\\npiv | aik"]; MB [{mux}, label="mul_b\\nqa | qb"];
  RMA [{reg}, label="mul_a"]; RMB [{reg}, label="mul_b"];
  MUL [{uf}, label="MULTIPLICADOR\\n25 × 25 → 50"];
  XA [{mux}, label="sr_a\\nproducto | resultado"]; XB [{mux}, label="sr_b\\nproducto | p | cociente"];
  RSA [{reg}, label="sr_a\\n(t1, residuo)"]; RSB [{reg}, label="sr_b\\n(t2, p, cociente)"];
  SR [{uf}, label="SUMADOR/RESTADOR\\n50 bits (op)"];
  COC [{reg}, label="cociente"]; DET [{reg}, label="det"];
  dirp [shape=plaintext, label="dir_p"]; OP [{mux}, label="pivote\\nb1..b4 | det"];
  odet [shape=plaintext, label="det (32)"]; opiv [shape=plaintext, label="pivote (32)"];
  CNT -> ROM [label="dira"]; CNT -> DIR; ROM -> MD [label="a"];
  DIR -> RAMA; DIR -> RAMB; MD -> RAMA; MD -> RAMB;
  RAMA -> AIK [label="qa"]; RAMA -> TMP; RAMA -> MB; RAMB -> PIV [label="qb"]; RAMB -> MB; RAMB -> MD; RAMB -> BAN;
  TMP -> MD; PIV -> MA; AIK -> MA; PIV -> P;
  MA -> RMA; MB -> RMB; RMA -> MUL; RMB -> MUL; MUL -> XA [label="producto"]; MUL -> XB;
  XA -> RSA; XB -> RSB; P -> XB; COC -> XB; RSA -> SR; RSB -> SR;
  SR -> XA [label="resultado"]; SR -> MD; SR -> DET; COC -> DET; COC -> MD;
  BAN -> OP; DET -> OP; dirp -> OP; DET -> odet; OP -> opiv;
}}
"""


def camino_datos_vis():
    uf = f'shape=box, style=filled, fillcolor="{C_UF}"'
    reg = f'shape=box, style=filled, fillcolor="{C_REG}"'
    mux = 'shape=invtrapezium, style=filled, fillcolor="#f2f2f2"'
    return f"""digraph G {{
  graph [rankdir=TB, splines=spline, fontname="{FUENTE}", nodesep=0.25, ranksep=0.5, pad=0.2];
  node [fontname="{FUENTE}", fontsize=13];
  edge [fontname="{FUENTE}", fontsize=11, arrowsize=0.7];
  det [shape=plaintext, label="det (32)"]; piv [shape=plaintext, label="pivote (32)"];
  dirp [shape=plaintext, label="dir_p"]; tick [shape=plaintext, label="tick (1 ms)"];
  MV [{mux}, label="val\\ndet si dir_p = 0\\npivote si no"];
  NEG [{uf}, label="restador\\n0 − val"];
  MABS [{mux}, label="|val|\\n(val(31))"];
  BIN [{reg}, label="bin (32)\\ncorrimiento"];
  DEC [{reg}, label="dec (40)\\n10 dígitos BCD"];
  MDIG [{mux}, label="dígito(d)"];
  CMP [shape=ellipse, label="> 4 ?\\n(a la UC)"];
  S3 [{uf}, label="sumador\\n+3"];
  CNT [{reg}, label="cont (5), d (4)"];
  DISP [{reg}, label="disp (40)\\ndisp_neg"];
  DSEL [{reg}, label="dsel (3)\\ncontador"];
  MCAR [{mux}, label="carácter\\ndígito o signo"];
  SEG [shape=box, label="decodificador\\n7 segmentos"];
  AN [shape=box, label="decodificador\\nde ánodos"];
  DES [shape=ellipse, label="dígitos 7..9 ≠ 0 ?"];
  oseg [shape=plaintext, label="seg, dp"]; oan [shape=plaintext, label="an"];
  odes [shape=plaintext, label="desborde"];
  det -> MV; piv -> MV; dirp -> MV;
  MV -> NEG; MV -> MABS; NEG -> MABS; MABS -> BIN;
  BIN -> DEC [label="bin(31)"];
  DEC -> MDIG; CNT -> MDIG [label="d"]; MDIG -> CMP; MDIG -> S3; S3 -> DEC;
  DEC -> DISP;
  tick -> DSEL; DISP -> MCAR; DSEL -> MCAR; MCAR -> SEG -> oseg; DSEL -> AN -> oan;
  DISP -> DES -> odes;
}}
"""


# ===========================================================================
# TOPE PARA LA TARJETA
# ===========================================================================
def tope():
    blq = 'shape=box, style=filled, fillcolor="#ffffff"'
    return f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.3, ranksep=0.8, pad=0.2];
  node [fontname="{FUENTE}", fontsize=10];
  edge [fontname="{FUENTE}", fontsize=8, arrowsize=0.6];
  clk [shape=plaintext, label="clk 100 MHz\\n(E3)"]; btn [shape=plaintext, label="inicio\\n(BTNC)"];
  sw [shape=plaintext, label="dir_p\\n(SW2..SW0)"];
  subgraph cluster_t {{ label="det_bareiss (tope: solo conexiones; rst va a todos los bloques)"; style="rounded"; color="#555555";
    FREC [{blq}, label="divisor_frecuencia"];
    ANTI [{blq}, label="antirrebote"];
    PROC [shape=box, style=filled, fillcolor="#333333", fontcolor=white, label="procesador_bareiss"];
    VIS [shape=box, style=filled, fillcolor="{C_ESTADO}", label="visualizador\\n(ASM XS3 + display)"];
  }}
  leds [shape=plaintext, label="final (LD0)\\ndesborde (LD1)\\nlatido (LD15)"];
  seg7 [shape=plaintext, label="an, seg, dp\\n(8 displays)"];
  clk -> FREC;
  FREC -> ANTI [label="tick_1ms"]; FREC -> VIS [label="tick_1ms"]; FREC -> leds [label="onda_1s"];
  btn -> ANTI; ANTI -> PROC [label="pulso de inicio"];
  sw -> PROC [label="dir_p"]; sw -> VIS [label="dir_p"];
  PROC -> VIS [label="det, pivote, final"];
  VIS -> seg7; VIS -> leds [label="desborde"]; PROC -> leds [label="final"];
}}
"""


# ===========================================================================
# CAMINO DE DATOS DETALLADO (cada registro con su MUX, su carga y su selector)
# ===========================================================================
ROJO = "#b00000"


def _r(id_, nombre, bits, ld):
    return (f'  {id_} [shape=box, style=filled, fillcolor="#ffffff", penwidth=1.4, '
            f'label=<<b>{nombre}</b> ({bits})<br/><font color="{ROJO}" point-size="11">{ld}</font>>];')


def _m(id_, entradas, sel):
    filas = "<br/>".join(entradas)
    return (f'  {id_} [shape=invtrapezium, style=filled, fillcolor="#f2f2f2", margin="0.25,0.04", '
            f'label=<<font point-size="10">{filas}</font><br/><font color="{ROJO}" point-size="11">{sel}</font>>];')


def _u(id_, texto, color=C_UF):
    return f'  {id_} [shape=box, style="filled,rounded", fillcolor="{color}", label=<{texto}>];'


def _c(id_, texto, senal):
    return (f'  {id_} [shape=ellipse, label=<{texto}<br/><font color="{ROJO}" point-size="11">→ {senal}</font>>];')


def _p(id_, texto):
    return f'  {id_} [shape=plaintext, label=<{texto}>];'


CAB_CD = f"""digraph G {{
  graph [rankdir=TB, splines=spline, fontname="{FUENTE}", nodesep=0.3, ranksep=0.35, pad=0.2, newrank=true];
  node [fontname="{FUENTE}", fontsize=12];
  edge [fontname="{FUENTE}", fontsize=10, arrowsize=0.7];
"""


def _columna(L, ids, mux, reg, unidad=None, salida=None):
    """Una columna del CD: MUX -> registro -> (unidad +1 que vuelve al MUX) -> salida."""
    a = ids
    if mux:
        L.append(_m(a + "M", *mux))
    L.append(_r(a + "R", *reg))
    if mux:
        L.append(f"  {a}M -> {a}R;")
    if unidad:
        L.append(_u(a + "U", unidad, "#ffffff"))
        L.append(f"  {a}R -> {a}U; {a}U -> {a}M [constraint=false];")
    if salida:
        L.append(_p(a + "S", salida))
        L.append(f"  {a}R -> {a}S;")


def cd_indices():
    L = [CAB_CD]
    _columna(L, "dira", (["0: 1", "1: dira+1"], "sel_dira"), ("dira", 5, "ld_dira"), "+1",
             "→ ROM (dirección)")
    L.append(_p("aS", "a(2..0) de la ROM"))
    _columna(L, "n", None, ("n", 3, "ld_n"), None, "→ comparadores")
    L.append("  aS -> nR;")
    _columna(L, "i", (["00: 1", "01: i+1", "10: k+1"], "sel_i"), ("i", 3, "ld_i"), "+1",
             "→ i = n, dir_ij")
    _columna(L, "j", (["00: 1", "01: j+1", "10: k", "11: k+1"], "sel_j"), ("j", 3, "ld_j"), "+1",
             "→ j = n, dir_ij, dir_kj")
    _columna(L, "k", (["0: 1", "1: k+1"], "sel_k"), ("k", 3, "ld_k"), "+1 (k+1)",
             "→ MUX de i y j, dir_kj")
    L += [_c("Cin", "i = n", "i_n"), _c("Cjn", "j = n", "j_n"), _c("Ckn", "k+1 = n", "k1_n"),
          "  iR -> Cin; jR -> Cjn; kU -> Ckn;",
          "  { rank=same; diraM; iM; jM; kM; }",
          "  { rank=same; diraR; iR; jR; kR; nR; }"]
    L.append("}")
    return "\n".join(L)


def cd_direcciones():
    L = [CAB_CD]
    L += [_p("ij", "i, j"), _p("kj", "k, j"),
          _u("DA", "dir_ij<br/>c = 5: \"11\" &amp; f<br/>si no: f &amp; c(1..0)", "#ffffff"),
          _u("DB", "dir_kj<br/>(misma regla)", "#ffffff"),
          _m("Mw", ["0: dir_ij", "1: dir_kj"], "sel_w"),
          _p("oA", "rd_add → RAM A (qa = a(i,j))"), _p("oB", "rd_add → RAM B (qb = a(k,j))"),
          _p("oW", "wr_add → RAM A y RAM B"),
          """  ij -> DA; kj -> DB; DA -> oA; DB -> oB; DA -> Mw; DB -> Mw; Mw -> oW;
  { rank=same; DA; DB; }
}"""]
    return "\n".join(L)


def cd_memorias():
    L = [CAB_CD]
    L += [_p("a", "a (6) de la ROM"), _u("EXT", "extensión de signo<br/>6 → 32", "#ffffff"),
          _p("coc", "cociente, resultado(31..0)"),
          _m("Mpm", ["sq = 0: cociente", "sq = 1: 0 − cociente"], "(sq)"),
          _m("Mdata", ["00: a", "01: qb", "10: tmp", "11: ±cociente"], "sel_data"),
          _u("RA", "<b>RAM A</b><br/>32 × 32<br/>(modelo del profesor)", C_MEM),
          _u("RB", "<b>RAM B</b><br/>32 × 32<br/>(modelo del profesor)", C_MEM),
          _p("we", f'<font color="{ROJO}">we</font>, wr_add'), _p("rda", "dir_ij"), _p("rdb", "dir_kj"),
          _c("Z", "qa = 0", "z_a"), _c("Zb", "qb = 0", "z_b"),
          _r("piv", "piv", 32, "ld_piv"), _r("tmp", "tmp", 32, "ld_tmp"), _r("aik", "aik", 32, "ld_aik"),
          _u("BAN", f'<b>BANCO DE PIVOTES</b><br/>b1 a b4 (32 bits c/u)<br/>'
                    f'<font color="{ROJO}">we_banco</font>; registro elegido por k', C_MEM),
          _m("Mdet", ["00: 0", "01: cociente", "10: resultado"], "sel_det"), _r("det", "det", 32, "ld_det"),
          _m("Mpiv", ["det si dir_p = n", "b1..b4 según dir_p", "0 si no"], "(dir_p)"),
          _p("dirp", "dir_p (switches)"), _p("odet", "<b>det</b> (32)"), _p("opiv", "<b>pivote</b> (32)"),
          _p("qa_o", "qa → mul_b"), _p("qb_o", "qb → mul_b"), _p("coc2", "cociente, resultado")]
    L.append("""  a -> EXT -> Mdata; coc -> Mpm; Mpm -> Mdata; tmp -> Mdata;
  Mdata -> RA [label="data"]; Mdata -> RB [label="data"]; we -> RA; we -> RB; rda -> RA; rdb -> RB;
  RA -> Z [label="qa"]; RA -> tmp; RA -> aik; RA -> qa_o;
  RB -> Zb [label="qb"]; RB -> piv; RB -> Mdata; RB -> BAN; RB -> qb_o;
  coc2 -> Mdet; Mdet -> det; det -> odet; det -> Mpiv; BAN -> Mpiv; dirp -> Mpiv; Mpiv -> opiv;
  { rank=same; a; coc; }
  { rank=same; we; rda; rdb; }
}""")
    return "\n".join(L)


def cd_aritmetica():
    L = [CAB_CD]
    L += [_m("Mma", ["0: piv", "1: aik"], "sel_ma"), _m("Mmb", ["0: qa", "1: qb"], "sel_mb"),
          _r("ma", "mul_a", 25, "ld_ma"), _r("mb", "mul_b", 25, "ld_mb"),
          _u("MUL", "<b>MULTIPLICADOR</b><br/>producto = mul_a × mul_b"),
          _m("Msra", ["0: producto", "1: resultado"], "sel_sra"),
          _m("Msrb", ["00: producto", "01: p", "10: cociente"], "sel_srb"),
          _r("sra", "sr_a", 50, "ld_sra"), _r("srb", "sr_b", 50, "ld_srb"),
          _m("Mop", ["0: 1 (resta)", "1: not (resultado(49) ⊕ p(31))"], "sel_op"), _r("op", "op", 1, "ld_op"),
          _u("SR", f'<b>SUMADOR/RESTADOR</b><br/>resultado = sr_a + sr_b (op = 0)<br/>o sr_a − sr_b (op = 1)'),
          _c("Zr", "sr_a = 0", "z_res"),
          _p("SRS", "resultado (50) → sr_a, det, RAM (data)"),
          "  Mma -> ma; Mmb -> mb; ma -> MUL; mb -> MUL; MUL -> Msra [label=\"producto\"]; MUL -> Msrb;",
          "  Msra -> sra; Msrb -> srb; sra -> SR; srb -> SR; Mop -> op; op -> SR; SR -> SRS; sra -> Zr;",
          "  SR -> Msra [label=\"resultado\", constraint=false];"]
    _columna(L, "coc", (["0: 0", "1: cociente+1"], "sel_coc"), ("cociente", 32, "ld_coc"), "+1",
             "→ sr_b, det, RAM (data)")
    _columna(L, "p", (["0: 1", "1: piv"], "sel_p"), ("p", 32, "ld_p"), None, "→ sr_b; p(31) → sq, op")
    L += [_p("xE", "resultado(49) ⊕ p(31)"), _r("sqR", "sq", 1, "ld_sq"),
          _p("sqS", f'<font color="{ROJO}">sq ⊕ signo → sqs</font>'), "  xE -> sqR; sqR -> sqS;"]
    _columna(L, "sg", (["0: 0", "1: not signo"], "sel_signo"), ("signo", 1, "ld_signo"), "not", "→ sqs")
    L += ["  { rank=same; Mma; Mmb; }",
          "  { rank=same; cocM; pM; xE; sgM; }",
          "  SRS -> cocM [style=invis];", "}"]
    return "\n".join(L)


def cd_vis():
    L = [CAB_CD]
    L += [_p("det", "det (32)"), _p("pivote", "pivote (32)"), _p("dirp", "dir_p"),
          _m("Mval", ["det si dir_p = 0", "pivote si no"], "(dir_p)"),
          _p("vn", f'val(31) <font color="{ROJO}">→ val_neg</font>'),
          _u("NEG", "restador<br/>0 − val"),
          _m("Mbin", ["00: val", "01: 0 − val", "10: bin &lt;&lt; 1"], "sel_bin"), _r("bin", "bin", 32, "ld_bin"),
          _r("neg", "neg", 1, "ld_neg"),
          _m("Mdec", ["00: 0", "01: dec(39..1) &amp; bin(31)", "10: dígito(d) ← dígito(d)+3", "11: dec &lt;&lt; 1"],
             "sel_dec"),
          _r("dec", "dec", 40, "ld_dec"),
          _m("Mdig", ["dígito(d)"], "(d)"), _c("C4", "&gt; 4", "dig_4"), _u("S3", "sumador<br/>+3"),
          _m("Mcont", ["0: 0", "1: cont+1"], "sel_cont"), _r("cont", "cont", 5, "ld_cont"),
          _u("Icont", "+1", "#ffffff"), _c("C31", "cont = 31", "cont_31"),
          _m("Md", ["0: 0", "1: d+1"], "sel_d"), _r("d", "d", 4, "ld_d"), _u("Id", "+1", "#ffffff"),
          _c("C9", "d = 9", "d_9"),
          _r("disp", "disp, disp_neg", 41, "ld_disp"),
          _p("tick", "tick (1 ms)"), _u("DS", "dsel (3)<br/>contador", "#ffffff"),
          _m("Mcar", ["7 dígitos o signo"], "(dsel)"), _u("SEG", "decodificador<br/>7 segmentos", "#ffffff"),
          _u("AN", "decodificador<br/>de ánodos", "#ffffff"), _c("DES", "dígitos 7..9 ≠ 0", "desborde"),
          _p("oseg", "seg, dp"), _p("oan", "an")]
    L.append("""  det -> Mval; pivote -> Mval; dirp -> Mval; Mval -> vn; Mval -> NEG; Mval -> Mbin; NEG -> Mbin;
  Mbin -> bin; bin -> Mbin [label="<<1", constraint=false]; vn -> neg;
  bin -> Mdec [label="bin(31)"]; Mdec -> dec; dec -> Mdig; d -> Mdig; Mdig -> C4; Mdig -> S3; S3 -> Mdec;
  cont -> Icont; Icont -> Mcont; Mcont -> cont; cont -> C31;
  d -> Id; Id -> Md; Md -> d; d -> C9;
  dec -> disp; neg -> disp; tick -> DS; disp -> Mcar; DS -> Mcar; Mcar -> SEG -> oseg; DS -> AN -> oan;
  disp -> DES;
  { rank=same; det; pivote; dirp; }
}""")
    return "\n".join(L)


# ===========================================================================
# UNIDAD DE CONTROL CANONICA (ROM de entrada, registro de estado, ROM de salida)
# ===========================================================================
def _uc(ent_sig, ent_pc, n, rom_e, rom_s, salidas):
    return f"""digraph G {{
  graph [rankdir=LR, fontname="{FUENTE}", nodesep=0.5, ranksep=0.7, pad=0.2];
  node [fontname="{FUENTE}", fontsize=12];
  edge [fontname="{FUENTE}", fontsize=11, arrowsize=0.8];
  e1 [shape=plaintext, label="{esc(ent_sig)}"];
  RE [shape=box, style=filled, fillcolor="{C_MEM}", width=1.8, height=1.6, label="ROM DE ENTRADA\\n(estado siguiente)\\n\\n{rom_e}"];
  REG [shape=box, style=filled, fillcolor="#ffffff", width=1.4, height=1.6, label="REGISTRO\\nDE ESTADO\\n\\n{n} flip-flops D\\n(clk, rst → s0)"];
  RS [shape=box, style=filled, fillcolor="{C_MEM}", width=1.8, height=1.6, label="ROM DE SALIDA\\n(palabra de control)\\n\\n{rom_s}"];
  e2 [shape=plaintext, label="{esc(ent_pc)}"];
  s1 [shape=plaintext, label="{esc(salidas)}"];
  e1 -> RE; RE -> REG [label="D ({n})"]; REG -> RS [label="Q ({n})"];
  REG -> RE [label="Q ({n}) realimentación", constraint=false, color="#555555", fontcolor="#555555"];
  e2 -> RS; RS -> s1;
  {{ rank=same; e2; RS; }}
}}
"""


def uc_proc():
    return _uc("inicio\nz_b, z_a, i_n, j_n,\nk1_n, z_res\n(7 entradas)",
               "inicio, z_b, z_a, i_n, j_n,\nk1_n, z_res, sqs\n(8 condiciones)",
               4, "2^(4+7) × 4\\n= 2048 × 4", "2^(4+8) × 41\\n= 4096 × 41", "PC (40)\nfinal")


def uc_vis():
    return _uc("final\ncont_31, d_9\n(3 entradas)", "final, val_neg,\ncont_31, dig_4, d_9\n(5 condiciones)",
               3, "2^(3+3) × 3\\n= 64 × 3", "2^(3+5) × 12\\n= 256 × 12", "PC (12)")




def render(nombre, dot_txt, salida, dpi=170):
    salida.mkdir(parents=True, exist_ok=True)
    dot_file = salida / f"{nombre}.dot"
    dot_file.write_text(dot_txt, encoding="utf-8")
    png = salida / f"{nombre}.png"
    subprocess.run(["dot", "-Tpng", f"-Gdpi={dpi}", str(dot_file), "-o", str(png)], check=True)
    return png


DIAGRAMAS = {
    "arquitectura": arquitectura,
    "caja_negra": caja_negra,
    "caja_negra_vis": caja_negra_vis,
    "gris_proc": gris_proc,
    "gris_vis": gris_vis,
    "camino_datos_proc": camino_datos_proc,
    "camino_datos_vis": camino_datos_vis,
    "tope": tope,
    "vista_general": vista_general,
    "cd_indices": cd_indices,
    "cd_direcciones": cd_direcciones,
    "cd_memorias": cd_memorias,
    "cd_aritmetica": cd_aritmetica,
    "cd_vis": cd_vis,
    "uc_proc": uc_proc,
    "uc_vis": uc_vis,
}
for _n, _f in CONSTRUCTORES.items():
    DIAGRAMAS[_n] = (lambda f: (lambda: f().dot()))(_f)


def comprobar_vista_general(tabla):
    """La vista general debe tener exactamente las transiciones de las hojas."""
    hojas = {(e, d) for e, lista in tabla.items() if e.startswith("s") for _, d in lista}
    general = {(a, b) for a, b, _ in TRANS_GENERAL}
    if hojas != general:
        return [f"vista general distinta de las hojas: sobran {sorted(general - hojas)}, faltan {sorted(hojas - general)}"]
    return []


if __name__ == "__main__":
    tabla, errores = verificar()
    errores += comprobar_vista_general(tabla)
    for e in errores:
        print("ERROR:", e)
    if errores:
        sys.exit(1)
    print(f"Reglas ASM verificadas en {len(tabla)} estados; transiciones iguales al VHDL.")
    if "--verificar" in sys.argv:
        sys.exit(0)
    destino = Path(sys.argv[1] if len(sys.argv) > 1 else "figuras")
    for nombre, f in DIAGRAMAS.items():
        print(render(nombre, f(), destino))

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
# ASM DE BAREISS
# Conectores: A -> s1, B -> s4, C -> s9, D -> s14, E -> s16, F -> s18
# ===========================================================================
CONECTORES_BAREISS = {"A": "s1", "B": "s4", "C": "s9", "D": "s14", "E": "s16", "F": "s18"}


def asm_hoja1():
    g = ASM()
    g.conector("cA", "A")
    g.bloque("s0")
    g.estado("S0", "final = 0\ndira ← 0")
    g.decision("D0", "inicio", "inicio = 1", "inicio = 0")
    g.bloque("s1")
    g.estado("S1", "n ← a   (ROM 00h)\ndira ← 1\ni ← 1 ;  j ← 1")
    g.bloque("s2")
    g.estado("S2", "RAM(i,j) ← a\ndira ← dira + 1")
    g.decision("D2a", "i = n", "i = n", "i ≠ n")
    g.cond("C2a", "i ← i + 1")
    g.cond("C2b", "i ← 1")
    g.decision("D2b", "j = n", "j = n", "j ≠ n")
    g.cond("C2c", "j ← j + 1")
    g.bloque("s3")
    g.estado("S3", "k ← 1 ;  p ← 1 ;  |p| ← 1\nsigno ← 0 ;  det ← 0\nbanco ← 0  (clr_banco = 1)")
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
    return g


def asm_hoja2():
    g = ASM()
    g.conector("cB", "B")
    g.bloque("s4")
    g.estado("S4", "piv ← RAM_A(k,k)")
    g.decision("D4", "RAM_A(k,k) = 0", "a(k,k) = 0", "a(k,k) ≠ 0")
    g.cond("C4", "i ← k + 1")
    g.bloque("s5")
    g.estado("S5", "lee RAM_A(i,k)")
    g.decision("D5a", "RAM_A(i,k) = 0", "a(i,k) = 0", "a(i,k) ≠ 0")
    g.cond("C5a", "j ← k\nsigno ← not signo")
    g.decision("D5b", "i = n", "i = n", "i ≠ n")
    g.cond("C5b", "det ← 0\n(singular)")
    g.cond("C5c", "i ← i + 1")
    g.bloque("s6")
    g.estado("S6", "RAM(i,j) ← RAM_A(k,j)\ntmp ← RAM_B(i,j)")
    g.bloque("s7")
    g.estado("S7", "RAM(k,j) ← tmp")
    g.decision("D7", "j = n", "j = n", "j ≠ n")
    g.cond("C7", "j ← j + 1")
    g.bloque("s8")
    g.estado("S8", "banco(k) ← piv\ni ← k + 1 ;  j ← k + 1")
    g.conector("cC", "C")
    g.conector("cF", "F")
    g.flecha("cB", "S4")
    g.flecha("S4", "D4")
    g.flecha("D4", "S8", "0")
    g.flecha("D4", "C4", "1")
    g.flecha("C4", "S5")
    g.flecha("S5", "D5a")
    g.flecha("D5a", "C5a", "0")
    g.flecha("D5a", "D5b", "1")
    g.flecha("D5b", "C5b", "1")
    g.flecha("D5b", "C5c", "0")
    g.flecha("C5c", "S5")
    g.flecha("C5b", "cF")
    g.flecha("C5a", "S6")
    g.flecha("S6", "S7")
    g.flecha("S7", "D7")
    g.flecha("D7", "C7", "0")
    g.flecha("C7", "S6")
    g.flecha("D7", "S4", "1")
    g.flecha("S8", "cC")
    return g


def asm_hoja3():
    g = ASM()
    g.conector("cC", "C")
    g.bloque("s9")
    g.estado("S9", "mul_a ← piv\nmul_b ← RAM_A(i,j)")
    g.bloque("s10")
    g.estado("S10", "t1 ← producto\nmul_a ← RAM_A(i,k)\nmul_b ← RAM_B(k,j)")
    g.bloque("s11")
    g.estado("S11", "t2 ← producto")
    g.bloque("s12")
    g.estado("S12", "t3 ← t1 − t2\n(sumador/restador, op = 1)")
    g.bloque("s13")
    g.estado("S13", "DIVISIÓN: inicio\ncociente ← 0\nsq ← t3(49) ⊕ p(31)")
    g.decision("D13", "t3 < 0", "t3 < 0", "t3 ≥ 0")
    g.cond("C13a", "residuo ← 0 − t3\n(sumador/restador)")
    g.cond("C13b", "residuo ← t3")
    g.conector("cD", "D")
    g.flecha("cC", "S9")
    g.flecha("S9", "S10")
    g.flecha("S10", "S11")
    g.flecha("S11", "S12")
    g.flecha("S12", "S13")
    g.flecha("S13", "D13")
    g.flecha("D13", "C13a", "1")
    g.flecha("D13", "C13b", "0")
    g.flecha("C13a", "cD")
    g.flecha("C13b", "cD")
    return g


def asm_hoja4():
    g = ASM()
    g.conector("cD", "D")
    g.bloque("s14")
    g.estado("S14", "DIVISIÓN: resta sucesiva\nsumador/restador: residuo − |p|")
    g.decision("D14", "residuo − |p| ≥ 0", "residuo − |p| ≥ 0", "residuo − |p| < 0")
    g.cond("C14", "residuo ← residuo − |p|\ncociente ← cociente + 1")
    g.bloque("s15")
    g.estado("S15", "escribe a(i,j) en las RAM")
    g.decision("D15a", "sq", "sq = 1", "sq = 0")
    g.cond("C15a", "RAM(i,j) ← 0 − cociente\n(sumador/restador)")
    g.cond("C15b", "RAM(i,j) ← cociente")
    g.decision("D15b", "j = n", "j = n", "j ≠ n")
    g.cond("C15c", "j ← j + 1")
    g.decision("D15c", "i = n", "i = n", "i ≠ n")
    g.cond("C15d", "i ← i + 1\nj ← k + 1")
    g.conector("cC1", "C")
    g.conector("cC2", "C")
    g.conector("cE", "E")
    g.flecha("cD", "S14")
    g.flecha("S14", "D14")
    g.flecha("D14", "C14", "1")
    g.flecha("C14", "S14")
    g.flecha("D14", "S15", "0")
    g.flecha("S15", "D15a")
    g.flecha("D15a", "C15a", "1")
    g.flecha("D15a", "C15b", "0")
    g.flecha("C15a", "D15b")
    g.flecha("C15b", "D15b")
    g.flecha("D15b", "C15c", "0")
    g.flecha("C15c", "cC1")
    g.flecha("D15b", "D15c", "1")
    g.flecha("D15c", "C15d", "0")
    g.flecha("C15d", "cC2")
    g.flecha("D15c", "cE", "1")
    return g


def asm_hoja5():
    g = ASM()
    g.conector("cE", "E")
    g.bloque("s16")
    g.estado("S16", "p ← piv\nk ← k + 1")
    g.decision("D16a", "piv < 0", "piv < 0", "piv ≥ 0")
    g.cond("C16a", "|p| ← 0 − piv\n(sumador/restador)")
    g.cond("C16b", "|p| ← piv")
    g.decision("D16b", "k + 1 = n", "k + 1 = n", "k + 1 ≠ n")
    g.bloque("s17")
    g.estado("S17", "lee RAM_A(n,n)")
    g.decision("D17", "signo", "signo = 1", "signo = 0")
    g.cond("C17a", "det ← 0 − RAM_A(n,n)\nbanco(n) ← 0 − RAM_A(n,n)")
    g.cond("C17b", "det ← RAM_A(n,n)\nbanco(n) ← RAM_A(n,n)")
    g.conector("cF", "F")
    g.bloque("s18")
    g.estado("S18", "final = 1\ndira ← 0")
    g.decision("D18", "inicio", "inicio = 1", "inicio = 0")
    g.conector("cB", "B")
    g.conector("cA", "A")
    g.flecha("cE", "S16")
    g.flecha("S16", "D16a")
    g.flecha("D16a", "C16a", "1")
    g.flecha("D16a", "C16b", "0")
    g.flecha("C16a", "D16b")
    g.flecha("C16b", "D16b")
    g.flecha("D16b", "cB", "0")
    g.flecha("D16b", "S17", "1")
    g.flecha("S17", "D17")
    g.flecha("D17", "C17a", "1")
    g.flecha("D17", "C17b", "0")
    g.flecha("C17a", "S18")
    g.flecha("C17b", "S18")
    g.flecha("cF", "S18")
    g.flecha("S18", "D18")
    g.flecha("D18", "cA", "1")
    g.flecha("D18", "S18", "0")
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


HOJAS_BAREISS = ["asm_hoja1", "asm_hoja2", "asm_hoja3", "asm_hoja4", "asm_hoja5"]
CONSTRUCTORES = {"asm_hoja1": asm_hoja1, "asm_hoja2": asm_hoja2, "asm_hoja3": asm_hoja3,
                 "asm_hoja4": asm_hoja4, "asm_hoja5": asm_hoja5, "asm_xs3": asm_xs3}


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
    fin = ini + re.search(r"\n {8}when others", texto[ini:]).start()   # "when others" del case principal
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
    ("Carga de la matriz", "#eef4ff", ["s0", "s1", "s2", "s3"]),
    ("Pivote e intercambio de filas", "#fff3e6", ["s4", "s5", "s6", "s7", "s8"]),
    ("Actualización de a(i,j) y división", "#eefaf0", ["s9", "s10", "s11", "s12", "s13", "s14", "s15"]),
    ("Siguiente paso, determinante y final", "#f6eefc", ["s16", "s17", "s18"]),
]
TRANS_GENERAL = [
    ("s0", "s0", "inicio=0"), ("s0", "s1", "inicio=1"), ("s1", "s2", ""),
    ("s2", "s2", "copia"), ("s2", "s3", "i=n, j=n"), ("s3", "s4", ""),
    ("s4", "s8", "a(k,k)≠0"), ("s4", "s5", "a(k,k)=0"),
    ("s5", "s5", "a(i,k)=0, i≠n"), ("s5", "s6", "a(i,k)≠0"), ("s5", "s18", "i=n (det=0)"),
    ("s6", "s7", ""), ("s7", "s6", "j≠n"), ("s7", "s4", "j=n"),
    ("s8", "s9", ""), ("s9", "s10", ""), ("s10", "s11", ""), ("s11", "s12", ""),
    ("s12", "s13", ""), ("s13", "s14", ""),
    ("s14", "s14", "residuo≥|p|"), ("s14", "s15", "residuo<|p|"),
    ("s15", "s9", "falta (i,j)"), ("s15", "s16", "i=n, j=n"),
    ("s16", "s4", "k+1≠n"), ("s16", "s17", "k+1=n"), ("s17", "s18", ""),
    ("s18", "s18", "inicio=0"), ("s18", "s1", "inicio=1"),
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
        "UNIDAD DE CONTROL\n\nregistro de estado st\n(s0 a s18, 5 bits)\nlógica de estado siguiente\ny de salidas",
        "CAMINO DE DATOS\n\nROM, RAM A, RAM B,\n3 decodificadores dir_ram,\nmultiplicador, sumador/restador,\n"
        "banco de pivotes,\nregistros y multiplexores",
        "clk\nrst\ninicio",
        "PC: palabra de control (18 bits)\nwe, sel_data, sel_fra, sel_cra,\nsel_frb, sel_fw, sel_sra, sel_srb,\n"
        "op, clr_banco, we_banco, sel_banco\n(+ cargas de los registros)",
        "señales de estado (9)\nz_a, i_n, j_n, k1_n, t3_neg,\nres_neg, sq, piv_neg, signo",
        "final", "clk, rst\ndir_p (3)", "det (32)\npivote (32)")


def gris_vis():
    return _caja_gris(
        "UNIDAD DE CONTROL\n\nregistro de estado xs\n(x0 a x5, 3 bits)",
        "CAMINO DE DATOS\n\nmux det/pivote, restador 0 − val,\nregistros bin, dec, cont, d,\n"
        "sumador +3, comparador > 4,\nregistro disp y display",
        "clk\nrst\nfinal",
        "PC: palabra de control (8 bits)\nld_bin, clr_dec, ld_lsb, clr_d,\nld_dig, inc_d, desp, ld_disp",
        "señales de estado (4)\nval_neg, cont_31, dig_mayor_4, d_9",
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
  EXT [shape=box, label="extensión\\nde signo 6 → 32"];
  MF [{mux}, label="mux fila / columna\\n(i, j, k, n)"];
  DA [shape=box, label="dir_ram\\nlectura A"]; DB [shape=box, label="dir_ram\\nlectura B"];
  DW [shape=box, label="dir_ram\\nescritura"];
  MD [{mux}, label="mux data\\na | qa | tmp | ±cociente"];
  RAMA [{mem}, label="RAM A\\n32 × 32"]; RAMB [{mem}, label="RAM B\\n32 × 32"];
  Z [shape=ellipse, label="qa = 0 ?\\n(a la UC)"];
  PIV [{reg}, label="piv"]; TMP [{reg}, label="tmp"];
  MA [{reg}, label="mul_a"]; MB [{reg}, label="mul_b"];
  MUL [{uf}, label="MULTIPLICADOR\\n25 × 25 → 50"];
  T1 [{reg}, label="t1"]; T2 [{reg}, label="t2"]; T3 [{reg}, label="t3"];
  RES [{reg}, label="residuo"]; COC [{reg}, label="cociente"];
  PP [{reg}, label="p, |p|"];
  XA [{mux}, label="mux sr_a\\n0 | t1 | residuo"];
  XB [{mux}, label="mux sr_b\\n0 | t2 | t3 | |p| |\\ncociente | piv | qa"];
  SR [{uf}, label="SUMADOR/\\nRESTADOR\\n50 bits (op)"];
  DN [{mux}, label="±a(n,n)\\nqa | resultado"];
  DET [{reg}, label="det"];
  MBAN [{mux}, label="dato banco\\npiv | ±a(n,n)"];
  BAN [{mem}, label="BANCO DE\\nPIVOTES 5 × 32"];
  dirp [shape=plaintext, label="dir_p"];
  odet [shape=plaintext, label="det (32)"]; opiv [shape=plaintext, label="pivote (32)"];
  CNT -> ROM [label="dira"]; ROM -> EXT -> MD;
  CNT -> MF; MF -> DA; MF -> DB; MF -> DW;
  DA -> RAMA [label="rd_add"]; DB -> RAMB [label="rd_add"];
  DW -> RAMA [label="wr_add"]; DW -> RAMB;
  MD -> RAMA [label="data"]; MD -> RAMB;
  RAMA -> Z; RAMA -> PIV [label="qa"]; RAMA -> MA; RAMA -> MB; RAMA -> MD; RAMA -> XB; RAMA -> DN;
  RAMB -> TMP [label="qb"]; RAMB -> MB;
  TMP -> MD;
  PIV -> MA; PIV -> XB; PIV -> PP; PIV -> MBAN;
  MA -> MUL; MB -> MUL; MUL -> T1 [label="producto"]; MUL -> T2;
  T1 -> XA; RES -> XA; T2 -> XB; T3 -> XB; PP -> XB; COC -> XB;
  XA -> SR [label="sr_a"]; XB -> SR [label="sr_b"];
  SR -> T3 [label="resultado"]; SR -> RES; SR -> PP; SR -> MD; SR -> DN;
  DN -> DET; DN -> MBAN;
  MBAN -> BAN; dirp -> BAN [label="dir_r"];
  DET -> odet; BAN -> opiv;
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

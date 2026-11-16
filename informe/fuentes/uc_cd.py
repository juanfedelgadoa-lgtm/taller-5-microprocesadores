#!/usr/bin/env python3
"""Camino de datos (CD) y unidad de control (UC) del informe del Taller 5.

Describe, a partir de los diagramas ASM, el hardware que sale del VHDL de alto
nivel (src/procesador_bareiss.vhd y src/visualizador.vhd):

  * los campos de la palabra de control (PC) de cada CD,
  * una fila por cada camino del ASM: estado, condiciones, estado siguiente y
    PC de ese camino (con esto se llenan la ROM de entrada y la ROM de salida),
  * un modelo ciclo a ciclo del CD manejado solo por esas tablas, para
    comprobar que dan los mismos resultados y ciclos que la simulacion del VHDL.

Uso:  python3 informe/fuentes/uc_cd.py          (incluye la matriz 7, unos minutos)
      python3 informe/fuentes/uc_cd.py --rapido (sin la matriz 7)
"""
import itertools
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "sim"))

M3, M5, M25, M32, M50 = 0x7, 0x1F, (1 << 25) - 1, (1 << 32) - 1, (1 << 50) - 1


def sext(x, bits):
    x &= (1 << bits) - 1
    return x - (1 << bits) if x >> (bits - 1) else x


def F(cond, sig, **pc):
    return (cond, sig, pc)


# ===========================================================================
# PROCESADOR DE BAREISS
# ===========================================================================
ESTADOS_P = [f"s{i}" for i in range(14)]

# (nombre, pregunta del ASM, bloque del CD que la genera, estados que la usan)
SENALES_P = [
    ("inicio", "inicio = 1", "Entrada externa (pulso del antirrebote)", "s0, s13"),
    ("z_b", "a(k,k) = 0", "Comparador de 32 bits: qb (salida de la RAM B) = 0", "s2"),
    ("z_a", "a(i,k) = 0", "Comparador de 32 bits: qa (salida de la RAM A) = 0", "s3"),
    ("i_n", "i = n", "Comparador de 3 bits", "s1, s3, s12"),
    ("j_n", "j = n", "Comparador de 3 bits", "s1, s5, s12"),
    ("k1_n", "k + 1 = n", "Incrementador de k y comparador de 3 bits", "s11, s12"),
    ("ms", "r(49) = s(49)", "Compuerta XNOR de los bits de signo de r y s", "s11"),
    ("sg", "signo = 1", "Salida del registro signo", "s11"),
    ("rt", "r = t", "Comparador de 50 bits", "s12"),
]

# (nombre, bits, grupo, que controla, codigos)
CAMPOS_P = [
    ("ld_dira", 1, "ld", "Carga dira", "1 = carga"),
    ("sel_dira", 1, "sel", "MUX de dira", "0 = 1 · 1 = dira + 1"),
    ("ld_n", 1, "ld", "Carga n", "1 = carga a(2..0)"),
    ("ld_i", 1, "ld", "Carga i", "1 = carga"),
    ("sel_i", 2, "sel", "MUX de i", "00 = 1 · 01 = i + 1 · 10 = k + 1"),
    ("ld_j", 1, "ld", "Carga j", "1 = carga"),
    ("sel_j", 2, "sel", "MUX de j", "00 = 1 · 01 = j + 1 · 10 = k · 11 = k + 1"),
    ("ld_k", 1, "ld", "Carga k", "1 = carga"),
    ("sel_k", 1, "sel", "MUX de k", "0 = 1 · 1 = k + 1"),
    ("ld_piv", 1, "ld", "Carga piv", "1 = carga qb"),
    ("ld_p", 1, "ld", "Carga p", "1 = carga"),
    ("sel_p", 1, "sel", "MUX de p", "0 = 1 · 1 = piv"),
    ("ld_aik", 1, "ld", "Carga aik", "1 = carga qa"),
    ("ld_tmp", 1, "ld", "Carga tmp", "1 = carga qa"),
    ("ld_sg", 1, "ld", "Carga signo", "1 = carga"),
    ("sel_sg", 1, "sel", "MUX de signo", "0 = 0 · 1 = not signo"),
    ("we_b", 1, "ld", "Escribe banco(k)", "1 = banco(k) ← qb"),
    ("ld_det", 1, "ld", "Carga det", "1 = carga"),
    ("sel_det", 1, "sel", "MUX de det", "0 = 0 · 1 = cociente"),
    ("ld_x", 1, "ld", "Carga x", "1 = carga"),
    ("sel_x", 1, "sel", "MUX de x", "0 = piv · 1 = aik"),
    ("ld_y", 1, "ld", "Carga y", "1 = carga"),
    ("sel_y", 1, "sel", "MUX de y", "0 = qa · 1 = qb"),
    ("ld_r", 1, "ld", "Carga r", "1 = carga"),
    ("sel_r", 2, "sel", "MUX de r", "00 = x·y · 01 = r − s · 10 = 0"),
    ("ld_s", 1, "ld", "Carga s", "1 = carga"),
    ("sel_s", 1, "sel", "MUX de s", "0 = x·y · 1 = p (con extensión de signo)"),
    ("ld_t", 1, "ld", "Carga t", "1 = carga"),
    ("sel_t", 1, "sel", "MUX de t", "0 = 0 · 1 = r"),
    ("ld_c", 1, "ld", "Carga cociente", "1 = carga"),
    ("sel_c", 1, "sel", "MUX de cociente", "0 = 0 · 1 = cociente ± 1 (− si sq = 1)"),
    ("ld_sq", 1, "ld", "Carga sq", "1 = carga"),
    ("sel_sq", 1, "sel", "MUX de sq", "0 = r(49) ⊕ s(49) · 1 = not (r(49) ⊕ s(49))"),
    ("we", 1, "ld", "Escritura de RAM A y RAM B", "1 = escribe"),
    ("sel_w", 1, "sel", "Dirección de escritura", "0 = dir_ij · 1 = dir_kj"),
    ("sel_d", 2, "sel", "Dato que se escribe", "00 = a (ROM) · 01 = qb · 10 = tmp · 11 = cociente"),
]
BITS_PC_P = sum(c[1] for c in CAMPOS_P)

# (registro, bits, carga, selector o None, contenido, estados que lo escriben)
REGISTROS_P = [
    ("dira", 5, "ld_dira", "sel_dira", "Dirección de la ROM", "s0, s1, s13"),
    ("n", 3, "ld_n", None, "Tamaño de la matriz (ROM 00h)", "s0"),
    ("i", 3, "ld_i", "sel_i", "Fila", "s0, s1, s2, s3, s12, s13"),
    ("j", 3, "ld_j", "sel_j", "Columna", "s0, s1, s5, s6, s12, s13"),
    ("k", 3, "ld_k", "sel_k", "Paso de Bareiss", "s1, s12"),
    ("piv", 32, "ld_piv", None, "Pivote actual a(k,k)", "s2"),
    ("p", 32, "ld_p", "sel_p", "Pivote anterior (divisor)", "s1, s12"),
    ("aik", 32, "ld_aik", None, "a(i,k) de la fila i", "s6"),
    ("tmp", 32, "ld_tmp", None, "Intercambio de filas", "s4"),
    ("signo", 1, "ld_sg", "sel_sg", "1 = número impar de intercambios", "s1, s3"),
    ("b1 a b4", 128, "we_b", None, "Banco de pivotes (4 × 32)", "s2"),
    ("det", 32, "ld_det", "sel_det", "Determinante (salida det)", "s3, s12"),
    ("x", 25, "ld_x", "sel_x", "Entrada A del multiplicador", "s7, s8"),
    ("y", 25, "ld_y", "sel_y", "Entrada B del multiplicador", "s7, s8"),
    ("r", 50, "ld_r", "sel_r", "Minuendo del restador; en la división, el residuo", "s8, s10, s11, s12"),
    ("s", 50, "ld_s", "sel_s", "Sustraendo del restador: a(i,k)·a(k,j) y luego p", "s9, s10"),
    ("t", 50, "ld_t", "sel_t", "Valor al que debe llegar r en la división", "s11"),
    ("cociente", 32, "ld_c", "sel_c", "Contador de restas (ascendente o descendente)", "s10, s12"),
    ("sq", 1, "ld_sq", "sel_sq", "1 = cociente negativo (cuenta hacia abajo)", "s11"),
]

FILAS_P = {
    "s0": [F({"inicio": 0}, "s0"),
           F({"inicio": 1}, "s1", ld_n=1, ld_dira=1, sel_dira="0", ld_i=1, sel_i="00", ld_j=1, sel_j="00")],
    "s1": [F({"i_n": 0}, "s1", we=1, sel_w="0", sel_d="00", ld_dira=1, sel_dira="1", ld_i=1, sel_i="01"),
           F({"i_n": 1, "j_n": 0}, "s1", we=1, sel_w="0", sel_d="00", ld_dira=1, sel_dira="1",
             ld_i=1, sel_i="00", ld_j=1, sel_j="01"),
           F({"i_n": 1, "j_n": 1}, "s2", we=1, sel_w="0", sel_d="00", ld_dira=1, sel_dira="1",
             ld_k=1, sel_k="0", ld_j=1, sel_j="00", ld_p=1, sel_p="0", ld_sg=1, sel_sg="0")],
    "s2": [F({"z_b": 1}, "s3", ld_piv=1, ld_i=1, sel_i="10"),
           F({"z_b": 0}, "s6", ld_piv=1, ld_i=1, sel_i="10", we_b=1)],
    "s3": [F({"z_a": 0}, "s4", ld_sg=1, sel_sg="1"),
           F({"z_a": 1, "i_n": 1}, "s13", ld_det=1, sel_det="0"),
           F({"z_a": 1, "i_n": 0}, "s3", ld_i=1, sel_i="01")],
    "s4": [F({}, "s5", we=1, sel_w="0", sel_d="01", ld_tmp=1)],
    "s5": [F({"j_n": 1}, "s2", we=1, sel_w="1", sel_d="10", ld_j=1, sel_j="10"),
           F({"j_n": 0}, "s4", we=1, sel_w="1", sel_d="10", ld_j=1, sel_j="01")],
    "s6": [F({}, "s7", ld_aik=1, ld_j=1, sel_j="11")],
    "s7": [F({}, "s8", ld_x=1, sel_x="0", ld_y=1, sel_y="0")],
    "s8": [F({}, "s9", ld_r=1, sel_r="00", ld_x=1, sel_x="1", ld_y=1, sel_y="1")],
    "s9": [F({}, "s10", ld_s=1, sel_s="0")],
    "s10": [F({}, "s11", ld_r=1, sel_r="01", ld_s=1, sel_s="1", ld_c=1, sel_c="0")],
    "s11": [F({"ms": ms, **cond}, "s12",
              **({"ld_t": 1, "sel_t": "0"} if ms else {"ld_t": 1, "sel_t": "1", "ld_r": 1, "sel_r": "10"}),
              ld_sq=1, sel_sq=inv)
            for ms in (1, 0)
            for cond, inv in (({"k1_n": 0}, "0"), ({"k1_n": 1, "sg": 0}, "0"), ({"k1_n": 1, "sg": 1}, "1"))],
    "s12": [F({"rt": 0}, "s12", ld_r=1, sel_r="01", ld_c=1, sel_c="1"),
            F({"rt": 1, "j_n": 0}, "s7", we=1, sel_w="0", sel_d="11", ld_j=1, sel_j="01"),
            F({"rt": 1, "j_n": 1, "i_n": 0}, "s6", we=1, sel_w="0", sel_d="11", ld_i=1, sel_i="01",
              ld_j=1, sel_j="10"),
            F({"rt": 1, "j_n": 1, "i_n": 1, "k1_n": 0}, "s2", we=1, sel_w="0", sel_d="11", ld_p=1, sel_p="1",
              ld_k=1, sel_k="1", ld_j=1, sel_j="11"),
            F({"rt": 1, "j_n": 1, "i_n": 1, "k1_n": 1}, "s13", we=1, sel_w="0", sel_d="11",
              ld_det=1, sel_det="1")],
    "s13": [F({"inicio": 0}, "s13"),
            F({"inicio": 1}, "s1", ld_dira=1, sel_dira="0", ld_i=1, sel_i="00", ld_j=1, sel_j="00")],
}
FINAL_P = {"s13"}

# Operación de cada estado (para la tabla del informe)
OPERACIONES_P = {
    "s0": "final = 0. Si inicio = 1: n ← a(2..0); dira ← 1; i ← 1; j ← 1",
    "s1": "RAM(i,j) ← a; dira ← dira + 1; avanza i y j por columnas; al terminar: k ← 1, j ← 1, p ← 1, signo ← 0",
    "s2": "piv ← qb = a(k,k); i ← k + 1; si a(k,k) ≠ 0: banco(k) ← a(k,k)",
    "s3": "Busca una fila i con a(i,k) ≠ 0: signo ← not signo; si no existe (i = n): det ← 0",
    "s4": "RAM(i,j) ← a(k,j); tmp ← a(i,j)",
    "s5": "RAM(k,j) ← tmp; avanza j (j ← k al terminar, para volver a leer el pivote)",
    "s6": "aik ← a(i,k); j ← k + 1",
    "s7": "x ← piv; y ← a(i,j)",
    "s8": "r ← x·y = piv·a(i,j); x ← aik; y ← a(k,j)",
    "s9": "s ← x·y = a(i,k)·a(k,j)",
    "s10": "r ← r − s (numerador); s ← p; cociente ← 0",
    "s11": "Prepara la división: t ← 0 (mismo signo) o t ← r y r ← 0 (signos distintos); fija el sentido sq",
    "s12": "Mientras r ≠ t: r ← r − p y cociente ± 1. Al terminar: RAM(i,j) ← cociente y avanza j, i o k; "
           "en el último paso det ← cociente",
    "s13": "final = 1. Si inicio = 1: dira ← 1; i ← 1; j ← 1",
}


# ===========================================================================
# VISUALIZADOR (ASM XS3)
# ===========================================================================
ESTADOS_V = [f"x{i}" for i in range(6)]

SENALES_V = [
    ("final", "final = 1", "Salida final del procesador", "x0"),
    ("val_neg", "val < 0", "Bit 31 del MUX val (det o pivote)", "x0"),
    ("cont_31", "cont = 31", "Comparador de 5 bits", "x2"),
    ("dig_4", "dígito(d) > 4", "Comparador de 5 bits ('0' & dígito) a la salida del MUX de dígitos", "x3"),
    ("d_9", "d = 9", "Comparador de 4 bits", "x3"),
]

CAMPOS_V = [
    ("ld_bin", 1, "ld", "Carga bin", "1 = carga"),
    ("sel_bin", 2, "sel", "MUX de bin", "00 = val · 01 = 0 − val · 10 = bin << 1"),
    ("ld_neg", 1, "ld", "Carga neg", "1 = carga val(31)"),
    ("ld_dec", 1, "ld", "Carga dec", "1 = carga"),
    ("sel_dec", 2, "sel", "MUX de dec",
     "00 = 0 · 01 = dec(39..1) & bin(31) · 10 = dígito(d) + 3 en el dígito d · 11 = dec << 1"),
    ("ld_cont", 1, "ld", "Carga cont", "1 = carga"),
    ("sel_cont", 1, "sel", "MUX de cont", "0 = 0 · 1 = cont + 1"),
    ("ld_d", 1, "ld", "Carga d", "1 = carga"),
    ("sel_d", 1, "sel", "MUX de d", "0 = 0 · 1 = d + 1"),
    ("ld_disp", 1, "ld", "Carga disp y disp_neg", "1 = carga dec y neg"),
]
BITS_PC_V = sum(c[1] for c in CAMPOS_V)

REGISTROS_V = [
    ("bin", 32, "ld_bin", "sel_bin", "Registro binario (|val|)", "x0, x4"),
    ("neg", 1, "ld_neg", None, "Signo del valor", "x0"),
    ("dec", 40, "ld_dec", "sel_dec", "Registro decimal: 10 dígitos BCD", "x1, x2, x3, x4"),
    ("cont", 5, "ld_cont", "sel_cont", "Bits que ya entraron (0 a 31)", "x1, x4"),
    ("d", 4, "ld_d", "sel_d", "Dígito que se revisa (0 a 9)", "x2, x3"),
    ("disp, disp_neg", 41, "ld_disp", None, "Valor que muestra el display", "x5"),
]

FILAS_V = {
    "x0": [F({"final": 0}, "x0"),
           F({"final": 1, "val_neg": 1}, "x1", ld_bin=1, sel_bin="01", ld_neg=1),
           F({"final": 1, "val_neg": 0}, "x1", ld_bin=1, sel_bin="00", ld_neg=1)],
    "x1": [F({}, "x2", ld_dec=1, sel_dec="00", ld_cont=1, sel_cont="0")],
    "x2": [F({"cont_31": 1}, "x5", ld_dec=1, sel_dec="01"),
           F({"cont_31": 0}, "x3", ld_dec=1, sel_dec="01", ld_d=1, sel_d="0")],
    "x3": [F({"dig_4": g, "d_9": d9}, "x4" if d9 else "x3",
             **({"ld_dec": 1, "sel_dec": "10"} if g else {}), **({} if d9 else {"ld_d": 1, "sel_d": "1"}))
           for g in (1, 0) for d9 in (0, 1)],
    "x4": [F({}, "x2", ld_dec=1, sel_dec="11", ld_bin=1, sel_bin="10", ld_cont=1, sel_cont="1")],
    "x5": [F({}, "x0", ld_disp=1)],
}
FINAL_V = set()

OPERACIONES_V = {
    "x0": "Espera final = 1; bin ← |val|; neg ← val(31)",
    "x1": "PASO 1: dec ← 0; cont ← 0",
    "x2": "PASO 2: dec(0) ← bin(31); si cont = 31 termina (PASO 5); si no, d ← 0",
    "x3": "PASO 3: si dígito(d) > 4: dígito(d) ← dígito(d) + 3; d ← d + 1 hasta d = 9",
    "x4": "PASO 4: dec ← dec << 1; bin ← bin << 1; cont ← cont + 1",
    "x5": "disp ← dec; disp_neg ← neg",
}


# ===========================================================================
# Tablas de la UC
# ===========================================================================
def pc_completa(pc, campos):
    """PC con todos los campos: cargas y escrituras en 0; selectores sin usar en X."""
    out = {}
    for nombre, bits, grupo, _, _ in campos:
        if nombre in pc:
            out[nombre] = str(pc[nombre]).zfill(bits)
        elif grupo == "ld":
            out[nombre] = "0"
        else:
            out[nombre] = "X" * bits
    return out


def codigo(estados, e):
    n = max(1, (len(estados) - 1).bit_length())
    return format(estados.index(e), f"0{n}b")


def entradas_que_influyen(filas, campos, cual):
    """Señales que cambian el estado siguiente (cual = 'sig') o la PC ('pc')."""
    res = set()
    for lista in filas.values():
        for (c1, s1, p1), (c2, s2, p2) in itertools.combinations(lista, 2):
            dif = [k for k in set(c1) & set(c2) if c1[k] != c2[k]]
            if len(dif) != 1:
                continue
            if (cual == "sig" and s1 != s2) or (cual == "pc" and pc_completa(p1, campos) != pc_completa(p2, campos)):
                res.add(dif[0])
    return res


def proyectar(filas, campos, senales, cual):
    """Filas de la ROM de entrada ('sig') o de salida ('pc') con solo las señales que influyen."""
    usadas = entradas_que_influyen(filas, campos, cual)
    orden = [s[0] for s in senales if s[0] in usadas]
    out = []
    for e, lista in filas.items():
        vistos = []
        for cond, sig, pc in lista:
            clave = {k: v for k, v in cond.items() if k in usadas}
            valor = sig if cual == "sig" else pc_completa(pc, campos)
            if (clave, valor) not in vistos:
                vistos.append((clave, valor))
        for clave, valor in vistos:
            out.append((e, clave, valor))
    return orden, out


def verificar_filas(filas, estados):
    """Regla 1 del ASM: cada combinación de las decisiones de un estado da una sola fila."""
    errores = []
    for e in estados:
        lista = filas.get(e, [])
        if not lista:
            errores.append(f"{e}: sin filas")
            continue
        senales = sorted({k for c, _, _ in lista for k in c})
        for valores in itertools.product((0, 1), repeat=len(senales)):
            combo = dict(zip(senales, valores))
            n = sum(1 for c, _, _ in lista if all(combo[k] == v for k, v in c.items()))
            if n != 1:
                errores.append(f"{e}: {combo} coincide con {n} filas")
    return errores


def fila_de(filas, e, senal):
    for cond, sig, pc in filas[e]:
        if all(senal[k] == v for k, v in cond.items()):
            return sig, pc
    raise RuntimeError(f"{e}: ninguna fila para {senal}")


def campo(pcc, nombre):
    v = pcc[nombre]
    if "X" in v:
        raise RuntimeError(f"se usa el campo {nombre} con valor X")
    return v


# ===========================================================================
# Modelo ciclo a ciclo del CD del procesador manejado por la tabla de la UC
# ===========================================================================
def dir_ram(f, c):
    return (24 + f) if c == 5 else ((f << 2) | (c & 3))


def simular_procesador(rom, max_ciclos=50_000_000):
    """Devuelve (det, pivotes, ciclos). Los ciclos se cuentan desde el flanco en
    que s0 ve inicio = 1 hasta el flanco en que la UC entra a s13."""
    r = dict(dira=0, n=0, i=0, j=0, k=0, piv=0, p=0, aik=0, tmp=0, sg=0, det=0, x=0, y=0,
             r=0, s=0, t=0, c=0, sq=0)
    ram = [None] * 32
    banco = [0] * 5
    st = "s0"
    for ciclo in range(max_ciclos):
        qa, qb = ram[dir_ram(r["i"], r["j"])], ram[dir_ram(r["k"], r["j"])]
        a6 = rom[r["dira"]]
        prod = (sext(r["x"], 25) * sext(r["y"], 25)) & M50
        resta = (r["r"] - r["s"]) & M50
        senal = dict(inicio=1 if ciclo == 0 else 0,
                     z_b=None if qb is None else int(qb == 0), z_a=None if qa is None else int(qa == 0),
                     i_n=int(r["i"] == r["n"]), j_n=int(r["j"] == r["n"]),
                     k1_n=int(((r["k"] + 1) & M3) == r["n"]),
                     ms=int((r["r"] >> 49) == (r["s"] >> 49)), sg=r["sg"], rt=int(r["r"] == r["t"]))
        for k_ in {k for c, _, _ in FILAS_P[st] for k in c}:
            if senal[k_] is None:
                raise RuntimeError(f"{st}: la decisión {k_} lee una posición de la RAM sin escribir")
        sig, pc = fila_de(FILAS_P, st, senal)
        pcc = pc_completa(pc, CAMPOS_P)
        nuevo = dict(r)

        def carga(reg, ld, valor):
            if pcc[ld] == "1":
                nuevo[reg] = valor()

        carga("dira", "ld_dira", lambda: {"0": 1, "1": (r["dira"] + 1) & M5}[campo(pcc, "sel_dira")])
        carga("n", "ld_n", lambda: a6 & M3)
        carga("i", "ld_i", lambda: {"00": 1, "01": (r["i"] + 1) & M3, "10": (r["k"] + 1) & M3}[campo(pcc, "sel_i")])
        carga("j", "ld_j", lambda: {"00": 1, "01": (r["j"] + 1) & M3, "10": r["k"],
                                    "11": (r["k"] + 1) & M3}[campo(pcc, "sel_j")])
        carga("k", "ld_k", lambda: {"0": 1, "1": (r["k"] + 1) & M3}[campo(pcc, "sel_k")])
        carga("piv", "ld_piv", lambda: qb)
        carga("p", "ld_p", lambda: {"0": 1, "1": r["piv"]}[campo(pcc, "sel_p")])
        carga("aik", "ld_aik", lambda: qa)
        carga("tmp", "ld_tmp", lambda: qa)
        carga("sg", "ld_sg", lambda: {"0": 0, "1": r["sg"] ^ 1}[campo(pcc, "sel_sg")])
        carga("det", "ld_det", lambda: {"0": 0, "1": r["c"]}[campo(pcc, "sel_det")])
        carga("x", "ld_x", lambda: {"0": r["piv"] & M25, "1": r["aik"] & M25}[campo(pcc, "sel_x")])
        carga("y", "ld_y", lambda: {"0": qa & M25, "1": qb & M25}[campo(pcc, "sel_y")])
        carga("r", "ld_r", lambda: {"00": prod, "01": resta, "10": 0}[campo(pcc, "sel_r")])
        carga("s", "ld_s", lambda: {"0": prod, "1": sext(r["p"], 32) & M50}[campo(pcc, "sel_s")])
        carga("t", "ld_t", lambda: {"0": 0, "1": r["r"]}[campo(pcc, "sel_t")])
        carga("c", "ld_c", lambda: {"0": 0, "1": (r["c"] + (-1 if r["sq"] else 1)) & M32}[campo(pcc, "sel_c")])
        xs = (r["r"] >> 49) ^ (r["s"] >> 49)
        carga("sq", "ld_sq", lambda: {"0": xs, "1": xs ^ 1}[campo(pcc, "sel_sq")])
        if pcc["we"] == "1":
            fila = r["k"] if campo(pcc, "sel_w") == "1" else r["i"]
            dato = {"00": sext(a6, 6) & M32, "01": qb, "10": r["tmp"], "11": r["c"]}[campo(pcc, "sel_d")]
            ram[dir_ram(fila, r["j"])] = dato
        if pcc["we_b"] == "1":
            banco[r["k"]] = qb
        r, st = nuevo, sig
        if st == "s13":
            det = sext(r["det"], 32)
            return det, [sext(banco[k], 32) for k in range(1, r["n"])] + [det], ciclo + 1
    raise RuntimeError("no llegó a s13")


def simular_visualizador(valor):
    """Devuelve (10 dígitos BCD, neg, ciclos de una conversión)."""
    r = dict(bin=0, neg=0, dec=0, cont=0, d=0, disp=0, disp_neg=0)
    val = valor & M32
    st = "x0"
    for ciclo in range(2000):
        dig = (r["dec"] >> (4 * r["d"])) & 0xF if r["d"] <= 9 else 0
        senal = dict(final=1, val_neg=val >> 31, cont_31=int(r["cont"] == 31), dig_4=int(dig > 4),
                     d_9=int(r["d"] == 9))
        sig, pc = fila_de(FILAS_V, st, senal)
        pcc = pc_completa(pc, CAMPOS_V)
        nuevo = dict(r)
        if pcc["ld_bin"] == "1":
            nuevo["bin"] = {"00": val, "01": (-val) & M32, "10": (r["bin"] << 1) & M32}[campo(pcc, "sel_bin")]
        if pcc["ld_neg"] == "1":
            nuevo["neg"] = val >> 31
        if pcc["ld_dec"] == "1":
            s = campo(pcc, "sel_dec")
            if s == "00":
                nuevo["dec"] = 0
            elif s == "01":
                nuevo["dec"] = (r["dec"] & ~1) | (r["bin"] >> 31)
            elif s == "10":
                sh = 4 * r["d"]
                nuevo["dec"] = (r["dec"] & ~(0xF << sh)) | (((dig + 3) & 0xF) << sh)
            else:
                nuevo["dec"] = (r["dec"] << 1) & ((1 << 40) - 1)
        if pcc["ld_cont"] == "1":
            nuevo["cont"] = {"0": 0, "1": (r["cont"] + 1) & M5}[campo(pcc, "sel_cont")]
        if pcc["ld_d"] == "1":
            nuevo["d"] = {"0": 0, "1": (r["d"] + 1) & 0xF}[campo(pcc, "sel_d")]
        if pcc["ld_disp"] == "1":
            nuevo["disp"], nuevo["disp_neg"] = r["dec"], r["neg"]
        r = nuevo
        if st == "x5":
            return [(r["disp"] >> (4 * k)) & 0xF for k in range(10)], r["disp_neg"], ciclo + 1
        st = sig
    raise RuntimeError("el XS3 no terminó")


def ciclos_ghdl():
    texto = (RAIZ / "sim" / "resultado_ghdl.txt").read_text(encoding="utf-8")
    res = {}
    for bloque in re.split(r"== Matriz ", texto)[1:]:
        m = re.search(r"Corrida 1: final = 1 en (\d+) ciclos", bloque)
        if m:
            res[int(bloque.split()[0])] = int(m.group(1))
    return res


def rom_de(a):
    n = len(a)
    rom = [0] * 32
    rom[0] = n
    d = 1
    for j in range(n):
        for i in range(n):
            rom[d] = a[i][j] & 0x3F
            d += 1
    return rom


def comprobar(rapido=False, salida=print):
    from modelo_referencia import MATRICES, bareiss
    errores = verificar_filas(FILAS_P, ESTADOS_P) + verificar_filas(FILAS_V, ESTADOS_V)
    ghdl = ciclos_ghdl()
    res = []
    for num, a in enumerate(MATRICES):
        if rapido and num == 7:
            continue
        det, piv, ciclos = simular_procesador(rom_de(a), 30_000_000 if num == 7 else 200_000)
        det_ref, piv_ref, _ = bareiss(a)
        ok = det == det_ref and piv == piv_ref and ghdl.get(num) in (None, ciclos - 2)
        if not ok:
            errores.append(f"matriz {num}: modelo det={det} piv={piv} ciclos={ciclos}; "
                           f"esperado {det_ref} {piv_ref}, GHDL {ghdl.get(num)}")
        res.append((num, len(a), det, piv, ciclos, ghdl.get(num), ok))
        salida(f"matriz {num}: det = {det}, pivotes = {piv}, {ciclos} ciclos (GHDL: {ghdl.get(num)} + 2)  "
               f"{'OK' if ok else 'ERROR'}")
    for v in (0, 7, 362, -170, 9999999, -17121828, 2147483647, -2147483647):
        digitos, neg, ciclos = simular_visualizador(v)
        texto = "".join(str(x) for x in reversed(digitos))
        ok = texto == str(abs(v)).zfill(10) and neg == (v < 0) and ciclos == 376
        if not ok:
            errores.append(f"XS3 {v}: {texto} neg={neg} ciclos={ciclos}")
        salida(f"XS3 {v:>12}: dec = {texto}, neg = {neg}, {ciclos} ciclos  {'OK' if ok else 'ERROR'}")
    return res, errores


if __name__ == "__main__":
    _, errores = comprobar(rapido="--rapido" in sys.argv)
    for e in errores:
        print("ERROR:", e)
    print(f"PC del procesador: {BITS_PC_P} bits; PC del visualizador: {BITS_PC_V} bits")
    for nombre, filas, campos, senales in (("procesador", FILAS_P, CAMPOS_P, SENALES_P),
                                           ("visualizador", FILAS_V, CAMPOS_V, SENALES_V)):
        o1, r1 = proyectar(filas, campos, senales, "sig")
        o2, r2 = proyectar(filas, campos, senales, "pc")
        print(f"{nombre}: estado siguiente {o1} ({len(r1)} filas); PC {o2} ({len(r2)} filas)")
    sys.exit(1 if errores else 0)

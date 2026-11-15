#!/usr/bin/env python3
"""Camino de datos (CD) y unidad de control (UC) que se esperan de los ASM.

Este archivo describe, a partir de los diagramas ASM, el hardware que debe
salir del VHDL de alto nivel:

  * los campos de la palabra de control (PC) de cada CD,
  * una fila por cada camino del ASM: estado, condiciones, estado siguiente y
    la PC de ese camino (es la tabla de la UC: ROM de entrada + ROM de salida),
  * un modelo ciclo a ciclo del CD manejado por esa tabla, para comprobar que
    la UC y el CD propuestos calculan lo mismo que el VHDL (mismos resultados y
    mismos ciclos que la simulacion con GHDL).

Uso:  python3 uc_cd.py          comprueba las tablas y simula las 8 matrices
      python3 uc_cd.py --rapido no simula la matriz 7 (19 millones de ciclos)
"""
import itertools
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "sim"))

M3, M5, M25, M32, M50 = 0x7, 0x1F, (1 << 25) - 1, (1 << 32) - 1, (1 << 50) - 1


def sext(x, bits):
    """Valor con signo de x (bits en complemento a 2)."""
    x &= (1 << bits) - 1
    return x - (1 << bits) if x >> (bits - 1) else x


# ===========================================================================
# PROCESADOR DE BAREISS
# ===========================================================================
ESTADOS_P = [f"s{i}" for i in range(19)]

# Senales de estado (CD -> UC). La entrada externa inicio tambien llega a la UC.
SENALES_P = [
    ("inicio", "entrada externa", "Pulso del antirrebote"),
    ("z_a", "qa = 0", "Comparador de 32 bits de la salida de la RAM A con cero"),
    ("i_n", "i = n", "Comparador de 3 bits"),
    ("j_n", "j = n", "Comparador de 3 bits"),
    ("k1_n", "k + 1 = n", "Incrementador de k y comparador de 3 bits"),
    ("t3_neg", "t3 < 0", "Bit 49 del registro t3"),
    ("res_neg", "residuo − |p| < 0", "Bit 49 de la salida del sumador/restador"),
    ("sq", "sq = 1", "Registro del signo del cociente"),
    ("piv_neg", "piv < 0", "Bit 31 del registro piv"),
    ("signo", "signo = 1", "Registro de paridad de intercambios"),
]

# Campos de la palabra de control: (nombre, bits, grupo, que controla, codigos)
CAMPOS_P = [
    # cargas de registros
    ("ld_dira", 1, "ld", "carga dira", "1 = carga"),
    ("ld_n", 1, "ld", "carga n", "1 = carga"),
    ("ld_i", 1, "ld", "carga i", "1 = carga"),
    ("ld_j", 1, "ld", "carga j", "1 = carga"),
    ("ld_k", 1, "ld", "carga k", "1 = carga"),
    ("ld_piv", 1, "ld", "carga piv", "1 = carga"),
    ("ld_p", 1, "ld", "carga p", "1 = carga"),
    ("ld_pabs", 1, "ld", "carga |p|", "1 = carga"),
    ("ld_signo", 1, "ld", "carga signo", "1 = carga"),
    ("ld_tmp", 1, "ld", "carga tmp", "1 = carga"),
    ("ld_ma", 1, "ld", "carga mul_a", "1 = carga"),
    ("ld_mb", 1, "ld", "carga mul_b", "1 = carga"),
    ("ld_t1", 1, "ld", "carga t1", "1 = carga"),
    ("ld_t2", 1, "ld", "carga t2", "1 = carga"),
    ("ld_t3", 1, "ld", "carga t3", "1 = carga"),
    ("ld_res", 1, "ld", "carga residuo", "1 = carga"),
    ("ld_coc", 1, "ld", "carga cociente", "1 = carga"),
    ("ld_sq", 1, "ld", "carga sq", "1 = carga"),
    ("ld_det", 1, "ld", "carga det", "1 = carga"),
    # selectores de los MUX de entrada de los registros
    ("sel_dira", 2, "sel", "MUX de dira", "00 = 0 · 01 = 1 · 10 = dira + 1"),
    ("sel_i", 2, "sel", "MUX de i", "00 = 1 · 01 = i + 1 · 10 = k + 1"),
    ("sel_j", 2, "sel", "MUX de j", "00 = 1 · 01 = j + 1 · 10 = k · 11 = k + 1"),
    ("sel_k", 1, "sel", "MUX de k", "0 = 1 · 1 = k + 1"),
    ("sel_p", 1, "sel", "MUX de p", "0 = 1 · 1 = piv"),
    ("sel_pabs", 2, "sel", "MUX de |p|", "00 = 1 · 01 = piv · 10 = resultado"),
    ("sel_signo", 1, "sel", "MUX de signo", "0 = 0 · 1 = not signo"),
    ("sel_ma", 1, "sel", "MUX de mul_a", "0 = piv · 1 = qa"),
    ("sel_mb", 1, "sel", "MUX de mul_b", "0 = qa · 1 = qb"),
    ("sel_res", 1, "sel", "MUX de residuo", "0 = t3 · 1 = resultado"),
    ("sel_coc", 1, "sel", "MUX de cociente", "0 = 0 · 1 = cociente + 1"),
    ("sel_det", 1, "sel", "MUX de det", "0 = 0 · 1 = ±a(n,n)"),
    # memorias RAM A y RAM B
    ("we", 1, "ram", "escritura de RAM A y RAM B", "1 = escribe"),
    ("sel_fra", 2, "ram", "fila de lectura de RAM A", "00 = i · 01 = k · 10 = n"),
    ("sel_cra", 2, "ram", "columna de lectura de RAM A", "00 = j · 01 = k · 10 = n"),
    ("sel_frb", 1, "ram", "fila de lectura de RAM B (columna = j)", "0 = i · 1 = k"),
    ("sel_fw", 1, "ram", "fila de escritura (columna = j)", "0 = i · 1 = k"),
    ("sel_data", 3, "ram", "dato que se escribe",
     "000 = a (ROM) · 001 = qa · 010 = tmp · 011 = cociente · 100 = resultado (0 − cociente)"),
    # sumador/restador
    ("sel_sra", 2, "sr", "operando A del sumador/restador", "00 = 0 · 01 = t1 · 10 = residuo"),
    ("sel_srb", 3, "sr", "operando B del sumador/restador",
     "000 = 0 · 001 = t2 · 010 = t3 · 011 = |p| · 100 = cociente · 101 = piv · 110 = qa"),
    ("op", 1, "sr", "operación del sumador/restador", "0 = suma · 1 = resta"),
    # banco de pivotes
    ("clr_banco", 1, "banco", "borra el banco", "1 = borra"),
    ("we_banco", 1, "banco", "escribe un pivote", "1 = escribe"),
    ("sel_banco", 1, "banco", "dirección y dato del banco", "0 = (k, piv) · 1 = (n, ±a(n,n))"),
    ("sel_nn", 1, "banco", "MUX ±a(n,n)", "0 = qa · 1 = resultado (0 − qa)"),
]
BITS_PC_P = sum(c[1] for c in CAMPOS_P)

# Campos que alimentan las senales de estado: deben ser iguales en todas las
# filas de un estado (si no, habria un lazo combinacional UC -> CD -> UC).
CAMPOS_COMB_P = ["sel_fra", "sel_cra", "sel_frb", "sel_sra", "sel_srb", "op"]


# Registros del CD: (nombre, bits, carga, selector o None, fuente fija, uso)
REGISTROS_P = [
    ("dira", 5, "ld_dira", "sel_dira", None, "Dirección de la ROM"),
    ("n", 3, "ld_n", None, "a(2..0) (ROM 00h)", "Tamaño de la matriz"),
    ("i", 3, "ld_i", "sel_i", None, "Fila"),
    ("j", 3, "ld_j", "sel_j", None, "Columna"),
    ("k", 3, "ld_k", "sel_k", None, "Paso de Bareiss"),
    ("piv", 32, "ld_piv", None, "qa", "Pivote actual a(k,k)"),
    ("p", 32, "ld_p", "sel_p", None, "Pivote anterior (solo se usa su signo)"),
    ("|p| (pabs)", 32, "ld_pabs", "sel_pabs", None, "Divisor de la división"),
    ("signo", 1, "ld_signo", "sel_signo", None, "Paridad de intercambios de filas"),
    ("tmp", 32, "ld_tmp", None, "qb", "Intercambio de filas"),
    ("mul_a", 25, "ld_ma", "sel_ma", None, "Entrada A del multiplicador"),
    ("mul_b", 25, "ld_mb", "sel_mb", None, "Entrada B del multiplicador"),
    ("t1", 50, "ld_t1", None, "producto", "a(k,k)·a(i,j)"),
    ("t2", 50, "ld_t2", None, "producto", "a(i,k)·a(k,j)"),
    ("t3", 50, "ld_t3", None, "resultado", "t1 − t2"),
    ("residuo", 50, "ld_res", "sel_res", None, "División: residuo"),
    ("cociente", 32, "ld_coc", "sel_coc", None, "División: cociente (contador)"),
    ("sq", 1, "ld_sq", None, "t3(49) xor p(31)", "Signo del cociente"),
    ("det", 32, "ld_det", "sel_det", None, "Determinante (salida det)"),
]

REGISTROS_V = [
    ("bin", 32, "ld_bin", "sel_bin", None, "Registro binario del XS3"),
    ("neg", 1, "ld_neg", None, "val(31)", "Signo del valor"),
    ("dec", 40, "ld_dec", "sel_dec", None, "Registro decimal (10 dígitos BCD)"),
    ("cont", 5, "ld_cont", "sel_cont", None, "Bits procesados (0 a 31)"),
    ("d", 4, "ld_d", "sel_d", None, "Dígito revisado (0 a 9)"),
    ("disp, disp_neg", 41, "ld_disp", None, "dec, neg", "Valor que muestra el display"),
]


def F(cond, sig, **pc):
    return (cond, sig, pc)


# Una fila por camino del ASM: (estado, condiciones, siguiente, PC). Los campos
# que no aparecen valen 0 si son cargas/escrituras y X si son selectores.
FILAS_P = {
    "s0": [F({"inicio": 0}, "s0", ld_dira=1, sel_dira="00"),
           F({"inicio": 1}, "s1", ld_dira=1, sel_dira="00")],
    "s1": [F({}, "s2", ld_n=1, ld_dira=1, sel_dira="01", ld_i=1, sel_i="00", ld_j=1, sel_j="00")],
    "s2": [F({"i_n": 0}, "s2", we=1, sel_fw="0", sel_data="000", ld_dira=1, sel_dira="10",
             ld_i=1, sel_i="01"),
           F({"i_n": 1, "j_n": 0}, "s2", we=1, sel_fw="0", sel_data="000", ld_dira=1, sel_dira="10",
             ld_i=1, sel_i="00", ld_j=1, sel_j="01"),
           F({"i_n": 1, "j_n": 1}, "s3", we=1, sel_fw="0", sel_data="000", ld_dira=1, sel_dira="10",
             ld_i=1, sel_i="00")],
    "s3": [F({}, "s4", ld_k=1, sel_k="0", ld_p=1, sel_p="0", ld_pabs=1, sel_pabs="00",
             ld_signo=1, sel_signo="0", ld_det=1, sel_det="0", clr_banco=1)],
    "s4": [F({"z_a": 1}, "s5", ld_piv=1, sel_fra="01", sel_cra="01", ld_i=1, sel_i="10"),
           F({"z_a": 0}, "s8", ld_piv=1, sel_fra="01", sel_cra="01")],
    "s5": [F({"z_a": 0}, "s6", sel_fra="00", sel_cra="01", ld_j=1, sel_j="10", ld_signo=1, sel_signo="1"),
           F({"z_a": 1, "i_n": 1}, "s18", sel_fra="00", sel_cra="01", ld_det=1, sel_det="0"),
           F({"z_a": 1, "i_n": 0}, "s5", sel_fra="00", sel_cra="01", ld_i=1, sel_i="01")],
    "s6": [F({}, "s7", we=1, sel_fw="0", sel_data="001", sel_fra="01", sel_cra="00", sel_frb="0",
             ld_tmp=1)],
    "s7": [F({"j_n": 1}, "s4", we=1, sel_fw="1", sel_data="010"),
           F({"j_n": 0}, "s6", we=1, sel_fw="1", sel_data="010", ld_j=1, sel_j="01")],
    "s8": [F({}, "s9", we_banco=1, sel_banco="0", ld_i=1, sel_i="10", ld_j=1, sel_j="11")],
    "s9": [F({}, "s10", ld_ma=1, sel_ma="0", ld_mb=1, sel_mb="0", sel_fra="00", sel_cra="00")],
    "s10": [F({}, "s11", ld_t1=1, ld_ma=1, sel_ma="1", ld_mb=1, sel_mb="1", sel_fra="00", sel_cra="01",
              sel_frb="1")],
    "s11": [F({}, "s12", ld_t2=1)],
    "s12": [F({}, "s13", ld_t3=1, sel_sra="01", sel_srb="001", op="1")],
    "s13": [F({"t3_neg": 1}, "s14", ld_coc=1, sel_coc="0", ld_sq=1, sel_sra="00", sel_srb="010", op="1",
              ld_res=1, sel_res="1"),
            F({"t3_neg": 0}, "s14", ld_coc=1, sel_coc="0", ld_sq=1, sel_sra="00", sel_srb="010", op="1",
              ld_res=1, sel_res="0")],
    "s14": [F({"res_neg": 0}, "s14", sel_sra="10", sel_srb="011", op="1", ld_res=1, sel_res="1",
              ld_coc=1, sel_coc="1"),
            F({"res_neg": 1}, "s15", sel_sra="10", sel_srb="011", op="1")],
    "s15": [F({"sq": q, "j_n": 0}, "s9", we=1, sel_fw="0", sel_data=d, sel_sra="00", sel_srb="100",
              op="1", ld_j=1, sel_j="01") for q, d in ((1, "100"), (0, "011"))]
         + [F({"sq": q, "j_n": 1, "i_n": 0}, "s9", we=1, sel_fw="0", sel_data=d, sel_sra="00",
              sel_srb="100", op="1", ld_i=1, sel_i="01", ld_j=1, sel_j="11") for q, d in ((1, "100"), (0, "011"))]
         + [F({"sq": q, "j_n": 1, "i_n": 1}, "s16", we=1, sel_fw="0", sel_data=d, sel_sra="00",
              sel_srb="100", op="1") for q, d in ((1, "100"), (0, "011"))],
    "s16": [F({"piv_neg": pn, "k1_n": kn}, "s17" if kn else "s4", ld_p=1, sel_p="1", ld_k=1, sel_k="1",
              ld_pabs=1, sel_pabs="10" if pn else "01", sel_sra="00", sel_srb="101", op="1")
            for pn in (1, 0) for kn in (0, 1)],
    "s17": [F({"signo": sg}, "s18", sel_fra="10", sel_cra="10", sel_sra="00", sel_srb="110", op="1",
              ld_det=1, sel_det="1", we_banco=1, sel_banco="1", sel_nn="1" if sg else "0")
            for sg in (1, 0)],
    "s18": [F({"inicio": 1}, "s1", ld_dira=1, sel_dira="00"),
            F({"inicio": 0}, "s18", ld_dira=1, sel_dira="00")],
}
FINAL_P = {"s18"}


# ===========================================================================
# VISUALIZADOR (ASM XS3)
# ===========================================================================
ESTADOS_V = [f"x{i}" for i in range(6)]

SENALES_V = [
    ("final", "entrada del procesador", "final del procesador de Bareiss"),
    ("val_neg", "val < 0", "Bit 31 del MUX val (det o pivote)"),
    ("cont_31", "cont = 31", "Comparador de 5 bits"),
    ("dig_4", "dígito(d) > 4", "Comparador de 4 bits a la salida del MUX de dígitos"),
    ("d_9", "d = 9", "Comparador de 4 bits"),
]

CAMPOS_V = [
    ("ld_bin", 1, "ld", "carga bin", "1 = carga"),
    ("ld_neg", 1, "ld", "carga neg", "1 = carga"),
    ("ld_dec", 1, "ld", "carga dec", "1 = carga"),
    ("ld_cont", 1, "ld", "carga cont", "1 = carga"),
    ("ld_d", 1, "ld", "carga d", "1 = carga"),
    ("ld_disp", 1, "ld", "carga disp y disp_neg", "1 = carga"),
    ("sel_bin", 2, "sel", "MUX de bin", "00 = val · 01 = 0 − val · 10 = bin << 1"),
    ("sel_dec", 2, "sel", "MUX de dec",
     "00 = 0 · 01 = dec(39..1) & bin(31) · 10 = dígito(d) + 3 · 11 = dec << 1"),
    ("sel_cont", 1, "sel", "MUX de cont", "0 = 0 · 1 = cont + 1"),
    ("sel_d", 1, "sel", "MUX de d", "0 = 0 · 1 = d + 1"),
]
BITS_PC_V = sum(c[1] for c in CAMPOS_V)
CAMPOS_COMB_V = []

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


# ===========================================================================
# Utilidades comunes a las dos UC
# ===========================================================================
def pc_completa(pc, campos):
    """Palabra de control con todos los campos: cargas/escrituras en 0 y
    selectores sin usar en X."""
    out = {}
    for nombre, bits, grupo, _, _ in campos:
        if nombre in pc:
            v = str(pc[nombre])
            out[nombre] = v.zfill(bits) if v != "X" else "X" * bits
        elif grupo == "ld" or nombre in ("we", "clr_banco", "we_banco"):
            out[nombre] = "0"
        else:
            out[nombre] = "X" * bits
    return out


def codigo(estados, e):
    n = max(1, (len(estados) - 1).bit_length())
    return format(estados.index(e), f"0{n}b")


def entradas_que_influyen(filas, campos, cual):
    """Senales que cambian el estado siguiente (cual = 'sig') o la PC ('pc')."""
    res = set()
    for e, lista in filas.items():
        for (c1, s1, p1), (c2, s2, p2) in itertools.combinations(lista, 2):
            dif = [k for k in set(c1) & set(c2) if c1[k] != c2[k]]
            if len(dif) != 1:
                continue
            if (cual == "sig" and s1 != s2) or (cual == "pc" and pc_completa(p1, campos) != pc_completa(p2, campos)):
                res.add(dif[0])
    return res


def proyectar(filas, campos, senales, cual):
    """Filas compactas de la ROM de entrada (cual='sig') o de salida ('pc'):
    solo con las senales que influyen; las demas se agrupan."""
    usadas = entradas_que_influyen(filas, campos, cual)
    orden = [s for s, _, _ in senales if s in usadas]
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


def verificar_filas(filas, campos, comb, estados):
    """Regla 1 del ASM (un solo estado siguiente y una sola PC por combinacion),
    caminos completos y campos combinacionales iguales en cada estado."""
    errores = []
    for e in estados:
        lista = filas.get(e)
        if not lista:
            errores.append(f"{e}: no tiene filas")
            continue
        senales = sorted({k for c, _, _ in lista for k in c})
        for valores in itertools.product((0, 1), repeat=len(senales)):
            combo = dict(zip(senales, valores))
            coinciden = [f for f in lista if all(combo[k] == v for k, v in f[0].items())]
            if len(coinciden) != 1:
                errores.append(f"{e}: {combo} coincide con {len(coinciden)} filas")
        for campo in comb:
            vals = {pc_completa(p, campos)[campo] for _, _, p in lista}
            if len(vals) > 1:
                errores.append(f"{e}: el campo {campo} cambia con las condiciones ({vals})")
        for _, _, p in lista:
            for k in p:
                if k not in {c[0] for c in campos}:
                    errores.append(f"{e}: campo desconocido {k}")
    return errores


def comparar_con_asm(filas):
    """Los estados siguientes de la tabla deben ser los de los diagramas ASM."""
    import diagramas
    tabla, err = diagramas.verificar()
    errores = list(err)
    for e, lista in filas.items():
        dib = {d for _, d in tabla[e]}
        tab = {s for _, s, _ in lista}
        if dib != tab:
            errores.append(f"{e}: la tabla de la UC va a {sorted(tab)} y el ASM a {sorted(dib)}")
        if len(lista) != len(tabla[e]):
            errores.append(f"{e}: {len(lista)} filas en la UC y {len(tabla[e])} caminos en el ASM")
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
    return 5 * (f - 1) + (c - 1) if 1 <= f <= 5 and 1 <= c <= 5 else 31


class NoEscrito(Exception):
    pass


def simular_procesador(rom, max_ciclos=50_000_000):
    """rom: lista de 32 palabras de 6 bits. Devuelve (det, banco, ciclos), donde
    ciclos cuenta desde el flanco en que s0 ve inicio = 1 hasta el flanco en
    que la UC entra a s18."""
    r = dict(dira=0, n=0, i=0, j=0, k=0, piv=0, p=0, pabs=0, signo=0, tmp=0, ma=0, mb=0,
             t1=0, t2=0, t3=0, res=0, coc=0, sq=0, det=0)
    ram_a, ram_b = [None] * 32, [None] * 32
    banco = [0] * 8
    st = "s0"
    ciclos = 0
    for ciclo in range(max_ciclos):
        inicio = 1 if ciclo == 0 else 0
        base = pc_completa(FILAS_P[st][0][2], CAMPOS_P)       # campos combinacionales
        fila = {"00": r["i"], "01": r["k"], "10": r["n"]}
        fra = fila.get(base["sel_fra"], r["i"])
        cra = {"00": r["j"], "01": r["k"], "10": r["n"]}.get(base["sel_cra"], r["j"])
        frb = r["k"] if base["sel_frb"] == "1" else r["i"]
        qa, qb = ram_a[dir_ram(fra, cra)], ram_b[dir_ram(frb, r["j"])]
        a6 = rom[r["dira"]]
        a32 = sext(a6, 6) & M32
        producto = (sext(r["ma"], 25) * sext(r["mb"], 25)) & M50

        def leer(x):
            if x is None:
                raise NoEscrito(f"{st}: se lee una posición de la RAM que no se ha escrito")
            return x

        sra = {"00": 0, "01": r["t1"], "10": r["res"]}.get(base["sel_sra"], 0)
        srb_fuentes = {"000": lambda: 0, "001": lambda: r["t2"], "010": lambda: r["t3"],
                       "011": lambda: r["pabs"], "100": lambda: r["coc"],
                       "101": lambda: sext(r["piv"], 32) & M50, "110": lambda: sext(leer(qa), 32) & M50}
        srb = srb_fuentes.get(base["sel_srb"], lambda: 0)()
        op = 1 if base["op"] == "1" else 0
        resultado = (sra + (srb ^ (M50 if op else 0)) + op) & M50

        senal = dict(inicio=inicio, z_a=int(qa == 0) if qa is not None else None,
                     i_n=int(r["i"] == r["n"]), j_n=int(r["j"] == r["n"]),
                     k1_n=int(((r["k"] + 1) & M3) == r["n"]), t3_neg=r["t3"] >> 49,
                     res_neg=resultado >> 49, sq=r["sq"], piv_neg=r["piv"] >> 31, signo=r["signo"])
        for k_ in {k for c, _, _ in FILAS_P[st] for k in c}:
            if senal[k_] is None:
                raise NoEscrito(f"{st}: la decisión {k_} usa una posición de la RAM sin escribir")
        sig, pc = fila_de(FILAS_P, st, senal)
        pcc = pc_completa(pc, CAMPOS_P)
        for k_ in pc:
            if k_ in CAMPOS_COMB_P and pcc[k_] != base[k_]:
                raise RuntimeError("campo combinacional distinto de la fila base")

        nn = resultado & M32 if pcc["sel_nn"] == "1" else (leer(qa) if pcc["sel_nn"] == "0" else None)
        nuevo = dict(r)

        def carga(reg, ld, valor):
            if pcc[ld] == "1":
                nuevo[reg] = valor()

        carga("dira", "ld_dira", lambda: {"00": 0, "01": 1, "10": (r["dira"] + 1) & M5}[campo(pcc, "sel_dira")])
        carga("n", "ld_n", lambda: a6 & M3)
        carga("i", "ld_i", lambda: {"00": 1, "01": (r["i"] + 1) & M3, "10": (r["k"] + 1) & M3}[campo(pcc, "sel_i")])
        carga("j", "ld_j", lambda: {"00": 1, "01": (r["j"] + 1) & M3, "10": r["k"],
                                    "11": (r["k"] + 1) & M3}[campo(pcc, "sel_j")])
        carga("k", "ld_k", lambda: {"0": 1, "1": (r["k"] + 1) & M3}[campo(pcc, "sel_k")])
        carga("piv", "ld_piv", lambda: leer(qa))
        carga("p", "ld_p", lambda: {"0": 1, "1": r["piv"]}[campo(pcc, "sel_p")])
        carga("pabs", "ld_pabs", lambda: {"00": 1, "01": r["piv"], "10": resultado & M32}[campo(pcc, "sel_pabs")])
        carga("signo", "ld_signo", lambda: {"0": 0, "1": r["signo"] ^ 1}[campo(pcc, "sel_signo")])
        carga("tmp", "ld_tmp", lambda: leer(qb))
        carga("ma", "ld_ma", lambda: {"0": r["piv"] & M25, "1": leer(qa) & M25}[campo(pcc, "sel_ma")])
        carga("mb", "ld_mb", lambda: {"0": leer(qa) & M25, "1": leer(qb) & M25}[campo(pcc, "sel_mb")])
        carga("t1", "ld_t1", lambda: producto)
        carga("t2", "ld_t2", lambda: producto)
        carga("t3", "ld_t3", lambda: resultado)
        carga("res", "ld_res", lambda: {"0": r["t3"], "1": resultado}[campo(pcc, "sel_res")])
        carga("coc", "ld_coc", lambda: {"0": 0, "1": (r["coc"] + 1) & M32}[campo(pcc, "sel_coc")])
        carga("sq", "ld_sq", lambda: (r["t3"] >> 49) ^ (r["p"] >> 31))
        carga("det", "ld_det", lambda: {"0": 0, "1": nn}[campo(pcc, "sel_det")])

        if pcc["we"] == "1":
            fw = r["k"] if campo(pcc, "sel_fw") == "1" else r["i"]
            dato = {"000": lambda: a32, "001": lambda: leer(qa), "010": lambda: r["tmp"],
                    "011": lambda: r["coc"], "100": lambda: resultado & M32}[campo(pcc, "sel_data")]()
            ram_a[dir_ram(fw, r["j"])] = dato
            ram_b[dir_ram(fw, r["j"])] = dato
        if pcc["clr_banco"] == "1":
            banco = [0] * 8
        elif pcc["we_banco"] == "1":
            if campo(pcc, "sel_banco") == "1":
                banco[r["n"]] = nn
            else:
                banco[r["k"]] = r["piv"]
        r = nuevo
        st = sig
        if st == "s18":
            ciclos = ciclo + 1
            break
    else:
        raise RuntimeError("no llegó a s18")
    return sext(r["det"], 32), [sext(banco[k], 32) for k in range(1, r["n"] + 1)], ciclos


# ===========================================================================
# Modelo del CD del visualizador
# ===========================================================================
def simular_visualizador(valor):
    """Devuelve (dígitos decimales del display (10), neg, ciclos de una conversión)."""
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
            digitos = [(r["disp"] >> (4 * k)) & 0xF for k in range(10)]
            return digitos, r["disp_neg"], ciclo + 1
        st = sig
    raise RuntimeError("el XS3 no terminó")


# ===========================================================================
# Comprobacion completa
# ===========================================================================
def ciclos_ghdl():
    """{matriz: ciclos de la Corrida 1} leidos de sim/resultado_ghdl.txt."""
    import re
    texto = (RAIZ / "sim" / "resultado_ghdl.txt").read_text(encoding="utf-8")
    res = {}
    for bloque in re.split(r"== Matriz ", texto)[1:]:
        m = re.search(r"Corrida 1: final = 1 en (\d+) ciclos", bloque)
        if m:
            res[int(bloque.split()[0])] = int(m.group(1))
    return res


def comprobar(rapido=False, salida=print):
    from modelo_referencia import MATRICES, bareiss
    errores = []
    errores += verificar_filas(FILAS_P, CAMPOS_P, CAMPOS_COMB_P, ESTADOS_P)
    errores += verificar_filas(FILAS_V, CAMPOS_V, CAMPOS_COMB_V, ESTADOS_V)
    errores += comparar_con_asm(FILAS_P)
    errores += comparar_con_asm(FILAS_V)
    resultados = []
    ghdl = ciclos_ghdl()
    for num, a in enumerate(MATRICES):
        if rapido and num == 7:
            continue
        n = len(a)
        rom = [0] * 32
        rom[0] = n
        d = 1
        for j in range(n):
            for i in range(n):
                rom[d] = a[i][j] & 0x3F
                d += 1
        try:
            det, piv, ciclos = simular_procesador(rom, 30_000_000 if num == 7 else 100_000)
        except (RuntimeError, NoEscrito, KeyError) as ex:
            errores.append(f"matriz {num}: el modelo se detuvo: {ex}")
            continue
        det_ref, piv_ref, _ = bareiss(a)
        ok = det == det_ref and piv == piv_ref
        # el testbench de GHDL empieza a contar 2 ciclos después del flanco que ve inicio
        ok_ciclos = ghdl.get(num) is None or ghdl[num] == ciclos - 2
        if not ok:
            errores.append(f"matriz {num}: modelo det={det} piv={piv}; esperado {det_ref} {piv_ref}")
        if not ok_ciclos:
            errores.append(f"matriz {num}: {ciclos} ciclos en el modelo y {ghdl[num]} en GHDL")
        resultados.append((num, n, det, ciclos, ghdl.get(num), ok and ok_ciclos))
        salida(f"matriz {num}: det = {det}, pivotes = {piv}, {ciclos} ciclos "
               f"(GHDL: {ghdl.get(num)} + 2)  {'OK' if ok and ok_ciclos else 'ERROR'}")
    for v in (0, 7, 362, -170, 9999999, -17121828, 2147483647, -2147483647):
        digitos, neg, ciclos = simular_visualizador(v)
        texto = "".join(str(x) for x in reversed(digitos))
        ok = texto == str(abs(v)).zfill(10) and neg == (v < 0) and ciclos == 376
        if not ok:
            errores.append(f"XS3 {v}: {texto} neg={neg} ciclos={ciclos}")
        salida(f"XS3 {v:>12}: dec = {texto}, neg = {neg}, {ciclos} ciclos  {'OK' if ok else 'ERROR'}")
    return resultados, errores


if __name__ == "__main__":
    _, errores = comprobar(rapido="--rapido" in sys.argv)
    for e in errores:
        print("ERROR:", e)
    print(f"PC del procesador: {BITS_PC_P} bits; PC del visualizador: {BITS_PC_V} bits")
    for nombre, filas, campos, senales in (("procesador", FILAS_P, CAMPOS_P, SENALES_P),
                                           ("visualizador", FILAS_V, CAMPOS_V, SENALES_V)):
        o1, r1 = proyectar(filas, campos, senales, "sig")
        o2, r2 = proyectar(filas, campos, senales, "pc")
        print(f"{nombre}: entradas al estado siguiente {o1} ({len(r1)} filas); "
              f"entradas a la PC {o2} ({len(r2)} filas)")
    sys.exit(1 if errores else 0)

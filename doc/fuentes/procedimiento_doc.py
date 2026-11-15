"""Secciones del PDF con el procedimiento del curso (guía UC + CD):
del ASM al camino de datos, la palabra de control, la caja gris y la unidad de
control (dimensionamiento y contenido de las ROM), y lo que se espera ver en
la síntesis de ISE.

Las tablas se generan con doc/fuentes/uc_cd.py, que también simula el CD y la
UC propuestos y los compara con la simulación del VHDL.
"""
import re

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle

import uc_cd as U
from generar_pdf import AZUL, E, GRIS, P, RAIZ, fmt, tabla, viñetas

E["mini"] = ParagraphStyle("mini", fontName="DV", fontSize=6.7, leading=8.0)
E["mini_b"] = ParagraphStyle("mini_b", fontName="DV-B", fontSize=6.7, leading=8.0, textColor=colors.white)
E["mini_m"] = ParagraphStyle("mini_m", fontName="DVM", fontSize=6.7, leading=8.0)


def tabla_mini(filas, anchos, mono_desde=None):
    """Tabla de letra pequeña (para las ROM). Las columnas desde mono_desde van en monoespaciado."""
    datos = []
    for r, fila in enumerate(filas):
        celdas = []
        for c, v in enumerate(fila):
            est = "mini_b" if r == 0 else ("mini_m" if mono_desde is not None and c >= mono_desde else "mini")
            celdas.append(Paragraph(fmt(str(v)), E[est]))
        datos.append(celdas)
    t = Table(datos, colWidths=[w * inch for w in anchos], repeatRows=1)
    estilo = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#999999")),
              ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (-1, 0), AZUL),
              ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
              ("TOPPADDING", (0, 0), (-1, -1), 1.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2)]
    for r in range(2, len(filas), 2):
        estilo.append(("BACKGROUND", (0, r), (-1, r), GRIS))
    t.setStyle(TableStyle(estilo))
    return t


# ---------------------------------------------------------------------------
# Ayudas para leer las tablas de uc_cd
# ---------------------------------------------------------------------------
def codigos(campos, nombre):
    texto = next(c[4] for c in campos if c[0] == nombre)
    return {p.split(" = ", 1)[0].strip(): p.split(" = ", 1)[1].strip() for p in texto.split(" · ")}


def texto_cond(clave, senales):
    orden = [s for s, _, _ in senales]
    return ", ".join(f"{k}={clave[k]}" for k in sorted(clave, key=orden.index)) or "—"


def por_estado(filas_proy):
    res = {}
    for e, clave, valor in filas_proy:
        res.setdefault(e, []).append((clave, valor))
    return res


def usos(filas, campos, senales, ld, sel, fija):
    """'fuente: estados' de un registro, leído de la ROM de salida."""
    _, proy = U.proyectar(filas, campos, senales, "pc")
    grupos = por_estado(proy)
    cod = codigos(campos, sel) if sel else {}
    fuentes = {}
    for e, lista in grupos.items():
        valores = {(pc[ld], pc[sel] if sel else "") for _, pc in lista}
        for clave, pc in lista:
            if pc[ld] != "1":
                continue
            fuente = cod[pc[sel]] if sel else fija
            etiqueta = e if len(valores) == 1 else f"{e} ({texto_cond(clave, senales)})"
            fuentes.setdefault(fuente, [])
            if etiqueta not in fuentes[fuente]:
                fuentes[fuente].append(etiqueta)
    return " · ".join(f"[b]{f}[/b]: {', '.join(es)}" for f, es in fuentes.items())


def usos_campo(filas, campos, senales, nombre, solo_uno=False):
    """'valor: estados' de un campo de la PC (selectores de unidades y memorias)."""
    _, proy = U.proyectar(filas, campos, senales, "pc")
    grupos = por_estado(proy)
    cod = codigos(campos, nombre)
    fuentes = {}
    for e, lista in grupos.items():
        valores = {pc[nombre] for _, pc in lista}
        for clave, pc in lista:
            v = pc[nombre]
            if "X" in v or (solo_uno and v != "1"):
                continue
            etiqueta = e if len(valores) == 1 else f"{e} ({texto_cond(clave, senales)})"
            texto = cod.get(v, v)
            fuentes.setdefault(texto, [])
            if etiqueta not in fuentes[texto]:
                fuentes[texto].append(etiqueta)
    return " · ".join(f"[b]{f}[/b]: {', '.join(es)}" for f, es in fuentes.items())


def rom_entrada(filas, campos, senales, estados):
    orden, proy = U.proyectar(filas, campos, senales, "sig")
    cab = ["Q (actual)", "Estado"] + orden + ["D (siguiente)", "Siguiente"]
    out = [cab]
    for e, clave, sig in proy:
        out.append([U.codigo(estados, e), e] + [str(clave.get(s, "X")) for s in orden]
                   + [U.codigo(estados, sig), sig])
    n = len(U.codigo(estados, estados[0]))
    usados = len(estados)
    if usados < 2 ** n:
        out.append([f"{usados:0{n}b} a {2 ** n - 1:0{n}b}", "no usados"] + ["X"] * len(orden)
                   + [U.codigo(estados, estados[0]), f"{estados[0]} (vuelta segura)"])
    return orden, out


def rom_salida(filas, campos, senales, grupos_campos, finales):
    orden, proy = U.proyectar(filas, campos, senales, "pc")
    tablas = []
    for titulo, nombres, cortos in grupos_campos:
        cab = ["Estado", "Condiciones"] + cortos + (["final"] if finales is not None and nombres is grupos_campos[-1][1] else [])
        out = [cab]
        for e, clave, pc in proy:
            fila = [e, texto_cond(clave, senales)] + [pc[nm] for nm in nombres]
            if finales is not None and nombres is grupos_campos[-1][1]:
                fila.append("1" if e in finales else "0")
            out.append(fila)
        tablas.append((titulo, out))
    return orden, len(proy), tablas


# ---------------------------------------------------------------------------
# Datos para las secciones
# ---------------------------------------------------------------------------
GRUPOS_P = [
    ("Cargas de los registros (ld_x)", [c[0] for c in U.CAMPOS_P if c[2] == "ld"],
     ["dira", "n", "i", "j", "k", "piv", "p", "aik", "tmp", "sg", "det", "ma", "mb", "sra", "srb", "op",
      "coc", "sq"]),
    ("Selectores de los MUX de los registros (sel_x)", [c[0] for c in U.CAMPOS_P if c[2] == "sel"],
     ["dira", "i", "j", "k", "p", "sg", "det", "ma", "mb", "sra", "srb", "op", "coc"]),
    ("RAM y banco de pivotes", [c[0] for c in U.CAMPOS_P if c[2] in ("ram", "banco")],
     ["we", "sel_w", "sel_data", "we_banco"]),
]
GRUPOS_V = [("Palabra de control del visualizador", [c[0] for c in U.CAMPOS_V],
             ["ld bin", "ld neg", "ld dec", "ld cont", "ld d", "ld disp", "sel bin", "sel dec", "sel cont", "sel d"])]

TRANSFERENCIAS = [
    ("s0", "n ← a; dira ← 1; i ← 1; j ← 1 (si inicio = 1)", "", "", "lee ROM(00h)"),
    ("s1", "RAM(i,j) ← a; dira ← dira + 1; i ← i + 1, o i ← 1 y j ← j + 1; al final k ← 1, j ← 1, p ← 1, "
           "signo ← 0", "", "", "escribe (i,j)"),
    ("s2", "piv ← qb; i ← k + 1; banco(k) ← qb (si qb ≠ 0)", "", "", "lee B(k,k)"),
    ("s3", "signo ← not signo (qa ≠ 0); det ← 0 (qa = 0, i = n); i ← i + 1 (qa = 0, i ≠ n)", "", "",
     "lee A(i,k)"),
    ("s4", "RAM(i,j) ← qb; tmp ← qa", "", "", "lee A(i,j) y B(k,j); escribe (i,j)"),
    ("s5", "RAM(k,j) ← tmp; j ← k o j ← j + 1", "", "", "escribe (k,j)"),
    ("s6", "aik ← qa; j ← k + 1", "", "", "lee A(i,k)"),
    ("s7", "mul_a ← piv; mul_b ← qa", "", "", "lee A(i,j)"),
    ("s8", "sr_a ← producto; mul_a ← aik; mul_b ← qb", "piv · a(i,j)", "", "lee B(k,j)"),
    ("s9", "sr_b ← producto; op ← 1", "a(i,k) · a(k,j)", "", ""),
    ("s10", "sr_a ← resultado; sr_b ← p; sq; op; cociente ← 0", "", "t1 − t2", ""),
    ("s11", "sr_a ← resultado y cociente ← cociente + 1 (residuo ≠ 0); sr_b ← cociente y op ← 1 (residuo = 0)",
     "", "residuo ∓ p", ""),
    ("s12", "RAM(i,j) ← ±cociente; avanza j, i o k; en el último paso det ← ±cociente", "", "0 − cociente",
     "escribe (i,j)"),
    ("s13", "final = 1; dira ← 1, i ← 1, j ← 1 (si inicio = 1)", "", "", ""),
]


def resultados_modelo():
    texto = (RAIZ / "sim" / "resultado_modelo_uc_cd.txt").read_text(encoding="utf-8")
    filas = []
    for m in re.finditer(r"matriz (\d+): det = (-?\d+), pivotes = \[([^\]]*)\], (\d+) ciclos \(GHDL: (\d+) \+ 2\)\s+(\w+)",
                         texto):
        filas.append(m.groups())
    xs3 = re.findall(r"XS3\s+(-?\d+): dec = (\d+), neg = (\d), (\d+) ciclos\s+(\w+)", texto)
    return filas, xs3


# ===========================================================================
# 9. Procesador de Bareiss
# ===========================================================================
def seccion_procesador(h, fig):
    A, V = h.append, h.extend
    A(PageBreak())
    A(P("9. Del ASM al hardware: procesador de Bareiss", "h1"))
    A(P("Esta sección sigue la metodología de la guía del curso para pasar del ASM al camino de datos (CD) y a la "
        "unidad de control (UC). El VHDL es de alto nivel, como en los ejemplos ASM_Sumax y ASM_contador_unos: un solo "
        "process con [c]case st is[/c], y la herramienta de síntesis construye el CD y la UC a partir de él. Aquí se "
        "deduce, desde el ASM, qué hardware debe aparecer; la sección 11 dice dónde comprobarlo en ISE."))
    A(tabla([
        ["Paso de la guía", "Dónde está"],
        ["1. Caja negra", "Sección 4.1"],
        ["2. Pseudoalgoritmo", "Sección 3"],
        ["3. Diagrama ASM respetando los recursos (1 multiplicador, 1 sumador/restador)", "Sección 6 y tabla 9.2"],
        ["4. Tiempos de vida y registros", "Secciones 9.3 y 9.12"],
        ["5. Camino de datos: registros, unidades, MUX, comparadores", "Secciones 9.4 a 9.7"],
        ["6. Palabra de control", "Sección 9.8"],
        ["7. Caja gris con los anchos de bus", "Sección 9.9"],
        ["8. Unidad de control: tamaño y contenido de la ROM de entrada y de la ROM de salida", "Sección 9.10"],
    ], [4.9, 2.0]))

    # 9.1 Puertos y señales --------------------------------------------------
    A(P("9.1 Puertos, señales de estado, señales de control y señales internas", "h2"))
    A(P("El enunciado pide identificar estos grupos de señales para el CD y para la UC:"))
    A(tabla([
        ["Grupo", "Señales"],
        ["Puertos de entrada", "clk, rst, inicio (a la UC); dir_p (3, al CD)"],
        ["Puertos de salida", "final (de la UC); det (32) y pivote (32) (del CD)"],
        ["Señales de estado (CD → UC)", "z_b, z_a, i_n, j_n, k1_n, z_res, sqs (7 bits)"],
        ["Señales de control (UC → CD)", f"Palabra de control de {U.BITS_PC_P} bits (sección 9.8)"],
        ["Señales internas de la UC", "st (estado presente, 4 bits) y el estado siguiente"],
        ["Señales internas del CD",
         "18 registros y el banco b1 a b4 (sección 9.3); a (ROM); qa, qb, dir_ij, dir_kj, wr_add, data, we (RAM); "
         "producto y resultado (unidades); las salidas de los incrementadores (+1)"],
    ], [2.0, 4.9]))

    # 9.2 Transferencias ------------------------------------------------------
    A(P("9.2 Transferencias por estado y uso de las unidades", "h2"))
    A(P("Cada estado del ASM se escribe como transferencias entre registros. La tabla confirma la restricción de "
        "recursos: en ningún estado se usa más de una vez el multiplicador ni el sumador/restador. Las dos unidades "
        "toman sus entradas de registros (mul_a, mul_b, sr_a, sr_b, op): un estado carga las entradas y el siguiente "
        "guarda el resultado."))
    A(tabla([["Estado", "Transferencias", "Multiplicador", "Sumador/ restador", "RAM"]]
            + [list(t) for t in TRANSFERENCIAS], [0.6, 3.0, 1.05, 1.05, 1.2]))

    # 9.3 Registros --------------------------------------------------------
    A(P("9.3 Registros y sus multiplexores de entrada", "h2"))
    A(P("Regla de la guía: cada registro con más de una fuente lleva un MUX y cada registro tiene una señal de carga "
        "(ld). Un VHDL de alto nivel produce un registro por señal asignada en el process del ASM. La columna "
        "«Fuentes» se lee de la ROM de salida (sección 9.10): para cada valor del MUX se indican los estados que lo "
        "usan, y entre paréntesis la condición cuando el estado tiene varios caminos."))
    filas = [["Registro", "Bits", "Carga", "MUX", "Fuentes (estados en que se carga)"]]
    total = 0
    for nombre, bits, ld, sel, fija, uso in U.REGISTROS_P:
        total += bits
        mux = "—" if sel is None else f"{len(codigos(U.CAMPOS_P, sel))}:1, {sel} ({next(c[1] for c in U.CAMPOS_P if c[0] == sel)} b)"
        filas.append([f"{nombre}[br][i]{uso}[/i]", str(bits), ld, mux, usos(U.FILAS_P, U.CAMPOS_P, U.SENALES_P, ld, sel, fija)])
    filas.append(["b1 a b4[br][i]Banco de pivotes[/i]", "4 × 32", "we_banco", "—",
                  "[b]qb[/b]: s2 (z_b=0), en el registro que indica k"])
    A(tabla(filas, [1.25, 0.5, 0.6, 1.2, 3.35]))
    A(Spacer(1, 4))
    A(P(f"Total: {len(U.REGISTROS_P)} registros y {total} bits, más el banco (128 bits) y los 4 bits del registro de "
        "estado. sr_a y sr_b se reutilizan: sr_a guarda t1 y después el residuo; sr_b guarda t2, después p y al final "
        "el cociente que se va a negar (sección 9.12)."))
    A(P("Los anchos salen de la desigualdad de Hadamard: cada valor de la RAM es el determinante de una submatriz de "
        "A (identidad de Sylvester) y |det| ≤ (32·√m)[sup]m[/sup] para una submatriz m×m."))
    V(viñetas([
        "Operandos del multiplicador: submatrices de hasta 4×4, |x| < 2[sup]24[/sup]. Caben en 25 bits con signo.",
        "Determinante 5×5: |det| ≤ 1,88 × 10[sup]9[/sup] < 2[sup]31[/sup]. RAM, piv, p, det y cociente son de 32 bits.",
        "Numerador: |t1 − t2| ≤ 3,2 × 10[sup]14[/sup] < 2[sup]49[/sup]. sr_a, sr_b y el sumador/restador son de 50 bits.",
    ]))

    # 9.4 Unidades y memorias -------------------------------------------------
    A(P("9.4 Unidades funcionales, memorias y fuentes de sus entradas", "h2"))
    A(tabla([
        ["Bloque", "Entrada", "Fuente (estados)"],
        ["Multiplicador 25 × 25 → 50", "a, b", "Registros mul_a y mul_b (cable directo)"],
        ["Sumador/restador 50 bits", "A, B, op", "Registros sr_a, sr_b y op (cable directo)"],
        ["ROM 32 × 6", "dira", "Registro dira (cable directo)"],
        ["RAM A (32 × 32)", "dirección de lectura", "dir_ij: siempre lee a(i,j) → qa"],
        ["RAM B (32 × 32)", "dirección de lectura", "dir_kj: siempre lee a(k,j) → qb"],
        ["RAM A y RAM B", "we = 1", usos_campo(U.FILAS_P, U.CAMPOS_P, U.SENALES_P, "we", True)],
        ["", "dirección de escritura (sel_w)", usos_campo(U.FILAS_P, U.CAMPOS_P, U.SENALES_P, "sel_w")],
        ["", "data (sel_data)", usos_campo(U.FILAS_P, U.CAMPOS_P, U.SENALES_P, "sel_data")],
        ["Banco de pivotes b1 a b4", "we_banco = 1", usos_campo(U.FILAS_P, U.CAMPOS_P, U.SENALES_P, "we_banco", True)],
        ["", "lectura", "dir_p (switches): b1 a b4, o det si dir_p = n"],
    ], [1.55, 1.75, 3.6]))
    A(Spacer(1, 4))
    A(P("La dirección de a(f,c) en la RAM es f & c(1 downto 0) para las columnas 1 a 4 y \"11\" & f para la columna "
        "5, así que no hace falta multiplicar ni sumar para ubicar un elemento. Para leer a(k,k) se pone j = k y se "
        "lee la RAM B; para leer a(i,k), j = k y la RAM A."))

    # 9.5 Señales de estado ---------------------------------------------------
    A(P("9.5 Señales de estado (comparadores)", "h2"))
    A(P("Cada caja de decisión del ASM que pregunta por datos se convierte en un comparador del CD y en una señal de "
        "estado de 1 bit hacia la UC. inicio es una entrada externa de la UC."))
    A(tabla([["Señal", "Pregunta del ASM", "Bloque que la genera", "Estados"]] + [
        [s_, q, b, e] for (s_, q, b), e in zip(U.SENALES_P, [
            "s0, s13", "s2", "s3", "s1, s3, s12", "s1, s5, s12", "s12", "s11", "s12"])],
        [0.75, 1.4, 3.6, 1.15]))

    # 9.6 / 9.7 Camino de datos ----------------------------------------------
    A(P("9.6 Camino de datos", "h2"))
    A(P("El CD se dibuja en cuatro partes para que se lean todas las conexiones. En rojo están las señales de control "
        "(cargas ld_x y selectores sel_x) y las señales de estado que van a la UC. Los nombres de las entradas de cada "
        "MUX son las fuentes de la sección 9.3."))
    A(fig("cd_indices", "CD, parte 1: contadores dira, n, i, j y k con sus MUX y comparadores.", max_alto=2.4))
    A(fig("cd_direcciones", "CD, parte 2: direcciones de lectura y escritura de las RAM.", max_alto=2.2, max_ancho=5.0))
    A(fig("cd_memorias", "CD, parte 3: ROM, RAM A, RAM B, registros piv, tmp, aik y det, y banco de pivotes.",
          max_alto=5.0))
    A(fig("cd_aritmetica", "CD, parte 4: multiplicador, sumador/restador, división y signos.", max_alto=5.4))
    A(P("9.7 Vista general del camino de datos", "h2"))
    A(fig("camino_datos_proc", "Vista general del camino de datos del procesador.", max_alto=7.6))

    # 9.8 Palabra de control --------------------------------------------------
    A(PageBreak())
    A(P("9.8 Palabra de control", "h2"))
    A(P(f"La palabra de control reúne todas las entradas de control del CD: {U.BITS_PC_P} bits. El orden de la tabla "
        "es el orden de los bits en la ROM de salida, y después va final (1 bit), que es una salida de la UC."))
    A(tabla([["Campo", "Bits", "Controla", "Códigos"]] + [[n_, str(b), q, c] for n_, b, _, q, c in U.CAMPOS_P],
            [0.85, 0.4, 2.0, 3.65]))
    A(Spacer(1, 4))
    A(P("Regla de la guía: las cargas y escrituras (ld_x, we, we_banco) nunca son X: si un registro no debe cambiar, "
        "su carga vale 0. Los selectores que no se usan en un estado sí son X. El MUX que elige entre +cociente y "
        "−cociente para escribir en la RAM lo controla el registro sq dentro del CD, no la UC."))

    # 9.9 Caja gris -----------------------------------------------------------
    A(P("9.9 Caja gris", "h2"))
    A(fig("gris_proc", f"Caja gris del procesador: PC de {U.BITS_PC_P} bits y 7 señales de estado.", max_alto=2.6))

    # 9.10 Unidad de control ----------------------------------------------------
    A(PageBreak())
    A(P("9.10 Unidad de control", "h2"))
    o_sig, rows_sig = rom_entrada(U.FILAS_P, U.CAMPOS_P, U.SENALES_P, U.ESTADOS_P)
    o_pc, n_pc, tablas_pc = rom_salida(U.FILAS_P, U.CAMPOS_P, U.SENALES_P, GRUPOS_P, U.FINAL_P)
    A(P("El ASM tiene cajas de salida condicional (por ejemplo «banco(k) ← a(k,k)» si a(k,k) ≠ 0 en s2), así que la "
        "UC es de tipo Mealy, como el ejemplo «ASM Mealy» del contador de unos: la palabra de control depende del "
        "estado y de algunas señales de estado. Para dimensionar las ROM se separan las señales que cambian el estado "
        "siguiente de las que cambian la palabra de control:"))
    A(tabla([
        ["Elemento", "Cálculo", "Tamaño"],
        ["Estados", "s0 a s13", "E = 14"],
        ["Registro de estado", "n = ⌈log₂ 14⌉", "4 flip-flops D"],
        ["Entradas al estado siguiente", ", ".join(o_sig), f"c = {len(o_sig)}"],
        ["ROM de entrada", f"2^(n + c) × n = 2^(4 + {len(o_sig)}) × 4", f"{2 ** (4 + len(o_sig))} × 4"],
        ["Condiciones que cambian la PC", ", ".join(o_pc), f"c' = {len(o_pc)}"],
        ["ROM de salida (Mealy)", f"2^(n + c') × (k + f) = 2^(4 + {len(o_pc)}) × ({U.BITS_PC_P} + 1)",
         f"{2 ** (4 + len(o_pc))} × {U.BITS_PC_P + 1}"],
    ], [1.9, 3.2, 1.8]))
    A(Spacer(1, 4))
    A(P("sqs (sq ⊕ signo) solo elige si el determinante es cociente o 0 − cociente en el último paso, así que solo "
        "entra a la ROM de salida, como α en la versión Mealy del contador de unos. Las demás señales cambian el "
        "estado siguiente y también la palabra de control."))
    A(fig("uc_proc", "Unidad de control canónica del procesador (ROM de entrada, registro, ROM de salida).",
          max_alto=2.3))
    A(P("Códigos de estado: el orden de la declaración [c]type estados_asm is (s0, s1, …, s13)[/c], en binario: "
        "s0 = 0000, s1 = 0001, …, s13 = 1101. La síntesis puede cambiar la codificación (sección 11)."))
    A(P("ROM de entrada (tabla de transiciones)", "h2"))
    A(P(f"Una fila por combinación que importa; X = no importa. Las {2 ** (4 + len(o_sig))} posiciones de la ROM "
        "salen de repetir cada fila para todos los valores de las X. Los códigos no usados vuelven a s0."))
    A(tabla_mini(rows_sig, [0.8, 0.55] + [0.52] * len(o_sig) + [0.8, 1.1]))
    A(PageBreak())
    A(P("ROM de salida (palabras de control)", "h2"))
    A(P(f"{n_pc} filas: una por estado y combinación de las condiciones que cambian la PC. Se muestra en tres tablas "
        "por grupos de campos (los nombres son los de la sección 9.8 sin el prefijo). En la ROM, X se puede llenar "
        "con 0."))
    for titulo, filas in tablas_pc:
        ncol = len(filas[0]) - 2
        ancho = (6.9 - 0.48 - 1.6) / ncol
        A(KeepTogether([P(titulo, "h2_anexo"), tabla_mini(filas, [0.48, 1.6] + [ancho] * ncol, mono_desde=2)]))
        A(Spacer(1, 6))

    # 9.11 Comprobacion -------------------------------------------------------
    A(PageBreak())
    A(P("9.11 Comprobación de la UC y el CD propuestos", "h2"))
    A(P("El programa doc/fuentes/uc_cd.py simula ciclo a ciclo el CD de esta sección manejado por las dos ROM "
        "(transiciones y palabras de control), sin usar el VHDL. Comprueba además que cada estado cumple la regla 1 "
        "del ASM (cada combinación de condiciones tiene una sola fila) y que los estados siguientes coinciden con los "
        "diagramas ASM. Resultados (sim/resultado_modelo_uc_cd.txt):"))
    filas_m, xs3 = resultados_modelo()
    A(tabla([["Matriz", "det", "Pivotes", "Ciclos del modelo", "Ciclos GHDL + 2", "Resultado"]]
            + [[m, d, p_, c, str(int(g) + 2), r] for m, d, p_, c, g, r in filas_m],
            [0.55, 0.95, 2.45, 1.05, 1.05, 0.85]))
    A(Spacer(1, 4))
    A(P("Los resultados y el número de ciclos son iguales a los de la simulación del VHDL en todas las matrices (el "
        "testbench de GHDL empieza a contar 2 ciclos después). Por eso el CD y la UC de esta sección describen el "
        "mismo hardware que el VHDL. Como las direcciones de lectura de las RAM son fijas (a(i,j) y a(k,j)) y las "
        "unidades toman sus entradas de registros, ninguna señal de estado depende de la palabra de control del "
        "mismo ciclo: no hay lazos combinacionales UC → CD → UC."))

    # 9.12 Tiempos de vida --------------------------------------------------
    A(P("9.12 Tiempos de vida en el lazo interno", "h2"))
    A(P("La guía minimiza registros con la tabla de tiempos de vida y el algoritmo left-edge. Para las variables "
        "temporales del lazo s7 a s12 (i, j, k, piv, p y aik están vivas en todo el lazo):"))
    vida = {"t1": (9, 10), "t2": (10, 10), "residuo": (11, 12), "p (copia)": (11, 11), "−cociente": (12, 12),
            "mul_a": (8, 9), "mul_b": (8, 9), "cociente": (11, 12), "sq": (11, 12)}
    escrita = {"t1": "s8", "t2": "s9", "residuo": "s10, s11", "p (copia)": "s10", "−cociente": "s11",
               "mul_a": "s7, s8", "mul_b": "s7, s8", "cociente": "s10, s11", "sq": "s10"}
    leida = {"t1": "s10", "t2": "s10", "residuo": "s11, s12", "p (copia)": "s11", "−cociente": "s12",
             "mul_a": "s8, s9", "mul_b": "s8, s9", "cociente": "s11, s12", "sq": "s12"}
    reg = {"t1": "sr_a", "t2": "sr_b", "residuo": "sr_a", "p (copia)": "sr_b", "−cociente": "sr_b",
           "mul_a": "mul_a", "mul_b": "mul_b", "cociente": "cociente", "sq": "sq"}
    est = list(range(7, 13))
    filas = [["Variable", "Registro", "Se escribe", "Se lee"] + [f"s{e}" for e in est]]
    for v, (a_, b_) in vida.items():
        filas.append([v, reg[v], escrita[v], leida[v]] + ["X" if a_ <= e <= b_ else "" for e in est])
    filas.append(["Vivas", "", "", ""] + [str(sum(1 for a_, b_ in vida.values() if a_ <= e <= b_)) for e in est])
    A(tabla(filas, [0.85, 0.75, 0.85, 0.85] + [0.6] * len(est)))
    A(Spacer(1, 4))
    A(P("El diseño ya aplica la compartición en las entradas del sumador/restador: t1 y el residuo usan sr_a (sus "
        "vidas no se cruzan), y t2, la copia de p y el cociente que se niega usan sr_b. El máximo de variables vivas "
        "es 4 (en s11 y s12). mul_a y mul_b podrían compartir registro con cociente y sq, pero tienen otro ancho "
        "(25 bits contra 32 y 1) y el VHDL quedaría menos claro; con la FPGA usada por debajo del 1 % no hace falta."))


# ===========================================================================
# 10. Visualizador
# ===========================================================================
def seccion_visualizador(h, fig):
    A, V = h.append, h.extend
    A(PageBreak())
    A(P("10. Del ASM al hardware: visualizador (XS3)", "h1"))
    A(P("El mismo procedimiento aplicado al ASM del XS3. Este ASM no tiene salida final; su resultado es lo que "
        "muestra el display."))
    A(P("10.1 Señales", "h2"))
    A(tabla([
        ["Grupo", "Señales"],
        ["Entradas", "clk, rst, final (a la UC); tick, dir_p, det, pivote (al CD)"],
        ["Salidas", "an (8), seg (7), dp, desborde (del CD)"],
        ["Señales de estado (CD → UC)", "val_neg, cont_31, dig_4, d_9 (4 bits)"],
        ["Señales de control (UC → CD)", f"Palabra de control de {U.BITS_PC_V} bits"],
        ["Señales internas", "xs (estado, 3 bits); registros de la tabla 10.2; val, 0 − val, dígito(d), dígito + 3, dsel"],
    ], [2.0, 4.9]))
    A(tabla([["Señal", "Pregunta del ASM", "Bloque que la genera"]] + [list(s) for s in U.SENALES_V], [0.9, 1.7, 4.3]))
    A(P("10.2 Registros", "h2"))
    filas = [["Registro", "Bits", "Carga", "MUX", "Fuentes (estados en que se carga)"]]
    for nombre, bits, ld, sel, fija, uso in U.REGISTROS_V:
        mux = "—" if sel is None else f"{len(codigos(U.CAMPOS_V, sel))}:1, {sel}"
        filas.append([f"{nombre}[br][i]{uso}[/i]", str(bits), ld, mux, usos(U.FILAS_V, U.CAMPOS_V, U.SENALES_V, ld, sel, fija)])
    filas.append(["dsel[br][i]Dígito encendido[/i]", "3", "tick", "—", "Contador que avanza con cada tick de 1 ms (no lo maneja el ASM)"])
    A(tabla(filas, [1.35, 0.42, 0.6, 0.9, 3.63]))
    A(Spacer(1, 4))
    A(P("En x3 solo cambia el dígito d del registro dec: un decodificador de d habilita la carga de esos 4 bits. Las "
        "unidades propias del visualizador son el restador 0 − val (32 bits), el sumador +3 (4 bits), los "
        "incrementadores de cont, d y dsel, y los comparadores > 4, = 31, = 9 y «dígitos 7 a 9 ≠ 0» (desborde)."))
    A(fig("cd_vis", "Camino de datos del visualizador.", max_alto=6.3))
    A(P("10.3 Palabra de control y caja gris", "h2"))
    A(tabla([["Campo", "Bits", "Controla", "Códigos"]] + [[n, str(b), q, c] for n, b, _, q, c in U.CAMPOS_V],
            [0.85, 0.4, 2.0, 3.65]))
    A(fig("gris_vis", f"Caja gris del visualizador: PC de {U.BITS_PC_V} bits y 4 señales de estado.", max_alto=2.4))
    A(P("10.4 Unidad de control", "h2"))
    o_sig, rows_sig = rom_entrada(U.FILAS_V, U.CAMPOS_V, U.SENALES_V, U.ESTADOS_V)
    o_pc, n_pc, tablas_pc = rom_salida(U.FILAS_V, U.CAMPOS_V, U.SENALES_V, GRUPOS_V, None)
    A(tabla([
        ["Elemento", "Cálculo", "Tamaño"],
        ["Estados", "x0 a x5", "E = 6"],
        ["Registro de estado", "n = ⌈log₂ 6⌉", "3 flip-flops D"],
        ["Entradas al estado siguiente", ", ".join(o_sig), f"c = {len(o_sig)}"],
        ["ROM de entrada", f"2^(3 + {len(o_sig)}) × 3", f"{2 ** (3 + len(o_sig))} × 3"],
        ["Condiciones que cambian la PC", ", ".join(o_pc), f"c' = {len(o_pc)}"],
        ["ROM de salida (Mealy)", f"2^(3 + {len(o_pc)}) × {U.BITS_PC_V}", f"{2 ** (3 + len(o_pc))} × {U.BITS_PC_V}"],
    ], [1.9, 3.2, 1.8]))
    A(fig("uc_vis", "Unidad de control canónica del visualizador.", max_alto=2.2))
    A(P("Códigos de estado: x0 = 000, x1 = 001, …, x5 = 101 (orden del type)."))
    A(KeepTogether([P("ROM de entrada", "h2_anexo"),
                    tabla_mini(rows_sig, [1.0, 0.7] + [0.7] * len(o_sig) + [1.0, 1.3])]))
    A(Spacer(1, 6))
    for titulo, filas in tablas_pc:
        ncol = len(filas[0]) - 2
        A(KeepTogether([P("ROM de salida", "h2_anexo"),
                        tabla_mini(filas, [0.45, 1.65] + [(6.9 - 2.1) / ncol] * ncol, mono_desde=2)]))
    A(Spacer(1, 4))
    _, xs3 = resultados_modelo()
    A(P("El modelo de uc_cd.py con estas tablas convierte " + ", ".join(v for v, *_ in xs3) +
        " con el resultado correcto y en 376 ciclos por conversión, igual que el VHDL: x0 y x1 (2 ciclos), 32 pasadas "
        "por x2, 31 × (10 ciclos en x3 + 1 en x4) y x5."))


# ===========================================================================
# 11. Lo que se espera de la síntesis en ISE
# ===========================================================================
REG_BLOQUES = [
    ("procesador_bareiss: registros de la tabla 9.3 y banco b1 a b4", "490", "490", ""),
    ("procesador_bareiss: registro de estado st", "4", "4 a 14", "14 si XST elige one-hot"),
    ("visualizador (bin, neg, dec, cont, d, disp, disp_neg, dsel)", "126", "126", ""),
    ("visualizador: registro de estado xs", "3", "3 a 6", "6 si XST elige one-hot"),
    ("antirrebote (b1, b2, muestras, estable, estable_ant)", "12", "12", ""),
    ("divisor_frecuencia (cuenta_ciclos, cuenta_ms, onda)", "27", "27", ""),
    ("Total", "662", "662 a 675", "Yosys dio 668"),
]


def seccion_sintesis(h, fig):
    A, V = h.append, h.extend
    A(PageBreak())
    A(P("11. Lo que se espera de la síntesis en ISE", "h1"))
    A(P("Como en el informe del Taller 6, la síntesis sirve para comprobar que el VHDL de alto nivel se convirtió en "
        "el hardware esperado: una FSM por ASM (la UC) y un CD con registros, MUX, unidades funcionales y memorias. "
        "Esta sección dice qué buscar y qué valores esperar. No se ejecutó ISE: los números de recursos son una "
        "estimación con otra herramienta (Yosys) y ISE dará valores parecidos, no iguales."))
    A(P("11.1 Dónde mirar", "h2"))
    V(viñetas([
        "[b]View RTL Schematic[/b]: el tope det_bareiss con sus 4 bloques (U_FREC, U_ANTI, U_PROC, U_VIS). Dentro de "
        "U_PROC aparecen U_ROM, U_RAM_A y U_RAM_B, y la lógica del ASM: la FSM, los registros, el multiplicador, el "
        "sumador/restador, los comparadores y los MUX. El esquemático no va a ser tan pequeño como el de ASM_Sumax: el "
        "algoritmo maneja una matriz de 5 × 5, una división y un banco de pivotes.",
        "[b]Synthesis Report → HDL Synthesis[/b]: una línea por macro inferida («Found 32-bit register for signal "
        "<piv>», «Found 25x25-bit multiplier», «Found finite state machine <FSM_0> for signal <st>»…). Al final, "
        "«Macro Statistics».",
        "[b]Advanced HDL Synthesis[/b]: la codificación que XST eligió para cada FSM y la implementación de las RAM "
        "(con lectura asíncrona, XST las pone en LUT como RAM distribuida) y del multiplicador (DSP48E1).",
        "[b]Design Summary[/b] (después de Implement Design): uso de slices, LUT, flip-flops, DSP48E1, IOB. "
        "[b]Timing Report[/b]: periodo mínimo y camino crítico.",
    ]))
    A(P("11.2 Máquinas de estado esperadas", "h2"))
    A(tabla([
        ["Dato del reporte", "FSM del procesador (st)", "FSM del visualizador (xs)"],
        ["States", "14 (s0 a s13)", "6 (x0 a x5)"],
        ["Transitions", "25 flechas en el diagrama de estados (XST puede contarlas distinto)", "9"],
        ["Inputs", "7: inicio, qb = 0, qa = 0, i = n, j = n, k + 1 = n, sr_a = 0", "3: final, cont = 31, d = 9"],
        ["Clock / Reset", "clk (flanco de subida) / rst (alto, asíncrono)", "igual"],
        ["Reset State", "s0", "x0"],
        ["Encoding", "auto: XST elige (one-hot, Gray o binario)", "auto"],
        ["Flip-flops", "4 en binario, 14 en one-hot", "3 en binario, 6 en one-hot"],
    ], [1.5, 3.2, 2.2]))
    A(Spacer(1, 4))
    A(P("Declarar los estados con [c]type estados_asm[/c], como en los ejemplos del curso, es lo que permite a XST "
        "reconocer la FSM y mostrarla como un bloque aparte en el esquemático. Las entradas de la FSM son las 7 señales "
        "que cambian el estado siguiente (sección 9.10)."))
    A(P("11.3 Macros del camino de datos esperadas", "h2"))
    A(tabla([
        ["Macro", "Procesador", "Visualizador y demás"],
        ["RAMs", "2 × 32x32-bit dual-port, escritura síncrona y lectura asíncrona → RAM distribuida (LUT)", "—"],
        ["ROMs", "rom_matriz 32x6", "Decodificador de 7 segmentos y de ánodos"],
        ["Multipliers", "1 × 25x25-bit con signo (producto) → 2 DSP48E1 (el DSP48E1 multiplica 25 × 18)", "—"],
        ["Adders/Subtractors", "resultado: sumador/restador de 50 bits (XST puede listarlo como un addsub o como un "
                               "sumador y un restador con un MUX); incrementadores dira + 1 (5), i + 1, j + 1, "
                               "k + 1 (3), cociente + 1 (32)",
         "visualizador: 0 − val (32), dígito + 3 (4), cont + 1 (5), d + 1 (4), dsel + 1 (3); divisor: 17 y 9 bits"],
        ["Comparators", "qa = 0, qb = 0 (32 bits), sr_a = 0 (50 bits), i = n, j = n, k + 1 = n, dir_p = n (3 bits)",
         "dígito > 4, cont = 31, d = 9, desborde (12 bits = 0); divisor y antirrebote"],
        ["Registers", "Tabla siguiente", "Tabla siguiente"],
        ["Multiplexers", "Los MUX de las secciones 9.3 y 9.4 (XST los suele absorber en LUT)", "Los de la sección 10.2"],
        ["FSMs", "1", "1"],
    ], [1.25, 3.25, 2.4]))
    A(Spacer(1, 4))
    A(tabla([["Bloque", "Bits en el VHDL", "Flip-flops esperados", "Nota"]] + [list(r) for r in REG_BLOQUES],
            [3.0, 1.0, 1.2, 1.7]))
    A(P("11.4 Recursos estimados", "h2"))
    A(P("Estimación con Yosys 0.71 (synth_xilinx para la familia 7 de Xilinx) sobre la netlist que produce GHDL "
        "(sim/estimacion_yosys.txt). Capacidad del XC7A100T-1CSG324C según la hoja de datos de Artix-7:"))
    A(tabla([
        ["Recurso", "Estimado", "Disponible", "Uso"],
        ["Flip-flops (slice registers)", "668", "126 800", "0,5 %"],
        ["LUT de lógica", "≈ 830 a 880", "63 400", "≈ 1,4 %"],
        ["LUT como memoria (RAM distribuida)", "48 (12 RAM32M: 6 por RAM)", "19 000", "0,3 %"],
        ["DSP48E1", "2 (multiplicador 25 × 25)", "240", "0,8 %"],
        ["IOB", "25 (6 entradas, 19 salidas)", "210", "11,9 %"],
        ["BUFG", "1", "32", "3 %"],
    ], [2.2, 2.2, 1.2, 1.3]))
    A(Spacer(1, 4))
    A(P("Por bloque (Yosys): procesador_bareiss ≈ 650 LUT y 497 flip-flops, más 2 DSP48E1; cada RAM 6 RAM32M; "
        "visualizador ≈ 220 LUT y 132 flip-flops. Comparado con la versión anterior del procesador (19 estados y 8 "
        "entidades), el diseño completo bajó de 1 022 a 877 LUT y de 780 a 668 flip-flops."))
    A(P("11.5 Tiempos", "h2"))
    A(P("El reloj es de 100 MHz (TIMESPEC de 10 ns en el .ucf). Caminos candidatos a ser el crítico:"))
    V(viñetas([
        "mul_a, mul_b → multiplicador (2 DSP48E1 en cascada, sin registros internos) → sr_a o sr_b.",
        "sr_a, sr_b, op → sumador/restador de 50 bits → sr_a (lazo de la división en s11).",
        "i, j, k → dir_ij o dir_kj → RAM (lectura asíncrona) → qa = 0 o qb = 0 → UC.",
    ]))
    A(P("El periodo mínimo que da XST después de la síntesis es una estimación; el valor que cuenta es el del reporte "
        "de tiempos después de Implement Design. Si no se cumplen los 10 ns, la solución sin cambiar el ASM es bajar el "
        "reloj: generar 50 MHz con el Clocking Wizard y poner PERIOD = 20 ns."))
    A(P("11.6 Tabla para el informe", "h2"))
    A(P("Llenen la última columna con los valores de ISE y comenten las diferencias:"))
    A(tabla([
        ["Parámetro", "Esperado", "Obtenido en ISE"],
        ["FSM del procesador: estados / entradas / flip-flops", "14 / 7 / 4 a 14", ""],
        ["FSM del visualizador: estados / entradas / flip-flops", "6 / 3 / 3 a 6", ""],
        ["RAM 32x32 dual-port en LUT", "2", ""],
        ["Multiplicador 25x25 / DSP48E1", "1 / 2", ""],
        ["Sumador/restador de 50 bits en el procesador", "1 (o un sumador y un restador)", ""],
        ["Flip-flops", "662 a 675", ""],
        ["LUT", "≈ 900", ""],
        ["IOB", "25", ""],
        ["Periodo mínimo / frecuencia máxima", "≤ 10 ns / ≥ 100 MHz (objetivo)", ""],
        ["Camino crítico", "multiplicador o sumador de 50 bits", ""],
    ], [3.2, 2.2, 1.5]))

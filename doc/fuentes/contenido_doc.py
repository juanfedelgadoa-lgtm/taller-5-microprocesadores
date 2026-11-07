"""Contenido del PDF del Taller 5 (version RTL: unidad de control + camino de datos).

Lo importa generar_pdf.py.  La tabla de la palabra de control se genera leyendo
la unidad de control en src/det_bareiss.vhd, para que el documento siempre
coincida con el codigo.
"""
import re

from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Preformatted, Spacer
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus import TableStyle

from generar_pdf import E, P, RAIZ, codigo, figura, tabla, traza_xs3, viñetas
from modelo_referencia import MATRICES, bareiss

VHDL = (RAIZ / "src" / "det_bareiss.vhd").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Lectura de la unidad de control desde el VHDL
# ---------------------------------------------------------------------------
def bloque_entidad(nombre):
    ini = VHDL.index(f"entity {nombre} is")
    return VHDL[ini:VHDL.index(f"end {nombre};", ini)]


def puertos(nombre):
    """Lista (nombre, direccion, bits) de los puertos de una entidad."""
    ent = bloque_entidad(nombre)
    res = []
    for m in re.finditer(r"^\s*([\w, ]+?)\s*:\s*(in|out)\s+STD_LOGIC(?:_VECTOR \((\d+) downto 0\))?",
                         ent, re.M):
        w = int(m.group(3)) + 1 if m.group(3) else 1
        for nm in m.group(1).split(","):
            res.append((nm.strip(), m.group(2), w))
    return res


def codigos_estado():
    return re.findall(r'constant (S\d+)\s*: STD_LOGIC_VECTOR \(4 downto 0\) := "([01]{5})";', VHDL)


def cond_txt(c):
    c = c.strip().strip("()")
    m = re.fullmatch(r"(\w+) = '([01])'", c)
    if m:
        return m.group(1) if m.group(2) == "1" else f"no {m.group(1)}"
    return c


def asign_txt(dest, val):
    val = val.strip()
    if val == "'1'" and (dest.startswith("sel_") or dest == "op_sr"):
        return f"{dest} = 1"
    if val == "'1'":
        return dest
    if val == "'0'":
        return f"{dest} = 0"
    if re.fullmatch(r'"[01]+"', val):
        return f"{dest} = {val.strip(chr(34))}"
    if dest == "prox":
        return f"→ {val}"
    return f"{dest} = {val}"


def palabra_control():
    """Para cada estado: (estado, codigo, salidas Moore, texto Mealy/siguiente)."""
    arq = VHDL[VHDL.index("architecture RTL of unidad_control"):]
    arq = arq[arq.index("case st is"):arq.index("end case;")]
    arq = re.sub(r"--[^\n]*", "", arq)
    bloques = re.split(r"\bwhen (S\d+) =>", arq)
    codigos = dict(codigos_estado())
    filas = []
    for idx in range(1, len(bloques), 2):
        est, cuerpo = bloques[idx], bloques[idx + 1]
        cuerpo = cuerpo.split("when others")[0]
        tokens = re.finditer(r"\bend if;|\belsif\s+(.+?)\s+then\b|\bif\s+(.+?)\s+then\b|\belse\b|(\w+)\s*<=\s*([^;]+);",
                             cuerpo, re.S)
        moore, mealy = [], []
        prof = 0
        linea = []

        def vaciar():
            if linea:
                mealy.append("\u00a0\u00a0\u00a0" * prof + ", ".join(linea))
                linea.clear()

        for t in tokens:
            txt = t.group(0)
            if txt.startswith("end if"):
                vaciar()
                prof -= 1
            elif txt.startswith("elsif"):
                vaciar()
                mealy.append("\u00a0\u00a0\u00a0" * (prof - 1) + f"si no, si {cond_txt(t.group(1))}:")
            elif txt.startswith("if"):
                vaciar()
                prof += 1
                mealy.append("\u00a0\u00a0\u00a0" * (prof - 1) + f"si {cond_txt(t.group(2))}:")
            elif txt == "else":
                vaciar()
                mealy.append("\u00a0\u00a0\u00a0" * (prof - 1) + "si no:")
            else:
                a = asign_txt(t.group(3), t.group(4))
                if prof == 0:
                    moore.append(a)
                else:
                    linea.append(a)
        vaciar()
        sig = [m for m in moore if m.startswith("→")]
        moore = [m for m in moore if not m.startswith("→")]
        texto_mealy = "[br]".join(mealy + sig)
        filas.append([est, codigos[est], ", ".join(moore) or "—", texto_mealy])
    return filas


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
    V = h.extend

    p_uc = puertos("unidad_control")
    n_ctrl = sum(1 for nm, d, w in p_uc if d == "out" and nm != "final")
    b_ctrl = sum(w for nm, d, w in p_uc if d == "out" and nm != "final")
    n_est = sum(1 for nm, d, w in p_uc if d == "in" and nm not in ("clk", "rst", "inicio"))

    # Portada -----------------------------------------------------------------
    A(Spacer(1, 1.1 * inch))
    A(P("Universidad Distrital Francisco José de Caldas[br]Ingeniería Electrónica · Análisis y Diseño de Microprocesadores", "subtitulo"))
    A(Spacer(1, 0.45 * inch))
    A(P("TALLER 5", "titulo"))
    A(P("Microprocesador de propósito específico:[br]determinante por el algoritmo de Bareiss[br]con salida BCD (algoritmo XS3)", "titulo"))
    A(Spacer(1, 0.3 * inch))
    A(P("Diseño RTL: unidad de control (FSM) y camino de datos[br]Diagrama ASM, señales de control y de estado, y código VHDL", "subtitulo"))
    A(Spacer(1, 0.15 * inch))
    A(P("Herramienta: Xilinx ISE 14.7 (XST, ISim) · Tarjeta: Digilent Nexys A7-100T (XC7A100T-1CSG324C)", "subtitulo"))
    A(Spacer(1, 0.8 * inch))
    A(P("[b]Nota para el equipo.[/b] Este documento explica un diseño de referencia. El enunciado advierte que "
        "los diseños parecidos entre equipos no se califican, así que revisen cada estado y cada señal, entiendan "
        "por qué está ahí y adáptenlo antes de entregarlo. Las conclusiones del informe son responsabilidad del equipo.", "nota"))
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
        "determinante con el algoritmo de Bareiss. Usa un multiplicador, un sumador/restador y una división por restas "
        "sucesivas. Guarda los pivotes en un banco de registros y convierte a BCD el valor que se va a mostrar con el "
        "algoritmo XS3 (sumar 3 y desplazar)."))
    A(P(f"El diseño está dividido como en las notas de clase: una [b]unidad de control[/b] (FSM de 27 estados, S0 a "
        f"S26, que implementa el diagrama ASM) y un [b]camino de datos[/b] (registros, multiplexores, memorias y "
        f"unidades funcionales). La unidad de control le envía {n_ctrl} señales de control ({b_ctrl} bits) y recibe "
        f"{n_est} señales de estado. Todas las entidades están en un solo archivo, src/det_bareiss.vhd."))
    A(P("Restricciones de diseño RTL", "h2"))
    A(tabla([
        ["Restricción", "Cómo se cumple"],
        ["Sin variables", "No hay ninguna [c]variable[/c] en el diseño. Solo el testbench, que no se sintetiza, las usa."],
        ["Solo std_logic y std_logic_vector",
         "Todas las señales, puertos y constantes son std_logic o std_logic_vector. El estado de la FSM es un "
         "std_logic_vector(4 downto 0) con constantes S0 a S26. No hay integer, signed, unsigned, enumerados ni "
         "genéricos. [b]Única excepción:[/b] la RAM se describe como [c]array of std_logic_vector[/c], que es la forma "
         "en que XST infiere una memoria (igual que el modelo de RAM del aula)."],
        ["Construcciones sintetizables", "Sin [c]wait[/c], [c]after[/c], archivos ni lazos [c]for[/c]/[c]while[/c] en el "
         "diseño. La síntesis genérica con GHDL termina sin errores y sin latches."],
        ["RTL claro: registros, lógica combinacional, FSM",
         "Cada registro tiene sus señales de carga (ld_*, clr_*, inc_*). Cada multiplexor tiene su selección (sel_*) "
         "y está escrito con [c]with … select[/c]. Las unidades funcionales son entidades combinacionales."],
        ["Separación FSM / camino de datos",
         "Entidades [c]unidad_control[/c] y [c]camino_datos[/c], unidas por la entidad estructural [c]procesador[/c]."],
        ["Nada de descripciones tipo software",
         "Las repeticiones del algoritmo (filas, columnas, pasos k, restas de la división, dígitos y bits del XS3) "
         "las hace la FSM, un paso por ciclo de reloj, con contadores del camino de datos."],
        ["Compatible con el esquemático RTL",
         "Jerarquía estructural (figura 3). En ISE, «View RTL Schematic» muestra cada bloque como un símbolo."],
    ], [2.0, 4.9]))
    A(P("Requisitos del enunciado", "h2"))
    A(tabla([
        ["Requisito del taller", "Cómo lo cumple el diseño"],
        ["ASM con señal de inicio y de final", "La FSM arranca con [c]inicio[/c] (BTNC) y pone [c]final = '1'[/c] solo en S26."],
        ["Matriz en ROM: 00h = n, luego los a(i,j) como en la Figura 1",
         "ROM de 256 × 6 bits escrita con [c]with dir select[/c], 8 páginas de 32 palabras. En cada página, 00h = n y "
         "los elementos van por columnas (a11, a21, …). [c]dira[/c] de 5 bits; datos en complemento a 2 (−32 a 31)."],
        ["Multiplicador, sumador/restador y división por restas sucesivas",
         "Entidades [c]multiplicador[/c] (con signo, 25 × 25) y [c]sumador_restador[/c] (50 bits). La división son los "
         "registros R, Q y |p| del camino de datos más el lazo del estado S17, que usa el restador."],
        ["Memoria RAM para las iteraciones", "Entidad [c]ram_trabajo[/c] de 64 × 32 bits; dirección fila & columna."],
        ["Pivotes en un banco de registros, visibles con los switches",
         "Registros b1 a b4. SW2..SW0 = 0 muestra el determinante; SW2..SW0 = k muestra el pivote k."],
        ["Determinante en los displays", "Entidad [c]display_8dig[/c]: AN7 = signo, AN6..AN0 = 7 dígitos; LD1 = desborde."],
        ["XS3 evidenciado paso a paso en el ASM",
         "Un estado por paso del documento XS3, cada uno con su señal de control: S22 (clr_bcd), S23 (ins_bcd), "
         "S24 (aj_bcd) y S25 (sh_bcd)."],
    ], [2.2, 4.7]))
    A(KeepTogether([P("Archivos del repositorio", "h2"), tabla([
        ["Archivo", "Contenido"],
        ["src/det_bareiss.vhd", "Diseño completo: 10 entidades (ROM, RAM, multiplicador, sumador/restador, camino de "
                                "datos, unidad de control, procesador, sincronizador, display y tope)."],
        ["src/nexys_a7.ucf", "Pines y restricción de reloj (100 MHz) para ISE."],
        ["sim/tb_procesador.vhd", "Testbench de la unidad de control + camino de datos con las 8 matrices y sus pivotes."],
        ["sim/tb_det_bareiss.vhd", "Testbench del tope: lee el display de 7 segmentos (an, seg)."],
        ["sim/modelo_referencia.py", "Modelo en Python: det y pivotes esperados, ciclos y líneas de la ROM."],
        ["sim/resultado_ghdl.txt", "Salida de las simulaciones."],
        ["doc/figuras/*.png, doc/fuentes/*.py", "Diagramas y scripts que generan las figuras y este PDF."],
    ], [2.2, 4.7])]))

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
    A(P("Si a(k,k) = 0, la FSM busca la primera fila i > k con a(i,k) ≠ 0 (estado S5), intercambia las filas k e i en "
        "las columnas k a n (S6 a S9) e invierte el bit [c]signo[/c]. Al final, det = −a(n,n) si hubo un número impar de "
        "intercambios. Si no hay ninguna fila con a(i,k) ≠ 0, det = 0. Las columnas menores que k no se intercambian "
        "porque el algoritmo no las vuelve a leer."))

    # 3 -----------------------------------------------------------------------
    A(P("3. Algoritmo XS3 dentro del ASM", "h1"))
    A(P("El documento XS3 describe 5 pasos. En el ASM cada paso es un estado propio con su señal de control, de modo "
        "que el diagrama muestra la conversión completa y no una caja que diga «convertir a BCD»."))
    A(tabla([
        ["Paso del documento XS3", "Estado", "Señal de control", "Operación en el camino de datos"],
        ["1. Inicializar el registro decimal en ceros", "S22", "clr_bcd, clr_cont", "BCD ← 0 (40 bits); cont ← 0"],
        ["2. Colocar el MSB del registro binario en el LSB del registro decimal", "S23", "ins_bcd",
         "BCD ← BCD(39..1) & bin(31)"],
        ["3. Revisar cada dígito: si es ≥ 5 (> 0100), sumarle 3 (0011)", "S24", "aj_bcd (si dig_gt4), inc_d",
         "Un dígito por ciclo (d = 0 a 9). El multiplexor de dígitos entrega BCD(d); el sumador calcula BCD(d) + 3; "
         "solo ese dígito se reemplaza."],
        ["4. Correr a la izquierda y descartar el bit que sale; repetir desde el paso 2", "S25",
         "sh_bcd, ld_bin (sel_bin = 10), inc_cont", "BCD ← BCD(38..0) & 0; bin ← bin(30..0) & 0; cont ← cont + 1"],
        ["5. Realizar únicamente el paso 2", "S23 con cont_31", "ins_bcd",
         "En la pasada 32 por S23 entra el último bit y la FSM va a S26 sin pasar por S24 ni S25."],
    ], [2.15, 0.65, 1.35, 2.75]))
    A(Spacer(1, 6))
    A(P("Por qué se suma 3: si un dígito vale 5 o más, al correrlo a la izquierda quedaría en 10 o más, que no es un "
        "dígito BCD válido. Sumar 3 antes del corrimiento equivale a sumar 6 después, que es la corrección BCD, y "
        "hace que el exceso pase como acarreo al dígito siguiente."))
    A(P("Tamaños: el registro binario [c]bin[/c] tiene 32 bits, así que el registro decimal necesita 10 dígitos "
        "(2[sup]32[/sup] − 1 = 4 294 967 295) y el lazo da 32 pasadas por el paso 2 (cont = 0 a 31). El signo no entra "
        "al XS3: en S21 se carga |valor| en [c]bin[/c] y el signo en [c]neg[/c], que luego enciende el segmento g de AN7."))
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
        "La simulación muestra « 0000362» en el display para esta matriz."))

    # 4 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("4. Caja negra, cajas grises y jerarquía", "h1"))
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
    A(Spacer(1, 6))
    A(figura("cajas_grises", "Figura 2. Cajas grises: señales de control (UC → CD) y señales de estado (CD → UC)."))
    A(P("La unidad de control no toca datos: solo decide qué hace el camino de datos en cada ciclo. El camino de datos "
        "no decide nada: ejecuta las cargas y selecciones que le piden y devuelve las comparaciones que la FSM necesita "
        "para elegir el siguiente estado."))
    A(figura("jerarquia", "Figura 3. Jerarquía de entidades (lo que muestra el esquemático RTL de ISE).", max_alto=3.6))
    A(tabla([
        ["Entidad", "Tipo", "Contenido"],
        ["det_bareiss", "Estructural", "Tope: sincronizador + procesador + display."],
        ["sincronizador", "RTL", "Dos flip-flops por entrada (inicio, sw_mat, sw_piv) para evitar metaestabilidad."],
        ["procesador", "Estructural", "Unidad de control + camino de datos conectados por las señales de control y de estado."],
        ["unidad_control", "FSM", "Registro de estado (5 bits) y lógica combinacional de estado siguiente y de salidas."],
        ["camino_datos", "RTL", "Registros, multiplexores, comparadores; instancia ROM, RAM, multiplicador y sumador/restador."],
        ["rom_matrices", "Combinacional", "[c]with dir select[/c] con las 8 matrices de prueba."],
        ["ram_trabajo", "Memoria", "64 × 32 bits, escritura síncrona y lectura asíncrona."],
        ["multiplicador", "Combinacional", "Producto con signo 25 × 25 → 50 bits ([c]std_logic_signed[/c])."],
        ["sumador_restador", "Combinacional", "50 bits, A + B o A + not(B) + 1."],
        ["display_8dig", "RTL", "Contador de refresco de 18 bits, multiplexor de dígitos y decodificador de 7 segmentos."],
    ], [1.45, 1.05, 4.4]))

    # 5 -----------------------------------------------------------------------
    A(P("5. Pseudocódigo con el hardware disponible", "h1"))
    A(P("Cada línea indica el estado de la FSM que la ejecuta. Las operaciones del mismo estado ocurren en el mismo "
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
        "  S23:  XS3 paso 2:  BCD(0) = bin(31);   si cont = 31 salir   (paso 5)\n"
        "  S24:  XS3 paso 3:  para d = 0..9:  si BCD(d) > 4 entonces BCD(d) = BCD(d) + 3\n"
        "  S25:  XS3 paso 4:  BCD = BCD << 1;  bin = bin << 1;  cont = cont + 1\n"
        "S26:  final = 1;  display = BCD;  si inicio = 1 ir a S1;  si cambia sw_piv ir a S21"))
    A(P("Los «para» y «mientras» del pseudocódigo no son lazos del VHDL: cada uno es un lazo de la FSM que vuelve a un "
        "estado mientras un contador del camino de datos no llegue a su límite."))

    # 6 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("6. Diagrama ASM", "h1"))
    A(P("Convenciones", "h2"))
    A(tabla([
        ["Elemento", "Significado"],
        ["Caja de estado (rectángulo azul)", "Operaciones de todo el estado: salidas Moore de la FSM."],
        ["Caja de decisión (rombo)", "Pregunta sobre una señal de estado; entre paréntesis va el nombre de la señal en el "
                                     "VHDL. La salida 1 es la condición verdadera."],
        ["Caja de salida condicional (rectángulo redondeado naranja)",
         "Operación que solo ocurre si se toma ese camino: salida Mealy de la FSM."],
        ["Bloque ASM (recuadro punteado)", "Caja de estado más sus decisiones y salidas condicionales: dura un ciclo de reloj."],
        ["Conector (círculo verde)", "Une hojas del diagrama: A → S1, B → S4, C → S11, D → S21, E → S20, F → S17, G → S22."],
        ["x ← expresión", "Carga de un registro; se hace efectiva en el flanco de subida al final del ciclo."],
        ["x = expresión", "Valor combinacional (no se guarda), por ejemplo final = 1 o la selección val."],
        ["M(i,j)", "Palabra de la RAM en la dirección fila i, columna j."],
    ], [2.3, 4.6]))
    A(Spacer(1, 4))
    A(P("Todas las decisiones de un bloque usan los valores que tienen los registros al comenzar el ciclo. Por "
        "ejemplo, en S19 la pregunta k = n − 1 usa el k anterior al incremento. Cada combinación de estado y decisiones "
        "lleva a un solo estado siguiente, y todo camino de decisiones termina en un estado."))
    A(P("Vista general", "h2"))
    A(figura("vista_general", "Figura 4. Diagrama de estados de la unidad de control (27 estados), agrupado por función.",
             max_alto=3.0))

    hojas = [
        ("asm_hoja1", "Hoja 1: espera y carga de la matriz (S0 a S3)",
         "S2 recorre la ROM con el contador [c]dira[/c] y los contadores de fila y columna. La dirección de la RAM es "
         "fila & columna, así que no hace falta multiplicar para ubicar a(i,j)."),
        ("asm_hoja2", "Hoja 2: pivote, búsqueda de fila e intercambio (S4 a S10)",
         "La RAM tiene un solo puerto: cada lectura o escritura ocupa un estado, por eso el intercambio usa cuatro "
         "estados por columna. Después del intercambio se vuelve a S4 para leer el pivote nuevo."),
        ("asm_hoja3", "Hoja 3: productos y numerador (S11 a S16)",
         "Con un solo multiplicador, los dos productos de la fórmula (1) se hacen en estados distintos. Los operandos "
         "se cargan en mul_a y mul_b un estado antes, para que el camino crítico sea registro → multiplicador → registro."),
        ("asm_hoja4", "Hoja 4: división por restas sucesivas y avance (S17 a S19)",
         "S17 es el lazo de la división: el restador calcula R − |p| y la señal r_ge indica si el resultado no es "
         "negativo. Si es así, R se carga con la resta y Q se incrementa. El signo se aplica al escribir en S18."),
        ("asm_hoja5", "Hoja 5: determinante y valor a mostrar (S20 y S21)",
         "A S21 se llega desde S20 (cálculo normal), desde S5 (matriz singular) y desde S26 cuando cambian SW2..SW0."),
        ("asm_hoja6", "Hoja 6: algoritmo XS3 paso a paso y fin (S22 a S26)",
         "S26 espera con final = 1 y el valor en el display. Si cambian SW2..SW0, la FSM vuelve a S21 y repite el XS3 "
         "con el pivote elegido (373 ciclos, invisibles para el ojo)."),
    ]
    for i, (fig, titulo, texto) in enumerate(hojas, start=1):
        A(PageBreak())
        A(P(titulo, "h2"))
        A(P(texto))
        A(figura(fig, f"Figura {4 + i}. {titulo}.", max_alto=7.9))

    # 7 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("7. Unidad de control", "h1"))
    A(P("La entidad [c]unidad_control[/c] tiene dos procesos, el modelo clásico de FSM en RTL:"))
    V(viñetas([
        "[b]Registro de estado[/b] (proceso secuencial): [c]st <= prox[/c] en cada flanco de subida; [c]st <= S0[/c] con rst.",
        "[b]Lógica combinacional[/b] (proceso combinacional sensible a st, inicio y las señales de estado): primero pone "
        "todas las salidas en su valor de reposo (ninguna carga, [c]op_sr = '1'[/c], [c]prox <= st[/c]) y luego, con "
        "[c]case st is[/c], activa las señales del estado actual. Las asignaciones dentro de un [c]if[/c] son las "
        "salidas condicionales (Mealy) del ASM. Como todas las salidas tienen un valor por defecto, no se generan latches.",
    ]))
    A(P("Codificación de estados", "h2"))
    cods = codigos_estado()
    filas_c = [["Estado", "Código", "Estado", "Código", "Estado", "Código"]]
    for r in range(9):
        fila = []
        for c in range(3):
            idx = r + 9 * c
            fila += [cods[idx][0], cods[idx][1]] if idx < len(cods) else ["", ""]
        filas_c.append(fila)
    A(tabla(filas_c, [0.8, 0.9, 0.8, 0.9, 0.8, 0.9]))
    A(Spacer(1, 4))
    A(P("El código es binario de 5 bits ([c]constant S0 : STD_LOGIC_VECTOR(4 downto 0) := \"00000\"[/c]). XST puede "
        "recodificar la FSM (por ejemplo a one-hot); el reporte de síntesis indica la codificación final."))
    A(P("Palabra de control por estado", "h2"))
    A(P("Esta tabla se generó leyendo el [c]case st is[/c] del VHDL. La columna Moore lista las señales que se activan "
        "en todo el estado. La columna Mealy muestra las que dependen de una señal de estado y el estado siguiente "
        "(→). Las señales que no aparecen están en reposo: '0', selección \"00\"/\"000\" y [c]op_sr = 1[/c]."))
    A(tabla([["Estado", "Código", "Salidas Moore", "Salidas Mealy y estado siguiente"]] + palabra_control(),
            [0.64, 0.6, 2.7, 2.96]))

    # 8 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("8. Señales del procesador", "h1"))
    A(P("8.1 Señales de estado (CD → UC)", "h2"))
    A(tabla([
        ["Señal", "Lógica en el camino de datos", "Se usa en"],
        ["inicio", "Botón BTNC tras el sincronizador", "S0, S26"],
        ["z_dout", "dout = 0 (comparador de 32 bits con la salida de la RAM)", "S4, S5"],
        ["i_eq_n", "i = n (comparador de 3 bits)", "S2, S5, S18"],
        ["j_eq_n", "j = n", "S2, S9, S18"],
        ["k1_eq_n", "k + 1 = n, es decir k = n − 1", "S19"],
        ["t3_neg", "t3(49), bit de signo del numerador", "S16"],
        ["r_ge", "not sr_s(49): la resta R − |p| no es negativa", "S17"],
        ["sq", "Registro sq_r = signo(t3) xor signo(p)", "S18"],
        ["piv_neg", "piv(31)", "S19"],
        ["signo", "Registro signo_r: paridad de intercambios", "S20"],
        ["val_neg", "val(31), signo del valor seleccionado", "S21"],
        ["cont_31", "cont = 11111", "S23"],
        ["dig_gt4", "BCD(d) > 0100 (comparador de 4 bits a la salida del mux de dígitos)", "S24"],
        ["d_9", "d = 1001", "S24"],
        ["sel_dif", "sw_piv ≠ sel_ant", "S26"],
    ], [1.0, 4.4, 1.5]))
    A(P("8.2 Señales de control (UC → CD)", "h2"))
    A(tabla([
        ["Señal", "Bits", "Efecto en el camino de datos"],
        ["ld_pag", "1", "pag ← sw_mat"],
        ["clr_dira, inc_dira", "1, 1", "dira ← 0 / dira ← dira + 1"],
        ["we_ram", "1", "Escribe din en RAM(fila & col)"],
        ["sel_fila", "2", "Fila de la RAM: 00 = i, 01 = k, 10 = n"],
        ["sel_col", "2", "Columna de la RAM: 00 = j, 01 = k, 10 = n"],
        ["sel_din", "3", "Dato de la RAM: 000 = ROM extendida, 001 = tmp1, 010 = tmp2, 011 = Q, 100 = sr_s (−Q)"],
        ["ld_n", "1", "n ← ROM(2..0)"],
        ["ld_i, sel_i", "1, 2", "i ← 00: 1, 01: i + 1, 10: k + 1"],
        ["ld_j, sel_j", "1, 2", "j ← 00: 1, 01: j + 1, 10: k + 1, 11: k"],
        ["ld_k, sel_k", "1, 1", "k ← 0: 1, 1: k + 1"],
        ["ld_piv", "1", "piv ← dout"],
        ["ld_p, sel_p", "1, 1", "p ← 0: 1, 1: piv"],
        ["ld_pabs, sel_pabs", "1, 2", "|p| ← 00: 1, 01: piv, 10: sr_s (−piv)"],
        ["clr_signo, tog_signo", "1, 1", "signo ← 0 / signo ← not signo"],
        ["clr_banco, ld_banco", "1, 1", "b1..b4 ← 0 / b(k) ← piv"],
        ["ld_tmp1, ld_tmp2", "1, 1", "tmp1 ← dout / tmp2 ← dout"],
        ["ld_ma, sel_ma, ld_mb", "1, 1, 1", "mul_a ← 0: piv, 1: dout / mul_b ← dout"],
        ["ld_t1, ld_t2, ld_t3", "1, 1, 1", "t1 ← producto / t2 ← producto / t3 ← sr_s"],
        ["ld_r, sel_r", "1, 1", "R ← 0: t3, 1: sr_s"],
        ["clr_q, inc_q, ld_sq", "1, 1, 1", "Q ← 0 / Q ← Q + 1 / sq ← signo(t3) xor signo(p)"],
        ["ld_det, sel_det", "1, 2", "det ← 00: 0, 01: dout, 10: sr_s (−M(n,n))"],
        ["sel_sra", "2", "Operando A del sumador: 00 = 0, 01 = t1, 10 = R, 11 = BCD(d)"],
        ["sel_srb", "3", "Operando B: 000 = t2, 001 = t3, 010 = |p|, 011 = Q, 100 = piv, 101 = dout, 110 = val, 111 = 3"],
        ["op_sr", "1", "0 = suma, 1 = resta"],
        ["ld_selant, ld_neg", "1, 1", "sel_ant ← sw_piv / neg ← signo(val)"],
        ["ld_bin, sel_bin", "1, 2", "bin ← 00: val, 01: sr_s (−val), 10: bin << 1"],
        ["clr_bcd, ins_bcd, aj_bcd, sh_bcd", "1, 1, 1, 1", "XS3 pasos 1, 2, 3 y 4 sobre el registro BCD"],
        ["clr_cont, inc_cont", "1, 1", "cont ← 0 / cont ← cont + 1"],
        ["clr_d, inc_d", "1, 1", "d ← 0 / d ← d + 1"],
        ["ld_disp", "1", "disp ← BCD; disp_neg ← neg"],
        ["final", "1", "Salida del procesador (LD0)"],
    ], [1.85, 0.75, 4.3]))
    A(P("8.3 Registros y tamaños", "h2"))
    A(tabla([
        ["Registro", "Bits", "Uso"],
        ["st (en la UC)", "5", "Estado de la FSM"],
        ["pag, dira", "3, 5", "Página y dirección de la ROM"],
        ["n, i, j, k", "3 c/u", "Tamaño de la matriz y contadores de fila, columna y paso"],
        ["piv, p, |p|", "32 c/u", "Pivote actual, pivote anterior (divisor) y su magnitud"],
        ["signo_r", "1", "Paridad de intercambios de filas"],
        ["b1, b2, b3, b4", "32 c/u", "Banco de pivotes"],
        ["tmp1, tmp2", "32 c/u", "Intercambio de filas"],
        ["mul_a, mul_b", "25 c/u", "Registros de entrada del multiplicador"],
        ["t1, t2, t3", "50 c/u", "Productos y numerador de la fórmula (1)"],
        ["R, Q, sq_r", "50, 32, 1", "Residuo, cociente y signo del cociente"],
        ["det", "32", "Determinante"],
        ["sel_ant, neg", "3, 1", "Selección ya convertida y signo del valor convertido"],
        ["bin, BCD", "32, 40", "Registros binario y decimal del XS3"],
        ["cont, d", "5, 4", "Bits procesados y dígito revisado en el XS3"],
        ["disp, disp_neg_r", "40, 1", "Valor que se ve en el display"],
        ["refresco (display_8dig)", "18", "Barrido del display: 2[sup]15[/sup] ciclos por dígito, 2,6 ms por barrido"],
    ], [1.75, 1.0, 4.15]))
    A(P("Por qué estos anchos", "h2"))
    A(P("Por la identidad de Sylvester, cada valor guardado en la RAM es el determinante de una submatriz m×m de A. La "
        "desigualdad de Hadamard lo acota: |det| ≤ (32·√m)[sup]m[/sup] cuando |a(i,j)| ≤ 32."))
    V(viñetas([
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
    A(P("El camino de datos se organiza alrededor de dos buses: la salida de la RAM ([c]dout[/c]) y la salida del "
        "sumador/restador ([c]sr_s[/c]). Entre corchetes están las señales de control de cada bloque."))
    A(figura("camino_datos", "Figura 11. Camino de datos con sus señales de control.", max_alto=5.2))
    A(P("Cómo está escrito cada elemento", "h2"))
    A(tabla([
        ["Elemento", "Forma en el VHDL"],
        ["Registro con carga", "[c]if ld_x = '1' then x <= x_d; end if;[/c] dentro del único proceso con reloj del camino de datos."],
        ["Contador", "[c]if clr_x = '1' then x <= 0 elsif inc_x = '1' then x <= x + '1'[/c]."],
        ["Multiplexor", "[c]with sel_x select x_d <= … when \"00\", …[/c] (sentencia concurrente)."],
        ["Comparador", "[c]z <= '1' when a = b else '0';[/c]"],
        ["Extensión de signo", "Señal auxiliar [c]sx <= (others => x(31));[/c] y concatenación [c]sx & x[/c]."],
        ["Unidad funcional", "Entidad combinacional instanciada con [c]port map[/c] (multiplicador, sumador/restador)."],
        ["Memoria", "ROM: [c]with dir select[/c]. RAM: arreglo con escritura en el flanco y lectura asíncrona."],
    ], [1.6, 5.3]))
    A(P("La síntesis genérica con GHDL ([c]ghdl --synth[/c]) confirma un solo multiplicador (25 × 25), un solo sumador "
        "de 50 bits, la RAM de 64 × 32 inferida como memoria y ningún latch."))

    # 10 ----------------------------------------------------------------------
    A(P("10. Tiempo de ejecución", "h1"))
    V(viñetas([
        "Carga de la matriz (S0 a S3): n² + 3 ciclos.",
        "Paso k: S4, S10 y S19 (3 ciclos) más, por cada uno de los (n − k)² elementos, 8 ciclos fijos (S11 a S16 y S18) "
        "y |cociente| + 1 ciclos de división en S17.",
        "Intercambio de filas: hasta n − k ciclos de búsqueda, 4 ciclos por columna y una nueva lectura del pivote.",
        "XS3: 373 ciclos desde S21 hasta llegar a S26.",
    ]))
    A(P("La división por restas sucesivas domina el tiempo cuando los valores son grandes, porque tarda tantos ciclos "
        "como vale el cociente. En la página 7 (5×5 con valores cercanos a ±32) el cálculo tarda 19 013 425 ciclos, "
        "0,19 s a 100 MHz. En el peor caso teórico el último cociente se acerca a 1,9 × 10[sup]9[/sup], unos 19 s. Una "
        "división con corrimiento y resta (restauración) haría lo mismo en 50 ciclos; aquí se dejó la de restas "
        "sucesivas porque es la que pide el enunciado."))

    # 11 ----------------------------------------------------------------------
    A(P("11. Implementación en ISE 14.7 y la Nexys A7", "h1"))
    A(P("11.1 Proyecto", "h2"))
    V(viñetas([
        "File → New Project. Top-level source type: HDL.",
        "Family: Artix7 · Device: XC7A100T · Package: CSG324 · Speed: −1 · Synthesis: XST · Simulator: ISim · "
        "Preferred language: VHDL. ISE solo soporta la Nexys A7-100T; la variante 50T exige Vivado.",
        "Add Source: src/det_bareiss.vhd y src/nexys_a7.ucf (Implementation); sim/tb_procesador.vhd y "
        "sim/tb_det_bareiss.vhd (Simulation). ISE detecta det_bareiss como tope; si no, márquenlo con «Set as Top Module».",
        "Synthesize → View RTL Schematic para ver la jerarquía de la figura 3. Luego Implement Design y "
        "Generate Programming File. Revisen en el reporte de tiempos que se cumpla TS_sys_clk (10 ns).",
        "Programación: según el manual de la tarjeta, la Nexys A7 no funciona con Digilent Adept. Usen iMPACT de ISE o "
        "el Hardware Manager de Vivado (Lab Edition) con el archivo .bit.",
    ]))
    A(P("11.2 Operación en la tarjeta", "h2"))
    V(viñetas([
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
        "el det y los pivotes esperados y las líneas de la ROM (formato [c]\"dato\" when \"dirección\",[/c]) listas para "
        "pegar en la entidad rom_matrices."))
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
    V(viñetas([
        "[b]sim/tb_procesador.vhd[/b] prueba la unidad de control con el camino de datos. Para cada matriz pulsa inicio, "
        "espera final = 1 y compara disp_bcd, disp_neg y desborde con el valor esperado; después recorre los pivotes "
        "con sw_piv = 1 a n − 1. El genérico MAX_MATRIZ del testbench vale 6 por defecto (unos 0,2 ms simulados); con 7 "
        "incluye la matriz extrema, que tarda bastante.",
        "[b]sim/tb_det_bareiss.vhd[/b] prueba el tope completo con el sincronizador y el display: calcula la página 3 y "
        "lee los 8 dígitos decodificando an y seg durante un barrido completo (2[sup]18[/sup] ciclos). Luego elige el "
        "pivote 3.",
    ]))
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
    A(P("Todos los pivotes también coinciden, y el testbench del tope leyó « 0000362» y «-0000170» en los segmentos "
        "(ver sim/resultado_ghdl.txt). Para comprobar que los testbench detectan errores se probaron dos fallas en una "
        "copia del diseño: con «+2» en lugar de «+3» en el XS3, y con |p| ← piv en lugar de |p| ← −piv en S19. En ambos "
        "casos el testbench reportó errores."))

    # 13 ----------------------------------------------------------------------
    A(P("13. Limitaciones y verificación pendiente", "h1"))
    V(viñetas([
        "[b]No se ejecutó ISE.[/b] El diseño se verificó con GHDL 4.1 (simulación con [c]-fsynopsys -fexplicit[/c] y "
        "síntesis genérica), no con XST ni ISim. Hay que sintetizar en ISE 14.7 y revisar el reporte de tiempos a "
        "100 MHz. Si no se cumpliera, generen un reloj de 50 MHz con el Clocking Wizard y pongan PERIOD = 20 ns.",
        "[b]Arreglo de la RAM.[/b] Es la única construcción que no es std_logic ni std_logic_vector. Si el profesor no la "
        "acepta, reemplacen la entidad ram_trabajo por el modelo de RAM del aula con los mismos puertos.",
        "[b]Modelo de RAM.[/b] Se usó lectura asíncrona. Si el modelo del aula tiene lectura síncrona, cada lectura "
        "(S4, S5, S6, S7, S11, S12, S13, S20) necesita un estado de espera antes de usar el dato.",
        "[b]Display de 7 dígitos.[/b] Con signo en AN7 caben valores hasta ±9 999 999; para valores mayores se "
        "enciende LD1 y se ven los 7 dígitos de abajo.",
        "[b]Tiempo de la división.[/b] Proporcional al cociente (sección 10).",
        "[b]Valor de n.[/b] El diseño supone 2 ≤ n ≤ 5 en la ROM y no lo valida.",
        "[b]ROM con 8 páginas.[/b] La selección de página con SW15..SW13 permite mostrar varios tamaños sin volver a "
        "sintetizar. Si el profesor quiere una sola matriz, usen la página 0 con esos switches en 0.",
    ]))

    # Anexo -------------------------------------------------------------------
    A(PageBreak())
    A(P("Anexo A. Código VHDL completo (src/det_bareiss.vhd)", "h1"))
    numeradas = "\n".join(f"{n:4d}  {l}" for n, l in enumerate(VHDL.splitlines(), start=1))
    A(Preformatted(numeradas, E["anexo"]))
    return h

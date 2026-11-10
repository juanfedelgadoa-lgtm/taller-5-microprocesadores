"""Contenido del PDF del Taller 5 (procesador con una ALU; XS3 y division
integrados al ASM de Bareiss).

Lo importa generar_pdf.py.  Los resultados de simulacion se leen de
sim/resultado_ghdl.txt y la tabla de matrices de sim/modelo_referencia.py.
"""
import re

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Preformatted, Spacer, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents

from generar_pdf import E, P, RAIZ, codigo, figura, tabla, traza_xs3, viñetas
from modelo_referencia import MATRICES, MATRIZ_POR_DEFECTO, bareiss, texto_display

E["h2_anexo"] = ParagraphStyle("h2_anexo", parent=E["h2"])   # no aparece en el indice

ARCHIVOS_VHDL = ["det_bareiss.vhd", "procesador.vhd", "asm_bareiss.vhd", "alu.vhd",
                 "multiplicador.vhd", "banco_pivotes.vhd", "ram.vhd", "rom_matriz.vhd",
                 "divisor_frecuencia.vhd", "antirrebote.vhd", "sincronizador.vhd", "display_8dig.vhd"]


def resultados_sim():
    """{matriz: (ciclos, det_texto)} desde sim/resultado_ghdl.txt."""
    texto = (RAIZ / "sim" / "resultado_ghdl.txt").read_text(encoding="utf-8")
    res = {}
    for bloque in re.split(r"== Matriz ", texto)[1:]:
        num = int(bloque[0])
        ciclos = int(re.search(r"Corrida 1: final = 1 en (\d+) ciclos", bloque).group(1))
        det = re.search(r"det\s+= '(.{11})'  OK", bloque).group(1)
        res[num] = (ciclos, det)
    return res


def mat_txt(a):
    return "[br]".join("[c]" + " ".join(f"{x:3d}" for x in fila).replace(" ", "\u00a0") + "[/c]" for fila in a)


def contenido():
    h = []
    A = h.append
    V = h.extend

    # Portada -----------------------------------------------------------------
    A(Spacer(1, 1.1 * inch))
    A(P("Universidad Distrital Francisco José de Caldas[br]Ingeniería Electrónica · Análisis y Diseño de Microprocesadores", "subtitulo"))
    A(Spacer(1, 0.45 * inch))
    A(P("TALLER 5", "titulo"))
    A(P("Microprocesador de propósito específico:[br]determinante por el algoritmo de Bareiss[br]con salida BCD (algoritmo XS3)", "titulo"))
    A(Spacer(1, 0.3 * inch))
    A(P("Caja negra, cajas grises, pseudoalgoritmo, diagrama ASM y código VHDL", "subtitulo"))
    A(Spacer(1, 0.15 * inch))
    A(P("Herramienta: Xilinx ISE 14.7 (XST, ISim) · Tarjeta: Digilent Nexys A7-100T (XC7A100T-1CSG324C)", "subtitulo"))
    A(Spacer(1, 0.8 * inch))
    A(P("[b]Nota para el equipo.[/b] Este documento explica un diseño de referencia. El enunciado advierte que "
        "los diseños parecidos entre equipos no se califican, así que revisen cada estado y cada bloque, entiendan "
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
    A(P("El procesador calcula el determinante de la matriz guardada en su ROM (de 2×2 a 5×5) con el algoritmo de "
        "Bareiss, guarda los pivotes en un banco de registros y entrega el determinante y el pivote que indica "
        "[c]dir_p[/c] en BCD, convertidos con el algoritmo XS3. La ROM hace parte de la arquitectura: para calcular "
        "el determinante de otra matriz se cambia el archivo de la ROM y se vuelve a programar la FPGA."))
    A(P("Los bloques del camino de datos (ROM, RAM, multiplicador, ALU y banco de pivotes) están descritos aparte e "
        "interconectados en la entidad estructural [c]procesador[/c]. Un solo ASM ([c]asm_bareiss[/c], 27 estados) "
        "maneja el direccionamiento y les distribuye las señales. La división por restas sucesivas y el algoritmo "
        "XS3 están integrados en ese ASM, y todas sus sumas y restas pasan por la [b]única ALU[/b] del procesador, "
        "que sigue la tabla de funcionamiento del curso (M, s1, s0)."))
    A(P("Reglas de descripción", "h2"))
    A(tabla([
        ["Regla", "Cómo se cumple"],
        ["Solo std_logic, excepto la RAM",
         "Todas las señales, puertos y constantes son std_logic o std_logic_vector. La RAM sigue el modelo del curso "
         "([c]type mem is array … of std_logic_vector[/c] y [c]conv_integer[/c] en la línea de dirección); es el único "
         "lugar del diseño donde aparecen."],
        ["Sin integer, signed ni unsigned",
         "No hay [c]integer[/c], [c]natural[/c], [c]signed[/c], [c]unsigned[/c], [c]boolean[/c], tipos enumerados ni "
         "genéricos. Los estados son constantes [c]std_logic_vector[/c]; el [c]case st is / when s0 =>[/c] se escribe "
         "igual que en los ejemplos de clase."],
        ["Sin variables ni descripciones tipo software",
         "No hay [c]variable[/c] ni lazos [c]for[/c]/[c]while[/c]. Las repeticiones del algoritmo las hace el ASM, "
         "un paso por ciclo de reloj, con contadores."],
        ["Una sola ALU",
         "Entidad [c]alu[/c] con la tabla del curso. La usan t1 − t2, la división (residuo − |p|), los valores "
         "absolutos (0 − x) y el +3 del XS3. No hay otro sumador/restador de datos en el diseño."],
        ["Un solo multiplicador", "Entidad [c]multiplicador[/c] (25 × 25 → 50 bits)."],
        ["Sintetizable y con esquemático RTL claro",
         "Un archivo por bloque y entidades estructurales ([c]procesador[/c], [c]det_bareiss[/c]) que solo conectan "
         "bloques. La síntesis genérica con GHDL termina sin errores ni latches, con un solo sumador de 50 bits "
         "(dentro de la ALU) y un solo multiplicador."],
        ["Solo para simulación", "Los testbench usan variables, integer, real, string y wait; no se sintetizan."],
    ], [1.9, 5.0]))
    A(P("Requisitos del enunciado y de la clase", "h2"))
    A(tabla([
        ["Requisito", "Cómo lo cumple el diseño"],
        ["Señal de inicio y señal de final", "Entradas y salidas del procesador; [c]final = '1'[/c] en el estado s26."],
        ["Matriz en ROM: 00h = n, luego los a(i,j) como en la Figura 1",
         "Entidad [c]rom_matriz[/c]: dirección [c]dira[/c] de 5 bits y dato [c]a[/c] de 6 bits en complemento a 2. "
         "Elementos por columnas: a11, a21, …, an1, a12, …"],
        ["La ROM hace parte de la arquitectura", "La ROM está dentro del procesador; no se ingresa por puertos."],
        ["Multiplicador, sumador/restador y división por restas sucesivas",
         "Entidad [c]multiplicador[/c]; la ALU hace de sumador/restador; la división son los estados s15 y s16 del ASM."],
        ["Memoria RAM para las iteraciones", "Entidad [c]RAM_memory[/c] (modelo del curso), 64 × 32 bits."],
        ["Pivotes en un banco de registros, visibles con los switches",
         "Entidad [c]banco_pivotes[/c]. dir_p = k (SW2..SW0) elige el pivote; el último pivote (k = n) es el determinante."],
        ["Determinante en los displays, en decimal", "Salida [c]det[/c] en BCD; con dir_p = 0 el display muestra det."],
        ["XS3 integrado al algoritmo de Bareiss, usando la ALU",
         "Estados s20 a s25 del mismo ASM, un estado por paso del documento XS3; el +3 lo calcula la ALU (A + B)."],
        ["Un solo antirrebote", "Entidad [c]antirrebote[/c], solo para el botón de inicio."],
    ], [2.2, 4.7]))
    A(KeepTogether([P("Archivos del repositorio", "h2"), tabla([
        ["Archivo", "Contenido"],
        ["src/det_bareiss.vhd", "Tope para la Nexys A7 (estructural)."],
        ["src/procesador.vhd", "Procesador: une el ASM con sus bloques (estructural)."],
        ["src/asm_bareiss.vhd", "ASM de Bareiss con la división y el XS3 integrados (s0 a s26)."],
        ["src/alu.vhd", "ALU con la tabla del curso (M, s1, s0)."],
        ["src/multiplicador.vhd", "Multiplicador con signo 25 × 25 → 50."],
        ["src/rom_matriz.vhd, src/ram.vhd, src/banco_pivotes.vhd", "ROM con la matriz, RAM (modelo del curso), banco de pivotes."],
        ["src/divisor_frecuencia.vhd, src/antirrebote.vhd, src/sincronizador.vhd, src/display_8dig.vhd",
         "Interfaz con la tarjeta."],
        ["src/nexys_a7.ucf", "Pines y restricción de reloj (100 MHz)."],
        ["sim/tb_alu.vhd", "Testbench de las 8 operaciones de la ALU."],
        ["sim/tb_procesador.vhd, sim/pkg_prueba.vhd", "Testbench autoverificado del procesador: sirve para cualquier ROM."],
        ["sim/tb_det_bareiss.vhd", "Testbench de la tarjeta: botón con rebotes y lectura del display."],
        ["sim/modelo_referencia.py", "Valores esperados y generador de src/rom_matriz.vhd."],
        ["sim/probar_matrices.py, sim/resultado_ghdl.txt", "Prueba con las 8 matrices y sus resultados."],
        ["doc/figuras/*.png, doc/fuentes/*.py", "Figuras de este documento y los scripts que las generan."],
    ], [2.6, 4.3])]))

    # 2 -----------------------------------------------------------------------
    A(P("2. Repaso del algoritmo de Bareiss", "h1"))
    A(P("Bareiss es una eliminación gaussiana sin fracciones. En el paso k, cada elemento de la submatriz que está "
        "debajo y a la derecha del pivote se actualiza con la fórmula (1) del enunciado:"))
    A(codigo("a(i,j) = ( a(k,k)·a(i,j) − a(i,k)·a(k,j) ) / p        para k < i ≤ n,  k < j ≤ n\n"
             "p = pivote del paso anterior (p = 1 en el primer paso)"))
    A(P("Después del paso k, el pivote actual a(k,k) pasa a ser p. Tras n − 1 pasos, el determinante queda en a(n,n), "
        "que es el último pivote. La división siempre es exacta: por la identidad de Sylvester, después del paso k "
        "cada a(i,j) es el determinante de una submatriz de (k+1)×(k+1) de A, que es un entero."))
    A(P("Durante el paso k solo cambian los elementos con i > k y j > k. La fila k y la columna k no se modifican, "
        "por eso el cálculo se hace sobre la misma RAM, sin una segunda copia de la matriz."))
    A(P("Ejemplo 3×3", "h2"))
    A(codigo("A = | 2 1 3 |      k = 1, p = 1:  a22 = (2·4 − 1·1)/1 = 7    a23 = (2·2 − 1·3)/1 = 1\n"
             "    | 1 4 2 |                     a32 = (2·2 − 3·1)/1 = 1    a33 = (2·5 − 3·3)/1 = 1\n"
             "    | 3 2 5 |      k = 2, p = 2:  a33 = (7·1 − 1·1)/2 = 3   →   det = 3\n"
             "Banco de pivotes: pivote 1 = 2, pivote 2 = 7, pivote 3 = 3 = det"))
    A(P("Pivote cero", "h2"))
    A(P("Si a(k,k) = 0, el ASM busca la primera fila i > k con a(i,k) ≠ 0 (estado s5), intercambia las filas k e i en "
        "las columnas k a n (s6 a s8) e invierte el bit [c]signo[/c]. Al final, det = −a(n,n) si hubo un número impar de "
        "intercambios, y ese valor con su signo es el que se guarda como último pivote, para que el pivote n siempre "
        "sea igual al determinante. Si no hay fila con a(i,k) ≠ 0, det = 0."))

    # 3 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("3. Caja negra", "h1"))
    A(P("La caja negra es la del tablero de clase: entradas clk, rst, inicio y dir_p; salidas det, pivote y final. La "
        "ROM, la RAM, el multiplicador y la ALU están adentro. Es la entidad [c]procesador[/c]."))
    A(figura("caja_negra", "Figura 1. Caja negra del procesador.", max_ancho=5.8))
    A(tabla([
        ["Puerto", "Dir.", "Bits", "Función"],
        ["clk", "in", "1", "Reloj (100 MHz en la tarjeta)"],
        ["rst", "in", "1", "Reinicio asíncrono, activo en alto"],
        ["inicio", "in", "1", "Comienza el cálculo (pulso de un ciclo; se lee en s0 y s26)"],
        ["dir_p", "in", "3", "Dirección del banco de pivotes: 1 a n = pivote k (el n es el det); 0, 6 y 7 leen 0"],
        ["det, det_neg", "out", "40, 1", "|det| en BCD (10 dígitos) y su signo"],
        ["pivote, piv_neg", "out", "40, 1", "|pivote(dir_p)| en BCD y su signo"],
        ["final", "out", "1", "'1' cuando det y pivote están listos (estado s26)"],
    ], [1.3, 0.5, 0.6, 4.5]))
    A(P("Caja negra de la tarjeta", "h2"))
    A(P("La entidad [c]det_bareiss[/c] conecta el procesador con la Nexys A7:"))
    A(tabla([
        ["Puerto", "Pin", "Función"],
        ["clk", "E3", "Reloj de 100 MHz"],
        ["rst", "BTNU (M18)", "Reinicio de todo el diseño"],
        ["inicio", "BTNC (N17)", "Comienza el cálculo (pasa por el antirrebote)"],
        ["dir_p(2..0)", "SW2..SW0", "0: el display muestra det; 1 a 5: muestra el pivote k"],
        ["final", "LD0", "Fin del cálculo"],
        ["desborde", "LD1", "El valor mostrado tiene más de 7 dígitos"],
        ["latido", "LD15", "Onda de 1 s del divisor de frecuencia (indica que el diseño está corriendo)"],
        ["an, seg, dp", "AN7..AN0, CA..CG, DP", "Display: AN7 = signo, AN6..AN0 = 7 dígitos"],
    ], [1.3, 1.8, 3.8]))

    # 4 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("4. Cajas grises", "h1"))
    A(P("Antes del ASM se define el hardware: qué bloques hay, cómo se conectan y qué señales intercambian con la "
        "unidad de control. La caja gris del procesador muestra el ASM y los bloques del camino de datos con todas "
        "sus señales."))
    A(figura("cajas_grises", "Figura 2. Caja gris del procesador: unidad de control (ASM) y bloques del camino de datos.",
             max_alto=5.8))
    A(tabla([
        ["Bloque", "Entradas desde el ASM", "Salidas hacia el ASM", "Uso"],
        ["ROM (rom_matriz)", "dira (5)", "a (6)", "Leer n y los elementos (s1, s2)"],
        ["RAM (RAM_memory)", "rd_add (6), wr_add (6), we, data (32)", "q (32)", "Matriz de trabajo; dirección fila & columna"],
        ["multiplicador", "mul_a (25), mul_b (25)", "producto (50)", "a(k,k)·a(i,j) y a(i,k)·a(k,j)"],
        ["alu", "alu_a (50), alu_b (50), alu_m, alu_s1, alu_s0", "resultado (50)",
         "t1 − t2, división, valores absolutos y +3 del XS3"],
        ["banco_pivotes", "clr_banco, we_banco, dir_banco (3), dato_banco (32)", "piv_banco (32)",
         "Guardar los pivotes; se lee con dir_p"],
    ], [1.35, 2.2, 1.45, 1.9]))
    A(P("Tope de la tarjeta", "h2"))
    A(figura("tope", "Figura 3. Bloques del tope det_bareiss.", max_alto=2.6))

    # 5 -----------------------------------------------------------------------
    A(P("5. La ALU", "h1"))
    A(P("La entidad [c]alu[/c] es la unidad aritmético-lógica del curso. Las líneas M, s1 y s0 eligen la operación:"))
    A(tabla([
        ["M", "s1", "s0", "Operación", "Uso en este procesador"],
        ["0", "0", "0", "not B", "—"],
        ["0", "0", "1", "A and B", "—"],
        ["0", "1", "0", "A or B", "—"],
        ["0", "1", "1", "A xnor B", "—"],
        ["1", "0", "0", "A + 1", "—"],
        ["1", "0", "1", "A + B", "s23: dígito BCD + 3 (paso 3 del XS3)"],
        ["1", "1", "0", "A − B", "s14: t1 − t2; s16: residuo − |p|; s15, s17, s18, s19, s20: valores absolutos 0 − x"],
        ["1", "1", "1", "A − 1", "—"],
    ], [0.35, 0.35, 0.35, 1.0, 4.85]))
    A(Spacer(1, 4))
    A(P("La ALU implementa las 8 operaciones aunque el algoritmo solo use A + B y A − B. Las cuatro operaciones "
        "aritméticas comparten un solo sumador [c]S = A + Bx + cin[/c]; lo único que cambia es el segundo operando "
        "y el acarreo de entrada:"))
    A(tabla([
        ["Operación", "Bx", "cin", "Por qué"],
        ["A + 1", "0", "1", "A + 0 + 1"],
        ["A + B", "B", "0", "Suma directa"],
        ["A − B", "not B", "1", "Complemento a 2: −B = not B + 1"],
        ["A − 1", "1…1", "0", "1…1 es −1 en complemento a 2"],
    ], [1.0, 0.9, 0.6, 4.4]))
    A(Spacer(1, 4))
    A(figura("alu_interna", "Figura 4. Estructura interna de la ALU.", max_alto=3.2))
    A(P("La ALU es de 50 bits porque la operación más ancha es t1 − t2 (productos de 50 bits). El ASM elige los "
        "operandos con dos multiplexores según el estado (sección 10.1) y fija [c]M s1 s0 = 101[/c] en s23 y "
        "[c]110[/c] en los demás estados. La prueba sim/tb_alu.vhd verifica las 8 operaciones."))

    # 6 -----------------------------------------------------------------------
    A(P("6. Pseudoalgoritmo con el hardware disponible", "h1"))
    A(P("Cada línea indica el estado del ASM que la ejecuta. Las operaciones del mismo estado ocurren en el mismo "
        "ciclo de reloj. «RAM(f,c)» es la palabra de la RAM en la dirección fila f, columna c."))
    A(codigo(
        "s0 :  final = 0;  esperar inicio = 1\n"
        "s1 :  n = ROM(00h)\n"
        "s2 :  para j = 1..n, i = 1..n:  RAM(i,j) = ROM(dira);  dira = dira + 1     (por columnas)\n"
        "s3 :  k = 1;  p = 1;  |p| = 1;  signo = 0;  conv_piv = 0;  banco = 0\n"
        "mientras k <= n-1:\n"
        "  s4 :  piv = RAM(k,k)\n"
        "        si piv = 0:\n"
        "  s5 :     buscar i = k+1..n con RAM(i,k) /= 0;  si no existe: det_bin = 0, ir a XS3\n"
        "  s6-s8:   intercambiar filas k e i (columnas k..n);  signo = not signo;  volver a s4\n"
        "  s9 :  banco(k) = piv\n"
        "        para i = k+1..n, j = k+1..n:\n"
        "  s10-s13:  t1 = piv · RAM(i,j);   t2 = RAM(i,k) · RAM(k,j)      (multiplicador)\n"
        "  s14:      t3 = t1 - t2                                       (ALU)\n"
        "  s15:      residuo = |t3|;  cociente = 0                      (ALU para 0 - t3)\n"
        "  s16:      mientras residuo - |p| >= 0:                       (ALU)\n"
        "               residuo = residuo - |p|;  cociente = cociente + 1\n"
        "  s17:      RAM(i,j) = +cociente o -cociente  (signo(t3) xor signo(p))\n"
        "  s18:  p = piv;  |p| = |piv|;  k = k + 1\n"
        "s19:  det_bin = RAM(n,n) o -RAM(n,n) (según signo);  banco(n) = det_bin\n"
        "XS3 (dos veces: conv_piv = 0 para det, conv_piv = 1 para el pivote):\n"
        "s20:  val = det_bin o banco(dir_p);  bin = |val|;  neg = signo(val)\n"
        "s21:  PASO 1:  BCD = 0;  cont = 0\n"
        "repetir:\n"
        "  s22:  PASO 2:  BCD(0) = bin(31);   si cont = 31 salir   (PASO 5)\n"
        "  s23:  PASO 3:  para d = 0..9:  si BCD(d) > 4 entonces BCD(d) = BCD(d) + 3   (ALU)\n"
        "  s24:  PASO 4:  BCD = BCD << 1;  bin = bin << 1;  cont = cont + 1\n"
        "s25:  si conv_piv = 0:  det = BCD;  conv_piv = 1;  repetir XS3\n"
        "      si no:            pivote = BCD\n"
        "s26:  final = 1;  si inicio = 1 ir a s1;  si cambia dir_p ir a s20"))
    A(P("Los «para» y «mientras» no son lazos del VHDL: cada uno es un lazo del ASM que vuelve a un estado mientras "
        "un contador no llegue a su límite."))

    # 7 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("7. Diagrama ASM", "h1"))
    A(P("Convenciones", "h2"))
    A(tabla([
        ["Elemento", "Significado"],
        ["Caja de estado (rectángulo azul)", "Operaciones de todo el estado (salidas tipo Moore)."],
        ["Caja de decisión (rombo)", "Pregunta sobre una señal de estado. La salida 1 es la condición verdadera."],
        ["Caja de salida condicional (rectángulo redondeado naranja)",
         "Operación que solo ocurre si se toma ese camino (tipo Mealy), como en el ejemplo «ASM Mealy» de clase."],
        ["Bloque ASM (recuadro punteado)", "Caja de estado más sus decisiones y salidas condicionales: dura un ciclo de reloj."],
        ["Conector (círculo verde)", "Une hojas del diagrama: A → s1, B → s4, C → s10, D → s20, E → s16."],
        ["x ← expresión", "Carga de un registro; se hace efectiva en el flanco de subida al final del ciclo."],
        ["x = expresión", "Señal combinacional, por ejemplo final = 1."],
        ["(ALU: A − B)", "La operación se hace en la ALU en ese estado."],
        ["RAM(f,c) ← dato", "Escritura en la RAM (we = 1) en la dirección fila f, columna c."],
    ], [2.3, 4.6]))
    A(Spacer(1, 4))
    A(P("Todas las decisiones de un bloque usan los valores que tienen los registros al comenzar el ciclo. Cada "
        "combinación de estado y decisiones lleva a un solo estado siguiente, y todo camino de decisiones termina en "
        "un estado."))
    A(P("Vista general", "h2"))
    A(figura("vista_general", "Figura 5. Diagrama de estados del ASM (27 estados).", max_alto=3.0))

    hojas = [
        ("asm_hoja1", "Hoja 1: espera y carga de la matriz (s0 a s3)",
         "s2 recorre la ROM con el contador dira y los contadores i y j. La dirección de la RAM es fila & columna "
         "(3 + 3 bits), así que no hace falta multiplicar para ubicar a(i,j)."),
        ("asm_hoja2", "Hoja 2: pivote, búsqueda de fila, intercambio y banco (s4 a s9)",
         "La RAM tiene una dirección de lectura y otra de escritura. En s7 se lee RAM(i,j) y en el mismo flanco se "
         "escribe tmp1 en esa posición; por eso el intercambio usa tres estados por columna."),
        ("asm_hoja3", "Hoja 3: productos, resta e inicio de la división (s10 a s15)",
         "Con un solo multiplicador, los dos productos se hacen en estados distintos. La ALU calcula t1 − t2 en s14 y "
         "0 − t3 en s15, para que el residuo empiece con |t3|."),
        ("asm_hoja4", "Hoja 4: división, escritura de a(i,j), avance y determinante (s16 a s19)",
         "s16 es el lazo de la división por restas sucesivas: en cada ciclo la ALU calcula residuo − |p|; si no es "
         "negativo se guarda y el cociente aumenta. En s17 la ALU calcula 0 − cociente para escribir el valor con signo. "
         "s19 guarda el determinante como último pivote."),
        ("asm_hoja5", "Hoja 5: algoritmo XS3 integrado y final (s20 a s26)",
         "El XS3 convierte primero |det| y luego |pivote(dir_p)|, con un estado por paso del documento. En s23 la ALU "
         "calcula dígito + 3. En s26 el ASM espera con final = 1; si cambia dir_p vuelve a s20 y convierte el nuevo pivote."),
    ]
    for i, (fig, titulo, texto) in enumerate(hojas, start=1):
        A(PageBreak())
        A(P(titulo, "h2"))
        A(P(texto))
        A(figura(fig, f"Figura {5 + i}. {titulo}.", max_alto=7.9))

    descripciones = [
        ("s0", "final = 0; dira ← 0", "inicio = 1: s1. Si no: s0."),
        ("s1", "n ← a (ROM 00h); dira ← 1; i ← 1; j ← 1", "s2"),
        ("s2", "RAM(i,j) ← a (con extensión de signo); dira ← dira + 1",
               "i ≠ n: i ← i + 1, s2. i = n y j ≠ n: i ← 1, j ← j + 1, s2. i = n y j = n: s3."),
        ("s3", "k ← 1; p ← 1; |p| ← 1; signo ← 0; conv_piv ← 0; banco ← 0 (clr_banco)", "s4"),
        ("s4", "piv ← RAM(k,k)", "RAM(k,k) = 0: i ← k + 1, s5. Si no: s9."),
        ("s5", "Lee RAM(i,k)", "RAM(i,k) ≠ 0: j ← k, signo ← not signo, s6. RAM(i,k) = 0 e i = n: det_bin ← 0, s20. "
               "Si no: i ← i + 1, s5."),
        ("s6", "tmp1 ← RAM(k,j)", "s7"),
        ("s7", "tmp2 ← RAM(i,j); RAM(i,j) ← tmp1", "s8"),
        ("s8", "RAM(k,j) ← tmp2", "j = n: s4. Si no: j ← j + 1, s6."),
        ("s9", "banco(k) ← piv; i ← k + 1; j ← k + 1", "s10"),
        ("s10", "mul_a ← piv; mul_b ← RAM(i,j)", "s11"),
        ("s11", "t1 ← producto; mul_a ← RAM(i,k)", "s12"),
        ("s12", "mul_b ← RAM(k,j)", "s13"),
        ("s13", "t2 ← producto", "s14"),
        ("s14", "t3 ← t1 − t2 (ALU)", "s15"),
        ("s15", "cociente ← 0; sq ← signo(t3) xor signo(p); residuo ← |t3| (ALU: 0 − t3 si t3 < 0)", "s16"),
        ("s16", "ALU: residuo − |p|", "residuo − |p| ≥ 0: residuo ← residuo − |p|, cociente ← cociente + 1, s16. Si no: s17."),
        ("s17", "RAM(i,j) ← cociente, o 0 − cociente (ALU) si sq = 1",
                "j ≠ n: j ← j + 1, s10. j = n e i ≠ n: i ← i + 1, j ← k + 1, s10. i = n y j = n: s18."),
        ("s18", "p ← piv; |p| ← |piv| (ALU: 0 − piv si piv < 0); k ← k + 1", "k + 1 = n: s19. Si no: s4."),
        ("s19", "det_bin ← ±RAM(n,n); banco(n) ← ±RAM(n,n) (ALU: 0 − RAM(n,n) si signo = 1)", "s20"),
        ("s20", "val = det_bin si conv_piv = 0, banco(dir_p) si conv_piv = 1; neg ← signo(val); dir_ant ← dir_p; "
                "bin ← |val| (ALU: 0 − val si val < 0)", "s21"),
        ("s21", "XS3 paso 1: BCD ← 0; cont ← 0", "s22"),
        ("s22", "XS3 paso 2: BCD(0) ← bin(31)", "cont = 31: s25 (paso 5 cumplido). Si no: d ← 0, s23."),
        ("s23", "XS3 paso 3: ALU dígito(d) + 3; si dígito(d) > 4, dígito(d) ← dígito(d) + 3",
                "d ≠ 9: d ← d + 1, s23. d = 9: s24."),
        ("s24", "XS3 paso 4: BCD ← BCD << 1; bin ← bin << 1; cont ← cont + 1", "s22"),
        ("s25", "Guarda el resultado del XS3", "conv_piv = 0: det ← BCD, det_neg ← neg, conv_piv ← 1, s20. "
                "conv_piv = 1: pivote ← BCD, piv_neg ← neg, s26."),
        ("s26", "final = 1; dira ← 0", "inicio = 1: s1. dir_p ≠ dir_ant: s20. Si no: s26."),
    ]
    A(PageBreak())
    A(P("Tabla de estados", "h2"))
    A(P("Resumen de cada bloque ASM, en el orden del archivo src/asm_bareiss.vhd."))
    A(tabla([["Estado", "Operaciones", "Siguiente estado"]] + [list(d) for d in descripciones], [0.6, 3.3, 3.0]))

    # 8 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("8. Algoritmo XS3 dentro del ASM", "h1"))
    A(P("El XS3 no es un bloque externo: sus pasos son estados del mismo ASM de Bareiss y su suma (+3) se hace en la "
        "ALU del procesador. Sus registros (binario, decimal y contadores) están en el ASM. Cada paso del documento "
        "XS3 tiene su estado:"))
    A(tabla([
        ["Paso del documento XS3", "Estado", "Operación"],
        ["1. Inicializar el registro decimal en ceros", "s21", "BCD ← 0 (40 bits); cont ← 0"],
        ["2. Colocar el MSB del registro binario en el LSB del registro decimal", "s22", "BCD(0) ← bin(31)"],
        ["3. Revisar cada dígito: si es ≥ 5 (> 0100), sumarle 3 (0011)", "s23",
         "Un dígito por ciclo (d = 0 a 9): un multiplexor entrega el dígito d, la ALU calcula dígito + 3 (A + B) y, "
         "si el dígito es > 4, se reemplaza por el resultado."],
        ["4. Correr a la izquierda y descartar el bit que sale; repetir desde el paso 2", "s24",
         "BCD ← BCD(38..0) & '0'; bin ← bin(30..0) & '0'; cont ← cont + 1; vuelve a s22"],
        ["5. Realizar únicamente el paso 2", "s22 con cont = 31",
         "En la pasada 32 por s22 entra el último bit y el ASM va a s25."],
    ], [2.6, 0.9, 3.4]))
    A(Spacer(1, 6))
    A(P("Por qué se suma 3: si un dígito vale 5 o más, al correrlo a la izquierda quedaría en 10 o más, que no es un "
        "dígito BCD válido. Sumar 3 antes del corrimiento equivale a sumar 6 después, que es la corrección BCD, y "
        "hace que el exceso pase como acarreo al dígito siguiente. El registro binario es de 32 bits, así que el "
        "decimal necesita 10 dígitos (2[sup]32[/sup] − 1 = 4 294 967 295) y hay 32 pasadas por el paso 2. El signo no "
        "entra al XS3: en s20 se carga |valor| en bin y el signo en neg."))
    A(P("Traza del XS3 para 362", "h2"))
    A(P("362 = 1 0110 1010[sub]2[/sub] tiene 9 bits significativos. En las pasadas cont = 0 a 22 solo entran ceros, por "
        "eso la tabla empieza en cont = 23. «bin(31..23)» son los 9 bits de arriba del registro binario; el de la "
        "izquierda, bin(31), es el que copia el paso 2. El registro decimal se muestra con sus tres dígitos bajos."))
    filas, bcd_fin = traza_xs3(362)
    cambio = {"S23 (2)": "s22 (2)", "S24 (3)": "s23 (3)", "S25 (4)": "s24 (4)"}
    filas = [[cambio.get(c, c).replace("va a S26", "va a s25") for c in f] for f in filas]
    A(tabla([["cont", "Estado (paso)", "BCD: C D U", "bin(31..23)", "Comentario"]] + filas,
            [0.45, 0.85, 1.25, 0.95, 3.4]))
    A(Spacer(1, 4))
    A(P(f"Resultado: BCD = {bcd_fin[2]:04b} {bcd_fin[1]:04b} {bcd_fin[0]:04b} = {bcd_fin[2]} {bcd_fin[1]} {bcd_fin[0]}."))

    # 9 -----------------------------------------------------------------------
    A(P("9. División por restas sucesivas", "h1"))
    A(P("La división también está dentro del ASM y usa la ALU. Divide magnitudes: residuo = |t3| y divisor = |p|; el "
        "signo del resultado (sq = signo(t3) xor signo(p)) se aplica al escribir en la RAM."))
    V(viñetas([
        "s15: cociente ← 0; residuo ← |t3| (la ALU calcula 0 − t3 si t3 es negativo).",
        "s16: la ALU calcula residuo − |p|. Si el resultado no es negativo (bit 49 = 0), residuo ← resultado y "
        "cociente ← cociente + 1, y el ASM se queda en s16. Si es negativo, pasa a s17.",
        "s17: RAM(i,j) ← cociente, o 0 − cociente (en la ALU) si sq = 1.",
    ]))
    A(P("Tarda |cociente| + 1 ciclos en s16. Como la división de Bareiss es exacta, al salir el residuo es 0."))

    # 10 ----------------------------------------------------------------------
    A(PageBreak())
    A(P("10. Señales del ASM", "h1"))
    A(P("10.1 Señales de control por estado (ASM → bloques)", "h2"))
    A(P("Son asignaciones concurrentes de src/asm_bareiss.vhd que dependen del estado. Los estados que no aparecen "
        "no usan estos bloques."))
    A(tabla([
        ["Estado", "RAM (lectura / escritura)", "ALU (M s1 s0 = op)", "Otros bloques"],
        ["s2", "escribe (i,j) ← a", "—", "ROM: dira"],
        ["s3", "—", "—", "banco: clr_banco = 1"],
        ["s4", "lee (k,k)", "—", "—"],
        ["s5", "lee (i,k)", "—", "—"],
        ["s6", "lee (k,j)", "—", "—"],
        ["s7", "lee (i,j); escribe (i,j) ← tmp1", "—", "—"],
        ["s8", "escribe (k,j) ← tmp2", "—", "—"],
        ["s9", "—", "—", "banco: we_banco, dir_banco = k, dato = piv"],
        ["s10", "lee (i,j)", "—", "multiplicador: carga mul_a, mul_b"],
        ["s11", "lee (i,k)", "—", "multiplicador: t1 ← producto"],
        ["s12", "lee (k,j)", "—", "—"],
        ["s13", "—", "—", "multiplicador: t2 ← producto"],
        ["s14", "—", "110: t1 − t2", "—"],
        ["s15", "—", "110: 0 − t3", "—"],
        ["s16", "—", "110: residuo − |p|", "—"],
        ["s17", "escribe (i,j) ← ±cociente", "110: 0 − cociente", "—"],
        ["s18", "—", "110: 0 − piv", "—"],
        ["s19", "lee (n,n)", "110: 0 − RAM(n,n)", "banco: we_banco, dir_banco = n, dato = ±RAM(n,n)"],
        ["s20", "—", "110: 0 − val", "—"],
        ["s23", "—", "101: dígito + 3", "—"],
        ["s26", "—", "—", "final = 1"],
    ], [0.55, 2.2, 1.55, 2.6]))
    A(P("10.2 Señales de estado (bloques → ASM)", "h2"))
    A(tabla([
        ["Señal", "Origen", "Se pregunta en"],
        ["inicio", "Pulso del antirrebote", "s0, s26"],
        ["RAM(k,k) = 0, RAM(i,k) = 0", "Comparador de q con 0", "s4, s5"],
        ["i = n, j = n", "Comparadores de 3 bits", "s2, s5, s8, s17"],
        ["k + 1 = n", "Contador k y comparador", "s18"],
        ["signo(t3) = t3(49)", "Registro t3", "s15"],
        ["resultado(49)", "Signo de la salida de la ALU (residuo − |p| < 0)", "s16"],
        ["sq", "Registro del signo del cociente", "s17"],
        ["signo(piv) = piv(31)", "Registro piv", "s18"],
        ["signo", "Registro de paridad de intercambios", "s19"],
        ["signo(val) = val(31)", "Multiplexor val", "s20"],
        ["cont = 31", "Contador cont", "s22"],
        ["dígito(d) > 4", "Comparador de 4 bits a la salida del multiplexor de dígitos", "s23"],
        ["d = 9", "Contador d", "s23"],
        ["conv_piv", "Registro: 0 = convierte det, 1 = convierte pivote", "s20, s25"],
        ["dir_p ≠ dir_ant", "Comparador de 3 bits", "s26"],
    ], [2.1, 2.9, 1.9]))
    A(P("10.3 Registros del ASM y anchos", "h2"))
    A(tabla([
        ["Registro", "Bits", "Uso"],
        ["st", "5 (27 estados)", "Estado del ASM"],
        ["dira_r", "5", "Contador de dirección de la ROM"],
        ["n, i, j, k", "3 c/u", "Tamaño de la matriz y contadores de fila, columna y paso"],
        ["piv, p, pabs", "32 c/u", "Pivote actual, pivote anterior y |p| (divisor)"],
        ["tmp1, tmp2", "32 c/u", "Intercambio de filas"],
        ["mul_a, mul_b", "25 c/u", "Entradas del multiplicador"],
        ["t1, t2, t3", "50 c/u", "Productos y numerador de la fórmula (1)"],
        ["residuo, cociente", "50, 32", "División por restas sucesivas (cociente es un contador)"],
        ["sq, signo, conv_piv, neg", "1 c/u", "Signo del cociente, paridad de intercambios, qué se convierte, signo convertido"],
        ["det_bin", "32", "Determinante en binario"],
        ["bin, BCD", "32, 40", "Registros binario y decimal del XS3"],
        ["cont, d", "5, 4", "Contadores del XS3: bits procesados y dígito revisado"],
        ["dir_ant", "3", "dir_p ya convertido"],
        ["det, pivote", "40 c/u", "Salidas en BCD"],
    ], [1.8, 1.1, 4.0]))
    A(P("Los contadores (dira, i, j, k, cociente, cont, d) son registros que se incrementan; las operaciones sobre los "
        "datos de la matriz y del XS3 pasan por la ALU."))
    A(P("Por la identidad de Sylvester, cada valor de la RAM es el determinante de una submatriz de A, y la desigualdad "
        "de Hadamard lo acota: |det| ≤ (32·√m)[sup]m[/sup] para una submatriz m×m."))
    V(viñetas([
        "Operandos del multiplicador: submatrices de hasta 4×4, |x| < 2[sup]24[/sup]. Caben en 25 bits con signo.",
        "Determinante 5×5: |det| ≤ 1,88 × 10[sup]9[/sup] < 2[sup]31[/sup]. RAM, det_bin, cociente y bin son de 32 bits.",
        "Numerador: |t3| ≤ 3,2 × 10[sup]14[/sup] < 2[sup]49[/sup]. t1, t2, t3, residuo y la ALU son de 50 bits.",
        "BCD: 32 bits binarios necesitan 10 dígitos. El display muestra 7 y LD1 avisa si hay más.",
    ]))

    # 11 ----------------------------------------------------------------------
    A(PageBreak())
    A(P("11. Interfaz con la tarjeta", "h1"))
    A(P("Divisor de frecuencia", "h2"))
    A(P("El oscilador de la Nexys A7 es de 100 MHz (pin E3, sección 5 del manual de la tarjeta). El bloque "
        "[c]divisor_frecuencia[/c] genera un pulso de un ciclo cada 1 ms (cuenta 100 000 ciclos) y una onda cuadrada "
        "de periodo 1 s (cambia cada 500 ms) que se ve en LD15. Los pulsos se usan como habilitación: todo el diseño "
        "trabaja con el mismo reloj, sin relojes derivados."))
    A(P("El procesador trabaja a 100 MHz y no usa el divisor. Con un reloj de 1 s, la matriz 3×3 de prueba (822 ciclos) "
        "tardaría unos 14 minutos y la 5×5 (4 583 ciclos) más de una hora."))
    A(P("Antirrebote (uno solo)", "h2"))
    A(P("El diseño tiene un solo antirrebote, para el botón de inicio. El bloque [c]antirrebote[/c] sincroniza el botón "
        "con dos flip-flops, lo muestrea cada 1 ms en un registro de 8 bits y cambia su nivel estable solo con 8 "
        "muestras iguales (8 ms sin rebote). Entrega un pulso de un ciclo en el flanco de subida del nivel estable, "
        "así una pulsación arranca un solo cálculo."))
    A(P("Sincronizador y display", "h2"))
    A(P("Los switches dir_p no llevan antirrebote: el bloque [c]sincronizador[/c] solo los pasa por dos flip-flops "
        "para evitar metaestabilidad. El bloque [c]display_8dig[/c] cambia de dígito con cada pulso de 1 ms (barrido "
        "de 8 ms, 125 Hz): AN7 muestra el signo y AN6..AN0 los 7 dígitos. En el tope, un multiplexor elige det si "
        "dir_p = 0 y pivote si dir_p = 1 a 5, y LD1 se enciende si los dígitos 7 a 9 del valor mostrado no son cero."))

    # 12 ----------------------------------------------------------------------
    A(P("12. Tiempo de ejecución", "h1"))
    V(viñetas([
        "Carga de la matriz (s0 a s3): n² + 3 ciclos.",
        "Por cada elemento actualizado: s10 a s15 y s17 (7 ciclos) más |cociente| + 1 ciclos de división en s16.",
        "XS3: unos 375 ciclos por conversión (s20 a s25). Al terminar el cálculo se hacen dos (det y pivote).",
    ]))
    A(P("La división por restas sucesivas domina el tiempo cuando los valores son grandes. Las matrices de prueba "
        "terminan en menos de 50 µs, salvo la matriz 7 (valores cercanos a ±32), que tarda 19 millones de ciclos "
        "(0,19 s). Con los valores de la clase («del orden de cientos de miles») el tiempo es de microsegundos."))

    # 13 ----------------------------------------------------------------------
    A(P("13. Implementación en ISE 14.7 y la Nexys A7", "h1"))
    A(P("13.1 Proyecto", "h2"))
    V(viñetas([
        "File → New Project. Top-level source type: HDL. Family: Artix7 · Device: XC7A100T · Package: CSG324 · "
        "Speed: −1 · Synthesis: XST · Simulator: ISim · Preferred language: VHDL. ISE solo soporta la Nexys A7-100T.",
        "Add Source: todos los .vhd de src/ y src/nexys_a7.ucf (Implementation); sim/pkg_prueba.vhd y los testbench "
        "de sim/ (Simulation). Si ISE no elige det_bareiss como tope, usen «Set as Top Module».",
        "Synthesize (View RTL Schematic muestra los bloques) → Implement Design → Generate Programming File. Revisen "
        "que se cumpla la restricción de 10 ns (TS_sys_clk).",
        "Programación: la Nexys A7 no funciona con Digilent Adept. Usen iMPACT de ISE o el Hardware Manager de Vivado "
        "(Lab Edition) con el archivo .bit.",
    ]))
    A(P("13.2 Cambiar la matriz (día de la evaluación)", "h2"))
    V(viñetas([
        "Opción 1: editar src/rom_matriz.vhd. La línea de 00h es n; las siguientes son a11, a21, …, an1, a12, … en "
        "complemento a 2 de 6 bits.",
        "Opción 2: [c]python3 sim/modelo_referencia.py rom \"2 1 3; 1 4 2; 3 2 5\"[/c] escribe el archivo e imprime el "
        "determinante y los pivotes esperados.",
        "Simular con sim/tb_procesador.vhd: lee la ROM, calcula los valores esperados y los compara, sin modificar el "
        "testbench.",
        "Sintetizar y volver a programar la FPGA.",
    ]))
    A(P("13.3 Operación en la tarjeta", "h2"))
    V(viñetas([
        "Pulsar BTNU (rst). Poner SW2..SW0 en 000.",
        "Pulsar BTNC (inicio). Cuando termina, LD0 (final) se enciende y el display muestra el determinante.",
        "Poner SW2..SW0 en 1 a n para ver el pivote k; con k = n se ve otra vez el determinante.",
        "Si LD1 está encendido, el valor tiene más de 7 dígitos y se ven los 7 de abajo. LD15 parpadea cada segundo.",
    ]))
    A(P("13.4 Matrices de prueba", "h2"))
    filas = [["#", "n", "Matriz A", "det", "Pivotes (dir_p = 1..n)", "Qué prueba"]]
    queprueba = ["Caso básico 2×2", "Ejemplo del documento", "a11 = 0: intercambio en k = 1",
                 "5×5 general (ROM por defecto)", "Pivote negativo; intercambio en k = 2",
                 "Pivote cero en k = 2 (p ≠ 1)", "Columna 1 en cero: singular",
                 "Valores extremos; desborde del display"]
    for num, a in enumerate(MATRICES):
        d, piv, _ = bareiss(a)
        filas.append([str(num), str(len(a)), mat_txt(a), f"{d:,}".replace(",", " "),
                      ", ".join(str(x) for x in piv), queprueba[num]])
    A(tabla(filas, [0.3, 0.25, 1.95, 0.85, 1.65, 1.9]))
    A(P(f"src/rom_matriz.vhd trae la matriz {MATRIZ_POR_DEFECTO}. Para cargar otra de la lista: "
        "[c]python3 sim/modelo_referencia.py rom <número>[/c]."))
    A(P("13.5 Pines (src/nexys_a7.ucf)", "h2"))
    A(tabla([
        ["Señal", "Pines"],
        ["clk", "E3 (100 MHz)"],
        ["rst / inicio", "M18 (BTNU) / N17 (BTNC)"],
        ["dir_p(0..2)", "J15 (SW0), L16 (SW1), M13 (SW2)"],
        ["final / desborde / latido", "H17 (LD0) / K15 (LD1) / V11 (LD15)"],
        ["seg(0..6) = CA..CG, dp", "T10, R10, K16, K13, P15, T11, L18; DP = H15"],
        ["an(0..7)", "J17, J18, T9, J14, P14, T14, K2, U13"],
    ], [1.9, 5.0]))

    # 14 ----------------------------------------------------------------------
    A(P("14. Simulación", "h1"))
    V(viñetas([
        "[b]sim/tb_alu.vhd[/b] prueba las 8 operaciones de la ALU con valores positivos, negativos y extremos.",
        "[b]sim/tb_procesador.vhd[/b] (con sim/pkg_prueba.vhd) lee la matriz de la ROM, calcula el determinante y los "
        "pivotes esperados con un modelo de Bareiss en VHDL, pulsa inicio, compara det, recorre dir_p = 1 a n "
        "comparando cada pivote, comprueba que el pivote n sea el det y repite todo con un segundo inicio.",
        "[b]sim/probar_matrices.py[/b] escribe cada una de las 8 matrices de prueba en una ROM temporal y corre ese "
        "testbench con GHDL.",
        "[b]sim/tb_det_bareiss.vhd[/b] prueba la tarjeta completa con tiempos reales: pulsa BTNC con rebotes, comprueba "
        "que hay un solo cálculo y lee los 8 dígitos decodificando an y seg con dir_p = 0, 2 y n.",
    ]))
    res = resultados_sim()
    filas = [["#", "n", "det esperado", "det del procesador", "Ciclos hasta final", "Resultado"]]
    for num, a in enumerate(MATRICES):
        d, _, _ = bareiss(a)
        ciclos, det_hw = res[num]
        esperado = ("-" if d < 0 else " ") + str(abs(d)).zfill(10)
        filas.append([str(num), str(len(a)), f"[c]'{esperado}'[/c]".replace(" ", "\u00a0"),
                      f"[c]'{det_hw}'[/c]".replace(" ", "\u00a0"), f"{ciclos:,}".replace(",", " "),
                      "OK" if det_hw == esperado else "ERROR"])
    A(tabla(filas, [0.3, 0.3, 1.55, 1.55, 1.35, 0.9]))
    A(Spacer(1, 4))
    A(P("Todos los pivotes también coinciden con el modelo, y en la prueba de la tarjeta el display mostró "
        f"«{texto_display(bareiss(MATRICES[MATRIZ_POR_DEFECTO])[0])}» con un solo cálculo después de la pulsación con "
        "rebotes (ver sim/resultado_ghdl.txt). Para comprobar que las pruebas detectan errores se probaron tres fallas "
        "en una copia del diseño: el XS3 sumando 2 en lugar de 3, el último pivote sin el signo de los intercambios "
        "(matriz 2) y la resta de la ALU sin el acarreo de entrada. Las tres se detectaron."))

    # 15 ----------------------------------------------------------------------
    A(P("15. Limitaciones y verificación pendiente", "h1"))
    V(viñetas([
        "[b]No se ejecutó ISE.[/b] El diseño se verificó con GHDL 4.1 (simulación con [c]-fsynopsys -fexplicit[/c] y "
        "síntesis genérica). Hay que sintetizar en ISE 14.7 y revisar el reporte de tiempos a 100 MHz. El camino más "
        "largo pasa por la ALU de 50 bits; si no se cumplen los 10 ns, generen un reloj de 50 MHz con el Clocking "
        "Wizard y pongan PERIOD = 20 ns.",
        "[b]Contadores.[/b] Los índices (dira, i, j, k), el cociente y los contadores del XS3 (cont, d) son contadores "
        "propios; no pasan por la ALU. Si el profesor quiere que también usen la ALU (A + 1), cada incremento necesita "
        "un estado más.",
        "[b]Multiplicador.[/b] Es una unidad aparte, combinacional, que usa el paquete [c]std_logic_signed[/c] sobre "
        "std_logic_vector (no el tipo signed). Si el profesor quiere un multiplicador por sumas y desplazamientos que "
        "use la ALU, hay que cambiarlo.",
        "[b]Salidas en BCD.[/b] det y pivote salen del procesador ya convertidos por el XS3. Si el profesor las quiere "
        "en binario, los valores existen dentro del ASM (det_bin y el banco).",
        "[b]RAM.[/b] Es el modelo del curso con 64 palabras en lugar de 32 y contenido inicial en cero.",
        "[b]Display de 7 dígitos.[/b] Valores hasta ±9 999 999; para valores mayores se enciende LD1.",
        "[b]Valor de n.[/b] El diseño supone 2 ≤ n ≤ 5 en la ROM y no lo valida.",
    ]))

    # Anexo -------------------------------------------------------------------
    A(PageBreak())
    A(P("Anexo A. Código VHDL", "h1"))
    for nombre in ARCHIVOS_VHDL:
        texto = (RAIZ / "src" / nombre).read_text(encoding="utf-8")
        A(P(f"src/{nombre}", "h2_anexo"))
        numeradas = "\n".join(f"{n:4d}  {l}" for n, l in enumerate(texto.splitlines(), start=1))
        A(Preformatted(numeradas, E["anexo"]))
    return h

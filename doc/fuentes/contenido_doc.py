"""Contenido del PDF del Taller 5 (procesador estructural con ASM de alto nivel).

Lo importa generar_pdf.py.  Los resultados de simulacion se leen de
sim/resultado_ghdl.txt y la tabla de matrices de sim/modelo_referencia.py.
"""
import re

from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Preformatted, Spacer, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents

from generar_pdf import E, P, RAIZ, codigo, figura, tabla, traza_xs3, viñetas
from modelo_referencia import MATRICES, MATRIZ_POR_DEFECTO, bareiss, texto_display

from reportlab.lib.styles import ParagraphStyle

E["h2_anexo"] = ParagraphStyle("h2_anexo", parent=E["h2"])   # no aparece en el indice

ARCHIVOS_VHDL = ["det_bareiss.vhd", "procesador.vhd", "asm_bareiss.vhd", "bloque_division.vhd",
                 "xs3.vhd", "banco_pivotes.vhd", "sumador_restador.vhd", "multiplicador.vhd",
                 "ram.vhd", "rom_matriz.vhd", "divisor_frecuencia.vhd", "antirrebote.vhd",
                 "sincronizador.vhd", "display_8dig.vhd"]


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
    A(P("Caja negra, cajas grises, pseudoalgoritmo, diagramas ASM y código VHDL", "subtitulo"))
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
    A(P("Siguiendo la clase del 9 de noviembre, el diseño es un híbrido entre un camino de datos estructural y un ASM "
        "de alto nivel. Los bloques principales (ROM, RAM, multiplicador, sumador/restador, división, XS3 y banco de "
        "pivotes) están descritos aparte e interconectados en la entidad [c]procesador[/c]. El ASM principal "
        "([c]asm_bareiss[/c], 22 estados) se encarga del direccionamiento y de distribuir las señales a esos bloques. "
        "La división y el XS3 tienen cada uno su propia unidad de control y su propio camino de datos."))
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
         "No hay [c]variable[/c] ni lazos [c]for[/c]/[c]while[/c]. Las repeticiones del algoritmo las hacen los ASM, "
         "un paso por ciclo de reloj, con contadores."],
        ["Sintetizable y con esquemático RTL claro",
         "Un archivo por bloque y entidades estructurales ([c]procesador[/c], [c]det_bareiss[/c]) que solo conectan "
         "bloques. La síntesis genérica con GHDL termina sin errores ni latches."],
        ["Un solo multiplicador y un solo sumador/restador",
         "Entidades [c]multiplicador[/c] y [c]sumador_restador[/c], compartidas por los estados del ASM principal "
         "mediante multiplexores. El bloque de división tiene su restador propio (es el «bloque de división» del "
         "enunciado) y el XS3 su sumador de 4 bits (+3)."],
        ["Solo para simulación", "Los testbench usan variables, integer, real, string y wait; no se sintetizan."],
    ], [1.9, 5.0]))
    A(P("Requisitos del enunciado y de la clase", "h2"))
    A(tabla([
        ["Requisito", "Cómo lo cumple el diseño"],
        ["Señal de inicio y señal de final", "Entradas y salidas del procesador; [c]final = '1'[/c] en el estado s21."],
        ["Matriz en ROM: 00h = n, luego los a(i,j) como en la Figura 1",
         "Entidad [c]rom_matriz[/c] (src/rom_matriz.vhd): dirección [c]dira[/c] de 5 bits y dato [c]a[/c] de 6 bits en "
         "complemento a 2. Elementos por columnas: a11, a21, …, an1, a12, …"],
        ["La ROM hace parte de la arquitectura", "La ROM está dentro del procesador; no se ingresa por puertos."],
        ["Multiplicador, sumador/restador y división por restas sucesivas",
         "Entidades [c]multiplicador[/c], [c]sumador_restador[/c] y [c]bloque_division[/c]."],
        ["Memoria RAM para las iteraciones", "Entidad [c]RAM_memory[/c] (modelo del curso), 64 × 32 bits."],
        ["Pivotes en un banco de registros, visibles con los switches",
         "Entidad [c]banco_pivotes[/c]. dir_p = k (SW2..SW0) elige el pivote; el último pivote (k = n) es el determinante."],
        ["Determinante en los displays, en decimal", "Salida [c]det[/c] en BCD; con dir_p = 0 el display muestra det."],
        ["Bloque XS3 con su unidad de control y su camino de datos",
         "Entidad [c]xs3[/c]: ASM de 6 estados, un estado por cada paso del documento XS3."],
        ["Antirrebote solo para el botón de inicio", "Entidad [c]antirrebote[/c] (src/antirrebote.vhd)."],
    ], [2.2, 4.7]))
    A(KeepTogether([P("Archivos del repositorio", "h2"), tabla([
        ["Archivo", "Contenido"],
        ["src/det_bareiss.vhd", "Tope para la Nexys A7 (estructural)."],
        ["src/procesador.vhd", "Procesador: une el ASM con sus bloques (estructural)."],
        ["src/asm_bareiss.vhd", "ASM principal (s0 a s21)."],
        ["src/bloque_division.vhd, src/xs3.vhd", "Bloques con ASM propio: división por restas sucesivas y XS3."],
        ["src/rom_matriz.vhd, src/ram.vhd, src/banco_pivotes.vhd", "ROM con la matriz, RAM (modelo del curso), banco de pivotes."],
        ["src/multiplicador.vhd, src/sumador_restador.vhd", "Unidades aritméticas."],
        ["src/divisor_frecuencia.vhd, src/antirrebote.vhd, src/sincronizador.vhd, src/display_8dig.vhd",
         "Interfaz con la tarjeta."],
        ["src/nexys_a7.ucf", "Pines y restricción de reloj (100 MHz)."],
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
        "ROM, la RAM, la división y el XS3 están adentro. Es la entidad [c]procesador[/c]."))
    A(figura("caja_negra", "Figura 1. Caja negra del procesador.", max_ancho=5.8))
    A(tabla([
        ["Puerto", "Dir.", "Bits", "Función"],
        ["clk", "in", "1", "Reloj (100 MHz en la tarjeta)"],
        ["rst", "in", "1", "Reinicio asíncrono, activo en alto"],
        ["inicio", "in", "1", "Comienza el cálculo (pulso de un ciclo; se lee en s0 y s21)"],
        ["dir_p", "in", "3", "Dirección del banco de pivotes: 1 a n = pivote k (el n es el det); 0, 6 y 7 leen 0"],
        ["det, det_neg", "out", "40, 1", "|det| en BCD (10 dígitos) y su signo"],
        ["pivote, piv_neg", "out", "40, 1", "|pivote(dir_p)| en BCD y su signo"],
        ["final", "out", "1", "'1' cuando det y pivote están listos (estado s21)"],
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
        "unidad de control. La caja gris del procesador muestra el ASM principal y los bloques del camino de datos "
        "con todas sus señales."))
    A(figura("cajas_grises", "Figura 2. Caja gris del procesador: unidad de control (ASM) y bloques del camino de datos.",
             max_alto=6.0))
    A(tabla([
        ["Bloque", "Entradas desde el ASM", "Salidas hacia el ASM", "Uso"],
        ["ROM (rom_matriz)", "dira (5)", "a (6)", "Leer n y los elementos (s1, s2)"],
        ["RAM (RAM_memory)", "rd_add (6), wr_add (6), we, data (32)", "q (32)", "Matriz de trabajo; dirección fila & columna"],
        ["multiplicador", "mul_a (25), mul_b (25)", "producto (50)", "a(k,k)·a(i,j) y a(i,k)·a(k,j)"],
        ["sumador_restador", "sr_a (50), sr_b (50), sr_op", "resultado (50)", "t1 − t2 y las negaciones 0 − x"],
        ["bloque_division", "ini_div, dividendo (50), divisor (32)", "cociente (32), fin_div", "|t3| / |p| por restas sucesivas"],
        ["xs3", "ini_xs3, bin_xs3 (32)", "bcd_xs3 (40), fin_xs3", "Convertir |det| y |pivote| a BCD"],
        ["banco_pivotes", "clr_banco, we_banco, dir_banco (3), dato_banco (32)", "piv_banco (32)",
         "Guardar los pivotes; se lee con dir_p"],
    ], [1.35, 2.2, 1.45, 1.9]))
    A(P("Cajas grises de los bloques con ASM propio", "h2"))
    A(P("La división y el XS3 son pequeños procesadores: cada uno tiene una unidad de control y un camino de datos, y "
        "se comunican con el ASM principal con un protocolo inicio / final. El ASM principal activa [c]ini_div[/c] o "
        "[c]ini_xs3[/c] durante un ciclo y espera [c]fin_div[/c] o [c]fin_xs3[/c]."))
    A(figura("grises_bloques", "Figura 3. Cajas grises del bloque XS3 y del bloque de división.", max_alto=3.2))
    A(P("Tope de la tarjeta", "h2"))
    A(figura("tope", "Figura 4. Bloques del tope det_bareiss.", max_alto=2.6))

    # 5 -----------------------------------------------------------------------
    A(P("5. Pseudoalgoritmo con el hardware disponible", "h1"))
    A(P("Cada línea indica el estado del ASM principal que la ejecuta. Las operaciones del mismo estado ocurren en el "
        "mismo ciclo de reloj. «RAM(f,c)» es la palabra de la RAM en la dirección fila f, columna c."))
    A(codigo(
        "s0 :  final = 0;  esperar inicio = 1\n"
        "s1 :  n = ROM(00h)\n"
        "s2 :  para j = 1..n, i = 1..n:  RAM(i,j) = ROM(dira);  dira = dira + 1     (por columnas)\n"
        "s3 :  k = 1;  p = 1;  |p| = 1;  signo = 0;  conv_piv = 0;  banco = 0\n"
        "mientras k <= n-1:\n"
        "  s4 :  piv = RAM(k,k)\n"
        "        si piv = 0:\n"
        "  s5 :     buscar i = k+1..n con RAM(i,k) /= 0;  si no existe: det_bin = 0, ir a CONVERTIR\n"
        "  s6-s8:   intercambiar filas k e i (columnas k..n);  signo = not signo;  volver a s4\n"
        "  s9 :  banco(k) = piv\n"
        "        para i = k+1..n, j = k+1..n:\n"
        "  s10-s13:  t1 = piv · RAM(i,j);   t2 = RAM(i,k) · RAM(k,j)      (multiplicador)\n"
        "  s14:      t3 = t1 - t2                                       (sumador/restador)\n"
        "  s15-s16:  cociente = |t3| / |p|                              (bloque de división)\n"
        "            RAM(i,j) = +cociente o -cociente  (signo(t3) xor signo(p))\n"
        "  s17:  p = piv;  |p| = |piv|;  k = k + 1\n"
        "s18:  det_bin = RAM(n,n) o -RAM(n,n) (según signo);  banco(n) = det_bin\n"
        "CONVERTIR (dos veces: conv_piv = 0 para det, conv_piv = 1 para el pivote):\n"
        "s19-s20:  BCD = XS3(|val|)  con val = det_bin o banco(dir_p)       (bloque XS3)\n"
        "          si conv_piv = 0:  det = BCD;  conv_piv = 1;  repetir CONVERTIR\n"
        "          si no:            pivote = BCD\n"
        "s21:  final = 1;  si inicio = 1 ir a s1;  si cambia dir_p ir a CONVERTIR"))
    A(P("Los «para» y «mientras» no son lazos del VHDL: cada uno es un lazo del ASM que vuelve a un estado mientras "
        "un contador no llegue a su límite."))

    # 6 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("6. Diagrama ASM principal", "h1"))
    A(P("Convenciones", "h2"))
    A(tabla([
        ["Elemento", "Significado"],
        ["Caja de estado (rectángulo azul)", "Operaciones de todo el estado (salidas tipo Moore)."],
        ["Caja de decisión (rombo)", "Pregunta sobre una señal de estado. La salida 1 es la condición verdadera."],
        ["Caja de salida condicional (rectángulo redondeado naranja)",
         "Operación que solo ocurre si se toma ese camino (tipo Mealy), como en el ejemplo «ASM Mealy» de clase."],
        ["Bloque ASM (recuadro punteado)", "Caja de estado más sus decisiones y salidas condicionales: dura un ciclo de reloj."],
        ["Conector (círculo verde)", "Une hojas del diagrama: A → s1, B → s4, C → s10, D → s19, E → s16."],
        ["x ← expresión", "Carga de un registro; se hace efectiva en el flanco de subida al final del ciclo."],
        ["x = expresión", "Señal combinacional hacia un bloque, por ejemplo ini_div = 1 o final = 1."],
        ["RAM(f,c) ← dato", "Escritura en la RAM (we = 1) en la dirección fila f, columna c."],
    ], [2.3, 4.6]))
    A(Spacer(1, 4))
    A(P("Todas las decisiones de un bloque usan los valores que tienen los registros al comenzar el ciclo. Cada "
        "combinación de estado y decisiones lleva a un solo estado siguiente, y todo camino de decisiones termina en "
        "un estado."))
    A(P("Vista general", "h2"))
    A(figura("vista_general", "Figura 5. Diagrama de estados del ASM principal (22 estados).", max_alto=3.0))

    hojas = [
        ("asm_hoja1", "Hoja 1: espera y carga de la matriz (s0 a s3)",
         "s2 recorre la ROM con el contador dira y los contadores i y j. La dirección de la RAM es fila & columna "
         "(3 + 3 bits), así que no hace falta multiplicar para ubicar a(i,j)."),
        ("asm_hoja2", "Hoja 2: pivote, búsqueda de fila, intercambio y banco (s4 a s9)",
         "La RAM tiene una dirección de lectura y otra de escritura. En s7 se lee RAM(i,j) y en el mismo flanco se "
         "escribe tmp1 en esa posición; por eso el intercambio usa tres estados por columna."),
        ("asm_hoja3", "Hoja 3: productos, resta e inicio de la división (s10 a s15)",
         "Con un solo multiplicador, los dos productos se hacen en estados distintos. En s15 el sumador/restador "
         "calcula 0 − t3; el multiplexor de dividendo entrega |t3| y el bloque de división lo carga en el flanco."),
        ("asm_hoja4", "Hoja 4: espera de la división, escritura y avance (s16 a s18)",
         "El ASM espera fin_div. En ese ciclo el cociente es válido y se escribe en RAM(i,j) con el signo sq "
         "(el sumador/restador calcula 0 − cociente). s18 guarda el determinante como último pivote."),
        ("asm_hoja5", "Hoja 5: conversión XS3 y final (s19 a s21)",
         "El bloque XS3 convierte primero |det| y luego |pivote(dir_p)|. En s21 el ASM espera con final = 1; si "
         "cambia dir_p vuelve a s19 y convierte el nuevo pivote (unos 4 µs)."),
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
        ("s5", "Lee RAM(i,k)", "RAM(i,k) ≠ 0: j ← k, signo ← not signo, s6. RAM(i,k) = 0 e i = n: det_bin ← 0, s19. "
               "Si no: i ← i + 1, s5."),
        ("s6", "tmp1 ← RAM(k,j)", "s7"),
        ("s7", "tmp2 ← RAM(i,j); RAM(i,j) ← tmp1", "s8"),
        ("s8", "RAM(k,j) ← tmp2", "j = n: s4. Si no: j ← j + 1, s6."),
        ("s9", "banco(k) ← piv; i ← k + 1; j ← k + 1", "s10"),
        ("s10", "mul_a ← piv; mul_b ← RAM(i,j)", "s11"),
        ("s11", "t1 ← producto; mul_a ← RAM(i,k)", "s12"),
        ("s12", "mul_b ← RAM(k,j)", "s13"),
        ("s13", "t2 ← producto", "s14"),
        ("s14", "t3 ← t1 − t2", "s15"),
        ("s15", "ini_div = 1; dividendo = |t3|; divisor = |p|; sq ← signo(t3) xor signo(p)", "s16"),
        ("s16", "Espera el bloque de división", "fin_div = 0: s16. fin_div = 1: RAM(i,j) ← ±cociente y además: "
                "j ≠ n: j ← j + 1, s10; j = n e i ≠ n: i ← i + 1, j ← k + 1, s10; i = n y j = n: s17."),
        ("s17", "p ← piv; |p| ← |piv|; k ← k + 1", "k + 1 = n: s18. Si no: s4."),
        ("s18", "det_bin ← ±RAM(n,n); banco(n) ← ±RAM(n,n) (signo negativo si signo = 1)", "s19"),
        ("s19", "ini_xs3 = 1; bin_xs3 = |val| (val = det_bin si conv_piv = 0, banco(dir_p) si conv_piv = 1); "
                "neg ← signo(val); dir_ant ← dir_p", "s20"),
        ("s20", "Espera el bloque XS3", "fin_xs3 = 0: s20. fin_xs3 = 1 y conv_piv = 0: det ← bcd_xs3, det_neg ← neg, "
                "conv_piv ← 1, s19. fin_xs3 = 1 y conv_piv = 1: pivote ← bcd_xs3, piv_neg ← neg, s21."),
        ("s21", "final = 1; dira ← 0", "inicio = 1: s1. dir_p ≠ dir_ant: s19. Si no: s21."),
    ]
    A(PageBreak())
    A(P("Tabla de estados", "h2"))
    A(P("Resumen de cada bloque ASM, en el orden del archivo src/asm_bareiss.vhd."))
    A(tabla([["Estado", "Operaciones", "Siguiente estado"]] + [list(d) for d in descripciones], [0.6, 3.3, 3.0]))

    # 7 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("7. ASM del bloque de división", "h1"))
    A(P("El bloque [c]bloque_division[/c] divide magnitudes por restas sucesivas. Recibe |t3| y |p|; el signo lo "
        "aplica el ASM principal al escribir en la RAM. Como la división de Bareiss es exacta, al terminar el residuo R "
        "es 0."))
    A(figura("asm_division", "Figura 11. ASM del bloque de división.", max_alto=4.6))
    A(tabla([
        ["Estado", "Operaciones", "Siguiente estado"],
        ["d0", "final = 0", "inicio = 1: R ← dividendo, D ← divisor, Q ← 0, d1. Si no: d0."],
        ["d1", "El restador calcula R − D", "R − D ≥ 0: R ← R − D, Q ← Q + 1, d1. Si no: d2."],
        ["d2", "final = 1; cociente = Q", "d0"],
    ], [0.6, 2.6, 3.7]))
    A(P("Tarda |cociente| + 3 ciclos. El ASM principal está en s16 mientras tanto y escribe el cociente en el ciclo en "
        "que [c]final = 1[/c]."))

    # 8 -----------------------------------------------------------------------
    A(P("8. ASM del bloque XS3", "h1"))
    A(P("El documento XS3 describe 5 pasos. En el bloque [c]xs3[/c] cada paso es un estado propio, de modo que el "
        "diagrama muestra la conversión completa. Su camino de datos es el que se describió en clase: registro "
        "binario, registro decimal, un sumador (+3), un comparador de magnitud (> 4) y desplazadores."))
    A(figura("asm_xs3", "Figura 12. ASM del bloque XS3.", max_alto=6.8))
    A(tabla([
        ["Paso del documento XS3", "Estado", "Operación"],
        ["1. Inicializar el registro decimal en ceros", "x1", "dec ← 0 (40 bits); cont ← 0"],
        ["2. Colocar el MSB del registro binario en el LSB del registro decimal", "x2", "dec(0) ← bin(31)"],
        ["3. Revisar cada dígito: si es ≥ 5 (> 0100), sumarle 3 (0011)", "x3",
         "Un dígito por ciclo (d = 0 a 9): el multiplexor entrega el dígito d; si es > 4 se reemplaza por dígito + 3."],
        ["4. Correr a la izquierda y descartar el bit que sale; repetir desde el paso 2", "x4",
         "dec ← dec(38..0) & '0'; bin ← bin(30..0) & '0'; cont ← cont + 1; vuelve a x2"],
        ["5. Realizar únicamente el paso 2", "x2 con cont = 31",
         "En la pasada 32 por x2 entra el último bit y el ASM va a x5 (final = 1)."],
    ], [2.6, 0.9, 3.4]))
    A(Spacer(1, 6))
    A(P("Por qué se suma 3: si un dígito vale 5 o más, al correrlo a la izquierda quedaría en 10 o más, que no es un "
        "dígito BCD válido. Sumar 3 antes del corrimiento equivale a sumar 6 después, que es la corrección BCD, y "
        "hace que el exceso pase como acarreo al dígito siguiente. El registro binario es de 32 bits, así que el "
        "decimal necesita 10 dígitos (2[sup]32[/sup] − 1 = 4 294 967 295) y hay 32 pasadas por el paso 2."))
    A(P("Traza del XS3 para 362", "h2"))
    A(P("362 = 1 0110 1010[sub]2[/sub] tiene 9 bits significativos. En las pasadas cont = 0 a 22 solo entran ceros, por "
        "eso la tabla empieza en cont = 23. «bin(31..23)» son los 9 bits de arriba del registro binario; el de la "
        "izquierda, bin(31), es el que copia el paso 2. El registro decimal se muestra con sus tres dígitos bajos."))
    filas, bcd_fin = traza_xs3(362)
    cambio = {"S23 (2)": "x2 (2)", "S24 (3)": "x3 (3)", "S25 (4)": "x4 (4)"}
    filas = [[cambio.get(c, c).replace("va a S26", "va a x5") for c in f] for f in filas]
    A(tabla([["cont", "Estado (paso)", "dec: C D U", "bin(31..23)", "Comentario"]] + filas,
            [0.45, 0.85, 1.25, 0.95, 3.4]))
    A(Spacer(1, 4))
    A(P(f"Resultado: dec = {bcd_fin[2]:04b} {bcd_fin[1]:04b} {bcd_fin[0]:04b} = {bcd_fin[2]} {bcd_fin[1]} {bcd_fin[0]}."))

    # 9 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("9. Señales del ASM principal", "h1"))
    A(P("9.1 Señales de control por estado (ASM → bloques)", "h2"))
    A(P("Son asignaciones concurrentes de src/asm_bareiss.vhd que dependen del estado. Los estados que no aparecen "
        "no usan estos bloques."))
    A(tabla([
        ["Estado", "RAM (lectura / escritura)", "Sumador/restador", "Otros bloques"],
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
        ["s14", "—", "t1 − t2", "—"],
        ["s15", "—", "0 − t3", "división: ini_div, dividendo = |t3|, divisor = |p|"],
        ["s16", "escribe (i,j) ← ±cociente cuando fin_div = 1", "0 − cociente", "—"],
        ["s17", "—", "0 − piv", "—"],
        ["s18", "lee (n,n)", "0 − RAM(n,n)", "banco: we_banco, dir_banco = n, dato = ±RAM(n,n)"],
        ["s19", "—", "0 − val", "XS3: ini_xs3, bin_xs3 = |val|"],
        ["s21", "—", "—", "final = 1"],
    ], [0.55, 2.35, 1.25, 2.75]))
    A(P("En este algoritmo el sumador/restador siempre resta ([c]sr_op = '1'[/c]): t1 − t2 y las negaciones 0 − x "
        "que dan los valores absolutos y los signos."))
    A(P("9.2 Señales de estado (bloques → ASM)", "h2"))
    A(tabla([
        ["Señal", "Origen", "Se pregunta en"],
        ["inicio", "Pulso del antirrebote", "s0, s21"],
        ["RAM(k,k) = 0, RAM(i,k) = 0", "Comparador de q con 0", "s4, s5"],
        ["i = n, j = n", "Comparadores de 3 bits", "s2, s5, s8, s16"],
        ["k + 1 = n", "Contador k y comparador", "s17"],
        ["signo(t3) = t3(49)", "Registro t3", "s15 (multiplexor de dividendo)"],
        ["sq", "Registro del signo del cociente", "s16"],
        ["fin_div", "Bloque de división", "s16"],
        ["signo(piv) = piv(31)", "Registro piv", "s17"],
        ["signo", "Registro de paridad de intercambios", "s18"],
        ["signo(val) = val(31)", "Multiplexor val", "s19"],
        ["fin_xs3", "Bloque XS3", "s20"],
        ["conv_piv", "Registro: 0 = convierte det, 1 = convierte pivote", "s19, s20"],
        ["dir_p ≠ dir_ant", "Comparador de 3 bits", "s21"],
    ], [2.1, 2.9, 1.9]))
    A(P("9.3 Registros del ASM principal y anchos", "h2"))
    A(tabla([
        ["Registro", "Bits", "Uso"],
        ["st", "5 (22 estados)", "Estado del ASM"],
        ["dira_r", "5", "Dirección de la ROM"],
        ["n, i, j, k", "3 c/u", "Tamaño de la matriz y contadores de fila, columna y paso"],
        ["piv, p, pabs", "32 c/u", "Pivote actual, pivote anterior y |p| (divisor)"],
        ["tmp1, tmp2", "32 c/u", "Intercambio de filas"],
        ["mul_a, mul_b", "25 c/u", "Entradas del multiplicador"],
        ["t1, t2, t3", "50 c/u", "Productos y numerador de la fórmula (1)"],
        ["sq, signo, conv_piv, neg", "1 c/u", "Signo del cociente, paridad de intercambios, qué se convierte, signo convertido"],
        ["det_bin", "32", "Determinante en binario"],
        ["dir_ant", "3", "dir_p ya convertido"],
        ["det, pivote", "40 c/u", "Salidas en BCD"],
    ], [1.8, 1.1, 4.0]))
    A(P("Por la identidad de Sylvester, cada valor de la RAM es el determinante de una submatriz de A, y la desigualdad "
        "de Hadamard lo acota: |det| ≤ (32·√m)[sup]m[/sup] para una submatriz m×m."))
    V(viñetas([
        "Operandos del multiplicador: submatrices de hasta 4×4, |x| < 2[sup]24[/sup]. Caben en 25 bits con signo.",
        "Determinante 5×5: |det| ≤ 1,88 × 10[sup]9[/sup] < 2[sup]31[/sup]. RAM, det_bin, cociente y XS3 son de 32 bits.",
        "Numerador: |t3| ≤ 3,2 × 10[sup]14[/sup] < 2[sup]49[/sup]. t1, t2, t3, el sumador/restador y el dividendo son de 50 bits.",
        "BCD: 32 bits binarios necesitan 10 dígitos. El display muestra 7 y LD1 avisa si hay más.",
    ]))

    # 10 ----------------------------------------------------------------------
    A(PageBreak())
    A(P("10. Interfaz con la tarjeta", "h1"))
    A(P("Divisor de frecuencia", "h2"))
    A(P("El oscilador de la Nexys A7 es de 100 MHz (pin E3, sección 5 del manual de la tarjeta). El bloque "
        "[c]divisor_frecuencia[/c] genera un pulso de un ciclo cada 1 ms (cuenta 100 000 ciclos) y una onda cuadrada "
        "de periodo 1 s (cambia cada 500 ms) que se ve en LD15. Los pulsos se usan como habilitación: todo el diseño "
        "trabaja con el mismo reloj, sin relojes derivados."))
    A(P("El procesador trabaja a 100 MHz y no usa el divisor. Con un reloj de 1 s, la matriz 3×3 de prueba (822 ciclos) "
        "tardaría unos 14 minutos y la 5×5 (4 583 ciclos) más de una hora."))
    A(P("Antirrebote", "h2"))
    A(P("Solo el botón de inicio lo necesita. El bloque [c]antirrebote[/c] sincroniza el botón con dos flip-flops, lo "
        "muestrea cada 1 ms en un registro de 8 bits y cambia su nivel estable solo con 8 muestras iguales (8 ms sin "
        "rebote). Entrega un pulso de un ciclo en el flanco de subida del nivel estable, así una pulsación arranca un "
        "solo cálculo."))
    A(P("Sincronizador y display", "h2"))
    A(P("El bloque [c]sincronizador[/c] pasa los switches dir_p por dos flip-flops. El bloque [c]display_8dig[/c] cambia "
        "de dígito con cada pulso de 1 ms (barrido de 8 ms, 125 Hz): AN7 muestra el signo y AN6..AN0 los 7 dígitos. "
        "En el tope, un multiplexor elige det si dir_p = 0 y pivote si dir_p = 1 a 5, y LD1 se enciende si los "
        "dígitos 7 a 9 del valor mostrado no son cero."))

    # 11 ----------------------------------------------------------------------
    A(P("11. Tiempo de ejecución", "h1"))
    V(viñetas([
        "Carga de la matriz (s0 a s3): n² + 3 ciclos.",
        "Por cada elemento actualizado: s10 a s15 (6 ciclos) más la división (|cociente| + 3 ciclos).",
        "Conversión XS3: unos 380 ciclos (3,8 µs). Al terminar el cálculo se hacen dos (det y pivote).",
    ]))
    A(P("La división por restas sucesivas domina el tiempo cuando los valores son grandes. Las matrices de prueba "
        "terminan en menos de 50 µs, salvo la matriz 7 (valores cercanos a ±32), que tarda 19 millones de ciclos "
        "(0,19 s). Con los valores de la clase («del orden de cientos de miles») el tiempo es de microsegundos."))

    # 12 ----------------------------------------------------------------------
    A(P("12. Implementación en ISE 14.7 y la Nexys A7", "h1"))
    A(P("12.1 Proyecto", "h2"))
    V(viñetas([
        "File → New Project. Top-level source type: HDL. Family: Artix7 · Device: XC7A100T · Package: CSG324 · "
        "Speed: −1 · Synthesis: XST · Simulator: ISim · Preferred language: VHDL. ISE solo soporta la Nexys A7-100T.",
        "Add Source: todos los .vhd de src/ y src/nexys_a7.ucf (Implementation); sim/pkg_prueba.vhd, "
        "sim/tb_procesador.vhd y sim/tb_det_bareiss.vhd (Simulation). Si ISE no elige det_bareiss como tope, usen "
        "«Set as Top Module».",
        "Synthesize (View RTL Schematic muestra los bloques) → Implement Design → Generate Programming File. Revisen "
        "que se cumpla la restricción de 10 ns (TS_sys_clk).",
        "Programación: la Nexys A7 no funciona con Digilent Adept. Usen iMPACT de ISE o el Hardware Manager de Vivado "
        "(Lab Edition) con el archivo .bit.",
    ]))
    A(P("12.2 Cambiar la matriz (día de la evaluación)", "h2"))
    V(viñetas([
        "Opción 1: editar src/rom_matriz.vhd. La línea de 00h es n; las siguientes son a11, a21, …, an1, a12, … en "
        "complemento a 2 de 6 bits.",
        "Opción 2: [c]python3 sim/modelo_referencia.py rom \"2 1 3; 1 4 2; 3 2 5\"[/c] escribe el archivo e imprime el "
        "determinante y los pivotes esperados.",
        "Simular con sim/tb_procesador.vhd: lee la ROM, calcula los valores esperados y los compara, sin modificar el "
        "testbench.",
        "Sintetizar y volver a programar la FPGA.",
    ]))
    A(P("12.3 Operación en la tarjeta", "h2"))
    V(viñetas([
        "Pulsar BTNU (rst). Poner SW2..SW0 en 000.",
        "Pulsar BTNC (inicio). Cuando termina, LD0 (final) se enciende y el display muestra el determinante.",
        "Poner SW2..SW0 en 1 a n para ver el pivote k; con k = n se ve otra vez el determinante.",
        "Si LD1 está encendido, el valor tiene más de 7 dígitos y se ven los 7 de abajo. LD15 parpadea cada segundo.",
    ]))
    A(P("12.4 Matrices de prueba", "h2"))
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
    A(P("12.5 Pines (src/nexys_a7.ucf)", "h2"))
    A(tabla([
        ["Señal", "Pines"],
        ["clk", "E3 (100 MHz)"],
        ["rst / inicio", "M18 (BTNU) / N17 (BTNC)"],
        ["dir_p(0..2)", "J15 (SW0), L16 (SW1), M13 (SW2)"],
        ["final / desborde / latido", "H17 (LD0) / K15 (LD1) / V11 (LD15)"],
        ["seg(0..6) = CA..CG, dp", "T10, R10, K16, K13, P15, T11, L18; DP = H15"],
        ["an(0..7)", "J17, J18, T9, J14, P14, T14, K2, U13"],
    ], [1.9, 5.0]))

    # 13 ----------------------------------------------------------------------
    A(P("13. Simulación", "h1"))
    V(viñetas([
        "[b]sim/tb_procesador.vhd[/b] (con sim/pkg_prueba.vhd) lee la matriz de la ROM, calcula el determinante y los "
        "pivotes esperados con un modelo de Bareiss en VHDL (con números reales para no desbordar los enteros de 32 "
        "bits), pulsa inicio, compara det, recorre dir_p = 1 a n comparando cada pivote, comprueba que el pivote n sea "
        "el det y repite todo con un segundo inicio.",
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
        "en una copia del diseño: XS3 sumando 2 en lugar de 3, antirrebote sin el muestreo de 1 ms (el cálculo arrancó "
        "13 veces) y último pivote sin el signo de los intercambios (matriz 2). Las tres se detectaron."))

    # 14 ----------------------------------------------------------------------
    A(P("14. Limitaciones y verificación pendiente", "h1"))
    V(viñetas([
        "[b]No se ejecutó ISE.[/b] El diseño se verificó con GHDL 4.1 (simulación con [c]-fsynopsys -fexplicit[/c] y "
        "síntesis genérica). Hay que sintetizar en ISE 14.7 y revisar el reporte de tiempos a 100 MHz. El camino más "
        "largo pasa por el sumador/restador de 50 bits hacia el bloque de división (s15); si no se cumplen los 10 ns, "
        "generen un reloj de 50 MHz con el Clocking Wizard y pongan PERIOD = 20 ns.",
        "[b]Salidas en BCD.[/b] det y pivote salen del procesador ya convertidos por el XS3. Si el profesor las quiere "
        "en binario, los valores existen dentro del ASM (det_bin y el banco).",
        "[b]Multiplicador con signo.[/b] Usa el paquete [c]std_logic_signed[/c] sobre std_logic_vector (no el tipo "
        "signed). Si no se acepta, hay que multiplicar magnitudes y aplicar el signo con el sumador/restador.",
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

"""Contenido del PDF del Taller 5 (ASM de alto nivel, solo std_logic).

Lo importa generar_pdf.py.  Los resultados de simulacion se leen de
sim/resultado_ghdl.txt y la tabla de matrices de sim/modelo_referencia.py.
"""
import re

from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Preformatted, Spacer, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents

from generar_pdf import E, P, RAIZ, codigo, figura, tabla, traza_xs3, viñetas
from modelo_referencia import MATRICES, bareiss

VHDL = (RAIZ / "src" / "det_bareiss.vhd").read_text(encoding="utf-8")


def resultados_sim():
    texto = (RAIZ / "sim" / "resultado_ghdl.txt").read_text(encoding="utf-8")
    res = {}
    for m in re.finditer(r"Matriz (\d) \((\dx\d)\): det='(.{8})' desborde='(.)'  ciclos=(\d+)  OK", texto):
        res[int(m.group(1))] = (m.group(2), m.group(3), m.group(4), int(m.group(5)))
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
    A(P("Explicación del diagrama ASM, del camino de datos y del código VHDL", "subtitulo"))
    A(Spacer(1, 0.15 * inch))
    A(P("Herramienta: Xilinx ISE 14.7 (XST, ISim) · Tarjeta: Digilent Nexys A7-100T (XC7A100T-1CSG324C)", "subtitulo"))
    A(Spacer(1, 0.8 * inch))
    A(P("[b]Nota para el equipo.[/b] Este documento explica un diseño de referencia. El enunciado advierte que "
        "los diseños parecidos entre equipos no se califican, así que revisen cada estado, entiendan por qué está "
        "ahí y adáptenlo antes de entregarlo. Las conclusiones del informe son responsabilidad del equipo.", "nota"))
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
    A(P("El procesador lee de una ROM externa una matriz simétrica de 2×2 a 5×5, la copia a una RAM de trabajo y "
        "calcula su determinante con el algoritmo de Bareiss. Usa un multiplicador, un sumador/restador y una división "
        "por restas sucesivas, y guarda los pivotes en un banco de registros. Al terminar convierte a BCD, con el "
        "algoritmo XS3, el determinante y el pivote que indica [c]dir_p[/c]."))
    A(P("El ASM tiene 28 estados (s0 a s27) y está escrito en un solo proceso VHDL, con el mismo estilo de los "
        "ejemplos de clase ([c]ASM_contador_unos[/c] y [c]ASM_Sumax[/c]): un [c]case st is[/c], un [c]when[/c] por "
        "estado y las operaciones de cada caja escritas dentro de su estado."))
    A(P("Reglas de descripción", "h2"))
    A(tabla([
        ["Regla", "Cómo se cumple"],
        ["Solo std_logic (excepto la RAM)",
         "Todas las señales, puertos y constantes son std_logic o std_logic_vector. La única excepción es la RAM, "
         "descrita como [c]array of std_logic_vector[/c] (forma en que XST infiere una memoria); [c]conv_integer[/c] "
         "solo aparece para indexar esa RAM."],
        ["Estados del ASM",
         "Los ejemplos de clase usan [c]type estados_asm is (s0, s1, …)[/c], que no es std_logic. Para cumplir la regla, "
         "los estados son constantes: [c]constant s0 : STD_LOGIC_VECTOR(4 downto 0) := \"00000\";[/c]. El "
         "[c]case st is / when s0 =>[/c] se escribe y se lee igual."],
        ["Sin variables ni tipos de software",
         "No hay [c]variable[/c], [c]integer[/c], [c]signed[/c]/[c]unsigned[/c], [c]boolean[/c] ni genéricos en el "
         "diseño. La ROM es un [c]with dir select[/c]; el registro BCD es un vector de 40 bits; el banco son 4 registros."],
        ["Sintetizable", "Sin [c]wait[/c], [c]after[/c] ni lazos [c]for[/c]/[c]while[/c]. La síntesis genérica con GHDL "
                         "termina sin errores ni latches, con un solo multiplicador."],
        ["Solo para simulación", "Los testbench sí usan variables, integer, string y wait; no se sintetizan."],
    ], [1.9, 5.0]))
    A(P("Requisitos del enunciado", "h2"))
    A(tabla([
        ["Requisito del taller", "Cómo lo cumple el diseño"],
        ["ASM en VHDL de alto nivel, con inicio y final",
         "Un proceso con [c]case st is[/c] (s0 a s27). [c]final = '1'[/c] solo en s27. El cálculo arranca con "
         "[c]inicio[/c] (BTNC)."],
        ["Matriz en ROM: 00h = n, luego los a(i,j) como en la Figura 1",
         "ROM externa al ASM ([c]rom_matrices[/c]), conectada por [c]dira[/c] (5 bits) y [c]a[/c] (6 bits, "
         "complemento a 2). Los elementos van por columnas: a11, a21, …, an1, a12, … Tiene 8 páginas de prueba."],
        ["Multiplicador, sumador/restador y división por restas sucesivas",
         "Entidades [c]multiplicador[/c] (con signo, 25 × 25) y [c]sumador_restador[/c] (50 bits). La división son los "
         "registros R y Q y el lazo del estado s17, que usa el restador."],
        ["Memoria RAM para las iteraciones", "Entidad [c]ram_trabajo[/c] de 64 × 32 bits; dirección fila & columna."],
        ["Pivotes en un banco de registros, visibles con los switches",
         "Registros b1 a b4; [c]dir_p[/c] (SW2..SW0) elige el pivote y la salida [c]pivote[/c] lo entrega en BCD."],
        ["Determinante en los displays", "Salida [c]det[/c] en BCD; SW3 elige si el display muestra det o pivote."],
        ["XS3 evidenciado paso a paso en el ASM",
         "Un estado por paso del documento XS3: s22 (paso 1), s23 (pasos 2 y 5), s24 (paso 3) y s25 (paso 4)."],
    ], [2.2, 4.7]))
    A(KeepTogether([P("Archivos del repositorio", "h2"), tabla([
        ["Archivo", "Contenido"],
        ["src/det_bareiss.vhd", "Diseño completo: ROM, RAM, multiplicador, sumador/restador, ASM, sincronizador, "
                                "display y tope para la tarjeta."],
        ["src/nexys_a7.ucf", "Pines y restricción de reloj (100 MHz) para ISE."],
        ["sim/tb_asm_bareiss.vhd", "Testbench del ASM con la ROM externa: 8 matrices y todos sus pivotes."],
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
    A(P("Si a(k,k) = 0, el ASM busca la primera fila i > k con a(i,k) ≠ 0 (estado s5), intercambia las filas k e i en "
        "las columnas k a n (s6 a s9) e invierte el bit [c]signo[/c]. Al final, det = −a(n,n) si hubo un número impar de "
        "intercambios. Si no hay ninguna fila con a(i,k) ≠ 0, det = 0. Las columnas menores que k no se intercambian "
        "porque el algoritmo no las vuelve a leer."))

    # 3 -----------------------------------------------------------------------
    A(P("3. Algoritmo XS3 dentro del ASM", "h1"))
    A(P("El documento XS3 describe 5 pasos. En el ASM cada paso es un estado propio, de modo que el diagrama muestra "
        "la conversión completa y no una caja que diga «convertir a BCD». La misma secuencia de estados se usa dos "
        "veces: primero para el determinante y después para el pivote. El registro [c]conv_piv[/c] indica cuál de los "
        "dos se está convirtiendo, y s26 guarda el resultado en [c]det[/c] o en [c]pivote[/c]."))
    A(tabla([
        ["Paso del documento XS3", "Estado", "Operación en el ASM"],
        ["1. Inicializar el registro decimal en ceros", "s22", "bcd ← 0 (40 bits); cont ← 0"],
        ["2. Colocar el MSB del registro binario en el LSB del registro decimal", "s23", "bcd(0) ← bin(31)"],
        ["3. Revisar cada dígito: si es ≥ 5 (> 0100), sumarle 3 (0011)", "s24",
         "Un dígito por ciclo (d = 0 a 9). Si dig > 0100, el dígito d se reemplaza por dig + 3, calculado en el "
         "sumador/restador."],
        ["4. Correr a la izquierda y descartar el bit que sale; repetir desde el paso 2", "s25",
         "bcd ← bcd(38..0) & '0'; bin ← bin(30..0) & '0'; cont ← cont + 1; vuelve a s23"],
        ["5. Realizar únicamente el paso 2", "s23 con cont = 31",
         "En la pasada 32 por s23 entra el último bit y el ASM va a s26 sin pasar por s24 ni s25."],
    ], [2.6, 0.9, 3.4]))
    A(Spacer(1, 6))
    A(P("Por qué se suma 3: si un dígito vale 5 o más, al correrlo a la izquierda quedaría en 10 o más, que no es un "
        "dígito BCD válido. Sumar 3 antes del corrimiento equivale a sumar 6 después, que es la corrección BCD, y "
        "hace que el exceso pase como acarreo al dígito siguiente."))
    A(P("Tamaños: el registro binario [c]bin[/c] tiene 32 bits, así que el registro decimal necesita 10 dígitos "
        "(2[sup]32[/sup] − 1 = 4 294 967 295) y el lazo da 32 pasadas por el paso 2 (cont = 0 a 31). El signo no entra "
        "al XS3: en s21 se carga |valor| en [c]bin[/c] y el signo en [c]neg[/c]."))
    A(P("Traza del XS3 para 362 (determinante de la página 3)", "h2"))
    A(P("362 = 1 0110 1010[sub]2[/sub] tiene 9 bits significativos. En las pasadas cont = 0 a 22 solo entran ceros y el "
        "registro decimal sigue en 0, por eso la tabla empieza en cont = 23. La columna «bin(31..23)» muestra los 9 bits "
        "de arriba del registro binario; el bit de la izquierda, bin(31), es el que copia el paso 2. El registro decimal "
        "se muestra con sus tres dígitos bajos: centenas, decenas y unidades."))
    filas, bcd_fin = traza_xs3(362)
    filas = [[c.replace("S23", "s23").replace("S24", "s24").replace("S25", "s25").replace("S26", "s26") for c in f]
             for f in filas]
    A(tabla([["cont", "Estado (paso)", "BCD: C D U", "bin(31..23)", "Comentario"]] + filas,
            [0.45, 0.85, 1.25, 0.95, 3.4]))
    A(Spacer(1, 4))
    A(P(f"Resultado: BCD = {bcd_fin[2]:04b} {bcd_fin[1]:04b} {bcd_fin[0]:04b} = {bcd_fin[2]} {bcd_fin[1]} {bcd_fin[0]}. "
        "La simulación muestra « 0000362» en el display para esta matriz."))

    # 4 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("4. Caja negra", "h1"))
    A(P("La caja negra sigue los apuntes del profesor: la ROM está fuera del bloque «Algoritmo Bareiss» y se conecta "
        "por [c]dira[/c] y [c]a[/c]; las entradas son clk, rst, inicio y dir_p; las salidas son el determinante, el "
        "pivote y final; el XS3 forma parte del bloque. Es la entidad [c]asm_bareiss[/c]."))
    A(figura("caja_negra", "Figura 1. Caja negra del procesador (entidad asm_bareiss) con la ROM externa.", max_ancho=6.2))
    A(tabla([
        ["Puerto", "Dir.", "Bits", "Función"],
        ["clk", "in", "1", "Reloj"],
        ["rst", "in", "1", "Reinicio asíncrono, activo en alto"],
        ["inicio", "in", "1", "Comienza el cálculo (se lee en s0 y s27)"],
        ["dir_p", "in", "3", "Dirección del banco de pivotes: 1 a 4 = pivote k; 0 y 5 a 7 dan 0"],
        ["a", "in", "6", "Dato de la ROM, complemento a 2"],
        ["dira", "out", "5", "Dirección de la ROM"],
        ["det, det_neg", "out", "40, 1", "|det| en BCD (10 dígitos) y su signo"],
        ["pivote, piv_neg", "out", "40, 1", "|pivote(dir_p)| en BCD y su signo"],
        ["final", "out", "1", "'1' cuando det y pivote están listos (estado s27)"],
    ], [1.3, 0.5, 0.6, 4.5]))
    A(P("Tope para la tarjeta", "h2"))
    A(P("La entidad [c]det_bareiss[/c] conecta la caja negra con la Nexys A7: sincroniza los botones y switches, "
        "conecta la ROM (dirección = SW15..SW13 & dira) y muestra det o pivote en los 8 displays según SW3."))
    A(figura("jerarquia", "Figura 2. Entidades del archivo src/det_bareiss.vhd.", max_alto=2.6))
    A(tabla([
        ["Puerto del tope", "Pin Nexys A7", "Función"],
        ["clk", "E3", "Reloj de 100 MHz"],
        ["rst / inicio", "BTNU (M18) / BTNC (N17)", "Reinicio / inicio del cálculo"],
        ["sw_mat(2..0)", "SW15..SW13", "Matriz de prueba (página de la ROM)"],
        ["dir_p(2..0)", "SW2..SW0", "Dirección del pivote"],
        ["ver", "SW3", "0: el display muestra det; 1: muestra pivote"],
        ["final / desborde", "LD0 / LD1", "Fin del cálculo / el valor mostrado tiene más de 7 dígitos"],
        ["an, seg, dp", "AN7..AN0, CA..CG, DP", "Display: AN7 = signo, AN6..AN0 = 7 dígitos"],
    ], [1.5, 1.9, 3.5]))

    # 5 -----------------------------------------------------------------------
    A(P("5. Cajas grises: unidad de control y camino de datos", "h1"))
    A(P("La unidad de control (UC) es el registro de estado [c]st[/c] y la lógica que elige el siguiente estado. El "
        "camino de datos (CD) contiene la RAM, los registros y las unidades funcionales. En el VHDL de alto nivel las "
        "dos partes están en el mismo proceso, como en los ejemplos de clase; las señales de control son el estado "
        "actual y las de estado son las condiciones de las cajas de decisión (sección 8)."))
    A(figura("cajas_grises", "Figura 3. Cajas grises: señales de control (UC → CD) y señales de estado (CD → UC)."))

    # 6 -----------------------------------------------------------------------
    A(P("6. Pseudocódigo con el hardware disponible", "h1"))
    A(P("Cada línea indica el estado del ASM que la ejecuta. Las operaciones del mismo estado ocurren en el mismo "
        "ciclo de reloj."))
    A(codigo(
        "s0 :  final = 0;  esperar inicio = 1\n"
        "s1 :  n = ROM(00h)\n"
        "s2 :  para j = 1..n, i = 1..n:  M(i,j) = ROM(dira);  dira = dira + 1     (orden por columnas)\n"
        "s3 :  k = 1;  p = 1;  |p| = 1;  signo = 0;  banco = 0;  conv_piv = 0\n"
        "mientras k <= n-1:\n"
        "  s4 :  piv = M(k,k)\n"
        "        si piv = 0:\n"
        "  s5 :     buscar i = k+1..n con M(i,k) /= 0\n"
        "           si no existe:  det_bin = 0;  ir a CONVERTIR\n"
        "  s6-s9:   intercambiar filas k e i (columnas k..n);  signo = not signo;  volver a s4\n"
        "  s10:  banco(k) = piv\n"
        "        para i = k+1..n, j = k+1..n:\n"
        "  s11-s14:  t1 = piv · M(i,j);   t2 = M(i,k) · M(k,j)        (un multiplicador, dos usos)\n"
        "  s15:      t3 = t1 - t2                                     (sumador/restador)\n"
        "  s16-s17:  Q = |t3| / |p|  por restas sucesivas            (sumador/restador)\n"
        "  s18:      M(i,j) = +Q  o  -Q   (signo = signo(t3) xor signo(p))\n"
        "  s19:  p = piv;  |p| = |piv|;  k = k + 1\n"
        "s20:  det_bin = M(n,n);  si signo = 1 entonces det_bin = -det_bin\n"
        "CONVERTIR (dos veces: conv_piv = 0 para det, conv_piv = 1 para el pivote):\n"
        "s21:  val = det_bin o banco(dir_p);  bin = |val|;  neg = signo(val)\n"
        "s22:  XS3 paso 1:  BCD = 0;  cont = 0\n"
        "repetir:\n"
        "  s23:  XS3 paso 2:  BCD(0) = bin(31);   si cont = 31 salir   (paso 5)\n"
        "  s24:  XS3 paso 3:  para d = 0..9:  si BCD(d) > 4 entonces BCD(d) = BCD(d) + 3\n"
        "  s25:  XS3 paso 4:  BCD = BCD << 1;  bin = bin << 1;  cont = cont + 1\n"
        "s26:  si conv_piv = 0:  det = BCD;  conv_piv = 1;  ir a s21\n"
        "      si no:            pivote = BCD\n"
        "s27:  final = 1;  si inicio = 1 ir a s1;  si cambia dir_p ir a s21"))
    A(P("Los «para» y «mientras» del pseudocódigo no son lazos del VHDL: cada uno es un lazo del ASM que vuelve a un "
        "estado mientras un contador no llegue a su límite."))

    # 7 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("7. Diagrama ASM", "h1"))
    A(P("Convenciones", "h2"))
    A(tabla([
        ["Elemento", "Significado"],
        ["Caja de estado (rectángulo azul)", "Operaciones que se hacen en todo el estado (salidas tipo Moore)."],
        ["Caja de decisión (rombo)", "Pregunta sobre una señal de estado. La salida 1 es la condición verdadera."],
        ["Caja de salida condicional (rectángulo redondeado naranja)",
         "Operación que solo ocurre si se toma ese camino (tipo Mealy), como en el ejemplo «ASM Mealy» de clase."],
        ["Bloque ASM (recuadro punteado)", "Caja de estado más sus decisiones y salidas condicionales: dura un ciclo de reloj."],
        ["Conector (círculo verde)", "Une hojas del diagrama: A → s1, B → s4, C → s11, D → s21, E → s20, F → s17, G → s22."],
        ["x ← expresión", "Asignación a un registro; se hace efectiva al final del ciclo (flanco de subida)."],
        ["x = expresión", "Valor combinacional (no se guarda), por ejemplo final = 1 o la selección val."],
        ["M(i,j)", "Palabra de la RAM en la dirección fila i, columna j."],
    ], [2.3, 4.6]))
    A(Spacer(1, 4))
    A(P("Todas las decisiones de un bloque usan los valores que tienen los registros al comenzar el ciclo. Por "
        "ejemplo, en s19 la pregunta k = n − 1 usa el k anterior al incremento. Cada combinación de estado y "
        "decisiones lleva a un solo estado siguiente, y todo camino de decisiones termina en un estado."))
    A(P("Vista general", "h2"))
    A(figura("vista_general", "Figura 4. Diagrama de estados del ASM (28 estados), agrupado por función.",
             max_alto=3.0))

    hojas = [
        ("asm_hoja1", "Hoja 1: espera y carga de la matriz (s0 a s3)",
         "s2 recorre la ROM externa con el contador [c]dira[/c] y los contadores de fila y columna. La dirección de la "
         "RAM es fila & columna, así que no hace falta multiplicar para ubicar a(i,j)."),
        ("asm_hoja2", "Hoja 2: pivote, búsqueda de fila e intercambio (s4 a s10)",
         "La RAM tiene un solo puerto: cada lectura o escritura ocupa un estado, por eso el intercambio usa cuatro "
         "estados por columna. Después del intercambio se vuelve a s4 para leer el pivote nuevo, que ya no es cero."),
        ("asm_hoja3", "Hoja 3: productos y numerador (s11 a s16)",
         "Con un solo multiplicador, los dos productos de la fórmula (1) se hacen en estados distintos. Los operandos "
         "se cargan en mul_a y mul_b un estado antes, para que el camino crítico sea registro → multiplicador → registro."),
        ("asm_hoja4", "Hoja 4: división por restas sucesivas y avance (s17 a s19)",
         "s17 es el lazo de la división: en cada ciclo el restador calcula R − |p|; si el resultado no es negativo se "
         "guarda en R y el cociente Q aumenta en 1. La división se hace con magnitudes y el signo se aplica al escribir "
         "en s18."),
        ("asm_hoja5", "Hoja 5: determinante y valor a convertir (s20 y s21)",
         "A s21 se llega desde s20 (cálculo normal), desde s5 (matriz singular, det_bin = 0), desde s26 (después de "
         "convertir det, para convertir el pivote) y desde s27 cuando cambia dir_p."),
        ("asm_hoja6", "Hoja 6: algoritmo XS3 paso a paso, guardado y fin (s22 a s27)",
         "En la primera pasada s26 guarda el BCD en det y vuelve a s21 para convertir el pivote; en la segunda lo guarda "
         "en pivote y pasa a s27. s27 espera con final = 1. Si cambia dir_p, el ASM vuelve a s21 y convierte el nuevo "
         "pivote (unos 375 ciclos, invisibles para el ojo)."),
    ]
    for i, (fig, titulo, texto) in enumerate(hojas, start=1):
        A(PageBreak())
        A(P(titulo, "h2"))
        A(P(texto))
        A(figura(fig, f"Figura {4 + i}. {titulo}.", max_alto=7.9))

    descripciones = [
        ("s0", "final = 0; dira ← 0", "inicio = 1: s1. Si no: s0."),
        ("s1", "n ← a(2..0) = ROM(00h); dira ← 1; i ← 1; j ← 1", "s2"),
        ("s2", "M(i,j) ← a con extensión de signo a 32 bits; dira ← dira + 1. i es el índice que cambia más rápido, "
               "como en la Figura 1 del taller.", "i ≠ n: i ← i + 1, s2. i = n y j ≠ n: i ← 1, j ← j + 1, s2. "
               "i = n y j = n: s3."),
        ("s3", "k ← 1; p ← 1 (pivote inicial a(0,0) = 1); |p| ← 1; signo ← 0; banco ← 0; conv_piv ← 0", "s4"),
        ("s4", "piv ← M(k,k)", "M(k,k) = 0: i ← k + 1, s5. Si no: s10."),
        ("s5", "Lee M(i,k) buscando una fila con elemento distinto de cero en la columna k.",
               "M(i,k) ≠ 0: j ← k, signo ← not signo, s6. M(i,k) = 0 e i = n: det_bin ← 0, s21 (singular). "
               "Si no: i ← i + 1, s5."),
        ("s6", "tmp1 ← M(k,j)", "s7"),
        ("s7", "tmp2 ← M(i,j)", "s8"),
        ("s8", "M(k,j) ← tmp2", "s9"),
        ("s9", "M(i,j) ← tmp1", "j ≠ n: j ← j + 1, s6. j = n: s4 (vuelve a leer el pivote)."),
        ("s10", "banco(k) ← piv; i ← k + 1; j ← k + 1", "s11"),
        ("s11", "mul_a ← piv; mul_b ← M(i,j)", "s12"),
        ("s12", "t1 ← mul_a × mul_b (= a(k,k)·a(i,j)); mul_a ← M(i,k)", "s13"),
        ("s13", "mul_b ← M(k,j)", "s14"),
        ("s14", "t2 ← mul_a × mul_b (= a(i,k)·a(k,j))", "s15"),
        ("s15", "t3 ← t1 − t2", "s16"),
        ("s16", "Q ← 0; sq ← signo(t3) xor signo(p); R ← |t3| (0 − t3 si t3 < 0)", "s17"),
        ("s17", "El restador calcula R − |p| (resta de prueba).", "R − |p| ≥ 0: R ← R − |p|, Q ← Q + 1, s17. "
                "Si no: s18 (R queda en 0 porque la división es exacta)."),
        ("s18", "M(i,j) ← Q, o 0 − Q si sq = 1", "j ≠ n: j ← j + 1, s11. j = n e i ≠ n: i ← i + 1, j ← k + 1, s11. "
                "i = n y j = n: s19."),
        ("s19", "p ← piv; |p| ← |piv|; k ← k + 1", "k = n − 1: s20. Si no: s4."),
        ("s20", "det_bin ← M(n,n), o 0 − M(n,n) si signo = 1", "s21"),
        ("s21", "val = det_bin si conv_piv = 0, banco(dir_p) si conv_piv = 1; neg ← signo(val); bin ← |val|; "
                "dir_ant ← dir_p", "s22"),
        ("s22", "XS3 paso 1: bcd ← 0; cont ← 0", "s23"),
        ("s23", "XS3 paso 2: bcd(0) ← bin(31)", "cont = 31: s26 (paso 5 cumplido). Si no: d ← 0, s24."),
        ("s24", "XS3 paso 3 sobre el dígito d: si dig > 4, dígito d ← dig + 3 (en el sumador/restador)",
                "d ≠ 9: d ← d + 1, s24. d = 9: s25."),
        ("s25", "XS3 paso 4: bcd ← bcd << 1 (entra 0); bin ← bin << 1; cont ← cont + 1", "s23"),
        ("s26", "Guarda el resultado del XS3.", "conv_piv = 0: det ← bcd, det_neg ← neg, conv_piv ← 1, s21. "
                "conv_piv = 1: pivote ← bcd, piv_neg ← neg, s27."),
        ("s27", "final = 1; dira ← 0", "inicio = 1: s1. dir_p ≠ dir_ant: s21. Si no: s27."),
    ]
    A(PageBreak())
    A(P("Tabla de estados", "h2"))
    A(P("Resumen de cada bloque ASM: lo que hace la caja de estado y las salidas condicionales, y a qué estado va "
        "según las decisiones. Es la misma información de las figuras 5 a 10, en el orden del código VHDL."))
    A(tabla([["Estado", "Operaciones", "Siguiente estado"]] + [list(d) for d in descripciones], [0.62, 3.35, 2.93]))

    # 8 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("8. Señales del procesador", "h1"))
    A(P("8.1 Señales de estado (CD → UC)", "h2"))
    A(tabla([
        ["Señal de estado", "Cómo se obtiene", "Se pregunta en"],
        ["inicio", "Botón BTNC sincronizado con dos flip-flops", "s0, s27"],
        ["M(k,k) = 0", "Comparador de dout_ram con 0", "s4"],
        ["M(i,k) = 0", "Comparador de dout_ram con 0", "s5"],
        ["i = n", "Comparador de 3 bits", "s2, s5, s18"],
        ["j = n", "Comparador de 3 bits", "s2, s9, s18"],
        ["k = n − 1", "Comparador k + 1 = n", "s19"],
        ["signo(t3)", "Bit t3(49)", "s16"],
        ["R − |p| ≥ 0", "Bit 49 de la salida del sumador/restador en 0", "s17"],
        ["sq", "Registro de signo del cociente", "s18"],
        ["signo(piv)", "Bit piv(31)", "s19"],
        ["signo", "Registro con la paridad de intercambios de filas", "s20"],
        ["signo(val)", "Bit val(31)", "s21"],
        ["cont = 31", "Comparador de 5 bits", "s23"],
        ["BCD(d) > 4", "Comparador de 4 bits sobre el dígito elegido por d", "s24"],
        ["d = 9", "Comparador de 4 bits", "s24"],
        ["conv_piv", "Registro: 0 = se convierte det, 1 = se convierte el pivote", "s26 (y el mux val en s21)"],
        ["dir_p ≠ dir_ant", "Comparador de 3 bits (dir_p sincronizado)", "s27"],
    ], [1.5, 3.6, 1.8]))
    A(P("8.2 Señales de control por estado (UC → CD)", "h2"))
    A(P("Además de cargar los registros que aparecen en cada caja, el estado controla la RAM, el multiplicador y el "
        "sumador/restador. Los estados que no aparecen no usan estas unidades."))
    A(tabla([
        ["Estado", "Dirección RAM (fila, col)", "Escribe en RAM", "Sumador/restador", "Multiplicador"],
        ["s2", "(i, j)", "ROM con extensión de signo", "—", "—"],
        ["s4", "(k, k)", "—", "—", "—"],
        ["s5", "(i, k)", "—", "—", "—"],
        ["s6", "(k, j)", "—", "—", "—"],
        ["s7", "(i, j)", "—", "—", "—"],
        ["s8", "(k, j)", "tmp2", "—", "—"],
        ["s9", "(i, j)", "tmp1", "—", "—"],
        ["s11", "(i, j)", "—", "—", "carga mul_a, mul_b"],
        ["s12", "(i, k)", "—", "—", "t1 ← producto; carga mul_a"],
        ["s13", "(k, j)", "—", "—", "carga mul_b"],
        ["s14", "—", "—", "—", "t2 ← producto"],
        ["s15", "—", "—", "t1 − t2", "—"],
        ["s16", "—", "—", "0 − t3", "—"],
        ["s17", "—", "—", "R − |p|", "—"],
        ["s18", "(i, j)", "Q, o la salida del restador si sq = 1", "0 − Q", "—"],
        ["s19", "—", "—", "0 − piv", "—"],
        ["s20", "(n, n)", "—", "0 − M(n,n)", "—"],
        ["s21", "—", "—", "0 − val", "—"],
        ["s24", "—", "—", "dig + 3 (suma)", "—"],
    ], [0.62, 1.4, 1.98, 1.35, 1.55]))
    A(P("En el VHDL estas señales son asignaciones concurrentes que dependen de [c]st[/c]: [c]fila_ram[/c], "
        "[c]col_ram[/c], [c]we_ram[/c], [c]din_ram[/c], [c]sr_a[/c], [c]sr_b[/c] y [c]sr_op[/c]. Si en el informe "
        "implementan la UC con ROM de entrada, registro y ROM de salida, como en el ejemplo del contador de unos, esta "
        "tabla es la base de la ROM de salida (palabra de control)."))
    A(P("8.3 Registros internos y tamaños", "h2"))
    A(tabla([
        ["Registro", "Bits", "Uso"],
        ["st", "5 (28 estados)", "Estado del ASM"],
        ["dira_r", "5", "Dirección de la ROM (sale por dira)"],
        ["n, i, j, k", "3 c/u", "Tamaño de la matriz y contadores de fila, columna y paso"],
        ["piv, p, pabs", "32 c/u", "Pivote actual, pivote anterior (divisor) y su magnitud"],
        ["tmp1, tmp2", "32 c/u", "Intercambio de filas"],
        ["mul_a, mul_b", "25 c/u", "Registros de entrada del multiplicador"],
        ["t1, t2, t3", "50 c/u", "Productos y numerador de la fórmula (1)"],
        ["R, Q, sq", "50, 32, 1", "Residuo, cociente y signo del cociente"],
        ["signo", "1", "Paridad de intercambios de filas"],
        ["det_bin", "32", "Determinante en binario"],
        ["b1, b2, b3, b4", "32 c/u", "Banco de pivotes"],
        ["conv_piv, dir_ant", "1, 3", "Qué se convierte y qué dir_p ya se convirtió"],
        ["bin, bcd", "32, 40", "Registros binario y decimal del XS3"],
        ["cont, d, neg", "5, 4, 1", "Bits procesados, dígito revisado y signo del valor convertido"],
        ["det_bcd, det_neg_r", "40, 1", "Salida det"],
        ["piv_bcd, piv_neg_r", "40, 1", "Salida pivote"],
    ], [1.75, 1.1, 4.05]))
    A(P("Por qué estos anchos", "h2"))
    A(P("Por la identidad de Sylvester, cada valor guardado en la RAM es el determinante de una submatriz m×m de A. La "
        "desigualdad de Hadamard lo acota: |det| ≤ (32·√m)[sup]m[/sup] cuando |a(i,j)| ≤ 32."))
    V(viñetas([
        "Operandos del multiplicador: en el paso k son submatrices de k×k con k ≤ 4, así que |x| < 2[sup]24[/sup] = "
        "16 777 216. Caben en 25 bits con signo. (La cota no se alcanza porque +32 no existe en 6 bits.)",
        "Determinante 5×5: |det| ≤ 1,88 × 10[sup]9[/sup] < 2[sup]31[/sup]. Por eso la RAM, det_bin, Q y bin son de 32 bits.",
        "Numerador: t3 = p · a(k), con |p| ≤ 170 268 (submatriz 3×3), así que |t3| ≤ 3,2 × 10[sup]14[/sup] < "
        "2[sup]49[/sup]. t1, t2, t3, R y el sumador/restador son de 50 bits.",
        "BCD: 32 bits binarios necesitan 10 dígitos decimales. El display muestra los 7 de abajo; si los dígitos 7 a 9 "
        "no son cero, LD1 (desborde) se enciende.",
    ]))

    # 9 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("9. Camino de datos", "h1"))
    A(P("El camino de datos se organiza alrededor de dos buses: la salida de la RAM ([c]dout_ram[/c]) y la salida del "
        "sumador/restador ([c]resultado[/c]). Los multiplexores de la figura los controla el estado del ASM (sección 8.2)."))
    A(figura("camino_datos", "Figura 11. Diagrama de bloques simplificado del camino de datos.", max_alto=5.2))
    A(tabla([
        ["Unidad", "Detalle", "Estados"],
        ["Multiplicador", "Entidad con signo, 25 × 25 → 50 bits: [c]p <= a * b;[/c] con [c]std_logic_signed[/c].", "s12, s14"],
        ["Sumador/restador", "Entidad de 50 bits: [c]s <= a + bx + op;[/c] con bx = not b en resta. Un solo sumador "
                             "con acarreo de entrada, como el bloque «+/−» de las notas de clase.", "s15 a s21, s24"],
        ["División por restas sucesivas", "Registros R y Q, incrementador Q + 1 y el bit de signo de la resta R − |p| "
                                          "como señal de estado. Usa el sumador/restador.", "s16 a s18"],
        ["ROM", "Externa al ASM: entidad [c]rom_matrices[/c], [c]with dir select[/c], 256 × 6 bits.", "s1, s2"],
        ["RAM", "64 × 32 bits, escritura síncrona y lectura asíncrona; dirección fila & columna", "s2 a s20"],
        ["Banco de pivotes", "4 registros de 32 bits; escritura en s10; lectura con dir_p ([c]with dir_p select[/c])", "s3, s10, s21"],
        ["Contadores", "dira, i, j, k, Q, cont y d", "varios"],
        ["Comparadores", "= 0, i = n, j = n, k + 1 = n, cont = 31, d = 9, dig > 4, dir_p ≠ dir_ant", "varios"],
    ], [1.5, 4.3, 1.1]))
    A(P("La síntesis genérica con GHDL ([c]ghdl --synth[/c]) confirma un solo multiplicador (25 × 25), la RAM de "
        "64 × 32 inferida como memoria y ningún latch."))

    # 10 ----------------------------------------------------------------------
    A(P("10. Tiempo de ejecución", "h1"))
    V(viñetas([
        "Carga de la matriz (s0 a s3): n² + 3 ciclos.",
        "Paso k: s4, s10 y s19 (3 ciclos) más, por cada uno de los (n − k)² elementos, 8 ciclos fijos (s11 a s16 y s18) "
        "y |cociente| + 1 ciclos de división en s17.",
        "Intercambio de filas: hasta n − k ciclos de búsqueda, 4 ciclos por columna y una nueva lectura del pivote.",
        "XS3: unos 375 ciclos por conversión (s21 a s26). Al terminar el cálculo se hacen dos (det y pivote); al cambiar "
        "dir_p, una.",
    ]))
    A(P("La división por restas sucesivas domina el tiempo cuando los valores son grandes, porque tarda tantos ciclos "
        "como vale el cociente. En la página 7 (5×5 con valores cercanos a ±32) el cálculo tarda unos 19 millones de "
        "ciclos, 0,19 s a 100 MHz. En el peor caso teórico el último cociente se acerca a 1,9 × 10[sup]9[/sup], unos "
        "19 s. Una división con corrimiento y resta (restauración) haría lo mismo en 50 ciclos; aquí se dejó la de "
        "restas sucesivas porque es la que pide el enunciado."))

    # 11 ----------------------------------------------------------------------
    A(P("11. Implementación en ISE 14.7 y la Nexys A7", "h1"))
    A(P("11.1 Proyecto", "h2"))
    V(viñetas([
        "File → New Project. Top-level source type: HDL.",
        "Family: Artix7 · Device: XC7A100T · Package: CSG324 · Speed: −1 · Synthesis: XST · Simulator: ISim · "
        "Preferred language: VHDL. ISE solo soporta la Nexys A7-100T; la variante 50T exige Vivado.",
        "Add Source: src/det_bareiss.vhd y src/nexys_a7.ucf (Implementation); sim/tb_asm_bareiss.vhd y "
        "sim/tb_det_bareiss.vhd (Simulation). Si ISE no elige det_bareiss como tope, usen «Set as Top Module».",
        "Synthesize → Implement Design → Generate Programming File. Revisen en el reporte de tiempos que se cumpla la "
        "restricción de 10 ns (TS_sys_clk).",
        "Programación: según el manual de la tarjeta, la Nexys A7 no funciona con Digilent Adept. Usen iMPACT de ISE o "
        "el Hardware Manager de Vivado (Lab Edition) con el archivo .bit.",
    ]))
    A(P("11.2 Operación en la tarjeta", "h2"))
    V(viñetas([
        "Pulsar BTNU (rst).",
        "Elegir la matriz con SW15..SW13 (0 a 7, tabla 11.3) y el pivote con SW2..SW0 (1 a 4).",
        "Pulsar BTNC (inicio). Cuando termina, LD0 (final) se enciende.",
        "Con SW3 = 0 el display muestra el determinante; con SW3 = 1 muestra el pivote elegido con SW2..SW0. AN7 es el "
        "signo y AN6..AN0 los 7 dígitos.",
        "Al mover SW2..SW0, el ASM convierte el nuevo pivote (LD0 se apaga unos 4 µs).",
        "Si LD1 (desborde) está encendido, el valor mostrado tiene más de 7 dígitos y se ven los 7 de abajo.",
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
        "el det y los pivotes esperados y las líneas de la ROM ([c]\"dato\" when \"dirección\",[/c]) listas para pegar "
        "en la entidad rom_matrices. Cada página empieza en la dirección 32 × página."))
    A(P("11.4 Pines (src/nexys_a7.ucf)", "h2"))
    A(tabla([
        ["Señal", "Pines"],
        ["clk", "E3 (100 MHz)"],
        ["rst / inicio", "M18 (BTNU) / N17 (BTNC)"],
        ["dir_p(0..2)", "J15 (SW0), L16 (SW1), M13 (SW2)"],
        ["ver", "R15 (SW3)"],
        ["sw_mat(0..2)", "U12 (SW13), U11 (SW14), V10 (SW15)"],
        ["final / desborde", "H17 (LD0) / K15 (LD1)"],
        ["seg(0..6) = CA..CG, dp", "T10, R10, K16, K13, P15, T11, L18; DP = H15"],
        ["an(0..7)", "J17, J18, T9, J14, P14, T14, K2, U13"],
    ], [1.8, 5.1]))

    # 12 ----------------------------------------------------------------------
    A(P("12. Simulación", "h1"))
    V(viñetas([
        "[b]sim/tb_asm_bareiss.vhd[/b] conecta la ROM externa al ASM, como en la caja negra. Para cada matriz pone "
        "dir_p = 1, pulsa inicio, espera final = 1 y compara det, det_neg y el pivote 1. Después recorre dir_p = 2 a "
        "n − 1 y compara cada pivote, y verifica que det no cambie. El genérico MAX_MATRIZ del testbench vale 6 por "
        "defecto (unos 0,2 ms simulados); con 7 incluye la matriz extrema, que tarda bastante.",
        "[b]sim/tb_det_bareiss.vhd[/b] prueba el tope con el sincronizador, la ROM y el display: calcula la página 3 y "
        "lee los 8 dígitos decodificando an y seg durante un barrido completo (2[sup]18[/sup] ciclos), primero con "
        "SW3 = 0 (det) y luego con SW3 = 1 y dir_p = 3 (pivote 3).",
    ]))
    res = resultados_sim()
    filas = [["Pág.", "Tamaño", "det esperado", "det simulado", "LD1", "Ciclos", "Resultado"]]
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
    A(P("Los ciclos van desde que se suelta inicio hasta final = 1 e incluyen las dos conversiones XS3. Todos los "
        "pivotes también coinciden, y el testbench del tope leyó « 0000362» y «-0000170» en los segmentos (ver "
        "sim/resultado_ghdl.txt). Para comprobar que los testbench detectan errores se probaron dos fallas en una copia "
        "del diseño: «+2» en lugar de «+3» en el XS3, y saltar la conversión del pivote en s26. En ambos casos el "
        "testbench reportó errores."))

    # 13 ----------------------------------------------------------------------
    A(P("13. Limitaciones y verificación pendiente", "h1"))
    V(viñetas([
        "[b]No se ejecutó ISE.[/b] El diseño se verificó con GHDL 4.1 (simulación con [c]-fsynopsys -fexplicit[/c] y "
        "síntesis genérica), no con XST ni ISim. Hay que sintetizar en ISE 14.7 y revisar el reporte de tiempos a "
        "100 MHz. Si no se cumpliera, generen un reloj de 50 MHz con el Clocking Wizard y pongan PERIOD = 20 ns.",
        "[b]Salidas det y pivote en BCD.[/b] En la caja negra de los apuntes no se ve si Det y Pivote salen en binario "
        "o en BCD. Aquí salen en BCD porque el XS3 debe estar dentro del ASM. Si el profesor las quiere en binario, "
        "los valores ya existen dentro del ASM (det_bin y el banco).",
        "[b]Estados como constantes.[/b] Si el profesor acepta [c]type estados_asm[/c] como en sus ejemplos, basta "
        "cambiar la declaración de st y borrar las constantes; el resto del código no cambia.",
        "[b]Modelo de RAM.[/b] Se usó lectura asíncrona. Si el modelo del aula tiene lectura síncrona, cada lectura "
        "(s4, s5, s6, s7, s11, s12, s13, s20) necesita un estado de espera antes de usar el dato.",
        "[b]Display de 7 dígitos.[/b] Con signo en AN7 caben valores hasta ±9 999 999; para valores mayores se "
        "enciende LD1 y se ven los 7 dígitos de abajo.",
        "[b]Tiempo de la división.[/b] Proporcional al cociente (sección 10).",
        "[b]Valor de n.[/b] El diseño supone 2 ≤ n ≤ 5 en la ROM y no lo valida.",
        "[b]ROM con 8 páginas.[/b] La selección con SW15..SW13 permite mostrar varios tamaños sin volver a sintetizar. "
        "Si el profesor quiere una sola matriz, usen la página 0 con esos switches en 0.",
    ]))

    # Anexo -------------------------------------------------------------------
    A(PageBreak())
    A(P("Anexo A. Código VHDL completo (src/det_bareiss.vhd)", "h1"))
    numeradas = "\n".join(f"{n:4d}  {l}" for n, l in enumerate(VHDL.splitlines(), start=1))
    A(Preformatted(numeradas, E["anexo"]))
    return h

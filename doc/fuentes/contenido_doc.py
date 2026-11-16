"""Contenido del PDF del Taller 5: 4 bloques (antirrebote, divisor de frecuencia,
procesador de Bareiss y visualizador con el ASM XS3).

Lo importa generar_pdf.py. Los resultados de simulacion se leen de
sim/resultado_ghdl.txt, la tabla de matrices de sim/modelo_referencia.py, las
transiciones de los ASM de diagramas.py (que las compara con el VHDL) y las
secciones 9 a 11 (camino de datos, unidad de control y sintesis esperada) de
procedimiento_doc.py y uc_cd.py.
"""
import re

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Preformatted, Spacer, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents

import diagramas
from procedimiento_doc import seccion_procesador, seccion_sintesis, seccion_visualizador
from generar_pdf import E, P, RAIZ, codigo, figura, tabla, traza_xs3, viñetas
from modelo_referencia import MATRICES, MATRIZ_POR_DEFECTO, bareiss, texto_display

E["h2_anexo"] = ParagraphStyle("h2_anexo", parent=E["h2"])   # no aparece en el indice

ARCHIVOS_VHDL = ["det_bareiss.vhd", "procesador_bareiss.vhd", "visualizador.vhd",
                 "antirrebote.vhd", "divisor_frecuencia.vhd"]

ESTADOS_B = [f"s{i}" for i in range(14)]


def resultados_sim():
    """{matriz: (ciclos, det_texto)} desde sim/resultado_ghdl.txt."""
    texto = (RAIZ / "sim" / "resultado_ghdl.txt").read_text(encoding="utf-8")
    res = {}
    for bloque in re.split(r"== Matriz ", texto)[1:]:
        num = int(bloque[0])
        ciclos = int(re.search(r"Corrida 1: final = 1 en (\d+) ciclos", bloque).group(1))
        det = re.search(r"det\s+= (.{11})  OK", bloque).group(1)
        res[num] = (ciclos, det)
    return res


def mat_txt(a):
    return "[br]".join("[c]" + " ".join(f"{x:3d}" for x in fila).replace(" ", "\u00a0") + "[/c]" for fila in a)


def tabla_transiciones(tabla_asm, estados):
    filas = [["Estado", "Condiciones (cajas de decisión del camino)", "Estado siguiente"]]
    for e in estados:
        for conds, destino in tabla_asm[e]:
            filas.append([e, "; ".join(conds) if conds else "(sin decisión)", destino])
    return filas


class Figuras:
    def __init__(self):
        self.n = 0

    def __call__(self, nombre, pie, **kw):
        self.n += 1
        return figura(nombre, f"Figura {self.n}. {pie}", **kw)


def contenido():
    h = []
    A = h.append
    V = h.extend
    fig = Figuras()
    tabla_asm, errores_asm = diagramas.verificar()

    # Portada -----------------------------------------------------------------
    A(Spacer(1, 1.1 * inch))
    A(P("Universidad Distrital Francisco José de Caldas[br]Ingeniería Electrónica · Análisis y Diseño de Microprocesadores", "subtitulo"))
    A(Spacer(1, 0.45 * inch))
    A(P("TALLER 5", "titulo"))
    A(P("Microprocesador de propósito específico:[br]determinante por el algoritmo de Bareiss[br]con salida decimal (algoritmo XS3)", "titulo"))
    A(Spacer(1, 0.3 * inch))
    A(P("Pseudoalgoritmo, caja negra, diagramas ASM, camino de datos, unidad de control, síntesis esperada y código VHDL", "subtitulo"))
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
    A(P("El diseño tiene cuatro bloques, cada uno en su archivo:"))
    V(viñetas([
        "[b]antirrebote.vhd[/b]: un solo antirrebote, para el botón de inicio.",
        "[b]divisor_frecuencia.vhd[/b]: pulso de 1 ms (antirrebote y barrido del display) y onda de 1 s.",
        "[b]procesador_bareiss.vhd[/b]: el ASM de Bareiss en alto nivel, como los ejemplos ASM_Sumax y "
        "ASM_contador_unos: un solo process con [c]case st is[/c] y 14 estados. Usa la ROM con la matriz, dos RAM del "
        "modelo del profesor, un banco de pivotes y las [b]dos únicas unidades funcionales[/b]: un multiplicador y un "
        "sumador/restador. La RAM, el multiplicador y el sumador/restador son entidades aparte. No hay ALU.",
        "[b]visualizador.vhd[/b]: en un mismo archivo, el ASM del algoritmo XS3 y el display de 8 dígitos. Es un ASM "
        "aparte que trabaja en paralelo con el de Bareiss y tiene sus propias unidades (no comparte las del procesador).",
    ]))
    A(P("El procesador calcula el determinante de la matriz guardada en su ROM (de 2×2 a 5×5) y deja los pivotes en "
        "el banco. Cuando termina sube [c]final[/c]. Desde ese momento, el ASM XS3 del visualizador convierte una y "
        "otra vez a decimal el valor que elige [c]dir_p[/c] (det con dir_p = 0, el pivote k con dir_p = k) y el "
        "display lo muestra. ISE necesita una entidad superior para asignar los pines; ese es el archivo "
        "[c]det_bareiss.vhd[/c], que solo conecta los cuatro bloques."))
    A(fig("arquitectura", "Arquitectura: los cuatro bloques y el contenido del procesador.", max_alto=4.2))
    A(P("Reglas de descripción", "h2"))
    A(tabla([
        ["Regla", "Cómo se cumple"],
        ["Solo std_logic, excepto la RAM y los estados",
         "Todas las señales de datos, puertos y constantes son std_logic o std_logic_vector. Hay dos excepciones, "
         "las dos tomadas de los ejemplos del curso: la RAM es el modelo del profesor sin cambios ([c]type mem is "
         "array(0 to 31) of std_logic_vector(31 downto 0)[/c] y [c]conv_integer[/c]), y los estados de cada ASM se "
         "declaran como en ASM_Sumax y ASM_contador_unos: [c]type estados_asm is (s0, s1, …); signal st : "
         "estados_asm;[/c]."],
        ["Sin integer, signed ni unsigned",
         "No hay [c]integer[/c], [c]natural[/c], [c]signed[/c], [c]unsigned[/c], [c]boolean[/c] ni genéricos. El ASM "
         "se escribe como en los ejemplos: [c]case st is / when s0 =>[/c]."],
        ["Sin variables ni descripciones tipo software",
         "No hay [c]variable[/c], [c]function[/c] ni lazos [c]for[/c]/[c]while[/c]. Las repeticiones las hace el ASM, "
         "un paso por ciclo de reloj, con contadores."],
        ["Unidades funcionales del procesador",
         "Dos entidades con una instancia cada una: [c]multiplicador[/c] (U_MUL, 25 × 25 → 50) y "
         "[c]sumador_restador[/c] (U_SR, 50 bits, op = 0 suma y op = 1 resta). La RAM es la entidad RAM_memory del "
         "profesor (dos instancias). Los estados cargan las entradas de las unidades. El visualizador tiene sus "
         "propias unidades (restador 0 − val, sumador +3, comparador > 4)."],
        ["Alto nivel, como los ejemplos",
         "Cada estado del process hace las operaciones de su caja ASM (por ejemplo [c]cociente <= cociente + 1;[/c]). "
         "No hay constantes con nombre: se usan literales como [c]\"001\"[/c] y [c](others => '0')[/c]. La síntesis "
         "genérica con GHDL termina sin errores ni latches."],
        ["Reglas del ASM", "Verificadas con un programa sobre los diagramas (sección 6.2)."],
        ["Solo para simulación", "Los testbench usan variables, integer, real, string y wait; no se sintetizan."],
    ], [1.9, 5.0]))
    A(P("Requisitos del enunciado y de la clase", "h2"))
    A(tabla([
        ["Requisito", "Cómo lo cumple el diseño"],
        ["Señal de inicio y señal de final", "Entradas y salidas del procesador; final = 1 en el estado s13."],
        ["Matriz en ROM: 00h = n, luego los a(i,j) como en la Figura 1 del taller",
         "Entidad [c]rom_matriz[/c] dentro de procesador_bareiss.vhd: dirección dira de 5 bits y dato a de 6 bits "
         "en complemento a 2. Elementos por columnas: a11, a21, …, an1, a12, …"],
        ["La ROM hace parte de la arquitectura", "Está dentro del procesador; no entra por puertos."],
        ["Multiplicador, sumador/restador y división por restas sucesivas",
         "Entidades multiplicador y sumador_restador (una instancia de cada una); la división son los estados s10 y "
         "s11."],
        ["Memoria RAM del curso", "Dos instancias de [c]RAM_memory[/c] (modelo del profesor, 32 × 32)."],
        ["Pivotes en un banco de registros, visibles con los switches",
         "Registros b1 a b4: dir_p = k (SW2..SW0) elige el pivote; con dir_p = n sale el determinante, que es el "
         "último pivote."],
        ["Determinante en decimal en los displays", "El visualizador convierte con el XS3 y muestra signo y 7 dígitos."],
        ["ASM del XS3 aparte, en paralelo", "ASM de 6 estados en visualizador.vhd, un estado por paso del documento XS3."],
        ["Un solo antirrebote", "Entidad [c]antirrebote[/c], solo para el botón de inicio."],
    ], [2.2, 4.7]))
    A(KeepTogether([P("Archivos del repositorio", "h2"), tabla([
        ["Archivo", "Contenido"],
        ["src/procesador_bareiss.vhd", "rom_matriz (la matriz), RAM_memory (modelo del profesor), multiplicador, "
                                       "sumador_restador y procesador_bareiss (el ASM de Bareiss, un solo process)."],
        ["src/visualizador.vhd", "ASM XS3 y display de 8 dígitos."],
        ["src/antirrebote.vhd", "Antirrebote del botón de inicio."],
        ["src/divisor_frecuencia.vhd", "Pulso de 1 ms y onda de 1 s (reloj de 100 MHz)."],
        ["src/det_bareiss.vhd", "Tope para ISE: solo conecta los cuatro bloques."],
        ["src/nexys_a7.ucf", "Pines y restricción de reloj (10 ns)."],
        ["sim/tb_procesador.vhd, sim/pkg_prueba.vhd", "Testbench autoverificado del procesador: sirve para cualquier ROM."],
        ["sim/tb_visualizador.vhd", "Testbench del XS3 y del display."],
        ["sim/tb_det_bareiss.vhd", "Testbench de la tarjeta: botón con rebotes y lectura del display."],
        ["sim/modelo_referencia.py", "Valores esperados; cambia la ROM dentro de procesador_bareiss.vhd."],
        ["sim/probar_matrices.py, sim/resultado_ghdl.txt", "Prueba con las 8 matrices y resultados de la simulación."],
        ["doc/fuentes/uc_cd.py, sim/resultado_modelo_uc_cd.txt",
         "Camino de datos y unidad de control esperados (tablas de las ROM) y su simulación ciclo a ciclo."],
        ["sim/estimacion_yosys.txt", "Estimación de recursos en Artix-7 con Yosys (referencia para comparar con ISE)."],
        ["doc/figuras/*.png, doc/fuentes/*.py", "Figuras de este documento y los scripts que las generan y verifican."],
    ], [2.4, 4.5])]))

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
        "por eso el cálculo se hace en la misma memoria, sin otra copia de la matriz."))
    A(P("Ejemplo 3×3", "h2"))
    A(codigo("A = | 2 1 3 |      k = 1, p = 1:  a22 = (2·4 − 1·1)/1 = 7    a23 = (2·2 − 1·3)/1 = 1\n"
             "    | 1 4 2 |                     a32 = (2·2 − 3·1)/1 = 1    a33 = (2·5 − 3·3)/1 = 1\n"
             "    | 3 2 5 |      k = 2, p = 2:  a33 = (7·1 − 1·1)/2 = 3   →   det = 3\n"
             "Banco de pivotes: pivote 1 = 2, pivote 2 = 7, pivote 3 = 3 = det"))
    A(P("Pivote cero", "h2"))
    A(P("Si a(k,k) = 0, el ASM busca la primera fila i > k con a(i,k) ≠ 0 (estado s3), intercambia las filas k e i en "
        "las columnas k a n (s4 y s5) e invierte el bit [c]signo[/c]. Al final, det = −a(n,n) si hubo un número impar "
        "de intercambios; ese valor con su signo es el que se guarda como último pivote, para que el pivote n siempre "
        "sea igual al determinante. Si no hay fila con a(i,k) ≠ 0, det = 0."))

    # 3 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("3. Pseudoalgoritmo con el hardware disponible", "h1"))
    A(P("Cada línea indica el estado del ASM que la ejecuta. Las operaciones de un mismo estado ocurren en el mismo "
        "ciclo de reloj. RAM(f,c) es el elemento a(f,c). Las dos RAM tienen la misma matriz: la RAM A lee a(i,j) y la RAM B lee a(k,j) (sección 9.4)."))
    A(P("Procesador de Bareiss", "h2"))
    A(codigo(
        "s0 :  final = 0;  esperar inicio = 1;  n = ROM(00h);  dira = 1;  i = 1;  j = 1\n"
        "s1 :  para j = 1..n, i = 1..n:  RAM(i,j) = ROM(dira);  dira = dira + 1     (por columnas)\n"
        "      al terminar:  k = 1;  j = 1;  p = 1;  signo = 0\n"
        "mientras k <= n-1:\n"
        "  s2 :  piv = a(k,k)  (RAM B con j = k);  i = k + 1\n"
        "        si piv = 0:\n"
        "  s3 :     buscar i = k+1..n con a(i,k) /= 0;  si no existe: det = 0, ir a s13\n"
        "  s4-s5:   para j = k..n:  RAM(i,j) = a(k,j);  tmp = a(i,j);  RAM(k,j) = tmp\n"
        "           signo = not signo;  volver a s2\n"
        "        si no:  banco(k) = piv\n"
        "        para i = k+1..n:\n"
        "  s6 :     aik = a(i,k)\n"
        "           para j = k+1..n:\n"
        "  s7-s9:     t1 = piv · a(i,j);   t2 = aik · a(k,j)                (multiplicador)\n"
        "  s10:       residuo = t1 - t2;  cociente = 0                     (sumador/restador)\n"
        "             sq = signo(residuo) xor signo(p)\n"
        "  s11:       mientras residuo /= 0:                               (sumador/restador)\n"
        "                residuo = residuo - p (mismo signo) o residuo + p (signos distintos)\n"
        "                cociente = cociente + 1\n"
        "  s12:       RAM(i,j) = +cociente o -cociente (según sq)\n"
        "        p = piv;  k = k + 1\n"
        "  s12:  en el último paso:  det = +cociente o -cociente (según sq xor signo)\n"
        "s13:  final = 1;  si inicio = 1 ir a s1"))
    A(P("Visualizador (ASM XS3, en paralelo)", "h2"))
    A(codigo(
        "repetir siempre:\n"
        "  x0:  esperar final = 1;  val = det si dir_p = 0, pivote si no\n"
        "       bin = |val|;  neg = signo(val)\n"
        "  x1:  PASO 1:  dec = 0 (10 dígitos);  cont = 0\n"
        "  repetir:\n"
        "    x2:  PASO 2:  dec(0) = bin(31);   si cont = 31 salir   (PASO 5)\n"
        "    x3:  PASO 3:  para d = 0..9:  si dígito(d) > 4 entonces dígito(d) = dígito(d) + 3\n"
        "    x4:  PASO 4:  dec = dec << 1;  bin = bin << 1;  cont = cont + 1\n"
        "  x5:  disp = dec;  disp_neg = neg        (lo que muestra el display)"))
    A(P("Los «para» y «mientras» no son lazos del VHDL: cada uno es un lazo del ASM que vuelve a un estado mientras "
        "un contador no llegue a su límite."))

    # 4 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("4. Cajas negras", "h1"))
    A(P("4.1 Procesador de Bareiss", "h2"))
    A(P("Es la caja negra del tablero de clase: entradas clk, rst, inicio y dir_p; salidas det, pivote y final. La "
        "ROM, las RAM, el multiplicador y el sumador/restador están adentro."))
    A(fig("caja_negra", "Caja negra del procesador (entidad procesador_bareiss).", max_ancho=5.4))
    A(tabla([
        ["Puerto", "Dir.", "Bits", "Función"],
        ["clk", "in", "1", "Reloj (100 MHz en la tarjeta)"],
        ["rst", "in", "1", "Reinicio asíncrono, activo en alto"],
        ["inicio", "in", "1", "Comienza el cálculo (pulso de un ciclo; se lee en s0 y s13)"],
        ["dir_p", "in", "3", "Dirección del banco de pivotes: 1 a n = pivote k (el n es el det); 0, 6 y 7 leen 0"],
        ["det", "out", "32", "Determinante en binario (complemento a 2)"],
        ["pivote", "out", "32", "Pivote dir_p en binario (complemento a 2)"],
        ["final", "out", "1", "1 cuando det y los pivotes están listos (estado s13)"],
    ], [1.0, 0.5, 0.5, 4.9]))
    A(P("4.2 Visualizador", "h2"))
    A(fig("caja_negra_vis", "Caja negra del visualizador (entidad visualizador).", max_ancho=3.4))
    A(tabla([
        ["Puerto", "Dir.", "Bits", "Función"],
        ["clk, rst", "in", "1, 1", "Reloj y reinicio"],
        ["tick", "in", "1", "Pulso de 1 ms del divisor: cambia el dígito encendido"],
        ["final", "in", "1", "Del procesador: con 1 el ASM XS3 convierte; con 0 conserva lo que muestra"],
        ["dir_p", "in", "3", "0: muestra det; 1 a 5: muestra pivote"],
        ["det, pivote", "in", "32, 32", "Salidas binarias del procesador"],
        ["an, seg, dp", "out", "8, 7, 1", "Display: AN7 = signo, AN6..AN0 = 7 dígitos (activos en bajo)"],
        ["desborde", "out", "1", "1 si el valor tiene más de 7 dígitos (LD1)"],
    ], [1.0, 0.5, 0.8, 4.6]))
    A(P("4.3 Tarjeta", "h2"))
    A(tabla([
        ["Puerto de det_bareiss", "Pin", "Función"],
        ["clk", "E3", "Reloj de 100 MHz"],
        ["rst", "BTNU (M18)", "Reinicio de todo el diseño"],
        ["inicio", "BTNC (N17)", "Comienza el cálculo (pasa por el antirrebote)"],
        ["dir_p(2..0)", "SW2..SW0", "0: el display muestra det; 1 a 5: muestra el pivote k"],
        ["final", "LD0", "Fin del cálculo"],
        ["desborde", "LD1", "El valor mostrado tiene más de 7 dígitos"],
        ["latido", "LD15", "Onda de 1 s del divisor de frecuencia (el diseño está corriendo)"],
        ["an, seg, dp", "AN7..AN0, CA..CG, DP", "Display de 8 dígitos"],
    ], [1.5, 1.7, 3.7]))
    A(fig("tope", "Conexión de los cuatro bloques en el tope det_bareiss.", max_alto=2.2))

    # 5 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("5. Convenciones de los diagramas ASM", "h1"))
    A(tabla([
        ["Elemento", "Significado"],
        ["Caja de estado (rectángulo azul)", "Operaciones de todo el estado (salidas tipo Moore)."],
        ["Caja de decisión (rombo)", "Pregunta sobre una señal de estado. La salida 1 es la condición verdadera."],
        ["Caja de salida condicional (rectángulo redondeado naranja)",
         "Operación que solo ocurre si se toma ese camino (tipo Mealy), como en el ejemplo «ASM Mealy» de clase."],
        ["Bloque ASM (recuadro punteado)", "Caja de estado más sus decisiones y salidas condicionales: dura un ciclo de reloj."],
        ["Conector (círculo verde)", "Une hojas: A → s1, B → s2, C → s6, D → s7, E → s11, F → s13."],
        ["x ← expresión", "Carga de un registro; se hace efectiva en el flanco de subida al final del ciclo."],
        ["x = expresión", "Señal combinacional, por ejemplo final = 1."],
        ["RAM(f,c) ← dato", "Escritura en RAM A y RAM B (we = 1) en la posición fila f, columna c."],
        ["qa, qb", "Lectura de las RAM: qa = a(i,j) (RAM A) y qb = a(k,j) (RAM B)."],
    ], [2.3, 4.6]))
    A(Spacer(1, 4))
    A(P("Todas las decisiones de un bloque usan los valores que tienen los registros al comenzar el ciclo."))

    # 6 -----------------------------------------------------------------------
    A(P("6. Diagrama ASM del procesador de Bareiss", "h1"))
    A(P("6.1 Vista general", "h2"))
    A(fig("vista_general", "Diagrama de estados del ASM de Bareiss (14 estados).", max_alto=3.4))
    A(P("6.2 Verificación de las reglas del ASM", "h2"))
    A(P("Las reglas de clase son: (1) para cada estado presente y conjunto de decisiones solo se define un estado "
        "siguiente; (2) un camino de cajas de decisión debe llegar a un estado, sin ciclos. El programa "
        "doc/fuentes/diagramas.py revisa los mismos diagramas que se dibujan, antes de generar este documento:"))
    V(viñetas([
        "Cada caja de decisión tiene exactamente dos salidas, 1 y 0; cada caja de estado y de salida condicional tiene "
        "una sola salida. Así, cada combinación de decisiones lleva a un único estado siguiente (regla 1).",
        "Desde cada estado recorre todos los caminos de decisiones y salidas condicionales: ninguno vuelve a una caja "
        "ya visitada sin pasar por un estado, y todos terminan en un estado o en un conector (regla 2).",
        "Compara los estados siguientes de cada diagrama con las asignaciones [c]st <= …[/c] y [c]xs <= …[/c] del "
        "[c]case[/c] del VHDL, y la vista general con las hojas.",
    ]))
    estado_verif = ("Resultado: sin errores en los 20 estados (14 de Bareiss y 6 del XS3)." if not errores_asm
                    else "Resultado: ERRORES: " + "; ".join(errores_asm))
    A(P(f"[b]{estado_verif}[/b] La tabla de transiciones de la sección 6.3 la genera ese mismo programa."))

    hojas = [
        ("asm_hoja1", "Hoja 1: espera y carga de la matriz (s0 y s1)",
         "Mientras espera, s0 tiene en la ROM la dirección 00h (n). Cuando llega inicio carga n y empieza la copia. "
         "s1 recorre la ROM con el contador dira y los contadores i y j (por columnas); cada dato se escribe en las "
         "dos RAM a la vez. Al terminar deja k = 1 y j = 1, para que la RAM B lea a(1,1)."),
        ("asm_hoja2", "Hoja 2: pivote, búsqueda de fila e intercambio (s2 a s5)",
         "La RAM A siempre lee a(i,j) y la RAM B a(k,j). Con j = k, s2 lee el pivote a(k,k) en la RAM B y s3 busca "
         "a(i,k) ≠ 0 en la RAM A. El intercambio usa dos estados por columna: s4 escribe a(k,j) en la posición (i,j) "
         "y guarda a(i,j) en tmp; s5 escribe tmp en la posición (k,j)."),
        ("asm_hoja3", "Hoja 3: productos y resta (s6 a s10)",
         "s6 guarda a(i,k) en aik al empezar cada fila. Con un solo multiplicador, los dos productos se hacen en "
         "estados seguidos: s7 carga piv y a(i,j), s8 guarda t1 en sr_a y carga aik y a(k,j), s9 guarda t2 en sr_b. "
         "En s10 el sumador/restador da t1 − t2, que pasa a ser el residuo."),
        ("asm_hoja4", "Hoja 4: división, escritura de a(i,j) y final (s11 a s13)",
         "s11 es el lazo de la división: en cada ciclo el residuo se acerca a 0 restando p (si tienen el mismo signo) "
         "o sumándolo (si no), y el cociente aumenta. Cuando el residuo llega a 0, s12 escribe el cociente con su "
         "signo y avanza a la siguiente posición; en el último paso guarda el determinante. En s13 el ASM espera con "
         "final = 1."),
    ]
    for titulo_fig, titulo, texto in hojas:
        if titulo_fig != "asm_hoja1":
            A(PageBreak())
        A(P(titulo, "h2"))
        A(P(texto))
        A(fig(titulo_fig, titulo + ".", max_alto=6.4 if titulo_fig == "asm_hoja1" else 7.6))

    descripciones = [
        ("s0", "final = 0. Si inicio = 1: n ← a (ROM 00h); dira ← 1; i ← 1; j ← 1"),
        ("s1", "RAM(i,j) ← a con extensión de signo; dira ← dira + 1; avanza i, j; al final k ← 1, j ← 1, p ← 1, "
               "signo ← 0"),
        ("s2", "piv ← a(k,k) (qb); i ← k + 1; si a(k,k) ≠ 0: banco(k) ← a(k,k)"),
        ("s3", "Lee a(i,k) (qa); si ≠ 0: signo ← not signo; si = 0 e i = n: det ← 0; si no: i ← i + 1"),
        ("s4", "RAM(i,j) ← a(k,j) (qb); tmp ← a(i,j) (qa)"),
        ("s5", "RAM(k,j) ← tmp; si j = n: j ← k; si no: j ← j + 1"),
        ("s6", "aik ← a(i,k) (qa); j ← k + 1"),
        ("s7", "mul_a ← piv; mul_b ← a(i,j)"),
        ("s8", "sr_a ← producto (t1); mul_a ← aik; mul_b ← a(k,j)"),
        ("s9", "sr_b ← producto (t2); op ← 1"),
        ("s10", "sr_a ← t1 − t2 (residuo); sr_b ← p; sq ← signo(t1 − t2) xor signo(p); op ← not sq; cociente ← 0"),
        ("s11", "Si residuo ≠ 0: residuo ← residuo ∓ p; cociente ← cociente + 1. Si no: sr_b ← cociente; op ← 1"),
        ("s12", "RAM(i,j) ← ±cociente; avanza j, i o k; en el último paso det ← ±cociente"),
        ("s13", "final = 1. Si inicio = 1: dira ← 1; i ← 1; j ← 1"),
    ]
    A(PageBreak())
    A(P("6.3 Tabla de estados y transiciones", "h2"))
    A(tabla([["Estado", "Operaciones"]] + [list(d) for d in descripciones], [0.6, 6.3]))
    A(Spacer(1, 6))
    A(P("Transiciones leídas de los diagramas (una fila por camino de decisiones):"))
    A(tabla(tabla_transiciones(tabla_asm, ESTADOS_B), [0.6, 4.9, 1.4]))

    # 7 -----------------------------------------------------------------------
    A(PageBreak())
    A(P("7. ASM del XS3 (visualizador)", "h1"))
    A(P("El ASM del XS3 está en visualizador.vhd, separado del ASM de Bareiss. Usa sus propias unidades: un "
        "restador 0 − val para el valor absoluto, un sumador de 4 bits para el +3 y un comparador > 4. Tiene un "
        "estado por paso del documento XS3:"))
    A(tabla([
        ["Paso del documento XS3", "Estado", "Operación"],
        ["Antes de empezar: valor absoluto y signo", "x0", "bin ← |val|; neg ← val(31) (solo si final = 1)"],
        ["1. Inicializar el registro decimal en ceros", "x1", "dec ← 0 (40 bits); cont ← 0"],
        ["2. Colocar el MSB del registro binario en el LSB del registro decimal", "x2", "dec(0) ← bin(31)"],
        ["3. Revisar cada dígito: si es ≥ 5 (> 0100), sumarle 3 (0011)", "x3",
         "Un dígito por ciclo (d = 0 a 9): un multiplexor entrega el dígito d; si es > 4 se reemplaza por dígito + 3."],
        ["4. Correr a la izquierda y descartar el bit que sale; repetir desde el paso 2", "x4",
         "dec ← dec(38..0) & '0'; bin ← bin(30..0) & '0'; cont ← cont + 1; vuelve a x2"],
        ["5. Realizar únicamente el paso 2", "x2 con cont = 31",
         "En la pasada 32 por x2 entra el último bit y el ASM va a x5."],
        ["Resultado al display", "x5", "disp ← dec; disp_neg ← neg; vuelve a x0"],
    ], [2.6, 0.9, 3.4]))
    A(Spacer(1, 4))
    A(fig("asm_xs3", "Diagrama ASM del XS3.", max_alto=7.0))
    A(P("Funcionamiento en paralelo", "h2"))
    A(P("Los dos ASM usan el mismo reloj y corren al mismo tiempo. Mientras el procesador calcula (final = 0), el ASM "
        "XS3 espera en x0 y el display conserva el último valor. Cuando el procesador llega a s13 (final = 1), el ASM "
        "XS3 convierte el valor elegido con dir_p y vuelve a x0; como final sigue en 1, empieza otra conversión. Cada "
        "conversión tarda 376 ciclos (3,76 µs), así que al mover los switches el display cambia de inmediato. El "
        "procesador no espera al visualizador y no necesita señales extra: su caja negra sigue siendo la de clase."))
    A(P("Por qué se suma 3: si un dígito vale 5 o más, al correrlo a la izquierda quedaría en 10 o más, que no es un "
        "dígito BCD válido. Sumar 3 antes del corrimiento equivale a sumar 6 después, que es la corrección BCD, y "
        "hace que el exceso pase como acarreo al dígito siguiente. El registro binario es de 32 bits, así que el "
        "decimal necesita 10 dígitos (2[sup]31[/sup] = 2 147 483 648) y hay 32 pasadas por el paso 2."))
    A(P("Traza del XS3 para 362", "h2"))
    A(P("362 = 1 0110 1010[sub]2[/sub] tiene 9 bits significativos. En las pasadas cont = 0 a 22 solo entran ceros, por "
        "eso la tabla empieza en cont = 23. bin(31..23) son los 9 bits de arriba del registro binario; el de la "
        "izquierda, bin(31), es el que copia el paso 2. Del registro decimal se muestran los tres dígitos bajos."))
    filas, bcd_fin = traza_xs3(362)
    A(tabla([["cont", "Estado (paso)", "dec: C D U", "bin(31..23)", "Comentario"]] + filas,
            [0.45, 0.85, 1.25, 0.95, 3.4]))
    A(Spacer(1, 4))
    A(P(f"Resultado: dec = {bcd_fin[2]:04b} {bcd_fin[1]:04b} {bcd_fin[0]:04b} = {bcd_fin[2]} {bcd_fin[1]} {bcd_fin[0]}."))
    A(P("Transiciones del ASM XS3", "h2"))
    A(tabla(tabla_transiciones(tabla_asm, [f"x{i}" for i in range(6)]), [0.6, 4.9, 1.4]))

    # 8 -----------------------------------------------------------------------
    A(P("8. División por restas sucesivas", "h1"))
    A(P("La división está dentro del ASM de Bareiss y usa el sumador/restador con sus dos operaciones. No hace falta "
        "sacar valores absolutos: el residuo empieza en t1 − t2 y se acerca a 0 de a p por ciclo."))
    V(viñetas([
        "s10: residuo (sr_a) ← t1 − t2; sr_b ← p; cociente ← 0; sq ← signo(t1 − t2) xor signo(p). Si los dos tienen "
        "el mismo signo, op ← 1 (resta); si no, op ← 0 (suma).",
        "s11: si el residuo no es 0, residuo ← residuo − p (o + p) y cociente ← cociente + 1, y el ASM se queda en s11. "
        "Cuando llega a 0, carga sr_b ← cociente y op ← 1 para calcular 0 − cociente.",
        "s12: RAM(i,j) ← cociente si sq = 0, o 0 − cociente si sq = 1.",
    ]))
    A(P("Ejemplo: t1 − t2 = −12 y p = 3 (signos distintos, op = 0): −12 → −9 → −6 → −3 → 0, cociente = 4 y sq = 1, "
        "así que a(i,j) = −4 = −12 / 3."))
    A(P("Tarda |cociente| + 1 ciclos en s11. El lazo termina porque la división de Bareiss es exacta: el residuo "
        "llega justo a 0 (el enunciado lo garantiza)."))

    # 9 a 11: procedimiento UC + CD y sintesis ---------------------------------
    seccion_procesador(h, fig)
    seccion_visualizador(h, fig)
    seccion_sintesis(h, fig)

    # 12 ----------------------------------------------------------------------
    A(P("12. Interfaz con la tarjeta", "h1"))
    A(P("Divisor de frecuencia", "h2"))
    A(P("El oscilador de la Nexys A7 es de 100 MHz (pin E3, sección 5 del manual de la tarjeta). El bloque "
        "[c]divisor_frecuencia[/c] genera un pulso de un ciclo cada 1 ms (cuenta 100 000 ciclos) y una onda cuadrada "
        "de periodo 1 s (cambia cada 500 ms) que se ve en LD15. Los pulsos se usan como habilitación: todo el diseño "
        "trabaja con el mismo reloj, sin relojes derivados. El procesador trabaja a 100 MHz: con un reloj de 1 s, la "
        "matriz 5×5 por defecto (3 770 ciclos) tardaría más de una hora."))
    A(P("Antirrebote (uno solo)", "h2"))
    A(P("El bloque [c]antirrebote[/c] sincroniza el botón de inicio con dos flip-flops, lo muestrea cada 1 ms en un "
        "registro de 8 bits y cambia su nivel estable solo con 8 muestras iguales (8 ms sin rebote). Entrega un pulso "
        "de un ciclo en el flanco de subida del nivel estable: una pulsación arranca un solo cálculo."))
    A(P("Switches dir_p y display", "h2"))
    A(P("Los switches dir_p no pasan por ningún ASM de decisión: solo eligen la lectura del banco de pivotes y el "
        "valor que convierte el visualizador. Si un switch cambia en medio de una conversión, esa conversión puede "
        "salir mal, pero la siguiente (3,76 µs después) la corrige; por eso no llevan antirrebote ni sincronizador. "
        "El display cambia de dígito con cada pulso de 1 ms (barrido de 8 ms, 125 Hz): AN7 muestra el signo y AN6..AN0 "
        "los 7 dígitos. LD1 se enciende si los dígitos 7 a 9 del valor no son cero."))

    # 13 ----------------------------------------------------------------------
    A(P("13. Tiempo de ejecución", "h1"))
    V(viñetas([
        "Carga de la matriz (s0 y s1): n² + 1 ciclos.",
        "Por cada paso k: s2 (1 ciclo); si el pivote es cero, además la búsqueda en s3, 2 ciclos por columna "
        "intercambiada y otra lectura en s2. Por cada fila: s6 (1 ciclo).",
        "Por cada elemento actualizado: s7 a s10 y s12 (5 ciclos) más |cociente| + 1 ciclos de división en s11.",
        "XS3: 376 ciclos por conversión, en paralelo, sin detener al procesador.",
    ]))
    A(P("La división por restas sucesivas domina el tiempo cuando los valores son grandes. Las matrices de prueba "
        "terminan en menos de 40 µs, salvo la matriz 7 (valores cercanos a ±32), que tarda 19 millones de ciclos "
        "(0,19 s). Con valores «del orden de cientos de miles», como dijo el profesor, cada división tarda del orden de "
        "1 ms y el cálculo completo, del orden de decenas de milisegundos."))

    # 14 ----------------------------------------------------------------------
    A(P("14. Implementación en ISE 14.7 y la Nexys A7", "h1"))
    A(P("14.1 Proyecto", "h2"))
    V(viñetas([
        "File → New Project. Top-level source type: HDL. Family: Artix7 · Device: XC7A100T · Package: CSG324 · "
        "Speed: −1 · Synthesis: XST · Simulator: ISim · Preferred language: VHDL.",
        "Add Source: los cinco .vhd de src/ y src/nexys_a7.ucf (Implementation); sim/pkg_prueba.vhd y los testbench "
        "de sim/ (Simulation). procesador_bareiss.vhd tiene varias entidades en el mismo archivo; ISE las muestra "
        "debajo de procesador_bareiss en la jerarquía. Si ISE no elige det_bareiss como tope, usen «Set as Top Module».",
        "Synthesize (View RTL Schematic muestra los 4 bloques y, adentro del procesador, las dos RAM, el "
        "multiplicador y el sumador/restador) → Implement Design → Generate Programming File. Revisen que se cumpla "
        "la restricción de 10 ns (TS_sys_clk).",
        "Programación: usen iMPACT de ISE o el Hardware Manager de Vivado (Lab Edition) con el archivo .bit.",
    ]))
    A(P("14.2 Cambiar la matriz (día de la evaluación)", "h2"))
    V(viñetas([
        "Opción 1: editar la ROM en src/procesador_bareiss.vhd, entre las marcas «>>> INICIO ROM» y «<<< FIN ROM». La "
        "línea de 00h es n; las siguientes son a11, a21, …, an1, a12, … en complemento a 2 de 6 bits.",
        "Opción 2: [c]python3 sim/modelo_referencia.py rom \"2 1 3; 1 4 2; 3 2 5\"[/c] cambia ese bloque e imprime el "
        "determinante y los pivotes esperados.",
        "Simular con sim/tb_procesador.vhd: lee la ROM, calcula los valores esperados y los compara, sin modificar el "
        "testbench.",
        "Sintetizar y volver a programar la FPGA.",
    ]))
    A(P("14.3 Operación en la tarjeta", "h2"))
    V(viñetas([
        "Pulsar BTNU (rst). Poner SW2..SW0 en 000.",
        "Pulsar BTNC (inicio). Cuando termina, LD0 (final) se enciende y el display muestra el determinante.",
        "Poner SW2..SW0 en 1 a n para ver el pivote k; con k = n se ve otra vez el determinante.",
        "Si LD1 está encendido, el valor tiene más de 7 dígitos y se ven los 7 de abajo. LD15 parpadea cada segundo.",
    ]))
    A(P("14.4 Matrices de prueba", "h2"))
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
    A(P(f"src/procesador_bareiss.vhd trae la matriz {MATRIZ_POR_DEFECTO}. Para cargar otra de la lista: "
        "[c]python3 sim/modelo_referencia.py rom <número>[/c]."))
    A(P("14.5 Pines (src/nexys_a7.ucf)", "h2"))
    A(tabla([
        ["Señal", "Pines"],
        ["clk", "E3 (100 MHz)"],
        ["rst / inicio", "M18 (BTNU) / N17 (BTNC)"],
        ["dir_p(0..2)", "J15 (SW0), L16 (SW1), M13 (SW2)"],
        ["final / desborde / latido", "H17 (LD0) / K15 (LD1) / V11 (LD15)"],
        ["seg(0..6) = CA..CG, dp", "T10, R10, K16, K13, P15, T11, L18; DP = H15"],
        ["an(0..7)", "J17, J18, T9, J14, P14, T14, K2, U13"],
    ], [1.9, 5.0]))

    # 15 ----------------------------------------------------------------------
    A(P("15. Simulación", "h1"))
    V(viñetas([
        "[b]sim/tb_procesador.vhd[/b] (con sim/pkg_prueba.vhd) lee la matriz de la ROM, calcula el determinante y los "
        "pivotes esperados con un modelo de Bareiss en VHDL, pulsa inicio, compara det, recorre dir_p = 1 a n "
        "comparando cada pivote, comprueba que el pivote n sea el det y repite todo con un segundo inicio.",
        "[b]sim/probar_matrices.py[/b] pone cada una de las 8 matrices de prueba en una copia temporal de "
        "procesador_bareiss.vhd y corre ese testbench con GHDL.",
        "[b]sim/tb_visualizador.vhd[/b] prueba el XS3 y el display con 0, 7, 362, −170, ±9 999 999, 10 000 000, "
        "−17 121 828, ±2 147 483 647 y pivotes elegidos con dir_p, y comprueba que con final = 0 el display no cambie.",
        "[b]sim/tb_det_bareiss.vhd[/b] prueba la tarjeta completa con tiempos reales: pulsa BTNC con rebotes, comprueba "
        "que hay un solo cálculo y lee los 8 dígitos decodificando an y seg con dir_p = 0, 2, 3 y n.",
        "[b]doc/fuentes/uc_cd.py[/b] simula el camino de datos y la unidad de control de la sección 9 (las dos ROM) y "
        "obtiene los mismos resultados y ciclos que GHDL (sección 9.11).",
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
    A(P("Todos los pivotes también coinciden con el modelo. En la prueba de la tarjeta el display mostró "
        f"«{texto_display(bareiss(MATRICES[MATRIZ_POR_DEFECTO])[0])}» con un solo cálculo después de la pulsación con "
        "rebotes, y el visualizador pasó sus 15 comparaciones (ver sim/resultado_ghdl.txt). Para comprobar que las "
        "pruebas detectan errores se probaron tres fallas en una copia del diseño: el XS3 sumando 2 en lugar de 3, el "
        "último pivote sin el signo de los intercambios (matriz 2) y el antirrebote muestreando cada ciclo en lugar de "
        "cada 1 ms. Las tres se detectaron."))
    A(P("La síntesis genérica con GHDL ([c]ghdl --synth[/c]) terminó sin latches. En el procesador quedaron un "
        "multiplicador y un sumador de 50 bits, además de los contadores; cada RAM se infirió como memoria de 32 × 32. "
        "La estimación con Yosys para Artix-7 está en la sección 11.4."))

    # 16 ----------------------------------------------------------------------
    A(P("16. Puntos para confirmar con el profesor", "h1"))
    V(viñetas([
        "[b]Contadores.[/b] dira, i, j, k, cociente y los contadores del XS3 tienen su propio +1, como el i = i + 1 del "
        "ejemplo Sumax. Si deben pasar por el sumador/restador, cada incremento necesita un estado más.",
        "[b]Archivo del tope.[/b] Además de los cuatro bloques está det_bareiss.vhd, que solo los conecta; ISE lo "
        "necesita para asignar los pines.",
        "[b]Salidas en binario.[/b] det y pivote salen del procesador en binario; la conversión a decimal la hace el "
        "visualizador.",
        "[b]Dos RAM.[/b] Son dos instancias del modelo del profesor con el mismo contenido: la RAM A lee a(i,j) y la "
        "RAM B lee a(k,j). Con una sola RAM habría que agregar un estado por elemento (en s8) y por columna "
        "intercambiada (en s4).",
        "[b]Dirección de la RAM.[/b] a(f,c) se guarda en f & c(1 downto 0), o en \"11\" & f para la columna 5. Así no "
        "hace falta multiplicar ni sumar para ubicar un elemento; quedan 7 de las 32 palabras sin usar.",
        "[b]División con signo.[/b] En lugar de dividir valores absolutos, el residuo se acerca a 0 sumando o restando "
        "p. Esto usa las dos operaciones del sumador/restador y termina porque la división de Bareiss es exacta.",
        "[b]Multiplicador.[/b] Es combinacional ([c]*[/c] de std_logic_signed sobre std_logic_vector, no el tipo "
        "signed). Si lo quieren por sumas y desplazamientos, hay que cambiarlo.",
        "[b]Unidad de control Mealy.[/b] El ASM tiene cajas de salida condicional, así que la ROM de salida recibe 8 "
        "condiciones además del estado (4096 × 41). Si el profesor quiere una UC Moore, cada caja condicional pasa a "
        "ser un estado y la ROM de salida queda de 2^n palabras.",
        "[b]Banco de pivotes.[/b] b1 a b4 guardan los pivotes 1 a n − 1; el pivote n es el determinante, así que con "
        "dir_p = n la salida pivote muestra det.",
    ]))
    A(P("Limitaciones", "h2"))
    V(viñetas([
        "[b]No se ejecutó ISE.[/b] El diseño se verificó con GHDL 4.1 (simulación con [c]-fsynopsys -fexplicit[/c] y "
        "síntesis genérica). Hay que sintetizar en ISE 14.7 y revisar el reporte de tiempos a 100 MHz. Los caminos "
        "más largos pasan por el multiplicador de 25 × 25 y por el sumador de 50 bits; si no se cumplen los 10 ns, "
        "generen un reloj de 50 MHz con el Clocking Wizard y pongan PERIOD = 20 ns.",
        "[b]Contenido inicial de la RAM.[/b] El modelo del profesor no la inicializa; en simulación las posiciones que "
        "no se han escrito valen 'U'. El ASM solo lee posiciones que ya escribió.",
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

"""Pseudoalgoritmos del informe (draw.io), con el estilo de los ejemplos del curso:
líneas en mayúsculas, bloques entre corchetes y recuadros de colores que
agrupan cada parte del algoritmo (el texto del informe se refiere a ellos por
el color)."""
import drawio as D

F = D.F
LINEA = F + "text;html=1;align=left;verticalAlign=middle;whiteSpace=nowrap;fontSize=12.5;spacing=0;"
NOTA = F + "text;html=1;align=left;verticalAlign=middle;whiteSpace=nowrap;fontSize=10.5;spacing=0;" \
           "fontColor=#808080;fontStyle=2;"
ALTO = 18           # alto de cada línea
SANGRIA = 17        # px por nivel

ESPACIO = "espacio"          # separación entre dos recuadros
ROSA, ROJO, AZUL, VERDE, AMARILLO, NARANJA = "#E040E0", "#E02020", "#2F5597", "#2E9E3E", "#E0B000", "#E07000"


def columna(d, x, y, lineas, x_nota=255):
    """lineas: (nivel, texto[, nota]). Devuelve la y de arriba de cada línea."""
    ys = []
    yy = y - ALTO
    for ln in lineas:
        if ln == ESPACIO:
            yy += 10
            continue
        nivel, texto = ln[0], ln[1]
        yy += ALTO
        ys.append(yy)
        d.nodo(x + 10 + nivel * SANGRIA, yy, 300, ALTO, texto, LINEA)
        if len(ln) > 2:
            d.nodo(x + x_nota, yy, 70, ALTO, ln[2], NOTA)
    return ys


def marco(d, x, y0, y1, w, color, grosor=1.6):
    d.celdas.insert(0, f'<mxCell id="m{d._id()}" value="" style="rounded=0;html=1;fillColor=none;strokeColor={color};'
                       f'strokeWidth={grosor};" vertex="1" parent="1"><mxGeometry x="{x}" y="{y0}" width="{w}" '
                       f'height="{y1 - y0}" as="geometry"/></mxCell>')


def pseudo_bareiss():
    d = D.Diagrama("pseudo_bareiss")
    izq = [
        (0, "FINAL = 0"),
        (0, "SI INICIO = 1"),
        (0, "[ N = ROM(0)"),
        (1, "DIRA = 1"),
        (1, "PARA J = 1 : N"),
        (1, "[ PARA I = 1 : N"),
        (2, "[ RAM(I,J) = ROM(DIRA)"),
        (3, "DIRA = DIRA + 1"),
        (2, "]"),
        (1, "]"),
        (1, "P = 1"),
        (1, "SIGNO = 0"),
        ESPACIO,
        (1, "PARA K = 1 : N − 1"),
        (1, "[ PIV = RAM(K,K)"),
        (2, "I = K + 1"),
        (2, "SI PIV = 0"),
        (2, "[ MIENTRAS RAM(I,K) = 0"),
        (3, "[ SI I = N"),
        (4, "[ DET = 0"),
        (5, "FINAL = 1 ; terminar ]"),
        (4, "I = I + 1"),
        (3, "]"),
        (3, "SIGNO = NOT SIGNO"),
        (3, "PARA J = K : N"),
        (3, "[ TMP = RAM(I,J)"),
        (4, "RAM(I,J) = RAM(K,J)"),
        (4, "RAM(K,J) = TMP"),
        (3, "]"),
        (3, "PIV = RAM(K,K)"),
        (2, "]"),
        (2, "BANCO(K) = PIV"),
        (2, "<i>(sigue en la otra columna)</i>"),
    ]
    der = [
        (2, "PARA I = K + 1 : N"),
        (2, "[ AIK = RAM(I,K)"),
        (3, "PARA J = K + 1 : N"),
        (3, "[ X = PIV ;  Y = RAM(I,J)"),
        (4, "R = X * Y"),
        (4, "X = AIK ;  Y = RAM(K,J)"),
        (4, "S = X * Y"),
        (4, "R = R − S"),
        (4, "S = P ;  COCIENTE = 0"),
        (4, "SQ = R(49) ⊕ S(49)"),
        (4, "SI K + 1 = N Y SIGNO = 1"),
        (4, "[ SQ = NOT SQ ]"),
        (4, "SI R(49) = S(49)"),
        (4, "[ T = 0 ]"),
        (4, "SI NO"),
        (4, "[ T = R ;  R = 0 ]"),
        (4, "MIENTRAS R ≠ T"),
        (4, "[ R = R − S"),
        (5, "SI SQ = 0"),
        (5, "[ COCIENTE = COCIENTE + 1 ]"),
        (5, "SI NO"),
        (5, "[ COCIENTE = COCIENTE − 1 ]"),
        (4, "]"),
        (4, "RAM(I,J) = COCIENTE"),
        (3, "]"),
        (2, "]"),
        (2, "P = PIV"),
        (1, "]"),
        ESPACIO,
        (1, "DET = COCIENTE"),
        (1, "FINAL = 1"),
        (0, "]"),
    ]
    W = 330
    y = 12
    ys = columna(d, 0, y, izq)
    marco(d, 2, ys[0] - 4, ys[11] + ALTO + 3, W - 4, ROSA)
    marco(d, 2 + SANGRIA, ys[12] - 3, ys[31] + ALTO + 3, W - 4 - SANGRIA, ROJO)
    marco(d, 2 + 2 * SANGRIA, ys[15] - 1, ys[29] + ALTO + 1, W - 8 - 2 * SANGRIA, AZUL)
    x2 = W + 30
    ys2 = columna(d, x2, y + 6, der)
    marco(d, x2 + 2 + SANGRIA, ys2[0] - 9, ys2[27] + ALTO + 3, W - 4 - SANGRIA, ROJO)
    marco(d, x2 + 2 + 2 * SANGRIA, ys2[0] - 3, ys2[25] + ALTO + 1, W - 8 - 2 * SANGRIA, VERDE)
    marco(d, x2 + 2 + 4 * SANGRIA, ys2[8] - 1, ys2[22] + ALTO + 1, W - 14 - 4 * SANGRIA, AMARILLO)
    marco(d, x2 + 2 + SANGRIA, ys2[28] - 3, ys2[29] + ALTO + 3, W - 4 - SANGRIA, NARANJA)
    return d


def pseudo_xs3():
    d = D.Diagrama("pseudo_xs3")
    lineas = [
        (0, "<i>VAL = DET si DIR_P = 0; si no, VAL = PIVOTE</i>"),
        ESPACIO,
        (0, "SI FINAL = 1"),
        (0, "[ NEG = VAL(31)"),
        (1, "SI VAL(31) = 1"),
        (1, "[ BIN = 0 − VAL ]"),
        (1, "SI NO"),
        (1, "[ BIN = VAL ]"),
        ESPACIO,
        (1, "DEC = 0 ;  CONT = 0", "PASO 1"),
        (1, "DEC(0) = BIN(31)", "PASO 2"),
        (1, "MIENTRAS CONT ≠ 31", "PASO 5"),
        (1, "[ PARA D = 0 : 9", "PASO 3"),
        (2, "[ SI DÍGITO(D) &gt; 4"),
        (3, "[ DÍGITO(D) = DÍGITO(D) + 3 ]"),
        (2, "]"),
        (2, "DEC = DEC &lt;&lt; 1 ;  BIN = BIN &lt;&lt; 1", "PASO 4"),
        (2, "CONT = CONT + 1"),
        (2, "DEC(0) = BIN(31)", "PASO 2"),
        (1, "]"),
        ESPACIO,
        (1, "DISP = DEC ;  DISP_NEG = NEG"),
        (0, "]"),
        (0, "<i>(se repite mientras FINAL = 1)</i>"),
    ]
    W = 380
    ys = columna(d, 0, 12, lineas, x_nota=W - 62)
    marco(d, 2, ys[1] - 4, ys[6] + ALTO + 3, W - 4, ROSA)
    marco(d, 2 + SANGRIA, ys[7] - 3, ys[17] + ALTO + 3, W - 4 - SANGRIA, ROJO)
    marco(d, 14 + SANGRIA, ys[10] - 1, ys[13] + ALTO + 1, W - 20 - SANGRIA, AZUL)
    marco(d, 2 + SANGRIA, ys[18] - 3, ys[18] + ALTO + 3, W - 4 - SANGRIA, NARANJA)
    return d


def todas():
    return [pseudo_bareiss(), pseudo_xs3()]

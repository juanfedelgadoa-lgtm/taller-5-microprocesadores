"""Pequeña ayuda para escribir archivos .drawio (mxGraph) desde Python.

Cada figura del informe se arma con nodos (cajas, rombos, MUX, registros...) y
aristas ortogonales conectadas a los nodos, para que en draw.io se puedan mover
las cajas sin perder las conexiones.
"""
from xml.sax.saxutils import escape, quoteattr

# ---------------------------------------------------------------------------
# Estilos (colores parecidos a los del informe del Taller 4)
# ---------------------------------------------------------------------------
F = "fontFamily=Helvetica;"
ESTADO = F + "rounded=0;whiteSpace=wrap;html=1;fillColor=#EAF1F8;strokeColor=#5B7FA6;fontSize=11;"
DECISION = F + "rhombus;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D6B656;fontSize=11;"
CONDICIONAL = F + "rounded=1;arcSize=45;whiteSpace=wrap;html=1;fillColor=#FDEBD3;strokeColor=#E08A2E;fontSize=10.5;"
CONECTOR = F + "rounded=1;arcSize=30;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#5B7FA6;fontSize=10.5;"
BLOQUE = F + ("rounded=0;html=1;fillColor=none;dashed=1;dashPattern=6 4;strokeColor=#E08A2E;"
              "verticalAlign=top;align=right;spacingRight=4;fontColor=#E08A2E;fontStyle=1;fontSize=11;")
CAJA = F + "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#333333;fontSize=12;"
CAJA_AZUL = F + "rounded=0;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize=11;"
CAJA_VERDE = F + "rounded=0;whiteSpace=wrap;html=1;fillColor=#D5E8D4;strokeColor=#82B366;fontSize=11;"
CAJA_LILA = F + "rounded=0;whiteSpace=wrap;html=1;fillColor=#E1D5E7;strokeColor=#9673A6;fontSize=11;"
CAJA_GRIS = F + "rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;"
PUERTO = F + "rounded=1;arcSize=25;whiteSpace=wrap;html=1;fillColor=#EAF1F8;strokeColor=#5B7FA6;fontSize=10.5;"
REGISTRO = F + "rounded=0;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize=11;fontStyle=1;"
UNIDAD = F + "rounded=1;arcSize=20;whiteSpace=wrap;html=1;fillColor=#D5E8D4;strokeColor=#82B366;fontSize=11;"
MEMORIA = F + "rounded=0;whiteSpace=wrap;html=1;fillColor=#E1D5E7;strokeColor=#9673A6;fontSize=11;"
MUX = F + ("shape=trapezoid;perimeter=trapezoidPerimeter;whiteSpace=wrap;html=1;fixedSize=1;size=10;flipV=1;"
           "fillColor=#F5F5F5;strokeColor=#666666;fontSize=9;verticalAlign=bottom;spacingBottom=1;")
TEXTO = F + "text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;fontSize=10;"
TEXTO_IZQ = F + "text;html=1;align=left;verticalAlign=middle;whiteSpace=nowrap;fontSize=10;"
TEXTO_DER = F + "text;html=1;align=right;verticalAlign=middle;whiteSpace=nowrap;fontSize=10;"
ROJO = "fontColor=#C00000;"
RELOJ = F + "triangle;whiteSpace=wrap;html=1;direction=north;fillColor=#FFFFFF;strokeColor=#6C8EBF;"

ARISTA = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;endSize=5;"
          "strokeColor=#333333;fontSize=9;" + F)
ARISTA_RECTA = "rounded=0;html=1;endArrow=block;endFill=1;endSize=5;strokeColor=#333333;fontSize=9;" + F
CONTROL = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=open;endSize=5;dashed=1;"
           "strokeColor=#C00000;fontColor=#C00000;fontSize=9;" + F)
SIN_FLECHA = "endArrow=none;"


class Diagrama:
    def __init__(self, nombre):
        self.nombre = nombre
        self.celdas = []
        self.n = 0
        self.geo = {}            # id -> (x, y, w, h)
        self.tipo = {}           # id -> etiqueta de tipo (para revisar los ASM)
        self.texto = {}
        self.aristas = []        # (id, origen, destino, etiqueta)

    def _id(self, pref="c"):
        self.n += 1
        return f"{pref}{self.n}"

    # -- nodos ---------------------------------------------------------------
    def nodo(self, x, y, w, h, texto, estilo, tipo=None, id=None):
        id = id or self._id()
        self.celdas.append(f'<mxCell id="{id}" value={quoteattr(texto)} style={quoteattr(estilo)} vertex="1" '
                           f'parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        self.geo[id] = (x, y, w, h)
        self.tipo[id] = tipo
        self.texto[id] = texto
        return id

    def etiqueta(self, x, y, w, h, texto, estilo=TEXTO):
        return self.nodo(x, y, w, h, texto, estilo)

    # -- aristas -------------------------------------------------------------
    def arista(self, a, b, texto="", estilo=ARISTA, salida=None, entrada=None, puntos=(), etiqueta_pos=None):
        """Arista de a a b. salida/entrada = (x, y) relativos (0..1) en el borde."""
        id = self._id("e")
        est = estilo
        if salida:
            est += f"exitX={salida[0]};exitY={salida[1]};exitDx=0;exitDy=0;"
        if entrada:
            est += f"entryX={entrada[0]};entryY={entrada[1]};entryDx=0;entryDy=0;"
        pts = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in puntos)
        arr = f'<Array as="points">{pts}</Array>' if puntos else ""
        geo = f'<mxGeometry relative="1" as="geometry">{arr}</mxGeometry>'
        if etiqueta_pos is not None:
            geo = (f'<mxGeometry x="{etiqueta_pos[0]}" y="{etiqueta_pos[1]}" relative="1" as="geometry">'
                   f'{arr}<mxPoint as="offset"/></mxGeometry>')
        self.celdas.append(f'<mxCell id="{id}" value={quoteattr(texto)} style={quoteattr(est)} edge="1" parent="1" '
                           f'source="{a}" target="{b}">{geo}</mxCell>')
        self.aristas.append((id, a, b, texto))
        return id

    def linea(self, p1, p2, texto="", estilo=ARISTA, puntos=()):
        """Arista libre entre dos puntos (no queda pegada a ningún nodo)."""
        id = self._id("e")
        pts = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in puntos)
        arr = f'<Array as="points">{pts}</Array>' if puntos else ""
        self.celdas.append(
            f'<mxCell id="{id}" value={quoteattr(texto)} style={quoteattr(estilo)} edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry"><mxPoint x="{p1[0]}" y="{p1[1]}" as="sourcePoint"/>'
            f'<mxPoint x="{p2[0]}" y="{p2[1]}" as="targetPoint"/>{arr}</mxGeometry></mxCell>')
        return id

    def bloque(self, ids, nombre, margen=8, extra=(0, 0, 0, 0)):
        """Recuadro punteado alrededor de las cajas de un bloque ASM."""
        xs = [self.geo[i][0] for i in ids]
        ys = [self.geo[i][1] for i in ids]
        x2 = [self.geo[i][0] + self.geo[i][2] for i in ids]
        y2 = [self.geo[i][1] + self.geo[i][3] for i in ids]
        x, y = min(xs) - margen - extra[0], min(ys) - margen - 14 - extra[1]
        w = max(x2) + margen + extra[2] - x
        h = max(y2) + margen + extra[3] - y
        id = self._id("b")
        # va primero para quedar detrás de las cajas
        self.celdas.insert(0, f'<mxCell id="{id}" value={quoteattr(nombre)} style={quoteattr(BLOQUE)} vertex="1" '
                              f'parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return id

    def xml(self):
        cuerpo = "\n".join(self.celdas)
        return (f'<mxfile host="drawio" type="device"><diagram id="{self.nombre}" name={quoteattr(self.nombre)}>'
                f'<mxGraphModel dx="1000" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
                f'arrows="1" fold="1" page="0" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">'
                f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>\n{cuerpo}\n</root></mxGraphModel></diagram></mxfile>\n')

    def guardar(self, carpeta):
        ruta = carpeta / f"{self.nombre}.drawio"
        ruta.write_text(self.xml(), encoding="utf-8")
        return ruta


def bus(n):
    """Etiqueta del ancho de un bus."""
    return f"{n}"

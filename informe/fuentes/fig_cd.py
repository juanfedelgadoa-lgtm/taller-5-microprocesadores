"""Camino de datos dibujado como circuito (draw.io).

Convenciones de las figuras:
  * MUX: trapecio con las entradas arriba (el número es el código del selector)
    y la salida abajo; el selector llega por un lado.
  * Registro: rectángulo azul con el triángulo de reloj. Todos los registros
    comparten clk y rst (no se dibujan).
  * Rojo punteado = señal de control que viene de la UC (campo de la PC).
  * Azul = señal de estado que va a la UC.
  * Punto negro = unión de cables. Un cruce sin punto no es conexión.
  * Una etiqueta con el mismo nombre en dos sitios es el mismo cable; el nombre
    de un registro como etiqueta es su salida.
"""
import re

import drawio as D

# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------
F = D.F
NET = F + "text;html=1;align=center;verticalAlign=middle;whiteSpace=nowrap;fontSize=9.5;"
NET_IZQ = NET + "align=right;"
NET_DER = NET + "align=left;"
CTRL = "fontColor=#C00000;"
ESTA = "fontColor=#1F4E9A;fontStyle=1;"
NOMBRE = F + "text;html=1;align=left;verticalAlign=middle;whiteSpace=nowrap;fontSize=8.5;fontColor=#777777;fontStyle=2;"
BITS = F + "text;html=1;align=left;verticalAlign=middle;whiteSpace=nowrap;fontSize=8;fontColor=#5B7FA6;"
NUM = F + "text;html=1;align=center;verticalAlign=top;fontSize=7.5;fontColor=#555555;spacing=0;spacingTop=1;"
MUXS = F + ("shape=trapezoid;perimeter=rectanglePerimeter;html=1;fixedSize=1;size=8;flipV=1;"
            "fillColor=#F5F5F5;strokeColor=#555555;")
REG = F + "rounded=0;html=1;whiteSpace=wrap;fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize=10.5;"
RELOJ = "triangle;html=1;direction=east;fillColor=#FFFFFF;strokeColor=#6C8EBF;"
SUMA = F + "ellipse;html=1;whiteSpace=wrap;fillColor=#D5E8D4;strokeColor=#82B366;fontSize=10;"
UNI = F + "rounded=0;html=1;whiteSpace=wrap;fillColor=#D5E8D4;strokeColor=#82B366;fontSize=10;"
COMP = F + "rounded=0;html=1;whiteSpace=wrap;fillColor=#FFF2CC;strokeColor=#D6B656;fontSize=10;"
LOG = F + "rounded=1;arcSize=40;html=1;whiteSpace=wrap;fillColor=#FFFFFF;strokeColor=#555555;fontSize=9;"
MEM = F + "rounded=0;html=1;whiteSpace=wrap;fillColor=#E1D5E7;strokeColor=#9673A6;fontSize=10.5;"
PORT_T = F + "text;html=1;whiteSpace=nowrap;fontSize=8;fontColor=#555555;spacing=1;"
PUERTO = F + "rounded=1;arcSize=30;html=1;whiteSpace=wrap;fillColor=#EAF1F8;strokeColor=#5B7FA6;fontSize=10;"
PUNTO = "ellipse;html=1;fillColor=#333333;strokeColor=#333333;"
NOTA = F + "text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;fontSize=9;fontColor=#555555;"
TITULO = F + "text;html=1;align=left;verticalAlign=middle;whiteSpace=nowrap;fontSize=10.5;fontStyle=1;fontColor=#333333;"

W = D.ARISTA
WC = D.CONTROL
WS = D.ARISTA + "strokeColor=#1F4E9A;"


def plano(t):
    return re.sub(r"<[^>]+>", "", t).replace("&amp;", "&").replace("&quot;", '"')


def ancho(t, fs=9.5):
    return round(fs * 0.56 * len(plano(t)) + 8)


# ---------------------------------------------------------------------------
# Piezas básicas
# ---------------------------------------------------------------------------
def net(d, cx, y, t, est="", h=14):
    """Etiqueta de red centrada en cx (borde de arriba en y)."""
    w = ancho(t)
    return d.nodo(cx - w / 2, y, w, h, t, NET + est)


def net_izq(d, xder, cy, t, est="", h=14):
    """Etiqueta de red con el borde derecho en xder."""
    w = ancho(t)
    return d.nodo(xder - w, cy - h / 2, w, h, t, NET_IZQ + est)


def net_der(d, xizq, cy, t, est="", h=14):
    w = ancho(t)
    return d.nodo(xizq, cy - h / 2, w, h, t, NET_DER + est)


def nombre(d, x, y, t, est=NOMBRE):
    """Nombre de un cable (texto pequeño junto a la línea)."""
    return d.nodo(x, y - 6, ancho(t, 8.5), 12, t, est)


def bits(d, x, y, n):
    return d.nodo(x, y - 6, 24, 12, str(n), BITS)


def punto(d, x, y):
    i = d.nodo(x - 3, y - 3, 6, 6, "", PUNTO)
    d.__dict__.setdefault("puntos", set()).add(i)
    return i


def cable(d, a, b, sal=None, ent=None, pts=(), est=W, texto=""):
    s = est
    puntos = d.__dict__.get("puntos", set())
    if a in puntos:
        sal = (0.5, 0.5)
        s += "exitPerimeter=0;"
    if b in puntos:
        ent = (0.5, 0.5)
        s += "entryPerimeter=0;endArrow=none;"
    return d.arista(a, b, texto, s, salida=sal, entrada=ent, puntos=pts)


def ancho_mux(entradas, paso=None):
    n = len(entradas)
    paso = paso or max(24, max(ancho(e) if isinstance(e, str) else 24 for e in entradas) + 2)
    return max(40, paso * n), paso


class Mux:
    def __init__(self, id, xs, x0, w, y, h):
        self.id, self.xs, self.x0, self.w, self.y, self.h = id, xs, x0, w, y, h

    def ent(self, k):
        return (round((self.xs[k] - self.x0) / self.w, 4), 0)

    def lado(self, izq):
        dx = round(4 / self.w, 4)
        return (dx, 0.5) if izq else (1 - dx, 0.5)

    @property
    def cy(self):
        return self.y + self.h / 2


def mux(d, cx, y, entradas, sel, codigos=None, paso=None, h=22, sel_izq=False, sel_est=CTRL, alto_ent=30):
    """MUX con entradas arriba. Cada entrada es un texto (etiqueta de red), None
    (se conecta después) o (id, salida) para cablear un nodo."""
    n = len(entradas)
    w, paso = ancho_mux(entradas, paso)
    x0 = cx - w / 2
    m = d.nodo(x0, y, w, h, "", MUXS)
    nb = max(1, (n - 1).bit_length())
    codigos = codigos or [format(k, f"0{nb}b") for k in range(n)]
    xs = []
    for k, e in enumerate(entradas):
        xin = x0 + (w - paso * n) / 2 + paso * (k + 0.5)
        xs.append(xin)
        d.nodo(xin - 8, y, 16, 10, codigos[k], NUM)
    M = Mux(m, xs, x0, w, y, h)
    for k, e in enumerate(entradas):
        if e is None:
            continue
        if isinstance(e, str):
            lab = net(d, xs[k], y - alto_ent, e)
            cable(d, lab, m, (0.5, 1), M.ent(k))
        else:
            cable(d, e[0], m, e[1], M.ent(k))
    if sel:
        estilo = (WC if sel_est == CTRL else W) + "entryPerimeter=0;"
        if sel_izq:
            lab = net_izq(d, x0 - 6, y + h / 2, sel, sel_est)
            d.arista(lab, m, "", estilo, salida=(1, 0.5), entrada=M.lado(True))
        else:
            lab = net_der(d, x0 + w + 6, y + h / 2, sel, sel_est)
            d.arista(lab, m, "", estilo, salida=(0, 0.5), entrada=M.lado(False))
    return M


def registro(d, cx, y, texto, ld, w=None, h=26, ld_izq=True, ld_est=CTRL):
    w = w or max(54, ancho(texto, 10.5) + 18)
    r = d.nodo(cx - w / 2, y, w, h, texto, REG)
    d.nodo(cx - w / 2, y + h - 12, 7, 10, "", RELOJ)
    if ld:
        est = WC if ld_est == CTRL else W
        if ld_izq:
            lab = net_izq(d, cx - w / 2 - 8, y + h / 2 - 3, ld, ld_est)
            d.arista(lab, r, "", est, salida=(1, 0.5), entrada=(0, round(0.5 - 3 / h, 3)))
        else:
            lab = net_der(d, cx + w / 2 + 8, y + h / 2, ld, ld_est)
            d.arista(lab, r, "", est, salida=(0, 0.5), entrada=(1, 0.5))
    return r


def registro_h(d, x, cy, texto, ld, w=None, h=26, ld_est=CTRL):
    """Registro con la entrada por la izquierda, la salida por la derecha y la carga
    por arriba."""
    w = w or max(54, ancho(texto, 10.5) + 18)
    r = d.nodo(x, cy - h / 2, w, h, texto, REG)
    d.nodo(x, cy + h / 2 - 12, 7, 10, "", RELOJ)
    if ld:
        lab = net(d, x + w / 2, cy - h / 2 - 26, ld, ld_est)
        cable(d, lab, r, (0.5, 1), (0.5, 0), est=WC if ld_est == CTRL else W)
    return r


def unidad(d, x, cy, entradas, texto, salida=None, salida_est="", forma=COMP, w=34, h=None, gap=12):
    """Bloque combinacional: entradas por la izquierda (etiquetas o (id, salida)) y
    salida por la derecha hacia una etiqueta."""
    n = len(entradas)
    h = h or max(24, 14 * n + 6)
    u = d.nodo(x, cy - h / 2, w, h, texto, forma)
    for k, e in enumerate(entradas):
        yk = cy + (k - (n - 1) / 2) * 14
        rel = (0, round((yk - (cy - h / 2)) / h, 4))
        if isinstance(e, str):
            lab = net_izq(d, x - gap, yk, e)
            cable(d, lab, u, (1, 0.5), rel)
        else:
            cable(d, e[0], u, e[1], rel)
    o = None
    if salida:
        o = net_der(d, x + w + gap, cy, salida, salida_est)
        cable(d, u, o, (1, 0.5), (0, 0.5), est=WS if salida_est == ESTA else W)
    return u, o


def columna(d, cx, y, texto, entradas, sel, ld, inc=None, inc_ctrl=None, comps=(), salida=None,
            salida_est="", codigos=None, w_reg=None, nombre_reg=None, nombre_inc=None):
    """Rebanada vertical: entradas -> MUX -> registro -> (incrementador realimentado)
    -> comparadores. '@inc' en entradas marca la entrada que llega del incrementador.
    comps: (fuente 'reg' o 'inc', otra entrada, símbolo, señal de salida, estilo)."""
    out = {}
    if len(entradas) > 1:
        ent = [None if e == "@inc" else e for e in entradas]
        M = mux(d, cx, y + 30, ent, sel, codigos, sel_izq=True)
        r = registro(d, cx, y + 70, texto, ld, w_reg)
        cable(d, M.id, r, (0.5, 1), (0.5, 0))
        out["mux"] = M
    else:
        M = None
        lab = net(d, cx, y + 40, entradas[0])
        r = registro(d, cx, y + 70, texto, ld, w_reg)
        cable(d, lab, r, (0.5, 1), (0.5, 0))
    out["reg"] = r
    wr = d.geo[r][2]
    fuente, fsal = r, (0.5, 1)
    yj = y + 112
    if inc:
        p1 = punto(d, cx, yj)
        cable(d, r, p1, (0.5, 1))
        u = d.nodo(cx + wr / 2 + 2, yj - 12, 28, 24, inc, SUMA)
        cable(d, p1, u, ent=(0, 0.5))
        xr = max(cx + wr / 2 + 2 + 28 + 10, M.x0 + M.w + 10)
        k = entradas.index("@inc")
        if inc_ctrl:
            lab = net(d, cx + wr / 2 + 16, yj + 22, inc_ctrl)
            cable(d, lab, u, (0.5, 0), (0.5, 1))
        if any(c[0] == "inc" for c in comps):
            p2 = punto(d, xr, yj)
            cable(d, u, p2, (1, 0.5))
            cable(d, p2, M.id, ent=M.ent(k), pts=[(xr, y - 6), (M.xs[k], y - 6)])
            out["inc_fuente"] = p2
        else:
            cable(d, u, M.id, (1, 0.5), M.ent(k), pts=[(xr, yj), (xr, y - 6), (M.xs[k], y - 6)])
        if nombre_inc:
            w_n = ancho(nombre_inc, 8.5)
            d.nodo((M.xs[k] + xr) / 2 - w_n / 2, y - 20, w_n, 12, nombre_inc, NOMBRE + "align=center;")
        out["inc"], out["xr"] = u, xr
        fuente, fsal = p1, None
    out["fuente"] = fuente
    if nombre_reg:
        nombre(d, cx + 4, y + 104 if not inc else yj + 12, nombre_reg)
    yc = y + 134
    for src, otra, simb, sal, est in comps:
        if src == "reg":
            xc, f, fs = cx, fuente, fsal
        else:
            xc, f, fs = out["xr"], out["inc_fuente"], None
        c = d.nodo(xc - 17, yc, 34, 24, simb, COMP)
        cable(d, f, c, fs, (0.5, 0))
        lab = net_izq(d, xc - 27, yc + 12, otra)
        cable(d, lab, c, (1, 0.5), (0, 0.5))
        o = net_der(d, xc + 27, yc + 12, sal, est)
        cable(d, c, o, (1, 0.5), (0, 0.5), est=WS if est == ESTA else W)
        out.setdefault("comps", []).append(c)
    if salida:
        o = net(d, cx, y + 134, salida, salida_est)
        cable(d, fuente, o, fsal, (0.5, 0))
        out["salida"] = o
    return out


def medir(func, *args, **kw):
    """Ancho que ocupa una pieza dibujada en x = 0: (x mínimo, x máximo)."""
    t = D.Diagrama("t")
    func(t, 0, *args, **kw)
    xs = [g[0] for g in t.geo.values()]
    xe = [g[0] + g[2] for g in t.geo.values()]
    return min(xs), max(xe)


def fila(d, x, y, piezas, sep=24):
    """Coloca columnas una al lado de la otra. piezas: (func, args, kwargs)."""
    res = []
    for func, args, kw in piezas:
        x0, x1 = medir(lambda t, cx: func(t, cx, y, *args, **kw))
        cx = x - x0
        res.append(func(d, cx, y, *args, **kw))
        x = cx + x1 + sep
    return res, x - sep


def leyenda(d, x, y, w):
    t = ("<font color='#C00000'><b>rojo punteado</b>: control desde la UC</font> · "
         "<font color='#1F4E9A'><b>azul</b>: estado hacia la UC</font> · "
         "punto = unión de cables · una etiqueta repetida es el mismo cable · "
         "todos los registros usan clk y rst")
    return d.nodo(x, y, w, 28, t, NOTA)


def caja_mem(d, x, y, w, h, titulo, puertos):
    """Memoria con nombres de puertos. puertos: {nombre: (lado, rel)}; lado = t, b, l, r."""
    m = d.nodo(x, y, w, h, titulo, MEM)
    for nombre_p, (lado, rel) in puertos.items():
        tw = ancho(nombre_p, 8)
        if lado == "t":
            d.nodo(x + rel * w - tw / 2, y + 1, tw, 11, nombre_p, PORT_T + "align=center;verticalAlign=top;")
        elif lado == "b":
            d.nodo(x + rel * w - tw / 2, y + h - 12, tw, 11, nombre_p, PORT_T + "align=center;verticalAlign=bottom;")
        elif lado == "l":
            d.nodo(x + 2, y + rel * h - 6, tw, 12, nombre_p, PORT_T + "align=left;")
        else:
            d.nodo(x + w - tw - 2, y + rel * h - 6, tw, 12, nombre_p, PORT_T + "align=right;")
    return m


# ---------------------------------------------------------------------------
# 1. Índices y direcciones
# ---------------------------------------------------------------------------
def cd_indices():
    d = D.Diagrama("cd_indices")
    d.nodo(0, 0, 400, 16, "Dirección de la ROM (5 bits) e índices n, i, j, k (3 bits)", TITULO)
    y = 44
    piezas = [
        (columna, ("<b>dira</b>", ["1", "@inc"], "sel_dira", "ld_dira"),
         dict(inc="+1", salida="dira → ROM", nombre_inc="dira+1")),
        (columna, ("<b>i</b>", ["1", "@inc", "k+1"], "sel_i", "ld_i"),
         dict(inc="+1", nombre_inc="i+1", nombre_reg="i", comps=[("reg", "n", "=", "i_n", ESTA)])),
        (columna, ("<b>j</b>", ["1", "@inc", "k", "k+1"], "sel_j", "ld_j"),
         dict(inc="+1", nombre_inc="j+1", nombre_reg="j", comps=[("reg", "n", "=", "j_n", ESTA)])),
        (columna, ("<b>k</b>", ["1", "@inc"], "sel_k", "ld_k"),
         dict(inc="+1", nombre_inc="k+1", nombre_reg="k", comps=[("inc", "n", "=", "k1_n", ESTA)])),
    ]
    _, xmax = fila(d, 0, y, piezas, sep=14)

    # Direcciones de lectura de las RAM
    y4 = 236
    d.nodo(0, y4, 560, 16, "Direcciones de lectura: a(f,c) se guarda en f &amp; c(1..0); la columna 5, en "
           "\"11\" &amp; f", TITULO)
    ea = ["i &amp; j(1..0)", "\"11\" &amp; i"]
    eb = ["k &amp; j(1..0)", "\"11\" &amp; k"]
    wa, _ = ancho_mux(ea)
    wb, _ = ancho_mux(eb)
    ym = y4 + 86
    ma = mux(d, 30 + wa / 2, ym, ea, None)
    xc = 30 + wa + 70
    c = d.nodo(xc - 28, y4 + 40, 56, 24, "=", COMP)
    l1 = net(d, xc - 14, y4 + 22, "j")
    l2 = net(d, xc + 14, y4 + 22, "\"101\"")
    cable(d, l1, c, (0.5, 1), (0.25, 0))
    cable(d, l2, c, (0.5, 1), (0.75, 0))
    p = punto(d, xc, ma.cy)
    cable(d, c, p, (0.5, 1))
    nombre(d, xc + 4, y4 + 74, "j5")
    mb = mux(d, xc + 70 + wb / 2, ym, eb, None)
    cable(d, p, ma.id, ent=ma.lado(False), est=W + "entryPerimeter=0;")
    cable(d, p, mb.id, ent=mb.lado(True), est=W + "entryPerimeter=0;")
    for M, t in ((ma, "<b>dir_ij</b> → rd_add de la RAM A"), (mb, "<b>dir_kj</b> → rd_add de la RAM B")):
        o = net(d, M.x0 + M.w / 2, ym + 44, t)
        cable(d, M.id, o, (0.5, 1), (0.5, 0))
        bits(d, M.x0 + M.w / 2 + 4, ym + 33, 5)
    columna(d, mb.x0 + mb.w + 150, y4 + 6, "<b>n</b>", ["a(2..0)"], None, "ld_n", salida="n")
    leyenda(d, 0, ym + 80, max(xmax, 640))
    return d


# ---------------------------------------------------------------------------
# 2. ROM, RAM A, RAM B y registros que se cargan desde las RAM
# ---------------------------------------------------------------------------
def rama_h(d, bus_x, cy, destino, ent=(0, 0.5)):
    """Punto en el bus vertical y cable horizontal hasta el destino."""
    p = punto(d, bus_x, cy)
    cable(d, p, destino, ent=ent)
    return p


def bajo_ram(d, ram, bus_x, y0, filas, nombre_bus):
    """Bus vertical que sale del puerto q y reparte el dato a la derecha.
    filas: lista de (tipo, texto, carga o señal, estilo de salida)."""
    prev = ram
    ys = []
    y = y0
    for k, (tipo, texto, extra, est) in enumerate(filas):
        cy = y + 13
        x = bus_x + 34
        if tipo == "comp":
            u = d.nodo(x, cy - 12, 40, 24, texto, COMP)
            o = net_der(d, x + 52, cy, extra, est)
            cable(d, u, o, (1, 0.5), (0, 0.5), est=WS if est == ESTA else W)
        else:
            u = registro_h(d, x, cy, texto, extra)
            o = net_der(d, x + d.geo[u][2] + 12, cy, plano(texto).split(" ")[0])
            cable(d, u, o, (1, 0.5), (0, 0.5))
        p = punto(d, bus_x, cy)
        cable(d, prev, p, (0.12, 1) if prev == ram else None)
        cable(d, p, u, ent=(0, 0.5))
        prev = p
        ys.append(cy)
        y += 58 if (k + 1 < len(filas) and filas[k + 1][0] == "reg") else 40
    o = net(d, bus_x, y + 6, nombre_bus)
    cable(d, prev, o, ent=(0.5, 0))
    nombre(d, bus_x + 4, y0 - 12, nombre_bus)
    bits(d, bus_x + 4, y0 - 1, 32)
    return ys


def cd_memorias():
    d = D.Diagrama("cd_memorias")
    d.nodo(0, 0, 400, 16, "ROM de la matriz, RAM A, RAM B y registros piv, aik y tmp", TITULO)
    # ROM y extensión de signo
    l = net(d, 55, 24, "dira")
    rom = d.nodo(15, 50, 80, 50, "<b>ROM</b><br>32 × 6", MEM)
    cable(d, l, rom, (0.5, 1), (0.5, 0))
    bits(d, 59, 43, 5)
    p = punto(d, 115, 75)
    cable(d, rom, p, (1, 0.5))
    bits(d, 100, 68, 6)
    nombre(d, 99, 84, "a")
    lab = net(d, 115, 100, "a(2..0) → n")
    cable(d, p, lab, ent=(0.5, 0))
    ext = d.nodo(135, 60, 74, 30, "ext. signo<br>6 → 32", UNI + "fontSize=9;")
    cable(d, p, ext, ent=(0, 0.5))
    # MUX del dato y de la dirección de escritura
    ram_a = (120, 220, 240, 70)
    ram_b = (430, 220, 240, 70)
    xd = 330
    md = mux(d, xd, 130, [None, "qb", "tmp", "cociente"], "sel_d", alto_ent=34)
    cable(d, ext, md.id, (1, 0.5), md.ent(0), pts=[(md.xs[0], 75)])
    bits(d, 213, 68, 32)
    x_wb = ram_b[0] + 0.45 * ram_b[2]
    mw = mux(d, x_wb, 130, ["dir_ij", "dir_kj"], "sel_w", alto_ent=34)
    # RAM A y RAM B
    puertos = {"data": ("t", 0.2), "wr_add": ("t", 0.45), "rd_add": ("l", 0.35), "we": ("l", 0.72),
               "q": ("b", 0.12)}
    ra = caja_mem(d, *ram_a, "<b>RAM A</b><br>32 × 32<br><font style='font-size:9px'>RAM_memory</font>", puertos)
    rb = caja_mem(d, *ram_b, "<b>RAM B</b><br>32 × 32<br><font style='font-size:9px'>RAM_memory</font>", puertos)
    for x, y, w, h in (ram_a, ram_b):
        d.nodo(x, y + h - 12, 7, 10, "", RELOJ.replace("#6C8EBF", "#9673A6"))
    pd = punto(d, xd, 178)
    cable(d, md.id, pd, (0.5, 1))
    pw = punto(d, x_wb, 194)
    cable(d, mw.id, pw, (0.5, 1))
    for ram in (ra, rb):
        cable(d, pd, ram, ent=(0.2, 0), pts=[(d.geo[ram][0] + 0.2 * d.geo[ram][2], 178)])
    cable(d, pw, ra, ent=(0.45, 0), pts=[(ram_a[0] + 0.45 * ram_a[2], 194)])
    cable(d, pw, rb, ent=(0.45, 0))
    nombre(d, xd + 4, 168, "data")
    bits(d, xd + 4, 159, 32)
    nombre(d, x_wb + 4, 176, "wr_add")
    bits(d, x_wb + 4, 162, 5)
    for ram, (x, y, w, h), dr in ((ra, ram_a, "dir_ij"), (rb, ram_b, "dir_kj")):
        l1 = net_izq(d, x - 12, y + 0.35 * h, dr)
        cable(d, l1, ram, (1, 0.5), (0, 0.35))
        l2 = net_izq(d, x - 12, y + 0.72 * h, "we", CTRL)
        d.arista(l2, ram, "", WC, salida=(1, 0.5), entrada=(0, 0.72))
    # Salidas de las RAM
    bajo_ram(d, ra, ram_a[0] + 0.12 * ram_a[2], ram_a[1] + ram_a[3] + 16,
             [("comp", "= 0", "z_a", ESTA), ("reg", "<b>aik</b>", "ld_aik", ""), ("reg", "<b>tmp</b>", "ld_tmp", "")],
             "qa")
    bajo_ram(d, rb, ram_b[0] + 0.12 * ram_b[2], ram_b[1] + ram_b[3] + 16,
             [("comp", "= 0", "z_b", ESTA), ("reg", "<b>piv</b>", "ld_piv", "")], "qb")
    leyenda(d, 0, 500, 680)
    return d


# ---------------------------------------------------------------------------
# 3. Multiplicador y restador
# ---------------------------------------------------------------------------
def cd_aritmetica():
    d = D.Diagrama("cd_aritmetica")
    d.nodo(0, 0, 420, 16, "Multiplicador (25 × 25) y sumador/restador (50 bits)", TITULO)
    y = 30
    cx, cy_, cm = 150, 400, 275
    ox = columna(d, cx, y, "<b>x</b>", ["piv(24..0)", "aik(24..0)"], "sel_x", "ld_x")
    oy = columna(d, cy_, y, "<b>y</b>", ["qa(24..0)", "qb(24..0)"], "sel_y", "ld_y")
    mult = d.nodo(cm - 30, 150, 60, 34, "<b>×</b><br><font style='font-size:8px'>25 × 25</font>", UNI)
    cable(d, ox["reg"], mult, (0.5, 1), (0.25, 0), pts=[(cx, 138), (cm - 15, 138)])
    cable(d, oy["reg"], mult, (0.5, 1), (0.75, 0), pts=[(cy_, 138), (cm + 15, 138)])
    bits(d, cx + 4, 132, 25)
    bits(d, cy_ + 4, 132, 25)
    pm = punto(d, cm, 205)
    cable(d, mult, pm, (0.5, 1))
    nombre(d, cm + 4, 194, "x·y")
    bits(d, cm + 26, 194, 50)
    # r y s
    yr = 210
    mr = mux(d, cx, yr + 30, [None, None, "0"], "sel_r", codigos=["01", "00", "10"], alto_ent=24)
    r = registro(d, cx, yr + 70, "<b>r</b>", "ld_r")
    cable(d, mr.id, r, (0.5, 1), (0.5, 0))
    ms_ = mux(d, cy_, yr + 30, [None, None], "sel_s")
    s = registro(d, cy_, yr + 70, "<b>s</b>", "ld_s")
    cable(d, ms_.id, s, (0.5, 1), (0.5, 0))
    cable(d, pm, mr.id, ent=mr.ent(1), pts=[(mr.xs[1], 205)])
    cable(d, pm, ms_.id, ent=ms_.ent(0), pts=[(ms_.xs[0], 205)])
    # restador
    res = d.nodo(cm - 30, 330, 60, 34, "<b>−</b><br><font style='font-size:8px'>r − s</font>", UNI)
    pr = punto(d, cx, 318)
    cable(d, r, pr, (0.5, 1))
    cable(d, pr, res, ent=(0.25, 0), pts=[(cm - 15, 318)])
    ps = punto(d, cy_, 318)
    cable(d, s, ps, (0.5, 1))
    cable(d, ps, res, ent=(0.75, 0), pts=[(cm + 15, 318)])
    lr = net(d, cx, 340, "r")
    cable(d, pr, lr, ent=(0.5, 0))
    ls = net(d, cy_, 340, "s")
    cable(d, ps, ls, ent=(0.5, 0))
    cable(d, res, mr.id, (0.5, 1), mr.ent(0), pts=[(cm, 384), (14, 384), (14, 222), (mr.xs[0], 222)])
    nombre(d, 18, 300, "r − s")
    bits(d, cm + 4, 376, 50)
    # p con extensión de signo hacia s
    xp = 590
    op = columna(d, xp, y, "<b>p</b>", ["1", "piv"], "sel_p", "ld_p")
    ext = d.nodo(xp - 37, 156, 74, 30, "ext. signo<br>32 → 50", UNI + "fontSize=9;")
    cable(d, op["reg"], ext, (0.5, 1), (0.5, 0))
    cable(d, ext, ms_.id, (0.5, 1), ms_.ent(1), pts=[(xp, 222), (ms_.xs[1], 222)])
    bits(d, xp + 4, 143, 32)
    bits(d, xp + 4, 200, 50)
    # t, r = t y signos
    yt = 410
    d.nodo(0, yt - 4, 300, 16, "División: valor final t y señales de estado", TITULO)
    columna(d, 120, yt + 14, "<b>t</b>", ["0", "r"], "sel_t", "ld_t", comps=[("reg", "r", "=", "rt", ESTA)])
    unidad(d, 300, yt + 100, ["r(49)", "s(49)"], "XNOR", "ms", ESTA, forma=LOG, w=46)
    d.nodo(256, yt + 124, 220, 30, "ms = 1 si r y s tienen el mismo signo", NOTA)
    d.nodo(256, yt + 150, 300, 40, "rt = 1 cuando r llega al valor t: la división terminó", NOTA)
    leyenda(d, 0, yt + 200, 680)
    return d


# ---------------------------------------------------------------------------
# 4. Cociente, signo, banco de pivotes y salidas
# ---------------------------------------------------------------------------
def cd_division():
    d = D.Diagrama("cd_division")
    d.nodo(0, 0, 420, 16, "Sentido del cociente (sq), contador cociente, signo y det", TITULO)
    y = 60
    # sq: XOR de los bits de signo y su negación
    xq = 120
    mq = mux(d, xq, y + 30, [None, None], "sel_sq", sel_izq=True)
    xo = d.nodo(54, y - 30, 44, 24, "XOR", LOG)
    for k, t in enumerate(("r(49)", "s(49)")):
        lab = net_izq(d, 44, y - 30 + 24 * (0.3 + 0.4 * k), t)
        cable(d, lab, xo, (1, 0.5), (0, 0.3 + 0.4 * k))
    pq = punto(d, mq.xs[0], y + 10)
    cable(d, xo, pq, (0.5, 1), pts=[(76, y + 10)])
    cable(d, pq, mq.id, ent=mq.ent(0))
    no = d.nodo(118, y - 30, 40, 24, "NOT", LOG)
    cable(d, pq, no, ent=(0, 0.5), pts=[(mq.xs[0], y - 18)])
    cable(d, no, mq.id, (round((mq.xs[1] - 118) / 40, 3), 1), mq.ent(1))
    rq = registro(d, xq, y + 70, "<b>sq</b>", "ld_sq")
    cable(d, mq.id, rq, (0.5, 1), (0.5, 0))
    lq = net(d, xq, y + 116, "sq")
    cable(d, rq, lq, (0.5, 1), (0.5, 0))
    # cociente
    oc = columna(d, 330, y, "<b>cociente</b>", ["0", "@inc"], "sel_c", "ld_c", inc="±1", inc_ctrl="sq",
                 nombre_inc="cociente ± 1", salida="cociente")
    # signo
    og = columna(d, 560, y, "<b>signo</b>", ["0", "@inc"], "sel_sg", "ld_sg", inc="not", salida="sg",
                 salida_est=ESTA, nombre_inc="not signo")
    d.nodo(300, y + 156, 400, 24, "±1: suma 1 si sq = 0 y resta 1 si sq = 1 (contador ascendente/descendente)",
           NOTA)
    # banco de pivotes, alineado con las entradas del MUX de pivote
    yb = 250
    d.nodo(0, yb, 420, 16, "Banco de pivotes b1..b4, registro det y salida pivote", TITULO)
    yr = yb + 70
    ym = yr + 110
    mp = mux(d, 220, ym, [None, None, None, None, None, "0"], None,
             codigos=["1", "2", "3", "4", "= n", "otro"], paso=66, alto_ent=26)
    lq = net(d, 14, yr - 44, "qb")
    prev = lq
    for k in range(4):
        x = mp.xs[k]
        p = punto(d, x, yr - 14)
        cable(d, prev, p, (0.5, 1) if prev == lq else None, pts=[(14, yr - 14)] if prev == lq else ())
        b = registro(d, x, yr, f"<b>b{k + 1}</b>", f"e{k + 1}", w=40, ld_est="")
        cable(d, p, b, ent=(0.5, 0))
        cable(d, b, mp.id, (0.5, 1), mp.ent(k))
        prev = p
    # decodificador de k con habilitación we_b
    xdec = mp.xs[3] + 64
    dec, _ = unidad(d, xdec, yr + 13, ["k", "we_b"], "DEC<br>2 → 4", None, forma=COMP.replace("#FFF2CC", "#FFFFFF")
                    .replace("#D6B656", "#555555"), w=50, h=60)
    for k in range(4):
        cyk = yr - 8 + 14 * k
        o = net_der(d, xdec + 60, cyk, f"e{k + 1}")
        cable(d, dec, o, (1, round((cyk - (yr - 17)) / 60, 3)), (0, 0.5))
    d.nodo(xdec - 40, yr + 46, 170, 14, "e<i>m</i> = we_b cuando k = <i>m</i>", NOTA)
    # det
    xd = 640
    od = columna(d, xd, yr - 66, "<b>det</b>", ["0", "cociente"], "sel_det", "ld_det")
    pdt = punto(d, xd, ym - 34)
    cable(d, od["reg"], pdt, (0.5, 1))
    port_det = d.nodo(xd - 50, ym + 20, 100, 26, "det[31:0]", PUERTO)
    cable(d, pdt, port_det, ent=(0.5, 0))
    cable(d, pdt, mp.id, ent=mp.ent(4), pts=[(mp.xs[4], ym - 34)])
    # selección del pivote que se muestra
    sel = d.nodo(mp.x0 + mp.w + 24, ym - 2, 96, 26, "selección<br>(dir_p, n)", LOG + "fontSize=8.5;")
    cable(d, sel, mp.id, (0, 0.5), mp.lado(False), est=W + "entryPerimeter=0;")
    lp = net(d, mp.x0 + mp.w + 72, ym + 50, "dir_p, n")
    cable(d, lp, sel, (0.5, 0), (0.5, 1))
    port_p = d.nodo(mp.x0 + mp.w / 2 - 50, ym + 50, 100, 26, "pivote[31:0]", PUERTO)
    cable(d, mp.id, port_p, (0.5, 1), (0.5, 0))
    leyenda(d, 0, ym + 92, 690)
    return d


# ---------------------------------------------------------------------------
# 5. Visualizador: camino de datos del XS3
# ---------------------------------------------------------------------------
def cd_xs3():
    d = D.Diagrama("cd_xs3")
    d.nodo(0, 0, 420, 16, "Valor a convertir, registro binario y registro decimal", TITULO)
    # val = det si dir_p = 0; si no, pivote
    xv = 140
    mv = mux(d, xv, 56, ["pivote", "det"], "dir_p = 0", sel_izq=True, sel_est="")
    pv = punto(d, xv, 96)
    cable(d, mv.id, pv, (0.5, 1))
    nombre(d, xv + 4, 86, "val")
    bits(d, xv + 22, 86, 32)
    neg_v = d.nodo(xv - 30, 108, 60, 22, "0 − val", UNI + "fontSize=9.5;")
    cable(d, pv, neg_v, ent=(0.5, 0))
    # bin
    xb = 320
    ob = columna(d, xb, 116, "<b>bin</b>", [None, None, "@inc"], "sel_bin", "ld_bin", codigos=["01", "00", "10"],
                 inc="&lt;&lt;1", nombre_inc="bin &lt;&lt; 1", salida="bin")
    mb = ob["mux"]
    cable(d, neg_v, mb.id, (0.5, 1), mb.ent(0), pts=[(xv, 138), (mb.xs[0], 138)])
    cable(d, pv, mb.id, ent=mb.ent(1), pts=[(mb.xs[1], 96)])
    # dec
    od = columna(d, 590, 116, "<b>dec</b> (40)", ["0", "dec_b", "dec_3", "@inc"], "sel_dec", "ld_dec",
                 inc="&lt;&lt;1", nombre_inc="dec &lt;&lt; 1", salida="dec")
    # fila 2: neg, cont, d, disp, disp_neg
    y2 = 300
    d.nodo(0, y2 - 10, 420, 16, "Signo, contadores cont y d, y registros del display", TITULO)
    piezas = [
        (columna, ("<b>neg</b>", ["val(31)"], None, "ld_neg"), dict(salida="neg")),
        (columna, ("<b>cont</b> (5)", ["0", "@inc"], "sel_cont", "ld_cont"),
         dict(inc="+1", nombre_inc="cont+1", comps=[("reg", "\"11111\"", "=", "cont_31", ESTA)])),
        (columna, ("<b>d</b> (4)", ["0", "@inc"], "sel_d", "ld_d"),
         dict(inc="+1", nombre_inc="d+1", nombre_reg="d", comps=[("reg", "\"1001\"", "=", "d_9", ESTA)])),
        (columna, ("<b>disp</b> (40)", ["dec"], None, "ld_disp"), dict(salida="disp")),
        (columna, ("<b>disp_neg</b>", ["neg"], None, "ld_disp"), dict(salida="disp_neg")),
    ]
    fila(d, 0, y2 + 30, piezas, sep=16)
    # fila 3: bloques combinacionales
    y3 = 530
    d.nodo(0, y3 - 10, 420, 16, "Bloques combinacionales del XS3", TITULO)
    fila_u = [
        (["dec(39..1)", "bin(31)"], "&amp;", "dec_b", "", COMP.replace("#FFF2CC", "#FFFFFF").replace("#D6B656", "#555555"), 34),
        (["dec", "d"], "MUX 10 → 1<br><font style='font-size:8px'>dígito d</font>", "dig", "",
         LOG.replace("arcSize=40", "arcSize=10"), 70),
        (["dig"], "+3", "dig_mas3", "", SUMA, 30),
    ]
    x = 0
    for ent, txt, sal, est, forma, w in fila_u:
        izq = max(ancho(e) for e in ent) + 12
        unidad(d, x + izq, y3 + 30, ent, txt, sal, est, forma=forma, w=w)
        x += izq + w + 12 + ancho(sal) + 30
    unidad(d, 70, y3 + 90, ["'0' &amp; dig"], "&gt; 4", "dig_4", ESTA, forma=COMP, w=40)
    lv = net_izq(d, 110, y3 + 124, "val(31)")
    ov = net_der(d, 150, y3 + 124, "val_neg", ESTA)
    cable(d, lv, ov, (1, 0.5), (0, 0.5), est=WS)
    u, _ = unidad(d, 330, y3 + 90, ["dec", "dig_mas3", "d"], "reemplaza el<br>dígito d", "dec_3", forma=UNI, w=84,
                  h=48)
    d.nodo(0, y3 + 140, 690, 30, "dec_b = dec(39..1) &amp; bin(31) (PASO 2); dec_3 = dec con el dígito d cambiado "
           "por dig + 3 (PASO 3); los corrimientos &lt;&lt;1 son los del PASO 4.", NOTA)
    leyenda(d, 0, y3 + 166, 690)
    return d


# ---------------------------------------------------------------------------
# 6. Visualizador: display de 8 dígitos
# ---------------------------------------------------------------------------
def cd_display():
    d = D.Diagrama("cd_display")
    d.nodo(0, 0, 420, 16, "Barrido del display (un dígito por cada tick de 1 ms)", TITULO)
    # dsel: contador de 3 bits habilitado por tick
    xs = 80
    y = 30
    r = registro(d, xs, y + 50, "<b>dsel</b> (3)", "tick", ld_est="")
    p1 = punto(d, xs, y + 92)
    cable(d, r, p1, (0.5, 1))
    wr = d.geo[r][2]
    u = d.nodo(xs + wr / 2 + 2, y + 80, 28, 24, "+1", SUMA)
    cable(d, p1, u, ent=(0, 0.5))
    xr = xs + wr / 2 + 2 + 28 + 10
    cable(d, u, r, (1, 0.5), (0.5, 0), pts=[(xr, y + 92), (xr, y + 30), (xs, y + 30)])
    l = net(d, xs, y + 112, "dsel")
    cable(d, p1, l, ent=(0.5, 0))
    d.nodo(xs + 70, y + 104, 160, 20, "dsel ← dsel + 1 cuando tick = 1", NOTA)
    # car_signo
    mc = mux(d, 300, y + 40, ["\"1111\"", "\"1010\""], "disp_neg", sel_est="")
    lc = net(d, 300, y + 84, "car_signo")
    cable(d, mc.id, lc, (0.5, 1), (0.5, 0))
    d.nodo(380, y + 70, 300, 30, "\"1010\" = signo menos (AN7); \"1111\" = dígito apagado", NOTA)
    # MUX de caracteres
    y2 = 170
    ent = [f"disp({4 * k + 3}..{4 * k})" for k in range(7)] + ["car_signo"]
    m = mux(d, 290, y2 + 30, ent, "dsel", paso=70, sel_est="")
    nombre(d, 294, y2 + 66, "car")
    bits(d, 320, y2 + 66, 4)
    s7 = d.nodo(220, y2 + 92, 140, 34, "decodificador<br>7 segmentos", LOG + "fontSize=9.5;")
    cable(d, m.id, s7, (0.5, 1), (0.5, 0))
    ps = d.nodo(240, y2 + 150, 100, 26, "SEG[6:0]", PUERTO)
    cable(d, s7, ps, (0.5, 1), (0.5, 0))
    # ánodos, desborde y punto decimal
    y3 = y2 + 110
    an = d.nodo(470, y3 - 10, 120, 34, "decodificador 3 → 8<br>(activo en bajo)", LOG + "fontSize=9;")
    la = net_izq(d, 458, y3 + 7, "dsel")
    cable(d, la, an, (1, 0.5), (0, 0.5))
    pa = d.nodo(620, y3 - 6, 80, 26, "AN[7:0]", PUERTO)
    cable(d, an, pa, (1, 0.5), (0, 0.5))
    c = d.nodo(470, y3 + 40, 120, 30, "≠ 0", COMP)
    lc2 = net_izq(d, 458, y3 + 55, "disp(39..28)")
    cable(d, lc2, c, (1, 0.5), (0, 0.5))
    pd = d.nodo(620, y3 + 42, 80, 26, "DESBORDE", PUERTO)
    cable(d, c, pd, (1, 0.5), (0, 0.5))
    l1 = net_izq(d, 588, y3 + 103, "'1'")
    pp = d.nodo(620, y3 + 90, 80, 26, "DP", PUERTO)
    cable(d, l1, pp, (1, 0.5), (0, 0.5))
    d.nodo(0, y3 + 130, 700, 28, "El barrido no depende del ASM XS3: dsel avanza con tick (1 ms) y muestra disp y "
           "disp_neg, que el ASM actualiza en x5. Ánodos y segmentos son activos en bajo.", NOTA)
    return d


def todas():
    return [cd_indices(), cd_memorias(), cd_aritmetica(), cd_division(), cd_xs3(), cd_display()]

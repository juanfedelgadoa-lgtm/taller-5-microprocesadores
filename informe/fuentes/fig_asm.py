"""Diagramas ASM del informe (procesador de Bareiss y XS3) en draw.io.

Cada diagrama se arma con cajas de estado, rombos de decisión, cajas de salida
condicional y conectores. Antes de guardar se revisan las reglas del ASM:
  1. cada rombo tiene una salida 1 y una salida 0; las demás cajas una sola salida;
  2. todo camino desde una caja de estado llega a un estado o a un conector sin
     pasar dos veces por la misma caja;
  y que los estados siguientes coincidan con las tablas de uc_cd.py.
"""
import drawio as D

ANCHO_1 = (-0.55, -9)       # posición de la etiqueta 1/0 cerca del rombo


class ASM(D.Diagrama):
    def __init__(self, nombre):
        super().__init__(nombre)
        self.bloques = {}

    def estado(self, nombre, x, y, w, h, texto):
        i = self.nodo(x, y, w, h, texto, D.ESTADO, tipo=f"estado:{nombre}")
        self.bloques.setdefault(nombre, []).append(i)
        return i

    def decision(self, bloque, x, y, w, h, texto):
        i = self.nodo(x, y, w, h, texto, D.DECISION, tipo="decision")
        self.bloques[bloque].append(i)
        return i

    def cond(self, bloque, x, y, w, h, texto):
        i = self.nodo(x, y, w, h, texto, D.CONDICIONAL, tipo="condicional")
        self.bloques[bloque].append(i)
        return i

    def conector(self, nombre, x, y, w=70, h=26, texto=None):
        return self.nodo(x, y, w, h, texto or nombre, D.CONECTOR, tipo=f"conector:{nombre}")

    def si(self, a, b, valor, salida, entrada=None, puntos=(), pos=ANCHO_1):
        est = D.ARISTA + "labelBackgroundColor=#FFFFFF;fontStyle=1;fontSize=10;fontColor=#7F6000;"
        return self.arista(a, b, str(valor), est, salida=salida, entrada=entrada, puntos=puntos, etiqueta_pos=pos)

    def va(self, a, b, salida=None, entrada=None, puntos=()):
        return self.arista(a, b, "", D.ARISTA, salida=salida, entrada=entrada, puntos=puntos)

    def cerrar_bloques(self, extras=None):
        extras = extras or {}
        for nombre, ids in self.bloques.items():
            self.bloque(ids, nombre, extra=extras.get(nombre, (0, 0, 0, 0)))

    # -- revisión ------------------------------------------------------------
    def caminos(self):
        """{estado: [(camino de etiquetas, destino), ...]} siguiendo las aristas."""
        salidas = {}
        for _, a, b, t in self.aristas:
            salidas.setdefault(a, []).append((b, t))
        errores, res = [], {}
        for i, tipo in self.tipo.items():
            if not tipo:
                continue
            n = len(salidas.get(i, []))
            if tipo == "decision":
                etq = sorted(t for _, t in salidas.get(i, []))
                if etq != ["0", "1"]:
                    errores.append(f"rombo '{self.texto[i]}' con salidas {etq}")
            elif tipo.startswith("estado") or tipo == "condicional":
                if n != 1:
                    errores.append(f"caja '{self.texto[i]}' con {n} salidas")
        for i, tipo in self.tipo.items():
            if not tipo or not tipo.startswith("estado:"):
                continue
            nombre = tipo.split(":")[1]

            def seguir(nodo, visto, camino):
                for b, t in salidas.get(nodo, []):
                    tb = self.tipo.get(b) or ""
                    paso = camino + ([f"{self.texto[nodo]}={t}"] if t else [])
                    if tb.startswith("estado:") or tb.startswith("conector:"):
                        res.setdefault(nombre, []).append((paso, tb.split(":")[1]))
                    elif b in visto:
                        errores.append(f"{nombre}: ciclo sin pasar por un estado")
                    else:
                        seguir(b, visto | {b}, paso)
            seguir(i, {i}, [])
        return res, errores


def h(s):
    return s


# ===========================================================================
# Procesador de Bareiss
# ===========================================================================
def asm_hoja1():
    d = ASM("asm_bareiss_1")
    cx = 255
    d.etiqueta(cx - 40, 0, 80, 18, "rst", D.TEXTO + D.ROJO)
    s0 = d.estado("s0", cx - 90, 40, 180, 38, "final = 0")
    d.linea((cx, 18), (cx, 40), "", D.ARISTA)
    di = d.decision("s0", cx - 60, 98, 120, 50, "inicio")
    d.va(s0, di)
    d.si(di, s0, 0, salida=(0, 0.5), entrada=(0.25, 0), puntos=[(cx - 120, 123), (cx - 120, 26), (cx - 45, 26)])
    c0 = d.cond("s0", cx - 95, 172, 190, 46, "n ← a(2..0) ; dira ← 1<br>i ← 1 ; j ← 1")
    d.si(di, c0, 1, salida=(0.5, 1))
    s1 = d.estado("s1", cx - 100, 262, 200, 44, "RAM(i,j) ← a (extensión de signo)<br>dira ← dira + 1")
    d.va(c0, s1)
    dn = d.decision("s1", cx - 55, 326, 110, 46, "i = n")
    d.va(s1, dn)
    ci = d.cond("s1", cx + 95, 330, 110, 38, "i ← i + 1")
    d.si(dn, ci, 0, salida=(1, 0.5), pos=(-0.4, -9))
    d.va(ci, s1, salida=(1, 0.5), entrada=(0.75, 0), puntos=[(cx + 240, 349), (cx + 240, 245), (cx + 50, 245)])
    dj = d.decision("s1", cx - 55, 396, 110, 46, "j = n")
    d.si(dn, dj, 1, salida=(0.5, 1))
    cj = d.cond("s1", cx + 95, 400, 130, 38, "i ← 1 ; j ← j + 1")
    d.si(dj, cj, 0, salida=(1, 0.5), pos=(-0.4, -9))
    d.va(cj, s1, salida=(1, 0.5), entrada=(0.75, 0), puntos=[(cx + 240, 419), (cx + 240, 245), (cx + 50, 245)])
    cf = d.cond("s1", cx - 95, 466, 190, 46, "k ← 1 ; j ← 1<br>p ← 1 ; signo ← 0")
    d.si(dj, cf, 1, salida=(0.5, 1))
    a = d.conector("s2", cx - 35, 540)
    d.va(cf, a)
    d.cerrar_bloques()
    return d


def asm_hoja2():
    d = ASM("asm_bareiss_2")
    cx = 270
    e1 = d.conector("s2", cx - 165, 0, 130, 26, "desde s1, s5 o s12")
    s2 = d.estado("s2", cx - 95, 50, 190, 44, "piv ← qb = a(k,k)<br>i ← k + 1")
    d.va(e1, s2, salida=(0.5, 1), entrada=(0.25, 0), puntos=[(cx - 100, 36), (cx - 47, 36)])
    dz = d.decision("s2", cx - 65, 114, 130, 50, "a(k,k) = 0")
    d.va(s2, dz)
    cb = d.cond("s2", cx + 95, 119, 120, 40, "banco(k) ← qb")
    d.si(dz, cb, 0, salida=(1, 0.5), pos=(-0.4, -9))
    c6 = d.conector("s6", cx + 245, 126, 60, 26)
    d.va(cb, c6)
    s3 = d.estado("s3", cx - 95, 226, 190, 38, "<i>busca una fila con a(i,k) ≠ 0</i>")
    d.si(dz, s3, 1, salida=(0.5, 1), pos=(-0.45, -9))
    da = d.decision("s3", cx - 65, 284, 130, 50, "a(i,k) = 0")
    d.va(s3, da)
    dn = d.decision("s3", cx + 105, 284, 110, 50, "i = n")
    d.si(da, dn, 1, salida=(1, 0.5), pos=(-0.3, -9))
    ci = d.cond("s3", cx + 240, 291, 100, 36, "i ← i + 1")
    d.si(dn, ci, 0, salida=(1, 0.5), pos=(-0.2, -9))
    d.va(ci, s3, salida=(0.5, 0), entrada=(1, 0.5), puntos=[(cx + 290, 245)])
    cdet = d.cond("s3", cx + 110, 360, 100, 36, "det ← 0")
    d.si(dn, cdet, 1, salida=(0.5, 1))
    c13 = d.conector("s13", cx + 125, 426, 70, 26)
    d.va(cdet, c13)
    cs = d.cond("s3", cx - 95, 364, 190, 36, "signo ← not signo")
    d.si(da, cs, 0, salida=(0.5, 1))
    s4 = d.estado("s4", cx - 95, 456, 190, 44, "RAM(i,j) ← qb = a(k,j)<br>tmp ← qa = a(i,j)")
    d.va(cs, s4)
    s5 = d.estado("s5", cx - 95, 546, 190, 38, "RAM(k,j) ← tmp")
    d.va(s4, s5)
    dj = d.decision("s5", cx - 55, 604, 110, 50, "j = n")
    d.va(s5, dj)
    cj = d.cond("s5", cx + 85, 610, 110, 38, "j ← j + 1")
    d.si(dj, cj, 0, salida=(1, 0.5), pos=(-0.4, -9))
    d.va(cj, s4, salida=(1, 0.5), entrada=(1, 0.5), puntos=[(cx + 230, 629), (cx + 230, 478)])
    ck = d.cond("s5", cx - 95, 678, 190, 38, "j ← k")
    d.si(dj, ck, 1, salida=(0.5, 1))
    d.va(ck, s2, salida=(0, 0.5), entrada=(0, 0.5), puntos=[(cx - 165, 697), (cx - 165, 72)])
    d.cerrar_bloques()
    return d


def asm_hoja3():
    d = ASM("asm_bareiss_3")
    cx = 250
    e = d.conector("s6", cx - 175, 0, 130, 26, "desde s2 o s12")
    s6 = d.estado("s6", cx - 95, 64, 190, 44, "aik ← qa = a(i,k)<br>j ← k + 1")
    d.va(e, s6, salida=(0.5, 1), entrada=(0.25, 0), puntos=[(cx - 110, 36), (cx - 47, 36)])
    s7 = d.estado("s7", cx - 95, 154, 190, 44, "x ← piv<br>y ← qa = a(i,j)")
    d.va(s6, s7)
    e7 = d.conector("s7", cx + 150, 163, 100, 26, "desde s12")
    d.va(e7, s7, salida=(0, 0.5), entrada=(1, 0.5))
    s8 = d.estado("s8", cx - 110, 244, 220, 58, "r ← x·y = piv·a(i,j)<br>x ← aik<br>y ← qb = a(k,j)")
    d.va(s7, s8)
    s9 = d.estado("s9", cx - 95, 348, 190, 36, "s ← x·y = a(i,k)·a(k,j)")
    d.va(s8, s9)
    s10 = d.estado("s10", cx - 95, 430, 190, 58, "r ← r − s<br>s ← p (extensión de signo)<br>cociente ← 0")
    d.va(s9, s10)
    s11 = d.estado("s11", cx - 95, 534, 190, 36, "<i>prepara la división r / s</i>")
    d.va(s10, s11)
    dm = d.decision("s11", cx - 70, 590, 140, 54, "r(49) = s(49)")
    d.va(s11, dm)
    c_ig = d.cond("s11", cx - 215, 668, 120, 36, "t ← 0")
    c_di = d.cond("s11", cx + 95, 668, 120, 40, "t ← r<br>r ← 0")
    d.si(dm, c_ig, 1, salida=(0, 0.5), entrada=(0.5, 0), puntos=[(cx - 155, 617)], pos=(-0.5, -9))
    d.si(dm, c_di, 0, salida=(1, 0.5), entrada=(0.5, 0), puntos=[(cx + 155, 617)], pos=(-0.5, -9))
    dk = d.decision("s11", cx - 60, 740, 120, 50, "k + 1 = n")
    d.va(c_ig, dk, salida=(0.5, 1), entrada=(0.5, 0), puntos=[(cx - 155, 724), (cx, 724)])
    d.va(c_di, dk, salida=(0.5, 1), entrada=(0.5, 0), puntos=[(cx + 155, 724), (cx, 724)])
    q0 = d.cond("s11", cx - 90, 836, 180, 40, "sq ← r(49) ⊕ s(49)")
    d.si(dk, q0, 0, salida=(0.5, 1), pos=(-0.45, -9))
    ds = d.decision("s11", cx + 120, 740, 100, 50, "signo")
    d.si(dk, ds, 1, salida=(1, 0.5), pos=(-0.2, -9))
    d.si(ds, q0, 0, salida=(0.5, 1), entrada=(1, 0.5), puntos=[(cx + 170, 856)], pos=(-0.6, -9))
    q1 = d.cond("s11", cx + 245, 745, 185, 40, "sq ← not (r(49) ⊕ s(49))")
    d.si(ds, q1, 1, salida=(1, 0.5), pos=(-0.2, -9))
    c12 = d.conector("s12", cx - 35, 926)
    d.va(q0, c12)
    d.va(q1, c12, salida=(0.5, 1), entrada=(0.5, 0), puntos=[(cx + 337, 906), (cx, 906)])
    d.cerrar_bloques()
    return d


def asm_hoja4():
    d = ASM("asm_bareiss_4")
    cx = 260
    e = d.conector("s12", cx - 185, 0, 100, 26, "desde s11")
    s12 = d.estado("s12", cx - 95, 64, 190, 36, "<i>división por restas sucesivas</i>")
    d.va(e, s12, salida=(0.5, 1), entrada=(0.25, 0), puntos=[(cx - 135, 36), (cx - 47, 36)])
    dr = d.decision("s12", cx - 55, 120, 110, 50, "r = t")
    d.va(s12, dr)
    cr = d.cond("s12", cx + 80, 122, 190, 46, "r ← r − s<br>cociente ← cociente ± 1")
    d.si(dr, cr, 0, salida=(1, 0.5), pos=(-0.4, -9))
    d.va(cr, s12, salida=(0.5, 0), entrada=(1, 0.5), puntos=[(cx + 175, 82)])
    cw = d.cond("s12", cx - 95, 194, 190, 36, "RAM(i,j) ← cociente")
    d.si(dr, cw, 1, salida=(0.5, 1))
    dj = d.decision("s12", cx - 55, 250, 110, 50, "j = n")
    d.va(cw, dj)
    cj = d.cond("s12", cx + 80, 256, 110, 38, "j ← j + 1")
    d.si(dj, cj, 0, salida=(1, 0.5), pos=(-0.4, -9))
    d.va(cj, d.conector("s7", cx + 300, 262, 60, 26))
    di = d.decision("s12", cx - 55, 324, 110, 50, "i = n")
    d.si(dj, di, 1, salida=(0.5, 1))
    ci = d.cond("s12", cx + 80, 330, 110, 38, "i ← i + 1<br>j ← k")
    d.si(di, ci, 0, salida=(1, 0.5), pos=(-0.4, -9))
    d.va(ci, d.conector("s6", cx + 300, 336, 60, 26))
    dk = d.decision("s12", cx - 60, 398, 120, 50, "k + 1 = n")
    d.si(di, dk, 1, salida=(0.5, 1))
    ck = d.cond("s12", cx + 80, 400, 165, 46, "p ← piv ; k ← k + 1<br>j ← k + 1")
    d.si(dk, ck, 0, salida=(1, 0.5), pos=(-0.4, -9))
    d.va(ck, d.conector("s2", cx + 300, 410, 60, 26))
    cd = d.cond("s12", cx - 95, 472, 190, 36, "det ← cociente")
    d.si(dk, cd, 1, salida=(0.5, 1))
    e13 = d.conector("s13", cx - 225, 552, 90, 26, "desde s3")
    s13 = d.estado("s13", cx - 95, 562, 190, 36, "final = 1")
    d.va(cd, s13)
    d.va(e13, s13, salida=(1, 0.5), entrada=(0, 0.5), puntos=[(cx - 115, 565), (cx - 115, 580)])
    dn = d.decision("s13", cx - 55, 618, 110, 50, "inicio")
    d.va(s13, dn)
    d.si(dn, s13, 0, salida=(1, 0.5), entrada=(1, 0.5), puntos=[(cx + 125, 643), (cx + 125, 580)], pos=(-0.3, -9))
    cn = d.cond("s13", cx - 95, 692, 190, 40, "dira ← 1 ; i ← 1 ; j ← 1")
    d.si(dn, cn, 1, salida=(0.5, 1))
    d.va(cn, d.conector("s1", cx - 35, 762))
    d.cerrar_bloques()
    return d


# ===========================================================================
# Visualizador (XS3)
# ===========================================================================
def asm_xs3():
    d = ASM("asm_xs3")
    cx = 290
    d.etiqueta(cx - 40, 0, 80, 18, "rst", D.TEXTO + D.ROJO)
    x0 = d.estado("x0", cx - 95, 40, 190, 36, "<i>espera final</i>")
    d.linea((cx, 18), (cx, 40), "", D.ARISTA)
    df = d.decision("x0", cx - 55, 96, 110, 48, "final")
    d.va(x0, df)
    d.si(df, x0, 0, salida=(0, 0.5), entrada=(0.25, 0), puntos=[(cx - 120, 120), (cx - 120, 28), (cx - 47, 28)])
    dv = d.decision("x0", cx - 55, 164, 110, 48, "val(31)")
    d.si(df, dv, 1, salida=(0.5, 1))
    cneg = d.cond("x0", cx - 230, 216, 160, 40, "bin ← 0 − val<br>neg ← val(31)")
    cpos = d.cond("x0", cx + 70, 216, 160, 40, "bin ← val<br>neg ← val(31)")
    d.si(dv, cneg, 1, salida=(0, 0.5), entrada=(0.5, 0), puntos=[(cx - 150, 188)], pos=(-0.5, -9))
    d.si(dv, cpos, 0, salida=(1, 0.5), entrada=(0.5, 0), puntos=[(cx + 150, 188)], pos=(-0.5, -9))
    x1 = d.estado("x1", cx - 95, 312, 190, 40, "PASO 1:<br>dec ← 0 ; cont ← 0")
    d.va(cneg, x1, salida=(0.5, 1), entrada=(0.5, 0), puntos=[(cx - 150, 278), (cx, 278)])
    d.va(cpos, x1, salida=(0.5, 1), entrada=(0.5, 0), puntos=[(cx + 150, 278), (cx, 278)])
    x2 = d.estado("x2", cx - 95, 404, 190, 40, "PASO 2:<br>dec(0) ← bin(31)")
    d.va(x1, x2)
    dc = d.decision("x2", cx - 60, 464, 120, 48, "cont = 31")
    d.va(x2, dc)
    cd = d.cond("x2", cx - 80, 532, 160, 32, "d ← 0")
    d.si(dc, cd, 0, salida=(0.5, 1))
    x5 = d.estado("x5", cx + 140, 468, 150, 40, "disp ← dec<br>disp_neg ← neg")
    d.si(dc, x5, 1, salida=(1, 0.5), pos=(-0.3, -9))
    d.va(x5, x0, salida=(1, 0.5), entrada=(1, 0.5), puntos=[(cx + 325, 488), (cx + 325, 58)])
    x3 = d.estado("x3", cx - 95, 616, 190, 40, "PASO 3: revisa el<br>dígito d de dec")
    d.va(cd, x3)
    dg = d.decision("x3", cx - 60, 676, 120, 48, "dígito(d) > 4")
    d.va(x3, dg)
    c3 = d.cond("x3", cx + 90, 681, 150, 38, "dígito(d) ←<br>dígito(d) + 3")
    d.si(dg, c3, 1, salida=(1, 0.5), pos=(-0.4, -9))
    d9 = d.decision("x3", cx - 55, 748, 110, 48, "d = 9")
    d.si(dg, d9, 0, salida=(0.5, 1))
    d.va(c3, d9, salida=(0.5, 1), entrada=(1, 0.5), puntos=[(cx + 165, 772)])
    cdd = d.cond("x3", cx - 245, 753, 110, 38, "d ← d + 1")
    d.si(d9, cdd, 0, salida=(0, 0.5), pos=(-0.4, -9))
    d.va(cdd, x3, salida=(0.5, 0), entrada=(0, 0.5), puntos=[(cx - 190, 636)])
    x4 = d.estado("x4", cx - 95, 836, 190, 58, "PASO 4: dec ← dec &lt;&lt; 1<br>bin ← bin &lt;&lt; 1<br>cont ← cont + 1")
    d.si(d9, x4, 1, salida=(0.5, 1))
    d.va(x4, x2, salida=(0, 0.5), entrada=(0, 0.5), puntos=[(cx - 275, 865), (cx - 275, 424)])
    d.cerrar_bloques()
    return d


HOJAS_BAREISS = [asm_hoja1, asm_hoja2, asm_hoja3, asm_hoja4]


def revisar_bareiss(filas, filas_v):
    """Compara los estados siguientes dibujados con las tablas de la UC."""
    errores = []
    caminos = {}
    for f in HOJAS_BAREISS:
        c, e = f().caminos()
        errores += e
        for k, v in c.items():
            caminos.setdefault(k, []).extend(v)
    for e, lista in filas.items():
        dib = sorted({dest for _, dest in caminos.get(e, [])})
        tab = sorted({s for _, s, _ in lista})
        if dib != tab:
            errores.append(f"{e}: el ASM va a {dib} y la tabla de la UC a {tab}")
        if len(caminos.get(e, [])) != len(lista):
            errores.append(f"{e}: {len(caminos.get(e, []))} caminos en el ASM y {len(lista)} filas en la UC")
    c, e = asm_xs3().caminos()
    errores += e
    for st, lista in filas_v.items():
        dib = sorted({dest for _, dest in c.get(st, [])})
        tab = sorted({s for _, s, _ in lista})
        if dib != tab:
            errores.append(f"{st}: el ASM va a {dib} y la tabla de la UC a {tab}")
        if len(c.get(st, [])) != len(lista):
            errores.append(f"{st}: {len(c.get(st, []))} caminos en el ASM y {len(lista)} filas en la UC")
    return errores, caminos

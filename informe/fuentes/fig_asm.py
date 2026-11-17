"""Diagramas ASM del informe (procesador de Bareiss y XS3) en draw.io.

Estilo de los ejemplos del profesor: cada caja de estado tiene el nombre del
estado y todas sus operaciones; los rombos son las decisiones (salidas 1 y 0);
las cajas redondeadas son las salidas condicionales; el recuadro rojo punteado
agrupa cada bloque ASM. Cada ASM es un solo diagrama completo, sin hojas ni
conectores.

Revisión automática (revisar):
  1. cada rombo tiene una salida 1 y una salida 0; las demás cajas, una sola;
  2. para todas las combinaciones de las señales de estado, el camino dibujado
     desde cada estado llega al mismo estado siguiente que la tabla de
     transiciones de uc_cd.py (que se comprobó contra la simulación del VHDL).
"""
import itertools
import re

import drawio as D

F = D.F
EST = F + "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontSize=12;spacing=3;"
DEC = F + "rhombus;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontSize=11.5;spacing=0;"
CON = F + "rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontSize=11.5;"
BLQ = F + "rounded=0;html=1;fillColor=none;dashed=1;dashPattern=7 4;strokeColor=#D02020;strokeWidth=1.3;"
ARI = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;endSize=5;strokeColor=#000000;"
       "fontSize=11;" + F)
ETQ = ARI + "labelBackgroundColor=#FFFFFF;fontStyle=1;"
TXT = F + "text;html=1;align=center;verticalAlign=middle;fontSize=11;fontColor=#D02020;fontStyle=1;"


def plano(t):
    return re.sub(r"<[^>]+>", " ", t).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def norm(t):
    return " ".join(plano(t).split())


class ASM(D.Diagrama):
    def __init__(self, nombre):
        super().__init__(nombre)
        self.bloques = {}

    # -- cajas (x, y = centro arriba) -----------------------------------------
    def estado(self, nombre, cx, y, w, ops, h=None):
        lineas = [f"<b>{nombre.upper()}</b>"] + list(ops)
        h = h or 15 * len(lineas) + 8
        i = self.nodo(cx - w / 2, y, w, h, "<br>".join(lineas), EST, tipo=f"estado:{nombre}")
        self.bloques.setdefault(nombre, []).append(i)
        return i

    def decision(self, bloque, cx, y, w, h, texto):
        i = self.nodo(cx - w / 2, y, w, h, texto, DEC, tipo="decision")
        self.bloques[bloque].append(i)
        return i

    def cond(self, bloque, cx, y, w, texto, h=None):
        h = h or 15 * (texto.count("<br>") + 1) + 12
        i = self.nodo(cx - w / 2, y, w, h, texto, CON, tipo="condicional")
        self.bloques[bloque].append(i)
        return i

    def cy(self, i, rel=0.5):
        return self.geo[i][1] + rel * self.geo[i][3]

    def cond_en(self, bloque, cx, cy, w, texto):
        """Salida condicional centrada en (cx, cy)."""
        h = 15 * (texto.count("<br>") + 1) + 12
        return self.cond(bloque, cx, cy - h / 2, w, texto)

    def si(self, a, b, valor, salida, entrada=(0.5, 0), puntos=(), pos=(-0.6, 10)):
        return self.arista(a, b, str(valor), ETQ, salida=salida, entrada=entrada, puntos=puntos, etiqueta_pos=pos)

    def va(self, a, b, salida=(0.5, 1), entrada=(0.5, 0), puntos=()):
        return self.arista(a, b, "", ARI, salida=salida, entrada=entrada, puntos=puntos)

    def cerrar_bloques(self, margen=6):
        for nombre, ids in self.bloques.items():
            xs = [self.geo[i][0] for i in ids]
            ys = [self.geo[i][1] for i in ids]
            x2 = [self.geo[i][0] + self.geo[i][2] for i in ids]
            y2 = [self.geo[i][1] + self.geo[i][3] for i in ids]
            x, y = min(xs) - margen, min(ys) - margen
            w, h = max(x2) + margen - x, max(y2) + margen - y
            self.celdas.insert(0, f'<mxCell id="b{nombre}" value="" style="{BLQ}" vertex="1" parent="1">'
                                  f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')

    # -- revisión ------------------------------------------------------------
    def revisar(self, senales, filas, fila_de):
        """senales: {texto del rombo: función(valores) -> 0/1}. filas/fila_de: tabla de la UC."""
        errores = []
        salidas = {}
        for _, a, b, t in self.aristas:
            salidas.setdefault(a, []).append((b, t))
        for i, tipo in self.tipo.items():
            if not tipo:
                continue
            etq = sorted(t for _, t in salidas.get(i, []))
            if tipo == "decision":
                if etq != ["0", "1"]:
                    errores.append(f"rombo '{norm(self.texto[i])}' con salidas {etq}")
                if norm(self.texto[i]) not in senales:
                    errores.append(f"rombo '{norm(self.texto[i])}' sin señal asociada")
            elif len(etq) != 1:
                errores.append(f"caja '{norm(self.texto[i])}' con {len(etq)} salidas")
        if errores:
            return errores, 0
        bases = sorted({k for c in filas.values() for cond, _, _ in c for k in cond} | {"sq"})
        estados = {tipo.split(":")[1]: i for i, tipo in self.tipo.items() if tipo and tipo.startswith("estado:")}
        revisadas = 0
        for nombre, caja in estados.items():
            for valores in itertools.product((0, 1), repeat=len(bases)):
                v = dict(zip(bases, valores))
                nodo, pasos = salidas[caja][0][0], 0
                while not (self.tipo.get(nodo) or "").startswith("estado:"):
                    pasos += 1
                    if pasos > 50:
                        errores.append(f"{nombre}: camino sin fin con {v}")
                        break
                    if self.tipo[nodo] == "decision":
                        bit = str(senales[norm(self.texto[nodo])](v))
                        nodo = next(b for b, t in salidas[nodo] if t == bit)
                    else:
                        nodo = salidas[nodo][0][0]
                destino = self.tipo[nodo].split(":")[1]
                esperado, _ = fila_de(filas, nombre, v)
                revisadas += 1
                if destino != esperado:
                    errores.append(f"{nombre}: con {v} el ASM va a {destino} y la tabla a {esperado}")
                    break
        return errores, revisadas


# ===========================================================================
# Procesador de Bareiss: un solo diagrama en dos columnas
# ===========================================================================
SENALES_P = {
    "INICIO": lambda v: v["inicio"],
    "RAM(K,K) = 0": lambda v: v["z_b"],
    "RAM(I,K) = 0": lambda v: v["z_a"],
    "I = N": lambda v: v["i_n"],
    "J = N": lambda v: v["j_n"],
    "K + 1 = N": lambda v: v["k1_n"],
    "R(49) = S(49)": lambda v: v["ms"],
    "K + 1 = N Y SIGNO = 1": lambda v: v["k1_n"] & v["sg"],
    "R = T": lambda v: v["rt"],
    "SQ": lambda v: v["sq"],
}


def asm_bareiss():
    d = ASM("asm_bareiss")
    A, B = 175, 700                         # centros de las dos columnas
    # ---------------------------------------------------------------- s0
    d.etiqueta(A - 20, 0, 40, 16, "rst", TXT)
    s0 = d.estado("s0", A, 30, 150, ["FINAL = 0"])
    d.linea((A, 16), (A, 30), "", ARI)
    i0 = d.decision("s0", A, 88, 110, 44, "INICIO")
    d.va(s0, i0)
    d.si(i0, s0, 0, salida=(0, 0.5), entrada=(0, 0.5), puntos=[(40, d.cy(i0)), (40, d.cy(s0))], pos=(-0.75, -9))
    c0 = d.cond("s0", A, 152, 175, "N = ROM(0) ; DIRA = 1<br>I = 1 ; J = 1")
    d.si(i0, c0, 1, salida=(0.5, 1), pos=(-0.3, 9))
    # ---------------------------------------------------------------- s1
    s1 = d.estado("s1", A, 222, 175, ["RAM(I,J) = ROM(DIRA)", "DIRA = DIRA + 1"])
    d.va(c0, s1)
    di = d.decision("s1", A, 296, 100, 44, "I = N")
    d.va(s1, di)
    ci = d.cond_en("s1", 318, d.cy(di), 96, "I = I + 1")
    d.si(di, ci, 0, salida=(1, 0.5), entrada=(0, 0.5), pos=(-0.2, -9))
    d.va(ci, s1, salida=(1, 0.5), entrada=(1, 0.3), puntos=[(392, d.cy(ci)), (392, d.cy(s1, 0.3))])
    dj = d.decision("s1", A, 364, 100, 44, "J = N")
    d.si(di, dj, 1, salida=(0.5, 1), pos=(-0.3, 9))
    cj = d.cond_en("s1", 318, d.cy(dj), 120, "I = 1 ; J = J + 1")
    d.si(dj, cj, 0, salida=(1, 0.5), entrada=(0, 0.5), pos=(-0.2, -9))
    d.va(cj, s1, salida=(1, 0.5), entrada=(1, 0.7), puntos=[(406, d.cy(cj)), (406, d.cy(s1, 0.7))])
    cf = d.cond("s1", A, 432, 175, "K = 1 ; J = 1<br>P = 1 ; SIGNO = 0")
    d.si(dj, cf, 1, salida=(0.5, 1), pos=(-0.3, 9))
    # ---------------------------------------------------------------- s2
    s2 = d.estado("s2", A, 504, 175, ["PIV = RAM(K,K)", "I = K + 1"])
    d.va(cf, s2)
    dz = d.decision("s2", A, 580, 130, 48, "RAM(K,K) = 0")
    d.va(s2, dz)
    cb = d.cond_en("s2", 335, d.cy(dz), 140, "BANCO(K) = RAM(K,K)")
    d.si(dz, cb, 0, salida=(1, 0.5), entrada=(0, 0.5), pos=(-0.1, -9))
    # ---------------------------------------------------------------- s3
    s3 = d.estado("s3", A, 656, 150, [])
    d.si(dz, s3, 1, salida=(0.5, 1), pos=(-0.3, 9))
    da = d.decision("s3", A, 704, 130, 48, "RAM(I,K) = 0")
    d.va(s3, da)
    dn = d.decision("s3", 322, d.cy(da) - 22, 100, 44, "I = N")
    d.si(da, dn, 1, salida=(1, 0.5), entrada=(0, 0.5), pos=(-0.1, -9))
    ci3 = d.cond_en("s3", 322, d.cy(s3), 96, "I = I + 1")
    d.si(dn, ci3, 0, salida=(0.5, 0), entrada=(0.5, 1), pos=(-0.2, 9))
    d.va(ci3, s3, salida=(0, 0.5), entrada=(1, 0.5))
    cd0 = d.cond("s3", 322, 776, 96, "DET = 0")
    d.si(dn, cd0, 1, salida=(0.5, 1), pos=(-0.3, 9))
    csg = d.cond("s3", A, 776, 160, "SIGNO = NOT SIGNO")
    d.si(da, csg, 0, salida=(0.5, 1), pos=(-0.3, 9))
    # ---------------------------------------------------------------- s4, s5
    s4 = d.estado("s4", A, 836, 175, ["RAM(I,J) = RAM(K,J)", "TMP = RAM(I,J)"])
    d.va(csg, s4)
    s5 = d.estado("s5", A, 918, 175, ["RAM(K,J) = TMP"])
    d.va(s4, s5)
    d5 = d.decision("s5", A, 978, 100, 44, "J = N")
    d.va(s5, d5)
    cj5 = d.cond_en("s5", 318, d.cy(d5), 96, "J = J + 1")
    d.si(d5, cj5, 0, salida=(1, 0.5), entrada=(0, 0.5), pos=(-0.2, -9))
    d.va(cj5, s4, salida=(1, 0.5), entrada=(1, 0.5), puntos=[(395, d.cy(cj5)), (395, d.cy(s4))])
    ck5 = d.cond("s5", A, 1046, 100, "J = K")
    d.si(d5, ck5, 1, salida=(0.5, 1), pos=(-0.3, 9))
    d.va(ck5, s2, salida=(0, 0.5), entrada=(0, 0.5), puntos=[(25, d.cy(ck5)), (25, d.cy(s2))])
    # ---------------------------------------------------------------- s13
    s13 = d.estado("s13", A, 1112, 150, ["FINAL = 1"])
    d.va(cd0, s13, salida=(1, 0.5), entrada=(1, 0.3), puntos=[(420, d.cy(cd0)), (420, d.cy(s13, 0.3))])
    i13 = d.decision("s13", A, 1170, 110, 44, "INICIO")
    d.va(s13, i13)
    d.si(i13, s13, 0, salida=(0, 0.5), entrada=(0, 0.5), puntos=[(40, d.cy(i13)), (40, d.cy(s13))], pos=(-0.75, -9))
    c13 = d.cond("s13", A, 1236, 175, "DIRA = 1 ; I = 1 ; J = 1")
    d.si(i13, c13, 1, salida=(0.5, 1), pos=(-0.3, 9))
    d.va(c13, s1, salida=(0, 0.5), entrada=(0, 0.5), puntos=[(10, d.cy(c13)), (10, d.cy(s1))])
    # ---------------------------------------------------------------- s6 a s10
    s6 = d.estado("s6", B, 30, 175, ["AIK = RAM(I,K)", "J = K + 1"])
    d.va(cb, s6, salida=(1, 0.5), entrada=(0.5, 0), puntos=[(455, d.cy(cb)), (455, 12), (B, 12)])
    s7 = d.estado("s7", B, 108, 175, ["X = PIV", "Y = RAM(I,J)"])
    d.va(s6, s7)
    s8 = d.estado("s8", B, 186, 175, ["R = X * Y", "X = AIK", "Y = RAM(K,J)"])
    d.va(s7, s8)
    s9 = d.estado("s9", B, 279, 175, ["S = X * Y"])
    d.va(s8, s9)
    s10 = d.estado("s10", B, 342, 175, ["R = R − S", "S = P", "COCIENTE = 0"])
    d.va(s9, s10)
    # ---------------------------------------------------------------- s11
    s11 = d.estado("s11", B, 435, 150, [])
    d.va(s10, s11)
    dm = d.decision("s11", B, 482, 130, 48, "R(49) = S(49)")
    d.va(s11, dm)
    ct0 = d.cond("s11", 568, 540, 96, "T = 0")
    ctr = d.cond("s11", 840, 540, 120, "T = R ; R = 0")
    d.si(dm, ct0, 1, salida=(0, 0.5), puntos=[(568, 506)], pos=(-0.5, -9))
    d.si(dm, ctr, 0, salida=(1, 0.5), puntos=[(840, 506)], pos=(-0.5, -9))
    dks = d.decision("s11", B, 598, 180, 56, "K + 1 = N Y<br>SIGNO = 1")
    d.va(ct0, dks, puntos=[(568, 584), (B, 584)])
    d.va(ctr, dks, puntos=[(840, 584), (B, 584)])
    cq1 = d.cond("s11", 568, 664, 165, "SQ = NOT (R(49) ⊕ S(49))")
    cq0 = d.cond("s11", 845, 664, 140, "SQ = R(49) ⊕ S(49)")
    d.si(dks, cq1, 1, salida=(0, 0.5), puntos=[(568, 626)], pos=(-0.5, -9))
    d.si(dks, cq0, 0, salida=(1, 0.5), puntos=[(845, 626)], pos=(-0.5, -9))
    # ---------------------------------------------------------------- s12
    s12 = d.estado("s12", B, 730, 150, [])
    d.va(cq1, s12, puntos=[(568, 712), (B, 712)])
    d.va(cq0, s12, puntos=[(845, 712), (B, 712)])
    drt = d.decision("s12", B, 778, 100, 44, "R = T")
    d.va(s12, drt)
    crs = d.cond_en("s12", 862, d.cy(drt), 100, "R = R − S")
    d.si(drt, crs, 0, salida=(1, 0.5), entrada=(0, 0.5), pos=(-0.1, -9))
    dsq = d.decision("s12", 862, d.cy(crs, 1) + 22, 76, 40, "SQ")
    d.va(crs, dsq)
    cmas = d.cond("s12", 862, d.cy(dsq, 1) + 20, 112, "COCIENTE =<br>COCIENTE + 1")
    d.si(dsq, cmas, 0, salida=(0.5, 1), pos=(-0.3, 9))
    cmen = d.cond("s12", 862, d.cy(cmas, 1) + 16, 112, "COCIENTE =<br>COCIENTE − 1")
    d.si(dsq, cmen, 1, salida=(0, 0.5), entrada=(0, 0.5), puntos=[(795, d.cy(dsq)), (795, d.cy(cmen))],
         pos=(-0.9, -9))
    vuelta = d.geo[s12][1] - 9
    d.va(cmas, s12, salida=(1, 0.5), entrada=(0.9, 0), puntos=[(945, d.cy(cmas)), (945, vuelta), (760, vuelta)])
    d.va(cmen, s12, salida=(1, 0.5), entrada=(0.9, 0), puntos=[(945, d.cy(cmen)), (945, vuelta), (760, vuelta)])
    cw = d.cond("s12", B, 846, 165, "RAM(I,J) = COCIENTE")
    d.si(drt, cw, 1, salida=(0.5, 1), pos=(-0.3, 9))
    dj12 = d.decision("s12", B, d.cy(cmen, 1) + 22, 100, 44, "J = N")
    d.va(cw, dj12)
    cj12 = d.cond_en("s12", 862, d.cy(dj12), 100, "J = J + 1")
    d.si(dj12, cj12, 0, salida=(1, 0.5), entrada=(0, 0.5), pos=(-0.1, -9))
    d.va(cj12, s7, salida=(1, 0.5), entrada=(1, 0.5), puntos=[(960, d.cy(cj12)), (960, d.cy(s7))])
    di12 = d.decision("s12", B, d.cy(dj12, 1) + 18, 100, 44, "I = N")
    d.si(dj12, di12, 1, salida=(0.5, 1), pos=(-0.3, 9))
    ci12 = d.cond_en("s12", 862, d.cy(di12), 100, "I = I + 1<br>J = K")
    d.si(di12, ci12, 0, salida=(1, 0.5), entrada=(0, 0.5), pos=(-0.1, -9))
    d.va(ci12, s6, salida=(1, 0.5), entrada=(1, 0.5), puntos=[(975, d.cy(ci12)), (975, d.cy(s6))])
    dk12 = d.decision("s12", B, d.cy(di12, 1) + 18, 110, 48, "K + 1 = N")
    d.si(di12, dk12, 1, salida=(0.5, 1), pos=(-0.3, 9))
    ck12 = d.cond_en("s12", 875, d.cy(dk12), 145, "P = PIV<br>K = K + 1 ; J = K + 1")
    d.si(dk12, ck12, 0, salida=(1, 0.5), entrada=(0, 0.5), pos=(-0.1, -9))
    d.va(ck12, s2, salida=(1, 0.5), entrada=(1, 0.5),
         puntos=[(990, d.cy(ck12)), (990, -6), (440, -6), (440, d.cy(s2))])
    cdc = d.cond("s12", B, d.cy(dk12, 1) + 22, 150, "DET = COCIENTE")
    d.si(dk12, cdc, 1, salida=(0.5, 1), pos=(-0.3, 9))
    d.va(cdc, s13, salida=(0.5, 1), entrada=(1, 0.7), puntos=[(B, d.cy(cdc, 1) + 14), (432, d.cy(cdc, 1) + 14),
                                                                     (432, d.cy(s13, 0.7))])
    d.cerrar_bloques()
    return d


# ===========================================================================
# Visualizador (XS3)
# ===========================================================================
SENALES_V = {
    "FINAL": lambda v: v["final"],
    "VAL(31)": lambda v: v["val_neg"],
    "CONT = 31": lambda v: v["cont_31"],
    "DÍGITO(D) > 4": lambda v: v["dig_4"],
    "D = 9": lambda v: v["d_9"],
}


def asm_xs3():
    d = ASM("asm_xs3")
    C = 300
    d.etiqueta(C - 20, 0, 40, 16, "rst", TXT)
    x0 = d.estado("x0", C, 30, 150, [])
    d.linea((C, 16), (C, 30), "", ARI)
    df = d.decision("x0", C, 78, 110, 44, "FINAL")
    d.va(x0, df)
    d.si(df, x0, 0, salida=(0, 0.5), entrada=(0, 0.5), puntos=[(185, d.cy(df)), (185, d.cy(x0))], pos=(-0.7, -9))
    dv = d.decision("x0", C, 144, 110, 44, "VAL(31)")
    d.si(df, dv, 1, salida=(0.5, 1), pos=(-0.3, 9))
    cneg = d.cond("x0", 150, 196, 150, "BIN = 0 − VAL<br>NEG = VAL(31)")
    cpos = d.cond("x0", 450, 196, 150, "BIN = VAL<br>NEG = VAL(31)")
    d.si(dv, cneg, 1, salida=(0, 0.5), puntos=[(150, 166)], pos=(-0.5, -9))
    d.si(dv, cpos, 0, salida=(1, 0.5), puntos=[(450, 166)], pos=(-0.5, -9))
    x1 = d.estado("x1", C, 268, 175, ["DEC = 0", "CONT = 0"], )
    d.va(cneg, x1, puntos=[(150, 252), (C, 252)])
    d.va(cpos, x1, puntos=[(450, 252), (C, 252)])
    x2 = d.estado("x2", C, 348, 175, ["DEC(0) = BIN(31)"])
    d.va(x1, x2)
    dc = d.decision("x2", C, 408, 120, 46, "CONT = 31")
    d.va(x2, dc)
    x5 = d.estado("x5", 495, d.cy(dc) - 26.5, 160, ["DISP = DEC", "DISP_NEG = NEG"])
    d.si(dc, x5, 1, salida=(1, 0.5), entrada=(0, 0.5), pos=(-0.3, -9))
    d.va(x5, x0, salida=(1, 0.5), entrada=(1, 0.5), puntos=[(600, d.cy(x5)), (600, d.cy(x0))])
    cd = d.cond("x2", C, 474, 110, "D = 0")
    d.si(dc, cd, 0, salida=(0.5, 1), pos=(-0.3, 9))
    x3 = d.estado("x3", C, 530, 150, [])
    d.va(cd, x3)
    dg = d.decision("x3", C, 578, 140, 48, "DÍGITO(D) &gt; 4")
    d.va(x3, dg)
    c3 = d.cond_en("x3", 475, d.cy(dg), 150, "DÍGITO(D) =<br>DÍGITO(D) + 3")
    d.si(dg, c3, 1, salida=(1, 0.5), entrada=(0, 0.5), pos=(-0.1, -9))
    d9 = d.decision("x3", C, 650, 100, 44, "D = 9")
    d.si(dg, d9, 0, salida=(0.5, 1), pos=(-0.3, 9))
    d.va(c3, d9, salida=(0.5, 1), entrada=(1, 0.5), puntos=[(475, d.cy(d9))])
    cdd = d.cond_en("x3", 160, d.cy(d9), 100, "D = D + 1")
    d.si(d9, cdd, 0, salida=(0, 0.5), entrada=(1, 0.5), pos=(-0.2, -9))
    d.va(cdd, x3, salida=(0.5, 0), entrada=(0, 0.5), puntos=[(160, d.cy(x3))])
    x4 = d.estado("x4", C, 720, 175, ["DEC = DEC &lt;&lt; 1", "BIN = BIN &lt;&lt; 1", "CONT = CONT + 1"])
    d.si(d9, x4, 1, salida=(0.5, 1), pos=(-0.3, 9))
    d.va(x4, x2, salida=(0, 0.5), entrada=(0, 0.5), puntos=[(95, d.cy(x4)), (95, d.cy(x2))])
    d.cerrar_bloques()
    return d


def todas():
    return [asm_bareiss(), asm_xs3()]


def revisar_todo(uc):
    """Revisa los dos ASM contra las tablas de transiciones de uc_cd.py."""
    e1, n1 = asm_bareiss().revisar(SENALES_P, uc.FILAS_P, uc.fila_de)
    e2, n2 = asm_xs3().revisar(SENALES_V, uc.FILAS_V, uc.fila_de)
    return e1 + e2, n1 + n2

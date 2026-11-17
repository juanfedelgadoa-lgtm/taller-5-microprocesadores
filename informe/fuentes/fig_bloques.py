"""Cajas negras, cajas grises y unidades de control (draw.io)."""
import drawio as D
import uc_cd as U

AZUL_OSC = "fontSize=13;"


def puerto(d, x, y, w, h, texto):
    return d.nodo(x, y, w, h, texto, D.PUERTO + "fontSize=11.5;")


def flecha_bits(d, a, b, bits, salida=(1, 0.5), entrada=(0, 0.5), puntos=()):
    est = D.ARISTA + "labelBackgroundColor=#FFFFFF;fontColor=#5B7FA6;fontSize=10;"
    return d.arista(a, b, bits, est, salida=salida, entrada=entrada, puntos=puntos, etiqueta_pos=(0, -8))


def caja_negra_sistema():
    d = D.Diagrama("caja_negra_sistema")
    ent = [("CLK<br>Reloj de 100 MHz (E3)", "1 bit"), ("RST<br>BTNU: reinicio", "1 bit"),
           ("INICIO<br>BTNC: comienza el cálculo", "1 bit"), ("DIR_P[2:0]<br>SW2..SW0: pivote a mostrar", "3 bits")]
    sal = [("SEG[6:0]<br>Segmentos CA..CG", "7 bits"), ("AN[7:0]<br>Selección de los 8 dígitos", "8 bits"),
           ("DP<br>Punto decimal apagado", "1 bit"), ("FINAL → LD0<br>Fin del cálculo", "1 bit"),
           ("DESBORDE → LD1<br>Más de 7 dígitos", "1 bit")]
    caja = d.nodo(250, 20, 300, 290, "<b>DETERMINANTE POR BAREISS</b><br><br>Antirrebote + divisor de frecuencia<br>"
                  "Procesador de Bareiss (UC + CD)<br>Visualizador XS3 + display<br><br>Nexys A7-100T",
                  D.CAJA + AZUL_OSC)
    for k, (t, b) in enumerate(ent):
        y = 40 + k * 66
        p = puerto(d, 0, y, 175, 42, t)
        flecha_bits(d, p, caja, b, entrada=(0, (y + 21 - 20) / 290))
    for k, (t, b) in enumerate(sal):
        y = 29 + k * 58
        p = puerto(d, 625, y, 175, 40, t)
        flecha_bits(d, caja, p, b, salida=(1, (y + 20 - 20) / 290))
    return d


def caja_negra_procesador():
    d = D.Diagrama("caja_negra_procesador")
    caja = d.nodo(220, 20, 260, 210, "<b>PROCESADOR DE BAREISS</b><br><br><font style='font-size:10px'>ROM 32 × 6 (matriz)<br>"
                  "RAM A y RAM B 32 × 32<br>Multiplicador 25 × 25<br>Sumador/restador 50 bits<br>"
                  "Banco de pivotes b1..b4</font>", D.CAJA + AZUL_OSC)
    ent = [("clk", "1 bit"), ("rst", "1 bit"), ("inicio", "1 bit"), ("dir_p[2:0]", "3 bits")]
    sal = [("det[31:0]<br>Determinante (C2)", "32 bits"), ("pivote[31:0]<br>Pivote dir_p (C2)", "32 bits"),
           ("final", "1 bit")]
    for k, (t, b) in enumerate(ent):
        y = 40 + k * 46
        p = puerto(d, 0, y, 140, 30, t)
        flecha_bits(d, p, caja, b, entrada=(0, (y + 15 - 20) / 210))
    for k, (t, b) in enumerate(sal):
        y = 40 + k * 62
        p = puerto(d, 560, y, 150, 40, t)
        flecha_bits(d, caja, p, b, salida=(1, (y + 20 - 20) / 210))
    return d


def caja_gris_sistema():
    d = D.Diagrama("caja_gris_sistema")
    P12 = "fontSize=12;"
    clk = d.nodo(0, 27, 84, 30, "CLK, RST", D.PUERTO + P12)
    ini = d.nodo(0, 150, 84, 30, "INICIO", D.PUERTO + P12)
    dp = d.nodo(0, 289, 84, 30, "DIR_P[2:0]", D.PUERTO + P12)
    frec = d.nodo(120, 10, 165, 70, "<b>divisor_frecuencia</b><br>tick_1ms (1 ms)", D.CAJA_GRIS + P12)
    anti = d.nodo(120, 130, 165, 70, "<b>antirrebote</b><br>un pulso por pulsación", D.CAJA_GRIS + P12)
    proc = d.nodo(335, 120, 180, 230, "<b>procesador_bareiss</b><br><br>UC + CD<br>ROM, RAM A, RAM B<br>"
                  "multiplicador<br>sumador/restador<br>banco de pivotes", D.CAJA_AZUL + P12)
    vis = d.nodo(575, 120, 165, 230, "<b>visualizador</b><br><br>ASM XS3<br>(binario → BCD)<br>+ display de<br>"
                 "8 dígitos", D.CAJA_VERDE + P12)
    fin = d.nodo(365, 374, 120, 28, "FINAL (LD0)", D.PUERTO + P12)
    seg = d.nodo(570, 374, 90, 28, "SEG, AN, DP", D.PUERTO + P12)
    des = d.nodo(668, 374, 115, 28, "DESBORDE (LD1)", D.PUERTO + P12)
    E = D.ARISTA + "labelBackgroundColor=#FFFFFF;fontSize=10.5;"
    d.arista(clk, frec, "", E, entrada=(0, round((42 - 10) / 70, 4)))
    d.arista(ini, anti, "botón", E, etiqueta_pos=(0, -9))
    d.arista(frec, anti, "tick", E, salida=(0.3, 1), entrada=(0.3, 0), etiqueta_pos=(0, 12))
    d.arista(anti, proc, "pulso → inicio", E, salida=(1, 0.5), entrada=(0, round(45 / 230, 4)),
             etiqueta_pos=(0, -9))
    d.arista(dp, proc, "3", E, salida=(1, 0.5), entrada=(0, round((304 - 120) / 230, 4)), etiqueta_pos=(0, -9))
    d.arista(dp, vis, "", E, salida=(0.5, 1), entrada=(0, round((332 - 120) / 230, 4)),
             puntos=[(42, 425), (548, 425), (548, 332)])
    d.arista(frec, vis, "tick (1 ms)", E, salida=(1, 0.5), entrada=(round(82 / 165, 4), 0), puntos=[(657, 45)],
             etiqueta_pos=(-0.3, -9))
    for k, (t, rel) in enumerate((("det (32)", 0.25), ("pivote (32)", 0.5), ("final", 0.75))):
        d.arista(proc, vis, t, E, salida=(1, rel), entrada=(0, rel), etiqueta_pos=(0, -9))
    d.arista(proc, fin, "", E, salida=(round(90 / 180, 4), 1), entrada=(0.5, 0))
    d.arista(vis, seg, "", E, salida=(round(40 / 165, 4), 1), entrada=(0.5, 0))
    d.arista(vis, des, "", E, salida=(round(150.5 / 165, 4), 1), entrada=(0.5, 0))
    d.etiqueta(100, 228, 210, 30, "<i>clk y rst llegan a los cuatro bloques</i>", D.TEXTO + "fontColor=#666666;"
               "fontSize=11;")
    return d


def caja_gris_procesador():
    d = D.Diagrama("caja_gris_procesador")
    P = "fontSize=12;"
    uc = d.nodo(90, 60, 160, 190, "<b>UNIDAD DE<br>CONTROL</b><br><br>14 estados<br>Mealy", D.CAJA_AZUL + "fontSize=13;")
    cd = d.nodo(420, 60, 170, 190, "<b>CAMINO DE<br>DATOS</b>", D.CAJA_VERDE + "fontSize=13;")
    E = D.ARISTA + "labelBackgroundColor=#FFFFFF;fontSize=11;"
    i1 = d.nodo(105, 0, 70, 26, "inicio", D.PUERTO + P)
    i2 = d.nodo(0, 110, 60, 26, "clk", D.PUERTO + P)
    i3 = d.nodo(0, 170, 60, 26, "rst", D.PUERTO + P)
    d.arista(i1, uc, "", E, salida=(0.5, 1), entrada=(round(50 / 160, 4), 0))
    d.arista(i2, uc, "", E, entrada=(0, round((123 - 60) / 190, 4)))
    d.arista(i3, uc, "", E, entrada=(0, round((183 - 60) / 190, 4)))
    fi = d.nodo(135, 300, 70, 26, "final", D.PUERTO + P)
    d.arista(uc, fi, "", E, salida=(0.5, 1))
    d.arista(uc, cd, "Palabra de control<br>(bits desconocidos)",
             E + "fontColor=#C00000;strokeColor=#C00000;", salida=(1, 0.25), entrada=(0, 0.25),
             etiqueta_pos=(0, -18))
    d.arista(cd, uc, "Señales de estado (9 bits):<br>z_b, z_a, i_n, j_n, k1_n,<br>ms, sg, rt, sq",
             E + "fontColor=#1F4E9A;strokeColor=#1F4E9A;", salida=(0, 0.72), entrada=(1, 0.72),
             etiqueta_pos=(0, 30))
    o1 = d.nodo(410, 0, 100, 26, "dir_p[2:0]", D.PUERTO + P)
    d.arista(o1, cd, "3", E, salida=(0.5, 1), entrada=(round(40 / 170, 4), 0), etiqueta_pos=(0, -9))
    c2 = d.nodo(530, 0, 80, 26, "clk, rst", D.PUERTO + P)
    d.arista(c2, cd, "", E, salida=(0.5, 1), entrada=(round(150 / 170, 4), 0))
    o2 = d.nodo(660, 90, 120, 34, "det[31:0]", D.PUERTO + P)
    o3 = d.nodo(660, 180, 120, 34, "pivote[31:0]", D.PUERTO + P)
    d.arista(cd, o2, "32", E, salida=(1, round((107 - 60) / 190, 4)), etiqueta_pos=(0, -9))
    d.arista(cd, o3, "32", E, salida=(1, round((197 - 60) / 190, 4)), etiqueta_pos=(0, -9))
    return d


def uc_canonica(nombre, n, c_sig, c_pc, final, senales_sig, senales_pc):
    """UC con ROM de entrada, registro de estado y ROM de salida. La palabra de
    control queda en XX bits: el diseño es de alto nivel y no hay un camino de
    datos dibujado del que salga su tamaño."""
    d = D.Diagrama(nombre)
    filas_e = 2 ** (n + c_sig)
    filas_s = 2 ** (n + c_pc)
    C = D.CAJA + "fontSize=12.5;"
    ancho_s = "(XX + 1)" if final else "XX"
    re = d.nodo(20, 100, 175, 110, f"<b>ROM DE ENTRADA</b><br>2^{n + c_sig} × {n} = {filas_e} × {n}<br>"
                f"D = estado siguiente", C)
    rg = d.nodo(255, 100, 140, 110, f"<b>REGISTRO DE<br>ESTADO</b><br>{n} flip-flops D<br>clk / rst", C)
    rs = d.nodo(455, 100, 185, 110, f"<b>ROM DE SALIDA</b><br>2^{n + c_pc} × {ancho_s}<br>= {filas_s} × {ancho_s}", C)
    cond = d.nodo(20, 0, 175, 54, "Condiciones:<br>" + senales_sig, D.PUERTO + "fontSize=11;")
    cp = d.nodo(455, 0, 185, 54, "Condiciones (Mealy):<br>" + senales_pc, D.PUERTO + "fontSize=11;")
    out = d.nodo(455, 262, 185, 44, "Palabra de control (XX bits)" + ("<br>FINAL (1 bit)" if final else ""),
                 D.PUERTO + "fontSize=11.5;")
    E = D.ARISTA + "labelBackgroundColor=#FFFFFF;fontSize=11;"
    d.arista(cond, re, f"{c_sig} bits", E, salida=(0.5, 1), entrada=(0.5, 0), etiqueta_pos=(0, -22))
    d.arista(cp, rs, f"{c_pc} bits", E, salida=(0.5, 1), entrada=(0.5, 0), etiqueta_pos=(0, -22))
    d.arista(re, rg, f"D[{n - 1}:0]", E, etiqueta_pos=(0, -9))
    d.arista(rg, rs, f"Q[{n - 1}:0]", E, etiqueta_pos=(0, -9))
    d.arista(rg, re, "Q realimentado", E, salida=(0.5, 1), entrada=(0.5, 1), puntos=[(325, 245), (107.5, 245)],
             etiqueta_pos=(0, 10))
    d.arista(rs, out, ancho_s.strip("()") + " bits", E, salida=(0.5, 1), entrada=(0.5, 0), etiqueta_pos=(0, -30))
    return d


def todas():
    return [caja_negra_sistema(), caja_negra_procesador(), caja_gris_sistema(), caja_gris_procesador(),
            uc_canonica("uc_procesador", 4, 7, 10, True,
                        "inicio, z_b, z_a, i_n,<br>j_n, k1_n, rt",
                        "inicio, z_b, z_a, i_n, j_n,<br>k1_n, ms, sg, rt, sq"),
            uc_canonica("uc_visualizador", 3, 3, 5, False, "final, cont_31, d_9",
                        "final, val_neg, cont_31,<br>dig_4, d_9")]

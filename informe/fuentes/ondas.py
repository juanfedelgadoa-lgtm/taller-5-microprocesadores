#!/usr/bin/env python3
"""Figuras de simulación del informe (formas de onda con el aspecto de ISim).

Simula sim/tb_informe.vhd con GHDL para varias matrices, sin cambiar los
archivos de src/: la ROM de cada caso se escribe en una copia del procesador
(sim/modelo_referencia.py, función escribir_rom con destino). Lee el archivo
.ghw con ghwdump (incluye las señales de estado st y xs) y dibuja las ondas
con matplotlib en informe/figuras/sim_*.png.

  GHDL=/ruta/ghdl python3 informe/fuentes/ondas.py
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(os.environ.get("HOME", "/tmp")) / ".mpl"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402
from PIL import Image  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "sim"))
import modelo_referencia as M  # noqa: E402

GHDL = os.environ.get("GHDL", "/projects/sandbox/.tools/ghdl/bin/ghdl")
GHWDUMP = os.environ.get("GHWDUMP", str(Path(GHDL).with_name("ghwdump")))
TRABAJO = Path(os.environ.get("SIMW", "/projects/sandbox/.tools/simwork"))
FIGURAS = RAIZ / "informe" / "figuras"
OPC = ["-fsynopsys", "-fexplicit"]


def correr(args, cwd):
    r = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, args))}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def simular(a, nombre, espera, fin_ns):
    w = TRABAJO / nombre
    shutil.rmtree(w, ignore_errors=True)
    w.mkdir(parents=True)
    proc = M.escribir_rom(a, destino=w / "procesador_bareiss.vhd")
    for f in (RAIZ / "src" / "RAM_memory.vhd", proc, RAIZ / "src" / "visualizador.vhd",
              RAIZ / "sim" / "tb_informe.vhd"):
        correr([GHDL, "-a", *OPC, f"--workdir={w}", f], w)
    correr([GHDL, "-e", *OPC, f"--workdir={w}", "tb_informe"], w)
    correr([GHDL, "-r", *OPC, f"--workdir={w}", "tb_informe", f"-gESPERA={espera}", f"-gN={len(a)}",
            "--ieee-asserts=disable-at-0", f"--stop-time={fin_ns}ns", f"--wave={w / 'ondas.ghw'}"], w)
    return w / "ondas.ghw"


def leer_ghw(ruta, nombres):
    """{nombre: [(t_ns, valor)]} con un valor por cambio. Los vectores quedan
    como cadena de bits (MSB primero) y los enumerados con su nombre."""
    mapa = {}
    for linea in correr([GHWDUMP, "-H", ruta], ruta.parent).splitlines():
        m = re.match(r"\s*(?:signal|port-in|port-out) (\S+): (.+): #(\d+)(?:-#(\d+))?$", linea)
        if m and m.group(1) not in mapa:
            i0, i1 = int(m.group(3)), int(m.group(4) or m.group(3))
            mapa[m.group(1)] = (list(range(i0, i1 + 1)), "vector" in m.group(2))
    ids = sorted({i for n in nombres for i in mapa[n][0]})
    texto = correr([GHWDUMP, "-s", "-f", ",".join(map(str, ids)), ruta], ruta.parent)
    tiempos = []
    for linea in texto.splitlines():
        if linea.startswith("Time is"):
            t = int(linea.split()[2]) / 1e6
            if tiempos and tiempos[-1][0] == t:
                tiempos.pop()                       # se queda el último delta
            tiempos.append((t, {}))
        else:
            m = re.match(r"#(\d+): (\S+)", linea)
            if m:
                tiempos[-1][1][int(m.group(1))] = m.group(2).strip("'")
    out = {}
    for n in nombres:
        idx, vec = mapa[n]
        seq = []
        for t, vals in tiempos:
            v = "".join(vals[i] for i in idx) if vec else vals[idx[0]]
            if not seq or seq[-1][1] != v:
                seq.append((t, v))
        out[n] = seq
    return out


def valor(v, fmt):
    if fmt in ("enum", "bit"):
        return v
    if any(c not in "01" for c in v):
        return "U" if "U" in v else "X"
    x = int(v, 2)
    if fmt == "sdec":
        return str(x - (1 << len(v)) if v[0] == "1" else x)
    if fmt == "hex":
        return format(x, f"0{(len(v) + 3) // 4}X")
    return str(x)


def en(seq, t):
    """Valor de una serie en el instante t."""
    v = seq[0][1]
    for tt, vv in seq:
        if tt > t:
            break
        v = vv
    return v


# ---------------------------------------------------------------------------
# Dibujo con el aspecto de la ventana de ondas de ISim
# ---------------------------------------------------------------------------
VERDE = "#00E000"
FONDO = "#000000"


def dibujar(datos, filas, t0, t1, salida, ancho=6.6, alto_fila=0.29, marcas=None, titulo=None):
    n = len(filas)
    banda = 0.24 if titulo else 0.0
    alto = 0.42 + n * alto_fila + banda
    fig = plt.figure(figsize=(ancho, alto), dpi=220)
    izq = 1.2 / ancho
    arriba = 1 - banda / alto
    ax_n = fig.add_axes([0, 0, izq, arriba - 0.30 / alto])
    ax = fig.add_axes([izq, 0, 1 - izq, arriba - 0.30 / alto])
    ax_r = fig.add_axes([izq, arriba - 0.30 / alto, 1 - izq, 0.30 / alto])
    for a in (ax_n, ax, ax_r):
        a.set_xticks([])
        a.set_yticks([])
        for s in a.spines.values():
            s.set_visible(False)
    ax_n.set_facecolor("#FFFFFF")
    ax.set_facecolor(FONDO)
    ax_r.set_facecolor(FONDO)
    ax.set_xlim(t0, t1)
    ax.set_ylim(n, 0)
    ax_r.set_xlim(t0, t1)
    ax_r.set_ylim(0, 1)
    ax_n.set_xlim(0, 1)
    ax_n.set_ylim(n, 0)
    # regla de tiempo
    paso = next(p for p in (10, 20, 50, 100, 200, 500, 1000, 2000, 5000) if (t1 - t0) / p <= 12)
    t = (int(t0 // paso) + 1) * paso
    if t - t0 < 0.04 * (t1 - t0):
        t += paso
    while t <= t1 - 0.03 * (t1 - t0):
        ax_r.plot([t, t], [0, 0.3], color="#FFFFFF", lw=0.6)
        ax_r.text(t, 0.42, f"{t:g} ns", color="#FFFFFF", fontsize=7, ha="center", va="bottom")
        ax.plot([t, t], [0, n], color="#303030", lw=0.4, zorder=0)
        t += paso
    ax_n.plot([0.98, 0.98], [0, n], color="#999999", lw=0.5)
    if titulo:
        fig.text(0.01, 1 - banda / 2 / alto, titulo, fontsize=8, fontweight="bold", va="center", ha="left")
    ux = (t1 - t0) / ((1 - izq) * ancho)       # ns por pulgada
    for k, (etq, nombre, fmt) in enumerate(filas):
        ax_n.text(0.05, k + 0.5, etq, fontsize=7.6, va="center", ha="left", color="#000000",
                  family="DejaVu Sans")
        ax.plot([t0, t1], [k + 1, k + 1], color="#202020", lw=0.4)
        seq = [(max(t0, tt), v) for tt, v in datos[nombre] if tt < t1]
        # recorta al inicio de la ventana
        ini = en(datos[nombre], t0)
        seq = [(t0, ini)] + [(tt, v) for tt, v in seq if tt > t0]
        tramos = [(seq[i][0], seq[i + 1][0] if i + 1 < len(seq) else t1, seq[i][1]) for i in range(len(seq))]
        y_al, y_ba = k + 0.2, k + 0.8
        if fmt == "bit":
            xs, ys = [], []
            for a, b, v in tramos:
                y = y_al if v == "1" else y_ba
                xs += [a, b]
                ys += [y, y]
                if v not in "01":
                    ax.fill_between([a, b], y_al, y_ba, color="#E05000", alpha=0.6, lw=0)
            ax.plot(xs, ys, color=VERDE, lw=0.7, drawstyle="default")
        else:
            d = min(0.25 * (t1 - t0) / 200, 2.0)
            for a, b, v in tramos:
                txt = valor(v, fmt)
                dd = min(d, (b - a) / 2)
                malo = txt in ("U", "X")
                col = "#E05000" if malo else VERDE
                pts = [(a, k + 0.5), (a + dd, y_al), (b - dd, y_al), (b, k + 0.5), (b - dd, y_ba), (a + dd, y_ba)]
                ax.add_patch(Polygon(pts, closed=True, fill=False, edgecolor=col, lw=0.6))
                ancho_txt = (len(txt) * 6.8 * 0.6 / 72 + 0.03) * ux
                if b - a > ancho_txt:
                    ax.text((a + b) / 2, k + 0.52, txt, color="#FFFFFF", fontsize=6.8, ha="center", va="center",
                            family="DejaVu Sans")
    for tm, texto in (marcas or []):
        ax.plot([tm, tm], [0, n], color="#FFD700", lw=0.7)
        cerca = tm > t1 - 0.12 * (t1 - t0)
        ax_r.text(tm + (-1 if cerca else 1) * 0.004 * (t1 - t0), 0.02, texto, color="#FFD700", fontsize=6.6,
                  ha="right" if cerca else "left", va="bottom")
    fig.savefig(salida, dpi=220, facecolor="#FFFFFF")
    plt.close(fig)
    return salida


# ---------------------------------------------------------------------------
# Casos del informe
# ---------------------------------------------------------------------------
U = "/tb_informe/uut/"
V = "/tb_informe/uvis/"
P = "/tb_informe/"


def ciclo_final(datos):
    return next(t for t, v in datos[P + "final"] if v == "1")


def apilar(partes, salida, sep=18):
    """Une varias imágenes una debajo de otra."""
    imgs = [Image.open(p) for p in partes]
    w = max(i.width for i in imgs)
    h = sum(i.height for i in imgs) + sep * (len(imgs) - 1)
    out = Image.new("RGB", (w, h), "white")
    y = 0
    for i in imgs:
        out.paste(i, (0, y))
        y += i.height + sep
    out.save(salida)
    for p in partes:
        Path(p).unlink()
    return salida


def caso_procesador(num, nombre, paneles):
    """paneles: lista de (función (tf, t_fin) -> (t0, t1), filas, título)."""
    a = M.MATRICES[num]
    n = len(a)
    _, _, _ = M.bareiss(a)
    ghw = simular(a, nombre, espera=4, fin_ns=60_000)
    nombres = sorted({f[1] for _, filas, _ in paneles for f in filas} | {P + "final", P + "det", P + "pivote"})
    datos = leer_ghw(ghw, nombres)
    tf = ciclo_final(datos)
    t_fin = tf + 10 * (4 + 3 * n) + 12
    partes = []
    for k, (ventana, filas, titulo) in enumerate(paneles):
        t0, t1 = ventana(tf, t_fin)
        marcas = [(m, txt) for m, txt in ((45, "inicio"), (tf, "final = 1")) if t0 <= m <= t1]
        partes.append(dibujar(datos, filas, t0, t1, FIGURAS / f"{nombre}_{k}.png", marcas=marcas, titulo=titulo))
    salida = apilar(partes, FIGURAS / f"{nombre}.png") if len(partes) > 1 else partes[0].rename(
        FIGURAS / f"{nombre}.png")
    det, piv, _ = M.bareiss(a)
    piv_sim = [valor(en(datos[P + "pivote"], tf + 10 * (4 + 3 * k) + 25), "sdec") for k in range(n)]
    return dict(nombre=nombre, n=n, det=det, pivotes=piv, t_final=tf, ciclos=round((tf - 45) / 10),
                det_sim=valor(en(datos[P + "det"], t_fin), "sdec"), pivotes_sim=piv_sim)


def caso_xs3(num=3):
    a = M.MATRICES[num]
    ghw = simular(a, "sim_xs3", espera=400, fin_ns=60_000)
    filas = [("clk", P + "clk", "bit"), ("final", P + "final", "bit"), ("dir_p[2:0]", P + "dir_p", "udec"),
             ("det[31:0]", P + "det", "sdec"), ("xs (estado)", V + "xs", "enum"),
             ("bin[31:0]", V + "bin", "hex"), ("cont[4:0]", V + "cont", "udec"), ("d[3:0]", V + "d", "udec"),
             ("dec[39:0]", V + "dec", "hex"), ("disp[39:0]", V + "disp", "hex"), ("disp_neg", V + "disp_neg", "bit")]
    datos = leer_ghw(ghw, sorted({f[1] for f in filas}))
    tf = ciclo_final(datos)
    tx5 = next(t for t, v in datos[V + "xs"] if v == "x5" and t > tf)
    partes = [dibujar(datos, filas, tf - 100, tx5 + 260, FIGURAS / "sim_xs3_0.png",
                      marcas=[(tf, "final = 1"), (tx5 + 10, "disp ← dec")],
                      titulo="a) Conversión completa de det = 362 (376 ciclos)"),
              dibujar(datos, filas, tx5 - 330, tx5 + 60, FIGURAS / "sim_xs3_1.png",
                      marcas=[(tx5 + 10, "disp ← dec")], titulo="b) Últimos bits y paso del resultado al display")]
    apilar(partes, FIGURAS / "sim_xs3.png")
    det = M.bareiss(a)[0]
    return dict(nombre="sim_xs3", det=det, t_final=tf, t_x5=tx5, ciclos=round((tx5 + 10 - tf) / 10),
                disp=valor(en(datos[V + "disp"], tx5 + 50), "hex"))


def todos():
    clk = [("clk", P + "clk", "bit")]
    ctrl = [("rst", P + "rst", "bit"), ("inicio", P + "inicio", "bit")]
    idx = [("st (estado)", U + "st", "enum"), ("k[2:0]", U + "k", "udec"), ("i[2:0]", U + "i", "udec"),
           ("j[2:0]", U + "j", "udec")]
    fin = [("final", P + "final", "bit"), ("det[31:0]", P + "det", "sdec"), ("dir_p[2:0]", P + "dir_p", "udec"),
           ("pivote[31:0]", P + "pivote", "sdec")]
    coc = [("cociente[31:0]", U + "cociente", "sdec")]
    sig = [("signo", U + "signo", "bit")]
    return [
        caso_procesador(1, "sim_3x3", [(lambda tf, te: (0, te), clk + ctrl + idx + coc + fin, None)]),
        caso_procesador(2, "sim_4x4_cero", [
            (lambda tf, te: (0, 420), clk + ctrl + idx + sig + [("qa[31:0]", U + "qa", "sdec"),
                                                             ("qb[31:0]", U + "qb", "sdec")],
             "a) Copia de la ROM, pivote a(1,1) = 0 e intercambio de filas"),
            (lambda tf, te: (tf - 250, te), clk + idx + sig + coc + fin,
             "b) Última división (cuenta hacia abajo porque signo = 1) y recorrido de dir_p")]),
        caso_procesador(3, "sim_5x5", [
            (lambda tf, te: (0, tf * 1.07), [ctrl[1]] + idx[:3] + [("final", P + "final", "bit"),
                                                                     ("det[31:0]", P + "det", "sdec")],
             "a) Cálculo completo (37,7 µs)"),
            (lambda tf, te: (tf - 150, te), clk + idx + coc + fin, "b) Fin de la última división y recorrido de dir_p")]),
        caso_xs3(3),
    ]


if __name__ == "__main__":
    for r in todos():
        print(r)

#!/usr/bin/env python3
"""Genera las figuras del informe en draw.io (informe/figuras/*.drawio) y sus PNG.

  python3 informe/fuentes/generar_figuras.py            # .drawio y PNG
  python3 informe/fuentes/generar_figuras.py --solo-xml # solo los .drawio

Para los PNG usa render_drawio.js (Node + Playwright) con el visor de draw.io;
las rutas se toman de las variables VISOR, NODE_PATH y PLAYWRIGHT_BROWSERS_PATH.
"""
import os
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
CARPETA = AQUI.parent / "figuras"

import fig_asm  # noqa: E402
import uc_cd  # noqa: E402


def todas():
    figs = [f() for f in fig_asm.HOJAS_BAREISS] + [fig_asm.asm_xs3()]
    try:
        import fig_bloques
        figs += fig_bloques.todas()
    except ImportError:
        pass
    try:
        import fig_cd
        figs += fig_cd.todas()
    except ImportError:
        pass
    return figs


def main():
    errores, _ = fig_asm.revisar_bareiss(uc_cd.FILAS_P, uc_cd.FILAS_V)
    for e in errores:
        print("ERROR ASM:", e)
    if errores:
        sys.exit(1)
    print("Reglas del ASM y estados siguientes verificados (procesador y XS3).")
    CARPETA.mkdir(exist_ok=True)
    rutas = [d.guardar(CARPETA) for d in todas()]
    if "--solo-xml" in sys.argv:
        return
    solo = [a for a in sys.argv[1:] if not a.startswith("--")]
    if solo:
        rutas = [r for r in rutas if any(s in r.stem for s in solo)]
    args = []
    for r in rutas:
        args += [str(r), str(r.with_suffix(".png"))]
    subprocess.run(["node", str(AQUI / "render_drawio.js"), *args], check=True, env=os.environ)


if __name__ == "__main__":
    main()

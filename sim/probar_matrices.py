#!/usr/bin/env python3
"""Prueba el procesador con las 8 matrices de modelo_referencia.py usando GHDL.

Para cada matriz escribe una copia temporal de src/procesador_bareiss.vhd con
esa matriz en la ROM, y la copia de la ROM que lee el testbench
(sim/rom_prueba.vhd), las compila y corre sim/tb_procesador.vhd (que se
autoverifica). No modifica src/ ni sim/.

Uso:
  python3 sim/probar_matrices.py              # matrices 0 a 6
  python3 sim/probar_matrices.py --todas      # incluye la 7 (unos 15 minutos mas)
  python3 sim/probar_matrices.py --solo 7     # solo una matriz
Variable de entorno GHDL: ruta al ejecutable (por defecto "ghdl").
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from modelo_referencia import MATRICES, escribir_rom, escribir_rom_prueba  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
GHDL = os.environ.get("GHDL", "ghdl")


def probar(num, matriz, carpeta, corridas):
    trabajo = Path(carpeta) / f"m{num}"
    trabajo.mkdir()
    copia = escribir_rom(matriz, trabajo / "procesador_bareiss.vhd")
    rom_tb = escribir_rom_prueba(matriz, trabajo / "rom_prueba.vhd")
    banderas = ["-fsynopsys", "-fexplicit", f"--workdir={trabajo}"]
    archivos = [str(RAIZ / "src" / "RAM_memory.vhd"), str(copia), str(rom_tb),
                str(RAIZ / "sim" / "pkg_prueba.vhd"),
                str(RAIZ / "sim" / "tb_procesador.vhd")]
    subprocess.run([GHDL, "-a", *banderas, *archivos], check=True)
    subprocess.run([GHDL, "-e", *banderas, "tb_procesador"], check=True)
    salida = subprocess.run([GHDL, "-r", *banderas, "tb_procesador", f"-gCORRIDAS={corridas}",
                             "--ieee-asserts=disable-at-0"],
                            capture_output=True, text=True).stdout
    lineas = [re.sub(r"^.*\(report (note|error|failure)\): ", "", l) for l in salida.splitlines()
              if "report" in l]
    return lineas


if __name__ == "__main__":
    if "--solo" in sys.argv:
        numeros = [int(sys.argv[sys.argv.index("--solo") + 1])]
    else:
        numeros = list(range(8 if "--todas" in sys.argv else 7))
    resumen = []
    with tempfile.TemporaryDirectory() as tmp:
        for num in numeros:
            lineas = probar(num, MATRICES[num], tmp, 1 if num == 7 else 2)
            ok = any("TODAS LAS PRUEBAS PASARON" in l for l in lineas)
            print(f"== Matriz {num}")
            for l in lineas:
                print("   " + l, flush=True)
            resumen.append((num, ok))
    print()
    for num, ok in resumen:
        print(f"Matriz {num}: {'PASA' if ok else 'FALLA'}")
    sys.exit(0 if all(ok for _, ok in resumen) else 1)

#!/usr/bin/env python3
"""Modelo de referencia del procesador del Taller 5 (Bareiss + XS3).

Sirve para:
  1. Calcular el determinante y los pivotes que debe mostrar la FPGA, con la
     MISMA regla de busqueda de pivote que el ASM (primera fila r > k con
     a(r,k) /= 0). El ultimo pivote (posicion n del banco) es el determinante.
  2. Escribir src/rom_matriz.vhd con la matriz que se quiera evaluar.

Uso:
  python3 sim/modelo_referencia.py
      Muestra det y pivotes de las 8 matrices de prueba.

  python3 sim/modelo_referencia.py rom 3
      Escribe src/rom_matriz.vhd con la matriz de prueba 3.

  python3 sim/modelo_referencia.py rom "2 1 3; 1 4 2; 3 2 5"
      Escribe src/rom_matriz.vhd con esa matriz (filas separadas por ';').
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Matrices de prueba (todas simetricas, elementos en [-32, 31]).
MATRICES = [
    # 0: 2x2 sencilla
    [[7, -3],
     [-3, 5]],
    # 1: 3x3 del ejemplo del documento
    [[2, 1, 3],
     [1, 4, 2],
     [3, 2, 5]],
    # 2: 4x4 con a11 = 0 (intercambio de filas en k = 1)
    [[0, 2, 1, 3],
     [2, 1, 0, 1],
     [1, 0, 3, 2],
     [3, 1, 2, 4]],
    # 3: 5x5 general, determinante positivo, pivotes negativos
    [[4, -2, 1, 3, 0],
     [-2, 6, 2, -1, 5],
     [1, 2, -7, 4, 2],
     [3, -1, 4, 5, -3],
     [0, 5, 2, -3, 8]],
    # 4: 3x3 con pivote negativo e intercambio en el ultimo paso (k = 2)
    [[-2, 4, 1],
     [4, -8, 3],
     [1, 3, 5]],
    # 5: 4x4 con pivote cero en k = 2 (intercambio con p /= 1)
    [[1, 2, 3, 0],
     [2, 4, 1, 5],
     [3, 1, -2, 4],
     [0, 5, 4, -3]],
    # 6: 5x5 singular: la columna 1 es cero, no hay fila para intercambiar
    [[0, 0, 0, 0, 0],
     [0, 3, 1, 2, 4],
     [0, 1, 5, -2, 1],
     [0, 2, -2, 6, 3],
     [0, 4, 1, 3, 7]],
    # 7: 5x5 con valores extremos; |det| > 9 999 999 (desborde del display)
    [[30, 27, 24, -29, -31],
     [27, -21, 28, 29, -24],
     [24, 28, 2, -28, -28],
     [-29, 29, -28, -27, 28],
     [-31, -24, -28, 28, -30]],
]

MATRIZ_POR_DEFECTO = 3       # la que queda en src/rom_matriz.vhd


def bareiss(a):
    """Bareiss con la misma secuencia que el ASM.

    Devuelve (det, pivotes, intercambios). pivotes tiene n posiciones:
    pivote k = a(k,k) usado en el paso k (k = 1..n-1) y pivote n = det.
    Si la matriz es singular, los pivotes que no se alcanzan quedan en 0."""
    m = [fila[:] for fila in a]
    n = len(m)
    p = 1
    signo = 1
    pivotes = [0] * n
    intercambios = []
    for k in range(n - 1):
        if m[k][k] == 0:
            r = next((r for r in range(k + 1, n) if m[r][k] != 0), None)
            if r is None:
                return 0, pivotes, intercambios
            m[k], m[r] = m[r], m[k]
            signo = -signo
            intercambios.append((k + 1, r + 1))
        pivotes[k] = m[k][k]
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                num = m[k][k] * m[i][j] - m[i][k] * m[k][j]
                assert num % p == 0, "division no exacta"
                m[i][j] = num // p
                assert abs(m[i][j]) < 2 ** 31
        p = m[k][k]
    det = signo * m[n - 1][n - 1]
    pivotes[n - 1] = det
    return det, pivotes, intercambios


def det_cofactores(a):
    """Determinante por cofactores (solo para validar el modelo)."""
    n = len(a)
    if n == 1:
        return a[0][0]
    return sum((-1) ** c * a[0][c] *
               det_cofactores([f[:c] + f[c + 1:] for f in a[1:]])
               for c in range(n))


def texto_display(valor):
    """Texto de 8 digitos que debe verse en la Nexys A7 (signo + 7 digitos)."""
    signo = '-' if valor < 0 else ' '
    return signo + str(abs(valor) % 10 ** 7).zfill(7)


def bin6(x):
    """Entero en complemento a 2 de 6 bits."""
    return format(x & 0x3F, "06b")


def validar(a):
    n = len(a)
    assert 2 <= n <= 5, "n debe estar entre 2 y 5"
    assert all(len(f) == n for f in a), "la matriz debe ser cuadrada"
    assert all(-32 <= x <= 31 for f in a for x in f), "elementos fuera de [-32, 31]"
    if any(a[i][j] != a[j][i] for i in range(n) for j in range(n)):
        print("Aviso: la matriz no es simetrica (el diseno funciona igual).")


def texto_rom(a):
    """Contenido de src/rom_matriz.vhd para la matriz a (orden por columnas)."""
    validar(a)
    n = len(a)
    det, piv, inter = bareiss(a)
    filas_txt = "\n".join("--   " + " ".join(f"{x:4d}" for x in f) for f in a)
    lineas = [f'    a <= "{bin6(n)}" when "00000",   -- 00h: n = {n}']
    d = 1
    for j in range(n):
        for i in range(n):
            lineas.append(f'         "{bin6(a[i][j])}" when "{d:05b}",   -- {d:02X}h: a{i+1}{j+1} = {a[i][j]}')
            d += 1
    lineas.append('         "000000" when others;')
    piv_txt = ", ".join(str(x) for x in piv)
    return f"""----------------------------------------------------------------------------------
-- ROM DE LA MATRIZ (32 x 6 bits, lectura combinacional)
--
-- Hace parte de la arquitectura del procesador: para calcular el determinante
-- de otra matriz se cambia este archivo y se vuelve a programar la FPGA.
-- Archivo generado con: python3 sim/modelo_referencia.py rom ...
--
-- Posicion 00h = n; luego los elementos a(i,j) por columnas (a11, a21, ...),
-- como en la Figura 1 del taller. Datos en complemento a 2 (-32 a 31).
--
-- Matriz ({n}x{n}):
{filas_txt}
-- Resultado esperado: det = {det}
-- Pivotes (dir_p = 1..{n}): {piv_txt}
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity rom_matriz is
    Port ( dira : in  STD_LOGIC_VECTOR (4 downto 0);
           a    : out STD_LOGIC_VECTOR (5 downto 0));
end rom_matriz;

architecture Behavioral of rom_matriz is
begin

with dira select
{chr(10).join(lineas)}

end Behavioral;
"""


def escribir_rom(a, ruta=RAIZ / "src" / "rom_matriz.vhd"):
    Path(ruta).write_text(texto_rom(a), encoding="ascii")
    return ruta


def leer_matriz(txt):
    return [[int(x) for x in fila.split()] for fila in txt.split(";") if fila.strip()]


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "rom":
        arg = sys.argv[2]
        a = MATRICES[int(arg)] if arg.isdigit() else leer_matriz(arg)
        ruta = escribir_rom(a, sys.argv[3] if len(sys.argv) > 3 else RAIZ / "src" / "rom_matriz.vhd")
        det, piv, inter = bareiss(a)
        print(f"Escrito {ruta}")
        print(f"det = {det}   display = '{texto_display(det)}'")
        for k, v in enumerate(piv, start=1):
            print(f"   dir_p = {k}: pivote = {v}   display = '{texto_display(v)}'")
        sys.exit(0)

    for num, a in enumerate(MATRICES):
        validar(a)
        n = len(a)
        det, piv, inter = bareiss(a)
        assert det == det_cofactores(a), "el modelo no coincide con cofactores"
        print(f"Matriz {num}: {n}x{n}  det = {det}  display = '{texto_display(det)}'"
              f"  intercambios = {inter}")
        print(f"   pivotes (dir_p = 1..{n}) = {piv}")

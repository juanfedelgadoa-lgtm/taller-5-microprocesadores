#!/usr/bin/env python3
"""Modelo de referencia del procesador del Taller 5 (Bareiss + XS3).

Sirve para:
  1. Calcular el determinante y los pivotes que debe mostrar la FPGA para
     cada matriz de la ROM, usando la MISMA regla de busqueda de pivote que
     el ASM (primera fila r > k con a(r,k) /= 0).
  2. Estimar cuantos ciclos de reloj tarda cada calculo (la division por
     restas sucesivas tarda |cociente| + 1 ciclos).
  3. Generar las lineas de la ROM en VHDL para matrices nuevas.

Uso:  python3 modelo_referencia.py
"""

# Matrices de prueba (todas simetricas, elementos en [-32, 31]).
# El indice de la lista es la pagina de la ROM (switches SW15..SW13).
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
    # 3: 5x5 general, determinante negativo
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
    # 7: 5x5 con valores extremos; |det| > 9 999 999 (prueba de desborde
    #    del display y de los anchos de palabra)
    [[30, 27, 24, -29, -31],
     [27, -21, 28, 29, -24],
     [24, 28, 2, -28, -28],
     [-29, 29, -28, -27, 28],
     [-31, -24, -28, 28, -30]],
]


def bareiss(a):
    """Bareiss con la misma secuencia que el ASM.

    Devuelve (det, pivotes, intercambios, ciclos_division)."""
    m = [fila[:] for fila in a]
    n = len(m)
    p = 1                # pivote anterior
    signo = 1
    pivotes = []
    intercambios = []
    ciclos_div = 0
    for k in range(n - 1):
        if m[k][k] == 0:
            r = next((r for r in range(k + 1, n) if m[r][k] != 0), None)
            if r is None:
                return 0, pivotes, intercambios, ciclos_div
            m[k], m[r] = m[r], m[k]
            signo = -signo
            intercambios.append((k + 1, r + 1))
        pivotes.append(m[k][k])
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                num = m[k][k] * m[i][j] - m[i][k] * m[k][j]
                assert num % p == 0, "division no exacta"
                q = abs(num) // abs(p)
                ciclos_div += q + 1
                m[i][j] = q if (num < 0) == (p < 0) else -q
                assert abs(m[i][j]) < 2 ** 31
        p = m[k][k]
    return signo * m[n - 1][n - 1], pivotes, intercambios, ciclos_div


def det_cofactores(a):
    """Determinante por cofactores (solo para validar el modelo)."""
    n = len(a)
    if n == 1:
        return a[0][0]
    return sum((-1) ** c * a[0][c] *
               det_cofactores([f[:c] + f[c + 1:] for f in a[1:]])
               for c in range(n))


def texto_display(valor):
    """Texto de 8 digitos que debe verse en la Nexys A7."""
    signo = '-' if valor < 0 else ' '
    mag = abs(valor) % 10 ** 7          # solo caben 7 digitos
    return signo + str(mag).zfill(7), abs(valor) > 9_999_999


def lineas_rom(pagina, a):
    """Lineas VHDL de la ROM (orden por columnas, como la Figura 1)."""
    n = len(a)
    base = 32 * pagina
    out = [f"      {base:3d} => conv_std_logic_vector({n:3d},6),  -- pagina {pagina}: n = {n}"]
    dir_ = 1
    for j in range(n):
        for i in range(n):
            out.append(f"      {base + dir_:3d} => conv_std_logic_vector({a[i][j]:3d},6),  -- a{i+1}{j+1}")
            dir_ += 1
    return out


if __name__ == "__main__":
    for pag, a in enumerate(MATRICES):
        n = len(a)
        assert all(a[i][j] == a[j][i] for i in range(n) for j in range(n)), "no simetrica"
        assert all(-32 <= x <= 31 for f in a for x in f), "fuera de rango"
        det, piv, inter, cdiv = bareiss(a)
        assert det == det_cofactores(a), "el modelo no coincide con cofactores"
        txt, desb = texto_display(det)
        print(f"Pagina {pag}: {n}x{n}  det = {det}  display = '{txt}'  desborde = {desb}")
        print(f"   pivotes = {piv}  intercambios = {inter}  ciclos de division ~ {cdiv}")
        for k, pv in enumerate(piv, start=1):
            print(f"   SW2..0 = {k}: display = '{texto_display(pv)[0]}'")
    print()
    print("-- Lineas para la ROM en VHDL:")
    for pag, a in enumerate(MATRICES):
        print("\n".join(lineas_rom(pag, a)))

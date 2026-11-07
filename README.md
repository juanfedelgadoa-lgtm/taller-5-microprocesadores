# Taller 5: determinante por Bareiss con salida BCD (XS3)

Microprocesador de propósito específico descrito con un diagrama ASM en VHDL
(ISE 14.7) para la Nexys A7-100T. Calcula el determinante de una matriz
simétrica de 2×2 a 5×5 por el algoritmo de Bareiss y lo muestra en los displays
después de convertirlo a BCD con el algoritmo XS3, que aparece paso a paso en el ASM.

| Archivo | Contenido |
|---|---|
| `doc/Taller5_ASM_Bareiss_XS3.pdf` | Explicación completa: Bareiss, XS3, caja negra y gris, pseudocódigo, diagrama ASM (S0 a S26), señales, camino de datos, uso en la tarjeta y simulación |
| `src/det_bareiss.vhd` | Diseño completo en un solo archivo (ROM, RAM, banco de pivotes, multiplicador, sumador/restador, división por restas sucesivas, XS3, display) |
| `src/nexys_a7.ucf` | Pines y reloj de 100 MHz |
| `sim/tb_det_bareiss.vhd` | Testbench: 8 matrices de prueba, compara el display con los valores esperados |
| `sim/modelo_referencia.py` | Valores esperados (det y pivotes) y generador de líneas de ROM |
| `sim/resultado_ghdl.txt` | Resultado de la simulación completa |
| `doc/figuras/` | Diagramas ASM y de bloques en PNG |
| `doc/fuentes/` | Scripts que generan las figuras y el PDF |

## Uso en ISE 14.7

1. Proyecto nuevo: Artix7, XC7A100T, CSG324, velocidad −1, XST, ISim, VHDL.
2. Agregar `src/det_bareiss.vhd` y `src/nexys_a7.ucf`; agregar `sim/tb_det_bareiss.vhd` solo para simulación.
3. Sintetizar, implementar y generar el `.bit`. Revisar que se cumpla la restricción de 10 ns.

## Uso en la tarjeta

- BTNU = reset, BTNC = inicio.
- SW15..SW13 elige la matriz de prueba (0 a 7).
- SW2..SW0 = 000 muestra el determinante; 001 a 100 muestran los pivotes 1 a 4.
- LD0 = final. LD1 = el valor tiene más de 7 dígitos.
- Display: AN7 = signo, AN6..AN0 = 7 dígitos.

## Simulación con GHDL (opcional)

```
ghdl -a -fsynopsys -fexplicit src/det_bareiss.vhd sim/tb_det_bareiss.vhd
ghdl -e -fsynopsys -fexplicit tb_det_bareiss
ghdl -r -fsynopsys -fexplicit tb_det_bareiss               # matrices 0 a 6
ghdl -r -fsynopsys -fexplicit tb_det_bareiss -gMAX_MATRIZ=7 # incluye la 5x5 extrema (lento)
```

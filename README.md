# Taller 5: determinante por Bareiss con salida BCD (XS3)

Microprocesador de propósito específico en VHDL (ISE 14.7) para la Nexys A7-100T.
Calcula el determinante de una matriz simétrica de 2×2 a 5×5 por el algoritmo de
Bareiss y lo muestra en los displays después de convertirlo a BCD con el algoritmo
XS3, que aparece paso a paso en el ASM.

El diseño es RTL: una unidad de control (FSM de 27 estados) separada del camino de
datos (registros, multiplexores, ROM, RAM, multiplicador y sumador/restador). Usa
solo señales `std_logic` y `std_logic_vector`, sin variables. La única excepción es
el arreglo de la RAM, que es la forma de describir una memoria para que XST la infiera.

| Archivo | Contenido |
|---|---|
| `doc/Taller5_ASM_Bareiss_XS3.pdf` | Explicación completa: Bareiss, XS3, caja negra y gris, jerarquía, pseudocódigo, diagrama ASM (S0 a S26), palabra de control por estado, señales, camino de datos, uso en la tarjeta y simulación |
| `src/det_bareiss.vhd` | Diseño completo en un solo archivo (10 entidades) |
| `src/nexys_a7.ucf` | Pines y reloj de 100 MHz |
| `sim/tb_procesador.vhd` | Testbench de la unidad de control + camino de datos: 8 matrices y sus pivotes |
| `sim/tb_det_bareiss.vhd` | Testbench del tope: lee el display de 7 segmentos |
| `sim/modelo_referencia.py` | Valores esperados (det y pivotes) y generador de líneas de ROM |
| `sim/resultado_ghdl.txt` | Resultado de las simulaciones |
| `doc/figuras/` | Diagramas ASM y de bloques en PNG |
| `doc/fuentes/` | Scripts que generan las figuras y el PDF |

## Jerarquía

```
det_bareiss (tope, estructural)
 ├─ sincronizador
 ├─ procesador (estructural)
 │   ├─ unidad_control   (FSM)
 │   └─ camino_datos
 │       ├─ rom_matrices
 │       ├─ ram_trabajo
 │       ├─ multiplicador
 │       └─ sumador_restador
 └─ display_8dig
```

## Uso en ISE 14.7

1. Proyecto nuevo: Artix7, XC7A100T, CSG324, velocidad −1, XST, ISim, VHDL.
2. Agregar `src/det_bareiss.vhd` y `src/nexys_a7.ucf`; agregar los dos testbench de `sim/` solo para simulación.
3. Sintetizar (View RTL Schematic muestra la jerarquía), implementar y generar el `.bit`. Revisar que se cumpla la restricción de 10 ns.

## Uso en la tarjeta

- BTNU = reset, BTNC = inicio.
- SW15..SW13 elige la matriz de prueba (0 a 7).
- SW2..SW0 = 000 muestra el determinante; 001 a 100 muestran los pivotes 1 a 4.
- LD0 = final. LD1 = el valor tiene más de 7 dígitos.
- Display: AN7 = signo, AN6..AN0 = 7 dígitos.

## Simulación con GHDL (opcional)

```
ghdl -a -fsynopsys -fexplicit src/det_bareiss.vhd sim/tb_procesador.vhd sim/tb_det_bareiss.vhd
ghdl -e -fsynopsys -fexplicit tb_procesador
ghdl -r -fsynopsys -fexplicit tb_procesador                 # matrices 0 a 6
ghdl -r -fsynopsys -fexplicit tb_procesador -gMAX_MATRIZ=7  # incluye la 5x5 extrema (lento)
ghdl -e -fsynopsys -fexplicit tb_det_bareiss
ghdl -r -fsynopsys -fexplicit tb_det_bareiss                # display de 7 segmentos
```

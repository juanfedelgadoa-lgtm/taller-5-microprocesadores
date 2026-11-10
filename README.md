# Taller 5: determinante por Bareiss con salida BCD (XS3)

Microprocesador de propósito específico descrito con un diagrama ASM en VHDL
(ISE 14.7) para la Nexys A7-100T. Calcula el determinante de una matriz
simétrica de 2×2 a 5×5 por el algoritmo de Bareiss y convierte el determinante
y el pivote elegido a BCD con el algoritmo XS3, que aparece paso a paso en el ASM.

El ASM (28 estados, s0 a s27) está en un solo proceso con `case st is`, como los
ejemplos de clase. Solo se usan señales `std_logic` y `std_logic_vector`; la
única excepción es la RAM (arreglo de `std_logic_vector`).

## Caja negra (entidad `asm_bareiss`)

Como en los apuntes del profesor, la ROM está fuera del bloque:

```
           +----------------------+
    clk -->|                      |--> det (BCD), det_neg
    rst -->|  Algoritmo Bareiss   |--> pivote (BCD), piv_neg
 inicio -->|       + XS3          |--> final
  dir_p -->|                      |--> dira --> ROM
      a -->|                      |
           +----------------------+
```

| Archivo | Contenido |
|---|---|
| `doc/Taller5_ASM_Bareiss_XS3.pdf` | Explicación completa: Bareiss, XS3, caja negra y gris, pseudocódigo, diagrama ASM (s0 a s27), señales, camino de datos, uso en la tarjeta y simulación |
| `src/det_bareiss.vhd` | Diseño completo: ROM, RAM, multiplicador, sumador/restador, ASM, sincronizador, display y tope |
| `src/nexys_a7.ucf` | Pines y reloj de 100 MHz |
| `sim/tb_asm_bareiss.vhd` | Testbench del ASM con la ROM externa: 8 matrices y sus pivotes |
| `sim/tb_det_bareiss.vhd` | Testbench del tope: lee el display de 7 segmentos |
| `sim/modelo_referencia.py` | Valores esperados (det y pivotes) y generador de líneas de ROM |
| `sim/resultado_ghdl.txt` | Resultado de las simulaciones |
| `doc/figuras/`, `doc/fuentes/` | Diagramas y scripts que generan las figuras y el PDF |

## Uso en ISE 14.7

1. Proyecto nuevo: Artix7, XC7A100T, CSG324, velocidad −1, XST, ISim, VHDL.
2. Agregar `src/det_bareiss.vhd` y `src/nexys_a7.ucf`; agregar los dos testbench de `sim/` solo para simulación.
3. Sintetizar, implementar y generar el `.bit`. Revisar que se cumpla la restricción de 10 ns.

## Uso en la tarjeta

- BTNU = reset, BTNC = inicio.
- SW15..SW13 elige la matriz de prueba (0 a 7).
- SW2..SW0 = dir_p: pivote 1 a 4.
- SW3 = 0 muestra el determinante; SW3 = 1 muestra el pivote.
- LD0 = final. LD1 = el valor mostrado tiene más de 7 dígitos.
- Display: AN7 = signo, AN6..AN0 = 7 dígitos.

## Simulación con GHDL (opcional)

```
ghdl -a -fsynopsys -fexplicit src/det_bareiss.vhd sim/tb_asm_bareiss.vhd sim/tb_det_bareiss.vhd
ghdl -e -fsynopsys -fexplicit tb_asm_bareiss
ghdl -r -fsynopsys -fexplicit tb_asm_bareiss                 # matrices 0 a 6
ghdl -r -fsynopsys -fexplicit tb_asm_bareiss -gMAX_MATRIZ=7  # incluye la 5x5 extrema (lento)
ghdl -e -fsynopsys -fexplicit tb_det_bareiss
ghdl -r -fsynopsys -fexplicit tb_det_bareiss                 # display de 7 segmentos
```

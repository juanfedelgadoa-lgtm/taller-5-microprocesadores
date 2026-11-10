# Taller 5: determinante por Bareiss con salida BCD (XS3)

Microprocesador de propósito específico en VHDL (ISE 14.7) para la Nexys A7-100T.
Calcula el determinante de la matriz guardada en su ROM (de 2×2 a 5×5) con el
algoritmo de Bareiss, guarda los pivotes en un banco de registros y entrega el
determinante y el pivote elegido en BCD, convertidos con el algoritmo XS3.

El diseño es un procesador estructural: un ASM de alto nivel (`case st is`,
27 estados) maneja bloques separados (ROM, RAM, multiplicador, ALU y banco de
pivotes). La división por restas sucesivas y el algoritmo XS3 están integrados
en ese ASM, y todas sus sumas y restas pasan por la única ALU, que sigue la
tabla del curso (M, s1, s0). Solo se usan `std_logic` y `std_logic_vector`; la
única excepción es la RAM, que sigue el modelo del curso. Hay un solo
antirrebote, para el botón de inicio.

**Documento completo** (caja negra, cajas grises, ALU, pseudoalgoritmo, diagrama
ASM, señales, simulación y código): [`doc/Taller5_ASM_Bareiss_XS3.pdf`](doc/Taller5_ASM_Bareiss_XS3.pdf).
Las figuras sueltas están en [`doc/figuras/`](doc/figuras).

## Caja negra del procesador

```
          +---------------------------+
   clk -->|                           |--> det    (BCD) + det_neg
   rst -->|        PROCESADOR         |--> pivote (BCD) + piv_neg
inicio -->|  (ROM, RAM, multiplicador |--> final
 dir_p -->|    y ALU internos)        |
          +---------------------------+
```

`dir_p` = 1..n elige el pivote; el pivote n es el determinante.

## ALU

| M | s1 | s0 | Operación | Uso |
|---|---|---|---|---|
| 0 | 0 | 0 | not B | — |
| 0 | 0 | 1 | A and B | — |
| 0 | 1 | 0 | A or B | — |
| 0 | 1 | 1 | A xnor B | — |
| 1 | 0 | 0 | A + 1 | — |
| 1 | 0 | 1 | A + B | +3 del XS3 |
| 1 | 1 | 0 | A − B | t1 − t2, división, valores absolutos |
| 1 | 1 | 1 | A − 1 | — |

## Archivos

| Archivo | Contenido |
|---|---|
| `src/det_bareiss.vhd` | Tope para la tarjeta (estructural) |
| `src/procesador.vhd` | Procesador: ASM + bloques (estructural) |
| `src/asm_bareiss.vhd` | ASM de Bareiss con la división y el XS3 integrados (s0 a s26) |
| `src/alu.vhd` | ALU con la tabla del curso |
| `src/multiplicador.vhd` | Multiplicador con signo 25 × 25 → 50 |
| `src/rom_matriz.vhd` | ROM con la matriz (se cambia para cada evaluación) |
| `src/ram.vhd` | RAM (modelo del curso, 64 × 32) |
| `src/banco_pivotes.vhd` | Banco de 5 registros de pivotes |
| `src/divisor_frecuencia.vhd` | Tick de 1 ms y onda de 1 s |
| `src/antirrebote.vhd` | Antirrebote del botón de inicio (el único del diseño) |
| `src/sincronizador.vhd`, `src/display_8dig.vhd` | Switches y display |
| `src/nexys_a7.ucf` | Pines y reloj de 100 MHz |
| `sim/tb_alu.vhd` | Testbench de las 8 operaciones de la ALU |
| `sim/tb_procesador.vhd`, `sim/pkg_prueba.vhd` | Testbench autoverificado (sirve para cualquier ROM) |
| `sim/tb_det_bareiss.vhd` | Testbench de la tarjeta (botón con rebotes, display) |
| `sim/modelo_referencia.py` | Valores esperados y generador de la ROM |
| `sim/probar_matrices.py`, `sim/resultado_ghdl.txt` | Prueba con 8 matrices y resultados |

## Cambiar la matriz

```
python3 sim/modelo_referencia.py rom "2 1 3; 1 4 2; 3 2 5"   # escribe src/rom_matriz.vhd
```

O editar `src/rom_matriz.vhd` a mano: 00h = n, luego a11, a21, …, an1, a12, … en
complemento a 2 de 6 bits. Después simular con `sim/tb_procesador.vhd`, sintetizar
y volver a programar la FPGA.

## Uso en ISE 14.7

1. Proyecto nuevo: Artix7, XC7A100T, CSG324, velocidad −1, XST, ISim, VHDL.
2. Agregar todos los `.vhd` de `src/` y `src/nexys_a7.ucf`; agregar `sim/pkg_prueba.vhd` y los testbench solo para simulación.
3. Sintetizar, implementar y generar el `.bit`. Revisar que se cumpla la restricción de 10 ns.

## Uso en la tarjeta

- BTNU = reset, BTNC = inicio.
- SW2..SW0 (`dir_p`) = 000 muestra el determinante; 001 a 101 muestran el pivote k.
- LD0 = final. LD1 = el valor mostrado tiene más de 7 dígitos. LD15 = onda de 1 s.
- Display: AN7 = signo, AN6..AN0 = 7 dígitos.

## Simulación con GHDL (opcional)

```
GHDL=ghdl python3 sim/probar_matrices.py           # matrices 0 a 6
GHDL=ghdl python3 sim/probar_matrices.py --todas   # incluye la 5x5 extrema (lento)
```

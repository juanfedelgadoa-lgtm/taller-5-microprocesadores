# Taller 5: determinante por Bareiss con salida decimal (XS3)

Microprocesador de propósito específico en VHDL (ISE 14.7) para la Nexys A7-100T.
Calcula el determinante de la matriz guardada en su ROM (de 2×2 a 5×5) con el
algoritmo de Bareiss, guarda los pivotes en un banco de registros y muestra en
decimal el determinante o el pivote elegido con los switches.

El diseño tiene cuatro bloques:

| Bloque | Archivo | Contenido |
|---|---|---|
| Antirrebote | `src/antirrebote.vhd` | El único antirrebote, para el botón de inicio |
| Divisor de frecuencia | `src/divisor_frecuencia.vhd` | Pulso de 1 ms y onda de 1 s (reloj de 100 MHz) |
| Procesador de Bareiss | `src/procesador_bareiss.vhd` | ASM de Bareiss (19 estados), ROM, dos RAM del modelo del profesor, banco de pivotes y las dos únicas unidades funcionales: multiplicador y sumador/restador. No hay ALU. |
| Visualizador | `src/visualizador.vhd` | ASM del XS3 (6 estados, uno por paso) y display de 8 dígitos, en el mismo archivo. Trabaja en paralelo con el procesador y tiene sus propias unidades. |

`src/det_bareiss.vhd` es el tope para ISE: solo conecta los cuatro bloques
(ISE lo necesita para asignar los pines con `src/nexys_a7.ucf`).

Solo se usan `std_logic` y `std_logic_vector`. Las excepciones salen de los
ejemplos del curso: la RAM es el modelo del profesor sin cambios (32 × 32) y los
estados de cada ASM se declaran como en `ASM_Sumax` y `ASM_contador_unos`:

```vhdl
type estados_asm is (s0,s1,s2, ... ,s18);
signal st : estados_asm;
```

**Documento completo** (pseudoalgoritmo, cajas negras, diagramas ASM con la
verificación de sus reglas, simulación y código):
[`doc/Taller5_ASM_Bareiss_XS3.pdf`](doc/Taller5_ASM_Bareiss_XS3.pdf).

Las secciones 9 a 11 del documento siguen el procedimiento de la guía del curso
para pasar del ASM al hardware y dicen qué debe aparecer en la síntesis de ISE:

- **Camino de datos**: 19 registros con sus MUX y cargas, multiplicador,
  sumador/restador, ROM, RAM A y RAM B, banco de pivotes y 9 señales de estado.
- **Palabra de control**: 55 bits (visualizador: 12).
- **Unidad de control** (Mealy, 19 estados, 5 flip-flops): ROM de entrada
  2048 × 5 y ROM de salida 8192 × 56, con el contenido de las dos ROM
  (visualizador: 64 × 3 y 256 × 12).
- **Comprobación**: `doc/fuentes/uc_cd.py` simula ese CD y esa UC ciclo a ciclo y
  da los mismos resultados y ciclos que el VHDL en las 8 matrices
  (`sim/resultado_modelo_uc_cd.txt`).
- **Síntesis esperada**: 2 FSM (19 y 6 estados), 2 RAM distribuidas de 32 × 32,
  1 multiplicador 25 × 25 (2 DSP48E1), unos 770 flip-flops y 1 000 LUT
  (estimación con Yosys en `sim/estimacion_yosys.txt`; ISE dará valores parecidos).
Las figuras sueltas están en [`doc/figuras/`](doc/figuras).

## Cajas negras

```
             +----------------------+
      clk -->|                      |--> det    (32, binario)
      rst -->|  PROCESADOR BAREISS  |--> pivote (32, binario)
   inicio -->| ROM, RAM A, RAM B,   |--> final
dir_p (3) -->| ×, +/-               |
             +----------------------+

             +----------------------+
 clk, rst -->|                      |--> an (8)
     tick -->|    VISUALIZADOR      |--> seg (7), dp
    final -->|  ASM XS3 + display   |--> desborde
dir_p (3) -->|                      |
 det (32) -->|                      |
piv. (32) -->|                      |
             +----------------------+
```

`dir_p` = 0 muestra el determinante; `dir_p` = 1..n muestra el pivote k (el pivote n es el determinante).

## Funcionamiento en paralelo

Mientras el procesador calcula (`final` = 0) el ASM XS3 espera y el display
conserva el último valor. Cuando el procesador termina (`final` = 1), el ASM XS3
convierte una y otra vez el valor elegido con `dir_p` (376 ciclos por conversión),
así que el display sigue a los switches sin que el procesador espere.

## Cambiar la matriz

```
python3 sim/modelo_referencia.py rom "2 1 3; 1 4 2; 3 2 5"
```

cambia la ROM dentro de `src/procesador_bareiss.vhd` (entre las marcas
`>>> INICIO ROM` y `<<< FIN ROM`) e imprime el determinante y los pivotes
esperados. También se puede editar a mano: 00h = n, luego a11, a21, …, an1,
a12, … en complemento a 2 de 6 bits. Después simular con `sim/tb_procesador.vhd`,
sintetizar y volver a programar la FPGA.

## Uso en ISE 14.7

1. Proyecto nuevo: Artix7, XC7A100T, CSG324, velocidad −1, XST, ISim, VHDL.
2. Agregar los cinco `.vhd` de `src/` y `src/nexys_a7.ucf`; agregar `sim/pkg_prueba.vhd` y los testbench solo para simulación.
3. Sintetizar, implementar y generar el `.bit`. Revisar que se cumpla la restricción de 10 ns.

## Uso en la tarjeta

- BTNU = reset, BTNC = inicio.
- SW2..SW0 (`dir_p`) = 000 muestra el determinante; 001 a 101 muestran el pivote k.
- LD0 = final. LD1 = el valor mostrado tiene más de 7 dígitos. LD15 = onda de 1 s.
- Display: AN7 = signo, AN6..AN0 = 7 dígitos.

## Simulación

| Archivo | Prueba |
|---|---|
| `sim/tb_procesador.vhd`, `sim/pkg_prueba.vhd` | Procesador: det y todos los pivotes contra un modelo de Bareiss (sirve para cualquier ROM) |
| `sim/tb_visualizador.vhd` | XS3 y display con valores positivos, negativos, de 7 dígitos y con desborde |
| `sim/tb_det_bareiss.vhd` | Tarjeta completa: botón con rebotes y lectura del display |
| `sim/probar_matrices.py` | Corre `tb_procesador` con las 8 matrices de prueba |
| `sim/resultado_ghdl.txt` | Resultados (GHDL 4.1), pruebas de mutación y síntesis genérica |
| `doc/fuentes/uc_cd.py`, `sim/resultado_modelo_uc_cd.txt` | Tablas de la UC (ROM de entrada y de salida) y modelo ciclo a ciclo del CD |
| `sim/estimacion_yosys.txt` | Estimación de recursos en Artix-7 (referencia para comparar con ISE) |

```
GHDL=ghdl python3 sim/probar_matrices.py           # matrices 0 a 6
GHDL=ghdl python3 sim/probar_matrices.py --todas   # incluye la 5x5 extrema (unos 15 minutos)
```

`python3 doc/fuentes/diagramas.py --verificar` revisa las reglas de los
diagramas ASM y que sus transiciones coincidan con el VHDL.
`python3 doc/fuentes/uc_cd.py` revisa las tablas de la unidad de control y simula
el camino de datos con ellas (`--rapido` omite la matriz de 19 millones de ciclos).

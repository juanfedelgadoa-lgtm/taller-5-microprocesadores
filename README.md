# Taller 5: determinante por Bareiss con salida decimal (XS3)

Microprocesador de propósito específico en VHDL (ISE 14.7) para la Nexys A7-100T.
Calcula el determinante de la matriz guardada en su ROM (de 2×2 a 5×5) con el
algoritmo de Bareiss, guarda los pivotes en un banco de registros y muestra en
decimal el determinante o el pivote elegido con los switches.

El diseño tiene cuatro bloques:

| Bloque | Archivo | Contenido |
|---|---|---|
| Antirrebote | `src/antirrebote.vhd` | El único antirrebote, para el botón de inicio |
| Divisor de frecuencia | `src/divisor_frecuencia.vhd` | Pulso de 1 ms (reloj de 100 MHz) para el barrido del display |
| Procesador de Bareiss | `src/procesador_bareiss.vhd`, `src/RAM_memory.vhd` | ASM de Bareiss en alto nivel, como `ASM_Sumax` y `ASM_contador_unos`: un solo process con `case st is` (14 estados) y las operaciones escritas en cada estado. La ROM es un `with dira select` dentro de la arquitectura. Las dos RAM son el modelo del curso sin cambios (`RAM_memory.vhd`); son el único `port map` del procesador. El multiplicador siempre es `x * y` y el restador siempre es `r - s`, sobre los mismos registros, así la síntesis arma una sola unidad de cada una. La división es por restas sucesivas de p, sin valor absoluto. |
| Visualizador | `src/visualizador.vhd` | ASM del XS3 (6 estados, uno por paso) y display de 8 dígitos, en el mismo archivo. Trabaja en paralelo con el procesador y tiene sus propias unidades. |

`src/det_bareiss.vhd` es el tope para ISE: solo conecta los cuatro bloques
(ISE lo necesita para asignar los pines con `src/nexys_a7.ucf`).

Solo se usan `std_logic` y `std_logic_vector` (no hay tipos `signed`, `unsigned`
ni `integer`, ni funciones de conversión como `SXT` o `conv_integer`, fuera de la
RAM). Librerías:

- `std_logic_unsigned`: solo en `src/RAM_memory.vhd` (modelo del profesor).
- `std_logic_signed`: procesador, visualizador y divisor de frecuencia, porque los
  datos de la matriz son con signo (complemento a 2). Da `+`, `-`, `*` y las
  comparaciones sobre `std_logic_vector`.
- El antirrebote y el tope solo usan `std_logic_1164`.

Las excepciones de tipos salen del curso: el arreglo de la RAM es el del modelo
del profesor (32 × 32) y los estados de cada ASM se declaran como en `ASM_Sumax`
y `ASM_contador_unos`:

```vhdl
type estados_asm is (s0,s1,s2,s3,s4,s5,s6,s7,s8,s9,s10,s11,s12,s13);
signal st : estados_asm;
```

## Informe

**Informe de laboratorio:** [`informe/Informe_Taller5_Bareiss.pdf`](informe/Informe_Taller5_Bareiss.pdf)
(y la versión editable [`informe/Informe_Taller5_Bareiss.docx`](informe/Informe_Taller5_Bareiss.docx)).
Sigue la estructura del Informe6 del curso, con una descripción de alto nivel:
caja negra, análisis del algoritmo y del hardware disponible, pseudoalgoritmo por
bloques de colores, diagrama ASM completo (una sola figura), caja gris, unidad de
control, visualizador XS3, bloques auxiliares, VHDL, resultados de ISE en la
XC7A100T, simulaciones y conclusiones. Como no hay un camino de datos diseñado a
mano, del ASM salen las señales de estado y el tamaño del registro de estado y de
la ROM de entrada (2048 × 4), pero no la palabra de control: en las figuras queda
como "XX bits" (ROM de salida 16 384 × (XX + 1)).

- Figuras en draw.io: `informe/figuras/*.drawio` (se abren y se editan en
  [app.diagrams.net](https://app.diagrams.net)); al lado está el PNG de cada una.
  `asm_bareiss` es el ASM completo del procesador, `asm_xs3` el del visualizador
  y `pseudo_bareiss` / `pseudo_xs3` los pseudoalgoritmos.
- Faltan las capturas del esquema RTL de ISE: el informe tiene tres recuadros
  grises para pegarlas (Figuras 11 a 13: caja negra, caja gris y FSM).
- Los valores de ISE de la Tabla 7 están resaltados en amarillo: son de la
  síntesis anterior (con la salida de 1 s en LD15) y hay que actualizarlos al
  volver a sintetizar. También falta el ancho de la palabra de control de la FSM
  (`[completar]` en la sección de caja gris).
- Las ondas de las simulaciones se simularon con GHDL y se dibujaron con el
  formato de ISim. El testbench es `sim/tb_informe.vhd`; en ISim se corre 45 µs.

Cómo se regenera (las fuentes están en `informe/fuentes/`):

| Script | Hace |
|---|---|
| `uc_cd.py` | Comprobación interna (no va en el informe): tablas de transiciones de la UC y modelo ciclo a ciclo (`--rapido` omite la matriz 7) |
| `generar_figuras.py` | Revisa los ASM contra las transiciones de `uc_cd.py` y escribe los `.drawio` (y los PNG con el visor de draw.io) |
| `ondas.py` | Simula `sim/tb_informe.vhd` con GHDL para las matrices 1, 2 y 3 y dibuja `sim_*.png` |
| `generar_informe.py` | Arma el `.docx`; el PDF se saca con `soffice --headless --convert-to pdf` |

Resultados de ISE 14.7 (XC7A100T-1CSG324) de la síntesis anterior: 702
flip-flops, 878 LUT, 2 DSP48E1, 1 multiplicador 25 × 25, 1 restador de 50 bits,
FSM de 14 estados y 26 transiciones; restricción de 10 ns cumplida con 1,206 ns
de holgura. Al quitar la salida de 1 s cambian los flip-flops del divisor y queda
un IOB menos (24).

> La carpeta `doc/` es de una versión anterior del procesador (con el
> multiplicador y el sumador/restador como entidades) y ya no corresponde al
> VHDL de `src/`. Se puede borrar; el documento vigente es el de `informe/`.

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
`>>> INICIO ROM` y `<<< FIN ROM`) y la copia que leen los testbench
(`sim/rom_prueba.vhd`), e imprime el determinante y los pivotes esperados.
También se puede editar a mano: 00h = n, luego a11, a21, …, an1, a12, … en
complemento a 2 de 6 bits; en ese caso hay que copiar las mismas líneas en
`sim/rom_prueba.vhd`. Después simular con `sim/tb_procesador.vhd`,
sintetizar y volver a programar la FPGA.

## Uso en ISE 14.7

1. Proyecto nuevo: Artix7, XC7A100T, CSG324, velocidad −1, XST, ISim, VHDL.
2. Agregar los seis `.vhd` de `src/` y `src/nexys_a7.ucf`; agregar `sim/rom_prueba.vhd`, `sim/pkg_prueba.vhd` y los testbench solo para simulación.
3. Sintetizar, implementar y generar el `.bit`. Revisar que se cumpla la restricción de 10 ns.

## Uso en la tarjeta

- BTNU = reset, BTNC = inicio.
- SW2..SW0 (`dir_p`) = 000 muestra el determinante; 001 a 101 muestran el pivote k.
- LD0 = final. LD1 = el valor mostrado tiene más de 7 dígitos.
- Display: AN7 = signo, AN6..AN0 = 7 dígitos.

## Simulación

| Archivo | Prueba |
|---|---|
| `sim/tb_procesador.vhd`, `sim/pkg_prueba.vhd`, `sim/rom_prueba.vhd` | Procesador: det y todos los pivotes contra un modelo de Bareiss (lee la matriz de `sim/rom_prueba.vhd`) |
| `sim/tb_visualizador.vhd` | XS3 y display con valores positivos, negativos, de 7 dígitos y con desborde |
| `sim/tb_det_bareiss.vhd` | Tarjeta completa: botón con rebotes y lectura del display |
| `sim/tb_informe.vhd` | Testbench sencillo (sin comparaciones) para las figuras de simulación del informe |
| `sim/probar_matrices.py` | Corre `tb_procesador` con las 8 matrices de prueba |
| `sim/resultado_ghdl.txt` | Resultados (GHDL 4.1), pruebas de mutación y síntesis genérica |
| `informe/fuentes/uc_cd.py` | Comprobación interna: transiciones de la UC y modelo ciclo a ciclo |
| `sim/estimacion_yosys.txt` | Estimación de recursos en Artix-7 (referencia para comparar con ISE) |

```
GHDL=ghdl python3 sim/probar_matrices.py           # matrices 0 a 6
GHDL=ghdl python3 sim/probar_matrices.py --todas   # incluye la 5x5 extrema (unos 15 minutos)
```

`python3 informe/fuentes/generar_figuras.py --solo-xml` revisa que los diagramas
ASM lleguen al estado siguiente correcto en todas las combinaciones de señales.
`python3 informe/fuentes/uc_cd.py` revisa las tablas de transiciones con un modelo
ciclo a ciclo (`--rapido` omite la matriz de 19 millones de ciclos).

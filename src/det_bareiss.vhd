----------------------------------------------------------------------------------
-- Universidad Distrital Francisco Jose de Caldas
-- Analisis y Diseno de Microprocesadores - Taller 5
--
-- Microprocesador de proposito especifico descrito con un diagrama ASM
-- (modelo VHDL de alto nivel, como los ejemplos de clase):
--   * Determinante de una matriz simetrica de 2x2 a 5x5 por el algoritmo de
--     Bareiss (eliminacion libre de fracciones).
--   * Division por restas sucesivas.
--   * Conversion binario -> BCD con el algoritmo XS3 (sumar 3 y desplazar),
--     descrita paso a paso dentro del mismo ASM (estados s22 a s25).
--   * Banco de registros con los pivotes; se eligen con dir_p (switches).
--
-- Herramienta : Xilinx ISE 14.7 (XST / ISim)
-- Tarjeta     : Digilent Nexys A7-100T (XC7A100T-1CSG324C), reloj de 100 MHz
--
-- Reglas de descripcion:
--   * Solo senales de tipo std_logic y std_logic_vector: sin variables, sin
--     integer, sin signed/unsigned, sin tipos enumerados, sin genericos y sin
--     lazos for. Los estados del ASM son constantes std_logic_vector.
--   * Unica excepcion: la RAM, descrita como un arreglo de std_logic_vector
--     (es la forma en que XST infiere una memoria).
--   * El ASM completo esta en un solo proceso (entidad asm_bareiss), con
--     "case st is" y las operaciones de cada caja escritas en su estado.
--
-- Caja negra del procesador (entidad asm_bareiss), como en los apuntes:
--
--            +---------------------------+
--     clk -->|                           |--> det    (BCD) + det_neg
--     rst -->|    Algoritmo Bareiss      |--> pivote (BCD) + piv_neg
--  inicio -->|         + XS3             |--> final
--   dir_p -->|                           |--> dira ----+
--       a -->|                           |             |
--            +---------------------------+             v
--                   ^                          +---------------+
--                   +----------- a ------------|      ROM      |
--                                              +---------------+
--
-- Entidades de este archivo:
--   rom_matrices                       : ROM con las matrices (fuera del ASM)
--   ram_trabajo, multiplicador,
--   sumador_restador                   : bloques usados por el ASM
--   asm_bareiss                        : el diagrama ASM (s0 a s27)
--   sincronizador, display_8dig        : interfaz con la tarjeta
--   det_bareiss                        : tope para la Nexys A7
----------------------------------------------------------------------------------


----------------------------------------------------------------------------------
-- ROM DE MATRICES: 256 x 6 bits, lectura combinacional.
-- dir = pag(3) & dira(5). En cada pagina: 00h = n, luego los a(i,j) por columnas
-- (a11, a21, ..., an1, a12, ...), como en la Figura 1 del taller.
-- Datos en complemento a 2 (-32 a 31).
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity rom_matrices is
    Port ( dir : in  STD_LOGIC_VECTOR (7 downto 0);
           a   : out STD_LOGIC_VECTOR (5 downto 0));
end rom_matrices;

architecture Behavioral of rom_matrices is
begin
with dir select
    a <= "000010" when "00000000",   -- pag 0, 00h: n = 2
         "000111" when "00000001",   -- pag 0, 01h: a11 = 7
         "111101" when "00000010",   -- pag 0, 02h: a21 = -3
         "111101" when "00000011",   -- pag 0, 03h: a12 = -3
         "000101" when "00000100",   -- pag 0, 04h: a22 = 5
         "000011" when "00100000",   -- pag 1, 00h: n = 3
         "000010" when "00100001",   -- pag 1, 01h: a11 = 2
         "000001" when "00100010",   -- pag 1, 02h: a21 = 1
         "000011" when "00100011",   -- pag 1, 03h: a31 = 3
         "000001" when "00100100",   -- pag 1, 04h: a12 = 1
         "000100" when "00100101",   -- pag 1, 05h: a22 = 4
         "000010" when "00100110",   -- pag 1, 06h: a32 = 2
         "000011" when "00100111",   -- pag 1, 07h: a13 = 3
         "000010" when "00101000",   -- pag 1, 08h: a23 = 2
         "000101" when "00101001",   -- pag 1, 09h: a33 = 5
         "000100" when "01000000",   -- pag 2, 00h: n = 4
         "000000" when "01000001",   -- pag 2, 01h: a11 = 0
         "000010" when "01000010",   -- pag 2, 02h: a21 = 2
         "000001" when "01000011",   -- pag 2, 03h: a31 = 1
         "000011" when "01000100",   -- pag 2, 04h: a41 = 3
         "000010" when "01000101",   -- pag 2, 05h: a12 = 2
         "000001" when "01000110",   -- pag 2, 06h: a22 = 1
         "000000" when "01000111",   -- pag 2, 07h: a32 = 0
         "000001" when "01001000",   -- pag 2, 08h: a42 = 1
         "000001" when "01001001",   -- pag 2, 09h: a13 = 1
         "000000" when "01001010",   -- pag 2, 0Ah: a23 = 0
         "000011" when "01001011",   -- pag 2, 0Bh: a33 = 3
         "000010" when "01001100",   -- pag 2, 0Ch: a43 = 2
         "000011" when "01001101",   -- pag 2, 0Dh: a14 = 3
         "000001" when "01001110",   -- pag 2, 0Eh: a24 = 1
         "000010" when "01001111",   -- pag 2, 0Fh: a34 = 2
         "000100" when "01010000",   -- pag 2, 10h: a44 = 4
         "000101" when "01100000",   -- pag 3, 00h: n = 5
         "000100" when "01100001",   -- pag 3, 01h: a11 = 4
         "111110" when "01100010",   -- pag 3, 02h: a21 = -2
         "000001" when "01100011",   -- pag 3, 03h: a31 = 1
         "000011" when "01100100",   -- pag 3, 04h: a41 = 3
         "000000" when "01100101",   -- pag 3, 05h: a51 = 0
         "111110" when "01100110",   -- pag 3, 06h: a12 = -2
         "000110" when "01100111",   -- pag 3, 07h: a22 = 6
         "000010" when "01101000",   -- pag 3, 08h: a32 = 2
         "111111" when "01101001",   -- pag 3, 09h: a42 = -1
         "000101" when "01101010",   -- pag 3, 0Ah: a52 = 5
         "000001" when "01101011",   -- pag 3, 0Bh: a13 = 1
         "000010" when "01101100",   -- pag 3, 0Ch: a23 = 2
         "111001" when "01101101",   -- pag 3, 0Dh: a33 = -7
         "000100" when "01101110",   -- pag 3, 0Eh: a43 = 4
         "000010" when "01101111",   -- pag 3, 0Fh: a53 = 2
         "000011" when "01110000",   -- pag 3, 10h: a14 = 3
         "111111" when "01110001",   -- pag 3, 11h: a24 = -1
         "000100" when "01110010",   -- pag 3, 12h: a34 = 4
         "000101" when "01110011",   -- pag 3, 13h: a44 = 5
         "111101" when "01110100",   -- pag 3, 14h: a54 = -3
         "000000" when "01110101",   -- pag 3, 15h: a15 = 0
         "000101" when "01110110",   -- pag 3, 16h: a25 = 5
         "000010" when "01110111",   -- pag 3, 17h: a35 = 2
         "111101" when "01111000",   -- pag 3, 18h: a45 = -3
         "001000" when "01111001",   -- pag 3, 19h: a55 = 8
         "000011" when "10000000",   -- pag 4, 00h: n = 3
         "111110" when "10000001",   -- pag 4, 01h: a11 = -2
         "000100" when "10000010",   -- pag 4, 02h: a21 = 4
         "000001" when "10000011",   -- pag 4, 03h: a31 = 1
         "000100" when "10000100",   -- pag 4, 04h: a12 = 4
         "111000" when "10000101",   -- pag 4, 05h: a22 = -8
         "000011" when "10000110",   -- pag 4, 06h: a32 = 3
         "000001" when "10000111",   -- pag 4, 07h: a13 = 1
         "000011" when "10001000",   -- pag 4, 08h: a23 = 3
         "000101" when "10001001",   -- pag 4, 09h: a33 = 5
         "000100" when "10100000",   -- pag 5, 00h: n = 4
         "000001" when "10100001",   -- pag 5, 01h: a11 = 1
         "000010" when "10100010",   -- pag 5, 02h: a21 = 2
         "000011" when "10100011",   -- pag 5, 03h: a31 = 3
         "000000" when "10100100",   -- pag 5, 04h: a41 = 0
         "000010" when "10100101",   -- pag 5, 05h: a12 = 2
         "000100" when "10100110",   -- pag 5, 06h: a22 = 4
         "000001" when "10100111",   -- pag 5, 07h: a32 = 1
         "000101" when "10101000",   -- pag 5, 08h: a42 = 5
         "000011" when "10101001",   -- pag 5, 09h: a13 = 3
         "000001" when "10101010",   -- pag 5, 0Ah: a23 = 1
         "111110" when "10101011",   -- pag 5, 0Bh: a33 = -2
         "000100" when "10101100",   -- pag 5, 0Ch: a43 = 4
         "000000" when "10101101",   -- pag 5, 0Dh: a14 = 0
         "000101" when "10101110",   -- pag 5, 0Eh: a24 = 5
         "000100" when "10101111",   -- pag 5, 0Fh: a34 = 4
         "111101" when "10110000",   -- pag 5, 10h: a44 = -3
         "000101" when "11000000",   -- pag 6, 00h: n = 5
         "000000" when "11000001",   -- pag 6, 01h: a11 = 0
         "000000" when "11000010",   -- pag 6, 02h: a21 = 0
         "000000" when "11000011",   -- pag 6, 03h: a31 = 0
         "000000" when "11000100",   -- pag 6, 04h: a41 = 0
         "000000" when "11000101",   -- pag 6, 05h: a51 = 0
         "000000" when "11000110",   -- pag 6, 06h: a12 = 0
         "000011" when "11000111",   -- pag 6, 07h: a22 = 3
         "000001" when "11001000",   -- pag 6, 08h: a32 = 1
         "000010" when "11001001",   -- pag 6, 09h: a42 = 2
         "000100" when "11001010",   -- pag 6, 0Ah: a52 = 4
         "000000" when "11001011",   -- pag 6, 0Bh: a13 = 0
         "000001" when "11001100",   -- pag 6, 0Ch: a23 = 1
         "000101" when "11001101",   -- pag 6, 0Dh: a33 = 5
         "111110" when "11001110",   -- pag 6, 0Eh: a43 = -2
         "000001" when "11001111",   -- pag 6, 0Fh: a53 = 1
         "000000" when "11010000",   -- pag 6, 10h: a14 = 0
         "000010" when "11010001",   -- pag 6, 11h: a24 = 2
         "111110" when "11010010",   -- pag 6, 12h: a34 = -2
         "000110" when "11010011",   -- pag 6, 13h: a44 = 6
         "000011" when "11010100",   -- pag 6, 14h: a54 = 3
         "000000" when "11010101",   -- pag 6, 15h: a15 = 0
         "000100" when "11010110",   -- pag 6, 16h: a25 = 4
         "000001" when "11010111",   -- pag 6, 17h: a35 = 1
         "000011" when "11011000",   -- pag 6, 18h: a45 = 3
         "000111" when "11011001",   -- pag 6, 19h: a55 = 7
         "000101" when "11100000",   -- pag 7, 00h: n = 5
         "011110" when "11100001",   -- pag 7, 01h: a11 = 30
         "011011" when "11100010",   -- pag 7, 02h: a21 = 27
         "011000" when "11100011",   -- pag 7, 03h: a31 = 24
         "100011" when "11100100",   -- pag 7, 04h: a41 = -29
         "100001" when "11100101",   -- pag 7, 05h: a51 = -31
         "011011" when "11100110",   -- pag 7, 06h: a12 = 27
         "101011" when "11100111",   -- pag 7, 07h: a22 = -21
         "011100" when "11101000",   -- pag 7, 08h: a32 = 28
         "011101" when "11101001",   -- pag 7, 09h: a42 = 29
         "101000" when "11101010",   -- pag 7, 0Ah: a52 = -24
         "011000" when "11101011",   -- pag 7, 0Bh: a13 = 24
         "011100" when "11101100",   -- pag 7, 0Ch: a23 = 28
         "000010" when "11101101",   -- pag 7, 0Dh: a33 = 2
         "100100" when "11101110",   -- pag 7, 0Eh: a43 = -28
         "100100" when "11101111",   -- pag 7, 0Fh: a53 = -28
         "100011" when "11110000",   -- pag 7, 10h: a14 = -29
         "011101" when "11110001",   -- pag 7, 11h: a24 = 29
         "100100" when "11110010",   -- pag 7, 12h: a34 = -28
         "100101" when "11110011",   -- pag 7, 13h: a44 = -27
         "011100" when "11110100",   -- pag 7, 14h: a54 = 28
         "100001" when "11110101",   -- pag 7, 15h: a15 = -31
         "101000" when "11110110",   -- pag 7, 16h: a25 = -24
         "100100" when "11110111",   -- pag 7, 17h: a35 = -28
         "011100" when "11111000",   -- pag 7, 18h: a45 = 28
         "100010" when "11111001",   -- pag 7, 19h: a55 = -30
         "000000" when others;
end Behavioral;


----------------------------------------------------------------------------------
-- RAM DE TRABAJO: 64 x 32 bits. Escritura sincrona, lectura asincrona.
-- dir = fila(3) & columna(3).
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity ram_trabajo is
    Port ( clk  : in  STD_LOGIC;
           we   : in  STD_LOGIC;
           dir  : in  STD_LOGIC_VECTOR (5 downto 0);
           din  : in  STD_LOGIC_VECTOR (31 downto 0);
           dout : out STD_LOGIC_VECTOR (31 downto 0));
end ram_trabajo;

architecture Behavioral of ram_trabajo is
type ram_tipo is array (0 to 63) of std_logic_vector (31 downto 0);
signal ram : ram_tipo := (others => (others => '0'));
begin

process (clk)
begin
    if clk'event and clk = '1' then
        if we = '1' then
            ram(conv_integer(dir)) <= din;
        end if;
    end if;
end process;

dout <= ram(conv_integer(dir));

end Behavioral;


----------------------------------------------------------------------------------
-- MULTIPLICADOR CON SIGNO 25 x 25 -> 50 bits (combinacional).
-- std_logic_signed interpreta los std_logic_vector en complemento a 2.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_signed.all;

entity multiplicador is
    Port ( a : in  STD_LOGIC_VECTOR (24 downto 0);
           b : in  STD_LOGIC_VECTOR (24 downto 0);
           p : out STD_LOGIC_VECTOR (49 downto 0));
end multiplicador;

architecture Behavioral of multiplicador is
begin
p <= a * b;
end Behavioral;


----------------------------------------------------------------------------------
-- SUMADOR/RESTADOR DE 50 bits (combinacional).
-- op = '0': s = a + b      op = '1': s = a + not(b) + 1 = a - b
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity sumador_restador is
    Port ( a  : in  STD_LOGIC_VECTOR (49 downto 0);
           b  : in  STD_LOGIC_VECTOR (49 downto 0);
           op : in  STD_LOGIC;
           s  : out STD_LOGIC_VECTOR (49 downto 0));
end sumador_restador;

architecture Behavioral of sumador_restador is
signal bx : STD_LOGIC_VECTOR (49 downto 0);
begin
bx <= not b when op = '1' else b;
s  <= a + bx + op;
end Behavioral;


----------------------------------------------------------------------------------
-- ASM DEL PROCESADOR: Bareiss + division por restas sucesivas + XS3
-- El proceso del final es el diagrama ASM: un "when" por estado (s0 a s27),
-- las cajas de decision son "if" y las cajas de salida condicional son las
-- asignaciones dentro del "if".
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity asm_bareiss is
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);   -- direccion del banco de pivotes (1..4)
           a        : in  STD_LOGIC_VECTOR (5 downto 0);   -- dato de la ROM
           dira     : out STD_LOGIC_VECTOR (4 downto 0);   -- direccion de la ROM
           det      : out STD_LOGIC_VECTOR (39 downto 0);  -- |det| en BCD (10 digitos)
           det_neg  : out STD_LOGIC;                       -- signo del determinante
           pivote   : out STD_LOGIC_VECTOR (39 downto 0);  -- |pivote(dir_p)| en BCD
           piv_neg  : out STD_LOGIC;                       -- signo del pivote
           final    : out STD_LOGIC);
end asm_bareiss;

architecture Behavioral of asm_bareiss is

component ram_trabajo
    Port ( clk  : in  STD_LOGIC;
           we   : in  STD_LOGIC;
           dir  : in  STD_LOGIC_VECTOR (5 downto 0);
           din  : in  STD_LOGIC_VECTOR (31 downto 0);
           dout : out STD_LOGIC_VECTOR (31 downto 0));
end component;

component multiplicador
    Port ( a : in  STD_LOGIC_VECTOR (24 downto 0);
           b : in  STD_LOGIC_VECTOR (24 downto 0);
           p : out STD_LOGIC_VECTOR (49 downto 0));
end component;

component sumador_restador
    Port ( a  : in  STD_LOGIC_VECTOR (49 downto 0);
           b  : in  STD_LOGIC_VECTOR (49 downto 0);
           op : in  STD_LOGIC;
           s  : out STD_LOGIC_VECTOR (49 downto 0));
end component;

------------------------------------------------------------------------------
-- Estados del ASM (constantes std_logic_vector)
------------------------------------------------------------------------------
-- s0        espera de inicio
-- s1..s2    lectura de n y copia de la matriz ROM -> RAM
-- s3        inicializacion de Bareiss
-- s4..s10   pivote: lectura, busqueda de fila, intercambio, banco de pivotes
-- s11..s18  actualizacion de a(i,j): multiplicaciones, resta y division
-- s19       actualizacion del pivote anterior p y avance de k
-- s20       det = (+/-) a(n,n)
-- s21       valor a convertir: det (1a pasada) o pivote(dir_p) (2a pasada)
-- s22..s25  algoritmo XS3 (pasos 1 a 5)
-- s26       guarda el BCD en det o en pivote
-- s27       final = 1
constant s0  : STD_LOGIC_VECTOR (4 downto 0) := "00000";
constant s1  : STD_LOGIC_VECTOR (4 downto 0) := "00001";
constant s2  : STD_LOGIC_VECTOR (4 downto 0) := "00010";
constant s3  : STD_LOGIC_VECTOR (4 downto 0) := "00011";
constant s4  : STD_LOGIC_VECTOR (4 downto 0) := "00100";
constant s5  : STD_LOGIC_VECTOR (4 downto 0) := "00101";
constant s6  : STD_LOGIC_VECTOR (4 downto 0) := "00110";
constant s7  : STD_LOGIC_VECTOR (4 downto 0) := "00111";
constant s8  : STD_LOGIC_VECTOR (4 downto 0) := "01000";
constant s9  : STD_LOGIC_VECTOR (4 downto 0) := "01001";
constant s10 : STD_LOGIC_VECTOR (4 downto 0) := "01010";
constant s11 : STD_LOGIC_VECTOR (4 downto 0) := "01011";
constant s12 : STD_LOGIC_VECTOR (4 downto 0) := "01100";
constant s13 : STD_LOGIC_VECTOR (4 downto 0) := "01101";
constant s14 : STD_LOGIC_VECTOR (4 downto 0) := "01110";
constant s15 : STD_LOGIC_VECTOR (4 downto 0) := "01111";
constant s16 : STD_LOGIC_VECTOR (4 downto 0) := "10000";
constant s17 : STD_LOGIC_VECTOR (4 downto 0) := "10001";
constant s18 : STD_LOGIC_VECTOR (4 downto 0) := "10010";
constant s19 : STD_LOGIC_VECTOR (4 downto 0) := "10011";
constant s20 : STD_LOGIC_VECTOR (4 downto 0) := "10100";
constant s21 : STD_LOGIC_VECTOR (4 downto 0) := "10101";
constant s22 : STD_LOGIC_VECTOR (4 downto 0) := "10110";
constant s23 : STD_LOGIC_VECTOR (4 downto 0) := "10111";
constant s24 : STD_LOGIC_VECTOR (4 downto 0) := "11000";
constant s25 : STD_LOGIC_VECTOR (4 downto 0) := "11001";
constant s26 : STD_LOGIC_VECTOR (4 downto 0) := "11010";
constant s27 : STD_LOGIC_VECTOR (4 downto 0) := "11011";

signal st : STD_LOGIC_VECTOR (4 downto 0);

------------------------------------------------------------------------------
-- Constantes
------------------------------------------------------------------------------
constant CERO18 : STD_LOGIC_VECTOR (17 downto 0) := "000000000000000000";
constant CERO32 : STD_LOGIC_VECTOR (31 downto 0) := x"00000000";
constant UNO32  : STD_LOGIC_VECTOR (31 downto 0) := x"00000001";
constant CERO40 : STD_LOGIC_VECTOR (39 downto 0) := x"0000000000";
constant CERO46 : STD_LOGIC_VECTOR (45 downto 0) := (others => '0');
constant CERO50 : STD_LOGIC_VECTOR (49 downto 0) := (others => '0');
constant TRES50 : STD_LOGIC_VECTOR (49 downto 0) := (1 downto 0 => '1', others => '0');

------------------------------------------------------------------------------
-- ROM (externa) y RAM
------------------------------------------------------------------------------
signal dira_r   : STD_LOGIC_VECTOR (4 downto 0);   -- registro de direccion de la ROM
signal ext_a    : STD_LOGIC_VECTOR (25 downto 0);
signal a32      : STD_LOGIC_VECTOR (31 downto 0);  -- dato de la ROM a 32 bits
signal fila_ram, col_ram : STD_LOGIC_VECTOR (2 downto 0);
signal dir_ram  : STD_LOGIC_VECTOR (5 downto 0);
signal din_ram  : STD_LOGIC_VECTOR (31 downto 0);
signal dout_ram : STD_LOGIC_VECTOR (31 downto 0);
signal we_ram   : STD_LOGIC;

------------------------------------------------------------------------------
-- Registros del algoritmo de Bareiss
------------------------------------------------------------------------------
signal n, i, j, k : STD_LOGIC_VECTOR (2 downto 0); -- tamano y contadores
signal piv   : STD_LOGIC_VECTOR (31 downto 0);     -- pivote actual a(k,k)
signal p     : STD_LOGIC_VECTOR (31 downto 0);     -- pivote anterior (divisor)
signal pabs  : STD_LOGIC_VECTOR (31 downto 0);     -- |p|
signal signo : STD_LOGIC;                          -- '1' = numero impar de intercambios
signal b1, b2, b3, b4 : STD_LOGIC_VECTOR (31 downto 0); -- banco de pivotes
signal tmp1, tmp2 : STD_LOGIC_VECTOR (31 downto 0); -- intercambio de filas
signal t1, t2, t3 : STD_LOGIC_VECTOR (49 downto 0); -- productos y numerador
signal det_bin : STD_LOGIC_VECTOR (31 downto 0);   -- determinante en binario

-- Multiplicador: producto = mul_a * mul_b
signal mul_a, mul_b : STD_LOGIC_VECTOR (24 downto 0);
signal producto     : STD_LOGIC_VECTOR (49 downto 0);

-- Sumador/restador: resultado = sr_a + sr_b  o  sr_a - sr_b
signal sr_a, sr_b, resultado : STD_LOGIC_VECTOR (49 downto 0);
signal sr_op : STD_LOGIC;                          -- '0' suma, '1' resta
signal sx_piv, sx_dout, sx_val : STD_LOGIC_VECTOR (17 downto 0);

-- Division por restas sucesivas
signal R  : STD_LOGIC_VECTOR (49 downto 0);        -- residuo
signal Q  : STD_LOGIC_VECTOR (31 downto 0);        -- cociente
signal sq : STD_LOGIC;                             -- signo del cociente

------------------------------------------------------------------------------
-- Conversion XS3 (binario -> BCD)
------------------------------------------------------------------------------
signal conv_piv : STD_LOGIC;                       -- '0' convierte det, '1' convierte pivote
signal piv_sel  : STD_LOGIC_VECTOR (31 downto 0);  -- banco(dir_p)
signal val      : STD_LOGIC_VECTOR (31 downto 0);  -- valor que se va a convertir
signal dir_ant  : STD_LOGIC_VECTOR (2 downto 0);   -- dir_p ya convertido
signal bin      : STD_LOGIC_VECTOR (31 downto 0);  -- registro binario
signal bcd      : STD_LOGIC_VECTOR (39 downto 0);  -- registro decimal: 10 digitos de 4 bits
signal cont     : STD_LOGIC_VECTOR (4 downto 0);   -- bits procesados (0..31)
signal d        : STD_LOGIC_VECTOR (3 downto 0);   -- digito revisado (0..9)
signal dig      : STD_LOGIC_VECTOR (3 downto 0);   -- digito d del registro decimal
signal neg      : STD_LOGIC;                       -- signo del valor convertido
signal det_bcd, piv_bcd : STD_LOGIC_VECTOR (39 downto 0);   -- resultados
signal det_neg_r, piv_neg_r : STD_LOGIC;

begin

------------------------------------------------------------------------------
-- CAMINO DE DATOS: bloques y conexiones que dependen del estado
------------------------------------------------------------------------------

-- ROM externa
dira  <= dira_r;
ext_a <= (others => a(5));
a32   <= ext_a & a;                                     -- extension de signo

-- RAM: direccion, dato y escritura segun el estado
fila_ram <= k when (st = s4 or st = s6 or st = s8 or st = s13) else
            n when st = s20 else
            i;
col_ram  <= k when (st = s4 or st = s5 or st = s12) else
            n when st = s20 else
            j;
dir_ram  <= fila_ram & col_ram;

we_ram   <= '1' when (st = s2 or st = s8 or st = s9 or st = s18) else '0';

din_ram  <= a32                    when st = s2 else    -- copia de la ROM
            tmp2                   when st = s8 else    -- intercambio
            tmp1                   when st = s9 else    -- intercambio
            resultado(31 downto 0) when sq = '1' else   -- s18: -Q
            Q;                                          -- s18: +Q

U_RAM : ram_trabajo port map (clk => clk, we => we_ram, dir => dir_ram,
                              din => din_ram, dout => dout_ram);

-- Multiplicador
U_MUL : multiplicador port map (a => mul_a, b => mul_b, p => producto);

-- Sumador/restador: operandos segun el estado
sx_piv  <= (others => piv(31));
sx_dout <= (others => dout_ram(31));
sx_val  <= (others => val(31));

sr_a <= t1           when st = s15 else                 -- t1 - t2
        R            when st = s17 else                 -- R - |p|
        CERO46 & dig when st = s24 else                 -- digito + 3
        CERO50;                                         -- 0 - x (negacion)
sr_b <= t2                 when st = s15 else
        t3                 when st = s16 else           -- -t3
        CERO18 & pabs      when st = s17 else           -- |p|
        CERO18 & Q         when st = s18 else           -- -Q
        sx_piv & piv       when st = s19 else           -- -piv
        sx_dout & dout_ram when st = s20 else           -- -a(n,n)
        sx_val & val       when st = s21 else           -- -valor
        TRES50             when st = s24 else           -- +3 (XS3)
        CERO50;
sr_op <= '0' when st = s24 else '1';

U_SR : sumador_restador port map (a => sr_a, b => sr_b, op => sr_op, s => resultado);

-- Banco de pivotes: lectura con dir_p
with dir_p select
    piv_sel <= b1     when "001",
               b2     when "010",
               b3     when "011",
               b4     when "100",
               CERO32 when others;

-- Valor a convertir: det en la primera pasada, pivote(dir_p) en la segunda
val <= det_bin when conv_piv = '0' else piv_sel;

-- XS3: digito d del registro decimal
with d select
    dig <= bcd(3 downto 0)   when "0000",
           bcd(7 downto 4)   when "0001",
           bcd(11 downto 8)  when "0010",
           bcd(15 downto 12) when "0011",
           bcd(19 downto 16) when "0100",
           bcd(23 downto 20) when "0101",
           bcd(27 downto 24) when "0110",
           bcd(31 downto 28) when "0111",
           bcd(35 downto 32) when "1000",
           bcd(39 downto 36) when "1001",
           "0000"            when others;

-- Salidas de la caja negra
final   <= '1' when st = s27 else '0';
det     <= det_bcd;
det_neg <= det_neg_r;
pivote  <= piv_bcd;
piv_neg <= piv_neg_r;

------------------------------------------------------------------------------
-- DIAGRAMA ASM
------------------------------------------------------------------------------
process (clk, rst)
begin

if rst = '1' then
    st      <= s0;
    dira_r  <= "00000";
    n       <= "000";   i <= "000";   j <= "000";   k <= "000";
    piv     <= CERO32;  p <= CERO32;  pabs <= CERO32;  signo <= '0';
    b1      <= CERO32;  b2 <= CERO32;  b3 <= CERO32;  b4 <= CERO32;
    tmp1    <= CERO32;  tmp2 <= CERO32;
    mul_a   <= (others => '0');  mul_b <= (others => '0');
    t1      <= CERO50;  t2 <= CERO50;  t3 <= CERO50;
    R       <= CERO50;  Q <= CERO32;  sq <= '0';
    det_bin <= CERO32;
    conv_piv <= '0';    dir_ant <= "000";
    bin     <= CERO32;  bcd <= CERO40;  cont <= "00000";  d <= "0000";  neg <= '0';
    det_bcd <= CERO40;  det_neg_r <= '0';
    piv_bcd <= CERO40;  piv_neg_r <= '0';

elsif clk'event and clk = '1' then

    case st is

        ----------------------------------------------------------------
        -- Espera y carga de la matriz
        ----------------------------------------------------------------
        when s0 =>                              -- final = 0 ; dira = 0
            dira_r <= "00000";
            if inicio = '0' then
                st <= s0;
            else
                st <= s1;
            end if;

        when s1 =>                              -- n = ROM(00h)
            n      <= a(2 downto 0);
            dira_r <= "00001";
            i      <= "001";
            j      <= "001";
            st     <= s2;

        when s2 =>                              -- M(i,j) = ROM(dira), por columnas
            dira_r <= dira_r + '1';
            if i = n then
                i <= "001";
                if j = n then
                    st <= s3;
                else
                    j  <= j + '1';
                    st <= s2;
                end if;
            else
                i  <= i + '1';
                st <= s2;
            end if;

        when s3 =>                              -- inicializacion de Bareiss
            k        <= "001";
            p        <= UNO32;                  -- pivote inicial a(0,0) = 1
            pabs     <= UNO32;
            signo    <= '0';
            b1 <= CERO32;  b2 <= CERO32;  b3 <= CERO32;  b4 <= CERO32;
            conv_piv <= '0';
            st       <= s4;

        ----------------------------------------------------------------
        -- Pivote del paso k
        ----------------------------------------------------------------
        when s4 =>                              -- piv = M(k,k)
            piv <= dout_ram;
            if dout_ram = CERO32 then
                i  <= k + '1';
                st <= s5;
            else
                st <= s10;
            end if;

        when s5 =>                              -- busca fila i > k con M(i,k) /= 0
            if dout_ram /= CERO32 then
                j     <= k;
                signo <= not signo;             -- el intercambio cambia el signo
                st    <= s6;
            elsif i = n then
                det_bin <= CERO32;              -- no hay fila: matriz singular
                st      <= s21;
            else
                i  <= i + '1';
                st <= s5;
            end if;

        when s6 =>                              -- tmp1 = M(k,j)
            tmp1 <= dout_ram;
            st   <= s7;

        when s7 =>                              -- tmp2 = M(i,j)
            tmp2 <= dout_ram;
            st   <= s8;

        when s8 =>                              -- M(k,j) = tmp2
            st <= s9;

        when s9 =>                              -- M(i,j) = tmp1
            if j = n then
                st <= s4;                       -- vuelve a leer el pivote
            else
                j  <= j + '1';
                st <= s6;
            end if;

        when s10 =>                             -- banco(k) = piv ; i = j = k + 1
            case k is
                when "001"  => b1 <= piv;
                when "010"  => b2 <= piv;
                when "011"  => b3 <= piv;
                when "100"  => b4 <= piv;
                when others => null;
            end case;
            i  <= k + '1';
            j  <= k + '1';
            st <= s11;

        ----------------------------------------------------------------
        -- a(i,j) = ( a(k,k)*a(i,j) - a(i,k)*a(k,j) ) / p
        ----------------------------------------------------------------
        when s11 =>                             -- mul_a = a(k,k) ; mul_b = M(i,j)
            mul_a <= piv(24 downto 0);
            mul_b <= dout_ram(24 downto 0);
            st    <= s12;

        when s12 =>                             -- t1 = mul_a * mul_b ; mul_a = M(i,k)
            t1    <= producto;
            mul_a <= dout_ram(24 downto 0);
            st    <= s13;

        when s13 =>                             -- mul_b = M(k,j)
            mul_b <= dout_ram(24 downto 0);
            st    <= s14;

        when s14 =>                             -- t2 = mul_a * mul_b
            t2 <= producto;
            st <= s15;

        when s15 =>                             -- t3 = t1 - t2
            t3 <= resultado;
            st <= s16;

        when s16 =>                             -- R = |t3| ; Q = 0 ; signo del cociente
            Q  <= CERO32;
            sq <= t3(49) xor p(31);
            if t3(49) = '1' then
                R <= resultado;                 -- R = 0 - t3
            else
                R <= t3;
            end if;
            st <= s17;

        when s17 =>                             -- division por restas sucesivas
            if resultado(49) = '0' then         -- R - |p| >= 0
                R  <= resultado;                -- R = R - |p|
                Q  <= Q + '1';
                st <= s17;
            else
                st <= s18;
            end if;

        when s18 =>                             -- M(i,j) = Q o -Q ; avanza j, i
            if j = n then
                if i = n then
                    st <= s19;
                else
                    i  <= i + '1';
                    j  <= k + '1';
                    st <= s11;
                end if;
            else
                j  <= j + '1';
                st <= s11;
            end if;

        when s19 =>                             -- p = piv ; |p| = |piv| ; k = k + 1
            p <= piv;
            if piv(31) = '1' then
                pabs <= resultado(31 downto 0); -- |p| = 0 - piv
            else
                pabs <= piv;
            end if;
            k <= k + '1';
            if k + '1' = n then                 -- k = n - 1 : ultimo paso
                st <= s20;
            else
                st <= s4;
            end if;

        when s20 =>                             -- det = M(n,n) o -M(n,n)
            if signo = '1' then
                det_bin <= resultado(31 downto 0);  -- det = 0 - M(n,n)
            else
                det_bin <= dout_ram;
            end if;
            st <= s21;

        ----------------------------------------------------------------
        -- Conversion XS3 de det (conv_piv = 0) y del pivote (conv_piv = 1)
        ----------------------------------------------------------------
        when s21 =>                             -- bin = |val| ; neg = signo de val
            dir_ant <= dir_p;
            neg     <= val(31);
            if val(31) = '1' then
                bin <= resultado(31 downto 0);  -- bin = 0 - val
            else
                bin <= val;
            end if;
            st <= s22;

        when s22 =>                             -- XS3 paso 1: registro decimal = 0
            bcd  <= CERO40;
            cont <= "00000";
            st   <= s23;

        when s23 =>                             -- XS3 paso 2: LSB decimal = MSB binario
            bcd(0) <= bin(31);
            if cont = "11111" then
                st <= s26;                      -- paso 5: ultimo paso 2 hecho
            else
                d  <= "0000";
                st <= s24;
            end if;

        when s24 =>                             -- XS3 paso 3: si digito(d) > 4, sumar 3
            if dig > "0100" then
                case d is                       -- digito(d) = digito(d) + 3
                    when "0000" => bcd(3 downto 0)   <= resultado(3 downto 0);
                    when "0001" => bcd(7 downto 4)   <= resultado(3 downto 0);
                    when "0010" => bcd(11 downto 8)  <= resultado(3 downto 0);
                    when "0011" => bcd(15 downto 12) <= resultado(3 downto 0);
                    when "0100" => bcd(19 downto 16) <= resultado(3 downto 0);
                    when "0101" => bcd(23 downto 20) <= resultado(3 downto 0);
                    when "0110" => bcd(27 downto 24) <= resultado(3 downto 0);
                    when "0111" => bcd(31 downto 28) <= resultado(3 downto 0);
                    when "1000" => bcd(35 downto 32) <= resultado(3 downto 0);
                    when "1001" => bcd(39 downto 36) <= resultado(3 downto 0);
                    when others => null;
                end case;
            end if;
            if d = "1001" then
                st <= s25;
            else
                d  <= d + '1';
                st <= s24;
            end if;

        when s25 =>                             -- XS3 paso 4: corrimiento a la izquierda
            bcd  <= bcd(38 downto 0) & '0';
            bin  <= bin(30 downto 0) & '0';
            cont <= cont + '1';
            st   <= s23;

        when s26 =>                             -- guarda el resultado de la conversion
            if conv_piv = '0' then
                det_bcd   <= bcd;               -- det convertido
                det_neg_r <= neg;
                conv_piv  <= '1';
                st        <= s21;               -- ahora convierte el pivote
            else
                piv_bcd   <= bcd;               -- pivote convertido
                piv_neg_r <= neg;
                st        <= s27;
            end if;

        when s27 =>                             -- final = 1
            dira_r <= "00000";
            if inicio = '1' then
                st <= s1;                       -- nuevo calculo
            elsif dir_p /= dir_ant then
                st <= s21;                      -- cambio dir_p: convierte el nuevo pivote
            else
                st <= s27;
            end if;

        when others =>
            st <= s0;

    end case;
end if;
end process;

end Behavioral;


----------------------------------------------------------------------------------
-- SINCRONIZADOR: dos flip-flops para el boton y los switches
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity sincronizador is
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           sw_mat   : in  STD_LOGIC_VECTOR (2 downto 0);
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
           ver      : in  STD_LOGIC;
           inicio_s : out STD_LOGIC;
           sw_mat_s : out STD_LOGIC_VECTOR (2 downto 0);
           dir_p_s  : out STD_LOGIC_VECTOR (2 downto 0);
           ver_s    : out STD_LOGIC);
end sincronizador;

architecture Behavioral of sincronizador is
signal ini_1, ini_2, ver_1, ver_2 : STD_LOGIC;
signal mat_1, mat_2, dir_1, dir_2 : STD_LOGIC_VECTOR (2 downto 0);
begin

process (clk, rst)
begin
    if rst = '1' then
        ini_1 <= '0';    ini_2 <= '0';
        ver_1 <= '0';    ver_2 <= '0';
        mat_1 <= "000";  mat_2 <= "000";
        dir_1 <= "000";  dir_2 <= "000";
    elsif clk'event and clk = '1' then
        ini_1 <= inicio;  ini_2 <= ini_1;
        ver_1 <= ver;     ver_2 <= ver_1;
        mat_1 <= sw_mat;  mat_2 <= mat_1;
        dir_1 <= dir_p;   dir_2 <= dir_1;
    end if;
end process;

inicio_s <= ini_2;
ver_s    <= ver_2;
sw_mat_s <= mat_2;
dir_p_s  <= dir_2;

end Behavioral;


----------------------------------------------------------------------------------
-- DISPLAY DE 8 DIGITOS MULTIPLEXADO (Nexys A7, anodo comun, activos en bajo)
-- AN7 = signo ('-' o apagado), AN6..AN0 = 7 digitos BCD.
-- Contador de refresco de 18 bits: 2^15 ciclos por digito, 2,6 ms por barrido.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity display_8dig is
    Port ( clk, rst : in  STD_LOGIC;
           bcd      : in  STD_LOGIC_VECTOR (27 downto 0);
           neg      : in  STD_LOGIC;
           an       : out STD_LOGIC_VECTOR (7 downto 0);
           seg      : out STD_LOGIC_VECTOR (6 downto 0);   -- seg(0)=CA ... seg(6)=CG
           dp       : out STD_LOGIC);
end display_8dig;

architecture Behavioral of display_8dig is
signal refresco  : STD_LOGIC_VECTOR (17 downto 0);
signal dsel      : STD_LOGIC_VECTOR (2 downto 0);
signal car       : STD_LOGIC_VECTOR (3 downto 0);   -- 0-9, A = '-', F = apagado
signal car_signo : STD_LOGIC_VECTOR (3 downto 0);
begin

process (clk, rst)
begin
    if rst = '1' then
        refresco <= (others => '0');
    elsif clk'event and clk = '1' then
        refresco <= refresco + '1';
    end if;
end process;

dsel      <= refresco(17 downto 15);
car_signo <= "1010" when neg = '1' else "1111";

with dsel select
    car <= bcd(3 downto 0)   when "000",
           bcd(7 downto 4)   when "001",
           bcd(11 downto 8)  when "010",
           bcd(15 downto 12) when "011",
           bcd(19 downto 16) when "100",
           bcd(23 downto 20) when "101",
           bcd(27 downto 24) when "110",
           car_signo         when others;

with dsel select
    an <= "11111110" when "000",
          "11111101" when "001",
          "11111011" when "010",
          "11110111" when "011",
          "11101111" when "100",
          "11011111" when "101",
          "10111111" when "110",
          "01111111" when others;

with car select                                 --  gfedcba
    seg <= "1000000" when "0000",               --  0
           "1111001" when "0001",               --  1
           "0100100" when "0010",               --  2
           "0110000" when "0011",               --  3
           "0011001" when "0100",               --  4
           "0010010" when "0101",               --  5
           "0000010" when "0110",               --  6
           "1111000" when "0111",               --  7
           "0000000" when "1000",               --  8
           "0010000" when "1001",               --  9
           "0111111" when "1010",               --  -
           "1111111" when others;               --  apagado

dp <= '1';

end Behavioral;


----------------------------------------------------------------------------------
-- TOPE: det_bareiss (sincronizador + ROM + ASM + display)
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity det_bareiss is
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;                      -- BTNC
           sw_mat   : in  STD_LOGIC_VECTOR (2 downto 0);  -- SW15..SW13: matriz (pagina de la ROM)
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);  -- SW2..SW0 : direccion del pivote (1..4)
           ver      : in  STD_LOGIC;                      -- SW3: 0 = muestra det, 1 = muestra pivote
           final    : out STD_LOGIC;                      -- LD0
           desborde : out STD_LOGIC;                      -- LD1: el valor mostrado tiene mas de 7 digitos
           an       : out STD_LOGIC_VECTOR (7 downto 0);
           seg      : out STD_LOGIC_VECTOR (6 downto 0);
           dp       : out STD_LOGIC);
end det_bareiss;

architecture Behavioral of det_bareiss is

component sincronizador
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           sw_mat   : in  STD_LOGIC_VECTOR (2 downto 0);
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
           ver      : in  STD_LOGIC;
           inicio_s : out STD_LOGIC;
           sw_mat_s : out STD_LOGIC_VECTOR (2 downto 0);
           dir_p_s  : out STD_LOGIC_VECTOR (2 downto 0);
           ver_s    : out STD_LOGIC);
end component;

component rom_matrices
    Port ( dir : in  STD_LOGIC_VECTOR (7 downto 0);
           a   : out STD_LOGIC_VECTOR (5 downto 0));
end component;

component asm_bareiss
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
           a        : in  STD_LOGIC_VECTOR (5 downto 0);
           dira     : out STD_LOGIC_VECTOR (4 downto 0);
           det      : out STD_LOGIC_VECTOR (39 downto 0);
           det_neg  : out STD_LOGIC;
           pivote   : out STD_LOGIC_VECTOR (39 downto 0);
           piv_neg  : out STD_LOGIC;
           final    : out STD_LOGIC);
end component;

component display_8dig
    Port ( clk, rst : in  STD_LOGIC;
           bcd      : in  STD_LOGIC_VECTOR (27 downto 0);
           neg      : in  STD_LOGIC;
           an       : out STD_LOGIC_VECTOR (7 downto 0);
           seg      : out STD_LOGIC_VECTOR (6 downto 0);
           dp       : out STD_LOGIC);
end component;

constant CERO12 : STD_LOGIC_VECTOR (11 downto 0) := x"000";

signal inicio_s, ver_s : STD_LOGIC;
signal sw_mat_s, dir_p_s : STD_LOGIC_VECTOR (2 downto 0);
signal dira     : STD_LOGIC_VECTOR (4 downto 0);
signal dir_rom  : STD_LOGIC_VECTOR (7 downto 0);
signal a        : STD_LOGIC_VECTOR (5 downto 0);
signal det, pivote, mostrar : STD_LOGIC_VECTOR (39 downto 0);
signal det_neg, piv_neg, mostrar_neg : STD_LOGIC;

begin

U_SINC : sincronizador port map (
    clk => clk, rst => rst, inicio => inicio, sw_mat => sw_mat, dir_p => dir_p, ver => ver,
    inicio_s => inicio_s, sw_mat_s => sw_mat_s, dir_p_s => dir_p_s, ver_s => ver_s);

-- ROM externa al ASM; la pagina la eligen los switches SW15..SW13
dir_rom <= sw_mat_s & dira;
U_ROM : rom_matrices port map (dir => dir_rom, a => a);

U_ASM : asm_bareiss port map (
    clk => clk, rst => rst, inicio => inicio_s, dir_p => dir_p_s, a => a, dira => dira,
    det => det, det_neg => det_neg, pivote => pivote, piv_neg => piv_neg, final => final);

-- Valor que se muestra en los displays
mostrar     <= det     when ver_s = '0' else pivote;
mostrar_neg <= det_neg when ver_s = '0' else piv_neg;
desborde    <= '0' when mostrar(39 downto 28) = CERO12 else '1';

U_DISP : display_8dig port map (
    clk => clk, rst => rst, bcd => mostrar(27 downto 0), neg => mostrar_neg,
    an => an, seg => seg, dp => dp);

end Behavioral;

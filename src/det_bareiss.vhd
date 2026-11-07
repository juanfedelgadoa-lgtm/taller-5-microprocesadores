----------------------------------------------------------------------------------
-- Universidad Distrital Francisco Jose de Caldas
-- Analisis y Diseno de Microprocesadores - Taller 5
--
-- Microprocesador de proposito especifico: determinante de una matriz simetrica
-- de 2x2 a 5x5 por el algoritmo de Bareiss, division por restas sucesivas y
-- conversion binario -> BCD por el algoritmo XS3 (paso a paso en el ASM).
--
-- Herramienta : Xilinx ISE 14.7 (XST / ISim)
-- Tarjeta     : Digilent Nexys A7-100T (XC7A100T-1CSG324C), reloj de 100 MHz
--
-- Estilo RTL:
--   * Solo senales de tipo std_logic y std_logic_vector (sin variables, sin
--     integer, sin signed/unsigned, sin genericos).  La unica excepcion es el
--     arreglo de la RAM (array of std_logic_vector), que es la forma de
--     describir una memoria para que XST la infiera.
--   * Unidad de control (FSM de 27 estados) separada del camino de datos.
--   * Camino de datos = registros con habilitacion + multiplexores + unidades
--     funcionales (multiplicador, sumador/restador) + memorias (ROM, RAM).
--   * Sin lazos for ni descripciones tipo software: las repeticiones del
--     algoritmo las hace la FSM, un paso por ciclo de reloj.
--
-- Jerarquia (todas las entidades estan en este archivo):
--   det_bareiss (tope)
--     |- sincronizador
--     |- procesador
--     |    |- unidad_control      (FSM / ASM)
--     |    |- camino_datos
--     |         |- rom_matrices
--     |         |- ram_trabajo
--     |         |- multiplicador
--     |         |- sumador_restador
--     |- display_8dig
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

architecture RTL of rom_matrices is
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
end RTL;


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

architecture RTL of ram_trabajo is
type ram_tipo is array (0 to 63) of std_logic_vector (31 downto 0);
signal ram : ram_tipo := (others => (others => '0'));   -- contenido inicial (INIT)
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

end RTL;


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

architecture RTL of multiplicador is
begin
p <= a * b;
end RTL;


----------------------------------------------------------------------------------
-- SUMADOR/RESTADOR DE 50 bits (combinacional).
-- op = '0': s = a + b      op = '1': s = a + not(b) + 1 = a - b
-- Un solo sumador con acarreo de entrada.
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

architecture RTL of sumador_restador is
signal bx : STD_LOGIC_VECTOR (49 downto 0);
begin
bx <= not b when op = '1' else b;
s  <= a + bx + op;
end RTL;


----------------------------------------------------------------------------------
-- CAMINO DE DATOS
-- Registros con habilitacion (ld_*, clr_*, inc_*), multiplexores (sel_*),
-- memorias y unidades funcionales. Genera las senales de estado para la FSM.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity camino_datos is
    Port ( clk, rst  : in  STD_LOGIC;
           sw_mat    : in  STD_LOGIC_VECTOR (2 downto 0);
           sw_piv    : in  STD_LOGIC_VECTOR (2 downto 0);
           -- senales de control (desde la unidad de control)
           ld_pag, clr_dira, inc_dira : in STD_LOGIC;
           we_ram    : in  STD_LOGIC;
           sel_fila  : in  STD_LOGIC_VECTOR (1 downto 0);
           sel_col   : in  STD_LOGIC_VECTOR (1 downto 0);
           sel_din   : in  STD_LOGIC_VECTOR (2 downto 0);
           ld_n      : in  STD_LOGIC;
           ld_i      : in  STD_LOGIC;
           sel_i     : in  STD_LOGIC_VECTOR (1 downto 0);
           ld_j      : in  STD_LOGIC;
           sel_j     : in  STD_LOGIC_VECTOR (1 downto 0);
           ld_k, sel_k            : in STD_LOGIC;
           ld_piv                 : in STD_LOGIC;
           ld_p, sel_p            : in STD_LOGIC;
           ld_pabs   : in  STD_LOGIC;
           sel_pabs  : in  STD_LOGIC_VECTOR (1 downto 0);
           clr_signo, tog_signo   : in STD_LOGIC;
           clr_banco, ld_banco    : in STD_LOGIC;
           ld_tmp1, ld_tmp2       : in STD_LOGIC;
           ld_ma, sel_ma, ld_mb   : in STD_LOGIC;
           ld_t1, ld_t2, ld_t3    : in STD_LOGIC;
           ld_r, sel_r, clr_q, inc_q, ld_sq : in STD_LOGIC;
           ld_det    : in  STD_LOGIC;
           sel_det   : in  STD_LOGIC_VECTOR (1 downto 0);
           sel_sra   : in  STD_LOGIC_VECTOR (1 downto 0);
           sel_srb   : in  STD_LOGIC_VECTOR (2 downto 0);
           op_sr     : in  STD_LOGIC;
           ld_selant, ld_neg      : in STD_LOGIC;
           ld_bin    : in  STD_LOGIC;
           sel_bin   : in  STD_LOGIC_VECTOR (1 downto 0);
           clr_bcd, ins_bcd, aj_bcd, sh_bcd : in STD_LOGIC;
           clr_cont, inc_cont     : in STD_LOGIC;
           clr_d, inc_d           : in STD_LOGIC;
           ld_disp                : in STD_LOGIC;
           -- senales de estado (hacia la unidad de control)
           z_dout, i_eq_n, j_eq_n, k1_eq_n      : out STD_LOGIC;
           t3_neg, r_ge, sq, piv_neg            : out STD_LOGIC;
           signo, val_neg                       : out STD_LOGIC;
           cont_31, dig_gt4, d_9, sel_dif       : out STD_LOGIC;
           -- salida hacia el display
           disp_bcd  : out STD_LOGIC_VECTOR (27 downto 0);
           disp_neg  : out STD_LOGIC;
           desborde  : out STD_LOGIC);
end camino_datos;

architecture RTL of camino_datos is

component rom_matrices
    Port ( dir : in  STD_LOGIC_VECTOR (7 downto 0);
           a   : out STD_LOGIC_VECTOR (5 downto 0));
end component;

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

-- Constantes
constant UNO3   : STD_LOGIC_VECTOR (2 downto 0)  := "001";
constant CERO12 : STD_LOGIC_VECTOR (11 downto 0) := x"000";
constant CERO18 : STD_LOGIC_VECTOR (17 downto 0) := "000000000000000000";
constant CERO32 : STD_LOGIC_VECTOR (31 downto 0) := x"00000000";
constant UNO32  : STD_LOGIC_VECTOR (31 downto 0) := x"00000001";
constant CERO40 : STD_LOGIC_VECTOR (39 downto 0) := x"0000000000";
constant CERO46 : STD_LOGIC_VECTOR (45 downto 0) := (others => '0');
constant CERO50 : STD_LOGIC_VECTOR (49 downto 0) := (others => '0');
constant TRES50 : STD_LOGIC_VECTOR (49 downto 0) := (1 downto 0 => '1', others => '0');

-- Registros
signal pag      : STD_LOGIC_VECTOR (2 downto 0);   -- pagina de la ROM
signal dira     : STD_LOGIC_VECTOR (4 downto 0);   -- direccion de la ROM
signal n, i, j, k : STD_LOGIC_VECTOR (2 downto 0); -- tamano y contadores
signal piv      : STD_LOGIC_VECTOR (31 downto 0);  -- pivote actual a(k,k)
signal p        : STD_LOGIC_VECTOR (31 downto 0);  -- pivote anterior (divisor)
signal pabs     : STD_LOGIC_VECTOR (31 downto 0);  -- |p|
signal signo_r  : STD_LOGIC;                       -- paridad de intercambios
signal b1, b2, b3, b4 : STD_LOGIC_VECTOR (31 downto 0); -- banco de pivotes
signal tmp1, tmp2 : STD_LOGIC_VECTOR (31 downto 0); -- intercambio de filas
signal mul_a, mul_b : STD_LOGIC_VECTOR (24 downto 0); -- entradas del multiplicador
signal t1, t2, t3 : STD_LOGIC_VECTOR (49 downto 0); -- productos y numerador
signal R        : STD_LOGIC_VECTOR (49 downto 0);  -- residuo
signal Q        : STD_LOGIC_VECTOR (31 downto 0);  -- cociente
signal sq_r     : STD_LOGIC;                       -- signo del cociente
signal det      : STD_LOGIC_VECTOR (31 downto 0);  -- determinante
signal sel_ant  : STD_LOGIC_VECTOR (2 downto 0);   -- seleccion ya convertida
signal neg      : STD_LOGIC;                       -- signo del valor convertido
signal bin      : STD_LOGIC_VECTOR (31 downto 0);  -- registro binario (XS3)
signal bcd      : STD_LOGIC_VECTOR (39 downto 0);  -- registro decimal (XS3), 10 digitos
signal cont     : STD_LOGIC_VECTOR (4 downto 0);   -- bits procesados (0..31)
signal d        : STD_LOGIC_VECTOR (3 downto 0);   -- digito revisado (0..9)
signal disp     : STD_LOGIC_VECTOR (39 downto 0);  -- valor que se muestra
signal disp_neg_r : STD_LOGIC;

-- Senales combinacionales
signal dir_rom  : STD_LOGIC_VECTOR (7 downto 0);
signal a        : STD_LOGIC_VECTOR (5 downto 0);
signal ext_a    : STD_LOGIC_VECTOR (25 downto 0);
signal a32      : STD_LOGIC_VECTOR (31 downto 0);
signal fila, col : STD_LOGIC_VECTOR (2 downto 0);
signal dir_ram  : STD_LOGIC_VECTOR (5 downto 0);
signal din_ram  : STD_LOGIC_VECTOR (31 downto 0);
signal dout     : STD_LOGIC_VECTOR (31 downto 0);
signal mul_p    : STD_LOGIC_VECTOR (49 downto 0);
signal sr_a, sr_b, sr_s : STD_LOGIC_VECTOR (49 downto 0);
signal sx_piv, sx_dout, sx_val : STD_LOGIC_VECTOR (17 downto 0);
signal i_mas1, j_mas1, k_mas1 : STD_LOGIC_VECTOR (2 downto 0);
signal i_d, j_d, k_d : STD_LOGIC_VECTOR (2 downto 0);
signal p_d, pabs_d, det_d, bin_d : STD_LOGIC_VECTOR (31 downto 0);
signal ma_d     : STD_LOGIC_VECTOR (24 downto 0);
signal r_d      : STD_LOGIC_VECTOR (49 downto 0);
signal we_b1, we_b2, we_b3, we_b4 : STD_LOGIC;
signal val      : STD_LOGIC_VECTOR (31 downto 0);
signal dig      : STD_LOGIC_VECTOR (3 downto 0);
signal bcd_ins, bcd_aj, bcd_sh : STD_LOGIC_VECTOR (39 downto 0);

begin

------------------------------------------------------------------------------
-- Memorias y unidades funcionales
------------------------------------------------------------------------------
dir_rom <= pag & dira;
U_ROM : rom_matrices     port map (dir => dir_rom, a => a);
U_RAM : ram_trabajo      port map (clk => clk, we => we_ram, dir => dir_ram,
                                   din => din_ram, dout => dout);
U_MUL : multiplicador    port map (a => mul_a, b => mul_b, p => mul_p);
U_SR  : sumador_restador port map (a => sr_a, b => sr_b, op => op_sr, s => sr_s);

------------------------------------------------------------------------------
-- Extensiones de signo
------------------------------------------------------------------------------
ext_a   <= (others => a(5));
a32     <= ext_a & a;                       -- dato de la ROM a 32 bits
sx_piv  <= (others => piv(31));
sx_dout <= (others => dout(31));
sx_val  <= (others => val(31));

------------------------------------------------------------------------------
-- Direccion y dato de la RAM
------------------------------------------------------------------------------
with sel_fila select
    fila <= i when "00",
            k when "01",
            n when others;

with sel_col select
    col <= j when "00",
           k when "01",
           n when others;

dir_ram <= fila & col;

with sel_din select
    din_ram <= a32               when "000",   -- copia de la ROM
               tmp1              when "001",   -- intercambio
               tmp2              when "010",   -- intercambio
               Q                 when "011",   -- +Q
               sr_s(31 downto 0) when others;  -- -Q

------------------------------------------------------------------------------
-- Operandos del sumador/restador
------------------------------------------------------------------------------
with sel_sra select
    sr_a <= CERO50       when "00",
            t1           when "01",
            R            when "10",
            CERO46 & dig when others;

with sel_srb select
    sr_b <= t2              when "000",
            t3              when "001",
            CERO18 & pabs   when "010",
            CERO18 & Q      when "011",
            sx_piv & piv    when "100",
            sx_dout & dout  when "101",
            sx_val & val    when "110",
            TRES50          when others;

------------------------------------------------------------------------------
-- Multiplexores de entrada de los registros
------------------------------------------------------------------------------
i_mas1 <= i + '1';
j_mas1 <= j + '1';
k_mas1 <= k + '1';

with sel_i select
    i_d <= UNO3   when "00",
           i_mas1 when "01",
           k_mas1 when others;

with sel_j select
    j_d <= UNO3   when "00",
           j_mas1 when "01",
           k_mas1 when "10",
           k      when others;

k_d  <= UNO3 when sel_k = '0' else k_mas1;
p_d  <= UNO32 when sel_p = '0' else piv;
ma_d <= piv(24 downto 0) when sel_ma = '0' else dout(24 downto 0);
r_d  <= t3 when sel_r = '0' else sr_s;

with sel_pabs select
    pabs_d <= UNO32             when "00",
              piv               when "01",
              sr_s(31 downto 0) when others;

with sel_det select
    det_d <= CERO32            when "00",
             dout              when "01",
             sr_s(31 downto 0) when others;

with sel_bin select
    bin_d <= val                    when "00",
             sr_s(31 downto 0)      when "01",
             bin(30 downto 0) & '0' when others;   -- corrimiento (XS3 paso 4)

-- Banco de pivotes: escritura decodificada por k, lectura por sw_piv
we_b1 <= '1' when (ld_banco = '1' and k = "001") else '0';
we_b2 <= '1' when (ld_banco = '1' and k = "010") else '0';
we_b3 <= '1' when (ld_banco = '1' and k = "011") else '0';
we_b4 <= '1' when (ld_banco = '1' and k = "100") else '0';

with sw_piv select
    val <= det    when "000",
           b1     when "001",
           b2     when "010",
           b3     when "011",
           b4     when "100",
           CERO32 when others;

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

-- XS3 paso 2: el MSB del binario entra al LSB del decimal
bcd_ins <= bcd(39 downto 1) & bin(31);

-- XS3 paso 3: el digito d se reemplaza por digito + 3 (salida del sumador)
bcd_aj(3 downto 0)   <= sr_s(3 downto 0) when d = "0000" else bcd(3 downto 0);
bcd_aj(7 downto 4)   <= sr_s(3 downto 0) when d = "0001" else bcd(7 downto 4);
bcd_aj(11 downto 8)  <= sr_s(3 downto 0) when d = "0010" else bcd(11 downto 8);
bcd_aj(15 downto 12) <= sr_s(3 downto 0) when d = "0011" else bcd(15 downto 12);
bcd_aj(19 downto 16) <= sr_s(3 downto 0) when d = "0100" else bcd(19 downto 16);
bcd_aj(23 downto 20) <= sr_s(3 downto 0) when d = "0101" else bcd(23 downto 20);
bcd_aj(27 downto 24) <= sr_s(3 downto 0) when d = "0110" else bcd(27 downto 24);
bcd_aj(31 downto 28) <= sr_s(3 downto 0) when d = "0111" else bcd(31 downto 28);
bcd_aj(35 downto 32) <= sr_s(3 downto 0) when d = "1000" else bcd(35 downto 32);
bcd_aj(39 downto 36) <= sr_s(3 downto 0) when d = "1001" else bcd(39 downto 36);

-- XS3 paso 4: corrimiento a la izquierda, entra 0
bcd_sh <= bcd(38 downto 0) & '0';

------------------------------------------------------------------------------
-- Registros
------------------------------------------------------------------------------
process (clk, rst)
begin
if rst = '1' then
    pag  <= "000";   dira <= "00000";
    n    <= "000";   i    <= "000";   j <= "000";   k <= "000";
    piv  <= CERO32;  p    <= CERO32;  pabs <= CERO32;  signo_r <= '0';
    b1   <= CERO32;  b2   <= CERO32;  b3   <= CERO32;  b4 <= CERO32;
    tmp1 <= CERO32;  tmp2 <= CERO32;
    mul_a <= (others => '0');  mul_b <= (others => '0');
    t1   <= CERO50;  t2   <= CERO50;  t3   <= CERO50;
    R    <= CERO50;  Q    <= CERO32;  sq_r <= '0';
    det  <= CERO32;  sel_ant <= "000"; neg <= '0';
    bin  <= CERO32;  bcd  <= CERO40;  cont <= "00000";  d <= "0000";
    disp <= CERO40;  disp_neg_r <= '0';

elsif clk'event and clk = '1' then

    -- Carga de la matriz
    if ld_pag = '1' then pag <= sw_mat; end if;

    if clr_dira = '1' then
        dira <= "00000";
    elsif inc_dira = '1' then
        dira <= dira + '1';
    end if;

    if ld_n = '1' then n <= a(2 downto 0); end if;
    if ld_i = '1' then i <= i_d; end if;
    if ld_j = '1' then j <= j_d; end if;
    if ld_k = '1' then k <= k_d; end if;

    -- Bareiss
    if ld_piv  = '1' then piv  <= dout;   end if;
    if ld_p    = '1' then p    <= p_d;    end if;
    if ld_pabs = '1' then pabs <= pabs_d; end if;

    if clr_signo = '1' then
        signo_r <= '0';
    elsif tog_signo = '1' then
        signo_r <= not signo_r;
    end if;

    if clr_banco = '1' then
        b1 <= CERO32;  b2 <= CERO32;  b3 <= CERO32;  b4 <= CERO32;
    else
        if we_b1 = '1' then b1 <= piv; end if;
        if we_b2 = '1' then b2 <= piv; end if;
        if we_b3 = '1' then b3 <= piv; end if;
        if we_b4 = '1' then b4 <= piv; end if;
    end if;

    if ld_tmp1 = '1' then tmp1 <= dout; end if;
    if ld_tmp2 = '1' then tmp2 <= dout; end if;

    if ld_ma = '1' then mul_a <= ma_d;              end if;
    if ld_mb = '1' then mul_b <= dout(24 downto 0); end if;
    if ld_t1 = '1' then t1 <= mul_p; end if;
    if ld_t2 = '1' then t2 <= mul_p; end if;
    if ld_t3 = '1' then t3 <= sr_s;  end if;

    -- Division por restas sucesivas
    if ld_r  = '1' then R    <= r_d;               end if;
    if ld_sq = '1' then sq_r <= t3(49) xor p(31);  end if;

    if clr_q = '1' then
        Q <= CERO32;
    elsif inc_q = '1' then
        Q <= Q + '1';
    end if;

    if ld_det = '1' then det <= det_d; end if;

    -- XS3 y visualizacion
    if ld_selant = '1' then sel_ant <= sw_piv;  end if;
    if ld_neg    = '1' then neg     <= val(31); end if;
    if ld_bin    = '1' then bin     <= bin_d;   end if;

    if clr_bcd = '1' then
        bcd <= CERO40;                 -- paso 1
    elsif ins_bcd = '1' then
        bcd <= bcd_ins;                -- paso 2
    elsif aj_bcd = '1' then
        bcd <= bcd_aj;                 -- paso 3
    elsif sh_bcd = '1' then
        bcd <= bcd_sh;                 -- paso 4
    end if;

    if clr_cont = '1' then
        cont <= "00000";
    elsif inc_cont = '1' then
        cont <= cont + '1';
    end if;

    if clr_d = '1' then
        d <= "0000";
    elsif inc_d = '1' then
        d <= d + '1';
    end if;

    if ld_disp = '1' then
        disp       <= bcd;
        disp_neg_r <= neg;
    end if;

end if;
end process;

------------------------------------------------------------------------------
-- Senales de estado
------------------------------------------------------------------------------
z_dout  <= '1' when dout = CERO32 else '0';      -- M(.,.) = 0
i_eq_n  <= '1' when i = n else '0';
j_eq_n  <= '1' when j = n else '0';
k1_eq_n <= '1' when k_mas1 = n else '0';         -- k = n - 1
t3_neg  <= t3(49);
r_ge    <= not sr_s(49);                         -- R - |p| >= 0
sq      <= sq_r;
piv_neg <= piv(31);
signo   <= signo_r;
val_neg <= val(31);
cont_31 <= '1' when cont = "11111" else '0';
dig_gt4 <= '1' when dig > "0100" else '0';       -- digito >= 5
d_9     <= '1' when d = "1001" else '0';
sel_dif <= '1' when sw_piv /= sel_ant else '0';

------------------------------------------------------------------------------
-- Salidas hacia el display
------------------------------------------------------------------------------
disp_bcd <= disp(27 downto 0);                   -- 7 digitos
disp_neg <= disp_neg_r;
desborde <= '0' when disp(39 downto 28) = CERO12 else '1';

end RTL;


----------------------------------------------------------------------------------
-- UNIDAD DE CONTROL: FSM del diagrama ASM (27 estados, S0 a S26).
-- Proceso 1: registro de estado.  Proceso 2: logica combinacional de estado
-- siguiente y de salidas (Moore en las cajas de estado, Mealy en las cajas
-- de salida condicional).
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity unidad_control is
    Port ( clk, rst  : in  STD_LOGIC;
           inicio    : in  STD_LOGIC;
           -- senales de estado (desde el camino de datos)
           z_dout, i_eq_n, j_eq_n, k1_eq_n      : in STD_LOGIC;
           t3_neg, r_ge, sq, piv_neg            : in STD_LOGIC;
           signo, val_neg                       : in STD_LOGIC;
           cont_31, dig_gt4, d_9, sel_dif       : in STD_LOGIC;
           -- senales de control (hacia el camino de datos)
           ld_pag, clr_dira, inc_dira : out STD_LOGIC;
           we_ram    : out STD_LOGIC;
           sel_fila  : out STD_LOGIC_VECTOR (1 downto 0);
           sel_col   : out STD_LOGIC_VECTOR (1 downto 0);
           sel_din   : out STD_LOGIC_VECTOR (2 downto 0);
           ld_n      : out STD_LOGIC;
           ld_i      : out STD_LOGIC;
           sel_i     : out STD_LOGIC_VECTOR (1 downto 0);
           ld_j      : out STD_LOGIC;
           sel_j     : out STD_LOGIC_VECTOR (1 downto 0);
           ld_k, sel_k            : out STD_LOGIC;
           ld_piv                 : out STD_LOGIC;
           ld_p, sel_p            : out STD_LOGIC;
           ld_pabs   : out STD_LOGIC;
           sel_pabs  : out STD_LOGIC_VECTOR (1 downto 0);
           clr_signo, tog_signo   : out STD_LOGIC;
           clr_banco, ld_banco    : out STD_LOGIC;
           ld_tmp1, ld_tmp2       : out STD_LOGIC;
           ld_ma, sel_ma, ld_mb   : out STD_LOGIC;
           ld_t1, ld_t2, ld_t3    : out STD_LOGIC;
           ld_r, sel_r, clr_q, inc_q, ld_sq : out STD_LOGIC;
           ld_det    : out STD_LOGIC;
           sel_det   : out STD_LOGIC_VECTOR (1 downto 0);
           sel_sra   : out STD_LOGIC_VECTOR (1 downto 0);
           sel_srb   : out STD_LOGIC_VECTOR (2 downto 0);
           op_sr     : out STD_LOGIC;
           ld_selant, ld_neg      : out STD_LOGIC;
           ld_bin    : out STD_LOGIC;
           sel_bin   : out STD_LOGIC_VECTOR (1 downto 0);
           clr_bcd, ins_bcd, aj_bcd, sh_bcd : out STD_LOGIC;
           clr_cont, inc_cont     : out STD_LOGIC;
           clr_d, inc_d           : out STD_LOGIC;
           ld_disp                : out STD_LOGIC;
           final                  : out STD_LOGIC);
end unidad_control;

architecture RTL of unidad_control is

-- Codificacion de los estados
constant S0  : STD_LOGIC_VECTOR (4 downto 0) := "00000";
constant S1  : STD_LOGIC_VECTOR (4 downto 0) := "00001";
constant S2  : STD_LOGIC_VECTOR (4 downto 0) := "00010";
constant S3  : STD_LOGIC_VECTOR (4 downto 0) := "00011";
constant S4  : STD_LOGIC_VECTOR (4 downto 0) := "00100";
constant S5  : STD_LOGIC_VECTOR (4 downto 0) := "00101";
constant S6  : STD_LOGIC_VECTOR (4 downto 0) := "00110";
constant S7  : STD_LOGIC_VECTOR (4 downto 0) := "00111";
constant S8  : STD_LOGIC_VECTOR (4 downto 0) := "01000";
constant S9  : STD_LOGIC_VECTOR (4 downto 0) := "01001";
constant S10 : STD_LOGIC_VECTOR (4 downto 0) := "01010";
constant S11 : STD_LOGIC_VECTOR (4 downto 0) := "01011";
constant S12 : STD_LOGIC_VECTOR (4 downto 0) := "01100";
constant S13 : STD_LOGIC_VECTOR (4 downto 0) := "01101";
constant S14 : STD_LOGIC_VECTOR (4 downto 0) := "01110";
constant S15 : STD_LOGIC_VECTOR (4 downto 0) := "01111";
constant S16 : STD_LOGIC_VECTOR (4 downto 0) := "10000";
constant S17 : STD_LOGIC_VECTOR (4 downto 0) := "10001";
constant S18 : STD_LOGIC_VECTOR (4 downto 0) := "10010";
constant S19 : STD_LOGIC_VECTOR (4 downto 0) := "10011";
constant S20 : STD_LOGIC_VECTOR (4 downto 0) := "10100";
constant S21 : STD_LOGIC_VECTOR (4 downto 0) := "10101";
constant S22 : STD_LOGIC_VECTOR (4 downto 0) := "10110";
constant S23 : STD_LOGIC_VECTOR (4 downto 0) := "10111";
constant S24 : STD_LOGIC_VECTOR (4 downto 0) := "11000";
constant S25 : STD_LOGIC_VECTOR (4 downto 0) := "11001";
constant S26 : STD_LOGIC_VECTOR (4 downto 0) := "11010";

signal st, prox : STD_LOGIC_VECTOR (4 downto 0);

begin

-- Registro de estado
process (clk, rst)
begin
    if rst = '1' then
        st <= S0;
    elsif clk'event and clk = '1' then
        st <= prox;
    end if;
end process;

-- Logica de estado siguiente y de salidas
process (st, inicio, z_dout, i_eq_n, j_eq_n, k1_eq_n, t3_neg, r_ge, sq,
         piv_neg, signo, val_neg, cont_31, dig_gt4, d_9, sel_dif)
begin
    -- Valores por defecto: ninguna operacion, se mantiene el estado
    prox      <= st;
    ld_pag    <= '0';  clr_dira  <= '0';  inc_dira  <= '0';
    we_ram    <= '0';  sel_fila  <= "00"; sel_col   <= "00"; sel_din <= "000";
    ld_n      <= '0';
    ld_i      <= '0';  sel_i     <= "00";
    ld_j      <= '0';  sel_j     <= "00";
    ld_k      <= '0';  sel_k     <= '0';
    ld_piv    <= '0';
    ld_p      <= '0';  sel_p     <= '0';
    ld_pabs   <= '0';  sel_pabs  <= "00";
    clr_signo <= '0';  tog_signo <= '0';
    clr_banco <= '0';  ld_banco  <= '0';
    ld_tmp1   <= '0';  ld_tmp2   <= '0';
    ld_ma     <= '0';  sel_ma    <= '0';  ld_mb     <= '0';
    ld_t1     <= '0';  ld_t2     <= '0';  ld_t3     <= '0';
    ld_r      <= '0';  sel_r     <= '0';  clr_q     <= '0';  inc_q <= '0';  ld_sq <= '0';
    ld_det    <= '0';  sel_det   <= "00";
    sel_sra   <= "00"; sel_srb   <= "000"; op_sr    <= '1';
    ld_selant <= '0';  ld_neg    <= '0';
    ld_bin    <= '0';  sel_bin   <= "00";
    clr_bcd   <= '0';  ins_bcd   <= '0';  aj_bcd    <= '0';  sh_bcd <= '0';
    clr_cont  <= '0';  inc_cont  <= '0';
    clr_d     <= '0';  inc_d     <= '0';
    ld_disp   <= '0';
    final     <= '0';

    case st is

        ------------------------------------------------------------------
        -- Espera y carga de la matriz
        ------------------------------------------------------------------
        when S0 =>                              -- final = 0 ; dira <- 0
            clr_dira <= '1';
            if inicio = '1' then
                ld_pag <= '1';                  -- pag <- sw_mat
                prox   <= S1;
            else
                prox   <= S0;
            end if;

        when S1 =>                              -- n <- ROM(00h) ; dira <- 1 ; i <- 1 ; j <- 1
            ld_n     <= '1';
            inc_dira <= '1';
            ld_i     <= '1';  sel_i <= "00";
            ld_j     <= '1';  sel_j <= "00";
            prox     <= S2;

        when S2 =>                              -- M(i,j) <- ROM(dira) ; dira <- dira + 1
            we_ram   <= '1';  sel_fila <= "00"; sel_col <= "00"; sel_din <= "000";
            inc_dira <= '1';
            if i_eq_n = '1' then
                ld_i <= '1';  sel_i <= "00";    -- i <- 1
                if j_eq_n = '1' then
                    prox <= S3;
                else
                    ld_j <= '1';  sel_j <= "01";-- j <- j + 1
                    prox <= S2;
                end if;
            else
                ld_i <= '1';  sel_i <= "01";    -- i <- i + 1
                prox <= S2;
            end if;

        when S3 =>                              -- k <- 1 ; p <- 1 ; |p| <- 1 ; signo <- 0 ; banco <- 0
            ld_k      <= '1';  sel_k    <= '0';
            ld_p      <= '1';  sel_p    <= '0';
            ld_pabs   <= '1';  sel_pabs <= "00";
            clr_signo <= '1';
            clr_banco <= '1';
            prox      <= S4;

        ------------------------------------------------------------------
        -- Pivote, busqueda de fila e intercambio
        ------------------------------------------------------------------
        when S4 =>                              -- piv <- M(k,k)
            sel_fila <= "01";  sel_col <= "01";
            ld_piv   <= '1';
            if z_dout = '1' then
                ld_i <= '1';  sel_i <= "10";    -- i <- k + 1
                prox <= S5;
            else
                prox <= S10;
            end if;

        when S5 =>                              -- lee M(i,k)
            sel_fila <= "00";  sel_col <= "01";
            if z_dout = '0' then
                ld_j      <= '1';  sel_j <= "11";   -- j <- k
                tog_signo <= '1';                   -- signo <- not signo
                prox      <= S6;
            elsif i_eq_n = '1' then
                ld_det <= '1';  sel_det <= "00";    -- det <- 0 (singular)
                prox   <= S21;
            else
                ld_i <= '1';  sel_i <= "01";        -- i <- i + 1
                prox <= S5;
            end if;

        when S6 =>                              -- tmp1 <- M(k,j)
            sel_fila <= "01";  sel_col <= "00";
            ld_tmp1  <= '1';
            prox     <= S7;

        when S7 =>                              -- tmp2 <- M(i,j)
            sel_fila <= "00";  sel_col <= "00";
            ld_tmp2  <= '1';
            prox     <= S8;

        when S8 =>                              -- M(k,j) <- tmp2
            we_ram   <= '1';  sel_fila <= "01"; sel_col <= "00"; sel_din <= "010";
            prox     <= S9;

        when S9 =>                              -- M(i,j) <- tmp1
            we_ram   <= '1';  sel_fila <= "00"; sel_col <= "00"; sel_din <= "001";
            if j_eq_n = '1' then
                prox <= S4;
            else
                ld_j <= '1';  sel_j <= "01";    -- j <- j + 1
                prox <= S6;
            end if;

        when S10 =>                             -- banco(k) <- piv ; i <- k + 1 ; j <- k + 1
            ld_banco <= '1';
            ld_i     <= '1';  sel_i <= "10";
            ld_j     <= '1';  sel_j <= "10";
            prox     <= S11;

        ------------------------------------------------------------------
        -- a(i,j) = ( a(k,k)*a(i,j) - a(i,k)*a(k,j) ) / p
        ------------------------------------------------------------------
        when S11 =>                             -- mul_a <- piv ; mul_b <- M(i,j)
            sel_fila <= "00";  sel_col <= "00";
            ld_ma    <= '1';  sel_ma <= '0';
            ld_mb    <= '1';
            prox     <= S12;

        when S12 =>                             -- t1 <- mul_a x mul_b ; mul_a <- M(i,k)
            sel_fila <= "00";  sel_col <= "01";
            ld_t1    <= '1';
            ld_ma    <= '1';  sel_ma <= '1';
            prox     <= S13;

        when S13 =>                             -- mul_b <- M(k,j)
            sel_fila <= "01";  sel_col <= "00";
            ld_mb    <= '1';
            prox     <= S14;

        when S14 =>                             -- t2 <- mul_a x mul_b
            ld_t2    <= '1';
            prox     <= S15;

        when S15 =>                             -- t3 <- t1 - t2
            sel_sra  <= "01";  sel_srb <= "000";  op_sr <= '1';
            ld_t3    <= '1';
            prox     <= S16;

        when S16 =>                             -- Q <- 0 ; sq <- signo(t3) xor signo(p) ; R <- |t3|
            sel_sra  <= "00";  sel_srb <= "001";  op_sr <= '1';   -- 0 - t3
            clr_q    <= '1';
            ld_sq    <= '1';
            ld_r     <= '1';
            if t3_neg = '1' then
                sel_r <= '1';                   -- R <- 0 - t3
            else
                sel_r <= '0';                   -- R <- t3
            end if;
            prox     <= S17;

        when S17 =>                             -- division: R - |p|
            sel_sra  <= "10";  sel_srb <= "010";  op_sr <= '1';
            if r_ge = '1' then
                ld_r  <= '1';  sel_r <= '1';    -- R <- R - |p|
                inc_q <= '1';                   -- Q <- Q + 1
                prox  <= S17;
            else
                prox  <= S18;
            end if;

        when S18 =>                             -- M(i,j) <- Q o 0 - Q
            sel_sra  <= "00";  sel_srb <= "011";  op_sr <= '1';   -- 0 - Q
            we_ram   <= '1';  sel_fila <= "00"; sel_col <= "00";
            if sq = '1' then
                sel_din <= "100";               -- M(i,j) <- 0 - Q
            else
                sel_din <= "011";               -- M(i,j) <- Q
            end if;
            if j_eq_n = '1' then
                if i_eq_n = '1' then
                    prox <= S19;
                else
                    ld_i <= '1';  sel_i <= "01";-- i <- i + 1
                    ld_j <= '1';  sel_j <= "10";-- j <- k + 1
                    prox <= S11;
                end if;
            else
                ld_j <= '1';  sel_j <= "01";    -- j <- j + 1
                prox <= S11;
            end if;

        when S19 =>                             -- p <- piv ; |p| <- |piv| ; k <- k + 1
            sel_sra  <= "00";  sel_srb <= "100";  op_sr <= '1';   -- 0 - piv
            ld_p     <= '1';  sel_p <= '1';
            ld_pabs  <= '1';
            if piv_neg = '1' then
                sel_pabs <= "10";               -- |p| <- 0 - piv
            else
                sel_pabs <= "01";               -- |p| <- piv
            end if;
            ld_k     <= '1';  sel_k <= '1';
            if k1_eq_n = '1' then
                prox <= S20;
            else
                prox <= S4;
            end if;

        when S20 =>                             -- det <- M(n,n) o 0 - M(n,n)
            sel_fila <= "10";  sel_col <= "10";
            sel_sra  <= "00";  sel_srb <= "101";  op_sr <= '1';   -- 0 - M(n,n)
            ld_det   <= '1';
            if signo = '1' then
                sel_det <= "10";
            else
                sel_det <= "01";
            end if;
            prox     <= S21;

        ------------------------------------------------------------------
        -- Valor a mostrar y algoritmo XS3
        ------------------------------------------------------------------
        when S21 =>                             -- bin <- |val| ; neg <- signo(val) ; sel_ant <- sw_piv
            sel_sra   <= "00";  sel_srb <= "110";  op_sr <= '1';  -- 0 - val
            ld_selant <= '1';
            ld_neg    <= '1';
            ld_bin    <= '1';
            if val_neg = '1' then
                sel_bin <= "01";                -- bin <- 0 - val
            else
                sel_bin <= "00";                -- bin <- val
            end if;
            prox      <= S22;

        when S22 =>                             -- XS3 paso 1: BCD <- 0 ; cont <- 0
            clr_bcd  <= '1';
            clr_cont <= '1';
            prox     <= S23;

        when S23 =>                             -- XS3 paso 2: BCD(0) <- bin(31)
            ins_bcd  <= '1';
            if cont_31 = '1' then
                prox <= S26;                    -- paso 5: ultimo paso 2
            else
                clr_d <= '1';                   -- d <- 0
                prox  <= S24;
            end if;

        when S24 =>                             -- XS3 paso 3: si BCD(d) > 4, BCD(d) <- BCD(d) + 3
            sel_sra  <= "11";  sel_srb <= "111";  op_sr <= '0';   -- digito + 3
            if dig_gt4 = '1' then
                aj_bcd <= '1';
            end if;
            if d_9 = '1' then
                prox <= S25;
            else
                inc_d <= '1';                   -- d <- d + 1
                prox  <= S24;
            end if;

        when S25 =>                             -- XS3 paso 4: BCD << 1 ; bin << 1 ; cont <- cont + 1
            sh_bcd   <= '1';
            ld_bin   <= '1';  sel_bin <= "10";
            inc_cont <= '1';
            prox     <= S23;

        when S26 =>                             -- final = 1 ; display <- BCD ; dira <- 0
            final    <= '1';
            ld_disp  <= '1';
            clr_dira <= '1';
            if inicio = '1' then
                ld_pag <= '1';                  -- pag <- sw_mat
                prox   <= S1;
            elsif sel_dif = '1' then
                prox   <= S21;                  -- cambiaron los switches
            else
                prox   <= S26;
            end if;

        when others =>
            prox <= S0;

    end case;
end process;

end RTL;


----------------------------------------------------------------------------------
-- PROCESADOR: unidad de control + camino de datos (descripcion estructural)
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity procesador is
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           sw_mat   : in  STD_LOGIC_VECTOR (2 downto 0);
           sw_piv   : in  STD_LOGIC_VECTOR (2 downto 0);
           final    : out STD_LOGIC;
           disp_bcd : out STD_LOGIC_VECTOR (27 downto 0);
           disp_neg : out STD_LOGIC;
           desborde : out STD_LOGIC);
end procesador;

architecture Estructural of procesador is

component unidad_control
    Port ( clk, rst  : in  STD_LOGIC;
           inicio    : in  STD_LOGIC;
           z_dout, i_eq_n, j_eq_n, k1_eq_n      : in STD_LOGIC;
           t3_neg, r_ge, sq, piv_neg            : in STD_LOGIC;
           signo, val_neg                       : in STD_LOGIC;
           cont_31, dig_gt4, d_9, sel_dif       : in STD_LOGIC;
           ld_pag, clr_dira, inc_dira : out STD_LOGIC;
           we_ram    : out STD_LOGIC;
           sel_fila  : out STD_LOGIC_VECTOR (1 downto 0);
           sel_col   : out STD_LOGIC_VECTOR (1 downto 0);
           sel_din   : out STD_LOGIC_VECTOR (2 downto 0);
           ld_n      : out STD_LOGIC;
           ld_i      : out STD_LOGIC;
           sel_i     : out STD_LOGIC_VECTOR (1 downto 0);
           ld_j      : out STD_LOGIC;
           sel_j     : out STD_LOGIC_VECTOR (1 downto 0);
           ld_k, sel_k            : out STD_LOGIC;
           ld_piv                 : out STD_LOGIC;
           ld_p, sel_p            : out STD_LOGIC;
           ld_pabs   : out STD_LOGIC;
           sel_pabs  : out STD_LOGIC_VECTOR (1 downto 0);
           clr_signo, tog_signo   : out STD_LOGIC;
           clr_banco, ld_banco    : out STD_LOGIC;
           ld_tmp1, ld_tmp2       : out STD_LOGIC;
           ld_ma, sel_ma, ld_mb   : out STD_LOGIC;
           ld_t1, ld_t2, ld_t3    : out STD_LOGIC;
           ld_r, sel_r, clr_q, inc_q, ld_sq : out STD_LOGIC;
           ld_det    : out STD_LOGIC;
           sel_det   : out STD_LOGIC_VECTOR (1 downto 0);
           sel_sra   : out STD_LOGIC_VECTOR (1 downto 0);
           sel_srb   : out STD_LOGIC_VECTOR (2 downto 0);
           op_sr     : out STD_LOGIC;
           ld_selant, ld_neg      : out STD_LOGIC;
           ld_bin    : out STD_LOGIC;
           sel_bin   : out STD_LOGIC_VECTOR (1 downto 0);
           clr_bcd, ins_bcd, aj_bcd, sh_bcd : out STD_LOGIC;
           clr_cont, inc_cont     : out STD_LOGIC;
           clr_d, inc_d           : out STD_LOGIC;
           ld_disp                : out STD_LOGIC;
           final                  : out STD_LOGIC);
end component;

component camino_datos
    Port ( clk, rst  : in  STD_LOGIC;
           sw_mat    : in  STD_LOGIC_VECTOR (2 downto 0);
           sw_piv    : in  STD_LOGIC_VECTOR (2 downto 0);
           ld_pag, clr_dira, inc_dira : in STD_LOGIC;
           we_ram    : in  STD_LOGIC;
           sel_fila  : in  STD_LOGIC_VECTOR (1 downto 0);
           sel_col   : in  STD_LOGIC_VECTOR (1 downto 0);
           sel_din   : in  STD_LOGIC_VECTOR (2 downto 0);
           ld_n      : in  STD_LOGIC;
           ld_i      : in  STD_LOGIC;
           sel_i     : in  STD_LOGIC_VECTOR (1 downto 0);
           ld_j      : in  STD_LOGIC;
           sel_j     : in  STD_LOGIC_VECTOR (1 downto 0);
           ld_k, sel_k            : in STD_LOGIC;
           ld_piv                 : in STD_LOGIC;
           ld_p, sel_p            : in STD_LOGIC;
           ld_pabs   : in  STD_LOGIC;
           sel_pabs  : in  STD_LOGIC_VECTOR (1 downto 0);
           clr_signo, tog_signo   : in STD_LOGIC;
           clr_banco, ld_banco    : in STD_LOGIC;
           ld_tmp1, ld_tmp2       : in STD_LOGIC;
           ld_ma, sel_ma, ld_mb   : in STD_LOGIC;
           ld_t1, ld_t2, ld_t3    : in STD_LOGIC;
           ld_r, sel_r, clr_q, inc_q, ld_sq : in STD_LOGIC;
           ld_det    : in  STD_LOGIC;
           sel_det   : in  STD_LOGIC_VECTOR (1 downto 0);
           sel_sra   : in  STD_LOGIC_VECTOR (1 downto 0);
           sel_srb   : in  STD_LOGIC_VECTOR (2 downto 0);
           op_sr     : in  STD_LOGIC;
           ld_selant, ld_neg      : in STD_LOGIC;
           ld_bin    : in  STD_LOGIC;
           sel_bin   : in  STD_LOGIC_VECTOR (1 downto 0);
           clr_bcd, ins_bcd, aj_bcd, sh_bcd : in STD_LOGIC;
           clr_cont, inc_cont     : in STD_LOGIC;
           clr_d, inc_d           : in STD_LOGIC;
           ld_disp                : in STD_LOGIC;
           z_dout, i_eq_n, j_eq_n, k1_eq_n      : out STD_LOGIC;
           t3_neg, r_ge, sq, piv_neg            : out STD_LOGIC;
           signo, val_neg                       : out STD_LOGIC;
           cont_31, dig_gt4, d_9, sel_dif       : out STD_LOGIC;
           disp_bcd  : out STD_LOGIC_VECTOR (27 downto 0);
           disp_neg  : out STD_LOGIC;
           desborde  : out STD_LOGIC);
end component;

-- Senales de estado
signal z_dout, i_eq_n, j_eq_n, k1_eq_n : STD_LOGIC;
signal t3_neg, r_ge, sq, piv_neg       : STD_LOGIC;
signal signo, val_neg                  : STD_LOGIC;
signal cont_31, dig_gt4, d_9, sel_dif  : STD_LOGIC;

-- Senales de control
signal ld_pag, clr_dira, inc_dira : STD_LOGIC;
signal we_ram    : STD_LOGIC;
signal sel_fila  : STD_LOGIC_VECTOR (1 downto 0);
signal sel_col   : STD_LOGIC_VECTOR (1 downto 0);
signal sel_din   : STD_LOGIC_VECTOR (2 downto 0);
signal ld_n      : STD_LOGIC;
signal ld_i      : STD_LOGIC;
signal sel_i     : STD_LOGIC_VECTOR (1 downto 0);
signal ld_j      : STD_LOGIC;
signal sel_j     : STD_LOGIC_VECTOR (1 downto 0);
signal ld_k, sel_k            : STD_LOGIC;
signal ld_piv                 : STD_LOGIC;
signal ld_p, sel_p            : STD_LOGIC;
signal ld_pabs   : STD_LOGIC;
signal sel_pabs  : STD_LOGIC_VECTOR (1 downto 0);
signal clr_signo, tog_signo   : STD_LOGIC;
signal clr_banco, ld_banco    : STD_LOGIC;
signal ld_tmp1, ld_tmp2       : STD_LOGIC;
signal ld_ma, sel_ma, ld_mb   : STD_LOGIC;
signal ld_t1, ld_t2, ld_t3    : STD_LOGIC;
signal ld_r, sel_r, clr_q, inc_q, ld_sq : STD_LOGIC;
signal ld_det    : STD_LOGIC;
signal sel_det   : STD_LOGIC_VECTOR (1 downto 0);
signal sel_sra   : STD_LOGIC_VECTOR (1 downto 0);
signal sel_srb   : STD_LOGIC_VECTOR (2 downto 0);
signal op_sr     : STD_LOGIC;
signal ld_selant, ld_neg      : STD_LOGIC;
signal ld_bin    : STD_LOGIC;
signal sel_bin   : STD_LOGIC_VECTOR (1 downto 0);
signal clr_bcd, ins_bcd, aj_bcd, sh_bcd : STD_LOGIC;
signal clr_cont, inc_cont     : STD_LOGIC;
signal clr_d, inc_d           : STD_LOGIC;
signal ld_disp                : STD_LOGIC;

begin

U_UC : unidad_control port map (
    clk => clk, rst => rst, inicio => inicio,
    z_dout => z_dout, i_eq_n => i_eq_n, j_eq_n => j_eq_n, k1_eq_n => k1_eq_n,
    t3_neg => t3_neg, r_ge => r_ge, sq => sq, piv_neg => piv_neg,
    signo => signo, val_neg => val_neg,
    cont_31 => cont_31, dig_gt4 => dig_gt4, d_9 => d_9, sel_dif => sel_dif,
    ld_pag => ld_pag, clr_dira => clr_dira, inc_dira => inc_dira,
    we_ram => we_ram, sel_fila => sel_fila, sel_col => sel_col, sel_din => sel_din,
    ld_n => ld_n, ld_i => ld_i, sel_i => sel_i, ld_j => ld_j, sel_j => sel_j,
    ld_k => ld_k, sel_k => sel_k, ld_piv => ld_piv, ld_p => ld_p, sel_p => sel_p,
    ld_pabs => ld_pabs, sel_pabs => sel_pabs,
    clr_signo => clr_signo, tog_signo => tog_signo,
    clr_banco => clr_banco, ld_banco => ld_banco,
    ld_tmp1 => ld_tmp1, ld_tmp2 => ld_tmp2,
    ld_ma => ld_ma, sel_ma => sel_ma, ld_mb => ld_mb,
    ld_t1 => ld_t1, ld_t2 => ld_t2, ld_t3 => ld_t3,
    ld_r => ld_r, sel_r => sel_r, clr_q => clr_q, inc_q => inc_q, ld_sq => ld_sq,
    ld_det => ld_det, sel_det => sel_det,
    sel_sra => sel_sra, sel_srb => sel_srb, op_sr => op_sr,
    ld_selant => ld_selant, ld_neg => ld_neg, ld_bin => ld_bin, sel_bin => sel_bin,
    clr_bcd => clr_bcd, ins_bcd => ins_bcd, aj_bcd => aj_bcd, sh_bcd => sh_bcd,
    clr_cont => clr_cont, inc_cont => inc_cont, clr_d => clr_d, inc_d => inc_d,
    ld_disp => ld_disp, final => final);

U_CD : camino_datos port map (
    clk => clk, rst => rst, sw_mat => sw_mat, sw_piv => sw_piv,
    ld_pag => ld_pag, clr_dira => clr_dira, inc_dira => inc_dira,
    we_ram => we_ram, sel_fila => sel_fila, sel_col => sel_col, sel_din => sel_din,
    ld_n => ld_n, ld_i => ld_i, sel_i => sel_i, ld_j => ld_j, sel_j => sel_j,
    ld_k => ld_k, sel_k => sel_k, ld_piv => ld_piv, ld_p => ld_p, sel_p => sel_p,
    ld_pabs => ld_pabs, sel_pabs => sel_pabs,
    clr_signo => clr_signo, tog_signo => tog_signo,
    clr_banco => clr_banco, ld_banco => ld_banco,
    ld_tmp1 => ld_tmp1, ld_tmp2 => ld_tmp2,
    ld_ma => ld_ma, sel_ma => sel_ma, ld_mb => ld_mb,
    ld_t1 => ld_t1, ld_t2 => ld_t2, ld_t3 => ld_t3,
    ld_r => ld_r, sel_r => sel_r, clr_q => clr_q, inc_q => inc_q, ld_sq => ld_sq,
    ld_det => ld_det, sel_det => sel_det,
    sel_sra => sel_sra, sel_srb => sel_srb, op_sr => op_sr,
    ld_selant => ld_selant, ld_neg => ld_neg, ld_bin => ld_bin, sel_bin => sel_bin,
    clr_bcd => clr_bcd, ins_bcd => ins_bcd, aj_bcd => aj_bcd, sh_bcd => sh_bcd,
    clr_cont => clr_cont, inc_cont => inc_cont, clr_d => clr_d, inc_d => inc_d,
    ld_disp => ld_disp,
    z_dout => z_dout, i_eq_n => i_eq_n, j_eq_n => j_eq_n, k1_eq_n => k1_eq_n,
    t3_neg => t3_neg, r_ge => r_ge, sq => sq, piv_neg => piv_neg,
    signo => signo, val_neg => val_neg,
    cont_31 => cont_31, dig_gt4 => dig_gt4, d_9 => d_9, sel_dif => sel_dif,
    disp_bcd => disp_bcd, disp_neg => disp_neg, desborde => desborde);

end Estructural;


----------------------------------------------------------------------------------
-- SINCRONIZADOR: dos flip-flops para el boton y los switches
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity sincronizador is
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           sw_mat   : in  STD_LOGIC_VECTOR (2 downto 0);
           sw_piv   : in  STD_LOGIC_VECTOR (2 downto 0);
           inicio_s : out STD_LOGIC;
           sw_mat_s : out STD_LOGIC_VECTOR (2 downto 0);
           sw_piv_s : out STD_LOGIC_VECTOR (2 downto 0));
end sincronizador;

architecture RTL of sincronizador is
signal ini_1, ini_2 : STD_LOGIC;
signal mat_1, mat_2, piv_1, piv_2 : STD_LOGIC_VECTOR (2 downto 0);
begin

process (clk, rst)
begin
    if rst = '1' then
        ini_1 <= '0';    ini_2 <= '0';
        mat_1 <= "000";  mat_2 <= "000";
        piv_1 <= "000";  piv_2 <= "000";
    elsif clk'event and clk = '1' then
        ini_1 <= inicio;  ini_2 <= ini_1;
        mat_1 <= sw_mat;  mat_2 <= mat_1;
        piv_1 <= sw_piv;  piv_2 <= piv_1;
    end if;
end process;

inicio_s <= ini_2;
sw_mat_s <= mat_2;
sw_piv_s <= piv_2;

end RTL;


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

architecture RTL of display_8dig is
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

end RTL;


----------------------------------------------------------------------------------
-- TOPE: det_bareiss (descripcion estructural)
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity det_bareiss is
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;                      -- BTNC
           sw_mat   : in  STD_LOGIC_VECTOR (2 downto 0);  -- SW15..SW13: matriz (pagina de la ROM)
           sw_piv   : in  STD_LOGIC_VECTOR (2 downto 0);  -- SW2..SW0 : 0 = det, 1..4 = pivote k
           final    : out STD_LOGIC;                      -- LD0
           desborde : out STD_LOGIC;                      -- LD1: |valor| > 9 999 999
           an       : out STD_LOGIC_VECTOR (7 downto 0);
           seg      : out STD_LOGIC_VECTOR (6 downto 0);
           dp       : out STD_LOGIC);
end det_bareiss;

architecture Estructural of det_bareiss is

component sincronizador
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           sw_mat   : in  STD_LOGIC_VECTOR (2 downto 0);
           sw_piv   : in  STD_LOGIC_VECTOR (2 downto 0);
           inicio_s : out STD_LOGIC;
           sw_mat_s : out STD_LOGIC_VECTOR (2 downto 0);
           sw_piv_s : out STD_LOGIC_VECTOR (2 downto 0));
end component;

component procesador
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           sw_mat   : in  STD_LOGIC_VECTOR (2 downto 0);
           sw_piv   : in  STD_LOGIC_VECTOR (2 downto 0);
           final    : out STD_LOGIC;
           disp_bcd : out STD_LOGIC_VECTOR (27 downto 0);
           disp_neg : out STD_LOGIC;
           desborde : out STD_LOGIC);
end component;

component display_8dig
    Port ( clk, rst : in  STD_LOGIC;
           bcd      : in  STD_LOGIC_VECTOR (27 downto 0);
           neg      : in  STD_LOGIC;
           an       : out STD_LOGIC_VECTOR (7 downto 0);
           seg      : out STD_LOGIC_VECTOR (6 downto 0);
           dp       : out STD_LOGIC);
end component;

signal inicio_s : STD_LOGIC;
signal sw_mat_s, sw_piv_s : STD_LOGIC_VECTOR (2 downto 0);
signal disp_bcd : STD_LOGIC_VECTOR (27 downto 0);
signal disp_neg : STD_LOGIC;

begin

U_SINC : sincronizador port map (
    clk => clk, rst => rst, inicio => inicio, sw_mat => sw_mat, sw_piv => sw_piv,
    inicio_s => inicio_s, sw_mat_s => sw_mat_s, sw_piv_s => sw_piv_s);

U_PROC : procesador port map (
    clk => clk, rst => rst, inicio => inicio_s, sw_mat => sw_mat_s, sw_piv => sw_piv_s,
    final => final, disp_bcd => disp_bcd, disp_neg => disp_neg, desborde => desborde);

U_DISP : display_8dig port map (
    clk => clk, rst => rst, bcd => disp_bcd, neg => disp_neg,
    an => an, seg => seg, dp => dp);

end Estructural;

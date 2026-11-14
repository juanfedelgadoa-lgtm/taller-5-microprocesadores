----------------------------------------------------------------------------------
-- Universidad Distrital Francisco Jose de Caldas
-- Analisis y Diseno de Microprocesadores - Taller 5
--
-- PROCESADOR DE BAREISS (determinante de una matriz de 2x2 a 5x5)
--
-- Caja negra (entidad procesador_bareiss, al final del archivo):
--   entradas : clk, rst, inicio, dir_p (3 bits)
--   salidas  : det (32 bits), pivote (32 bits), final
--   det y pivote salen en binario (complemento a 2). La conversion a decimal
--   (algoritmo XS3) la hace el visualizador, que es otro bloque.
--
-- Bloques de este archivo (de abajo hacia arriba):
--   rom_matriz        ROM con la matriz (n y los elementos por columnas)
--   RAM_memory        RAM del curso (modelo del profesor, sin cambios); hay dos
--   dir_ram           decodificador fila, columna -> direccion de la RAM
--   multiplicador     unidad funcional 1: multiplicador 25 x 25 con signo
--   sumador_restador  unidad funcional 2: sumador/restador de 50 bits
--   banco_pivotes     registros donde quedan los pivotes y el determinante
--   asm_bareiss       ASM del algoritmo de Bareiss (unidad de control)
--   procesador_bareiss  une los bloques (descripcion estructural)
--
-- Solo se usan std_logic y std_logic_vector. La unica excepcion es el arreglo
-- de la RAM, que es el modelo del profesor.
----------------------------------------------------------------------------------


-- >>> INICIO ROM (generado con: python3 sim/modelo_referencia.py rom ...)
----------------------------------------------------------------------------------
-- ROM DE LA MATRIZ (32 x 6 bits, lectura combinacional)
--
-- Hace parte de la arquitectura del procesador: para calcular el determinante
-- de otra matriz se cambia este bloque y se vuelve a programar la FPGA.
--
-- Posicion 00h = n; luego los elementos a(i,j) por columnas (a11, a21, ...),
-- como en la Figura 1 del taller. Datos en complemento a 2 (-32 a 31).
--
-- Matriz (5x5):
--      4   -2    1    3    0
--     -2    6    2   -1    5
--      1    2   -7    4    2
--      3   -1    4    5   -3
--      0    5    2   -3    8
-- Resultado esperado: det = 362
-- Pivotes (dir_p = 1..5): 4, 20, -170, -639, 362
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
    a <= "000101" when "00000",   -- 00h: n = 5
         "000100" when "00001",   -- 01h: a11 = 4
         "111110" when "00010",   -- 02h: a21 = -2
         "000001" when "00011",   -- 03h: a31 = 1
         "000011" when "00100",   -- 04h: a41 = 3
         "000000" when "00101",   -- 05h: a51 = 0
         "111110" when "00110",   -- 06h: a12 = -2
         "000110" when "00111",   -- 07h: a22 = 6
         "000010" when "01000",   -- 08h: a32 = 2
         "111111" when "01001",   -- 09h: a42 = -1
         "000101" when "01010",   -- 0Ah: a52 = 5
         "000001" when "01011",   -- 0Bh: a13 = 1
         "000010" when "01100",   -- 0Ch: a23 = 2
         "111001" when "01101",   -- 0Dh: a33 = -7
         "000100" when "01110",   -- 0Eh: a43 = 4
         "000010" when "01111",   -- 0Fh: a53 = 2
         "000011" when "10000",   -- 10h: a14 = 3
         "111111" when "10001",   -- 11h: a24 = -1
         "000100" when "10010",   -- 12h: a34 = 4
         "000101" when "10011",   -- 13h: a44 = 5
         "111101" when "10100",   -- 14h: a54 = -3
         "000000" when "10101",   -- 15h: a15 = 0
         "000101" when "10110",   -- 16h: a25 = 5
         "000010" when "10111",   -- 17h: a35 = 2
         "111101" when "11000",   -- 18h: a45 = -3
         "001000" when "11001",   -- 19h: a55 = 8
         "000000" when others;

end Behavioral;
-- <<< FIN ROM


----------------------------------------------------------------------------------
-- RAM DEL CURSO (modelo del profesor: 32 palabras de 32 bits)
-- Escritura sincrona por wr_add; lectura asincrona por rd_add.
-- El procesador usa dos de estas RAM (A y B) con el mismo contenido: se
-- escriben al mismo tiempo y cada una se lee por su propia direccion, asi se
-- leen dos elementos de la matriz en el mismo ciclo.
----------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;

entity RAM_memory is
   port
   (
      c      : in  std_logic;
      data   : in  std_logic_vector (31 downto 0);
      wr_add : in  std_logic_vector (4 downto 0);
      rd_add : in  std_logic_vector (4 downto 0);
      we     : in  std_logic;
      q      : out std_logic_vector (31 downto 0)
   );
end RAM_memory;

architecture rtl of RAM_memory is
   type mem is array(0 to 31) of std_logic_vector(31 downto 0);
   signal ram_blk : mem;
begin

   process (c, data, wr_add, rd_add, ram_blk)
   begin
      if (c'event and c = '1') then
         if (we = '1') then
            ram_blk(conv_integer(wr_add)) <= data;
         end if;
      end if;
   end process;

   q <= ram_blk(conv_integer(rd_add));

end rtl;


----------------------------------------------------------------------------------
-- DECODIFICADOR DE DIRECCION DE LA RAM (combinacional)
-- a(fila, col) se guarda en la direccion 5*(fila-1) + (col-1), de 0 a 24.
-- Es una tabla: no usa multiplicador ni sumador. Hay tres: lectura A,
-- lectura B y escritura.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity dir_ram is
    Port ( fila : in  STD_LOGIC_VECTOR (2 downto 0);
           col  : in  STD_LOGIC_VECTOR (2 downto 0);
           dir  : out STD_LOGIC_VECTOR (4 downto 0));
end dir_ram;

architecture Behavioral of dir_ram is

signal fc : STD_LOGIC_VECTOR (5 downto 0);

begin

fc <= fila & col;

with fc select
    dir <= "00000" when "001001",   -- a(1,1) ->  0
           "00001" when "001010",   -- a(1,2) ->  1
           "00010" when "001011",   -- a(1,3) ->  2
           "00011" when "001100",   -- a(1,4) ->  3
           "00100" when "001101",   -- a(1,5) ->  4
           "00101" when "010001",   -- a(2,1) ->  5
           "00110" when "010010",   -- a(2,2) ->  6
           "00111" when "010011",   -- a(2,3) ->  7
           "01000" when "010100",   -- a(2,4) ->  8
           "01001" when "010101",   -- a(2,5) ->  9
           "01010" when "011001",   -- a(3,1) -> 10
           "01011" when "011010",   -- a(3,2) -> 11
           "01100" when "011011",   -- a(3,3) -> 12
           "01101" when "011100",   -- a(3,4) -> 13
           "01110" when "011101",   -- a(3,5) -> 14
           "01111" when "100001",   -- a(4,1) -> 15
           "10000" when "100010",   -- a(4,2) -> 16
           "10001" when "100011",   -- a(4,3) -> 17
           "10010" when "100100",   -- a(4,4) -> 18
           "10011" when "100101",   -- a(4,5) -> 19
           "10100" when "101001",   -- a(5,1) -> 20
           "10101" when "101010",   -- a(5,2) -> 21
           "10110" when "101011",   -- a(5,3) -> 22
           "10111" when "101100",   -- a(5,4) -> 23
           "11000" when "101101",   -- a(5,5) -> 24
           "11111" when others;     -- no se usa

end Behavioral;


----------------------------------------------------------------------------------
-- UNIDAD FUNCIONAL 1: MULTIPLICADOR CON SIGNO 25 x 25 -> 50 bits (combinacional)
-- El paquete std_logic_signed hace que "*" tome los std_logic_vector en
-- complemento a 2. 25 bits alcanzan: en el paso k los operandos son
-- determinantes de submatrices de k x k (k <= 4), menores que 2^24.
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
-- UNIDAD FUNCIONAL 2: SUMADOR/RESTADOR DE 50 bits (combinacional)
--   op = '0' : s = a + b
--   op = '1' : s = a - b = a + (not b) + 1
-- Es un solo sumador: op invierte b (compuertas XOR) y entra como acarreo.
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

signal op50 : STD_LOGIC_VECTOR (49 downto 0);
signal bx   : STD_LOGIC_VECTOR (49 downto 0);

begin

op50 <= (others => op);
bx   <= b xor op50;
s    <= a + bx + op;

end Behavioral;


----------------------------------------------------------------------------------
-- BANCO DE PIVOTES (5 registros de 32 bits)
-- Registro k = pivote a(k,k) del paso k (k = 1..n-1); registro n = det.
-- Escritura sincrona en dir_w; lectura combinacional en dir_r (= dir_p).
-- Las direcciones 0, 6 y 7 leen 0.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity banco_pivotes is
    Port ( clk, rst : in  STD_LOGIC;
           clr      : in  STD_LOGIC;                      -- borra los 5 registros
           we       : in  STD_LOGIC;
           dir_w    : in  STD_LOGIC_VECTOR (2 downto 0);
           dato     : in  STD_LOGIC_VECTOR (31 downto 0);
           dir_r    : in  STD_LOGIC_VECTOR (2 downto 0);
           q        : out STD_LOGIC_VECTOR (31 downto 0));
end banco_pivotes;

architecture Behavioral of banco_pivotes is

constant CERO32 : STD_LOGIC_VECTOR (31 downto 0) := x"00000000";

signal p1, p2, p3, p4, p5 : STD_LOGIC_VECTOR (31 downto 0);

begin

process (clk, rst)
begin
if rst = '1' then
    p1 <= CERO32;  p2 <= CERO32;  p3 <= CERO32;  p4 <= CERO32;  p5 <= CERO32;
elsif clk'event and clk = '1' then
    if clr = '1' then
        p1 <= CERO32;  p2 <= CERO32;  p3 <= CERO32;  p4 <= CERO32;  p5 <= CERO32;
    elsif we = '1' then
        case dir_w is
            when "001"  => p1 <= dato;
            when "010"  => p2 <= dato;
            when "011"  => p3 <= dato;
            when "100"  => p4 <= dato;
            when "101"  => p5 <= dato;
            when others => null;
        end case;
    end if;
end if;
end process;

with dir_r select
    q <= p1     when "001",
         p2     when "010",
         p3     when "011",
         p4     when "100",
         p5     when "101",
         CERO32 when others;

end Behavioral;


----------------------------------------------------------------------------------
-- ASM DE BAREISS (unidad de control y registros del algoritmo)
--
-- Un "when" por estado del diagrama ASM; las cajas de decision son "if" y las
-- salidas condicionales son las asignaciones dentro de cada "if".
-- Las unicas unidades funcionales son el multiplicador y el sumador/restador,
-- que estan fuera de este bloque: el ASM les entrega los operandos y la
-- operacion (op) y guarda el resultado en sus registros.
-- Los contadores (dira, i, j, k, cociente) tienen su propio "+1", como el
-- i = i + 1 del ejemplo Sumax del curso.
--
-- Estados:
--   s0        espera de inicio
--   s1, s2    lee n y copia la matriz de la ROM a las RAM
--   s3        inicializacion (k = 1, p = 1, signo = 0, banco = 0)
--   s4        lee el pivote a(k,k)
--   s5        busca una fila i > k con a(i,k) /= 0 (pivote cero)
--   s6, s7    intercambia las filas k e i (columna j)
--   s8        banco(k) = pivote ; i = j = k + 1
--   s9..s11   t1 = a(k,k)*a(i,j) ; t2 = a(i,k)*a(k,j)   (multiplicador)
--   s12       t3 = t1 - t2                              (sumador/restador)
--   s13, s14  division por restas sucesivas |t3| / |p|  (sumador/restador)
--   s15       a(i,j) = +/- cociente ; avanza j, i
--   s16       p = a(k,k) ; |p| ; k = k + 1
--   s17       det = +/- a(n,n) ; banco(n) = det
--   s18       final = 1
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity asm_bareiss is
    Port ( clk, rst   : in  STD_LOGIC;
           inicio     : in  STD_LOGIC;
           -- ROM
           dira       : out STD_LOGIC_VECTOR (4 downto 0);
           a          : in  STD_LOGIC_VECTOR (5 downto 0);
           -- RAM A y B: fila y columna de cada direccion
           fila_ra    : out STD_LOGIC_VECTOR (2 downto 0);
           col_ra     : out STD_LOGIC_VECTOR (2 downto 0);
           fila_rb    : out STD_LOGIC_VECTOR (2 downto 0);
           col_rb     : out STD_LOGIC_VECTOR (2 downto 0);
           fila_w     : out STD_LOGIC_VECTOR (2 downto 0);
           col_w      : out STD_LOGIC_VECTOR (2 downto 0);
           we         : out STD_LOGIC;
           data       : out STD_LOGIC_VECTOR (31 downto 0);
           qa         : in  STD_LOGIC_VECTOR (31 downto 0);
           qb         : in  STD_LOGIC_VECTOR (31 downto 0);
           -- multiplicador
           mul_a      : out STD_LOGIC_VECTOR (24 downto 0);
           mul_b      : out STD_LOGIC_VECTOR (24 downto 0);
           producto   : in  STD_LOGIC_VECTOR (49 downto 0);
           -- sumador/restador
           sr_a       : out STD_LOGIC_VECTOR (49 downto 0);
           sr_b       : out STD_LOGIC_VECTOR (49 downto 0);
           op         : out STD_LOGIC;
           resultado  : in  STD_LOGIC_VECTOR (49 downto 0);
           -- banco de pivotes
           clr_banco  : out STD_LOGIC;
           we_banco   : out STD_LOGIC;
           dir_banco  : out STD_LOGIC_VECTOR (2 downto 0);
           dato_banco : out STD_LOGIC_VECTOR (31 downto 0);
           -- salidas
           det        : out STD_LOGIC_VECTOR (31 downto 0);
           final      : out STD_LOGIC);
end asm_bareiss;

architecture Behavioral of asm_bareiss is

------------------------------------------------------------------------------
-- Estados
------------------------------------------------------------------------------
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

signal st : STD_LOGIC_VECTOR (4 downto 0);

------------------------------------------------------------------------------
-- Constantes
------------------------------------------------------------------------------
constant UNO3   : STD_LOGIC_VECTOR (2 downto 0)  := "001";
constant CERO18 : STD_LOGIC_VECTOR (17 downto 0) := "000000000000000000";
constant CERO25 : STD_LOGIC_VECTOR (24 downto 0) := "0000000000000000000000000";
constant CERO32 : STD_LOGIC_VECTOR (31 downto 0) := x"00000000";
constant UNO32  : STD_LOGIC_VECTOR (31 downto 0) := x"00000001";
constant CERO50 : STD_LOGIC_VECTOR (49 downto 0) := "00000000000000000000000000000000000000000000000000";

------------------------------------------------------------------------------
-- Registros
------------------------------------------------------------------------------
signal dira_r     : STD_LOGIC_VECTOR (4 downto 0);   -- direccion de la ROM
signal n, i, j, k : STD_LOGIC_VECTOR (2 downto 0);   -- tamano y contadores
signal piv        : STD_LOGIC_VECTOR (31 downto 0);  -- pivote actual a(k,k)
signal p          : STD_LOGIC_VECTOR (31 downto 0);  -- pivote anterior
signal pabs       : STD_LOGIC_VECTOR (31 downto 0);  -- |p| (divisor)
signal signo      : STD_LOGIC;                       -- paridad de intercambios
signal tmp        : STD_LOGIC_VECTOR (31 downto 0);  -- intercambio de filas
signal mul_a_r, mul_b_r : STD_LOGIC_VECTOR (24 downto 0);
signal t1, t2, t3 : STD_LOGIC_VECTOR (49 downto 0);  -- productos y numerador
signal residuo    : STD_LOGIC_VECTOR (49 downto 0);  -- division: residuo
signal cociente   : STD_LOGIC_VECTOR (31 downto 0);  -- division: cociente
signal sq         : STD_LOGIC;                       -- signo del cociente
signal det_r      : STD_LOGIC_VECTOR (31 downto 0);  -- determinante

------------------------------------------------------------------------------
-- Senales combinacionales
------------------------------------------------------------------------------
signal dira_mas1  : STD_LOGIC_VECTOR (4 downto 0);
signal i_mas1, j_mas1, k_mas1 : STD_LOGIC_VECTOR (2 downto 0);
signal cociente_mas1 : STD_LOGIC_VECTOR (31 downto 0);
signal ext_a      : STD_LOGIC_VECTOR (25 downto 0);  -- extensiones de signo
signal a32        : STD_LOGIC_VECTOR (31 downto 0);
signal sx_piv, sx_qa : STD_LOGIC_VECTOR (17 downto 0);
signal det_nn     : STD_LOGIC_VECTOR (31 downto 0);  -- +/- a(n,n)

begin

------------------------------------------------------------------------------
-- Contadores y extensiones de signo
------------------------------------------------------------------------------
dira_mas1     <= dira_r + '1';
i_mas1        <= i + '1';
j_mas1        <= j + '1';
k_mas1        <= k + '1';
cociente_mas1 <= cociente + '1';

ext_a  <= (others => a(5));
a32    <= ext_a & a;
sx_piv <= (others => piv(31));
sx_qa  <= (others => qa(31));

------------------------------------------------------------------------------
-- ROM y RAM
------------------------------------------------------------------------------
dira <= dira_r;

fila_ra <= k when (st = s4 or st = s6) else                -- a(k,k), a(k,j)
           n when st = s17 else                            -- a(n,n)
           i;                                              -- a(i,k), a(i,j)
col_ra  <= k when (st = s4 or st = s5 or st = s10) else    -- a(k,k), a(i,k)
           n when st = s17 else
           j;
fila_rb <= k when st = s10 else i;                         -- a(k,j) ; a(i,j)
col_rb  <= j;

fila_w  <= k when st = s7 else i;                          -- a(k,j) en s7
col_w   <= j;

we   <= '1' when (st = s2 or st = s6 or st = s7 or st = s15) else '0';

data <= a32                    when st = s2 else           -- copia de la ROM
        qa                     when st = s6 else           -- a(i,j) = a(k,j)
        tmp                    when st = s7 else           -- a(k,j) = a(i,j) anterior
        resultado(31 downto 0) when sq = '1' else          -- s15: -cociente
        cociente;                                          -- s15: +cociente

------------------------------------------------------------------------------
-- Multiplicador
------------------------------------------------------------------------------
mul_a <= mul_a_r;
mul_b <= mul_b_r;

------------------------------------------------------------------------------
-- Sumador/restador: operandos segun el estado (siempre resta, op = 1)
------------------------------------------------------------------------------
sr_a <= t1      when st = s12 else                         -- t1 - t2
        residuo when st = s14 else                         -- residuo - |p|
        CERO50;                                            -- 0 - x
sr_b <= t2                when st = s12 else
        t3                when st = s13 else               -- 0 - t3
        CERO18 & pabs     when st = s14 else               -- |p|
        CERO18 & cociente when st = s15 else               -- 0 - cociente
        sx_piv & piv      when st = s16 else               -- 0 - piv
        sx_qa & qa        when st = s17 else               -- 0 - a(n,n)
        CERO50;
op   <= '1' when (st = s12 or st = s13 or st = s14 or st = s15 or st = s16 or st = s17)
        else '0';

------------------------------------------------------------------------------
-- Banco de pivotes
------------------------------------------------------------------------------
det_nn     <= resultado(31 downto 0) when signo = '1' else qa;   -- s17
clr_banco  <= '1' when st = s3 else '0';
we_banco   <= '1' when (st = s8 or st = s17) else '0';
dir_banco  <= n when st = s17 else k;
dato_banco <= det_nn when st = s17 else piv;

------------------------------------------------------------------------------
-- Salidas
------------------------------------------------------------------------------
det   <= det_r;
final <= '1' when st = s18 else '0';

------------------------------------------------------------------------------
-- DIAGRAMA ASM
------------------------------------------------------------------------------
process (clk, rst)
begin

if rst = '1' then
    st      <= s0;
    dira_r  <= "00000";
    n <= "000";  i <= "000";  j <= "000";  k <= "000";
    piv     <= CERO32;  p <= CERO32;  pabs <= CERO32;  signo <= '0';
    tmp     <= CERO32;
    mul_a_r <= CERO25;  mul_b_r <= CERO25;
    t1      <= CERO50;  t2 <= CERO50;  t3 <= CERO50;
    residuo <= CERO50;  cociente <= CERO32;  sq <= '0';
    det_r   <= CERO32;

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
            i      <= UNO3;
            j      <= UNO3;
            st     <= s2;

        when s2 =>                              -- RAM(i,j) = ROM(dira), por columnas
            dira_r <= dira_mas1;
            if i = n then
                i <= UNO3;
                if j = n then
                    st <= s3;
                else
                    j  <= j_mas1;
                    st <= s2;
                end if;
            else
                i  <= i_mas1;
                st <= s2;
            end if;

        when s3 =>                              -- inicializacion ; banco = 0
            k     <= UNO3;
            p     <= UNO32;                     -- pivote inicial a(0,0) = 1
            pabs  <= UNO32;
            signo <= '0';
            det_r <= CERO32;
            st    <= s4;

        ----------------------------------------------------------------
        -- Pivote del paso k
        ----------------------------------------------------------------
        when s4 =>                              -- piv = RAM_A(k,k)
            piv <= qa;
            if qa = CERO32 then
                i  <= k_mas1;
                st <= s5;
            else
                st <= s8;
            end if;

        when s5 =>                              -- busca fila i > k con RAM_A(i,k) /= 0
            if qa /= CERO32 then
                j     <= k;
                signo <= not signo;             -- el intercambio cambia el signo
                st    <= s6;
            elsif i = n then
                det_r <= CERO32;                -- no hay fila: matriz singular
                st    <= s18;
            else
                i  <= i_mas1;
                st <= s5;
            end if;

        when s6 =>                              -- RAM(i,j) = RAM_A(k,j) ; tmp = RAM_B(i,j)
            tmp <= qb;
            st  <= s7;

        when s7 =>                              -- RAM(k,j) = tmp
            if j = n then
                st <= s4;                       -- vuelve a leer el pivote
            else
                j  <= j_mas1;
                st <= s6;
            end if;

        when s8 =>                              -- banco(k) = piv ; i = j = k + 1
            i  <= k_mas1;
            j  <= k_mas1;
            st <= s9;

        ----------------------------------------------------------------
        -- a(i,j) = ( a(k,k)*a(i,j) - a(i,k)*a(k,j) ) / p
        ----------------------------------------------------------------
        when s9 =>                              -- mul_a = a(k,k) ; mul_b = RAM_A(i,j)
            mul_a_r <= piv(24 downto 0);
            mul_b_r <= qa(24 downto 0);
            st      <= s10;

        when s10 =>                             -- t1 = producto
            t1      <= producto;                -- mul_a = RAM_A(i,k) ; mul_b = RAM_B(k,j)
            mul_a_r <= qa(24 downto 0);
            mul_b_r <= qb(24 downto 0);
            st      <= s11;

        when s11 =>                             -- t2 = producto
            t2 <= producto;
            st <= s12;

        when s12 =>                             -- t3 = t1 - t2
            t3 <= resultado;
            st <= s13;

        ----------------------------------------------------------------
        -- Division por restas sucesivas: cociente = |t3| / |p|
        ----------------------------------------------------------------
        when s13 =>                             -- residuo = |t3| ; cociente = 0
            cociente <= CERO32;
            sq       <= t3(49) xor p(31);       -- signo del cociente
            if t3(49) = '1' then
                residuo <= resultado;           -- 0 - t3
            else
                residuo <= t3;
            end if;
            st <= s14;

        when s14 =>                             -- residuo - |p|
            if resultado(49) = '0' then         -- residuo - |p| >= 0
                residuo  <= resultado;
                cociente <= cociente_mas1;
                st       <= s14;
            else
                st       <= s15;
            end if;

        when s15 =>                             -- RAM(i,j) = +/- cociente ; avanza j, i
            if j = n then
                if i = n then
                    st <= s16;
                else
                    i  <= i_mas1;
                    j  <= k_mas1;
                    st <= s9;
                end if;
            else
                j  <= j_mas1;
                st <= s9;
            end if;

        when s16 =>                             -- p = piv ; |p| = |piv| ; k = k + 1
            p <= piv;
            if piv(31) = '1' then
                pabs <= resultado(31 downto 0); -- 0 - piv
            else
                pabs <= piv;
            end if;
            k <= k_mas1;
            if k_mas1 = n then                  -- k = n - 1 : ultimo paso
                st <= s17;
            else
                st <= s4;
            end if;

        when s17 =>                             -- det = +/- RAM_A(n,n) ; banco(n) = det
            det_r <= det_nn;
            st    <= s18;

        when s18 =>                             -- final = 1
            dira_r <= "00000";
            if inicio = '1' then
                st <= s1;                       -- nuevo calculo
            else
                st <= s18;
            end if;

        when others =>
            st <= s0;

    end case;
end if;
end process;

end Behavioral;


----------------------------------------------------------------------------------
-- PROCESADOR DE BAREISS (descripcion estructural)
--
--   inicio, dir_p --> [ procesador_bareiss ] --> det, pivote, final
--
-- La ROM entrega la matriz; las dos RAM guardan la matriz de trabajo; el ASM
-- usa el multiplicador y el sumador/restador; el banco guarda los pivotes y
-- dir_p elige cual sale por "pivote".
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity procesador_bareiss is
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);   -- pivote que se lee (1..n)
           det      : out STD_LOGIC_VECTOR (31 downto 0);  -- complemento a 2
           pivote   : out STD_LOGIC_VECTOR (31 downto 0);  -- complemento a 2
           final    : out STD_LOGIC);
end procesador_bareiss;

architecture Estructural of procesador_bareiss is

component asm_bareiss
    Port ( clk, rst   : in  STD_LOGIC;
           inicio     : in  STD_LOGIC;
           dira       : out STD_LOGIC_VECTOR (4 downto 0);
           a          : in  STD_LOGIC_VECTOR (5 downto 0);
           fila_ra    : out STD_LOGIC_VECTOR (2 downto 0);
           col_ra     : out STD_LOGIC_VECTOR (2 downto 0);
           fila_rb    : out STD_LOGIC_VECTOR (2 downto 0);
           col_rb     : out STD_LOGIC_VECTOR (2 downto 0);
           fila_w     : out STD_LOGIC_VECTOR (2 downto 0);
           col_w      : out STD_LOGIC_VECTOR (2 downto 0);
           we         : out STD_LOGIC;
           data       : out STD_LOGIC_VECTOR (31 downto 0);
           qa         : in  STD_LOGIC_VECTOR (31 downto 0);
           qb         : in  STD_LOGIC_VECTOR (31 downto 0);
           mul_a      : out STD_LOGIC_VECTOR (24 downto 0);
           mul_b      : out STD_LOGIC_VECTOR (24 downto 0);
           producto   : in  STD_LOGIC_VECTOR (49 downto 0);
           sr_a       : out STD_LOGIC_VECTOR (49 downto 0);
           sr_b       : out STD_LOGIC_VECTOR (49 downto 0);
           op         : out STD_LOGIC;
           resultado  : in  STD_LOGIC_VECTOR (49 downto 0);
           clr_banco  : out STD_LOGIC;
           we_banco   : out STD_LOGIC;
           dir_banco  : out STD_LOGIC_VECTOR (2 downto 0);
           dato_banco : out STD_LOGIC_VECTOR (31 downto 0);
           det        : out STD_LOGIC_VECTOR (31 downto 0);
           final      : out STD_LOGIC);
end component;

component rom_matriz
    Port ( dira : in  STD_LOGIC_VECTOR (4 downto 0);
           a    : out STD_LOGIC_VECTOR (5 downto 0));
end component;

component RAM_memory
    port ( c      : in  std_logic;
           data   : in  std_logic_vector (31 downto 0);
           wr_add : in  std_logic_vector (4 downto 0);
           rd_add : in  std_logic_vector (4 downto 0);
           we     : in  std_logic;
           q      : out std_logic_vector (31 downto 0));
end component;

component dir_ram
    Port ( fila : in  STD_LOGIC_VECTOR (2 downto 0);
           col  : in  STD_LOGIC_VECTOR (2 downto 0);
           dir  : out STD_LOGIC_VECTOR (4 downto 0));
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

component banco_pivotes
    Port ( clk, rst : in  STD_LOGIC;
           clr      : in  STD_LOGIC;
           we       : in  STD_LOGIC;
           dir_w    : in  STD_LOGIC_VECTOR (2 downto 0);
           dato     : in  STD_LOGIC_VECTOR (31 downto 0);
           dir_r    : in  STD_LOGIC_VECTOR (2 downto 0);
           q        : out STD_LOGIC_VECTOR (31 downto 0));
end component;

-- ROM
signal dira : STD_LOGIC_VECTOR (4 downto 0);
signal a    : STD_LOGIC_VECTOR (5 downto 0);
-- RAM A y B
signal fila_ra, col_ra, fila_rb, col_rb, fila_w, col_w : STD_LOGIC_VECTOR (2 downto 0);
signal rd_add_a, rd_add_b, wr_add : STD_LOGIC_VECTOR (4 downto 0);
signal we       : STD_LOGIC;
signal data     : STD_LOGIC_VECTOR (31 downto 0);
signal qa, qb   : STD_LOGIC_VECTOR (31 downto 0);
-- multiplicador
signal mul_a, mul_b : STD_LOGIC_VECTOR (24 downto 0);
signal producto     : STD_LOGIC_VECTOR (49 downto 0);
-- sumador/restador
signal sr_a, sr_b, resultado : STD_LOGIC_VECTOR (49 downto 0);
signal op           : STD_LOGIC;
-- banco de pivotes
signal clr_banco, we_banco : STD_LOGIC;
signal dir_banco           : STD_LOGIC_VECTOR (2 downto 0);
signal dato_banco          : STD_LOGIC_VECTOR (31 downto 0);

begin

U_ASM : asm_bareiss port map (
    clk => clk, rst => rst, inicio => inicio,
    dira => dira, a => a,
    fila_ra => fila_ra, col_ra => col_ra, fila_rb => fila_rb, col_rb => col_rb,
    fila_w => fila_w, col_w => col_w,
    we => we, data => data, qa => qa, qb => qb,
    mul_a => mul_a, mul_b => mul_b, producto => producto,
    sr_a => sr_a, sr_b => sr_b, op => op, resultado => resultado,
    clr_banco => clr_banco, we_banco => we_banco, dir_banco => dir_banco,
    dato_banco => dato_banco,
    det => det, final => final);

U_ROM : rom_matriz port map (dira => dira, a => a);

U_DIR_A : dir_ram port map (fila => fila_ra, col => col_ra, dir => rd_add_a);
U_DIR_B : dir_ram port map (fila => fila_rb, col => col_rb, dir => rd_add_b);
U_DIR_W : dir_ram port map (fila => fila_w,  col => col_w,  dir => wr_add);

U_RAM_A : RAM_memory port map (
    c => clk, data => data, wr_add => wr_add, rd_add => rd_add_a, we => we, q => qa);

U_RAM_B : RAM_memory port map (
    c => clk, data => data, wr_add => wr_add, rd_add => rd_add_b, we => we, q => qb);

U_MUL : multiplicador port map (a => mul_a, b => mul_b, p => producto);

U_SR : sumador_restador port map (a => sr_a, b => sr_b, op => op, s => resultado);

U_BANCO : banco_pivotes port map (
    clk => clk, rst => rst, clr => clr_banco, we => we_banco, dir_w => dir_banco,
    dato => dato_banco, dir_r => dir_p, q => pivote);

end Estructural;

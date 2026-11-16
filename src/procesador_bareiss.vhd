----------------------------------------------------------------------------------
-- Universidad Distrital Francisco Jose de Caldas
-- Analisis y Diseno de Microprocesadores - Taller 5
--
-- PROCESADOR DE BAREISS (determinante de una matriz de 2x2 a 5x5)
--
-- Este archivo tiene cinco entidades:
--   rom_matriz          ROM con la matriz (se cambia para cada evaluacion)
--   RAM_memory          RAM del curso (modelo del profesor, sin cambios)
--   multiplicador       unidad funcional 1: multiplicador 25 x 25 con signo
--   sumador_restador    unidad funcional 2: sumador/restador de 50 bits
--   procesador_bareiss  ASM de Bareiss descrito en alto nivel, con el mismo
--                       estilo de los ejemplos ASM_Sumax y ASM_contador_unos
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
-- escriben al mismo tiempo. La RAM A lee a(i,j) y la RAM B lee a(k,j), asi se
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
-- UNIDAD FUNCIONAL 1: MULTIPLICADOR CON SIGNO 25 x 25 -> 50 bits (combinacional)
-- 25 bits alcanzan: los operandos son determinantes de submatrices de hasta
-- 4 x 4, menores que 2^24 en valor absoluto.
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
--   op = '1' : s = a - b
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_signed.all;

entity sumador_restador is
    Port ( a  : in  STD_LOGIC_VECTOR (49 downto 0);
           b  : in  STD_LOGIC_VECTOR (49 downto 0);
           op : in  STD_LOGIC;
           s  : out STD_LOGIC_VECTOR (49 downto 0));
end sumador_restador;

architecture Behavioral of sumador_restador is
begin

s <= a + b when op = '0' else a - b;

end Behavioral;

----------------------------------------------------------------------------------
-- PROCESADOR DE BAREISS
--
-- Caja negra:  clk, rst, inicio, dir_p (3)  -->  det (32), pivote (32), final
--
-- Un solo ASM (case st is), igual que en los ejemplos del curso. Cada estado
-- hace las operaciones de su caja en el diagrama ASM.
--
-- Unidades funcionales (una instancia de cada entidad):
--   U_MUL : multiplicador     producto  = mul_a * mul_b
--   U_SR  : sumador_restador  resultado = sr_a + sr_b  (op = 0)  o  sr_a - sr_b  (op = 1)
-- Los estados cargan las entradas (mul_a, mul_b, sr_a, sr_b) y en el estado
-- siguiente toman el resultado.
--
-- Memorias: la ROM tiene la matriz; las RAM A y B guardan la matriz de trabajo.
-- La RAM A lee a(i,j), la RAM B lee a(k,j) y se escribe en a(i,j) (en s5, en
-- a(k,j)).
-- Division por restas sucesivas: |t1 - t2| / |p|. El sumador/restador solo
-- resta (op = 1); el signo del cociente (sq) se aplica al escribir.
-- Los pivotes 1 a n-1 quedan en el banco b1..b4; el pivote n es el det.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_arith.all;
use ieee.std_logic_signed.all;

entity procesador_bareiss is
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);   -- pivote que se muestra (1..n)
           det      : out STD_LOGIC_VECTOR (31 downto 0);
           pivote   : out STD_LOGIC_VECTOR (31 downto 0);
           final    : out STD_LOGIC);
end procesador_bareiss;

architecture Behavioral of procesador_bareiss is

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

type estados_asm is (s0,s1,s2,s3,s4,s5,s6,s7,s8,s9,s10,s11,s12,s13);
signal st : estados_asm;

-- ROM y RAM
signal dira   : STD_LOGIC_VECTOR (4 downto 0);    -- direccion de la ROM
signal a      : STD_LOGIC_VECTOR (5 downto 0);    -- dato de la ROM
signal dir_ij : STD_LOGIC_VECTOR (4 downto 0);    -- direccion de a(i,j) en la RAM
signal dir_kj : STD_LOGIC_VECTOR (4 downto 0);    -- direccion de a(k,j) en la RAM
signal wr_add : STD_LOGIC_VECTOR (4 downto 0);
signal we     : STD_LOGIC;
signal data   : STD_LOGIC_VECTOR (31 downto 0);   -- dato que se escribe
signal qa, qb : STD_LOGIC_VECTOR (31 downto 0);   -- qa = a(i,j), qb = a(k,j)

-- Registros del algoritmo
signal n, i, j, k : STD_LOGIC_VECTOR (2 downto 0);
signal piv    : STD_LOGIC_VECTOR (31 downto 0);   -- pivote a(k,k)
signal p      : STD_LOGIC_VECTOR (31 downto 0);   -- pivote anterior
signal pabs   : STD_LOGIC_VECTOR (31 downto 0);   -- |p| (divisor)
signal aik    : STD_LOGIC_VECTOR (31 downto 0);   -- a(i,k) de la fila i
signal tmp    : STD_LOGIC_VECTOR (31 downto 0);   -- intercambio de filas
signal signo  : STD_LOGIC;                        -- 1 = numero impar de intercambios
signal b1, b2, b3, b4 : STD_LOGIC_VECTOR (31 downto 0);   -- banco de pivotes
signal deter  : STD_LOGIC_VECTOR (31 downto 0);   -- determinante

-- Multiplicador
signal mul_a, mul_b : STD_LOGIC_VECTOR (24 downto 0);
signal producto     : STD_LOGIC_VECTOR (49 downto 0);

-- Sumador/restador y division
signal sr_a, sr_b : STD_LOGIC_VECTOR (49 downto 0);   -- en la division, sr_a es el residuo
signal op         : STD_LOGIC;                        -- 1 = resta (el algoritmo solo resta)
signal resultado  : STD_LOGIC_VECTOR (49 downto 0);
signal cociente   : STD_LOGIC_VECTOR (31 downto 0);
signal sq         : STD_LOGIC;                        -- signo del cociente

begin

------------------------------------------------------------------------------
-- Memorias
------------------------------------------------------------------------------
U_ROM   : rom_matriz port map (dira => dira, a => a);
U_RAM_A : RAM_memory port map (c => clk, data => data, wr_add => wr_add,
                               rd_add => dir_ij, we => we, q => qa);
U_RAM_B : RAM_memory port map (c => clk, data => data, wr_add => wr_add,
                               rd_add => dir_kj, we => we, q => qb);

-- a(f,c) se guarda en f & c(1 downto 0) (columnas 1 a 4) o en "11" & f (columna 5)
dir_ij <= "11" & i when j = "101" else i & j(1 downto 0);
dir_kj <= "11" & k when j = "101" else k & j(1 downto 0);

-- Escritura en las dos RAM
we     <= '1' when (st = s1 or st = s4 or st = s5 or st = s12) else '0';
wr_add <= dir_kj when st = s5 else dir_ij;
data   <= SXT(a, 32)             when st = s1 else     -- copia de la ROM
          qb                     when st = s4 else     -- intercambio: a(k,j)
          tmp                    when st = s5 else     -- intercambio: a(i,j)
          resultado(31 downto 0) when sq = '1' else    -- s12: - cociente
          cociente;                                    -- s12: + cociente

------------------------------------------------------------------------------
-- Unidades funcionales
------------------------------------------------------------------------------
U_MUL : multiplicador    port map (a => mul_a, b => mul_b, p => producto);
U_SR  : sumador_restador port map (a => sr_a, b => sr_b, op => op, s => resultado);

op <= '1';                                          -- division por restas sucesivas

------------------------------------------------------------------------------
-- Salidas
------------------------------------------------------------------------------
final  <= '1' when st = s13 else '0';
det    <= deter;
pivote <= deter when dir_p = n     else             -- el pivote n es el det
          b1    when dir_p = "001" else
          b2    when dir_p = "010" else
          b3    when dir_p = "011" else
          b4    when dir_p = "100" else
          (others => '0');

------------------------------------------------------------------------------
-- DIAGRAMA ASM
------------------------------------------------------------------------------
process (clk, rst)
begin

if rst = '1' then
    st <= s0;
    dira <= (others => '0');
    n <= "000";  i <= "000";  j <= "000";  k <= "000";
    piv <= (others => '0');  p <= (others => '0');  pabs <= (others => '0');
    aik <= (others => '0');  tmp <= (others => '0');  signo <= '0';
    b1 <= (others => '0');  b2 <= (others => '0');
    b3 <= (others => '0');  b4 <= (others => '0');
    deter <= (others => '0');
    mul_a <= (others => '0');  mul_b <= (others => '0');
    sr_a <= (others => '0');  sr_b <= (others => '0');
    cociente <= (others => '0');  sq <= '0';

elsif clk'event and clk = '1' then

    case st is

        when s0 =>                          -- final = 0 ; espera inicio
            if inicio = '0' then
                st <= s0;
            else
                n    <= a(2 downto 0);      -- ROM(00h) = n
                dira <= "00001";
                i <= "001";
                j <= "001";
                st <= s1;
            end if;

        when s1 =>                          -- RAM(i,j) = ROM(dira), por columnas
            dira <= dira + 1;
            if i /= n then
                i  <= i + 1;
                st <= s1;
            elsif j /= n then
                i  <= "001";
                j  <= j + 1;
                st <= s1;
            else
                k     <= "001";
                j     <= "001";             -- la RAM B lee a(1,1)
                p     <= x"00000001";       -- pivote inicial = 1
                signo <= '0';
                st    <= s2;
            end if;

        when s2 =>                          -- piv = a(k,k) (RAM B con j = k) ; |p|
            piv <= qb;
            i   <= k + 1;
            if p(31) = '1' then             -- p < 0: |p| = 0 - p (preparado en s12)
                pabs <= resultado(31 downto 0);
            else
                pabs <= p;
            end if;
            if qb = 0 then
                st <= s3;                   -- pivote cero: busca otra fila
            else
                case k is                   -- banco(k) = piv
                    when "001"  => b1 <= qb;
                    when "010"  => b2 <= qb;
                    when "011"  => b3 <= qb;
                    when others => b4 <= qb;
                end case;
                st <= s6;
            end if;

        when s3 =>                          -- busca fila i con a(i,k) /= 0 (RAM A con j = k)
            if qa /= 0 then
                signo <= not signo;         -- el intercambio cambia el signo del det
                st <= s4;
            elsif i = n then
                deter <= (others => '0');   -- no hay fila: det = 0
                st <= s13;
            else
                i  <= i + 1;
                st <= s3;
            end if;

        when s4 =>                          -- RAM(i,j) = a(k,j) ; tmp = a(i,j)
            tmp <= qa;
            st  <= s5;

        when s5 =>                          -- RAM(k,j) = tmp
            if j = n then
                j  <= k;                    -- vuelve a leer el pivote
                st <= s2;
            else
                j  <= j + 1;
                st <= s4;
            end if;

        when s6 =>                          -- inicio de la fila i: aik = a(i,k)
            aik <= qa;
            j   <= k + 1;
            st  <= s7;

        when s7 =>                          -- multiplicador: piv * a(i,j)
            mul_a <= piv(24 downto 0);
            mul_b <= qa(24 downto 0);
            st <= s8;

        when s8 =>                          -- sr_a = piv * a(i,j) ; multiplicador: a(i,k) * a(k,j)
            sr_a  <= producto;
            mul_a <= aik(24 downto 0);
            mul_b <= qb(24 downto 0);
            st <= s9;

        when s9 =>                          -- sr_b = a(i,k) * a(k,j) ; signo del cociente
            sr_b     <= producto;
            sq       <= p(31);
            cociente <= (others => '0');
            st <= s10;

        when s10 =>                         -- residuo = |t1 - t2| ; divisor = |p|
            if resultado(49) = '1' then     -- t1 < t2: se resta al reves (t2 - t1)
                sr_a <= sr_b;
                sr_b <= sr_a;
                sq   <= not sq;
                st <= s10;
            else
                sr_a <= resultado;
                sr_b <= SXT(pabs, 50);
                st <= s11;
            end if;

        when s11 =>                         -- division por restas sucesivas: residuo - |p|
            if resultado(49) = '0' then     -- residuo - |p| >= 0
                sr_a     <= resultado;
                cociente <= cociente + 1;
                st <= s11;
            else
                sr_a <= (others => '0');    -- prepara 0 - cociente
                sr_b <= SXT(cociente, 50);
                st <= s12;
            end if;

        when s12 =>                         -- RAM(i,j) = +/- cociente ; avanza j, i, k
            if j /= n then
                j  <= j + 1;
                st <= s7;
            elsif i /= n then
                i  <= i + 1;
                j  <= k;
                st <= s6;
            elsif k + 1 /= n then
                p    <= piv;
                k    <= k + 1;
                j    <= k + 1;
                sr_a <= (others => '0');    -- prepara 0 - piv para |p| en s2
                sr_b <= SXT(piv, 50);
                st   <= s2;
            else                            -- ultimo paso: det = +/- a(n,n)
                if (sq xor signo) = '1' then
                    deter <= resultado(31 downto 0);
                else
                    deter <= cociente;
                end if;
                st <= s13;
            end if;

        when s13 =>                         -- final = 1
            if inicio = '1' then
                dira <= "00001";
                i <= "001";
                j <= "001";
                st <= s1;
            else
                st <= s13;
            end if;

    end case;
end if;
end process;

end Behavioral;

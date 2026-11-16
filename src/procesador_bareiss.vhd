----------------------------------------------------------------------------------
-- Universidad Distrital Francisco Jose de Caldas
-- Analisis y Diseno de Microprocesadores - Taller 5
--
-- PROCESADOR DE BAREISS (determinante de una matriz de 2x2 a 5x5)
--
-- Caja negra:  clk, rst, inicio, dir_p (3)  -->  det (32), pivote (32), final
--
-- ASM en alto nivel, con el estilo de los ejemplos ASM_Sumax y
-- ASM_contador_unos: un solo process con "case st is" y, en cada estado, las
-- operaciones de su caja en el diagrama ASM.
--
-- El ASM esta disenado con el hardware que pide el taller. Cada unidad
-- trabaja siempre sobre los mismos registros, asi la sintesis arma una sola:
--   * Multiplicador:     x * y   (s8 y s9)
--   * Sumador/restador:  r - s   (s10 y s12); el ASM solo necesita restar
--   * Division por restas sucesivas (s11 y s12): se resta p y se cuentan las
--     restas en el contador cociente. No usa valor absoluto.
--   * ROM con la matriz y dos RAM con el modelo de RAM del curso (RAM_memory).
-- Los contadores (dira, i, j, k y cociente) tienen su propio +1 o -1, como el
-- contador i del ejemplo ASM_Sumax.
--
-- Librerias: solo std_logic_1164 y std_logic_signed (los datos son con signo,
-- en complemento a 2). Todas las senales son std_logic o std_logic_vector.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
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

component RAM_memory
   port ( c      : in  std_logic;
          data   : in  std_logic_vector (31 downto 0);
          wr_add : in  std_logic_vector (4 downto 0);
          rd_add : in  std_logic_vector (4 downto 0);
          we     : in  std_logic;
          q      : out std_logic_vector (31 downto 0));
end component;

type estados_asm is (s0,s1,s2,s3,s4,s5,s6,s7,s8,s9,s10,s11,s12,s13);
signal st : estados_asm;

-- ROM de la matriz
signal dira  : STD_LOGIC_VECTOR (4 downto 0);
signal a     : STD_LOGIC_VECTOR (5 downto 0);
signal ext_a : STD_LOGIC_VECTOR (25 downto 0);    -- extension de signo de a

-- RAM A y RAM B: tienen el mismo contenido porque se escriben juntas. La RAM A
-- lee a(i,j) y la RAM B lee a(k,j): se leen dos elementos en el mismo ciclo.
signal we             : STD_LOGIC;
signal wr_add         : STD_LOGIC_VECTOR (4 downto 0);
signal data           : STD_LOGIC_VECTOR (31 downto 0);
signal dir_ij, dir_kj : STD_LOGIC_VECTOR (4 downto 0);    -- direcciones de a(i,j) y a(k,j)
signal qa, qb         : STD_LOGIC_VECTOR (31 downto 0);   -- qa = a(i,j), qb = a(k,j)

-- Registros del algoritmo
signal n, i, j, k     : STD_LOGIC_VECTOR (2 downto 0);
signal piv            : STD_LOGIC_VECTOR (31 downto 0);   -- pivote a(k,k)
signal p              : STD_LOGIC_VECTOR (31 downto 0);   -- pivote anterior (divisor)
signal ext_p          : STD_LOGIC_VECTOR (17 downto 0);   -- extension de signo de p
signal aik            : STD_LOGIC_VECTOR (31 downto 0);   -- a(i,k) de la fila i
signal tmp            : STD_LOGIC_VECTOR (31 downto 0);   -- intercambio de filas
signal signo          : STD_LOGIC;                        -- 1 = numero impar de intercambios
signal b1, b2, b3, b4 : STD_LOGIC_VECTOR (31 downto 0);   -- banco de pivotes
signal deter          : STD_LOGIC_VECTOR (31 downto 0);   -- determinante

-- Entradas del multiplicador (x * y) y del restador (r - s)
signal x, y           : STD_LOGIC_VECTOR (24 downto 0);
signal r, s           : STD_LOGIC_VECTOR (49 downto 0);   -- en la division, r es el residuo
signal t              : STD_LOGIC_VECTOR (49 downto 0);   -- division: valor final de r
signal cociente       : STD_LOGIC_VECTOR (31 downto 0);
signal sq             : STD_LOGIC;                        -- 1 = cociente negativo (cuenta hacia abajo)

begin

-- >>> INICIO ROM (generado con: python3 sim/modelo_referencia.py rom ...)
------------------------------------------------------------------------------
-- ROM DE LA MATRIZ (32 x 6 bits, lectura combinacional)
--
-- Hace parte de la arquitectura del procesador. Para calcular el determinante
-- de otra matriz se cambia este bloque y se vuelve a programar la FPGA. Si se
-- cambia a mano, copien las mismas lineas en sim/rom_prueba.vhd (la ROM que
-- leen los testbench); el script sim/modelo_referencia.py cambia las dos.
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
------------------------------------------------------------------------------
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
-- <<< FIN ROM

------------------------------------------------------------------------------
-- RAM A y RAM B (modelo de RAM del curso, archivo RAM_memory.vhd)
------------------------------------------------------------------------------
U_RAM_A : RAM_memory port map (c => clk, data => data, wr_add => wr_add,
                               rd_add => dir_ij, we => we, q => qa);
U_RAM_B : RAM_memory port map (c => clk, data => data, wr_add => wr_add,
                               rd_add => dir_kj, we => we, q => qb);

-- a(f,c) se guarda en f & c(1 downto 0) (columnas 1 a 4) o en "11" & f (columna 5)
dir_ij <= "11" & i when j = "101" else i & j(1 downto 0);
dir_kj <= "11" & k when j = "101" else k & j(1 downto 0);

-- Escrituras del ASM en las RAM: RAM(i,j) en s1, s4 y s12; RAM(k,j) en s5
we     <= '1' when st = s1 or st = s4 or st = s5 or (st = s12 and r = t) else '0';
wr_add <= dir_kj when st = s5 else dir_ij;
data   <= ext_a & a when st = s1 else           -- s1: copia de la ROM
          qb        when st = s4 else           -- s4: intercambio, a(k,j)
          tmp       when st = s5 else           -- s5: intercambio, a(i,j)
          cociente;                             -- s12: a(i,j) nuevo

ext_a <= (others => a(5));
ext_p <= (others => p(31));

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
    piv <= (others => '0');  p <= (others => '0');
    aik <= (others => '0');  tmp <= (others => '0');
    signo <= '0';
    b1 <= (others => '0');  b2 <= (others => '0');
    b3 <= (others => '0');  b4 <= (others => '0');
    deter <= (others => '0');
    x <= (others => '0');  y <= (others => '0');
    r <= (others => '0');  s <= (others => '0');  t <= (others => '0');
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

        when s2 =>                          -- piv = a(k,k) (RAM B con j = k)
            piv <= qb;
            i   <= k + 1;
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

        when s7 =>                          -- entradas del multiplicador: piv y a(i,j)
            x  <= piv(24 downto 0);
            y  <= qa(24 downto 0);
            st <= s8;

        when s8 =>                          -- multiplicador: r = piv * a(i,j)
            r  <= x * y;
            x  <= aik(24 downto 0);         -- entradas: a(i,k) y a(k,j)
            y  <= qb(24 downto 0);
            st <= s9;

        when s9 =>                          -- multiplicador: s = a(i,k) * a(k,j)
            s  <= x * y;
            st <= s10;

        when s10 =>                         -- restador: r = numerador ; s = p
            r        <= r - s;
            s        <= ext_p & p;
            cociente <= (others => '0');
            st <= s11;

        when s11 =>                         -- prepara la division r / s
            if r(49) = s(49) then           -- mismo signo: r baja hasta 0
                t <= (others => '0');
            else                            -- signos distintos: r va de 0 hasta el numerador
                t <= r;
                r <= (others => '0');
            end if;
            if k + 1 = n and signo = '1' then
                sq <= not (r(49) xor s(49));    -- ultimo paso: det = -a(n,n)
            else
                sq <= r(49) xor s(49);          -- cociente negativo si los signos son distintos
            end if;
            st <= s12;

        when s12 =>                         -- division por restas sucesivas: r = r - p
            if r /= t then
                r <= r - s;
                if sq = '0' then
                    cociente <= cociente + 1;
                else
                    cociente <= cociente - 1;
                end if;
                st <= s12;
            elsif j /= n then               -- RAM(i,j) = cociente ; siguiente columna
                j  <= j + 1;
                st <= s7;
            elsif i /= n then               -- siguiente fila
                i  <= i + 1;
                j  <= k;
                st <= s6;
            elsif k + 1 /= n then           -- siguiente paso: p = piv
                p  <= piv;
                k  <= k + 1;
                j  <= k + 1;
                st <= s2;
            else                            -- ultimo paso: det = a(n,n)
                deter <= cociente;
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

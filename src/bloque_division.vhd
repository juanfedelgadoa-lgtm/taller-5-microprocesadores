----------------------------------------------------------------------------------
-- BLOQUE DE DIVISION POR RESTAS SUCESIVAS
--
-- Divide magnitudes: cociente = dividendo / divisor (division entera).
-- Tiene su propia unidad de control (ASM de 3 estados) y su propio camino de
-- datos: registro residuo R, registro divisor D, contador cociente Q y un
-- restador R - D. El signo del resultado lo aplica el ASM principal.
--
-- ASM:
--   d0 : espera. Si inicio = 1: R <- dividendo, D <- divisor, Q <- 0
--   d1 : si R - D >= 0: R <- R - D, Q <- Q + 1 (se queda en d1); si no, va a d2
--   d2 : final = 1 (un ciclo), vuelve a d0. El cociente queda en Q.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity bloque_division is
    Port ( clk, rst  : in  STD_LOGIC;
           inicio    : in  STD_LOGIC;
           dividendo : in  STD_LOGIC_VECTOR (49 downto 0);   -- magnitud, < 2^49
           divisor   : in  STD_LOGIC_VECTOR (31 downto 0);   -- magnitud, >= 1
           cociente  : out STD_LOGIC_VECTOR (31 downto 0);
           final     : out STD_LOGIC);
end bloque_division;

architecture Behavioral of bloque_division is

constant d0 : STD_LOGIC_VECTOR (1 downto 0) := "00";
constant d1 : STD_LOGIC_VECTOR (1 downto 0) := "01";
constant d2 : STD_LOGIC_VECTOR (1 downto 0) := "10";

constant CERO18 : STD_LOGIC_VECTOR (17 downto 0) := "000000000000000000";

signal st     : STD_LOGIC_VECTOR (1 downto 0);
signal R      : STD_LOGIC_VECTOR (49 downto 0);   -- residuo
signal D      : STD_LOGIC_VECTOR (31 downto 0);   -- divisor
signal Q      : STD_LOGIC_VECTOR (31 downto 0);   -- cociente
signal resta  : STD_LOGIC_VECTOR (49 downto 0);   -- R - D
signal q_mas1 : STD_LOGIC_VECTOR (31 downto 0);

begin

-- Camino de datos
resta  <= R - (CERO18 & D);           -- restador
q_mas1 <= Q + '1';                    -- contador del cociente

cociente <= Q;
final    <= '1' when st = d2 else '0';

-- ASM
process (clk, rst)
begin
if rst = '1' then
    st <= d0;
    R  <= (others => '0');
    D  <= (others => '0');
    Q  <= (others => '0');

elsif clk'event and clk = '1' then
    case st is

        when d0 =>                          -- espera
            if inicio = '1' then
                R  <= dividendo;
                D  <= divisor;
                Q  <= (others => '0');
                st <= d1;
            else
                st <= d0;
            end if;

        when d1 =>                          -- resta sucesiva
            if resta(49) = '0' then         -- R - D >= 0
                R  <= resta;
                Q  <= q_mas1;
                st <= d1;
            else
                st <= d2;
            end if;

        when d2 =>                          -- final = 1
            st <= d0;

        when others =>
            st <= d0;

    end case;
end if;
end process;

end Behavioral;

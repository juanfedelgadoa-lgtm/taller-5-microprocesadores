----------------------------------------------------------------------------------
-- SUMADOR/RESTADOR DE 50 bits (combinacional)
--
-- Unico sumador/restador del procesador; el ASM lo comparte entre estados
-- eligiendo sus operandos con multiplexores.
--   op = '0' : s = a + b
--   op = '1' : s = a + not(b) + 1 = a - b
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

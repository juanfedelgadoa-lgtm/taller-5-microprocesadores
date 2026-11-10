----------------------------------------------------------------------------------
-- MULTIPLICADOR CON SIGNO 25 x 25 -> 50 bits (combinacional)
--
-- Unico multiplicador del procesador. Los puertos son std_logic_vector; el
-- paquete std_logic_signed hace que "*" los interprete en complemento a 2.
-- 25 bits alcanzan: en el paso k los operandos son determinantes de
-- submatrices de k x k (k <= 4), menores que 2^24 en valor absoluto.
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

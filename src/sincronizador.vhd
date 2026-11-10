----------------------------------------------------------------------------------
-- SINCRONIZADOR DE LOS SWITCHES dir_p (dos flip-flops por bit)
-- Evita la metaestabilidad al pasar los switches al dominio del reloj.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity sincronizador is
    Port ( clk, rst : in  STD_LOGIC;
           entrada  : in  STD_LOGIC_VECTOR (2 downto 0);
           salida   : out STD_LOGIC_VECTOR (2 downto 0));
end sincronizador;

architecture Behavioral of sincronizador is

signal s1, s2 : STD_LOGIC_VECTOR (2 downto 0);

begin

process (clk, rst)
begin
if rst = '1' then
    s1 <= "000";
    s2 <= "000";
elsif clk'event and clk = '1' then
    s1 <= entrada;
    s2 <= s1;
end if;
end process;

salida <= s2;

end Behavioral;

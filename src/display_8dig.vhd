----------------------------------------------------------------------------------
-- DISPLAY DE 8 DIGITOS MULTIPLEXADO (Nexys A7: anodo comun, activos en bajo)
--
-- AN7 = signo ('-' o apagado); AN6..AN0 = 7 digitos BCD.
-- Cambia de digito con cada tick (1 ms): barrido completo de 8 ms (125 Hz).
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity display_8dig is
    Port ( clk, rst : in  STD_LOGIC;
           tick     : in  STD_LOGIC;
           bcd      : in  STD_LOGIC_VECTOR (27 downto 0);
           neg      : in  STD_LOGIC;
           an       : out STD_LOGIC_VECTOR (7 downto 0);
           seg      : out STD_LOGIC_VECTOR (6 downto 0);   -- seg(0)=CA ... seg(6)=CG
           dp       : out STD_LOGIC);
end display_8dig;

architecture Behavioral of display_8dig is

signal dsel      : STD_LOGIC_VECTOR (2 downto 0);   -- digito encendido
signal car       : STD_LOGIC_VECTOR (3 downto 0);   -- 0-9, A = '-', F = apagado
signal car_signo : STD_LOGIC_VECTOR (3 downto 0);

begin

process (clk, rst)
begin
if rst = '1' then
    dsel <= "000";
elsif clk'event and clk = '1' then
    if tick = '1' then
        dsel <= dsel + '1';
    end if;
end if;
end process;

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

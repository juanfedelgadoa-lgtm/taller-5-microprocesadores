----------------------------------------------------------------------------------
-- BANCO DE REGISTROS DE PIVOTES (5 registros de 32 bits)
--
-- Registro k = pivote a(k,k) usado en el paso k (k = 1..n-1).
-- Registro n = determinante (el ultimo pivote es el determinante).
-- Escritura sincrona en la direccion dir_w; lectura combinacional en dir_r,
-- que viene de los switches (dir_p). Las direcciones 0, 6 y 7 leen 0.
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

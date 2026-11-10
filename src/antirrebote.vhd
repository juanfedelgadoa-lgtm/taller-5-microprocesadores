----------------------------------------------------------------------------------
-- ANTIRREBOTE PARA EL BOTON DE INICIO
--
-- 1. Sincroniza el boton con dos flip-flops.
-- 2. Lo muestrea cada 1 ms (tick) en un registro de 8 muestras.
-- 3. El nivel estable cambia a '1' con 8 muestras en '1' (8 ms sin rebote) y
--    a '0' con 8 muestras en '0'.
-- 4. pulso = '1' durante un solo ciclo de reloj cuando el nivel estable pasa
--    de '0' a '1': una pulsacion genera un unico inicio.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity antirrebote is
    Port ( clk, rst : in  STD_LOGIC;
           tick     : in  STD_LOGIC;      -- habilitacion de muestreo (1 ms)
           boton    : in  STD_LOGIC;
           pulso    : out STD_LOGIC);
end antirrebote;

architecture Behavioral of antirrebote is

signal b1, b2   : STD_LOGIC;
signal muestras : STD_LOGIC_VECTOR (7 downto 0);
signal estable, estable_ant : STD_LOGIC;

begin

process (clk, rst)
begin
if rst = '1' then
    b1 <= '0';  b2 <= '0';
    muestras    <= (others => '0');
    estable     <= '0';
    estable_ant <= '0';
elsif clk'event and clk = '1' then
    b1 <= boton;
    b2 <= b1;
    if tick = '1' then
        muestras <= muestras(6 downto 0) & b2;
    end if;
    if muestras = "11111111" then
        estable <= '1';
    elsif muestras = "00000000" then
        estable <= '0';
    end if;
    estable_ant <= estable;
end if;
end process;

pulso <= estable and not estable_ant;

end Behavioral;

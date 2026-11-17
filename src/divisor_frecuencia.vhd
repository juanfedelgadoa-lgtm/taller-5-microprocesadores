----------------------------------------------------------------------------------
-- DIVISOR DE FRECUENCIA (reloj de la Nexys A7 = 100 MHz, pin E3)
--
--   tick_1ms : pulso de un ciclo cada 1 ms (100 000 ciclos). Lo usan el
--              antirrebote (muestreo del boton) y el display (cambio de digito).
--
-- El pulso se usa como habilitacion (clock enable): todo el diseno trabaja
-- con el mismo reloj de 100 MHz. El procesador no usa este divisor: con un
-- reloj de 1 s una matriz de 3x3 tardaria casi un minuto.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_signed.all;      -- solo para el contador (+ 1)

entity divisor_frecuencia is
    Port ( clk, rst : in  STD_LOGIC;
           tick_1ms : out STD_LOGIC);
end divisor_frecuencia;

architecture Behavioral of divisor_frecuencia is

constant FIN_1MS : STD_LOGIC_VECTOR (16 downto 0) := "11000011010011111";   -- 99 999

signal cuenta_ciclos : STD_LOGIC_VECTOR (16 downto 0);
signal tick          : STD_LOGIC;

begin

tick <= '1' when cuenta_ciclos = FIN_1MS else '0';

process (clk, rst)
begin
if rst = '1' then
    cuenta_ciclos <= (others => '0');
elsif clk'event and clk = '1' then
    if tick = '1' then
        cuenta_ciclos <= (others => '0');
    else
        cuenta_ciclos <= cuenta_ciclos + 1;
    end if;
end if;
end process;

tick_1ms <= tick;

end Behavioral;

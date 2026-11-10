----------------------------------------------------------------------------------
-- DIVISOR DE FRECUENCIA (reloj de la Nexys A7 = 100 MHz, pin E3)
--
--   tick_1ms : pulso de un ciclo cada 1 ms (100 000 ciclos). Lo usan el
--              antirrebote (muestreo del boton) y el display (cambio de digito).
--   onda_1s  : onda cuadrada de periodo 1 s (cambia cada 500 ms).
--
-- Los pulsos se usan como habilitacion (clock enable): todo el diseno trabaja
-- con el mismo reloj de 100 MHz. El procesador no usa este divisor: con un
-- reloj de 1 s una matriz de 3x3 tardaria unos 13 minutos.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity divisor_frecuencia is
    Port ( clk, rst : in  STD_LOGIC;
           tick_1ms : out STD_LOGIC;
           onda_1s  : out STD_LOGIC);
end divisor_frecuencia;

architecture Behavioral of divisor_frecuencia is

constant FIN_1MS   : STD_LOGIC_VECTOR (16 downto 0) := "11000011010011111";   -- 99 999
constant FIN_500MS : STD_LOGIC_VECTOR (8 downto 0)  := "111110011";           -- 499

signal cuenta_ciclos : STD_LOGIC_VECTOR (16 downto 0);
signal cuenta_ms     : STD_LOGIC_VECTOR (8 downto 0);
signal tick          : STD_LOGIC;
signal onda          : STD_LOGIC;

begin

tick <= '1' when cuenta_ciclos = FIN_1MS else '0';

process (clk, rst)
begin
if rst = '1' then
    cuenta_ciclos <= (others => '0');
    cuenta_ms     <= (others => '0');
    onda          <= '0';
elsif clk'event and clk = '1' then
    if tick = '1' then
        cuenta_ciclos <= (others => '0');
        if cuenta_ms = FIN_500MS then
            cuenta_ms <= (others => '0');
            onda      <= not onda;
        else
            cuenta_ms <= cuenta_ms + '1';
        end if;
    else
        cuenta_ciclos <= cuenta_ciclos + '1';
    end if;
end if;
end process;

tick_1ms <= tick;
onda_1s  <= onda;

end Behavioral;

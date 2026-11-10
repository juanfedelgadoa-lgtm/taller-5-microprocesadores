----------------------------------------------------------------------------------
-- BLOQUE XS3: conversion binario -> BCD (sumar 3 y desplazar)
--
-- Tiene su propia unidad de control (ASM de 6 estados) y su propio camino de
-- datos: registro binario (32 bits), registro decimal (10 digitos = 40 bits),
-- un sumador de 4 bits (+3), un comparador de magnitud (> 4) y desplazadores.
-- Convierte una magnitud de 32 bits; el signo lo maneja el ASM principal.
--
-- ASM (un estado por cada paso del documento XS3):
--   x0 : espera. Si inicio = 1: bin <- bin_in
--   x1 : PASO 1. Registro decimal = 0; cont = 0
--   x2 : PASO 2. LSB del decimal = MSB del binario.
--        Si cont = 31 ya se hizo el ultimo paso 2 (PASO 5): va a x5
--   x3 : PASO 3. Revisa el digito d (0 a 9): si es > 4 le suma 3
--   x4 : PASO 4. Corrimiento a la izquierda de ambos registros; cont + 1
--   x5 : final = 1 (un ciclo), vuelve a x0. El resultado queda en bcd.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity xs3 is
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           bin_in   : in  STD_LOGIC_VECTOR (31 downto 0);
           bcd      : out STD_LOGIC_VECTOR (39 downto 0);
           final    : out STD_LOGIC);
end xs3;

architecture Behavioral of xs3 is

constant x0 : STD_LOGIC_VECTOR (2 downto 0) := "000";
constant x1 : STD_LOGIC_VECTOR (2 downto 0) := "001";
constant x2 : STD_LOGIC_VECTOR (2 downto 0) := "010";
constant x3 : STD_LOGIC_VECTOR (2 downto 0) := "011";
constant x4 : STD_LOGIC_VECTOR (2 downto 0) := "100";
constant x5 : STD_LOGIC_VECTOR (2 downto 0) := "101";

signal st      : STD_LOGIC_VECTOR (2 downto 0);
signal bin     : STD_LOGIC_VECTOR (31 downto 0);  -- registro binario
signal dec     : STD_LOGIC_VECTOR (39 downto 0);  -- registro decimal
signal cont    : STD_LOGIC_VECTOR (4 downto 0);   -- bits procesados (0..31)
signal d       : STD_LOGIC_VECTOR (3 downto 0);   -- digito revisado (0..9)
signal dig     : STD_LOGIC_VECTOR (3 downto 0);   -- digito d del registro decimal
signal dig_mas3 : STD_LOGIC_VECTOR (3 downto 0);
signal mayor4  : STD_LOGIC;
signal cont_mas1 : STD_LOGIC_VECTOR (4 downto 0);
signal d_mas1  : STD_LOGIC_VECTOR (3 downto 0);

begin

-- Camino de datos
with d select                                    -- multiplexor de digitos
    dig <= dec(3 downto 0)   when "0000",
           dec(7 downto 4)   when "0001",
           dec(11 downto 8)  when "0010",
           dec(15 downto 12) when "0011",
           dec(19 downto 16) when "0100",
           dec(23 downto 20) when "0101",
           dec(27 downto 24) when "0110",
           dec(31 downto 28) when "0111",
           dec(35 downto 32) when "1000",
           dec(39 downto 36) when "1001",
           "0000"            when others;

dig_mas3  <= dig + "0011";                       -- sumador de 4 bits
mayor4    <= '1' when dig > "0100" else '0';     -- comparador de magnitud
cont_mas1 <= cont + '1';
d_mas1    <= d + '1';

bcd   <= dec;
final <= '1' when st = x5 else '0';

-- ASM
process (clk, rst)
begin
if rst = '1' then
    st   <= x0;
    bin  <= (others => '0');
    dec  <= (others => '0');
    cont <= "00000";
    d    <= "0000";

elsif clk'event and clk = '1' then
    case st is

        when x0 =>                              -- espera
            if inicio = '1' then
                bin <= bin_in;
                st  <= x1;
            else
                st  <= x0;
            end if;

        when x1 =>                              -- PASO 1: registro decimal = 0
            dec  <= (others => '0');
            cont <= "00000";
            st   <= x2;

        when x2 =>                              -- PASO 2: LSB decimal = MSB binario
            dec(0) <= bin(31);
            if cont = "11111" then
                st <= x5;                       -- PASO 5: ultimo paso 2 hecho
            else
                d  <= "0000";
                st <= x3;
            end if;

        when x3 =>                              -- PASO 3: si digito(d) > 4, sumar 3
            if mayor4 = '1' then
                case d is
                    when "0000" => dec(3 downto 0)   <= dig_mas3;
                    when "0001" => dec(7 downto 4)   <= dig_mas3;
                    when "0010" => dec(11 downto 8)  <= dig_mas3;
                    when "0011" => dec(15 downto 12) <= dig_mas3;
                    when "0100" => dec(19 downto 16) <= dig_mas3;
                    when "0101" => dec(23 downto 20) <= dig_mas3;
                    when "0110" => dec(27 downto 24) <= dig_mas3;
                    when "0111" => dec(31 downto 28) <= dig_mas3;
                    when "1000" => dec(35 downto 32) <= dig_mas3;
                    when "1001" => dec(39 downto 36) <= dig_mas3;
                    when others => null;
                end case;
            end if;
            if d = "1001" then
                st <= x4;
            else
                d  <= d_mas1;
                st <= x3;
            end if;

        when x4 =>                              -- PASO 4: corrimiento a la izquierda
            dec  <= dec(38 downto 0) & '0';
            bin  <= bin(30 downto 0) & '0';
            cont <= cont_mas1;
            st   <= x2;

        when x5 =>                              -- final = 1
            st <= x0;

        when others =>
            st <= x0;

    end case;
end if;
end process;

end Behavioral;

----------------------------------------------------------------------------------
-- ROM DE LA MATRIZ (32 x 6 bits, lectura combinacional)
--
-- Hace parte de la arquitectura del procesador: para calcular el determinante
-- de otra matriz se cambia este archivo y se vuelve a programar la FPGA.
-- Archivo generado con: python3 sim/modelo_referencia.py rom ...
--
-- Posicion 00h = n; luego los elementos a(i,j) por columnas (a11, a21, ...),
-- como en la Figura 1 del taller. Datos en complemento a 2 (-32 a 31).
--
-- Matriz (5x5):
--      4   -2    1    3    0
--     -2    6    2   -1    5
--      1    2   -7    4    2
--      3   -1    4    5   -3
--      0    5    2   -3    8
-- Resultado esperado: det = 362
-- Pivotes (dir_p = 1..5): 4, 20, -170, -639, 362
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity rom_matriz is
    Port ( dira : in  STD_LOGIC_VECTOR (4 downto 0);
           a    : out STD_LOGIC_VECTOR (5 downto 0));
end rom_matriz;

architecture Behavioral of rom_matriz is
begin

with dira select
    a <= "000101" when "00000",   -- 00h: n = 5
         "000100" when "00001",   -- 01h: a11 = 4
         "111110" when "00010",   -- 02h: a21 = -2
         "000001" when "00011",   -- 03h: a31 = 1
         "000011" when "00100",   -- 04h: a41 = 3
         "000000" when "00101",   -- 05h: a51 = 0
         "111110" when "00110",   -- 06h: a12 = -2
         "000110" when "00111",   -- 07h: a22 = 6
         "000010" when "01000",   -- 08h: a32 = 2
         "111111" when "01001",   -- 09h: a42 = -1
         "000101" when "01010",   -- 0Ah: a52 = 5
         "000001" when "01011",   -- 0Bh: a13 = 1
         "000010" when "01100",   -- 0Ch: a23 = 2
         "111001" when "01101",   -- 0Dh: a33 = -7
         "000100" when "01110",   -- 0Eh: a43 = 4
         "000010" when "01111",   -- 0Fh: a53 = 2
         "000011" when "10000",   -- 10h: a14 = 3
         "111111" when "10001",   -- 11h: a24 = -1
         "000100" when "10010",   -- 12h: a34 = 4
         "000101" when "10011",   -- 13h: a44 = 5
         "111101" when "10100",   -- 14h: a54 = -3
         "000000" when "10101",   -- 15h: a15 = 0
         "000101" when "10110",   -- 16h: a25 = 5
         "000010" when "10111",   -- 17h: a35 = 2
         "111101" when "11000",   -- 18h: a45 = -3
         "001000" when "11001",   -- 19h: a55 = 8
         "000000" when others;

end Behavioral;

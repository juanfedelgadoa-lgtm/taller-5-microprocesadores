----------------------------------------------------------------------------------
-- ALU DEL PROCESADOR (50 bits, combinacional)
--
-- Funcionamiento de la ALU (tabla del curso):
--
--     M  s1  s0  | Operacion
--     0   0   0  | not B
--     0   0   1  | A and B
--     0   1   0  | A or B
--     0   1   1  | A xnor B
--     1   0   0  | A + 1
--     1   0   1  | A + B
--     1   1   0  | A - B
--     1   1   1  | A - 1
--
-- Es el unico sumador/restador del procesador: el ASM de Bareiss la usa para
-- t1 - t2, para la division por restas sucesivas, para los valores absolutos
-- (0 - x) y para el +3 del algoritmo XS3.
--
-- Las cuatro operaciones aritmeticas usan un solo sumador  S = A + Bx + cin:
--     A + 1 : Bx = 0      , cin = 1
--     A + B : Bx = B      , cin = 0
--     A - B : Bx = not B  , cin = 1      (complemento a 2)
--     A - 1 : Bx = 1...1  , cin = 0      (sumar -1)
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity alu is
    Port ( A  : in  STD_LOGIC_VECTOR (49 downto 0);
           B  : in  STD_LOGIC_VECTOR (49 downto 0);
           M  : in  STD_LOGIC;
           s1 : in  STD_LOGIC;
           s0 : in  STD_LOGIC;
           S  : out STD_LOGIC_VECTOR (49 downto 0));
end alu;

architecture Behavioral of alu is

constant CERO50 : STD_LOGIC_VECTOR (49 downto 0) := (others => '0');
constant UNOS50 : STD_LOGIC_VECTOR (49 downto 0) := (others => '1');

signal sel     : STD_LOGIC_VECTOR (2 downto 0);
signal bx      : STD_LOGIC_VECTOR (49 downto 0);   -- segundo operando del sumador
signal cin     : STD_LOGIC;                        -- acarreo de entrada
signal suma    : STD_LOGIC_VECTOR (49 downto 0);   -- unidad aritmetica
signal logica  : STD_LOGIC_VECTOR (49 downto 0);   -- unidad logica

begin

sel <= M & s1 & s0;

-- Unidad aritmetica: un solo sumador
with sel select
    bx <= CERO50 when "100",          -- A + 1
          B      when "101",          -- A + B
          not B  when "110",          -- A - B
          UNOS50 when others;         -- A - 1

cin  <= '1' when (sel = "100" or sel = "110") else '0';

suma <= A + bx + cin;

-- Unidad logica
with sel select
    logica <= not B      when "000",
              A and B    when "001",
              A or B     when "010",
              A xnor B   when others;

-- Salida: M = 0 logica, M = 1 aritmetica
S <= logica when M = '0' else suma;

end Behavioral;

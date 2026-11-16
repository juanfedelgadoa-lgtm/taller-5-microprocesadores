----------------------------------------------------------------------------------
-- Universidad Distrital Francisco Jose de Caldas
-- Analisis y Diseno de Microprocesadores - Taller 5
--
-- VISUALIZADOR: ASM del algoritmo XS3 + display de 8 digitos
--
-- Caja negra:
--   entradas : clk, rst, tick (1 ms), final, dir_p, det (32), pivote (32)
--   salidas  : an (8), seg (7), dp, desborde
--
-- Funciona en paralelo con el procesador de Bareiss. Mientras final = 1 el ASM
-- XS3 convierte una y otra vez el valor elegido con dir_p:
--   dir_p = 0      -> det
--   dir_p = 1..5   -> pivote (el procesador entrega banco(dir_p))
-- Cada conversion tarda 376 ciclos (3,76 us), asi que al mover dir_p el
-- display cambia de inmediato. Mientras final = 0 (el procesador calcula) el
-- display conserva el ultimo valor.
--
-- Unidades funcionales propias (no se comparten con el procesador):
--   restador 0 - val (valor absoluto), sumador +3 (dig_mas3), comparador > 4.
-- Display: AN7 = signo ('-' o apagado), AN6..AN0 = 7 digitos decimales.
-- desborde = 1 si el valor tiene mas de 7 digitos.
-- Solo std_logic y std_logic_vector, salvo el tipo de los estados del ASM
-- (type estados_asm), declarado como en los ejemplos del curso.
-- Libreria std_logic_signed (det y pivote son con signo). Los digitos BCD (0 a
-- 9) se comparan con un '0' adelante para que 8 y 9 no se lean como negativos.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_signed.all;

entity visualizador is
    Port ( clk, rst : in  STD_LOGIC;
           tick     : in  STD_LOGIC;                       -- 1 ms (cambio de digito)
           final    : in  STD_LOGIC;
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
           det      : in  STD_LOGIC_VECTOR (31 downto 0);  -- complemento a 2
           pivote   : in  STD_LOGIC_VECTOR (31 downto 0);  -- complemento a 2
           an       : out STD_LOGIC_VECTOR (7 downto 0);
           seg      : out STD_LOGIC_VECTOR (6 downto 0);   -- seg(0)=CA ... seg(6)=CG
           dp       : out STD_LOGIC;
           desborde : out STD_LOGIC);
end visualizador;

architecture Behavioral of visualizador is

------------------------------------------------------------------------------
-- Estados del ASM XS3
------------------------------------------------------------------------------
-- x0  espera final = 1 ; toma |valor| y su signo
-- x1  PASO 1: registro decimal = 0
-- x2  PASO 2: LSB del decimal = MSB del binario ; PASO 5: fin tras 32 bits
-- x3  PASO 3: si digito(d) > 4, digito(d) = digito(d) + 3 (d = 0..9)
-- x4  PASO 4: corrimiento a la izquierda (decimal y binario)
-- x5  pasa el resultado al display
type estados_asm is (x0,x1,x2,x3,x4,x5);
signal xs : estados_asm;

------------------------------------------------------------------------------
-- Registros del ASM XS3
------------------------------------------------------------------------------
signal bin      : STD_LOGIC_VECTOR (31 downto 0);  -- registro binario
signal dec      : STD_LOGIC_VECTOR (39 downto 0);  -- registro decimal (10 digitos)
signal cont     : STD_LOGIC_VECTOR (4 downto 0);   -- bits procesados (0..31)
signal d        : STD_LOGIC_VECTOR (3 downto 0);   -- digito revisado (0..9)
signal neg      : STD_LOGIC;                       -- signo del valor
signal disp     : STD_LOGIC_VECTOR (39 downto 0);  -- valor que muestra el display
signal disp_neg : STD_LOGIC;

------------------------------------------------------------------------------
-- Senales combinacionales
------------------------------------------------------------------------------
signal val       : STD_LOGIC_VECTOR (31 downto 0); -- valor elegido con dir_p
signal dig       : STD_LOGIC_VECTOR (3 downto 0);  -- digito d del registro decimal
signal dig_mas3  : STD_LOGIC_VECTOR (3 downto 0);  -- digito d + 3

------------------------------------------------------------------------------
-- Display
------------------------------------------------------------------------------
signal dsel      : STD_LOGIC_VECTOR (2 downto 0);  -- digito encendido
signal car       : STD_LOGIC_VECTOR (3 downto 0);  -- 0-9, A = '-', F = apagado
signal car_signo : STD_LOGIC_VECTOR (3 downto 0);

begin

------------------------------------------------------------------------------
-- Camino de datos del XS3
------------------------------------------------------------------------------
val      <= det when dir_p = "000" else pivote;
dig_mas3 <= dig + 3;                                -- sumador +3

with d select
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

------------------------------------------------------------------------------
-- DIAGRAMA ASM DEL XS3
------------------------------------------------------------------------------
process (clk, rst)
begin

if rst = '1' then
    xs       <= x0;
    bin      <= (others => '0');
    dec      <= (others => '0');
    cont     <= "00000";
    d        <= "0000";
    neg      <= '0';
    disp     <= (others => '0');
    disp_neg <= '0';

elsif clk'event and clk = '1' then

    case xs is

        when x0 =>                              -- espera final ; bin = |val|
            if final = '1' then
                neg <= val(31);
                if val(31) = '1' then
                    bin <= x"00000000" - val;  -- valor absoluto
                else
                    bin <= val;
                end if;
                xs <= x1;
            else
                xs <= x0;
            end if;

        when x1 =>                              -- PASO 1: decimal = 0
            dec  <= (others => '0');
            cont <= "00000";
            xs   <= x2;

        when x2 =>                              -- PASO 2: LSB decimal = MSB binario
            dec(0) <= bin(31);
            if cont = "11111" then
                xs <= x5;                       -- PASO 5: ya entraron los 32 bits
            else
                d  <= "0000";
                xs <= x3;
            end if;

        when x3 =>                              -- PASO 3: si digito(d) > 4, sumar 3
            if ('0' & dig) > 4 then
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
                xs <= x4;
            else
                d  <= d + 1;
                xs <= x3;
            end if;

        when x4 =>                              -- PASO 4: corrimiento a la izquierda
            dec  <= dec(38 downto 0) & '0';
            bin  <= bin(30 downto 0) & '0';
            cont <= cont + 1;
            xs   <= x2;

        when x5 =>                              -- resultado al display
            disp     <= dec;
            disp_neg <= neg;
            xs       <= x0;

        when others =>
            xs <= x0;

    end case;
end if;
end process;

------------------------------------------------------------------------------
-- DISPLAY DE 8 DIGITOS (anodo comun, activos en bajo)
-- Cambia de digito con cada tick (1 ms): barrido completo de 8 ms.
------------------------------------------------------------------------------
process (clk, rst)
begin
if rst = '1' then
    dsel <= "000";
elsif clk'event and clk = '1' then
    if tick = '1' then
        dsel <= dsel + 1;
    end if;
end if;
end process;

car_signo <= "1010" when disp_neg = '1' else "1111";

with dsel select
    car <= disp(3 downto 0)   when "000",
           disp(7 downto 4)   when "001",
           disp(11 downto 8)  when "010",
           disp(15 downto 12) when "011",
           disp(19 downto 16) when "100",
           disp(23 downto 20) when "101",
           disp(27 downto 24) when "110",
           car_signo          when others;

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

dp       <= '1';
desborde <= '0' when disp(39 downto 28) = x"000" else '1';

end Behavioral;

----------------------------------------------------------------------------------
-- Universidad Distrital Francisco Jose de Caldas
-- Analisis y Diseno de Microprocesadores - Taller 5
--
-- TOPE PARA LA NEXYS A7-100T (solo conexiones, descripcion estructural)
--
-- Une los 4 bloques del diseno:
--   divisor_frecuencia  -> tick de 1 ms
--   antirrebote         -> un pulso de inicio por cada pulsacion de BTNC
--   procesador_bareiss  -> ASM de Bareiss: det, pivote y final (en binario)
--   visualizador        -> ASM XS3 + display de 8 digitos
-- ISE necesita una entidad superior para asignar los pines (archivo .ucf);
-- este archivo no tiene logica propia.
--
-- Herramienta: Xilinx ISE 14.7. Reloj de la tarjeta: 100 MHz (pin E3).
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity det_bareiss is
    Port ( clk      : in  STD_LOGIC;                      -- 100 MHz
           rst      : in  STD_LOGIC;                      -- BTNU
           inicio   : in  STD_LOGIC;                      -- BTNC
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);  -- SW2..SW0
           final    : out STD_LOGIC;                      -- LD0
           desborde : out STD_LOGIC;                      -- LD1: mas de 7 digitos
           an       : out STD_LOGIC_VECTOR (7 downto 0);
           seg      : out STD_LOGIC_VECTOR (6 downto 0);
           dp       : out STD_LOGIC);
end det_bareiss;

architecture Estructural of det_bareiss is

component divisor_frecuencia
    Port ( clk, rst : in  STD_LOGIC;
           tick_1ms : out STD_LOGIC);
end component;

component antirrebote
    Port ( clk, rst : in  STD_LOGIC;
           tick     : in  STD_LOGIC;
           boton    : in  STD_LOGIC;
           pulso    : out STD_LOGIC);
end component;

component procesador_bareiss
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
           det      : out STD_LOGIC_VECTOR (31 downto 0);
           pivote   : out STD_LOGIC_VECTOR (31 downto 0);
           final    : out STD_LOGIC);
end component;

component visualizador
    Port ( clk, rst : in  STD_LOGIC;
           tick     : in  STD_LOGIC;
           final    : in  STD_LOGIC;
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
           det      : in  STD_LOGIC_VECTOR (31 downto 0);
           pivote   : in  STD_LOGIC_VECTOR (31 downto 0);
           an       : out STD_LOGIC_VECTOR (7 downto 0);
           seg      : out STD_LOGIC_VECTOR (6 downto 0);
           dp       : out STD_LOGIC;
           desborde : out STD_LOGIC);
end component;

signal tick_1ms, pulso_inicio, fin : STD_LOGIC;
signal det, pivote : STD_LOGIC_VECTOR (31 downto 0);

begin

U_FREC : divisor_frecuencia port map (
    clk => clk, rst => rst, tick_1ms => tick_1ms);

U_ANTI : antirrebote port map (
    clk => clk, rst => rst, tick => tick_1ms, boton => inicio, pulso => pulso_inicio);

U_PROC : procesador_bareiss port map (
    clk => clk, rst => rst, inicio => pulso_inicio, dir_p => dir_p,
    det => det, pivote => pivote, final => fin);

U_VIS : visualizador port map (
    clk => clk, rst => rst, tick => tick_1ms, final => fin, dir_p => dir_p,
    det => det, pivote => pivote, an => an, seg => seg, dp => dp, desborde => desborde);

final <= fin;

end Estructural;

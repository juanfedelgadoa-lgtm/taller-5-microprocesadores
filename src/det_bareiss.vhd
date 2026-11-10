----------------------------------------------------------------------------------
-- Universidad Distrital Francisco Jose de Caldas
-- Analisis y Diseno de Microprocesadores - Taller 5
--
-- TOPE PARA LA NEXYS A7-100T (descripcion estructural)
--
--   divisor_frecuencia -> tick de 1 ms y onda de 1 s
--   antirrebote        -> un pulso de inicio por cada pulsacion de BTNC
--   sincronizador      -> switches dir_p (SW2..SW0)
--   procesador         -> ASM de Bareiss con sus bloques (ROM, RAM, division, XS3...)
--   display_8dig       -> muestra det (dir_p = 0) o el pivote dir_p (1..5)
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
           latido   : out STD_LOGIC;                      -- LD15: onda de 1 s
           an       : out STD_LOGIC_VECTOR (7 downto 0);
           seg      : out STD_LOGIC_VECTOR (6 downto 0);
           dp       : out STD_LOGIC);
end det_bareiss;

architecture Estructural of det_bareiss is

component divisor_frecuencia
    Port ( clk, rst : in  STD_LOGIC;
           tick_1ms : out STD_LOGIC;
           onda_1s  : out STD_LOGIC);
end component;

component antirrebote
    Port ( clk, rst : in  STD_LOGIC;
           tick     : in  STD_LOGIC;
           boton    : in  STD_LOGIC;
           pulso    : out STD_LOGIC);
end component;

component sincronizador
    Port ( clk, rst : in  STD_LOGIC;
           entrada  : in  STD_LOGIC_VECTOR (2 downto 0);
           salida   : out STD_LOGIC_VECTOR (2 downto 0));
end component;

component procesador
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
           det      : out STD_LOGIC_VECTOR (39 downto 0);
           det_neg  : out STD_LOGIC;
           pivote   : out STD_LOGIC_VECTOR (39 downto 0);
           piv_neg  : out STD_LOGIC;
           final    : out STD_LOGIC);
end component;

component display_8dig
    Port ( clk, rst : in  STD_LOGIC;
           tick     : in  STD_LOGIC;
           bcd      : in  STD_LOGIC_VECTOR (27 downto 0);
           neg      : in  STD_LOGIC;
           an       : out STD_LOGIC_VECTOR (7 downto 0);
           seg      : out STD_LOGIC_VECTOR (6 downto 0);
           dp       : out STD_LOGIC);
end component;

constant CERO12 : STD_LOGIC_VECTOR (11 downto 0) := x"000";

signal tick_1ms, pulso_inicio : STD_LOGIC;
signal dir_p_s     : STD_LOGIC_VECTOR (2 downto 0);
signal det, pivote, mostrar : STD_LOGIC_VECTOR (39 downto 0);
signal det_neg, piv_neg, mostrar_neg : STD_LOGIC;

begin

U_FREC : divisor_frecuencia port map (clk => clk, rst => rst, tick_1ms => tick_1ms, onda_1s => latido);

U_ANTI : antirrebote port map (clk => clk, rst => rst, tick => tick_1ms, boton => inicio, pulso => pulso_inicio);

U_SINC : sincronizador port map (clk => clk, rst => rst, entrada => dir_p, salida => dir_p_s);

U_PROC : procesador port map (
    clk => clk, rst => rst, inicio => pulso_inicio, dir_p => dir_p_s,
    det => det, det_neg => det_neg, pivote => pivote, piv_neg => piv_neg, final => final);

-- Que se muestra: dir_p = 0 -> determinante ; dir_p = 1..5 -> pivote dir_p
mostrar     <= det     when dir_p_s = "000" else pivote;
mostrar_neg <= det_neg when dir_p_s = "000" else piv_neg;
desborde    <= '0' when mostrar(39 downto 28) = CERO12 else '1';

U_DISP : display_8dig port map (
    clk => clk, rst => rst, tick => tick_1ms, bcd => mostrar(27 downto 0), neg => mostrar_neg,
    an => an, seg => seg, dp => dp);

end Estructural;

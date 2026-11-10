----------------------------------------------------------------------------------
-- PROCESADOR: unidad de control (ASM) + camino de datos (descripcion estructural)
--
-- Caja negra:
--   entradas : clk, rst, inicio, dir_p (direccion del pivote, 1..n)
--   salidas  : det (BCD) + det_neg, pivote (BCD) + piv_neg, final
--
-- Bloques internos (cada uno en su archivo):
--   asm_bareiss       ASM principal (unidad de control y registros del algoritmo)
--   rom_matriz        ROM con la matriz (direccion dira, dato a)
--   RAM_memory        RAM de trabajo (modelo del curso)
--   multiplicador     unico multiplicador
--   sumador_restador  unico sumador/restador
--   bloque_division   division por restas sucesivas (ASM propio)
--   xs3               conversion binario -> BCD (ASM propio)
--   banco_pivotes     banco de registros de los pivotes
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity procesador is
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
           det      : out STD_LOGIC_VECTOR (39 downto 0);
           det_neg  : out STD_LOGIC;
           pivote   : out STD_LOGIC_VECTOR (39 downto 0);
           piv_neg  : out STD_LOGIC;
           final    : out STD_LOGIC);
end procesador;

architecture Estructural of procesador is

component asm_bareiss
    Port ( clk, rst   : in  STD_LOGIC;
           inicio     : in  STD_LOGIC;
           dir_p      : in  STD_LOGIC_VECTOR (2 downto 0);
           dira       : out STD_LOGIC_VECTOR (4 downto 0);
           a          : in  STD_LOGIC_VECTOR (5 downto 0);
           rd_add     : out STD_LOGIC_VECTOR (5 downto 0);
           wr_add     : out STD_LOGIC_VECTOR (5 downto 0);
           we         : out STD_LOGIC;
           data       : out STD_LOGIC_VECTOR (31 downto 0);
           q          : in  STD_LOGIC_VECTOR (31 downto 0);
           mul_a      : out STD_LOGIC_VECTOR (24 downto 0);
           mul_b      : out STD_LOGIC_VECTOR (24 downto 0);
           producto   : in  STD_LOGIC_VECTOR (49 downto 0);
           sr_a       : out STD_LOGIC_VECTOR (49 downto 0);
           sr_b       : out STD_LOGIC_VECTOR (49 downto 0);
           sr_op      : out STD_LOGIC;
           resultado  : in  STD_LOGIC_VECTOR (49 downto 0);
           ini_div    : out STD_LOGIC;
           dividendo  : out STD_LOGIC_VECTOR (49 downto 0);
           divisor    : out STD_LOGIC_VECTOR (31 downto 0);
           cociente   : in  STD_LOGIC_VECTOR (31 downto 0);
           fin_div    : in  STD_LOGIC;
           clr_banco  : out STD_LOGIC;
           we_banco   : out STD_LOGIC;
           dir_banco  : out STD_LOGIC_VECTOR (2 downto 0);
           dato_banco : out STD_LOGIC_VECTOR (31 downto 0);
           piv_banco  : in  STD_LOGIC_VECTOR (31 downto 0);
           ini_xs3    : out STD_LOGIC;
           bin_xs3    : out STD_LOGIC_VECTOR (31 downto 0);
           bcd_xs3    : in  STD_LOGIC_VECTOR (39 downto 0);
           fin_xs3    : in  STD_LOGIC;
           det        : out STD_LOGIC_VECTOR (39 downto 0);
           det_neg    : out STD_LOGIC;
           pivote     : out STD_LOGIC_VECTOR (39 downto 0);
           piv_neg    : out STD_LOGIC;
           final      : out STD_LOGIC);
end component;

component rom_matriz
    Port ( dira : in  STD_LOGIC_VECTOR (4 downto 0);
           a    : out STD_LOGIC_VECTOR (5 downto 0));
end component;

component RAM_memory
    port ( c      : in  std_logic;
           data   : in  std_logic_vector (31 downto 0);
           wr_add : in  std_logic_vector (5 downto 0);
           rd_add : in  std_logic_vector (5 downto 0);
           we     : in  std_logic;
           q      : out std_logic_vector (31 downto 0));
end component;

component multiplicador
    Port ( a : in  STD_LOGIC_VECTOR (24 downto 0);
           b : in  STD_LOGIC_VECTOR (24 downto 0);
           p : out STD_LOGIC_VECTOR (49 downto 0));
end component;

component sumador_restador
    Port ( a  : in  STD_LOGIC_VECTOR (49 downto 0);
           b  : in  STD_LOGIC_VECTOR (49 downto 0);
           op : in  STD_LOGIC;
           s  : out STD_LOGIC_VECTOR (49 downto 0));
end component;

component bloque_division
    Port ( clk, rst  : in  STD_LOGIC;
           inicio    : in  STD_LOGIC;
           dividendo : in  STD_LOGIC_VECTOR (49 downto 0);
           divisor   : in  STD_LOGIC_VECTOR (31 downto 0);
           cociente  : out STD_LOGIC_VECTOR (31 downto 0);
           final     : out STD_LOGIC);
end component;

component xs3
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;
           bin_in   : in  STD_LOGIC_VECTOR (31 downto 0);
           bcd      : out STD_LOGIC_VECTOR (39 downto 0);
           final    : out STD_LOGIC);
end component;

component banco_pivotes
    Port ( clk, rst : in  STD_LOGIC;
           clr      : in  STD_LOGIC;
           we       : in  STD_LOGIC;
           dir_w    : in  STD_LOGIC_VECTOR (2 downto 0);
           dato     : in  STD_LOGIC_VECTOR (31 downto 0);
           dir_r    : in  STD_LOGIC_VECTOR (2 downto 0);
           q        : out STD_LOGIC_VECTOR (31 downto 0));
end component;

-- ROM
signal dira : STD_LOGIC_VECTOR (4 downto 0);
signal a    : STD_LOGIC_VECTOR (5 downto 0);
-- RAM
signal rd_add, wr_add : STD_LOGIC_VECTOR (5 downto 0);
signal we             : STD_LOGIC;
signal data, q        : STD_LOGIC_VECTOR (31 downto 0);
-- multiplicador
signal mul_a, mul_b : STD_LOGIC_VECTOR (24 downto 0);
signal producto     : STD_LOGIC_VECTOR (49 downto 0);
-- sumador/restador
signal sr_a, sr_b, resultado : STD_LOGIC_VECTOR (49 downto 0);
signal sr_op                 : STD_LOGIC;
-- division
signal ini_div, fin_div : STD_LOGIC;
signal dividendo        : STD_LOGIC_VECTOR (49 downto 0);
signal divisor, cociente : STD_LOGIC_VECTOR (31 downto 0);
-- banco de pivotes
signal clr_banco, we_banco : STD_LOGIC;
signal dir_banco           : STD_LOGIC_VECTOR (2 downto 0);
signal dato_banco, piv_banco : STD_LOGIC_VECTOR (31 downto 0);
-- XS3
signal ini_xs3, fin_xs3 : STD_LOGIC;
signal bin_xs3          : STD_LOGIC_VECTOR (31 downto 0);
signal bcd_xs3          : STD_LOGIC_VECTOR (39 downto 0);

begin

U_ASM : asm_bareiss port map (
    clk => clk, rst => rst, inicio => inicio, dir_p => dir_p,
    dira => dira, a => a,
    rd_add => rd_add, wr_add => wr_add, we => we, data => data, q => q,
    mul_a => mul_a, mul_b => mul_b, producto => producto,
    sr_a => sr_a, sr_b => sr_b, sr_op => sr_op, resultado => resultado,
    ini_div => ini_div, dividendo => dividendo, divisor => divisor,
    cociente => cociente, fin_div => fin_div,
    clr_banco => clr_banco, we_banco => we_banco, dir_banco => dir_banco,
    dato_banco => dato_banco, piv_banco => piv_banco,
    ini_xs3 => ini_xs3, bin_xs3 => bin_xs3, bcd_xs3 => bcd_xs3, fin_xs3 => fin_xs3,
    det => det, det_neg => det_neg, pivote => pivote, piv_neg => piv_neg,
    final => final);

U_ROM : rom_matriz port map (dira => dira, a => a);

U_RAM : RAM_memory port map (
    c => clk, data => data, wr_add => wr_add, rd_add => rd_add, we => we, q => q);

U_MUL : multiplicador port map (a => mul_a, b => mul_b, p => producto);

U_SR : sumador_restador port map (a => sr_a, b => sr_b, op => sr_op, s => resultado);

U_DIV : bloque_division port map (
    clk => clk, rst => rst, inicio => ini_div, dividendo => dividendo,
    divisor => divisor, cociente => cociente, final => fin_div);

U_XS3 : xs3 port map (
    clk => clk, rst => rst, inicio => ini_xs3, bin_in => bin_xs3,
    bcd => bcd_xs3, final => fin_xs3);

U_BANCO : banco_pivotes port map (
    clk => clk, rst => rst, clr => clr_banco, we => we_banco, dir_w => dir_banco,
    dato => dato_banco, dir_r => dir_p, q => piv_banco);

end Estructural;

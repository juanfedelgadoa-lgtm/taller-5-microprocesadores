----------------------------------------------------------------------------------
-- TESTBENCH SENCILLO PARA LAS FIGURAS DE SIMULACION DEL INFORME
--
-- Conecta el procesador de Bareiss con el visualizador (sin antirrebote ni
-- divisor de frecuencia, para ver todo en pocos ciclos):
--   1. rst = 1 durante 20 ns.
--   2. Pulso de inicio de un ciclo (como el que entrega el antirrebote).
--   3. Espera final = 1 y deja dir_p = 0 ESPERA ciclos (el visualizador
--      convierte det en 376 ciclos).
--   4. Recorre dir_p = 1..N (PASO_P ciclos cada uno) para ver los pivotes en
--      la salida pivote. N es el tamano de la matriz que tenga la ROM.
-- No compara resultados: las comprobaciones automaticas estan en
-- tb_procesador.vhd, tb_visualizador.vhd y tb_det_bareiss.vhd.
-- En ISim: agregar a la ventana de ondas st, i, j, k y cociente de uut, y
-- xs, bin, dec, cont y disp de uvis.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity tb_informe is
    generic ( ESPERA : integer := 400;          -- ciclos con dir_p = 0 despues de final
              N      : integer := 5;            -- pivotes que se recorren con dir_p
              PASO_P : integer := 10 );         -- ciclos que se muestra cada pivote
end tb_informe;

architecture sim of tb_informe is

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

    signal clk      : STD_LOGIC := '0';
    signal rst      : STD_LOGIC := '1';
    signal inicio   : STD_LOGIC := '0';
    signal dir_p    : STD_LOGIC_VECTOR (2 downto 0) := "000";
    signal det      : STD_LOGIC_VECTOR (31 downto 0);
    signal pivote   : STD_LOGIC_VECTOR (31 downto 0);
    signal final    : STD_LOGIC;
    signal an       : STD_LOGIC_VECTOR (7 downto 0);
    signal seg      : STD_LOGIC_VECTOR (6 downto 0);
    signal dp       : STD_LOGIC;
    signal desborde : STD_LOGIC;

begin

    uut  : procesador_bareiss port map (clk => clk, rst => rst, inicio => inicio, dir_p => dir_p,
                                        det => det, pivote => pivote, final => final);

    uvis : visualizador port map (clk => clk, rst => rst, tick => '0', final => final, dir_p => dir_p,
                                  det => det, pivote => pivote, an => an, seg => seg, dp => dp,
                                  desborde => desborde);

    clk <= not clk after 5 ns;                  -- reloj de 100 MHz

    process
    begin
        rst <= '1';
        wait for 20 ns;
        rst <= '0';
        wait for 20 ns;
        inicio <= '1';                          -- pulso de un ciclo
        wait for 10 ns;
        inicio <= '0';
        wait until final = '1';
        wait for ESPERA * 10 ns;                -- dir_p = 0: se ve det
        dir_p <= "001";
        wait for PASO_P * 10 ns;
        dir_p <= "010";
        wait for PASO_P * 10 ns;
        if N > 2 then
            dir_p <= "011";
            wait for PASO_P * 10 ns;
        end if;
        if N > 3 then
            dir_p <= "100";
            wait for PASO_P * 10 ns;
        end if;
        if N > 4 then
            dir_p <= "101";
            wait for PASO_P * 10 ns;
        end if;
        dir_p <= "000";
        wait;
    end process;

end sim;

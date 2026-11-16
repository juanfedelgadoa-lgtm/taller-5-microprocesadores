----------------------------------------------------------------------------------
-- TESTBENCH DEL PROCESADOR DE BAREISS (autoverificado)
--
-- Lee la matriz de sim/rom_prueba.vhd (copia de la ROM), calcula el
-- determinante y los pivotes esperados con pkg_prueba y los compara con las
-- salidas binarias del procesador:
--   1. Pulso de inicio (un ciclo, como el que entrega el antirrebote).
--   2. Espera final y compara det.
--   3. Recorre dir_p = 1..n y compara cada pivote (el pivote n debe ser det).
--   4. Repite el calculo con un segundo inicio desde el estado final.
-- Sirve para cualquier matriz: si se cambia la ROM con sim/modelo_referencia.py,
-- no hay que tocar este archivo (el script tambien cambia sim/rom_prueba.vhd).
--
-- Solo para simulacion (usa variables, integer, real, string y wait).
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_arith.all;
use work.pkg_prueba.all;

entity tb_procesador is
    generic ( CORRIDAS : integer := 2 );   -- 1 para la matriz extrema (19 M ciclos)
end tb_procesador;

architecture sim of tb_procesador is

    component procesador_bareiss
        Port ( clk, rst : in  STD_LOGIC;
               inicio   : in  STD_LOGIC;
               dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
               det      : out STD_LOGIC_VECTOR (31 downto 0);
               pivote   : out STD_LOGIC_VECTOR (31 downto 0);
               final    : out STD_LOGIC);
    end component;

    component rom_matriz
        Port ( dira : in  STD_LOGIC_VECTOR (4 downto 0);
               a    : out STD_LOGIC_VECTOR (5 downto 0));
    end component;

    constant T : time := 10 ns;                      -- 100 MHz

    signal clk     : std_logic := '0';
    signal rst     : std_logic := '1';
    signal inicio  : std_logic := '0';
    signal dir_p   : std_logic_vector(2 downto 0) := "000";
    signal det     : std_logic_vector(31 downto 0);
    signal pivote  : std_logic_vector(31 downto 0);
    signal final   : std_logic;
    signal dir_tb  : std_logic_vector(4 downto 0) := "00000";
    signal a_tb    : std_logic_vector(5 downto 0);
    signal fin_sim : boolean := false;

begin

    uut : procesador_bareiss port map (
        clk => clk, rst => rst, inicio => inicio, dir_p => dir_p,
        det => det, pivote => pivote, final => final);

    U_ROM_TB : rom_matriz port map (dira => dir_tb, a => a_tb);   -- lectura de la matriz

    clk <= not clk after T/2 when not fin_sim else '0';

    estimulos : process
        variable n       : integer;
        variable m       : matriz_r;
        variable ref     : resultado_ref;
        variable dir     : integer;
        variable errores : integer := 0;
        variable ciclos  : integer;

        procedure espera_final (maximo : integer; c : out integer) is
            variable cc : integer := 0;
        begin
            while final /= '1' and cc < maximo loop
                wait until rising_edge(clk);
                cc := cc + 1;
            end loop;
            c := cc;
        end procedure;

        procedure pulso_inicio is
        begin
            wait until falling_edge(clk);
            inicio <= '1';
            wait until falling_edge(clk);
            inicio <= '0';
        end procedure;

        procedure compara (nombre : string; obtenido : std_logic_vector; esperado : integer) is
            variable v : integer;
        begin
            v := conv_integer(signed(obtenido));
            if v = esperado then
                report nombre & " = " & texto_valor(v) & "  OK";
            else
                report nombre & " = " & texto_valor(v) & "  esperado " & texto_valor(esperado) &
                       "  ERROR" severity error;
                errores := errores + 1;
            end if;
        end procedure;

    begin
        ------------------------------------------------------------------
        -- Lectura de la matriz y valores esperados
        ------------------------------------------------------------------
        dir_tb <= "00000";
        wait for 1 ns;
        n := conv_integer(signed(a_tb));
        dir := 1;
        for jj in 1 to n loop
            for ii in 1 to n loop
                dir_tb <= conv_std_logic_vector(dir, 5);
                wait for 1 ns;
                m(ii)(jj) := real(conv_integer(signed(a_tb)));
                dir := dir + 1;
            end loop;
        end loop;
        ref := bareiss_ref(m, n);
        report "Matriz de la ROM: " & integer'image(n) & "x" & integer'image(n) &
               "   det esperado = " & integer'image(ref.det) &
               "   intercambios de filas = " & integer'image(ref.cambios);

        ------------------------------------------------------------------
        -- Calculo
        ------------------------------------------------------------------
        wait for 5 * T;
        rst <= '0';
        wait for 5 * T;

        for corrida in 1 to CORRIDAS loop
            dir_p <= "000";
            pulso_inicio;
            wait for 2 * T;
            assert final = '0' report "final no bajo al iniciar" severity error;
            espera_final(40000000, ciclos);
            if final /= '1' then
                report "TIEMPO AGOTADO" severity error;
                errores := errores + 1;
            end if;
            report "Corrida " & integer'image(corrida) & ": final = 1 en " &
                   integer'image(ciclos) & " ciclos";
            compara("   det           ", det, ref.det);

            for kk in 1 to n loop
                dir_p <= conv_std_logic_vector(kk, 3);
                wait for 2 * T;
                compara("   pivote dir_p=" & integer'image(kk), pivote, ref.piv(kk));
            end loop;

            -- el ultimo pivote es el determinante
            if pivote /= det then
                report "   el pivote n no es igual al determinante  ERROR" severity error;
                errores := errores + 1;
            end if;

            -- dir_p = 0 no es un pivote: el banco entrega 0
            dir_p <= "000";
            wait for 2 * T;
            compara("   pivote dir_p=0", pivote, 0);
        end loop;

        if errores = 0 then
            report "TODAS LAS PRUEBAS PASARON";
        else
            report "PRUEBAS CON ERRORES: " & integer'image(errores) severity failure;
        end if;
        fin_sim <= true;
        wait;
    end process;

end sim;

----------------------------------------------------------------------------------
-- TESTBENCH DEL PROCESADOR (autoverificado)
--
-- Lee la matriz de src/rom_matriz.vhd (con otra instancia de la misma ROM),
-- calcula el determinante y los pivotes esperados con pkg_prueba y los compara
-- con las salidas del procesador:
--   1. Pulso de inicio (un ciclo, como el que entrega el antirrebote).
--   2. Espera final y compara det.
--   3. Recorre dir_p = 1..n y compara cada pivote (el pivote n debe ser det).
--   4. Repite el calculo con un segundo inicio desde el estado final.
-- Sirve para cualquier matriz: si se cambia la ROM, no hay que tocar este archivo.
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

    component rom_matriz
        Port ( dira : in  STD_LOGIC_VECTOR (4 downto 0);
               a    : out STD_LOGIC_VECTOR (5 downto 0));
    end component;

    constant T : time := 10 ns;                      -- 100 MHz

    signal clk     : std_logic := '0';
    signal rst     : std_logic := '1';
    signal inicio  : std_logic := '0';
    signal dir_p   : std_logic_vector(2 downto 0) := "000";
    signal det     : std_logic_vector(39 downto 0);
    signal pivote  : std_logic_vector(39 downto 0);
    signal det_neg, piv_neg, final : std_logic;
    signal dir_tb  : std_logic_vector(4 downto 0) := "00000";
    signal a_tb    : std_logic_vector(5 downto 0);
    signal fin_sim : boolean := false;

begin

    uut : procesador port map (
        clk => clk, rst => rst, inicio => inicio, dir_p => dir_p,
        det => det, det_neg => det_neg, pivote => pivote, piv_neg => piv_neg, final => final);

    U_ROM_TB : rom_matriz port map (dira => dir_tb, a => a_tb);   -- lectura de la matriz

    clk <= not clk after T/2 when not fin_sim else '0';

    estimulos : process
        variable n       : integer;
        variable m       : matriz_r;
        variable ref     : resultado_ref;
        variable dir     : integer;
        variable errores : integer := 0;
        variable ciclos  : integer;
        variable txt     : string(1 to 11);

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

        procedure compara (nombre : string; obtenido, esperado : string) is
        begin
            if obtenido = esperado then
                report nombre & " = '" & obtenido & "'  OK";
            else
                report nombre & " = '" & obtenido & "'  esperado '" & esperado & "'  ERROR"
                    severity error;
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
            compara("   det          ", texto_bcd(det, det_neg), texto_valor(ref.det));

            for kk in 1 to n loop
                dir_p <= conv_std_logic_vector(kk, 3);
                wait for 3 * T;
                espera_final(2000, ciclos);
                compara("   pivote dir_p=" & integer'image(kk), texto_bcd(pivote, piv_neg),
                        texto_valor(ref.piv(kk)));
            end loop;

            -- el ultimo pivote es el determinante
            if texto_bcd(pivote, piv_neg) /= texto_bcd(det, det_neg) then
                report "   el pivote n no es igual al determinante  ERROR" severity error;
                errores := errores + 1;
            end if;

            dir_p <= "000";
            wait for 3 * T;
            espera_final(2000, ciclos);
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

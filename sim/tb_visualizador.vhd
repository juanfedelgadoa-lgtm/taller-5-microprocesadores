----------------------------------------------------------------------------------
-- TESTBENCH DEL VISUALIZADOR (ASM XS3 + display), autoverificado
--
-- Pone valores en det o en pivote, sube final y lee los 8 digitos
-- decodificando an/seg durante un barrido. Usa un tick rapido (cada 8 ciclos)
-- para no simular milisegundos. Comprueba:
--   1. Antes del primer final el display muestra 0.
--   2. Conversion de varios valores (positivos, negativos, 7 digitos,
--      mas de 7 digitos con desborde, el maximo de 32 bits).
--   3. dir_p /= 0 muestra el pivote.
--   4. Con final = 0 el display conserva el ultimo valor.
--
-- Solo para simulacion (usa variables, integer, string y wait).
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_arith.all;
use work.pkg_prueba.all;

entity tb_visualizador is
end tb_visualizador;

architecture sim of tb_visualizador is

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

    constant T : time := 10 ns;

    signal clk      : std_logic := '0';
    signal rst      : std_logic := '1';
    signal tick     : std_logic := '0';
    signal final    : std_logic := '0';
    signal dir_p    : std_logic_vector(2 downto 0) := "000";
    signal det      : std_logic_vector(31 downto 0) := (others => '0');
    signal pivote   : std_logic_vector(31 downto 0) := (others => '0');
    signal an       : std_logic_vector(7 downto 0);
    signal seg      : std_logic_vector(6 downto 0);
    signal dp, desborde : std_logic;
    signal fin_sim  : boolean := false;

    function decodifica (s : std_logic_vector(6 downto 0)) return character is
    begin
        case s is
            when "1000000" => return '0';
            when "1111001" => return '1';
            when "0100100" => return '2';
            when "0110000" => return '3';
            when "0011001" => return '4';
            when "0010010" => return '5';
            when "0000010" => return '6';
            when "1111000" => return '7';
            when "0000000" => return '8';
            when "0010000" => return '9';
            when "0111111" => return '-';
            when "1111111" => return ' ';
            when others    => return '?';
        end case;
    end function;

begin

    uut : visualizador port map (
        clk => clk, rst => rst, tick => tick, final => final, dir_p => dir_p,
        det => det, pivote => pivote, an => an, seg => seg, dp => dp, desborde => desborde);

    clk <= not clk after T/2 when not fin_sim else '0';

    -- tick rapido: un ciclo de cada 8
    process
    begin
        wait until rising_edge(clk);
        for c in 1 to 7 loop
            wait until rising_edge(clk);
        end loop;
        tick <= '1';
        wait until rising_edge(clk);
        tick <= '0';
    end process;

    estimulos : process
        variable errores : integer := 0;
        variable txt     : string(1 to 8);

        procedure lee_display (texto : out string) is
            variable tt : string(1 to 8);
        begin
            tt := (others => '?');
            for c in 1 to 80 loop                -- barrido completo: 8 x 8 ciclos
                wait until falling_edge(clk);
                for dd in 0 to 7 loop
                    if an(dd) = '0' then
                        tt(8 - dd) := decodifica(seg);
                    end if;
                end loop;
            end loop;
            texto := tt;
        end procedure;

        procedure compara (nombre : string; esperado : string; desb : std_logic) is
            variable tt : string(1 to 8);
        begin
            lee_display(tt);
            if tt = esperado and desborde = desb then
                report nombre & " display='" & tt & "' desborde=" & std_logic'image(desborde) & "  OK";
            else
                report nombre & " display='" & tt & "' desborde=" & std_logic'image(desborde) &
                       "  esperado '" & esperado & "' " & std_logic'image(desb) & "  ERROR"
                       severity error;
                errores := errores + 1;
            end if;
        end procedure;

        procedure prueba (v : integer; por_pivote : boolean) is
            variable desb : std_logic;
        begin
            if por_pivote then
                pivote <= conv_std_logic_vector(v, 32);
                det    <= conv_std_logic_vector(1, 32);
                dir_p  <= "011";
            else
                det    <= conv_std_logic_vector(v, 32);
                pivote <= conv_std_logic_vector(1, 32);
                dir_p  <= "000";
            end if;
            final <= '1';
            for c in 1 to 1000 loop              -- mas de dos conversiones (376 ciclos c/u)
                wait until rising_edge(clk);
            end loop;
            if v >= 10000000 or v <= -10000000 then
                desb := '1';
            else
                desb := '0';
            end if;
            if por_pivote then
                compara("pivote (dir_p=3) =" & texto_valor(v), texto_display(v), desb);
            else
                compara("det    (dir_p=0) =" & texto_valor(v), texto_display(v), desb);
            end if;
        end procedure;

    begin
        wait for 5 * T;
        rst <= '0';
        wait for 5 * T;

        -- 1. antes del primer final
        compara("sin calcular (final=0)          ", texto_display(0), '0');

        -- 2. y 3. conversiones
        prueba(0, false);
        prueba(7, false);
        prueba(362, false);
        prueba(-170, false);
        prueba(9999999, false);
        prueba(-9999999, false);
        prueba(10000000, false);
        prueba(-17121828, false);
        prueba(2147483647, false);
        prueba(-2147483647, false);
        prueba(-639, true);
        prueba(277564, true);

        -- 4. con final = 0 el display no cambia
        final <= '0';
        wait until rising_edge(clk);
        det   <= conv_std_logic_vector(123, 32);
        dir_p <= "000";
        for c in 1 to 1000 loop
            wait until rising_edge(clk);
        end loop;
        compara("final=0, det=123 (se conserva)  ", texto_display(277564), '0');
        final <= '1';
        for c in 1 to 1000 loop
            wait until rising_edge(clk);
        end loop;
        compara("final=1 otra vez, det=123       ", texto_display(123), '0');

        if errores = 0 then
            report "TODAS LAS PRUEBAS PASARON";
        else
            report "PRUEBAS CON ERRORES: " & integer'image(errores) severity failure;
        end if;
        fin_sim <= true;
        wait;
    end process;

end sim;

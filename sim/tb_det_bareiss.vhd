----------------------------------------------------------------------------------
-- Testbench del Taller 5: determinante por Bareiss + XS3
--
-- Para cada una de las 8 matrices de la ROM:
--   1. Pulsa "inicio" y espera "final".
--   2. Lee los 8 digitos del display decodificando an/seg (igual que el ojo).
--   3. Compara con el valor del modelo de referencia (modelo_referencia.py).
--   4. Recorre los pivotes con sw_piv = 1..n-1 y los compara.
--
-- El refresco del display se acelera con N_REF = 5 para simular rapido.
-- (El testbench si usa variables; la restriccion de "solo senales" aplica al
--  diseno, no al banco de pruebas.)
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

entity tb_det_bareiss is
    -- MAX_MATRIZ = 6 prueba las paginas 0..6 (~0,2 ms simulados).
    -- MAX_MATRIZ = 7 agrega la 5x5 extrema: ~19 millones de ciclos de
    -- division (190 ms simulados), lento en ISim.
    generic ( MAX_MATRIZ : integer := 6 );
end tb_det_bareiss;

architecture sim of tb_det_bareiss is

    constant T : time := 10 ns;                    -- 100 MHz

    signal clk      : std_logic := '0';
    signal rst      : std_logic := '0';
    signal inicio   : std_logic := '0';
    signal sw_mat   : std_logic_vector(2 downto 0) := "000";
    signal sw_piv   : std_logic_vector(2 downto 0) := "000";
    signal final    : std_logic;
    signal desborde : std_logic;
    signal an       : std_logic_vector(7 downto 0);
    signal seg      : std_logic_vector(6 downto 0);
    signal dp       : std_logic;
    signal fin_sim  : boolean := false;

    subtype txt8 is string(1 to 8);
    type txt_arr is array (1 to 4) of txt8;
    type caso_t is record
        n    : integer;
        det  : txt8;
        desb : std_logic;
        piv  : txt_arr;
    end record;
    type casos_t is array (0 to 7) of caso_t;

    -- Valores esperados (salida de modelo_referencia.py)
    constant CASOS : casos_t := (
        0 => (2, " 0000026", '0', (" 0000007", " 0000000", " 0000000", " 0000000")),
        1 => (3, " 0000003", '0', (" 0000002", " 0000007", " 0000000", " 0000000")),
        2 => (4, "-0000022", '0', (" 0000002", " 0000004", " 0000013", " 0000000")),
        3 => (5, " 0000362", '0', (" 0000004", " 0000020", "-0000170", "-0000639")),
        4 => (3, " 0000050", '0', ("-0000002", "-0000010", " 0000000", " 0000000")),
        5 => (4, " 0000150", '0', (" 0000001", "-0000005", " 0000025", " 0000000")),
        6 => (5, " 0000000", '0', (" 0000000", " 0000000", " 0000000", " 0000000")),
        7 => (5, "-7121828", '1', (" 0000030", "-0001359", " 0022146", " 0277564")));

    function decodifica(s : std_logic_vector(6 downto 0)) return character is
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

    uut: entity work.det_bareiss
        generic map (N_REF => 5)
        port map (clk => clk, rst => rst, inicio => inicio,
                  sw_mat => sw_mat, sw_piv => sw_piv,
                  final => final, desborde => desborde,
                  an => an, seg => seg, dp => dp);

    clk <= not clk after T/2 when not fin_sim else '0';

    estimulos: process
        variable txt     : txt8;
        variable errores : integer := 0;
        variable ciclos  : integer;

        -- Lee el display durante dos barridos completos (2 x 32 ciclos)
        procedure lee_display(texto : out txt8) is
            variable tt : txt8;
        begin
            tt := (others => '?');
            for c in 1 to 80 loop
                wait until falling_edge(clk);
                for dd in 0 to 7 loop
                    if an(dd) = '0' then
                        tt(8 - dd) := decodifica(seg);
                    end if;
                end loop;
            end loop;
            texto := tt;
        end procedure;

        -- Espera final = '1' contando ciclos
        procedure espera_final(maximo : integer; c : out integer) is
            variable cc : integer := 0;
        begin
            while final /= '1' and cc < maximo loop
                wait until rising_edge(clk);
                cc := cc + 1;
            end loop;
            c := cc;
        end procedure;

    begin
        rst <= '1';
        wait for 5 * T;
        rst <= '0';
        wait for 5 * T;

        for m in 0 to MAX_MATRIZ loop
            -- 1. Seleccion de matriz y pulso de inicio
            sw_mat <= conv_std_logic_vector(m, 3);
            sw_piv <= "000";
            wait for 5 * T;
            inicio <= '1';
            wait for 4 * T;
            inicio <= '0';
            wait for 4 * T;
            assert final = '0' report "final no bajo al iniciar" severity error;

            -- 2. Espera el resultado
            espera_final(40000000, ciclos);
            if final /= '1' then
                report "Matriz " & integer'image(m) & ": TIEMPO AGOTADO" severity error;
                errores := errores + 1;
            end if;

            -- 3. Determinante en el display
            lee_display(txt);
            if txt = CASOS(m).det and desborde = CASOS(m).desb then
                report "Matriz " & integer'image(m) & " (" & integer'image(CASOS(m).n) & "x" &
                       integer'image(CASOS(m).n) & "): det  display='" & txt & "' desborde=" &
                       std_logic'image(desborde) & "  ciclos=" & integer'image(ciclos) & "  OK";
            else
                report "Matriz " & integer'image(m) & ": det  display='" & txt &
                       "' esperado='" & CASOS(m).det & "' desborde=" & std_logic'image(desborde) &
                       "  ERROR" severity error;
                errores := errores + 1;
            end if;

            -- 4. Pivotes del banco de registros
            for kk in 1 to CASOS(m).n - 1 loop
                sw_piv <= conv_std_logic_vector(kk, 3);
                wait for 8 * T;
                espera_final(2000, ciclos);
                lee_display(txt);
                if txt = CASOS(m).piv(kk) then
                    report "           pivote " & integer'image(kk) & "  display='" & txt & "'  OK";
                else
                    report "           pivote " & integer'image(kk) & "  display='" & txt &
                           "' esperado='" & CASOS(m).piv(kk) & "'  ERROR" severity error;
                    errores := errores + 1;
                end if;
            end loop;
            sw_piv <= "000";
            wait for 8 * T;
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

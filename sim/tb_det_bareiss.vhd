----------------------------------------------------------------------------------
-- TESTBENCH DEL TOPE det_bareiss (tarjeta completa, tiempos reales)
--
--   1. Pulsa BTNC con rebotes (2 ms de rebote, 20 ms presionado, rebote al soltar).
--   2. Comprueba que el calculo arranca una sola vez y que final = 1.
--   3. Lee los 8 digitos decodificando an/seg durante un barrido (8 ms):
--        dir_p = 0  -> determinante
--        dir_p = 2  -> pivote 2
--        dir_p = n  -> ultimo pivote (= determinante)
-- Los valores esperados se calculan de la ROM con pkg_prueba.
-- Simula unos 70 ms (7 millones de ciclos): tarda algunos minutos.
--
-- Solo para simulacion (usa variables, integer, real, string y wait).
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_arith.all;
use work.pkg_prueba.all;

entity tb_det_bareiss is
end tb_det_bareiss;

architecture sim of tb_det_bareiss is

    component det_bareiss
        Port ( clk      : in  STD_LOGIC;
               rst      : in  STD_LOGIC;
               inicio   : in  STD_LOGIC;
               dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
               final    : out STD_LOGIC;
               desborde : out STD_LOGIC;
               latido   : out STD_LOGIC;
               an       : out STD_LOGIC_VECTOR (7 downto 0);
               seg      : out STD_LOGIC_VECTOR (6 downto 0);
               dp       : out STD_LOGIC);
    end component;

    component rom_matriz
        Port ( dira : in  STD_LOGIC_VECTOR (4 downto 0);
               a    : out STD_LOGIC_VECTOR (5 downto 0));
    end component;

    constant T : time := 10 ns;

    signal clk      : std_logic := '0';
    signal rst      : std_logic := '1';
    signal inicio   : std_logic := '0';
    signal dir_p    : std_logic_vector(2 downto 0) := "000";
    signal final, desborde, latido, dp : std_logic;
    signal an       : std_logic_vector(7 downto 0);
    signal seg      : std_logic_vector(6 downto 0);
    signal dir_tb   : std_logic_vector(4 downto 0) := "00000";
    signal a_tb     : std_logic_vector(5 downto 0);
    signal fin_sim  : boolean := false;
    signal finales  : integer := 0;      -- veces que final pasa de 0 a 1

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

    uut : det_bareiss port map (
        clk => clk, rst => rst, inicio => inicio, dir_p => dir_p, final => final,
        desborde => desborde, latido => latido, an => an, seg => seg, dp => dp);

    U_ROM_TB : rom_matriz port map (dira => dir_tb, a => a_tb);

    clk <= not clk after T/2 when not fin_sim else '0';

    -- Cuenta cuantas veces termina un calculo (final sube)
    process (final)
    begin
        if final'event and final = '1' and final'last_value = '0' then
            finales <= finales + 1;
        end if;
    end process;

    estimulos : process
        variable n       : integer;
        variable m       : matriz_r;
        variable ref     : resultado_ref;
        variable dir     : integer;
        variable errores : integer := 0;
        variable txt     : string(1 to 8);

        -- Lee el display durante un barrido completo (8 ms) y un poco mas
        procedure lee_display (texto : out string) is
            variable tt : string(1 to 8);
        begin
            tt := (others => '?');
            for c in 1 to 900000 loop
                wait until falling_edge(clk);
                for dd in 0 to 7 loop
                    if an(dd) = '0' then
                        tt(8 - dd) := decodifica(seg);
                    end if;
                end loop;
            end loop;
            texto := tt;
        end procedure;

        procedure compara (nombre : string; obtenido, esperado : string) is
        begin
            if obtenido = esperado then
                report nombre & " display='" & obtenido & "'  OK";
            else
                report nombre & " display='" & obtenido & "'  esperado '" & esperado & "'  ERROR"
                    severity error;
                errores := errores + 1;
            end if;
        end procedure;

    begin
        -- Valores esperados
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
        report "Matriz " & integer'image(n) & "x" & integer'image(n) &
               ": det esperado = " & integer'image(ref.det);

        wait for 10 * T;
        rst <= '0';
        wait for 1 ms;

        -- 1. Pulsacion con rebotes
        for r in 1 to 7 loop
            inicio <= '1';  wait for 150 us;
            inicio <= '0';  wait for 130 us;
        end loop;
        inicio <= '1';
        wait for 20 ms;
        for r in 1 to 5 loop
            inicio <= '0';  wait for 120 us;
            inicio <= '1';  wait for 90 us;
        end loop;
        inicio <= '0';
        wait for 2 ms;

        -- 2. Un solo arranque y final = 1
        if final = '1' and finales = 1 then
            report "Pulsacion con rebotes: un solo calculo, final = 1  OK";
        else
            report "Pulsacion con rebotes: final subio " & integer'image(finales) & " veces" &
                   ", final = " & std_logic'image(final) & "  ERROR" severity error;
            errores := errores + 1;
        end if;

        -- 3. Display
        lee_display(txt);
        compara("dir_p=0 (det)     ", txt, texto_display(ref.det));

        dir_p <= "010";
        wait for 100 us;
        lee_display(txt);
        compara("dir_p=2 (pivote 2)", txt, texto_display(ref.piv(2)));

        dir_p <= conv_std_logic_vector(n, 3);
        wait for 100 us;
        lee_display(txt);
        compara("dir_p=n (pivote n)", txt, texto_display(ref.piv(n)));

        if errores = 0 then
            report "TODAS LAS PRUEBAS PASARON";
        else
            report "PRUEBAS CON ERRORES: " & integer'image(errores) severity failure;
        end if;
        fin_sim <= true;
        wait;
    end process;

end sim;

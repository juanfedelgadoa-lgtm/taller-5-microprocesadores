----------------------------------------------------------------------------------
-- Testbench del ASM (entidad asm_bareiss)
--
-- Para cada matriz de la ROM:
--   1. Pulsa "inicio" y espera "final".
--   2. Arma el texto del display (signo + 7 digitos) a partir de disp_neg y
--      disp_bcd y lo compara con el valor del modelo de referencia.
--   3. Recorre los pivotes con sw_piv = 1..n-1 y los compara.
--
-- Solo para simulacion (usa variables, procedimientos y wait).
-- MAX_MATRIZ = 6 prueba las paginas 0..6 (~0,2 ms simulados).
-- MAX_MATRIZ = 7 agrega la 5x5 extrema (~19 millones de ciclos, lento).
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

entity tb_asm_bareiss is
    generic ( MAX_MATRIZ : integer := 6 );
end tb_asm_bareiss;

architecture sim of tb_asm_bareiss is

    component asm_bareiss
        Port ( clk, rst : in  STD_LOGIC;
               inicio   : in  STD_LOGIC;
               sw_mat   : in  STD_LOGIC_VECTOR (2 downto 0);
               sw_piv   : in  STD_LOGIC_VECTOR (2 downto 0);
               final    : out STD_LOGIC;
               disp_bcd : out STD_LOGIC_VECTOR (27 downto 0);
               disp_neg : out STD_LOGIC;
               desborde : out STD_LOGIC);
    end component;

    constant T : time := 10 ns;                    -- 100 MHz

    signal clk      : std_logic := '0';
    signal rst      : std_logic := '0';
    signal inicio   : std_logic := '0';
    signal sw_mat   : std_logic_vector(2 downto 0) := "000";
    signal sw_piv   : std_logic_vector(2 downto 0) := "000";
    signal final    : std_logic;
    signal disp_bcd : std_logic_vector(27 downto 0);
    signal disp_neg : std_logic;
    signal desborde : std_logic;
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

    function digito(x : std_logic_vector(3 downto 0)) return character is
    begin
        case x is
            when "0000" => return '0';
            when "0001" => return '1';
            when "0010" => return '2';
            when "0011" => return '3';
            when "0100" => return '4';
            when "0101" => return '5';
            when "0110" => return '6';
            when "0111" => return '7';
            when "1000" => return '8';
            when "1001" => return '9';
            when others => return '?';
        end case;
    end function;

    function texto(b : std_logic_vector(27 downto 0); ng : std_logic) return txt8 is
        variable tx : txt8;
    begin
        if ng = '1' then tx(1) := '-'; else tx(1) := ' '; end if;
        for dd in 0 to 6 loop
            tx(8 - dd) := digito(b(4*dd + 3 downto 4*dd));
        end loop;
        return tx;
    end function;

begin

    uut: asm_bareiss port map (
        clk => clk, rst => rst, inicio => inicio, sw_mat => sw_mat, sw_piv => sw_piv,
        final => final, disp_bcd => disp_bcd, disp_neg => disp_neg, desborde => desborde);

    clk <= not clk after T/2 when not fin_sim else '0';

    estimulos: process
        variable txt     : txt8;
        variable errores : integer := 0;
        variable ciclos  : integer;

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
            wait for 3 * T;
            inicio <= '0';
            wait for 3 * T;
            assert final = '0' report "final no bajo al iniciar" severity error;

            -- 2. Espera el resultado
            espera_final(40000000, ciclos);
            wait for 3 * T;
            if final /= '1' then
                report "Matriz " & integer'image(m) & ": TIEMPO AGOTADO" severity error;
                errores := errores + 1;
            end if;

            -- 3. Determinante
            txt := texto(disp_bcd, disp_neg);
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
                wait for 4 * T;
                assert final = '0' report "no se reinicio la conversion XS3" severity error;
                espera_final(2000, ciclos);
                wait for 3 * T;
                txt := texto(disp_bcd, disp_neg);
                if txt = CASOS(m).piv(kk) then
                    report "           pivote " & integer'image(kk) & "  display='" & txt &
                           "'  ciclos XS3=" & integer'image(ciclos) & "  OK";
                else
                    report "           pivote " & integer'image(kk) & "  display='" & txt &
                           "' esperado='" & CASOS(m).piv(kk) & "'  ERROR" severity error;
                    errores := errores + 1;
                end if;
            end loop;
            sw_piv <= "000";
            wait for 4 * T;
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

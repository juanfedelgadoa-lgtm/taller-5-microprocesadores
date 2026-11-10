----------------------------------------------------------------------------------
-- Testbench del ASM (entidad asm_bareiss) con la ROM externa conectada
--
-- Para cada matriz de la ROM:
--   1. Pulsa "inicio" y espera "final".
--   2. Arma el texto del display (signo + 7 digitos) a partir de det/det_neg y
--      lo compara con el valor del modelo de referencia (modelo_referencia.py).
--   3. Recorre los pivotes con dir_p = 1..n-1 y compara pivote/piv_neg.
--
-- Solo para simulacion (usa variables, procedimientos, integer y wait).
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

    component rom_matrices
        Port ( dir : in  STD_LOGIC_VECTOR (7 downto 0);
               a   : out STD_LOGIC_VECTOR (5 downto 0));
    end component;

    component asm_bareiss
        Port ( clk, rst : in  STD_LOGIC;
               inicio   : in  STD_LOGIC;
               dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
               a        : in  STD_LOGIC_VECTOR (5 downto 0);
               dira     : out STD_LOGIC_VECTOR (4 downto 0);
               det      : out STD_LOGIC_VECTOR (39 downto 0);
               det_neg  : out STD_LOGIC;
               pivote   : out STD_LOGIC_VECTOR (39 downto 0);
               piv_neg  : out STD_LOGIC;
               final    : out STD_LOGIC);
    end component;

    constant T : time := 10 ns;                    -- 100 MHz

    signal clk     : std_logic := '0';
    signal rst     : std_logic := '0';
    signal inicio  : std_logic := '0';
    signal sw_mat  : std_logic_vector(2 downto 0) := "000";
    signal dir_p   : std_logic_vector(2 downto 0) := "000";
    signal a       : std_logic_vector(5 downto 0);
    signal dira    : std_logic_vector(4 downto 0);
    signal dir_rom : std_logic_vector(7 downto 0);
    signal det     : std_logic_vector(39 downto 0);
    signal pivote  : std_logic_vector(39 downto 0);
    signal det_neg, piv_neg, final : std_logic;
    signal fin_sim : boolean := false;

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

    function texto(b : std_logic_vector(39 downto 0); ng : std_logic) return txt8 is
        variable tx : txt8;
    begin
        if ng = '1' then tx(1) := '-'; else tx(1) := ' '; end if;
        for dd in 0 to 6 loop
            tx(8 - dd) := digito(b(4*dd + 3 downto 4*dd));
        end loop;
        return tx;
    end function;

    function desborde(b : std_logic_vector(39 downto 0)) return std_logic is
    begin
        if b(39 downto 28) = x"000" then return '0'; else return '1'; end if;
    end function;

begin

    -- ROM externa, como en la caja negra
    dir_rom <= sw_mat & dira;
    U_ROM : rom_matrices port map (dir => dir_rom, a => a);

    uut: asm_bareiss port map (
        clk => clk, rst => rst, inicio => inicio, dir_p => dir_p, a => a, dira => dira,
        det => det, det_neg => det_neg, pivote => pivote, piv_neg => piv_neg, final => final);

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
            -- 1. Seleccion de matriz, dir_p = 1 antes de iniciar y pulso de inicio
            sw_mat <= conv_std_logic_vector(m, 3);
            dir_p  <= "001";
            wait for 4 * T;
            espera_final(2000, ciclos);         -- (desde s27 el cambio de dir_p reconvierte)
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
            txt := texto(det, det_neg);
            if txt = CASOS(m).det and desborde(det) = CASOS(m).desb then
                report "Matriz " & integer'image(m) & " (" & integer'image(CASOS(m).n) & "x" &
                       integer'image(CASOS(m).n) & "): det='" & txt & "' desborde=" &
                       std_logic'image(desborde(det)) & "  ciclos=" & integer'image(ciclos) & "  OK";
            else
                report "Matriz " & integer'image(m) & ": det='" & txt &
                       "' esperado='" & CASOS(m).det & "' desborde=" & std_logic'image(desborde(det)) &
                       "  ERROR" severity error;
                errores := errores + 1;
            end if;

            -- 4a. Pivote 1: dir_p ya valia 1 al iniciar, debe estar listo con final
            txt := texto(pivote, piv_neg);
            if txt = CASOS(m).piv(1) then
                report "           dir_p=1  pivote='" & txt & "'  (listo con final)  OK";
            else
                report "           dir_p=1  pivote='" & txt & "' esperado='" & CASOS(m).piv(1) &
                       "'  (listo con final)  ERROR" severity error;
                errores := errores + 1;
            end if;

            -- 4b. Resto de pivotes del banco de registros (dir_p = k)
            for kk in 2 to CASOS(m).n - 1 loop
                dir_p <= conv_std_logic_vector(kk, 3);
                wait for 4 * T;
                assert final = '0' report "no se reinicio la conversion del pivote" severity error;
                espera_final(2000, ciclos);
                wait for 3 * T;
                txt := texto(pivote, piv_neg);
                if txt = CASOS(m).piv(kk) then
                    report "           dir_p=" & integer'image(kk) & "  pivote='" & txt &
                           "'  ciclos XS3=" & integer'image(ciclos) & "  OK";
                else
                    report "           dir_p=" & integer'image(kk) & "  pivote='" & txt &
                           "' esperado='" & CASOS(m).piv(kk) & "'  ERROR" severity error;
                    errores := errores + 1;
                end if;
            end loop;

            -- 5. El determinante no cambia al consultar los pivotes
            if texto(det, det_neg) /= CASOS(m).det then
                report "Matriz " & integer'image(m) & ": det cambio al leer pivotes  ERROR" severity error;
                errores := errores + 1;
            end if;

            -- 6. Vuelve dir_p a 0 y espera que termine esa conversion: el ASM
            --    solo lee "inicio" en s0 y s27 (en la tarjeta el boton dura ms)
            dir_p <= "000";
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

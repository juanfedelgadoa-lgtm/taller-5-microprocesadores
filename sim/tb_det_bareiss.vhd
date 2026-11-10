----------------------------------------------------------------------------------
-- Testbench del tope det_bareiss (sincronizador + ROM + ASM + display)
--
-- Calcula la matriz de la pagina 3 (5x5, det = 362) y lee los 8 digitos
-- decodificando an/seg, igual que el ojo:
--   * ver = 0            -> debe verse el determinante ' 0000362'
--   * ver = 1, dir_p = 3 -> debe verse el pivote 3     '-0000170'
-- El barrido del display dura 2^18 ciclos (2,6 ms), por eso solo se prueba una
-- matriz; las 8 matrices se prueban en tb_asm_bareiss.
--
-- Solo para simulacion (usa variables, procedimientos y wait).
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity tb_det_bareiss is
end tb_det_bareiss;

architecture sim of tb_det_bareiss is

    component det_bareiss
        Port ( clk, rst : in  STD_LOGIC;
               inicio   : in  STD_LOGIC;
               sw_mat   : in  STD_LOGIC_VECTOR (2 downto 0);
               dir_p    : in  STD_LOGIC_VECTOR (2 downto 0);
               ver      : in  STD_LOGIC;
               final    : out STD_LOGIC;
               desborde : out STD_LOGIC;
               an       : out STD_LOGIC_VECTOR (7 downto 0);
               seg      : out STD_LOGIC_VECTOR (6 downto 0);
               dp       : out STD_LOGIC);
    end component;

    constant T : time := 10 ns;

    signal clk      : std_logic := '0';
    signal rst      : std_logic := '0';
    signal inicio   : std_logic := '0';
    signal sw_mat   : std_logic_vector(2 downto 0) := "011";   -- pagina 3
    signal dir_p    : std_logic_vector(2 downto 0) := "000";
    signal ver      : std_logic := '0';
    signal final    : std_logic;
    signal desborde : std_logic;
    signal an       : std_logic_vector(7 downto 0);
    signal seg      : std_logic_vector(6 downto 0);
    signal dp       : std_logic;
    signal fin_sim  : boolean := false;

    subtype txt8 is string(1 to 8);

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

    uut: det_bareiss port map (
        clk => clk, rst => rst, inicio => inicio, sw_mat => sw_mat, dir_p => dir_p, ver => ver,
        final => final, desborde => desborde, an => an, seg => seg, dp => dp);

    clk <= not clk after T/2 when not fin_sim else '0';

    estimulos: process
        variable txt     : txt8;
        variable errores : integer := 0;

        -- Lee el display durante un barrido completo (2^18 ciclos) y un poco mas
        procedure lee_display(texto : out txt8) is
            variable tt : txt8;
        begin
            tt := (others => '?');
            for c in 1 to 270000 loop
                wait until falling_edge(clk);
                for dd in 0 to 7 loop
                    if an(dd) = '0' then
                        tt(8 - dd) := decodifica(seg);
                    end if;
                end loop;
            end loop;
            texto := tt;
        end procedure;

    begin
        rst <= '1';
        wait for 5 * T;
        rst <= '0';
        wait for 5 * T;

        inicio <= '1';
        wait for 4 * T;
        inicio <= '0';
        wait until final = '1' for 1 ms;

        lee_display(txt);
        if txt = " 0000362" and final = '1' and desborde = '0' and dp = '1' then
            report "ver=0          display='" & txt & "'  OK";
        else
            report "ver=0          display='" & txt & "'  esperado ' 0000362'  ERROR" severity error;
            errores := errores + 1;
        end if;

        dir_p <= "011";                        -- pivote 3
        ver   <= '1';
        wait for 10 * T;
        wait until final = '1' for 1 ms;
        lee_display(txt);
        if txt = "-0000170" then
            report "ver=1, dir_p=3 display='" & txt & "'  OK";
        else
            report "ver=1, dir_p=3 display='" & txt & "'  esperado '-0000170'  ERROR" severity error;
            errores := errores + 1;
        end if;

        if errores = 0 then
            report "TODAS LAS PRUEBAS PASARON";
        else
            report "PRUEBAS CON ERRORES: " & integer'image(errores) severity failure;
        end if;
        fin_sim <= true;
        wait;
    end process;

end sim;

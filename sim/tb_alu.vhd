----------------------------------------------------------------------------------
-- TESTBENCH DE LA ALU (autoverificado)
--
-- Prueba las 8 operaciones de la tabla (M s1 s0) con varios pares A, B y
-- compara con el valor esperado. Solo para simulacion.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

entity tb_alu is
end tb_alu;

architecture sim of tb_alu is

    component alu
        Port ( A  : in  STD_LOGIC_VECTOR (49 downto 0);
               B  : in  STD_LOGIC_VECTOR (49 downto 0);
               M  : in  STD_LOGIC;
               s1 : in  STD_LOGIC;
               s0 : in  STD_LOGIC;
               S  : out STD_LOGIC_VECTOR (49 downto 0));
    end component;

    signal A, B, S  : std_logic_vector(49 downto 0);
    signal M, s1, s0 : std_logic;

    type vec_t is array (natural range <>) of std_logic_vector(49 downto 0);

begin

    uut : alu port map (A => A, B => B, M => M, s1 => s1, s0 => s0, S => S);

    process
        constant VA : vec_t := (conv_std_logic_vector(362, 50),
                                conv_std_logic_vector(-170, 50),
                                (others => '1'),
                                (49 => '0', others => '1'),
                                conv_std_logic_vector(5, 50));
        constant VB : vec_t := (conv_std_logic_vector(3, 50),
                                conv_std_logic_vector(639, 50),
                                conv_std_logic_vector(1, 50),
                                conv_std_logic_vector(-1, 50),
                                conv_std_logic_vector(5, 50));
        variable esperado : std_logic_vector(49 downto 0);
        variable op       : std_logic_vector(2 downto 0);
        variable errores  : integer := 0;
        variable nombre   : string(1 to 9);
    begin
        for o in 0 to 7 loop
            op := conv_std_logic_vector(o, 3);
            for c in VA'range loop
                A <= VA(c);  B <= VB(c);
                M <= op(2);  s1 <= op(1);  s0 <= op(0);
                wait for 10 ns;
                case op is
                    when "000"  => esperado := not VB(c);           nombre := "not B    ";
                    when "001"  => esperado := VA(c) and VB(c);     nombre := "A and B  ";
                    when "010"  => esperado := VA(c) or VB(c);      nombre := "A or B   ";
                    when "011"  => esperado := VA(c) xnor VB(c);    nombre := "A xnor B ";
                    when "100"  => esperado := VA(c) + 1;           nombre := "A + 1    ";
                    when "101"  => esperado := VA(c) + VB(c);       nombre := "A + B    ";
                    when "110"  => esperado := VA(c) - VB(c);       nombre := "A - B    ";
                    when others => esperado := VA(c) - 1;           nombre := "A - 1    ";
                end case;
                if S /= esperado then
                    report "M s1 s0 = " & std_logic'image(op(2)) & std_logic'image(op(1)) &
                           std_logic'image(op(0)) & " (" & nombre & ") caso " & integer'image(c) &
                           "  ERROR" severity error;
                    errores := errores + 1;
                end if;
            end loop;
            report "M s1 s0 = " & std_logic'image(op(2)) & std_logic'image(op(1)) &
                   std_logic'image(op(0)) & "  " & nombre & "  probada";
        end loop;
        if errores = 0 then
            report "TODAS LAS PRUEBAS PASARON";
        else
            report "PRUEBAS CON ERRORES: " & integer'image(errores) severity failure;
        end if;
        wait;
    end process;

end sim;

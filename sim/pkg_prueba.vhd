----------------------------------------------------------------------------------
-- PAQUETE DE PRUEBA (solo simulacion; no se sintetiza)
--
-- Modelo de referencia de Bareiss en VHDL con numeros reales (los enteros de
-- VHDL son de 32 bits y los productos intermedios llegan a 2^49; un real
-- representa exactamente enteros hasta 2^53). Sigue la misma regla de pivote
-- que el ASM: primera fila r > k con a(r,k) /= 0. El pivote n es el det.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

package pkg_prueba is

    type fila_r   is array (1 to 5) of real;
    type matriz_r is array (1 to 5) of fila_r;
    type vec_int  is array (1 to 5) of integer;

    type resultado_ref is record
        det     : integer;
        piv     : vec_int;
        cambios : integer;
    end record;

    function bareiss_ref (m_in : matriz_r; n : integer) return resultado_ref;
    function texto_valor (v : integer) return string;                      -- signo + 10 digitos
    function texto_display (v : integer) return string;                    -- signo + 7 digitos

end package pkg_prueba;

package body pkg_prueba is

    function bareiss_ref (m_in : matriz_r; n : integer) return resultado_ref is
        variable m    : matriz_r := m_in;
        variable p    : real := 1.0;
        variable s    : integer := 1;
        variable r    : resultado_ref;
        variable tmp  : fila_r;
        variable fila : integer;
    begin
        r.det := 0;
        r.piv := (others => 0);
        r.cambios := 0;
        for k in 1 to n - 1 loop
            if m(k)(k) = 0.0 then
                fila := 0;
                for i in k + 1 to n loop
                    if fila = 0 and m(i)(k) /= 0.0 then
                        fila := i;
                    end if;
                end loop;
                if fila = 0 then
                    return r;                       -- singular: det = 0
                end if;
                tmp := m(k);  m(k) := m(fila);  m(fila) := tmp;
                s := -s;
                r.cambios := r.cambios + 1;
            end if;
            r.piv(k) := integer(m(k)(k));
            for i in k + 1 to n loop
                for j in k + 1 to n loop
                    m(i)(j) := (m(k)(k) * m(i)(j) - m(i)(k) * m(k)(j)) / p;
                end loop;
            end loop;
            p := m(k)(k);
        end loop;
        r.det := s * integer(m(n)(n));
        r.piv(n) := r.det;
        return r;
    end function;

    function texto_valor (v : integer) return string is
        variable t : string(1 to 11);
        variable x : integer;
    begin
        if v < 0 then t(1) := '-'; x := -v; else t(1) := ' '; x := v; end if;
        for d in 11 downto 2 loop
            t(d) := character'val(character'pos('0') + (x mod 10));
            x := x / 10;
        end loop;
        return t;
    end function;

    function texto_display (v : integer) return string is
        variable t : string(1 to 11);
    begin
        t := texto_valor(v);
        return t(1) & t(5 to 11);
    end function;

end package body pkg_prueba;

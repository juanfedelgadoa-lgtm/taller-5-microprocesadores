----------------------------------------------------------------------------------
-- ASM DEL PROCESADOR: algoritmo de Bareiss con la division por restas
-- sucesivas y el algoritmo XS3 integrados (estados s0 a s26)
--
-- Descripcion de alto nivel del diagrama ASM: un "when" por estado, las cajas
-- de decision son "if" y las salidas condicionales son las asignaciones dentro
-- del "if". Los bloques del camino de datos (ROM, RAM, multiplicador, ALU y
-- banco de pivotes) estan fuera de este archivo: el ASM les entrega
-- direcciones, datos, operandos y la operacion, y lee sus resultados.
--
-- Todas las operaciones sobre datos (resta t1 - t2, division, valores
-- absolutos y el +3 del XS3) pasan por la unica ALU.
-- Solo std_logic y std_logic_vector. Los estados son constantes.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

entity asm_bareiss is
    Port ( clk, rst   : in  STD_LOGIC;
           inicio     : in  STD_LOGIC;
           dir_p      : in  STD_LOGIC_VECTOR (2 downto 0);
           -- ROM
           dira       : out STD_LOGIC_VECTOR (4 downto 0);
           a          : in  STD_LOGIC_VECTOR (5 downto 0);
           -- RAM
           rd_add     : out STD_LOGIC_VECTOR (5 downto 0);
           wr_add     : out STD_LOGIC_VECTOR (5 downto 0);
           we         : out STD_LOGIC;
           data       : out STD_LOGIC_VECTOR (31 downto 0);
           q          : in  STD_LOGIC_VECTOR (31 downto 0);
           -- multiplicador
           mul_a      : out STD_LOGIC_VECTOR (24 downto 0);
           mul_b      : out STD_LOGIC_VECTOR (24 downto 0);
           producto   : in  STD_LOGIC_VECTOR (49 downto 0);
           -- ALU
           alu_a      : out STD_LOGIC_VECTOR (49 downto 0);
           alu_b      : out STD_LOGIC_VECTOR (49 downto 0);
           alu_m      : out STD_LOGIC;
           alu_s1     : out STD_LOGIC;
           alu_s0     : out STD_LOGIC;
           resultado  : in  STD_LOGIC_VECTOR (49 downto 0);
           -- banco de pivotes
           clr_banco  : out STD_LOGIC;
           we_banco   : out STD_LOGIC;
           dir_banco  : out STD_LOGIC_VECTOR (2 downto 0);
           dato_banco : out STD_LOGIC_VECTOR (31 downto 0);
           piv_banco  : in  STD_LOGIC_VECTOR (31 downto 0);   -- banco(dir_p)
           -- salidas del procesador
           det        : out STD_LOGIC_VECTOR (39 downto 0);   -- |det| en BCD
           det_neg    : out STD_LOGIC;
           pivote     : out STD_LOGIC_VECTOR (39 downto 0);   -- |pivote(dir_p)| en BCD
           piv_neg    : out STD_LOGIC;
           final      : out STD_LOGIC);
end asm_bareiss;

architecture Behavioral of asm_bareiss is

------------------------------------------------------------------------------
-- Estados
------------------------------------------------------------------------------
-- s0        espera de inicio
-- s1..s3    lectura de n, copia ROM -> RAM, inicializacion
-- s4..s9    pivote: lectura, busqueda de fila, intercambio, banco(k)
-- s10..s14  productos y resta t1 - t2
-- s15..s16  division por restas sucesivas |t3| / |p|
-- s17       escritura de a(i,j) y avance de i, j
-- s18       p = pivote actual, k = k + 1
-- s19       det = +/- a(n,n) ; banco(n) = det
-- s20       valor a convertir: det (1a pasada) o pivote(dir_p) (2a pasada)
-- s21..s24  algoritmo XS3 (pasos 1 a 5)
-- s25       guarda el BCD en det o en pivote
-- s26       final = 1
constant s0  : STD_LOGIC_VECTOR (4 downto 0) := "00000";
constant s1  : STD_LOGIC_VECTOR (4 downto 0) := "00001";
constant s2  : STD_LOGIC_VECTOR (4 downto 0) := "00010";
constant s3  : STD_LOGIC_VECTOR (4 downto 0) := "00011";
constant s4  : STD_LOGIC_VECTOR (4 downto 0) := "00100";
constant s5  : STD_LOGIC_VECTOR (4 downto 0) := "00101";
constant s6  : STD_LOGIC_VECTOR (4 downto 0) := "00110";
constant s7  : STD_LOGIC_VECTOR (4 downto 0) := "00111";
constant s8  : STD_LOGIC_VECTOR (4 downto 0) := "01000";
constant s9  : STD_LOGIC_VECTOR (4 downto 0) := "01001";
constant s10 : STD_LOGIC_VECTOR (4 downto 0) := "01010";
constant s11 : STD_LOGIC_VECTOR (4 downto 0) := "01011";
constant s12 : STD_LOGIC_VECTOR (4 downto 0) := "01100";
constant s13 : STD_LOGIC_VECTOR (4 downto 0) := "01101";
constant s14 : STD_LOGIC_VECTOR (4 downto 0) := "01110";
constant s15 : STD_LOGIC_VECTOR (4 downto 0) := "01111";
constant s16 : STD_LOGIC_VECTOR (4 downto 0) := "10000";
constant s17 : STD_LOGIC_VECTOR (4 downto 0) := "10001";
constant s18 : STD_LOGIC_VECTOR (4 downto 0) := "10010";
constant s19 : STD_LOGIC_VECTOR (4 downto 0) := "10011";
constant s20 : STD_LOGIC_VECTOR (4 downto 0) := "10100";
constant s21 : STD_LOGIC_VECTOR (4 downto 0) := "10101";
constant s22 : STD_LOGIC_VECTOR (4 downto 0) := "10110";
constant s23 : STD_LOGIC_VECTOR (4 downto 0) := "10111";
constant s24 : STD_LOGIC_VECTOR (4 downto 0) := "11000";
constant s25 : STD_LOGIC_VECTOR (4 downto 0) := "11001";
constant s26 : STD_LOGIC_VECTOR (4 downto 0) := "11010";

signal st : STD_LOGIC_VECTOR (4 downto 0);

------------------------------------------------------------------------------
-- Operaciones de la ALU (M s1 s0)
------------------------------------------------------------------------------
constant ALU_SUMA  : STD_LOGIC_VECTOR (2 downto 0) := "101";   -- A + B
constant ALU_RESTA : STD_LOGIC_VECTOR (2 downto 0) := "110";   -- A - B

------------------------------------------------------------------------------
-- Constantes
------------------------------------------------------------------------------
constant UNO3   : STD_LOGIC_VECTOR (2 downto 0)  := "001";
constant CERO18 : STD_LOGIC_VECTOR (17 downto 0) := "000000000000000000";
constant CERO32 : STD_LOGIC_VECTOR (31 downto 0) := x"00000000";
constant UNO32  : STD_LOGIC_VECTOR (31 downto 0) := x"00000001";
constant CERO40 : STD_LOGIC_VECTOR (39 downto 0) := x"0000000000";
constant CERO46 : STD_LOGIC_VECTOR (45 downto 0) := (others => '0');
constant CERO50 : STD_LOGIC_VECTOR (49 downto 0) := (others => '0');
constant TRES50 : STD_LOGIC_VECTOR (49 downto 0) := (1 downto 0 => '1', others => '0');

------------------------------------------------------------------------------
-- Registros del ASM
------------------------------------------------------------------------------
signal dira_r     : STD_LOGIC_VECTOR (4 downto 0);   -- direccion de la ROM
signal n, i, j, k : STD_LOGIC_VECTOR (2 downto 0);   -- tamano y contadores
signal piv        : STD_LOGIC_VECTOR (31 downto 0);  -- pivote actual a(k,k)
signal p          : STD_LOGIC_VECTOR (31 downto 0);  -- pivote anterior
signal pabs       : STD_LOGIC_VECTOR (31 downto 0);  -- |p| (divisor)
signal signo      : STD_LOGIC;                       -- paridad de intercambios
signal tmp1, tmp2 : STD_LOGIC_VECTOR (31 downto 0);  -- intercambio de filas
signal mul_a_r, mul_b_r : STD_LOGIC_VECTOR (24 downto 0);
signal t1, t2, t3 : STD_LOGIC_VECTOR (49 downto 0);  -- productos y numerador
signal residuo    : STD_LOGIC_VECTOR (49 downto 0);  -- division: residuo
signal cociente   : STD_LOGIC_VECTOR (31 downto 0);  -- division: cociente
signal sq         : STD_LOGIC;                       -- signo del cociente
signal det_bin    : STD_LOGIC_VECTOR (31 downto 0);  -- determinante en binario
signal conv_piv   : STD_LOGIC;                       -- '0' convierte det, '1' el pivote
signal dir_ant    : STD_LOGIC_VECTOR (2 downto 0);   -- dir_p ya convertido
signal neg        : STD_LOGIC;                       -- signo del valor convertido
signal bin        : STD_LOGIC_VECTOR (31 downto 0);  -- XS3: registro binario
signal bcd        : STD_LOGIC_VECTOR (39 downto 0);  -- XS3: registro decimal (10 digitos)
signal cont       : STD_LOGIC_VECTOR (4 downto 0);   -- XS3: bits procesados (0..31)
signal d          : STD_LOGIC_VECTOR (3 downto 0);   -- XS3: digito revisado (0..9)
signal det_bcd, piv_bcd     : STD_LOGIC_VECTOR (39 downto 0);
signal det_neg_r, piv_neg_r : STD_LOGIC;

------------------------------------------------------------------------------
-- Senales combinacionales
------------------------------------------------------------------------------
signal dira_mas1, cont_mas1 : STD_LOGIC_VECTOR (4 downto 0);    -- contadores
signal i_mas1, j_mas1, k_mas1 : STD_LOGIC_VECTOR (2 downto 0);
signal cociente_mas1 : STD_LOGIC_VECTOR (31 downto 0);
signal d_mas1  : STD_LOGIC_VECTOR (3 downto 0);
signal ext_a   : STD_LOGIC_VECTOR (25 downto 0);                -- extensiones de signo
signal a32     : STD_LOGIC_VECTOR (31 downto 0);
signal sx_piv, sx_q, sx_val : STD_LOGIC_VECTOR (17 downto 0);
signal rd_fila, rd_col, wr_fila : STD_LOGIC_VECTOR (2 downto 0);
signal op_alu  : STD_LOGIC_VECTOR (2 downto 0);
signal val     : STD_LOGIC_VECTOR (31 downto 0);                -- valor que se convierte
signal det_nn  : STD_LOGIC_VECTOR (31 downto 0);                -- +/- a(n,n)
signal dig     : STD_LOGIC_VECTOR (3 downto 0);                 -- digito d del BCD

begin

------------------------------------------------------------------------------
-- Contadores y extensiones de signo
------------------------------------------------------------------------------
dira_mas1     <= dira_r + '1';
i_mas1        <= i + '1';
j_mas1        <= j + '1';
k_mas1        <= k + '1';
cociente_mas1 <= cociente + '1';
cont_mas1     <= cont + '1';
d_mas1        <= d + '1';

ext_a  <= (others => a(5));
a32    <= ext_a & a;
sx_piv <= (others => piv(31));
sx_q   <= (others => q(31));
sx_val <= (others => val(31));

------------------------------------------------------------------------------
-- Senales hacia la ROM y la RAM
------------------------------------------------------------------------------
dira <= dira_r;

rd_fila <= k when (st = s4 or st = s6 or st = s12) else      -- RAM(k,k), RAM(k,j)
           n when st = s19 else                              -- RAM(n,n)
           i;
rd_col  <= k when (st = s4 or st = s5 or st = s11) else      -- RAM(k,k), RAM(i,k)
           n when st = s19 else
           j;
rd_add  <= rd_fila & rd_col;

wr_fila <= k when st = s8 else i;                            -- RAM(k,j) en s8
wr_add  <= wr_fila & j;

we   <= '1' when (st = s2 or st = s7 or st = s8 or st = s17) else '0';

data <= a32                    when st = s2 else              -- copia de la ROM
        tmp1                   when st = s7 else              -- intercambio
        tmp2                   when st = s8 else              -- intercambio
        resultado(31 downto 0) when sq = '1' else             -- s17: -cociente
        cociente;                                             -- s17: +cociente

------------------------------------------------------------------------------
-- Multiplicador
------------------------------------------------------------------------------
mul_a <= mul_a_r;
mul_b <= mul_b_r;

------------------------------------------------------------------------------
-- ALU: operandos y operacion segun el estado
------------------------------------------------------------------------------
alu_a <= t1           when st = s14 else                      -- t1 - t2
         residuo      when st = s16 else                      -- residuo - |p|
         CERO46 & dig when st = s23 else                      -- digito + 3 (XS3)
         CERO50;                                              -- 0 - x (negacion)
alu_b <= t2                when st = s14 else
         t3                when st = s15 else                 -- 0 - t3
         CERO18 & pabs     when st = s16 else                 -- |p|
         CERO18 & cociente when st = s17 else                 -- 0 - cociente
         sx_piv & piv      when st = s18 else                 -- 0 - piv
         sx_q & q          when st = s19 else                 -- 0 - a(n,n)
         sx_val & val      when st = s20 else                 -- 0 - valor
         TRES50            when st = s23 else                 -- +3 (XS3)
         CERO50;
op_alu <= ALU_SUMA when st = s23 else ALU_RESTA;
alu_m  <= op_alu(2);
alu_s1 <= op_alu(1);
alu_s0 <= op_alu(0);

------------------------------------------------------------------------------
-- Banco de pivotes
------------------------------------------------------------------------------
det_nn     <= resultado(31 downto 0) when signo = '1' else q; -- s19
clr_banco  <= '1' when st = s3 else '0';
we_banco   <= '1' when (st = s9 or st = s19) else '0';
dir_banco  <= n when st = s19 else k;
dato_banco <= det_nn when st = s19 else piv;

------------------------------------------------------------------------------
-- XS3: valor a convertir y digito d del registro decimal
------------------------------------------------------------------------------
val <= det_bin when conv_piv = '0' else piv_banco;

with d select
    dig <= bcd(3 downto 0)   when "0000",
           bcd(7 downto 4)   when "0001",
           bcd(11 downto 8)  when "0010",
           bcd(15 downto 12) when "0011",
           bcd(19 downto 16) when "0100",
           bcd(23 downto 20) when "0101",
           bcd(27 downto 24) when "0110",
           bcd(31 downto 28) when "0111",
           bcd(35 downto 32) when "1000",
           bcd(39 downto 36) when "1001",
           "0000"            when others;

------------------------------------------------------------------------------
-- Salidas del procesador
------------------------------------------------------------------------------
det     <= det_bcd;
det_neg <= det_neg_r;
pivote  <= piv_bcd;
piv_neg <= piv_neg_r;
final   <= '1' when st = s26 else '0';

------------------------------------------------------------------------------
-- DIAGRAMA ASM
------------------------------------------------------------------------------
process (clk, rst)
begin

if rst = '1' then
    st       <= s0;
    dira_r   <= "00000";
    n <= "000";  i <= "000";  j <= "000";  k <= "000";
    piv      <= CERO32;  p <= CERO32;  pabs <= CERO32;  signo <= '0';
    tmp1     <= CERO32;  tmp2 <= CERO32;
    mul_a_r  <= (others => '0');  mul_b_r <= (others => '0');
    t1       <= CERO50;  t2 <= CERO50;  t3 <= CERO50;
    residuo  <= CERO50;  cociente <= CERO32;  sq <= '0';
    det_bin  <= CERO32;
    conv_piv <= '0';     dir_ant <= "000";  neg <= '0';
    bin      <= CERO32;  bcd <= CERO40;  cont <= "00000";  d <= "0000";
    det_bcd  <= CERO40;  det_neg_r <= '0';
    piv_bcd  <= CERO40;  piv_neg_r <= '0';

elsif clk'event and clk = '1' then

    case st is

        ----------------------------------------------------------------
        -- Espera y carga de la matriz
        ----------------------------------------------------------------
        when s0 =>                              -- final = 0 ; dira = 0
            dira_r <= "00000";
            if inicio = '0' then
                st <= s0;
            else
                st <= s1;
            end if;

        when s1 =>                              -- n = ROM(00h)
            n      <= a(2 downto 0);
            dira_r <= "00001";
            i      <= UNO3;
            j      <= UNO3;
            st     <= s2;

        when s2 =>                              -- RAM(i,j) = ROM(dira), por columnas
            dira_r <= dira_mas1;
            if i = n then
                i <= UNO3;
                if j = n then
                    st <= s3;
                else
                    j  <= j_mas1;
                    st <= s2;
                end if;
            else
                i  <= i_mas1;
                st <= s2;
            end if;

        when s3 =>                              -- inicializacion ; banco = 0
            k        <= UNO3;
            p        <= UNO32;                  -- pivote inicial a(0,0) = 1
            pabs     <= UNO32;
            signo    <= '0';
            conv_piv <= '0';
            st       <= s4;

        ----------------------------------------------------------------
        -- Pivote del paso k
        ----------------------------------------------------------------
        when s4 =>                              -- piv = RAM(k,k)
            piv <= q;
            if q = CERO32 then
                i  <= k_mas1;
                st <= s5;
            else
                st <= s9;
            end if;

        when s5 =>                              -- busca fila i > k con RAM(i,k) /= 0
            if q /= CERO32 then
                j     <= k;
                signo <= not signo;             -- el intercambio cambia el signo
                st    <= s6;
            elsif i = n then
                det_bin <= CERO32;              -- no hay fila: matriz singular
                st      <= s20;
            else
                i  <= i_mas1;
                st <= s5;
            end if;

        when s6 =>                              -- tmp1 = RAM(k,j)
            tmp1 <= q;
            st   <= s7;

        when s7 =>                              -- tmp2 = RAM(i,j) ; RAM(i,j) = tmp1
            tmp2 <= q;
            st   <= s8;

        when s8 =>                              -- RAM(k,j) = tmp2
            if j = n then
                st <= s4;                       -- vuelve a leer el pivote
            else
                j  <= j_mas1;
                st <= s6;
            end if;

        when s9 =>                              -- banco(k) = piv ; i = j = k + 1
            i  <= k_mas1;
            j  <= k_mas1;
            st <= s10;

        ----------------------------------------------------------------
        -- a(i,j) = ( a(k,k)*a(i,j) - a(i,k)*a(k,j) ) / p
        ----------------------------------------------------------------
        when s10 =>                             -- mul_a = a(k,k) ; mul_b = RAM(i,j)
            mul_a_r <= piv(24 downto 0);
            mul_b_r <= q(24 downto 0);
            st      <= s11;

        when s11 =>                             -- t1 = producto ; mul_a = RAM(i,k)
            t1      <= producto;
            mul_a_r <= q(24 downto 0);
            st      <= s12;

        when s12 =>                             -- mul_b = RAM(k,j)
            mul_b_r <= q(24 downto 0);
            st      <= s13;

        when s13 =>                             -- t2 = producto
            t2 <= producto;
            st <= s14;

        when s14 =>                             -- t3 = t1 - t2  (ALU)
            t3 <= resultado;
            st <= s15;

        ----------------------------------------------------------------
        -- Division por restas sucesivas: cociente = |t3| / |p|
        ----------------------------------------------------------------
        when s15 =>                             -- residuo = |t3| ; cociente = 0
            cociente <= CERO32;
            sq       <= t3(49) xor p(31);       -- signo del cociente
            if t3(49) = '1' then
                residuo <= resultado;           -- residuo = 0 - t3  (ALU)
            else
                residuo <= t3;
            end if;
            st <= s16;

        when s16 =>                             -- ALU: residuo - |p|
            if resultado(49) = '0' then         -- residuo - |p| >= 0
                residuo  <= resultado;
                cociente <= cociente_mas1;
                st       <= s16;
            else
                st       <= s17;
            end if;

        when s17 =>                             -- RAM(i,j) = +/- cociente ; avanza j, i
            if j = n then
                if i = n then
                    st <= s18;
                else
                    i  <= i_mas1;
                    j  <= k_mas1;
                    st <= s10;
                end if;
            else
                j  <= j_mas1;
                st <= s10;
            end if;

        when s18 =>                             -- p = piv ; |p| = |piv| ; k = k + 1
            p <= piv;
            if piv(31) = '1' then
                pabs <= resultado(31 downto 0); -- |p| = 0 - piv  (ALU)
            else
                pabs <= piv;
            end if;
            k <= k_mas1;
            if k_mas1 = n then                  -- k = n - 1 : ultimo paso
                st <= s19;
            else
                st <= s4;
            end if;

        when s19 =>                             -- det = +/- RAM(n,n) ; banco(n) = det
            det_bin <= det_nn;
            st      <= s20;

        ----------------------------------------------------------------
        -- Algoritmo XS3 (primero det, luego el pivote elegido)
        ----------------------------------------------------------------
        when s20 =>                             -- bin = |val| ; neg = signo de val
            dir_ant <= dir_p;
            neg     <= val(31);
            if val(31) = '1' then
                bin <= resultado(31 downto 0);  -- bin = 0 - val  (ALU)
            else
                bin <= val;
            end if;
            st <= s21;

        when s21 =>                             -- XS3 paso 1: registro decimal = 0
            bcd  <= CERO40;
            cont <= "00000";
            st   <= s22;

        when s22 =>                             -- XS3 paso 2: LSB decimal = MSB binario
            bcd(0) <= bin(31);
            if cont = "11111" then
                st <= s25;                      -- paso 5: ultimo paso 2 hecho
            else
                d  <= "0000";
                st <= s23;
            end if;

        when s23 =>                             -- XS3 paso 3: si digito(d) > 4, sumar 3 (ALU)
            if dig > "0100" then
                case d is
                    when "0000" => bcd(3 downto 0)   <= resultado(3 downto 0);
                    when "0001" => bcd(7 downto 4)   <= resultado(3 downto 0);
                    when "0010" => bcd(11 downto 8)  <= resultado(3 downto 0);
                    when "0011" => bcd(15 downto 12) <= resultado(3 downto 0);
                    when "0100" => bcd(19 downto 16) <= resultado(3 downto 0);
                    when "0101" => bcd(23 downto 20) <= resultado(3 downto 0);
                    when "0110" => bcd(27 downto 24) <= resultado(3 downto 0);
                    when "0111" => bcd(31 downto 28) <= resultado(3 downto 0);
                    when "1000" => bcd(35 downto 32) <= resultado(3 downto 0);
                    when "1001" => bcd(39 downto 36) <= resultado(3 downto 0);
                    when others => null;
                end case;
            end if;
            if d = "1001" then
                st <= s24;
            else
                d  <= d_mas1;
                st <= s23;
            end if;

        when s24 =>                             -- XS3 paso 4: corrimiento a la izquierda
            bcd  <= bcd(38 downto 0) & '0';
            bin  <= bin(30 downto 0) & '0';
            cont <= cont_mas1;
            st   <= s22;

        when s25 =>                             -- guarda el resultado del XS3
            if conv_piv = '0' then
                det_bcd   <= bcd;
                det_neg_r <= neg;
                conv_piv  <= '1';
                st        <= s20;               -- ahora convierte el pivote
            else
                piv_bcd   <= bcd;
                piv_neg_r <= neg;
                st        <= s26;
            end if;

        when s26 =>                             -- final = 1
            dira_r <= "00000";
            if inicio = '1' then
                st <= s1;                       -- nuevo calculo
            elsif dir_p /= dir_ant then
                st <= s20;                      -- cambio dir_p: convierte el nuevo pivote
            else
                st <= s26;
            end if;

        when others =>
            st <= s0;

    end case;
end if;
end process;

end Behavioral;

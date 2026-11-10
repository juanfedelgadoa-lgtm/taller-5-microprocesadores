----------------------------------------------------------------------------------
-- ASM PRINCIPAL DEL PROCESADOR (algoritmo de Bareiss)
--
-- Descripcion de alto nivel del diagrama ASM (s0 a s21): un "when" por estado,
-- las cajas de decision son "if" y las salidas condicionales son las
-- asignaciones dentro del "if". Los bloques del camino de datos (ROM, RAM,
-- multiplicador, sumador/restador, division, XS3 y banco de pivotes) estan
-- fuera de este archivo: el ASM les entrega direcciones, datos y senales de
-- inicio, y lee sus resultados por los puertos.
--
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
           -- sumador/restador
           sr_a       : out STD_LOGIC_VECTOR (49 downto 0);
           sr_b       : out STD_LOGIC_VECTOR (49 downto 0);
           sr_op      : out STD_LOGIC;
           resultado  : in  STD_LOGIC_VECTOR (49 downto 0);
           -- bloque de division
           ini_div    : out STD_LOGIC;
           dividendo  : out STD_LOGIC_VECTOR (49 downto 0);
           divisor    : out STD_LOGIC_VECTOR (31 downto 0);
           cociente   : in  STD_LOGIC_VECTOR (31 downto 0);
           fin_div    : in  STD_LOGIC;
           -- banco de pivotes
           clr_banco  : out STD_LOGIC;
           we_banco   : out STD_LOGIC;
           dir_banco  : out STD_LOGIC_VECTOR (2 downto 0);
           dato_banco : out STD_LOGIC_VECTOR (31 downto 0);
           piv_banco  : in  STD_LOGIC_VECTOR (31 downto 0);   -- banco(dir_p)
           -- bloque XS3
           ini_xs3    : out STD_LOGIC;
           bin_xs3    : out STD_LOGIC_VECTOR (31 downto 0);
           bcd_xs3    : in  STD_LOGIC_VECTOR (39 downto 0);
           fin_xs3    : in  STD_LOGIC;
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
-- s10..s15  productos, resta e inicio de la division
-- s16       espera de la division y escritura de a(i,j)
-- s17       p = pivote actual, k = k + 1
-- s18       det = +/- a(n,n) ; banco(n) = det
-- s19..s20  conversion XS3 de det y del pivote elegido
-- s21       final = 1
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

signal st : STD_LOGIC_VECTOR (4 downto 0);

------------------------------------------------------------------------------
-- Constantes
------------------------------------------------------------------------------
constant UNO3   : STD_LOGIC_VECTOR (2 downto 0)  := "001";
constant CERO18 : STD_LOGIC_VECTOR (17 downto 0) := "000000000000000000";
constant CERO32 : STD_LOGIC_VECTOR (31 downto 0) := x"00000000";
constant UNO32  : STD_LOGIC_VECTOR (31 downto 0) := x"00000001";
constant CERO40 : STD_LOGIC_VECTOR (39 downto 0) := x"0000000000";
constant CERO50 : STD_LOGIC_VECTOR (49 downto 0) := (others => '0');

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
signal sq         : STD_LOGIC;                       -- signo del cociente
signal det_bin    : STD_LOGIC_VECTOR (31 downto 0);  -- determinante en binario
signal conv_piv   : STD_LOGIC;                       -- '0' convierte det, '1' el pivote
signal dir_ant    : STD_LOGIC_VECTOR (2 downto 0);   -- dir_p ya convertido
signal neg        : STD_LOGIC;                       -- signo del valor convertido
signal det_bcd, piv_bcd     : STD_LOGIC_VECTOR (39 downto 0);
signal det_neg_r, piv_neg_r : STD_LOGIC;

------------------------------------------------------------------------------
-- Senales combinacionales
------------------------------------------------------------------------------
signal dira_mas1 : STD_LOGIC_VECTOR (4 downto 0);    -- contadores
signal i_mas1, j_mas1, k_mas1 : STD_LOGIC_VECTOR (2 downto 0);
signal ext_a   : STD_LOGIC_VECTOR (25 downto 0);     -- extensiones de signo
signal a32     : STD_LOGIC_VECTOR (31 downto 0);
signal sx_piv, sx_q, sx_val : STD_LOGIC_VECTOR (17 downto 0);
signal rd_fila, rd_col, wr_fila : STD_LOGIC_VECTOR (2 downto 0);
signal val     : STD_LOGIC_VECTOR (31 downto 0);     -- valor que se convierte
signal det_nn  : STD_LOGIC_VECTOR (31 downto 0);     -- +/- a(n,n)

begin

------------------------------------------------------------------------------
-- Contadores y extensiones de signo
------------------------------------------------------------------------------
dira_mas1 <= dira_r + '1';
i_mas1    <= i + '1';
j_mas1    <= j + '1';
k_mas1    <= k + '1';

ext_a  <= (others => a(5));
a32    <= ext_a & a;
sx_piv <= (others => piv(31));
sx_q   <= (others => q(31));
sx_val <= (others => val(31));

------------------------------------------------------------------------------
-- Senales hacia la ROM y la RAM
------------------------------------------------------------------------------
dira <= dira_r;

rd_fila <= k when (st = s4 or st = s6 or st = s12) else      -- M(k,k), M(k,j)
           n when st = s18 else                              -- M(n,n)
           i;
rd_col  <= k when (st = s4 or st = s5 or st = s11) else      -- M(k,k), M(i,k)
           n when st = s18 else
           j;
rd_add  <= rd_fila & rd_col;

wr_fila <= k when st = s8 else i;                            -- M(k,j) en s8
wr_add  <= wr_fila & j;

we   <= '1' when (st = s2 or st = s7 or st = s8 or (st = s16 and fin_div = '1')) else '0';

data <= a32                    when st = s2 else              -- copia de la ROM
        tmp1                   when st = s7 else              -- intercambio
        tmp2                   when st = s8 else              -- intercambio
        resultado(31 downto 0) when sq = '1' else             -- s16: -cociente
        cociente;                                             -- s16: +cociente

------------------------------------------------------------------------------
-- Multiplicador
------------------------------------------------------------------------------
mul_a <= mul_a_r;
mul_b <= mul_b_r;

------------------------------------------------------------------------------
-- Sumador/restador (unico): operandos segun el estado
------------------------------------------------------------------------------
sr_a <= t1 when st = s14 else CERO50;                         -- t1 - t2 ; 0 - x
sr_b <= t2              when st = s14 else
        t3              when st = s15 else                    -- -t3
        CERO18 & cociente when st = s16 else                  -- -cociente
        sx_piv & piv    when st = s17 else                    -- -piv
        sx_q & q        when st = s18 else                    -- -a(n,n)
        sx_val & val    when st = s19 else                    -- -valor
        CERO50;
sr_op <= '1';                     -- en este algoritmo todas las operaciones son restas

------------------------------------------------------------------------------
-- Bloque de division: |t3| / |p|
------------------------------------------------------------------------------
ini_div   <= '1' when st = s15 else '0';
dividendo <= resultado when t3(49) = '1' else t3;             -- |t3|
divisor   <= pabs;

------------------------------------------------------------------------------
-- Banco de pivotes
------------------------------------------------------------------------------
det_nn     <= resultado(31 downto 0) when signo = '1' else q; -- s18
clr_banco  <= '1' when st = s3 else '0';
we_banco   <= '1' when (st = s9 or st = s18) else '0';
dir_banco  <= n when st = s18 else k;
dato_banco <= det_nn when st = s18 else piv;

------------------------------------------------------------------------------
-- Bloque XS3: convierte |det| (conv_piv = 0) o |pivote(dir_p)| (conv_piv = 1)
------------------------------------------------------------------------------
val     <= det_bin when conv_piv = '0' else piv_banco;
ini_xs3 <= '1' when st = s19 else '0';
bin_xs3 <= resultado(31 downto 0) when val(31) = '1' else val;  -- |val|

------------------------------------------------------------------------------
-- Salidas del procesador
------------------------------------------------------------------------------
det     <= det_bcd;
det_neg <= det_neg_r;
pivote  <= piv_bcd;
piv_neg <= piv_neg_r;
final   <= '1' when st = s21 else '0';

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
    t1       <= CERO50;  t2 <= CERO50;  t3 <= CERO50;  sq <= '0';
    det_bin  <= CERO32;
    conv_piv <= '0';     dir_ant <= "000";  neg <= '0';
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
        when s4 =>                              -- piv = M(k,k)
            piv <= q;
            if q = CERO32 then
                i  <= k_mas1;
                st <= s5;
            else
                st <= s9;
            end if;

        when s5 =>                              -- busca fila i > k con M(i,k) /= 0
            if q /= CERO32 then
                j     <= k;
                signo <= not signo;             -- el intercambio cambia el signo
                st    <= s6;
            elsif i = n then
                det_bin <= CERO32;              -- no hay fila: matriz singular
                st      <= s19;
            else
                i  <= i_mas1;
                st <= s5;
            end if;

        when s6 =>                              -- tmp1 = M(k,j)
            tmp1 <= q;
            st   <= s7;

        when s7 =>                              -- tmp2 = M(i,j) ; RAM(i,j) = tmp1
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
        when s10 =>                             -- mul_a = a(k,k) ; mul_b = M(i,j)
            mul_a_r <= piv(24 downto 0);
            mul_b_r <= q(24 downto 0);
            st      <= s11;

        when s11 =>                             -- t1 = producto ; mul_a = M(i,k)
            t1      <= producto;
            mul_a_r <= q(24 downto 0);
            st      <= s12;

        when s12 =>                             -- mul_b = M(k,j)
            mul_b_r <= q(24 downto 0);
            st      <= s13;

        when s13 =>                             -- t2 = producto
            t2 <= producto;
            st <= s14;

        when s14 =>                             -- t3 = t1 - t2
            t3 <= resultado;
            st <= s15;

        when s15 =>                             -- inicio division |t3| / |p|
            sq <= t3(49) xor p(31);             -- signo del cociente
            st <= s16;

        when s16 =>                             -- espera la division
            if fin_div = '1' then               -- RAM(i,j) = +/- cociente
                if j = n then
                    if i = n then
                        st <= s17;
                    else
                        i  <= i_mas1;
                        j  <= k_mas1;
                        st <= s10;
                    end if;
                else
                    j  <= j_mas1;
                    st <= s10;
                end if;
            else
                st <= s16;
            end if;

        when s17 =>                             -- p = piv ; |p| = |piv| ; k = k + 1
            p <= piv;
            if piv(31) = '1' then
                pabs <= resultado(31 downto 0); -- |p| = 0 - piv
            else
                pabs <= piv;
            end if;
            k <= k_mas1;
            if k_mas1 = n then                  -- k = n - 1 : ultimo paso
                st <= s18;
            else
                st <= s4;
            end if;

        when s18 =>                             -- det = +/- M(n,n) ; banco(n) = det
            det_bin <= det_nn;
            st      <= s19;

        ----------------------------------------------------------------
        -- Conversion XS3 (bloque aparte): primero det, luego el pivote
        ----------------------------------------------------------------
        when s19 =>                             -- inicio XS3 con |val|
            neg     <= val(31);
            dir_ant <= dir_p;
            st      <= s20;

        when s20 =>                             -- espera el XS3 y guarda el BCD
            if fin_xs3 = '1' then
                if conv_piv = '0' then
                    det_bcd   <= bcd_xs3;
                    det_neg_r <= neg;
                    conv_piv  <= '1';
                    st        <= s19;           -- ahora convierte el pivote
                else
                    piv_bcd   <= bcd_xs3;
                    piv_neg_r <= neg;
                    st        <= s21;
                end if;
            else
                st <= s20;
            end if;

        when s21 =>                             -- final = 1
            dira_r <= "00000";
            if inicio = '1' then
                st <= s1;                       -- nuevo calculo
            elsif dir_p /= dir_ant then
                st <= s19;                      -- cambio dir_p: convierte el nuevo pivote
            else
                st <= s21;
            end if;

        when others =>
            st <= s0;

    end case;
end if;
end process;

end Behavioral;

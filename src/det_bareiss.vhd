----------------------------------------------------------------------------------
-- Universidad Distrital Francisco Jose de Caldas
-- Analisis y Diseno de Microprocesadores - Taller 5
--
-- Microprocesador de proposito especifico descrito con un diagrama ASM:
--   * Determinante de una matriz simetrica de 2x2 a 5x5 por el algoritmo de
--     Bareiss (eliminacion libre de fracciones).
--   * Division por restas sucesivas.
--   * Conversion binario -> BCD con el algoritmo XS3 (sumar 3 y desplazar),
--     descrita paso a paso dentro del mismo ASM.
--   * Banco de registros con los pivotes; se eligen con los switches.
--
-- Herramienta : Xilinx ISE 14.7 (XST / ISim)
-- Tarjeta     : Digilent Nexys A7-100T (XC7A100T-1CSG324C), reloj de 100 MHz
--
-- Todo el diseno esta descrito con senales (no se usan variables).
-- El numero de cada estado coincide con el diagrama ASM del documento.
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

entity det_bareiss is
    generic ( N_REF : integer := 18 );  -- bits del contador de refresco del display
    Port ( clk, rst : in  STD_LOGIC;
           inicio   : in  STD_LOGIC;                      -- BTNC
           sw_mat   : in  STD_LOGIC_VECTOR (2 downto 0);  -- SW15..SW13: matriz (pagina de la ROM)
           sw_piv   : in  STD_LOGIC_VECTOR (2 downto 0);  -- SW2..SW0 : 0 = det, 1..4 = pivote k
           final    : out STD_LOGIC;                      -- LD0
           desborde : out STD_LOGIC;                      -- LD1: |valor| > 9 999 999
           an       : out STD_LOGIC_VECTOR (7 downto 0);  -- anodos (activos en bajo)
           seg      : out STD_LOGIC_VECTOR (6 downto 0);  -- seg(0)=CA ... seg(6)=CG (activos en bajo)
           dp       : out STD_LOGIC);
end det_bareiss;

architecture Behavioral of det_bareiss is

------------------------------------------------------------------------------
-- UNIDAD DE CONTROL: estados del ASM
------------------------------------------------------------------------------
-- s0        espera de inicio
-- s1..s2    lectura de n y copia de la matriz ROM -> RAM
-- s3        inicializacion de Bareiss
-- s4..s10   pivote: lectura, busqueda de fila, intercambio, banco de pivotes
-- s11..s18  actualizacion de a(i,j): multiplicaciones, resta y division
-- s19       actualizacion del pivote anterior p y avance de k
-- s20       det = (+/-) a(n,n)
-- s21       seleccion del valor a mostrar (det o pivote)
-- s22..s25  algoritmo XS3 (pasos 1 a 5)
-- s26       final = 1, valor en el display
type estados_asm is (s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10,
                     s11, s12, s13, s14, s15, s16, s17, s18, s19, s20,
                     s21, s22, s23, s24, s25, s26);
signal st : estados_asm;

------------------------------------------------------------------------------
-- MEMORIA ROM: 8 paginas de 32 palabras de 6 bits (complemento a 2).
-- En cada pagina: posicion 00h = n, luego los a(i,j) por columnas
-- (a11, a21, ..., an1, a12, ...), como en la Figura 1 del taller.
------------------------------------------------------------------------------
type rom_t is array (0 to 255) of std_logic_vector(5 downto 0);
constant ROM : rom_t := (
      -- pagina 0: 2x2, det = 26
        0 => conv_std_logic_vector(  2,6),  -- n = 2
        1 => conv_std_logic_vector(  7,6),  -- a11
        2 => conv_std_logic_vector( -3,6),  -- a21
        3 => conv_std_logic_vector( -3,6),  -- a12
        4 => conv_std_logic_vector(  5,6),  -- a22
      -- pagina 1: 3x3, det = 3
       32 => conv_std_logic_vector(  3,6),  -- n = 3
       33 => conv_std_logic_vector(  2,6),  -- a11
       34 => conv_std_logic_vector(  1,6),  -- a21
       35 => conv_std_logic_vector(  3,6),  -- a31
       36 => conv_std_logic_vector(  1,6),  -- a12
       37 => conv_std_logic_vector(  4,6),  -- a22
       38 => conv_std_logic_vector(  2,6),  -- a32
       39 => conv_std_logic_vector(  3,6),  -- a13
       40 => conv_std_logic_vector(  2,6),  -- a23
       41 => conv_std_logic_vector(  5,6),  -- a33
      -- pagina 2: 4x4 con a11 = 0 (intercambio de filas en k = 1), det = -22
       64 => conv_std_logic_vector(  4,6),  -- n = 4
       65 => conv_std_logic_vector(  0,6),  -- a11
       66 => conv_std_logic_vector(  2,6),  -- a21
       67 => conv_std_logic_vector(  1,6),  -- a31
       68 => conv_std_logic_vector(  3,6),  -- a41
       69 => conv_std_logic_vector(  2,6),  -- a12
       70 => conv_std_logic_vector(  1,6),  -- a22
       71 => conv_std_logic_vector(  0,6),  -- a32
       72 => conv_std_logic_vector(  1,6),  -- a42
       73 => conv_std_logic_vector(  1,6),  -- a13
       74 => conv_std_logic_vector(  0,6),  -- a23
       75 => conv_std_logic_vector(  3,6),  -- a33
       76 => conv_std_logic_vector(  2,6),  -- a43
       77 => conv_std_logic_vector(  3,6),  -- a14
       78 => conv_std_logic_vector(  1,6),  -- a24
       79 => conv_std_logic_vector(  2,6),  -- a34
       80 => conv_std_logic_vector(  4,6),  -- a44
      -- pagina 3: 5x5 general, det = 362
       96 => conv_std_logic_vector(  5,6),  -- n = 5
       97 => conv_std_logic_vector(  4,6),  -- a11
       98 => conv_std_logic_vector( -2,6),  -- a21
       99 => conv_std_logic_vector(  1,6),  -- a31
      100 => conv_std_logic_vector(  3,6),  -- a41
      101 => conv_std_logic_vector(  0,6),  -- a51
      102 => conv_std_logic_vector( -2,6),  -- a12
      103 => conv_std_logic_vector(  6,6),  -- a22
      104 => conv_std_logic_vector(  2,6),  -- a32
      105 => conv_std_logic_vector( -1,6),  -- a42
      106 => conv_std_logic_vector(  5,6),  -- a52
      107 => conv_std_logic_vector(  1,6),  -- a13
      108 => conv_std_logic_vector(  2,6),  -- a23
      109 => conv_std_logic_vector( -7,6),  -- a33
      110 => conv_std_logic_vector(  4,6),  -- a43
      111 => conv_std_logic_vector(  2,6),  -- a53
      112 => conv_std_logic_vector(  3,6),  -- a14
      113 => conv_std_logic_vector( -1,6),  -- a24
      114 => conv_std_logic_vector(  4,6),  -- a34
      115 => conv_std_logic_vector(  5,6),  -- a44
      116 => conv_std_logic_vector( -3,6),  -- a54
      117 => conv_std_logic_vector(  0,6),  -- a15
      118 => conv_std_logic_vector(  5,6),  -- a25
      119 => conv_std_logic_vector(  2,6),  -- a35
      120 => conv_std_logic_vector( -3,6),  -- a45
      121 => conv_std_logic_vector(  8,6),  -- a55
      -- pagina 4: 3x3 con pivote negativo e intercambio en k = 2, det = 50
      128 => conv_std_logic_vector(  3,6),  -- n = 3
      129 => conv_std_logic_vector( -2,6),  -- a11
      130 => conv_std_logic_vector(  4,6),  -- a21
      131 => conv_std_logic_vector(  1,6),  -- a31
      132 => conv_std_logic_vector(  4,6),  -- a12
      133 => conv_std_logic_vector( -8,6),  -- a22
      134 => conv_std_logic_vector(  3,6),  -- a32
      135 => conv_std_logic_vector(  1,6),  -- a13
      136 => conv_std_logic_vector(  3,6),  -- a23
      137 => conv_std_logic_vector(  5,6),  -- a33
      -- pagina 5: 4x4 con pivote cero en k = 2, det = 150
      160 => conv_std_logic_vector(  4,6),  -- n = 4
      161 => conv_std_logic_vector(  1,6),  -- a11
      162 => conv_std_logic_vector(  2,6),  -- a21
      163 => conv_std_logic_vector(  3,6),  -- a31
      164 => conv_std_logic_vector(  0,6),  -- a41
      165 => conv_std_logic_vector(  2,6),  -- a12
      166 => conv_std_logic_vector(  4,6),  -- a22
      167 => conv_std_logic_vector(  1,6),  -- a32
      168 => conv_std_logic_vector(  5,6),  -- a42
      169 => conv_std_logic_vector(  3,6),  -- a13
      170 => conv_std_logic_vector(  1,6),  -- a23
      171 => conv_std_logic_vector( -2,6),  -- a33
      172 => conv_std_logic_vector(  4,6),  -- a43
      173 => conv_std_logic_vector(  0,6),  -- a14
      174 => conv_std_logic_vector(  5,6),  -- a24
      175 => conv_std_logic_vector(  4,6),  -- a34
      176 => conv_std_logic_vector( -3,6),  -- a44
      -- pagina 6: 5x5 singular (columna 1 en cero), det = 0
      192 => conv_std_logic_vector(  5,6),  -- n = 5
      193 => conv_std_logic_vector(  0,6),  -- a11
      194 => conv_std_logic_vector(  0,6),  -- a21
      195 => conv_std_logic_vector(  0,6),  -- a31
      196 => conv_std_logic_vector(  0,6),  -- a41
      197 => conv_std_logic_vector(  0,6),  -- a51
      198 => conv_std_logic_vector(  0,6),  -- a12
      199 => conv_std_logic_vector(  3,6),  -- a22
      200 => conv_std_logic_vector(  1,6),  -- a32
      201 => conv_std_logic_vector(  2,6),  -- a42
      202 => conv_std_logic_vector(  4,6),  -- a52
      203 => conv_std_logic_vector(  0,6),  -- a13
      204 => conv_std_logic_vector(  1,6),  -- a23
      205 => conv_std_logic_vector(  5,6),  -- a33
      206 => conv_std_logic_vector( -2,6),  -- a43
      207 => conv_std_logic_vector(  1,6),  -- a53
      208 => conv_std_logic_vector(  0,6),  -- a14
      209 => conv_std_logic_vector(  2,6),  -- a24
      210 => conv_std_logic_vector( -2,6),  -- a34
      211 => conv_std_logic_vector(  6,6),  -- a44
      212 => conv_std_logic_vector(  3,6),  -- a54
      213 => conv_std_logic_vector(  0,6),  -- a15
      214 => conv_std_logic_vector(  4,6),  -- a25
      215 => conv_std_logic_vector(  1,6),  -- a35
      216 => conv_std_logic_vector(  3,6),  -- a45
      217 => conv_std_logic_vector(  7,6),  -- a55
      -- pagina 7: 5x5 con valores extremos, det = -17 121 828 (desborde del display)
      224 => conv_std_logic_vector(  5,6),  -- n = 5
      225 => conv_std_logic_vector( 30,6),  -- a11
      226 => conv_std_logic_vector( 27,6),  -- a21
      227 => conv_std_logic_vector( 24,6),  -- a31
      228 => conv_std_logic_vector(-29,6),  -- a41
      229 => conv_std_logic_vector(-31,6),  -- a51
      230 => conv_std_logic_vector( 27,6),  -- a12
      231 => conv_std_logic_vector(-21,6),  -- a22
      232 => conv_std_logic_vector( 28,6),  -- a32
      233 => conv_std_logic_vector( 29,6),  -- a42
      234 => conv_std_logic_vector(-24,6),  -- a52
      235 => conv_std_logic_vector( 24,6),  -- a13
      236 => conv_std_logic_vector( 28,6),  -- a23
      237 => conv_std_logic_vector(  2,6),  -- a33
      238 => conv_std_logic_vector(-28,6),  -- a43
      239 => conv_std_logic_vector(-28,6),  -- a53
      240 => conv_std_logic_vector(-29,6),  -- a14
      241 => conv_std_logic_vector( 29,6),  -- a24
      242 => conv_std_logic_vector(-28,6),  -- a34
      243 => conv_std_logic_vector(-27,6),  -- a44
      244 => conv_std_logic_vector( 28,6),  -- a54
      245 => conv_std_logic_vector(-31,6),  -- a15
      246 => conv_std_logic_vector(-24,6),  -- a25
      247 => conv_std_logic_vector(-28,6),  -- a35
      248 => conv_std_logic_vector( 28,6),  -- a45
      249 => conv_std_logic_vector(-30,6),  -- a55
      others => (others => '0'));

signal pag     : std_logic_vector(2 downto 0);   -- pagina elegida al iniciar
signal dira    : std_logic_vector(4 downto 0);   -- linea de direccion de la ROM
signal dir_rom : std_logic_vector(7 downto 0);
signal a       : std_logic_vector(5 downto 0);   -- bus de datos de la ROM

------------------------------------------------------------------------------
-- MEMORIA RAM de trabajo: 64 x 32 bits. Direccion = fila(3) & columna(3),
-- asi no se necesita multiplicar para calcular la direccion de a(i,j).
-- Escritura sincrona, lectura asincrona.
------------------------------------------------------------------------------
type ram_t is array (0 to 63) of std_logic_vector(31 downto 0);
signal ram      : ram_t;
signal fila_ram : std_logic_vector(2 downto 0);
signal col_ram  : std_logic_vector(2 downto 0);
signal dir_ram  : std_logic_vector(5 downto 0);
signal din_ram  : std_logic_vector(31 downto 0);
signal dout_ram : std_logic_vector(31 downto 0);
signal we_ram   : std_logic;

------------------------------------------------------------------------------
-- BANCO DE REGISTROS DE PIVOTES: pivote(k) = a(k,k) usado en el paso k
------------------------------------------------------------------------------
type banco_t is array (1 to 4) of std_logic_vector(31 downto 0);
signal banco : banco_t;

------------------------------------------------------------------------------
-- Registros del algoritmo de Bareiss
------------------------------------------------------------------------------
signal n, i, j, k : std_logic_vector(2 downto 0);  -- tamano y contadores
signal piv   : std_logic_vector(31 downto 0);      -- pivote actual a(k,k)
signal p     : std_logic_vector(31 downto 0);      -- pivote anterior (divisor)
signal pabs  : std_logic_vector(31 downto 0);      -- |p|
signal signo : std_logic;                          -- '1' = numero impar de intercambios
signal tmp1, tmp2 : std_logic_vector(31 downto 0); -- intercambio de filas
signal t1, t2, t3 : std_logic_vector(49 downto 0); -- productos y numerador
signal det   : std_logic_vector(31 downto 0);      -- determinante

-- Multiplicador (unidad funcional 1)
signal mul_a, mul_b : std_logic_vector(24 downto 0);
signal mul_p        : std_logic_vector(49 downto 0);

-- Sumador/restador (unidad funcional 2): sr_s = sr_a + sr_b  o  sr_a - sr_b
signal sr_a, sr_b, sr_bx, sr_s : std_logic_vector(49 downto 0);
signal sr_op : std_logic;                          -- '0' suma, '1' resta

-- Bloque de division por restas sucesivas (unidad funcional 3)
signal R  : std_logic_vector(49 downto 0);         -- residuo
signal Q  : std_logic_vector(31 downto 0);         -- cociente
signal sq : std_logic;                             -- signo del cociente

------------------------------------------------------------------------------
-- Conversion XS3 (binario -> BCD)
------------------------------------------------------------------------------
type bcd_t is array (0 to 9) of std_logic_vector(3 downto 0);
signal bcd     : bcd_t;                            -- registro decimal (10 digitos)
signal bin     : std_logic_vector(31 downto 0);    -- registro binario
signal cont    : std_logic_vector(4 downto 0);     -- bits procesados (0..31)
signal d       : std_logic_vector(3 downto 0);     -- digito revisado (0..9)
signal dig_d   : std_logic_vector(3 downto 0);     -- bcd(d)
signal neg     : std_logic;                        -- signo del valor convertido
signal val_sel : std_logic_vector(31 downto 0);    -- det o pivote elegido
signal sel_ant : std_logic_vector(2 downto 0);     -- seleccion ya convertida

------------------------------------------------------------------------------
-- Visualizacion
------------------------------------------------------------------------------
signal disp     : bcd_t;                           -- BCD que se muestra
signal disp_neg : std_logic;
signal refresco : std_logic_vector(N_REF-1 downto 0);
signal dsel     : std_logic_vector(2 downto 0);    -- digito encendido
signal car      : std_logic_vector(3 downto 0);    -- 0-9, A = '-', F = apagado

-- Sincronizacion de entradas externas
signal ini_r1, ini_s : std_logic;
signal piv_r1, piv_s : std_logic_vector(2 downto 0);
signal mat_r1, mat_s : std_logic_vector(2 downto 0);

begin

------------------------------------------------------------------------------
-- CAMINO DE DATOS
------------------------------------------------------------------------------

-- ROM
dir_rom <= pag & dira;
a <= ROM(conv_integer(dir_rom));

-- RAM: la direccion, el dato y la escritura dependen del estado
fila_ram <= k when (st = s4 or st = s6 or st = s8 or st = s13) else
            n when st = s20 else
            i;
col_ram  <= k when (st = s4 or st = s5 or st = s12) else
            n when st = s20 else
            j;
dir_ram  <= fila_ram & col_ram;

we_ram   <= '1' when (st = s2 or st = s8 or st = s9 or st = s18) else '0';

din_ram  <= sxt(a, 32)        when st = s2 else         -- copia de la ROM
            tmp2              when st = s8 else         -- intercambio
            tmp1              when st = s9 else         -- intercambio
            sr_s(31 downto 0) when sq = '1' else        -- s18: -Q
            Q;                                          -- s18: +Q

process (clk)
begin
    if clk'event and clk = '1' then
        if we_ram = '1' then
            ram(conv_integer(dir_ram)) <= din_ram;
        end if;
    end if;
end process;

dout_ram <= ram(conv_integer(dir_ram));

-- Multiplicador con signo 25 x 25 -> 50 bits
mul_p <= signed(mul_a) * signed(mul_b);

-- Sumador/restador de 50 bits: A + B  o  A + not(B) + 1 = A - B
sr_a <= t1             when st = s15 else               -- t1 - t2
        R              when st = s17 else               -- R - |p|
        ext(dig_d, 50) when st = s24 else               -- digito + 3
        (others => '0');                                -- 0 - x (negacion)
sr_b <= t2                           when st = s15 else
        t3                           when st = s16 else -- -t3
        ext(pabs, 50)                when st = s17 else -- |p|
        ext(Q, 50)                   when st = s18 else -- -Q
        sxt(piv, 50)                 when st = s19 else -- -piv
        sxt(dout_ram, 50)            when st = s20 else -- -a(n,n)
        sxt(val_sel, 50)             when st = s21 else -- -valor
        conv_std_logic_vector(3, 50) when st = s24 else -- +3 (XS3)
        (others => '0');
sr_op <= '0' when st = s24 else '1';
sr_bx <= not sr_b when sr_op = '1' else sr_b;
sr_s  <= sr_a + sr_bx + sr_op;

-- Valor a mostrar: det (sw_piv = 0) o pivote(k) (sw_piv = 1..4)
val_sel <= det                        when piv_s = "000" else
           banco(conv_integer(piv_s)) when piv_s < 5 else
           (others => '0');

dig_d <= bcd(conv_integer(d));

------------------------------------------------------------------------------
-- UNIDAD DE CONTROL: diagrama ASM
------------------------------------------------------------------------------
final <= '1' when st = s26 else '0';

process (clk, rst)
begin

if rst = '1' then
    st       <= s0;
    pag      <= (others => '0');
    dira     <= (others => '0');
    det      <= (others => '0');
    banco    <= (others => (others => '0'));
    sel_ant  <= (others => '0');
    d        <= (others => '0');
    cont     <= (others => '0');
    disp     <= (others => (others => '0'));
    disp_neg <= '0';

elsif clk'event and clk = '1' then

    case st is

        ----------------------------------------------------------------
        -- Espera y carga de la matriz
        ----------------------------------------------------------------
        when s0 =>                              -- final = 0, dira = 0
            dira <= (others => '0');
            if ini_s = '0' then
                st <= s0;
            else
                pag <= mat_s;
                st  <= s1;
            end if;

        when s1 =>                              -- n = ROM(00h)
            n    <= a(2 downto 0);
            dira <= "00001";
            i    <= "001";
            j    <= "001";
            st   <= s2;

        when s2 =>                              -- M(i,j) = ROM(dira), por columnas
            dira <= dira + 1;
            if i = n then
                i <= "001";
                if j = n then
                    st <= s3;
                else
                    j  <= j + 1;
                    st <= s2;
                end if;
            else
                i  <= i + 1;
                st <= s2;
            end if;

        when s3 =>                              -- inicializacion de Bareiss
            k     <= "001";
            p     <= conv_std_logic_vector(1, 32);   -- a(0,0) = 1
            pabs  <= conv_std_logic_vector(1, 32);
            signo <= '0';
            banco <= (others => (others => '0'));
            st    <= s4;

        ----------------------------------------------------------------
        -- Pivote del paso k
        ----------------------------------------------------------------
        when s4 =>                              -- piv = M(k,k)
            piv <= dout_ram;
            if dout_ram = 0 then
                i  <= k + 1;
                st <= s5;
            else
                st <= s10;
            end if;

        when s5 =>                              -- busca fila i > k con M(i,k) /= 0
            if dout_ram /= 0 then
                j     <= k;
                signo <= not signo;             -- el intercambio cambia el signo
                st    <= s6;
            elsif i = n then
                det <= (others => '0');         -- no hay fila: matriz singular
                st  <= s21;
            else
                i  <= i + 1;
                st <= s5;
            end if;

        when s6 =>                              -- tmp1 = M(k,j)
            tmp1 <= dout_ram;
            st   <= s7;

        when s7 =>                              -- tmp2 = M(i,j)
            tmp2 <= dout_ram;
            st   <= s8;

        when s8 =>                              -- M(k,j) = tmp2
            st <= s9;

        when s9 =>                              -- M(i,j) = tmp1
            if j = n then
                st <= s4;                       -- vuelve a leer el pivote
            else
                j  <= j + 1;
                st <= s6;
            end if;

        when s10 =>                             -- banco(k) = piv ; i = j = k+1
            banco(conv_integer(k)) <= piv;
            i  <= k + 1;
            j  <= k + 1;
            st <= s11;

        ----------------------------------------------------------------
        -- a(i,j) = ( a(k,k)*a(i,j) - a(i,k)*a(k,j) ) / p
        ----------------------------------------------------------------
        when s11 =>                             -- mul_a = a(k,k), mul_b = M(i,j)
            mul_a <= piv(24 downto 0);
            mul_b <= dout_ram(24 downto 0);
            st    <= s12;

        when s12 =>                             -- t1 = a(k,k)*a(i,j), mul_a = M(i,k)
            t1    <= mul_p;
            mul_a <= dout_ram(24 downto 0);
            st    <= s13;

        when s13 =>                             -- mul_b = M(k,j)
            mul_b <= dout_ram(24 downto 0);
            st    <= s14;

        when s14 =>                             -- t2 = a(i,k)*a(k,j)
            t2 <= mul_p;
            st <= s15;

        when s15 =>                             -- t3 = t1 - t2
            t3 <= sr_s;
            st <= s16;

        when s16 =>                             -- R = |t3|, Q = 0, signo del cociente
            Q  <= (others => '0');
            sq <= t3(49) xor p(31);
            if t3(49) = '1' then
                R <= sr_s;                      -- 0 - t3
            else
                R <= t3;
            end if;
            st <= s17;

        when s17 =>                             -- division por restas sucesivas
            if sr_s(49) = '0' then              -- R - |p| >= 0
                R  <= sr_s;
                Q  <= Q + 1;
                st <= s17;
            else
                st <= s18;
            end if;

        when s18 =>                             -- M(i,j) = +Q o -Q ; avanza j, i
            if j = n then
                if i = n then
                    st <= s19;
                else
                    i  <= i + 1;
                    j  <= k + 1;
                    st <= s11;
                end if;
            else
                j  <= j + 1;
                st <= s11;
            end if;

        when s19 =>                             -- p = a(k,k), |p|, k = k + 1
            p <= piv;
            if piv(31) = '1' then
                pabs <= sr_s(31 downto 0);      -- 0 - piv
            else
                pabs <= piv;
            end if;
            k <= k + 1;
            if k = n - 1 then
                st <= s20;
            else
                st <= s4;
            end if;

        when s20 =>                             -- det = (+/-) M(n,n)
            if signo = '1' then
                det <= sr_s(31 downto 0);       -- 0 - M(n,n)
            else
                det <= dout_ram;
            end if;
            st <= s21;

        ----------------------------------------------------------------
        -- Valor a mostrar y conversion XS3
        ----------------------------------------------------------------
        when s21 =>                             -- bin = |valor|, neg = signo
            sel_ant <= piv_s;
            neg     <= val_sel(31);
            if val_sel(31) = '1' then
                bin <= sr_s(31 downto 0);       -- 0 - valor
            else
                bin <= val_sel;
            end if;
            st <= s22;

        when s22 =>                             -- XS3 paso 1: registro decimal = 0
            bcd  <= (others => (others => '0'));
            cont <= (others => '0');
            st   <= s23;

        when s23 =>                             -- XS3 paso 2: LSB decimal = MSB binario
            bcd(0)(0) <= bin(31);
            if cont = 31 then
                st <= s26;                      -- paso 5: ultimo paso 2 hecho
            else
                d  <= (others => '0');
                st <= s24;
            end if;

        when s24 =>                             -- XS3 paso 3: si digito(d) > 4, sumar 3
            if dig_d > 4 then
                bcd(conv_integer(d)) <= sr_s(3 downto 0);   -- digito + 3
            end if;
            if d = 9 then
                st <= s25;
            else
                d  <= d + 1;
                st <= s24;
            end if;

        when s25 =>                             -- XS3 paso 4: corrimiento a la izquierda
            bcd(9) <= bcd(9)(2 downto 0) & bcd(8)(3);
            bcd(8) <= bcd(8)(2 downto 0) & bcd(7)(3);
            bcd(7) <= bcd(7)(2 downto 0) & bcd(6)(3);
            bcd(6) <= bcd(6)(2 downto 0) & bcd(5)(3);
            bcd(5) <= bcd(5)(2 downto 0) & bcd(4)(3);
            bcd(4) <= bcd(4)(2 downto 0) & bcd(3)(3);
            bcd(3) <= bcd(3)(2 downto 0) & bcd(2)(3);
            bcd(2) <= bcd(2)(2 downto 0) & bcd(1)(3);
            bcd(1) <= bcd(1)(2 downto 0) & bcd(0)(3);
            bcd(0) <= bcd(0)(2 downto 0) & '0';
            bin    <= bin(30 downto 0) & '0';
            cont   <= cont + 1;
            st     <= s23;

        when s26 =>                             -- final = 1, display = BCD
            disp     <= bcd;
            disp_neg <= neg;
            dira     <= (others => '0');
            if ini_s = '1' then
                pag <= mat_s;
                st  <= s1;                      -- nuevo calculo
            elsif piv_s /= sel_ant then
                st <= s21;                      -- cambio de switches: reconvertir
            else
                st <= s26;
            end if;

    end case;
end if;
end process;

------------------------------------------------------------------------------
-- Sincronizacion de botones y switches (dos flip-flops)
------------------------------------------------------------------------------
process (clk, rst)
begin
    if rst = '1' then
        ini_r1 <= '0';  ini_s <= '0';
        piv_r1 <= (others => '0');  piv_s <= (others => '0');
        mat_r1 <= (others => '0');  mat_s <= (others => '0');
    elsif clk'event and clk = '1' then
        ini_r1 <= inicio;  ini_s <= ini_r1;
        piv_r1 <= sw_piv;  piv_s <= piv_r1;
        mat_r1 <= sw_mat;  mat_s <= mat_r1;
    end if;
end process;

------------------------------------------------------------------------------
-- Display de 8 digitos multiplexado: AN7 = signo, AN6..AN0 = 7 digitos BCD
------------------------------------------------------------------------------
process (clk, rst)
begin
    if rst = '1' then
        refresco <= (others => '0');
    elsif clk'event and clk = '1' then
        refresco <= refresco + 1;
    end if;
end process;

dsel <= refresco(N_REF-1 downto N_REF-3);

car <= "1010" when (dsel = "111" and disp_neg = '1') else   -- signo menos
       "1111" when dsel = "111" else                        -- apagado
       disp(conv_integer(dsel));

with dsel select
    an <= "11111110" when "000",
          "11111101" when "001",
          "11111011" when "010",
          "11110111" when "011",
          "11101111" when "100",
          "11011111" when "101",
          "10111111" when "110",
          "01111111" when others;

with car select                                 --  gfedcba
    seg <= "1000000" when "0000",               --  0
           "1111001" when "0001",               --  1
           "0100100" when "0010",               --  2
           "0110000" when "0011",               --  3
           "0011001" when "0100",               --  4
           "0010010" when "0101",               --  5
           "0000010" when "0110",               --  6
           "1111000" when "0111",               --  7
           "0000000" when "1000",               --  8
           "0010000" when "1001",               --  9
           "0111111" when "1010",               --  -
           "1111111" when others;               --  apagado

dp <= '1';

-- Los digitos 7, 8 y 9 del BCD no caben en el display
desborde <= '0' when (disp(7) = "0000" and disp(8) = "0000" and disp(9) = "0000") else '1';

end Behavioral;

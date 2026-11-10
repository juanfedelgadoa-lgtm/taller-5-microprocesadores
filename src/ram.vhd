----------------------------------------------------------------------------------
-- RAM DE TRABAJO (modelo de RAM del curso)
--
-- Es el modelo del aula con dos cambios de tamano:
--   * 64 palabras en lugar de 32, para que la direccion sea fila(3) & columna(3)
--     y no haya que multiplicar para ubicar a(i,j).
--   * Contenido inicial en cero (solo evita valores 'U' en la simulacion).
-- Escritura sincrona; lectura asincrona por una direccion aparte (rd_add).
-- Es la unica parte del diseno que usa un tipo distinto de std_logic (el
-- arreglo de la memoria) y conv_integer para la linea de direccion.
----------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;

entity RAM_memory is
   port
   (
      c      : in  std_logic;
      data   : in  std_logic_vector (31 downto 0);
      wr_add : in  std_logic_vector (5 downto 0);
      rd_add : in  std_logic_vector (5 downto 0);
      we     : in  std_logic;
      q      : out std_logic_vector (31 downto 0)
   );
end RAM_memory;

architecture rtl of RAM_memory is
   type mem is array(0 to 63) of std_logic_vector(31 downto 0);
   signal ram_blk : mem := (others => (others => '0'));
begin

   process (c, data, wr_add, rd_add, ram_blk)
   begin
      if (c'event and c = '1') then
         if (we = '1') then
            ram_blk(conv_integer(wr_add)) <= data;
         end if;
      end if;
   end process;

   q <= ram_blk(conv_integer(rd_add));

end rtl;

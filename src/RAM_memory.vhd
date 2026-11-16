----------------------------------------------------------------------------------
-- RAM DEL CURSO: modelo del profesor, sin cambios (32 palabras de 32 bits)
-- Escritura sincrona por wr_add; lectura asincrona por rd_add.
-- Es el unico archivo que usa std_logic_unsigned (conv_integer de la direccion).
-- El procesador usa dos de estas RAM (A y B) con el mismo contenido.
----------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;

entity RAM_memory is
   port
   (
      c      : in  std_logic;
      data   : in  std_logic_vector (31 downto 0);
      wr_add : in  std_logic_vector (4 downto 0);
      rd_add : in  std_logic_vector (4 downto 0);
      we     : in  std_logic;
      q      : out std_logic_vector (31 downto 0)
   );
end RAM_memory;

architecture rtl of RAM_memory is
   type mem is array(0 to 31) of std_logic_vector(31 downto 0);
   signal ram_blk : mem;
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

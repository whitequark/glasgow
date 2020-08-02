# Ref: ATmega16U4/ATmega32U4 8-bit Microcontroller with 16/32K bytes of ISP Flash and USB Controller datasheet
# Accession: G00058

from ...support.bits import *
from ...support.bitstruct import *


__all__ = [
    # IR
    "IR_EXTEST", "IR_IDCODE", "IR_SAMPLE_PRELOAD",
    "IR_PROG_ENABLE", "IR_PROG_COMMANDS", "IR_PROG_PAGELOAD", "IR_PROG_PAGEREAD",
    "IR_PRIVATE0", "IR_PRIVATE1", "IR_PRIVATE2", "IR_PRIVATE3",
    "IR_AVR_RESET", "IR_BYPASS",
]


# IR values

IR_EXTEST           = bits(0x0, 4)
IR_IDCODE           = bits(0x1, 4)
IR_SAMPLE_PRELOAD   = bits(0x2, 4)
IR_PROG_ENABLE      = bits(0x4, 4) # DR[16]
IR_PROG_COMMANDS    = bits(0x5, 4) # DR[15]
IR_PROG_PAGELOAD    = bits(0x6, 4) # DR[8]
IR_PROG_PAGEREAD    = bits(0x7, 4) # DR[8]
IR_PRIVATE0         = bits(0x8, 4)
IR_PRIVATE1         = bits(0x9, 4)
IR_PRIVATE2         = bits(0xa, 4)
IR_PRIVATE3         = bits(0xb, 4)
IR_AVR_RESET        = bits(0xc, 4) # DR[1]
IR_BYPASS           = bits(0xf, 4)

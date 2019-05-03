import logging
import asyncio
from migen import *
from migen.genlib.cdc import MultiReg

from ... import *
from . import *


class PICICSPLVBus(Module):
    def __init__(self, pads):
        self.en     = Signal()
        self.clk    = Signal()
        self.dat_oe = Signal()
        self.dat_o  = Signal()
        self.dat_i  = Signal()

        ###

        self.comb += [
            pads.mclr_t.oe.eq(self.en),
            pads.mclr_t.o.eq(0),
            pads.icspclk_t.oe.eq(self.en),
            pads.icspclk_t.o.eq(self.clk),
            pads.icspdat_t.oe.eq(self.en & self.dat_oe),
            pads.icspdat_t.o.eq(self.dat_o),
        ]
        self.specials += [
            MultiReg(pads.icspdat_t.i, self.dat_i),
        ]


class ProgramPICLVApplet(GlasgowApplet, name="program-pic-lv"):
    logger = logging.getLogger(__name__)
    help = "program Microchip PIC microcontrollers via low-voltage ICSP"
    preview = True
    description = """
    Identify, program, and verify Microchip PIC microcontrollers using low-voltage in-circuit
    serial programming.

    NOTE: This applet is not functional yet.

    Supported devices are: TBD
    """

    __pins = ("mclr", "icspclk", "icspdat")

    @classmethod
    def add_build_arguments(cls, parser, access):
        super().add_build_arguments(parser, access)

        for pin in cls.__pins:
            access.add_pin_argument(parser, pin, default=True)

        parser.add_argument(
            "-f", "--frequency", metavar="FREQ", type=int, default=100,
            help="set ICSP clock frequency to FREQ kHz (default: %(default)s)")

    def build(self, target, args):
        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        iface.add_subtarget(ProgramPICSubtarget(
            bus=PICICSPLVBus(iface.get_pads(args, pins=self.__pins)),
            in_fifo=iface.get_in_fifo(),
            out_fifo=iface.get_out_fifo(),
            period_cyc=self.derive_clock(input_hz=target.sys_clk_freq,
                                         output_hz=args.frequency * 1000,
                                         # 2 cyc MultiReg delay from ICSPCLK to ICSPDAT
                                         min_cyc=4),
        ))

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        pic_iface = ProgramPICInterface(iface, self.logger)
        return pic_iface

    @classmethod
    def add_interact_arguments(cls, parser):
        pass

    async def interact(self, device, args, pic_iface):
        await pic_iface.enter_lvp()

# -------------------------------------------------------------------------------------------------

class ProgramPICLVAppletTestCase(GlasgowAppletTestCase, applet=ProgramPICLVApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()

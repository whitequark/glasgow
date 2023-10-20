import logging
from amaranth import *
from amaranth.lib.cdc import FFSynchronizer
from amaranth.lib.wiring import Component, In, Out

from ....support.logging import *
from ... import *


# class GPIBDeviceBus(Component):
#     # Data lines
#     doe  : In()
#     do   : In(8)
#     di   : Out(8)




# class GPIBControllerBus(Component):

#     # Control lines
#     eoi  : In() # End or Identify
#     dav  : In() # Data Valid            \
#     nrfd : Out() # Not Ready For Data    |  Handshake bus
#     ndac : Out() # No Data Accepted      /
#     ifc  : Signal() # Interface Clear    \
#     srq  : Signal() # Service Request    |  Management bus
#     atn  : Signal() # Attention          /
#     ren  : Signal() # Remote Enable


#     def __init__(self, pads):
#         self.pads = pads

#         # Data lines
#         self.doe  = Signal()
#         self.do   = Signal(8)
#         self.di   = Signal(8)

#         # Control lines
#         self.eoi  = Signal() # End or Identify
#         self.dav  = Signal() # Data Valid            \
#         self.nrfd = Signal() # Not Ready For Data    |  Handshake bus
#         self.ndac = Signal() # No Data Accepted      /
#         self.ifc  = Signal() # Interface Clear    \
#         self.srq  = Signal() # Service Request    |  Management bus
#         self.atn  = Signal() # Attention          /
#         self.ren  = Signal() # Remote Enable

#     def elaborate(self, platform):
#         m = Module()

#         m.d.comb += [
#             # Data lines
#             self.pads.dio_t.oe.eq(self.doe),
#             self.pads.dio_t.o.eq(self.do),
#             self.pads.dio_t.i.eq(self.di),

#             # Control lines
#             self.pads.eoi_t.oe.eq(1),
#             self.pads.
#         ]

#         return m


class GPIBControllerSubtarget(Elaboratable):
    def elaborate(self, platform):
        m = Module()
        return m


class GPIBControllerInterface:
    def __init__(self, interface, logger):
        self.lower   = interface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE

    async def reset(self):
        self._logger.debug("GPIB: reset")
        await self.lower.reset()


class GPIBControllerApplet(GlasgowApplet):
    logger = logging.getLogger(__name__)
    help = "control, talk, and listen to devices on the GPIB (née HP-IB) instrumentation bus"
    description = """
    Control, talk, and listen to devices on the IEEE 488.1 bus, known as GPIB or HP-IB. This bus
    is typically used to remotely control instrumentation, such as multimeters, oscilloscopes,
    frequency generators, and so on, though it is also used for some historic computer peripherals.

    The GPIB connector is wired as follows (front view of plug/cable side):

    ::
        _______________________________________________________________________
        \\                                                                     /
         \\    DIO1 DIO2 DIO3 DIO4 EOI  DAV  NRFD NDAC IFC  SRQ  ATN  Shld    /
          \\     1    2    3    4    5    6    7    8    9   10   11   12    /
           \\   24   23   22   21   20   19   18   17   16   15   14   13   /
            \\ GND  GND  GND  GND  GND  GND  GND  REN DIO8  DIO7 DIO6 DIO5 /
             \\___________________________________________________________/

    With the default pin configuration for this applet, the device pins 1..16 should be wired to
    the male GPIB connector pins in this sequence:

        1, 2, 3, 4, 13, 14, 15, 16, 6, 7, 8, 9, 11, 5, 10, 17
    """
    required_revision = "C0"

    __pins = ("dav", "nrfd", "ndac", "ifc", "atn", "eoi", "srq", "ren")
    __pin_sets = ("dio",)

    @classmethod
    def add_build_arguments(cls, parser, access):
        super().add_build_arguments(parser, access)

        # IEEE Std 488.1-2003 §7.1:
        # Selection of a minimum set of interface functions from Clause 4 leads to the following
        # minimum set of signal lines in order to be system compatible:
        # a) DIO 1–7
        # b) DAV, NRFD, NDAC
        # c) IFC and ATN (unnecessary in systems without a controller)

        # Required pins first.
        access.add_pin_set_argument(parser, "dio", range(7, 9), default=8, required=True)
        access.add_pin_argument(parser, "dav",  default=True, required=True)
        access.add_pin_argument(parser, "nrfd", default=True, required=True)
        access.add_pin_argument(parser, "ndac", default=True, required=True)
        # Non-required pins second.
        access.add_pin_argument(parser, "ifc", default=True)
        access.add_pin_argument(parser, "atn", default=True)
        access.add_pin_argument(parser, "eoi", default=True)
        access.add_pin_argument(parser, "srq", default=True)
        access.add_pin_argument(parser, "ren", default=True)

    def build(self, target, args):
        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        iface.add_subtarget(GPIBControllerSubtarget(
            pads=iface.get_pads(args, pins=self.__pins, pin_sets=self.__pin_sets),
            out_fifo=iface.get_out_fifo(),
            in_fifo=iface.get_in_fifo()
        ))

    @classmethod
    def add_run_arguments(cls, parser, access):
        pass # None of the parameters are configurable.

    async def run(self, device, args):
        # Although running GPIB on 3.3 V would be in-spec, none of the devices likely to have it
        # will use anything but 5 V, and so we don't need this to be configurable.
        await device.set_voltage(args.port, 5.0)

        iface = await device.demultiplexer.claim_interface(
            self, self.mux_interface, args,
            # Strictly speaking only NRFD, NDAC, and SRQ need to be pulled up; however there is no
            # harm in enabling the built-in ~10k pullups on every line, and this can help avoid
            # glitches in the complicated GPIB message coding state machines.
            pull_high=self.__pins + self.__pin_sets)
        gpib_iface = GPIBControllerInterface(iface, self.logger)
        return gpib_iface

# -------------------------------------------------------------------------------------------------

class GPIBControllerAppletTestCase(GlasgowAppletTestCase, applet=GPIBControllerApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()

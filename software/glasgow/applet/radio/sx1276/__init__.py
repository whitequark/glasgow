# Ref: SX1276/77/78/79 - 137 MHz to 1020 MHz Low Power Long Range Transceiver Datasheet
# Ref: https://www.semtech.com/products/wireless-rf/lora-connect/sx1276#documentation
# Accession: G00086

import math
import asyncio
import logging
from amaranth import *

from ....support.logging import *
from ....arch.sx1276 import *
from ...interface.spi_controller import SPIControllerSubtarget, SPIControllerInterface
from ... import *


class RadioSX1276Error(GlasgowAppletError):
    pass


class RadioSX1276Subtarget(Elaboratable):
    def __init__(self, spi_subtarget, reset_t, dut_reset):
        self.spi_subtarget = spi_subtarget
        self.reset_t = reset_t
        self.dut_reset = dut_reset

    def elaborate(self, platform):
        m = Module()

        m.submodules.spi_subtarget = self.spi_subtarget

        m.d.comb += [
            self.reset_t.o.eq(~self.dut_reset),
            self.reset_t.oe.eq(1),
        ]

        return m


class RadioSX1276Interface:
    def __init__(self, interface, logger, device, addr_dut_reset):
        self.lower   = interface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE
        self._device = device
        self._addr_dut_reset = addr_dut_reset

    def _log(self, message, *args) -> None:
        self._logger.log(self._level, "SX1276: " + message, *args)

    async def _apply_reset(self, reset) -> None:
        await self._device.write_register(self._addr_dut_reset, int(reset))

    async def reset(self) -> None:
        self._log("reset")
        await self.lower.synchronize()
        await self._apply_reset(True)
        await self.lower.delay_us(100) # TODO: reference DS
        await self.lower.synchronize()
        await self._apply_reset(False)
        await self.lower.delay_us(500) # TODO: reference DS
        await self.lower.synchronize()

    async def _read(self, address: int, *, length=1) -> int:
        assert address in range(0x7f) and length >= 1
        await self.lower.write([(0<<7)|address], hold_ss=True)
        value = int.from_bytes(await self.lower.read(length))
        self._log("read [%02x]=<%.*x>", address, length * 2, value)
        return value

    async def _write(self, address: int, value: int, *, length=1) -> None:
        assert address in range(0x7f) and isinstance(value, int) and length >= 1
        self._log("write [%02x]=<%.*x>", address, length * 2, value)
        await self.lower.write([(1<<7)|address, *value.to_bytes(length)])

    async def identify(self) -> int:
        version = await self._read(Addr.RegVersion)
        self._log("version=%02x", version)
        if version != Version.ProductionRevision:
            raise RadioSX1276Error(f"unknown version {version:#x} returned by device")
        return version


class RadioSX1276Applet(GlasgowApplet):
    logger = logging.getLogger(__name__)
    help = "transmit and receive using SX1276/7/8/9 RF PHYs"
    description = """
    Transmit and receive packets using the SX1276/7/8/9 RF PHYs. SX1276 is the base device, while
    SX1277/8/9 are the lower cost, reduced functionality, interface compatible versions of the same.

    [TODO: expand]
    """

    __pins = ("cs", "sck", "copi", "cipo", "reset", "dio0")

    @classmethod
    def add_build_arguments(cls, parser, access):
        access.add_build_arguments(parser)

        access.add_pin_argument(parser, "cs",    required=True, default=True)
        access.add_pin_argument(parser, "sck",   required=True, default=True)
        access.add_pin_argument(parser, "copi",  required=True, default=True)
        access.add_pin_argument(parser, "cipo",  required=True, default=True)
        access.add_pin_argument(parser, "reset", required=False, default=True)
        access.add_pin_argument(parser, "dio0",  required=False, default=True) # currently unused

        parser.add_argument(
            "-f", "--frequency", metavar="FREQ", type=int, default=1000,
            help="set SPI frequency to FREQ kHz (default: %(default)s)")

    def build(self, target, args):
        dut_reset, self.__addr_dut_reset = target.registers.add_rw(1)

        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        pads = iface.get_pads(args, pins=self.__pins)

        spi_subtarget = SPIControllerSubtarget(
            pads=pads,
            out_fifo=iface.get_out_fifo(),
            in_fifo=iface.get_in_fifo(),
            period_cyc=math.ceil(target.sys_clk_freq / (args.frequency * 1000)),
            delay_cyc=math.ceil(target.sys_clk_freq / 1e6),
            sck_idle=0,
            sck_edge="rising",
            cs_active=0,
        )
        sx1276_subtarget = RadioSX1276Subtarget(spi_subtarget, pads.reset_t, dut_reset)
        return iface.add_subtarget(sx1276_subtarget)

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        spi_iface = SPIControllerInterface(iface, self.logger)
        sx1276_iface = RadioSX1276Interface(spi_iface, self.logger, device,
                                                   self.__addr_dut_reset)
        return sx1276_iface

    @classmethod
    def tests(cls):
        from . import test
        return test.RadioSX1276AppletTestCase

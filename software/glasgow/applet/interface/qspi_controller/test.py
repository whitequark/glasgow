import logging

from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import fifo

from ... import *
from ....gateware.ports import PortGroup, SimulationPort, SimulationPlatform
from tests.gateware.test_qspi import simulate_flash, stream_get, stream_put
from . import QSPIControllerApplet, QSPIControllerSubtarget, QSPIControllerInterface


class InterfaceWrapper:
    def __init__(self, ctx, *, in_fifo, out_fifo):
        self._ctx = ctx
        self._in_fifo = in_fifo
        self._out_fifo = out_fifo

    async def read(self, count):
        buffer = bytearray()
        for _ in range(count):
            buffer.append(await stream_get(self._ctx, self._in_fifo.r_stream))
        return bytes(buffer)

    async def write(self, data):
        for octet in data:
            await stream_put(self._ctx, self._out_fifo.w_stream, octet)

    async def flush(self):
        pass


class QSPIControllerAppletTestCase(GlasgowAppletTestCase, applet=QSPIControllerApplet):
    logger = logging.getLogger(__name__)

    @synthesis_test
    def test_build(self):
        self.assertBuilds()

    def test_fifo(self):
        ports = PortGroup()
        ports.sck = SimulationPort(1, direction="io") # ideally should be an output port
        ports.io  = SimulationPort(4, direction="io")
        ports.cs  = SimulationPort(1, direction="io") # likewise

        out_fifo = fifo.SyncFIFOBuffered(width=8, depth=4)
        out_fifo.stream = out_fifo.r_stream

        in_fifo = fifo.SyncFIFOBuffered(width=8, depth=4)
        in_fifo.stream = in_fifo.w_stream
        in_fifo.flush = Signal(1)

        dut = QSPIControllerSubtarget(
            ports=ports,
            out_fifo=out_fifo,
            in_fifo=in_fifo,
            divisor=1,
            us_cycles=10,
        )

        rst = Signal()

        m = Module()
        m.d.comb += ResetSignal().eq(rst)
        m.submodules.dut = dut
        m.submodules.out_fifo = out_fifo
        m.submodules.in_fifo = in_fifo

        async def testbench_controller(ctx):
            iface = InterfaceWrapper(ctx, out_fifo=out_fifo, in_fifo=in_fifo)
            qspi_iface = QSPIControllerInterface(iface, self.logger)

            async with qspi_iface.select():
                o_data = bytes.fromhex("0b000000000000000000000000")
                i_data = await qspi_iface.exchange(o_data)
                print(i_data.hex())

            await ctx.tick().repeat(20)
            ctx.set(rst, 1)
            for _ in range(2):
                await ctx.tick()
            ctx.set(rst, 0)
            await ctx.tick().repeat(20)

            async with qspi_iface.select():
                o_data = bytes.fromhex("0b000000000000000000000000")
                i_data = await qspi_iface.exchange(o_data)
                print(i_data.hex())

        testbench_flash = simulate_flash(ports, memory=b"nya nya awa!nya nyaaaaan")

        # FIXME: amaranth-lang/amaranth#1446
        sim = Simulator(Fragment.get(m, SimulationPlatform()))
        sim.add_clock(1e-6)
        sim.add_testbench(testbench_controller)
        sim.add_testbench(testbench_flash, background=True)
        with sim.write_vcd("test.vcd"):
            sim.run()

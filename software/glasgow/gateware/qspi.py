from amaranth import *
from amaranth.lib import enum, data, wiring, stream, io
from amaranth.lib.wiring import In, Out, connect, flipped

from .ports import PortGroup
from .iostream import IOStreamer, IOClocker


__all__ = ["QSPIMode", "QSPIEnframer", "QSPIDeframer", "QSPIController"]


class QSPIMode(enum.Enum, shape=3):
    Dummy = 0
    PutX1 = 1
    GetX1 = 2
    PutX2 = 3
    GetX2 = 4
    PutX4 = 5
    GetX4 = 6
    Swap  = 7 # normal SPI


class QSPIEnframer(wiring.Component):
    def __init__(self, *, chip_count=1):
        assert chip_count >= 1

        super().__init__({
            "octets": In(stream.Signature(data.StructLayout({
                "chip": range(1 + chip_count),
                "mode": QSPIMode,
                "data": 8,
            }))),
            "frames": Out(IOStreamer.o_stream_signature({
                "io0": 1,
                "io1": 1,
                "io2": 1,
                "io3": 1,
                "cs": chip_count,
            }, meta_layout=QSPIMode))
        })

    def elaborate(self, platform):
        m = Module()

        cycle = Signal(range(8))
        m.d.comb += self.frames.valid.eq(self.octets.valid)
        with m.If(self.octets.valid & self.frames.ready):
            with m.Switch(self.octets.p.mode):
                with m.Case(QSPIMode.PutX1, QSPIMode.GetX1, QSPIMode.Swap):
                    m.d.comb += self.octets.ready.eq(cycle == 7)
                with m.Case(QSPIMode.PutX2, QSPIMode.GetX2):
                    m.d.comb += self.octets.ready.eq(cycle == 3)
                with m.Case(QSPIMode.PutX4, QSPIMode.GetX4):
                    m.d.comb += self.octets.ready.eq(cycle == 1)
                with m.Case(QSPIMode.Dummy):
                    m.d.comb += self.octets.ready.eq(cycle == 0)
            m.d.sync += cycle.eq(Mux(self.octets.ready, 0, cycle + 1))

        rev_data = self.octets.p.data[::-1] # MSB first
        with m.Switch(self.octets.p.mode):
            with m.Case(QSPIMode.PutX1, QSPIMode.Swap):
                m.d.comb += self.frames.p.port.io0.o.eq(rev_data.word_select(cycle, 1))
                m.d.comb += self.frames.p.port.io0.oe.eq(0b1)
                m.d.comb += self.frames.p.i_en.eq(self.octets.p.mode == QSPIMode.Swap)
            with m.Case(QSPIMode.GetX1):
                m.d.comb += self.frames.p.port.io0.oe.eq(0b1)
                m.d.comb += self.frames.p.i_en.eq(1)
            with m.Case(QSPIMode.PutX2):
                m.d.comb += Cat(self.frames.p.port.io1.o,
                                self.frames.p.port.io0.o).eq(rev_data.word_select(cycle, 2))
                m.d.comb += Cat(self.frames.p.port.io1.oe,
                                self.frames.p.port.io0.oe).eq(0b11)
            with m.Case(QSPIMode.GetX2):
                m.d.comb += self.frames.p.i_en.eq(1)
            with m.Case(QSPIMode.PutX4):
                m.d.comb += Cat(self.frames.p.port.io3.o,
                                self.frames.p.port.io2.o,
                                self.frames.p.port.io1.o,
                                self.frames.p.port.io0.o).eq(rev_data.word_select(cycle, 4))
                m.d.comb += Cat(self.frames.p.port.io3.oe,
                                self.frames.p.port.io2.oe,
                                self.frames.p.port.io1.oe,
                                self.frames.p.port.io0.oe).eq(0b1111)
            with m.Case(QSPIMode.GetX4):
                m.d.comb += self.frames.p.i_en.eq(1)
        m.d.comb += self.frames.p.port.cs.o.eq((1 << self.octets.p.chip)[1:])
        m.d.comb += self.frames.p.port.cs.oe.eq(1)
        m.d.comb += self.frames.p.meta.eq(self.octets.p.mode)

        return m


class QSPIDeframer(wiring.Component): # meow :3
    def __init__(self):
        super().__init__({
            "frames": In(IOStreamer.i_stream_signature({
                "sck": 1, # FIXME: should not be needed
                "io0": 1,
                "io1": 1,
                "io2": 1,
                "io3": 1,
                "cs": 1, # FIXME: should not be needed
            }, meta_layout=QSPIMode)),
            "octets": Out(stream.Signature(data.StructLayout({
                "data": 8,
            }))),
        })

    def elaborate(self, platform):
        m = Module()

        cycle = Signal(range(8))
        m.d.comb += self.frames.ready.eq(~self.octets.valid | self.octets.ready)
        with m.If(self.frames.valid):
            with m.Switch(self.frames.p.meta):
                with m.Case(QSPIMode.GetX1, QSPIMode.Swap):
                    m.d.comb += self.octets.valid.eq(cycle == 7)
                with m.Case(QSPIMode.GetX2):
                    m.d.comb += self.octets.valid.eq(cycle == 3)
                with m.Case(QSPIMode.GetX4):
                    m.d.comb += self.octets.valid.eq(cycle == 1)
            with m.If(self.frames.ready):
                m.d.sync += cycle.eq(Mux(self.octets.valid, 0, cycle + 1))

        data_reg = Signal(8)
        with m.Switch(self.frames.p.meta):
            with m.Case(QSPIMode.GetX1, QSPIMode.Swap): # note: samples IO1
                m.d.comb += self.octets.p.data.eq(Cat(self.frames.p.port.io1.i, data_reg))
            with m.Case(QSPIMode.GetX2):
                m.d.comb += self.octets.p.data.eq(Cat(self.frames.p.port.io0.i,
                                                      self.frames.p.port.io1.i, data_reg))
            with m.Case(QSPIMode.GetX4):
                m.d.comb += self.octets.p.data.eq(Cat(self.frames.p.port.io0.i,
                                                      self.frames.p.port.io1.i,
                                                      self.frames.p.port.io2.i,
                                                      self.frames.p.port.io3.i, data_reg))
        with m.If(self.frames.valid & self.frames.ready):
            m.d.sync += data_reg.eq(self.octets.p.data)

        return m


class QSPIController(wiring.Component):
    def __init__(self, ports, *, chip_count=1, use_ddr_buffers=False):
        assert len(ports.sck) == 1 and ports.sck.direction in (io.Direction.Output, io.Direction.Bidir)
        assert len(ports.io) == 4 and ports.io.direction == io.Direction.Bidir
        assert len(ports.cs) >= 1 and ports.cs.direction in (io.Direction.Output, io.Direction.Bidir)

        self._ports = PortGroup(
            sck=ports.sck,
            io0=ports.io[0],
            io1=ports.io[1],
            io2=ports.io[2],
            io3=ports.io[3],
            cs=~ports.cs,
        )
        self._ddr = use_ddr_buffers

        super().__init__({
            "o_octets": In(stream.Signature(data.StructLayout({
                "chip": range(1 + chip_count),
                "mode": QSPIMode,
                "data": 8
            }))),
            "i_octets": Out(stream.Signature(data.StructLayout({
                "data": 8
            }))),

            "divisor": In(16),
        })

    def elaborate(self, platform):
        ratio = (2 if self._ddr else 1)

        m = Module()

        m.submodules.enframer = enframer = QSPIEnframer()
        connect(m, controller=flipped(self.o_octets), enframer=enframer.octets)

        # FIXME: make clock toggle only when CS# is active
        m.submodules.io_clocker = io_clocker = IOClocker("sck", {
            "io0": 1,
            "io1": 1,
            "io2": 1,
            "io3": 1,
            "cs": len(self._ports.cs),
        }, o_ratio=ratio, meta_layout=QSPIMode)
        connect(m, enframer=enframer.frames, io_clocker=io_clocker.i_stream)
        m.d.comb += io_clocker.divisor.eq(self.divisor)

        m.submodules.io_streamer = io_streamer = IOStreamer({
            "sck": 1,
            "io0": 1,
            "io1": 1,
            "io2": 1,
            "io3": 1,
            "cs": len(self._ports.cs),
        }, self._ports, init={
            "sck": {"o": 1, "oe": 1}, # Motorola "Mode 3" with clock idling high
            "cs":  {"o": 0, "oe": 1}, # deselected
        }, ratio=ratio, meta_layout=QSPIMode)
        connect(m, io_clocker=io_clocker.o_stream, io_streamer=io_streamer.o_stream)

        m.submodules.deframer = deframer = QSPIDeframer()
        connect(m, io_streamer=io_streamer.i_stream, deframer=deframer.frames)

        connect(m, deframer=deframer.octets, controller=flipped(self.i_octets))

        return m

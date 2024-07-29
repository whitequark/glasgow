from amaranth import *
from amaranth.lib import enum, data, wiring, stream, io
from amaranth.lib.wiring import In, Out

from glasgow.gateware.ports import PortGroup


__all__ = ["IOStreamer"]


def _iter_ioshape(ioshape, *args):
    if isinstance(ioshape, int):
        yield args
    if isinstance(ioshape, dict):
        for name in ioshape:
            yield tuple(arg[name] for arg in args)


def _map_ioshape(ioshape, fn):
    if isinstance(ioshape, int):
        return fn(ioshape)
    if isinstance(ioshape, dict):
        return data.StructLayout(
            {name: fn(width) for name, width in ioshape.items()})
    assert False


class IOStreamer(wiring.Component):
    """I/O buffer to stream adapter.

    This adapter instantiates I/O buffers for a port (FF or DDR) and connects them to a pair of
    streams, one for the outputs of the buffers and one for the inputs. Whenever an `o_stream`
    transfer occurs, the state of the output is updated _t1_ cycles later; if `o_stream.p.i_en`
    is set, then _t2_ cycles later, a payload with the data captured at the same time as
    the outputs were updated appears on `i_stream.p.i`.

    Arbitrary ancillary data may be provided with `o_stream` transfers via `o_stream.p.meta`,
    and this data will be relayed back as `i_stream.p.meta` with the output-to-input latency
    of the buffer. Higher-level protocol engines can use this data to indicate how the inputs
    must be processed without needing counters or state machines on a higher level to match
    the latency (and, usually, without needing any knowledge of the latency at all).

    On reset, output ports have their drivers enabled, and bidirectional ports have them disabled.
    All of the signals are deasserted, which could be a low or a high level depending on the port
    polarity.
    """

    @staticmethod
    def o_stream_signature(ioshape, /, *, ratio=1, meta_layout=0):
        return stream.Signature(data.StructLayout({
            "port": _map_ioshape(ioshape, lambda width: data.StructLayout({
                "o":  width if ratio == 1 else data.ArrayLayout(width, ratio),
                "oe": 1,
            })),
            "i_en": 1,
            "meta": meta_layout,
        }))

    @staticmethod
    def i_stream_signature(ioshape, /, *, ratio=1, meta_layout=0):
        return stream.Signature(data.StructLayout({
            "port": _map_ioshape(ioshape, lambda width: data.StructLayout({
                "i":  width if ratio == 1 else data.ArrayLayout(width, ratio),
            })),
            "meta": meta_layout,
        }))

    def __init__(self, ioshape, ports, /, *, ratio=1, init=None, meta_layout=0):
        assert isinstance(ioshape, (int, dict))
        assert ratio in (1, 2)

        self._ioshape = ioshape
        self._ports   = ports
        self._ratio   = ratio
        self._init    = init

        super().__init__({
            "o_stream":  In(self.o_stream_signature(ioshape, ratio=ratio, meta_layout=meta_layout)),
            "i_stream": Out(self.i_stream_signature(ioshape, ratio=ratio, meta_layout=meta_layout)),
        })

    def elaborate(self, platform):
        m = Module()

        if self._ratio == 1:
            buffer_cls, latency = io.FFBuffer, 2
        if self._ratio == 2:
            # FIXME: should this be 2 or 3? the latency differs between i[0] and i[1]
            buffer_cls, latency = io.DDRBuffer, 3

        if isinstance(self._ports, io.PortLike):
            m.submodules.buffer = buffer = buffer_cls("io", self._ports)
        if isinstance(self._ports, PortGroup):
            buffer = {}
            for name, sub_port in self._ports.__dict__.items():
                m.submodules[f"buffer_{name}"] = buffer[name] = buffer_cls("io", sub_port)

        o_latch = Signal(_map_ioshape(self._ioshape, lambda width: data.StructLayout({
            "o":  width,
            "oe": 1,
        })), init=self._init)
        with m.If(self.o_stream.valid & self.o_stream.ready):
            for buffer_parts, stream_parts in _iter_ioshape(self._ioshape, buffer, self.o_stream.p.port):
                m.d.comb += buffer_parts.o.eq(stream_parts.o)
                m.d.comb += buffer_parts.oe.eq(stream_parts.oe)
            for latch_parts, stream_parts in _iter_ioshape(self._ioshape, o_latch, self.o_stream.p.port):
                if self._ratio == 1:
                    m.d.sync += latch_parts.o.eq(stream_parts.o)
                else:
                    m.d.sync += latch_parts.o.eq(stream_parts.o[-1])
                m.d.sync += latch_parts.oe.eq(stream_parts.oe)
        with m.Else():
            for buffer_parts, latch_parts in _iter_ioshape(self._ioshape, buffer, o_latch):
                if self._ratio == 1:
                    m.d.comb += buffer_parts.o.eq(latch_parts.o)
                else:
                    m.d.comb += buffer_parts.o.eq(latch_parts.o.replicate(self._ratio))
                m.d.comb += buffer_parts.oe.eq(latch_parts.oe)

        def delay(value, name):
            for stage in range(latency):
                next_value = Signal.like(value, name=f"{name}_{stage}")
                m.d.sync += next_value.eq(value)
                value = next_value
            return value

        i_en = delay(self.o_stream.valid & self.o_stream.ready &
                     self.o_stream.p.i_en, name="i_en")
        meta = delay(self.o_stream.p.meta, name="meta")

        # This skid buffer is organized as a shift register to avoid any uncertainties associated
        # with the use of an async read memory. On platforms that have LUTRAM, this implementation
        # may be slightly worse than using LUTRAM, and may have to be revisited in the future.
        skid = Array(Signal(self.i_stream.payload.shape(), name=f"skid_{stage}")
                     for stage in range(1 + latency))
        for skid_parts, buffer_parts in _iter_ioshape(self._ioshape, skid[0].port, buffer):
            m.d.comb += skid_parts.i.eq(buffer_parts.i)
        m.d.comb += skid[0].meta.eq(meta)

        skid_at = Signal(range(1 + latency))
        with m.If(i_en & ~self.i_stream.ready):
            # m.d.sync += Assert(skid_at != latency)
            m.d.sync += skid_at.eq(skid_at + 1)
            for n_shift in range(latency):
                m.d.sync += skid[n_shift + 1].eq(skid[n_shift])
        with m.Elif((skid_at != 0) & self.i_stream.ready):
            m.d.sync += skid_at.eq(skid_at - 1)

        m.d.comb += self.i_stream.payload.eq(skid[skid_at])
        m.d.comb += self.i_stream.valid.eq(i_en | (skid_at != 0))
        m.d.comb += self.o_stream.ready.eq(self.i_stream.ready & (skid_at == 0))

        return m


class IOClocker(wiring.Component):
    def __init__(self, clock, ioshape, *, o_ratio=1, meta_layout=0, divisor_width=16):
        assert isinstance(ioshape, dict)
        assert isinstance(clock, str)
        assert o_ratio in (1, 2)

        self._clock     = clock
        self._i_ioshape = ioshape
        self._o_ioshape = {clock: 1, **ioshape}
        self._o_ratio   = o_ratio

        super().__init__({
            "i_stream":  In(IOStreamer.o_stream_signature(self._i_ioshape, ratio=1,
                meta_layout=meta_layout)),
            "o_stream": Out(IOStreamer.o_stream_signature(self._o_ioshape, ratio=o_ratio,
                meta_layout=meta_layout)),

            "divisor": In(divisor_width),
        })

    def elaborate(self, platform):
        m = Module()

        for i_parts, o_parts in _iter_ioshape(self._i_ioshape, self.i_stream.p.port, self.o_stream.p.port):
            m.d.comb += o_parts.o .eq(i_parts.o.replicate(self._o_ratio))
            m.d.comb += o_parts.oe.eq(i_parts.oe)
        m.d.comb += self.o_stream.p.meta.eq(self.i_stream.p.meta)

        clock = Signal()
        if self._o_ratio == 1:
            m.d.comb += self.o_stream.p.port[self._clock].o.eq(clock)
        if self._o_ratio == 2:
            m.d.comb += self.o_stream.p.port[self._clock].o.eq(Cat(~clock, clock))
        m.d.comb += self.o_stream.p.port[self._clock].oe.eq(1)
        m.d.comb += self.o_stream.p.i_en.eq(self.i_stream.p.i_en & clock)

        timer = Signal.like(self.divisor)
        phase = Signal()
        with m.If((timer == 0) | (timer == 1)):
            m.d.comb += self.o_stream.valid.eq(self.i_stream.valid)
            m.d.comb += self.i_stream.ready.eq(self.o_stream.ready & clock)
            with m.If(self.i_stream.valid & self.o_stream.ready):
                with m.If((self._o_ratio == 2) & (self.divisor == 0)):
                    m.d.sync += phase.eq(0)
                    m.d.comb += clock.eq(1)
                with m.Else():
                    m.d.sync += phase.eq(~phase)
                    m.d.comb += clock.eq(phase)
                m.d.sync += timer.eq(self.divisor)
        with m.Else():
            m.d.sync += timer.eq(timer - 1)

        return m

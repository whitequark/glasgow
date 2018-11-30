# Ref: Intel® Low Pin Count (LPC) Interface Specification
# Document Number: 251289-001

# The LPC bus makes a monitor fairly hard to implement by using variable-length frames in three
# different ways.
#  1. The LPC frame field *width* is variable. Address and data width can only by determined
#     by completely parsing the frame header.
#  2. The LPC frame field *position* is variable, even within the same frame type. Synchronization
#     cycle insertion means the frame needs to be completely parsed in order to determine where
#     the data or acknowledgement is located.
#  3. The LPC frame *extent* is variable. LFRAME# is only asserted at frame start, and nothing
#     is asserted at frame end, so frame end can only be determined by completely parsing
#     the frame.
#
# It would not be possible to stream raw LPC frames to the host as-is (logic analyzer style,
# with {LAD,LFRAME} occupying low bits and framing occupying high bits) because revAB uses 30 MHz
# FIFO clock and the PCI clock is 33.33 MHz. Thus, frames need to be processed, and thus, frames
# need to be parsed completely.
#
# If frames are parsed, there is a choice between streaming raw frames to host after adding
# an appropriate header with length and flags, or streaming processed frames.
#  * Streaming raw frames has the advantage of simplicity and reducing the amount of bugs in less
#    used frame formats. However, it introduces a latency of up to 1 frame, which requires
#    buffering.
#  * Streaming processed frames has the advantage of directly streaming frames to the host with
#    minimal latency. However, there are very many frame formats, and no easy way to test them,
#    since x86 systems do not allow generating arbitrary LPC frames.
#
# An additional consideration is that if frame filtering is to be performed in gateware, buffering
# of up to 1 frame (or at least up to 1 frame header, which is almost as bad) will have to be
# performed anyway. Since there could be a very large amount of non-POST traffic (e.g. when reading
# the BIOS image over LPC), a POST card use case would greatly benefit from filtering in terms
# of reducing buffer overruns.
#
# As a result, the following design is used for the LPC monitor:
#  * All supported frames are parsed completely, in the LPC clock domain.
#  * Two FIFOs are used. Data FIFO buffers raw (4-bit) LAD values. Control FIFO buffers packet
#    sizes and header flags like "buffer overrun".
#  * Each time a payload nibble is parsed, a word is pushed into data FIFO. Nibbles such as TAR
#    or 2nd and later repeat of SYNC are not pushed. This limits the data FIFO size to either:
#     a) at most 32 nibbles, if 128-byte FWH reads are not supported, or
#     b) at most 273 nibbles, if 128-byte FWH reads are supported.
#    (Values taken from LPC specification and include all TAR and SYNC cycles. Actual FIFO depth
#    requirements are slightly lower because of that.)
#  * Each time a complete packet is parsed and either accepted or rejected, the running count
#    of the nibbles in the data FIFO is pushed into the control FIFO.
#    - Note: the control FIFO size has to be the same as the data FIFO size, to accomodate corner
#      cases such as a back-to-back sequence of aborts on the bus, which is effectively a series
#      of frames that each have size 1.
#  * On the read end of control and data FIFO, a simple packetizer either skips all nibbles of
#    rejected packets, or else downconverts nibbles of accepted packets to bytes and pushes them
#    into the host FIFO.
#
# This design also has a desirable property that the LPC state machine can be reset at will
# (such as during bus aborts) and yet the framing does not need to be self-synchronizing, because
# the packetizer is independent from the LPC FSM. At the same time, even a self-synchronizing
# encoding would not be able to reliably transfer aborted frames.

import logging
import asyncio
import argparse
import struct
from bitarray import bitarray
from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from migen.genlib.fifo import SyncFIFOBuffered
from migen.genlib.fsm import FSM

from .. import *
from ...arch.lpc import *
from ...gateware.pads import *


class LPCBus(Module):
    def __init__(self, pads):
        self.lad    = pads.lad_t
        self.lframe = ~pads.lframe_t.i
        self.lreset = ~pads.lreset_t.i
        self.lclk   = pads.lclk_t.i


class LPCMonitorFramePacketizer(Module):
    def __init__(self, in_fifo, depth=512):
        self.submodules.ctrl_fifo = ctrl_fifo = SyncFIFOBuffered(width=11, depth=depth)
        self.submodules.data_fifo = data_fifo = SyncFIFOBuffered(width=4,  depth=depth)

        ctrl = Record([
            ("accept",   1),
            ("overflow", 1),
            ("length",   9),
        ])
        data = Signal(4)

        self.submodules.fsm = FSM()
        self.fsm.act("IDLE",
            If(in_fifo.writable & ctrl_fifo.readable,
                NextValue(ctrl.raw_bits(), ctrl_fifo.dout),
                ctrl_fifo.re.eq(1),
                If(ctrl_fifo.dout[0],
                    NextState("HEADER-1")
                ).Else(
                    NextState("SKIP")
                )
            )
        )
        self.fsm.act("HEADER-1",
            If(in_fifo.writable,
                in_fifo.we.eq(1),
                in_fifo.din.eq(ctrl.length[8:] | (ctrl.overflow << 7)),
                NextState("HEADER-2")
            )
        )
        self.fsm.act("HEADER-2",
            If(in_fifo.writable,
                in_fifo.we.eq(1),
                in_fifo.din.eq(ctrl.length[:8]),
                NextState("DATA-HIGH")
            )
        )
        self.fsm.act("DATA-HIGH",
            If(ctrl.length == 0,
                NextState("IDLE")
            ).Else(
                If(in_fifo.writable & data_fifo.readable,
                    data_fifo.re.eq(1),
                    NextValue(data, data_fifo.dout),
                    NextValue(ctrl.length, ctrl.length - 1),
                    NextState("DATA-LOW")
                )
            )
        )
        self.fsm.act("DATA-LOW",
            If(ctrl.length == 0,
                If(in_fifo.writable,
                    in_fifo.we.eq(1),
                    in_fifo.din.eq(data << 4),
                    NextState("IDLE")
                )
            ).Else(
                If(in_fifo.writable & data_fifo.readable,
                    data_fifo.re.eq(1),
                    in_fifo.we.eq(1),
                    in_fifo.din.eq(Cat(data_fifo.dout, data)),
                    NextValue(ctrl.length, ctrl.length - 1),
                    NextState("DATA-HIGH")
                )
            )
        )
        self.fsm.act("SKIP",
            If(ctrl.length == 0,
                NextState("IDLE")
            ).Else(
                If(data_fifo.readable,
                    data_fifo.re.eq(1),
                    NextValue(ctrl.length, ctrl.length - 1),
                )
            )
        )


class LPCMonitorFrameParser(Module):
    def __init__(self, bus, ctrl_fifo, data_fifo):
        lad_r = Signal.like(bus.lad.i)
        self.sync.lpc += lad_r.eq(bus.lad.i)

        push    = Signal()
        accept  = Signal()
        reject  = Signal()

        length  = Signal(max=data_fifo.depth)
        self.comb += [
            data_fifo.we.eq(push),
            data_fifo.din.eq(lad_r),
        ]
        self.sync += [
            length.eq(Mux(ctrl_fifo.we & ctrl_fifo.writable, 0, length) +
                      (push & data_fifo.writable))
        ]

        overrun = Signal()
        self.comb += [
            ctrl_fifo.we.eq(accept | reject),
            ctrl_fifo.din.eq(Cat(accept, overrun, length)),
        ]
        self.sync += [
            If(~data_fifo.writable | ~ctrl_fifo.writable,
                overrun.eq(1)
            ).Elif(ctrl_fifo.we,
                overrun.eq(0)
            )
        ]

        index = Signal(max=8)
        trans = Record([
            ("start",   4),
            ("dir",     1),
            ("cyctype", 2),
            ("size",    2),
            ("addr",    32),
            ("sync",    4),
        ])

        self.submodules.fsm = ResetInserter()(FSM())
        self.comb += self.fsm.reset.eq(bus.lframe)
        self.sync += accept.eq((bus.lframe | self.fsm.after_entering("DONE")) & (length != 0))
        self.fsm.act("START",
            push.eq(~bus.lframe),
            NextValue(trans.start,   lad_r),
            Case(lad_r, {
                START_TARGET: NextState("TARGET-CYCTYPE-DIR"),
                STOP_ABORT:   NextState("DONE"),
                "default":    NextState("DONE"),
            })
        )
        self.fsm.act("DONE",
            NextState("DONE")
        )
        # Target memory or I/O cycles
        self.fsm.act("TARGET-CYCTYPE-DIR",
            push.eq(1),
            NextValue(trans.dir,     lad_r[1]),
            NextValue(trans.cyctype, lad_r[2:3]),
            NextState("TARGET-ADDR"),
            Case(lad_r[2:3], {
                CYCTYPE_IO:   NextValue(index, 3),
                CYCTYPE_MEM:  NextValue(index, 7),
                "default":    NextState("DONE")
            })
        )
        self.fsm.act("TARGET-ADDR",
            push.eq(1),
            NextValue(trans.addr,    Cat(lad_r, trans.addr)),
            NextValue(index, index - 1),
            If(index == 0,
                If(trans.dir == DIR_READ,
                    NextValue(index, 1),
                    NextState("TARGET-RD-TAR")
                ).Else(
                    NextValue(index, 1),
                    NextState("TARGET-WR-DATA")
                )
            )
        )
        # - Target read sub-cycles
        self.fsm.act("TARGET-RD-TAR",
            NextValue(index, index - 1),
            If(index == 0,
                NextState("TARGET-RD-SYNC")
            )
        )
        self.fsm.act("TARGET-RD-SYNC",
            NextValue(trans.sync, lad_r),
            If((lad_r == SYNC_SHORT_WAIT) | (lad_r == SYNC_LONG_WAIT),
                push.eq(index == 0),
                NextValue(index, 1),
            ).Elif((lad_r == SYNC_READY) | (lad_r == SYNC_ERROR),
                push.eq(1),
                NextValue(index, 1),
                NextState("TARGET-RD-DATA")
            ).Else(
                push.eq(1),
                NextState("DONE")
            )
        )
        self.fsm.act("TARGET-RD-DATA",
            push.eq(1),
            If(index == 0,
                NextState("DONE")
            )
        )
        # - Target write sub-cycles
        self.fsm.act("TARGET-WR-DATA",
            push.eq(1),
            If(index == 0,
                NextValue(index, 1),
                NextState("TARGET-WR-TAR")
            )
        )
        self.fsm.act("TARGET-WR-TAR",
            NextValue(index, index - 1),
            If(index == 0,
                NextValue(index, 0),
                NextState("TARGET-WR-SYNC")
            )
        )
        self.fsm.act("TARGET-WR-SYNC",
            NextValue(trans.sync, lad_r),
            If((lad_r == SYNC_SHORT_WAIT) | (lad_r == SYNC_LONG_WAIT),
                push.eq(index == 0),
                NextValue(index, 1),
            ).Else(
                push.eq(1),
                NextState("DONE")
            )
        )


class LPCMonitorSubtarget(Module):
    def __init__(self, pads, reset, make_in_fifo):
        self.submodules.bus = bus = LPCBus(pads)

        self.clock_domains.cd_lpc = ClockDomain()
        self.comb     += self.cd_lpc.clk.eq(bus.lclk)
        self.specials += AsyncResetSynchronizer(self.cd_lpc, reset)

        self.submodules.packetizer = ClockDomainsRenamer("lpc")(
            LPCMonitorFramePacketizer(make_in_fifo(self.cd_lpc), depth=127))
        self.submodules.parser = ClockDomainsRenamer("lpc")(
            LPCMonitorFrameParser(self.bus, self.packetizer.ctrl_fifo, self.packetizer.data_fifo))


class LPCFrameParser:
    def __init__(self, frame_bytes, length):
        self.length = length
        self.offset = 0
        self.frame = bitarray()
        self.frame.frombytes(bytes(frame_bytes))
        self.items = []
        self.warn = False

    def _add(self, item, *args):
        self.items.append(item.format(*args))

    def _err(self, item, *args):
        self._add("err=" + item, *args)
        raise ValueError("unrecognized")

    def _get_nibbles(self, count):
        if self.offset + count > self.length:
            self._err("truncated")

        start    = self.offset * 4
        subframe = self.frame[start:start + count * 4]
        value    = subframe.tobytes()
        self.offset += count
        return value

    def _get_nibble(self):
        value, = self._get_nibbles(1)
        return value >> 4

    def _get_byte(self):
        value, = struct.unpack(">B", self._get_nibbles(2))
        return value

    def _get_word(self):
        value, = struct.unpack(">H", self._get_nibbles(4))
        return value

    def _get_dword(self):
        value, = struct.unpack(">L", self._get_nibbles(8))
        return value

    def _parse_cyctype_dir(self):
        cyctype_dir = self._get_nibble()

        cyctype = (cyctype_dir & 0b1100) >> 2
        if cyctype == CYCTYPE_IO:
            self._add("io")
        elif cyctype == CYCTYPE_MEM:
            self._add("mem")
        elif cyctype == CYCTYPE_DMA:
            self._add("dma")
        else:
            self._add("type={:2b}", cyctype)
            self._err("illegal")

        cycdir = (cyctype_dir & 0b0010) >> 1
        if cycdir == DIR_READ:
            self._add("rd")
        elif cycdir == DIR_WRITE:
            self._add("wr")

        if cyctype == CYCTYPE_IO:
            address = self._get_word()
            self._add("addr={:04x}", address)
        elif cyctype == CYCTYPE_MEM:
            address = self._get_dword()
            self._add("addr={:08x}", address)
        else:
            self._err("illegal")

        return cyctype, cycdir

    def _parse_sync(self):
        sync1 = self._get_nibble()
        if sync1 in (SYNC_SHORT_WAIT, SYNC_LONG_WAIT):
            if sync1 == SYNC_SHORT_WAIT:
                self._add("sync=short")
            if sync1 == SYNC_LONG_WAIT:
                self._add("sync=long")
            sync2 = self._get_nibble()
        else:
            sync2 = sync1

        if sync2 == SYNC_READY:
            self._add("sync=ok")
        elif sync2 == SYNC_READY_MORE:
            self._add("sync=more")
        elif sync2 == SYNC_ERROR:
            self._add("sync=err")
        elif sync2 == 0b1111:
            # Not an actual code, but a consequence of SYNC always following TAR, and LAD being
            # driven to 1111 during TAR.
            self._add("sync=1111")
            self._err("timeout")
        else:
            self._add("sync={:04b}", sync2)
            self._err("illegal")

        return sync2

    def _parse_target(self):
        cyctype, cycdir = self._parse_cyctype_dir()
        if cycdir == DIR_READ:
            sync = self._parse_sync()
            data = self._get_byte()
            self._add("data={:02x}", data)
        if cycdir == DIR_WRITE:
            data = self._get_byte()
            self._add("data={:02x}", data)
            sync = self._parse_sync()

    def parse_frame(self):
        start = self._get_nibble()
        if start == START_TARGET:
            self._add("target")
            self._parse_target()

        elif start in (START_BUS_MASTER_0, START_BUS_MASTER_1):
            self._add("master")
            self._add("idx={:d}", start & 1)
            self._err("unimplemented")

        elif start in (START_FW_MEM_READ, START_FW_MEM_WRITE):
            self._add("fw-mem")
            if start == START_FW_MEM_READ:
                self._add("read")
            if start == START_FW_MEM_WRITE:
                self._add("write")
            self._err("unimplemented")

        elif start == STOP_ABORT:
            self.warn = True
            self._add("abort")

        else:
            self._add("start={:04b}", start)
            self._err("illegal")

        residue = self.length - self.offset
        if residue > 0:
            self.warn = True
            self._add("residue=<{:s}>", self._get_nibbles(residue).hex()[:residue])


class LPCMonitorInterface:
    def __init__(self, interface, logger):
        self.lower   = interface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE

    def _log(self, message, *args):
        self._logger.log(self._level, "LPC: " + message, *args)

    async def monitor(self):
        header,  = struct.unpack(">H", await self.lower.read(2))
        overflow = header >> 15
        length   = header & 0x7fff
        if overflow:
            self._logger.warning("FIFO overflow")
        if length == 0:
            return

        packet = await self.lower.read((length + 1) // 2)
        self._log("data=<%s>", packet.hex()[:length])

        parser = LPCFrameParser(packet, length)
        level  = logging.INFO
        try:
            parser.parse_frame()
            if parser.warn:
                level = logging.WARN
        except ValueError as e:
            level = logging.ERROR
        self._logger.log(level, "LPC: %s", " ".join(parser.items))


class LPCMonitorApplet(GlasgowApplet, name="lpc-monitor"):
    preview = True
    logger = logging.getLogger(__name__)
    help = "monitor transactions on the Intel LPC bus"
    description = """
    TBD
    """

    __pin_sets = ("lad",)
    __pins = ("lframe", "lreset", "lclk")

    @classmethod
    def add_build_arguments(cls, parser, access):
        super().add_build_arguments(parser, access)

        access.add_pin_argument(parser, "lclk", default=True)
        access.add_pin_set_argument(parser, "lad", width=4, default=True)
        access.add_pin_argument(parser, "lframe", default=True)
        access.add_pin_argument(parser, "lreset", default=True)

    def build(self, target, args):
        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        subtarget = LPCMonitorSubtarget(
            pads=iface.get_pads(args, pin_sets=self.__pin_sets, pins=self.__pins),
            reset=iface.reset,
            make_in_fifo=lambda cd: iface.get_in_fifo(clock_domain=cd),
        )
        iface.submodules += subtarget
        target.platform.add_period_constraint(subtarget.bus.lclk, 30)

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        lpc_iface = LPCMonitorInterface(iface, self.logger)
        return lpc_iface

    @classmethod
    def add_interact_arguments(cls, parser):
        p_operation = parser.add_subparsers(dest="operation", metavar="OPERATION")

    async def interact(self, device, args, lpc_iface):
        # for _ in range(128):
        # while True:
        #     await lpc_iface.monitor()
        with open("lpc.bin", "wb") as f:
            f.write(await lpc_iface.lower.read(1000000, hint=1000000))

# -------------------------------------------------------------------------------------------------

class LPCMonitorAppletTool(GlasgowAppletTool, applet=LPCMonitorApplet):
    help = "TBD"
    description = "TBD"

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "file", metavar="FILE", type=argparse.FileType("rb"),
            help="read LPC frames from FILE")

    async def run(self, args):
        while True:
            header,  = struct.unpack(">H", args.file.read(2))
            overflow = header >> 15
            length   = header & 0x7fff
            if overflow:
                self.logger.warning("FIFO overflow")
            if length == 0:
                continue

            packet = args.file.read((length + 1) // 2)
            self.logger.debug("data=<%s>", packet.hex()[:length])

            parser = LPCFrameParser(packet, length)
            level  = logging.INFO
            try:
                parser.parse_frame()
                if parser.warn:
                    level = logging.WARN
            except ValueError as e:
                level = logging.ERROR
            self.logger.log(level, "LPC: %s", " ".join(parser.items))

# -------------------------------------------------------------------------------------------------

class LPCMonitorAppletTestCase(GlasgowAppletTestCase, applet=LPCMonitorApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()

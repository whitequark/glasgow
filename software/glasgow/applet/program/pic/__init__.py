import enum
import logging
from bitstring import Bits
from migen import *

from ....gateware.clockgen import *


__all__ = ["ProgramPICSubtarget", "ProgramPICInterface"]


@enum.unique
class _Cmd(enum.IntEnum):
    DISABLE = 0x00
    ENABLE  = 0x01
    WRITE   = 0x02
    READ    = 0x03


class ProgramPICSubtarget(Module):
    def __init__(self, bus, in_fifo, out_fifo, period_cyc):
        self.submodules.bus    = bus
        self.submodules.clkgen = clkgen = ResetInserter()(ClockGen(period_cyc))

        cmd   = Signal(max=max(_Cmd) + 1)
        datai = Signal(8)
        datao = Signal(8)
        count = Signal(max=64 + 1)
        bitno = Signal(max=8 + 1)

        self.comb += [
            bus.clk.eq(clkgen.clk),
        ]
        self.sync += [
            If(clkgen.stb_r,
                bus.dat_o.eq(datao[0]),
                datao.eq(datao[1:])
            ).Elif(clkgen.stb_f,
                datai.eq(Cat(datai[1:], bus.dat_i))
            )
        ]

        self.submodules.fsm = FSM(reset_state="RECV-COMMAND")
        self.fsm.act("RECV-COMMAND",
            If(out_fifo.readable,
                out_fifo.re.eq(1),
                NextValue(cmd, out_fifo.dout),
                NextState("PARSE-COMMAND")
            )
        )
        self.fsm.act("PARSE-COMMAND",
            If(cmd == _Cmd.ENABLE,
                NextValue(bus.en, 1),
                NextState("RECV-COMMAND")
            ).Elif(cmd == _Cmd.DISABLE,
                NextValue(bus.en, 0),
                NextState("RECV-COMMAND")
            ).Elif(cmd == _Cmd.WRITE,
                NextValue(bus.dat_oe, 1),
                NextState("RECV-COUNT")
            ).Elif(cmd == _Cmd.READ,
                NextValue(bus.dat_oe, 0),
                NextState("RECV-COUNT")
            )
        )
        self.fsm.act("RECV-COUNT",
            If(out_fifo.readable,
                out_fifo.re.eq(1),
                NextValue(count, out_fifo.dout),
                NextState("PRE-TRANSFER/RECV-DATA")
            )
        )
        self.fsm.act("PRE-TRANSFER/RECV-DATA",
            NextValue(bitno, 8),
            If(out_fifo.readable & (cmd == _Cmd.WRITE),
                out_fifo.re.eq(1),
                If(count < 8,
                    NextValue(datao, out_fifo.dout >> (8 - count[:3])),
                ).Else(
                    NextValue(datao, out_fifo.dout),
                )
            ),
            If(out_fifo.readable | (cmd != _Cmd.WRITE),
                If(count == 0,
                    NextState("RECV-COMMAND")
                ).Else(
                    NextState("TRANSFER")
                )
            )
        )
        self.comb += clkgen.reset.eq(~self.fsm.ongoing("TRANSFER"))
        self.fsm.act("TRANSFER",
            If(self.clkgen.stb_r,
                NextValue(count, count - 1),
                NextValue(bitno, bitno - 1),
            ).Elif(self.clkgen.stb_f,
                If((bitno == 0) | (count == 0),
                    NextState("POST-TRANSFER/SEND-DATA")
                ),
            )
        )
        self.fsm.act("POST-TRANSFER/SEND-DATA",
            If(in_fifo.writable & (cmd == _Cmd.READ),
                in_fifo.we.eq(1),
                in_fifo.din.eq(datai),
            ),
            If(in_fifo.writable | (cmd != _Cmd.READ),
                If(count == 0,
                    NextState("RECV-COMMAND")
                ).Else(
                    NextState("PRE-TRANSFER/RECV-DATA")
                )
            )
        )


class ProgramPICInterface:
    def __init__(self, interface, logger):
        self.lower   = interface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name.startswith(__name__) else logging.TRACE

    def _log(self, message, *args):
        self._logger.log(self._level, "PIC: " + message, *args)

    async def _enable(self):
        self._log("enable")
        await self.lower.write([_Cmd.ENABLE])

    async def _disable(self):
        self._log("disable")
        await self.lower.write([_Cmd.DISABLE])

    async def _write(self, data_bits):
        data_bits = Bits(data_bits)
        assert len(data_bits) <= 64
        self._log("write bits=%s", data_bits.bin)
        await self.lower.write([_Cmd.WRITE, len(data_bits), *data_bits.tobytes()])

    async def _read(self, count):
        assert count <= 64
        await self.lower.write([_Cmd.READ, count])
        data_bytes = await self.lower.read((count + 7) // 8)
        data_bits = Bits(bytes=data_bytes, length=count)
        self._log("read bits=%s", data_bits.bin)
        return data_bits

    async def enter_lvp(self):
        self._log("enter lvp")
        # 33-bit pattern with trailing 0
        await self._enable()
        await self._write("0b01001101010000110100100001010000, 0b0")
        await self.lower.flush()

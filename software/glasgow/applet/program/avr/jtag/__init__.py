# Ref: ATmega16U4/ATmega32U4 8-bit Microcontroller with 16/32K bytes of ISP Flash and USB Controller datasheet
# Accession: G00058

import logging

from .....support.bits import *
from .....arch.avr.jtag import *
from ....interface.jtag_probe import JTAGProbeApplet
from .... import *
from .. import *


class ProgramAVRJTAGInterface(ProgramAVRInterface):
    def __init__(self, interface, logger):
        self.lower   = interface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE

    def _log(self, message, *args):
        self._logger.log(self._level, "AVR JTAG: " + message, *args)

    async def _write_cmd(self, command):
        await self.lower.write_dr(bits(command, 15))
        await self.lower.run_test_idle(0)

    async def _exchange_cmd(self, command):
        result = await self.lower.exchange_dr(bits(command, 15))
        await self.lower.run_test_idle(0)
        return result.to_int()

    async def _poll_cmd(self, command, mask):
        result = 0
        while (result & mask) == 0:
            result = await self._exchange_cmd(command)

    async def programming_enable(self):
        self._log("programming enable")
        await self.lower.write_ir(IR_AVR_RESET)
        await self.lower.write_dr(bits(1, 1))
        await self.lower.write_ir(IR_PROG_ENABLE)
        await self.lower.write_dr(bits(0b1010_0011_0111_0000, 16))

    async def programming_disable(self):
        self._log("programming disable")
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00001000) # Load No Operation Command (1)
        await self._write_cmd(0b1100011_00001000) # Load No Operation Command (2)
        await self.lower.write_ir(IR_PROG_ENABLE)
        await self.lower.write_dr(bits(0, 16))
        await self.lower.write_ir(IR_AVR_RESET)
        await self.lower.write_dr(bits(0, 1))
        # The datasheet says: "Note that the reset will be active as long as there is a logic
        # “one” in the Reset Chain. The output from this chain is not latched." This is a lie.
        # No amount of ones in the reset chain will reset the IC until you go through Update-DR.
        await self.lower.run_test_idle(0)

    async def read_signature(self):
        self._log("read signature")
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00001000) # Enter Signature Byte Read
        signature = []
        for address in range(3):
            await self._write_cmd(0b0000011_00000000|address) # Load Address Byte
            await self._write_cmd(0b0110010_00000000) # Read Signature Byte (1)
            result = await self._exchange_cmd(0b0110011_00000000) # Read Signature Byte (2)
            signature.append(result & 0xff)
        return tuple(signature)

    async def read_calibration(self, address):
        self._log("read calibration address %#04x", address)
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00001000) # Enter Calibration Byte Read
        await self._write_cmd(0b0000011_00000000|address) # Load Address Byte
        await self._write_cmd(0b0110110_00000000) # Read Calibration Byte (1)
        result = await self._exchange_cmd(0b0110111_00000000) # Read Calibration Byte (2)
        return result & 0xff

    async def read_fuse(self, address):
        self._log("read fuse address %#04x", address)
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00000100) # Enter Fuse/Lock Bit Read
        read_cmd_1 = {
            0: 0b0110010_00000000,
            1: 0b0111110_00000000,
            2: 0b0111010_00000000,
        }[address]
        read_cmd_2 = read_cmd_1 | 0b0000001_00000000
        await self._write_cmd(read_cmd_1) # Read Fuse Byte (1)
        result = await self._exchange_cmd(read_cmd_2) # Read Fuse Byte (2)
        return result & 0xff

    async def write_fuse(self, address, data):
        self._log("write fuse address %#04x data %02x", address, data)
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_01000000) #  Enter Fuse Write
        await self._write_cmd(0b0010011_00000000 | data) # Load Data Byte
        read_cmd_2 = {
            0: 0b0110001_00000000,
            1: 0b0110101_00000000,
            2: 0b0111001_00000000,
        }[address]
        read_cmd_1 = read_cmd_2 | 0b0000010_00000000
        await self._write_cmd(read_cmd_1) # Write Fuse Byte (1)
        await self._write_cmd(read_cmd_2) # Write Fuse Byte (2)
        await self._write_cmd(read_cmd_1) # Write Fuse Byte (3)
        await self._write_cmd(read_cmd_1) # Write Fuse Byte (4)
        await self._poll_cmd(read_cmd_1,
                             0b0000010_00000000) # Poll for Fuse Byte Write complete

    async def read_lock_bits(self):
        self._log("read lock bits")
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00000100) # Enter Fuse/Lock Bit Read
        await self._write_cmd(0b0110110_00000000) # Read Lock Bits (1)
        result = await self._exchange_cmd(0b0110111_00000000) # Read Lock Bits (2)
        return result & 0xff

    async def write_lock_bits(self, data):
        self._log("write lock bits data %02x", data)
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00100000) # Enter Lock Bit Write
        await self._write_cmd(0b0010011_00000000 | data) # Load Data Byte
        await self._write_cmd(0b0110011_00000000) # Write Lock Bits (1)
        await self._write_cmd(0b0110001_00000000) # Write Lock Bits (2)
        await self._write_cmd(0b0110011_00000000) # Write Lock Bits (3)
        await self._write_cmd(0b0110011_00000000) # Write Lock Bits (4)
        await self._poll_cmd(0b0110011_00000000,
                             0b0000010_00000000) # Poll for Lock Bit Write complete

    async def _load_address(self, address):
        await self._write_cmd(0b0001011_00000000 |
                              (address >> 16) & 0xff) # Load Address Extended High Byte
        await self._write_cmd(0b0000111_00000000 |
                              (address >>  8) & 0xff) # Load Address High Byte
        await self._write_cmd(0b0000011_00000000 |
                              (address >>  0) & 0xff) # Load Address Low Byte

    async def read_program_memory(self, address):
        self._log("read program memory address %#06x", address)
        word_address, byte_address = address >> 1, address & 1
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00000010) # Enter Flash Read
        await self._load_address(word_address)
        await self._write_cmd(0b0110010_00000000) # Read Data Low and High Byte (1)
        result0 = await self._exchange_cmd(0b0110110_00000000) # Read Data Low and High Byte (2)
        result1 = await self._exchange_cmd(0b0110111_00000000) # Read Data Low and High Byte (3)
        return (result1 if byte_address else result0) & 0xff

    async def read_program_memory_range(self, start, length):
        self._log("read program memory addresses %#06x:%#06x", start, start + length)
        word_address, byte_address = start >> 1, start & 1
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00000010) # Enter Flash Read
        await self._load_address(word_address)
        await self.lower.write_ir(IR_PROG_PAGEREAD)
        if byte_address: # skip the low byte if starting at an odd address
            await self.lower.read_dr(8)
        data = bytearray()
        for _ in range(length):
            result = await self.lower.read_dr(8)
            data.append(result.to_int())
        return data

    async def load_program_memory_page(self, address, data):
        self._log("load program memory address %#06x data %02x", address, data)
        word_address, byte_address = address >> 1, address & 1
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00010000) # Enter Flash Write
        await self._load_address(address)
        await self.lower.write_ir(IR_PROG_PAGELOAD)
        if byte_address: # skip the low byte if starting at an odd address
            await self.lower.write_dr(bits(0xff, 8))
        # for byte in data:
        await self.lower.write_dr(bits(data, 8))
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0110111_00000000) # Latch Data (1)
        await self._write_cmd(0b1110111_00000000) # Latch Data (2)
        await self._write_cmd(0b0110111_00000000) # Latch Data (3)

    async def write_program_memory_page(self, address):
        self._log("write program memory page at %#06x", address)
        word_address, byte_address = address >> 1, address & 1
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00010000) # Enter Flash Write
        await self._load_address(address)
        await self._write_cmd(0b0110111_00000000) # Write Flash Page (1)
        await self._write_cmd(0b0110101_00000000) # Write Flash Page (2)
        await self._write_cmd(0b0110111_00000000) # Write Flash Page (3)
        await self._write_cmd(0b0110111_00000000) # Write Flash Page (4)
        await self._poll_cmd(0b0110111_00000000,
                             0b0000010_00000000) # Poll for Page Write Complete

    async def read_eeprom(self, address):
        self._log("read EEPROM address %#06x", address)
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00000011) # Enter EEPROM Read
        await self._load_address(address)
        await self._write_cmd(0b0110011_00000000) # Read Data Byte (1)
        await self._write_cmd(0b0110110_00000000) # Read Data Byte (2)
        result = await self._exchange_cmd(0b0110111_00000000) # Read Data Byte (3)
        return result & 0xff

    async def load_eeprom_page(self, address, data):
        self._log("load EEPROM address %#06x data %02x", address, data)
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00010001) # Enter EEPROM Write
        await self._load_address(address)
        await self._write_cmd(0b0010011_00000000 | data) # Load Data Byte
        await self._write_cmd(0b0110111_00000000) # Latch Data (1)
        await self._write_cmd(0b1110111_00000000) # Latch Data (2)
        await self._write_cmd(0b0110111_00000000) # Latch Data (3)

    async def write_eeprom_page(self, address):
        self._log("write EEPROM page at %#06x", address)
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_00010001) # Enter EEPROM Write
        await self._load_address(address)
        await self._write_cmd(0b0110011_00000000) # Write EEPROM Page (1)
        await self._write_cmd(0b0110001_00000000) # Write EEPROM Page (2)
        await self._write_cmd(0b0110011_00000000) # Write EEPROM Page (3)
        await self._write_cmd(0b0110011_00000000) # Write EEPROM Page (4)
        await self._poll_cmd(0b0110011_00000000,
                             0b0000010_00000000) # Poll for Page Write Complete

    async def chip_erase(self):
        self._log("chip erase")
        await self.lower.write_ir(IR_PROG_COMMANDS)
        await self._write_cmd(0b0100011_10000000) # Chip Erase (1)
        await self._write_cmd(0b0110001_10000000) # Chip Erase (2)
        await self._write_cmd(0b0110011_10000000) # Chip Erase (3)
        await self._write_cmd(0b0110011_10000000) # Chip Erase (3)
        await self._poll_cmd(0b0110011_10000000,
                             0b0000010_00000000) # Poll for Chip Erase Complete


class ProgramAVRJTAGApplet(ProgramAVRApplet, JTAGProbeApplet, name="program-avr-jtag"):
    logger = logging.getLogger(__name__)
    help = f"{ProgramAVRApplet.help} via JTAG"
    description = """
    Identify, program, and verify Microchip AVR microcontrollers using JTAG programming.
    """

    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_tap_arguments(parser, access)

    async def run(self, device, args):
        tap_iface = await self.run_tap(ProgramAVRJTAGApplet, device, args)
        return ProgramAVRJTAGInterface(tap_iface, self.logger)

# -------------------------------------------------------------------------------------------------

class ProgramAVRJTAGAppletTestCase(GlasgowAppletTestCase, applet=ProgramAVRJTAGApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()

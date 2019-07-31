# Ref: IBM PS/2 Hardware Technical Reference ­- Keyboards (101- and 102-Key)
# Accession: G00037

import logging
import asyncio

from ... import *
from ...interface.ps2_host import PS2HostApplet


CMD_RESET                   = 0xff
CMD_RESEND                  = 0xfe
CMD_SET_KEY_MAKE_ONLY       = 0xfd
CMD_SET_KEY_MAKE_BREAK      = 0xfc
CMD_SET_KEY_TYPEMATIC       = 0xfb
CMD_SET_ALL_MAKE_ONLY       = 0xf9
CMD_SET_ALL_MAKE_BREAK      = 0xf8
CMD_SET_ALL_TYPEMATIC       = 0xf7
CMD_SET_DEFAULTS            = 0xf6
CMD_DISABLE_REPORTING       = 0xf5
CMD_ENABLE_REPORTING        = 0xf4 # default
CMD_SET_TYPEMATIC_OPTIONS   = 0xf3
CMD_GET_DEVICE_ID           = 0xf2
CMD_GET_SET_SCANCODE_SET    = 0xf0
CMD_ECHO                    = 0xee
CMD_SET_INDICATORS          = 0xed


class SensorKeyboardPS2Error(GlasgowAppletError):
    pass


class SensorKeyboardPS2Interface:
    def __init__(self, interface, logger):
        self.lower   = interface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE

    def _log(self, message, *args):
        self._logger.log(self._level, "PS/2 Keyboard: " + message, *args)

    async def reset(self):
        bat_result, = await self.lower.send_command(CMD_RESET, ret=1)
        self._log("reset bat-result=%02x", bat_result)
        if bat_result == 0xaa:
            pass # passed
        elif bat_result == 0xfc:
            raise SensorKeyboardPS2Error("Basic Assurance Test failed")
        else:
            raise SensorKeyboardPS2Error("invalid Basic Assurance Test response {:#04x}"
                                         .format(bat_result))

    async def identify(self):
        ident, = await self.lower.send_command(CMD_GET_DEVICE_ID, ret=1)
        self._log("ident=%02x", ident)
        return ident


class SensorKeyboardPS2Applet(PS2HostApplet, name="sensor-keyboard-ps2"):
    logger = logging.getLogger(__name__)
    help = "receive key press/release information from PS/2 keyboards"
    description = """
    Identify PS/2 keyboard, and receive key press/release updates. The updates may be logged or
    forwarded to the desktop on Linux.

    This applet has additional Python dependencies:
        * uinput (optional, required for Linux desktop forwarding)
    """

    async def run(self, device, args):
        ps2_iface = await self.run_lower(SensorKeyboardPS2Applet, device, args)
        kbd_iface = SensorKeyboardPS2Interface(ps2_iface, self.logger)
        return kbd_iface

    @classmethod
    def add_interact_arguments(cls, parser):
        parser.add_argument(
            "--no-reset", dest="reset", default=True, action="store_false",
            help="do not send the reset command before initialization (does not affect reset pin)")

        p_operation = parser.add_subparsers(dest="operation", metavar="OPERATION")

        p_stream_log = p_operation.add_parser("stream-log",
            help="stream events and log them")

        p_stream_uinput = p_operation.add_parser("stream-uinput",
            help="stream events and forward them to desktop via uinput (Linux only)")

    async def interact(self, device, args, kbd_iface):
        async def initialize():
            if args.reset:
                await kbd_iface.reset()
            return await kbd_iface.identify()

        try:
            ident = await asyncio.wait_for(initialize(), timeout=1)
        except asyncio.TimeoutError:
            raise SensorKeyboardPS2Error("initialization timeout; connection problem?")

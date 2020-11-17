# Ref: https://static.docs.arm.com/ihi0031/c/IHI0031C_debug_interface_as.pdf
# Document Number: IHI0031C
# Accession: G00027

from enum import IntEnum

from ....support.bitstruct import *


__all__ = [
    "MEM_AP_CSW_addr", "MEM_AP_CSW", "MEM_AP_AddrInc", "MEM_AP_Size",
    "MEM_AP_TAR_addr", "MEM_AP_TAR64_addr",
    "MEM_AP_DRW_addr",
    "MEM_AP_MBT_addr",
    "MEM_AP_T0TR_addr",
    "MEM_AP_BDn_addr",
    "MEM_AP_CFG1_addr", "MEM_AP_CFG1",
    "MEM_AP_CFG_addr", "MEM_AP_CFG",
    "MEM_AP_BASE_addr", "MEM_AP_BASE64_addr", "MEM_AP_BASE",
]


# CSW MEM-AP register layout

MEM_AP_CSW_addr = 0x00

MEM_AP_CSW = bitstruct("MEM_AP_CSW", 32, [
    ("Size",        3),
    (None,          1),
    ("AddrInc",     2),
    ("DeviceEn",    1),
    ("TrinProg",    1),
    ("Mode",        4),
    ("Type",        3),
    ("MTE",         1),
    (None,          7),
    ("SDeviceEn",   1),
    ("Prot",        7),
    ("DbgSwEnable", 1),
])


class MEM_AP_AddrInc(IntEnum):
    DISABLED    = 0b00
    SINGLE      = 0b01
    PACKED      = 0b10


class MEM_AP_Size(IntEnum):
    BYTE        = 0b000
    HALFWORD    = 0b001
    WORD        = 0b010
    DOUBLEWORD  = 0b011
    _128_BITS   = 0b100
    _256_BITS   = 0b101


# TAR MEM-AP register layout

MEM_AP_TAR_addr   = 0x04
MEM_AP_TAR64_addr = 0x08


# DRW MEM-AP register layout

MEM_AP_DRW_addr = 0x0C


# MBT MEM-AP register layout

MEM_AP_MBT_addr = 0x20


# T0TR MEM-AP register layout

MEM_AP_T0TR_addr = 0x30


# BD0-BD3 MEM-AP register layout

def MEM_AP_BDn_addr(n):
    assert n in range(4)
    return 0x10 + n


# CFG1 MEM-AP register layout

MEM_AP_CFG1_addr = 0xE0

MEM_AP_CFG1 = bitstruct("MEM_AP_CFG1", 32, [
    ("TAG0SIZE",    1),
    ("TAG0GRAN",    1),
    (None,         30),
])


# CFG MEM-AP register layout

MEM_AP_CFG_addr = 0xF4

MEM_AP_CFG = bitstruct("MEM_AP_CFG", 32, [
    ("BE",          1),
    ("LA",          1),
    ("LD",          1),
    (None,         29),
])


# BASE MEM-AP register layout

MEM_AP_BASE_addr   = 0xF8
MEM_AP_BASE64_addr = 0xF0

MEM_AP_BASE = bitstruct("MEM_AP_BASE", 32, [
    ("P",           1),
    ("Format",      1),
    (None,         10),
    (None,         20), # BASEADDR[31:12]
])


# IDR MEM-AP register layout (additional)

class MEM_AP_IDR_TYPE(IntEnum):
    AMBA_AHB3       = 0x1
    AMBA_APB2_APB3  = 0x2
    AMBA_AXI3_AXI4  = 0x4
    AMBA_AHB5       = 0x5
    AMBA_APB4       = 0x6
    AMBA_AXI5       = 0x7
    AMBA_AHB5_HPROT = 0x8

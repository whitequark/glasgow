# Ref: SX1276/77/78/79 - 137 MHz to 1020 MHz Low Power Long Range Transceiver Datasheet
# Ref: https://www.semtech.com/products/wireless-rf/lora-connect/sx1276#documentation
# Accession: G00086

# In this machine-readable version of the register table, we use the underscore symbol to imply that
# the data has been changed from what the vendor provided. E.g. the `_LoRa` suffix (used in cases
# where register names clash with each other), or the modem status flag `Header_info_valid` for
# which the vendor did not provide their own name and the description was used.

import enum

from ...support.bitstruct import *


__all__ = [
    "Addr", "Addr_LoRa", "Addr_FSK",
    "Version",
]


# --- Mode-independent registers ------------------------------------------------------------------

class Addr(enum.IntEnum):
    RegFifo                             = 0x00
    RegOpMode                           = 0x01
    # --- 0x02 - 0x05 ---
    RegFrfMsb                           = 0x06
    RegFrfMid                           = 0x07
    RegFrfLsb                           = 0x08
    RegPaConfig                         = 0x09
    RegPaRamp                           = 0x0a
    RegOcp                              = 0x0b
    RegLna                              = 0x0c
    # --- 0x0d - 0x3f ---
    RegDioMapping1                      = 0x40
    RegDioMapping2                      = 0x41
    RegVersion                          = 0x42
    # --- 0x43 - 0x4a ---
    RegTcxo                             = 0x4b
    # --- 0x4c - 0x4c ---
    RegPaDac                            = 0x4d
    # --- 0x4f - 0x5a ---
    RegFormerTemp                       = 0x5b
    # --- 0x5c - 0x60 ---
    RegAgcRef                           = 0x61
    RegAgcThresh1                       = 0x62
    RegAgcThresh2                       = 0x63
    RegAgcThresh3                       = 0x64
    # --- 0x65 - 0x6f ---
    RegPll                              = 0x70

# RegOpMode(0x01)
class Mode(enum.IntEnum):
    Sleep                               = 0b000
    Stdby                               = 0b001
    FSTx                                = 0b010
    Tx                                  = 0b011
    FSRx                                = 0b100
    Rx                                  = 0b101

class ModulationType(enum.IntEnum):
    FSK                                 = 0b00
    OOK                                 = 0b01

class LongRangeMode(enum.IntEnum):
    FSK_OOK                             = 0b0
    LoRa                                = 0b1

RegOpMode = bitstruct("RegOpMode", 8, [
    ("Mode",                            3),
    ("LowFrequencyModeOn",              1), # if 1 then access to lf mode registers (0x61 - 0x73)
    (None,                              1),
    ("ModulationType",                  2),
    ("LongRangeMode",                   1), # only modifiable in sleep mode
])

# RegFrMsb(0x06)
# RegFrMid(0x07)
# RegFrLsb(0x08)

# RegPaConfig(0x09)
class PaSelect(enum.IntEnum):
    PA_BOOST                            = 0b1
    RFO                                 = 0b0

RegPaConfig = bitstruct("RegPaConfig", 8, [
    ("OutputPower",                     4),
    ("MaxPower",                        3),
    ("PaSelect",                        1),
])

# RegPaRamp(0x0a)
class PaRamp(enum.IntEnum):
    _3_4ms                              = 0b0000
    _2ms                                = 0b0001
    _1ms                                = 0b0010
    _500us                              = 0b0011
    _250us                              = 0b0100
    _125us                              = 0b0101
    _100us                              = 0b0110
    _62us                               = 0b0111
    _50us                               = 0b1000
    _40us                               = 0b1001
    _31us                               = 0b1010
    _25us                               = 0b1011
    _20us                               = 0b1100
    _15us                               = 0b1101
    _12us                               = 0b1110
    _10us                               = 0b1111

RegPaRamp = bitstruct("RegPaRamp", 8, [
    ("PaRamp",                          4),
    (None,                              1),
    ("ModulationShaping",               2), # Unused in LoRa mode.
    (None,                              1),
])

# RegOcp(0x0b)
RegOcp = bitstruct("RegOcp", 8, [
    ("OcpTrim",                         5),
    ("OcpOn",                           1),
    (None,                              2),
])

# RegLna(0x0c)
class LnaBoostHf(enum.IntEnum):
    OFF                                 = 0b00
    ON                                  = 0b11

class LnaGain(enum.IntEnum):
    G1                                  = 0b001
    G2                                  = 0b010
    G3                                  = 0b011
    G4                                  = 0b100
    G5                                  = 0b101
    G6                                  = 0b110

RegLna = bitstruct("RegLna", 8, [
    ("LnaBoostHf",                      2),
    (None,                              1),
    ("LnaBoostLf",                      2),
    ("LnaGain",                         3),
])

# RegDioMapping1(0x40)
RegDioMapping1 = bitstruct("RegDioMapping1", 8, [
    ("Dio3Mapping",                     2),
    ("Dio2Mapping",                     2),
    ("Dio1Mapping",                     2),
    ("Dio0Mapping",                     2),
])

# RegDioMapping2(0x41)
class MapPreambleDetect(enum.IntEnum):
    # Map Rssi *or* PreambleDetect to DIO, as summarized on Tables 29 and 30 (G00086)
    Rssi                                = 0b0
    PreambleDetect                      = 0b1

RegDioMapping2 = bitstruct("RegDioMapping2", 8, [
    ("MapPreambleDetect",               1),
    (None,                              3),
    ("Dio5Mapping",                     2),
    ("Dio4Mapping",                     2),
])

# RegVersion(0x42)
class Version(enum.IntEnum):
    # A single specific value for this register is specified in the datasheet.
    ProductionRevision                  = 0x12

# RegTcxo(0x4b)
RegTcxo = bitstruct("RegTcxo", 8, [
    (None,                              4),
    ("TcxoInputOn",                     1),
    (None,                              3),
])

# RegPaDac(0x4d)
class PaDac(enum.IntEnum):
    Default                             = 0b100
    _20dBm_Mode                         = 0b111

RegPaDac = bitstruct("RegPaDac", 8, [
    ("PaDac",                           3),
    (None,                              5),
])

# RegFormerTemp(0x5b)

# RegAgcRef(0x61)
RegAgcRef = bitstruct("RegAgcRef", 8, [
    ("AgcReferenceLevel",               6),
    (None,                              2),
])

# RegAgcThresh1(0x62)

# RegAgcThresh2(0x63)

# RegAgcThresh3(0x64)

# RegPll(0x70)
class PllBandwidth(enum.IntEnum):
    _75kHz                              = 0b00
    _150kHz                             = 0b01
    _225kHz                             = 0b10
    _300kHz                             = 0b11

RegPll = bitstruct("RegPll", 8, [
    (None,                              6),
    ("PllBandwidth",                    2),
])


# --- LoRa mode specific registers ----------------------------------------------------------------

class Addr_LoRa(enum.IntEnum):
    RegFifoAddrPtr                      = 0x0d
    RegFifoTxBaseAddr                   = 0x0e
    RegFifoRxBaseAddr                   = 0x0f
    RegFifoRxCurrentAddr                = 0x10
    RegIrqFlagsMask                     = 0x11
    RegIrqFlags                         = 0x12
    RegRxNbBytes                        = 0x13
    RegRxHeaderCntValueMsb              = 0x14
    RegRxHeaderCntValueLsb              = 0x15
    RegRxPacketCntValueMsb              = 0x16
    RegRxPacketCntValueLsb              = 0x17
    RegModemStat                        = 0x18
    RegPktSnrValue                      = 0x19
    RegPktRssiValue                     = 0x1a
    RegRssiValue                        = 0x1b
    RegHopChannel                       = 0x1c
    RegModemConfig1                     = 0x1d
    RegModemConfig2                     = 0x1e
    # MSB is bytes [1:0] of MODEM_CONFIG_2
    RegSymbTimeoutLsb                   = 0x1f
    RegPreambleMsb                      = 0x20
    RegPreambleLsb                      = 0x21
    RegPayloadLength                    = 0x22
    RegMaxPayloadLength                 = 0x23
    RegHopPeriod                        = 0x24
    RegFifoRxByteAddr                   = 0x25
    RegModemConfig3                     = 0x26
    # Note: This is RESERVED in 4.1 for LoRa mode, but in 4.4 it's an unnamed address that controls
    # the ppm correction factor, and so is decidedly not RESERVED.
    Reg_PpmCorrection                   = 0x27
    RegFeiMsb                           = 0x28
    RegFeiMid                           = 0x29
    RegFeiLsb                           = 0x2a
    RegRssiWideband                     = 0x2c
    # Note: RegIfFreq is referred to inconsistently in the datasheet.
    # RESERVED                          - 0x2d
    # RESERVED                          - 0x2e
    RegIfFreq1                          = 0x2f
    RegIfFreq2                          = 0x30
    RegDetectOptimize                   = 0x31
    # RESERVED                          - 0x32
    RegInvertIQ                         = 0x33
    # RESERVED                          - 0x34
    # RESERVED                          - 0x35
    RegHighBwOptimize1                  = 0x36
    RegDetectionThreshold               = 0x37
    # RESERVED                          - 0x38
    RegSyncWord                         = 0x39
    # Note: RegHighBwOptimize2 is also referred to as RegHighBwOptimize1
    RegHighBwOptimize2                  = 0x3a
    RegInvertIQ2                        = 0x3b

# RegFifoAddrPtr(0x0d)
# RegFifoTxBaseAddr(0x0e)
# RegFifoRxBaseAddr(0x0f)
# RegFifoRxCurrentAddr(0x10)

# RegIrqFlagsMask(0x11)
RegIrqFlagsMask = bitstruct("RegIrqFlagsMask", 8, [
    ("CadDetectedMask",             1),
    ("FhssChangeChannelMask",       1),
    ("CadDoneMask",                 1),
    ("TxDoneMask",                  1),
    ("ValidHeaderMask",             1),
    ("PayloadCrcErrorMask",         1),
    ("RxDoneMask",                  1),
    ("RxTimeoutMask",               1),
])

# RegIrqFlags(0x12)
RegIrqFlags = bitstruct("RegIrqFlags", 8, [
    ("CadDetected",                 1),
    ("FhssChangeChannel",           1),
    ("CadDone",                     1),
    ("TxDone",                      1),
    ("ValidHeader",                 1),
    ("PayloadCrcError",             1),
    ("RxDone",                      1),
    ("RxTimeout",                   1),
])

# RegRxNbBytes(0x13)

# RegRxHeaderCntValueMsb(0x14)
# RegRxHeaderCntValueLsb(0x15)

# RegRxPacketCntValueMsb(0x16)
# RegRxPacketCntValueLsb(0x17)

# RegModemStat(0x18)
RegModemStat = bitstruct("RegModemStat", 8, [
    ("Signal_detected",                 1),
    ("Signal_synchronized",             1),
    ("RX_ongoing",                      1),
    ("Header_info_valid",               1),
    ("Modem_clear",                     1),
    ("RxCodingRate",                    3),
])

# RegPktSnrValue(0x19)

# RegPktRssiValue(0x1a)

# RegRssiValue_LoRa(0x1b)

# RegHopChannel(0x1c)
RegHopChannel = bitstruct("RegHopChannel", 8, [
    ("FhssPresentChannel",              6),
    ("CrcOnPayload",                    1),
    ("PllTimeout",                      1),
])

# RegModemConfig1(0x1d)
class Bw(enum.IntEnum):
    _7_8kHz                             = 0b0000
    _10_4kHz                            = 0b0001
    _15_6kHz                            = 0b0010
    _20_8kHz                            = 0b0011
    _31_25kHz                           = 0b0100
    _41_7kHz                            = 0b0101
    _62_5kHz                            = 0b0110
    _125kHz                             = 0b0111
    _250kHz                             = 0b1000
    _500kHz                             = 0b1001

class CodingRate(enum.IntEnum):
    _4_5                                = 0b001
    _4_6                                = 0b010
    _4_7                                = 0b011
    _4_8                                = 0b100

class ImplicitHeaderModeOn(enum.IntEnum):
    Explicit                            = 0b0
    Implicit                            = 0b1

RegModemConfig1 = bitstruct("RegModemConfig1", 8, [
    ("ImplicitHeaderModeOn",            1),
    ("CodingRate",                      3),
    ("Bw",                              4),
])

# RegModemConfig2(0x1e)
class SpreadingFactor(enum.IntEnum):
    SF6                                 = 0b0110 # 64 chips/sym
    SF7                                 = 0b0111 # 128 chips/sym
    SF8                                 = 0b1000 # 256 chips/sym
    SF9                                 = 0b1001 # 512 chips/sym
    SF10                                = 0b1010 # 1024 chips/sym
    SF11                                = 0b1011 # 2048 chips/sym
    SF12                                = 0b1100 # 4096 chips/sym

RegModemConfig2 = bitstruct("RegModemConfig2", 8, [
    ("SymbTimeout_MSB",                 2),
    ("RxPayloadCrcOn",                  1),
    ("TxContinuousMode",                1),
    ("SpreadingFactor",                 4), # Valid range is 6-12. All other values reserved.
])

# RegSymbTimeoutLsb(0x1f)

# RegPreambleMsb_LoRa(0x20)
# RegPreambleLsb_LoRa(0x21)

# RegPayloadLength_LoRa(0x22)

# RegMaxPayloadLength(0x23)

# RegHopPeriod(0x24)

# RegFifoRxByteAddr(0x25)

# RegModemConfig3(0x26)
RegModemConfig3 = bitstruct("RegModemConfig3", 8, [
    (None,                              2),
    ("AgcAutoOn",                       1),
    ("LowDataRateOptimize",             1), # mandated when sym length exceeds 16ms
    (None,                              4),
])

# Reg_PpmCorrection (0x27)

# RegFeiMsb_LoRa(0x28)
# RegFeiMid_LoRa(0x29)
# RegFeiLsb_LoRa(0x2a)

# RegRssiWideband(0x2c)

# RegIfFreq1(0x2f)
# see errata regarding RegIfFreq1

# RegIfFreq2(0x30)
# see errata regarding RegIfFreq2

# RegDetectOptimize(0x31)
RegDetectOptimize = bitstruct("RegDetectOptimize", 8, [
    ("DetectionOptimize",               3), # NOTE: Set to 0x03 for SF7-12, 0x05 for SF6
    (None,                              4),
    ("AutomaticIFOn",                   1), # NOTE: Should be set to 0x0 after each reset. See errata.
])

# RegInvertIQ(0x33)
RegInvertIQ = bitstruct("RegInvertIQ", 8, [
    ("InvertIQ_TX",                     1),
    (None,                              5),
    ("InvertIQ_RX",                     1),
    (None,                              1),
])

# RegHighBwOptimize1(0x36)
# see errata regarding RegHighBwOptimize1 for 500kHz Bw

# RegDetectionThreshold(0x37)
#  = 0x0A -> SF7-SF12
#  = 0x0C -> SF6

# RegSyncWord(0x39)
# NOTE: Value 0x34 is reserved for LoRaWAN networks. Default is 0x12.

# RegHighBwOptimize2(0x3a)
# see errata regarding RegHighBwOptimize2 for 500kHz Bw

# RegInvertIQ2(0x3b)
# Set to 0x19 for inverted IQ. Default is 0x1D


# --- FSK/OOK mode specific registers -------------------------------------------------------------

class Addr_FSK(enum.IntEnum):
    RegBitrateMsb                       = 0x02
    RegBitrateLsb                       = 0x03
    RegFdevMsb                          = 0x04
    RegFdevLsb                          = 0x05
    # --- 0x06 - 0x0c --- SHARED
    RegRxConfig                         = 0x0d
    RegRssiConfig                       = 0x0e
    RegRssiCollision                    = 0x0f
    RegRssiThresh                       = 0x10
    RegRssiValue                        = 0x11
    RegRxBw                             = 0x12
    RegAfcBw                            = 0x13
    RegOokPeak                          = 0x14
    RegOokFix                           = 0x15
    RegOokAvg                           = 0x16
    # --- 0x17 - 0x19 --- RESERVED
    RegAfcFei                           = 0x1a
    RegAfcMsb                           = 0x1b
    RegAfcLsb                           = 0x1c
    RegFeiMsb                           = 0x1d
    RegFeiLsb                           = 0x1e
    RegPreambleDetect                   = 0x1f
    RegRxTimeout1                       = 0x20
    RegRxTimeout2                       = 0x21
    RegRxTimeout3                       = 0x22
    RegRxDelay                          = 0x23
    RegOsc                              = 0x24
    RegPreambleMsb                      = 0x25
    RegPreambleLsb                      = 0x26
    RegSyncConfig                       = 0x27
    RegSyncValue1                       = 0x28
    RegSyncValue2                       = 0x29
    RegSyncValue3                       = 0x2a
    RegSyncValue4                       = 0x2b
    RegSyncValue5                       = 0x2c
    RegSyncValue6                       = 0x2d
    RegSyncValue7                       = 0x2e
    RegSyncValue8                       = 0x2f
    RegPacketConfig1                    = 0x30
    RegPacketConfig2                    = 0x31
    RegPayloadLength                    = 0x32
    RegNodeAdrs                         = 0x33
    RegBroadcastAdrs                    = 0x34
    RegFifoThresh                       = 0x35
    RegSeqConfig1                       = 0x36
    RegSeqConfig2                       = 0x37
    RegTimerResol                       = 0x38
    RegTimer1Coef                       = 0x39
    RegTimer2Coef                       = 0x3a
    RegImageCal                         = 0x3b
    RegTemp                             = 0x3c
    RegLowBat                           = 0x3d
    RegIrqFlags1                        = 0x3e
    RegIrqFlags2                        = 0x3f
    # --- 0x40 - 0x43 --- SHARED
    RegPllHop                           = 0x44
    # --- 0x45 - 0x5c --- SHARED
    RegBitRateFrac                      = 0x5d

# RegBitrateMsb(0x02)
# RegBitrateLsb(0x03)

# RegFdevMsb(0x04)
# RegFdevLsb(0x05)

# RegRxConfig(0x0d)
RegRxConfig = bitstruct("RegRxConfig", 8, [
    ("RxTrigger",                       3), # G00086 - Table 24 (G00086)
    ("AgcAutoOn",                       1),
    ("AfcAutoOn",                       1),
    ("RestartRxWithPllLock",            1),
    ("RestartRxWithoutPllLock",         1),
    ("RestartRxOnCollision",            1),
])

# RegRssiConfig(0x0e)
class RssiSmoothing(enum.IntEnum):
    _2                                  = 0b000
    _4                                  = 0b001
    _8                                  = 0b010 # default
    _16                                 = 0b011
    _32                                 = 0b100
    _64                                 = 0b101
    _128                                = 0b110
    _256                                = 0b111

RegRssiConfig = bitstruct("RegRssiConfig", 8, [
    ("RssiSmoothing",                   3),
    ("RssiOffset",                      5),
])

# RegRssiCollision(0x0f)

# RegRssiThresh(0x10)

# RegRssiValue_FSK(0x11)

# RegRxBw(0x12)
class RxBwMant(enum.IntEnum):
    _16                                 = 0b00
    _20                                 = 0b01
    _24                                 = 0b10

RegRxBw = bitstruct("RegRxBw", 8, [
    ("RxBwExp",                         3),
    ("RxBwMant",                        2),
    (None,                              3),
])

# RegAfcBw(0x13)
RegAfcBw = bitstruct("RegAfcBw", 8, [
    ("RxBwExpAfc",                      3),
    ("RxBwMantAfc",                     2),
    (None,                              3),
])

# RegOokPeak(0x14)
class OokPeakTheshStep(enum.IntEnum):
    _0_5dB                              = 0b000
    _1_0dB                              = 0b001
    _1_5dB                              = 0b010
    _2_0dB                              = 0b011
    _3_0dB                              = 0b100
    _4_0dB                              = 0b101
    _5_0dB                              = 0b110
    _6_0dB                              = 0b111

class OokThreshType(enum.IntEnum):
    Fixed                               = 0b00
    Peak                                = 0b01
    Average                             = 0b10
    # 0b11 is reserved.

RegOokPeak = bitstruct("RegOokPeak", 8, [
    ("OokPeakTheshStep",                3),
    ("OokThreshType",                   2),
    ("BitSyncOn",                       1),
    (None,                              2),
])

# RegOokFix(0x15)

# RegOokAvg(0x16)
class OokAverageThreshFilt(enum.IntEnum):
    # fC = chip rate/a multiplier of pi, as specified here.
    _32pi                               = 0b00
    _8pi                                = 0b01
    _4pi                                = 0b10
    _2pi                                = 0b11

class OokAverageOffset(enum.IntEnum):
    _0dB                                = 0b00
    _2dB                                = 0b01
    _4dB                                = 0b10
    _6dB                                = 0b11

class OokPeakThreshDec(enum.IntEnum):
    _1_PER_CHIP                         = 0b000
    _1_PER_2_CHIPS                      = 0b001
    _1_PER_4_CHIPS                      = 0b010
    _1_PER_8_CHIPS                      = 0b011
    _2_PER_CHIP                         = 0b100
    _4_PER_CHIP                         = 0b101
    _8_PER_CHIP                         = 0b110
    _16_PER_CHIP                        = 0b111

RegOokAvg = bitstruct("RegOokAvg", 8, [
    ("OokAverageThreshFilt",            2),
    ("OokAverageOffset",                2),
    (None,                              1),
    ("OokPeakThreshDec",                3),
])

# RegAfcFei(0x1a)
RegAfcFei = bitstruct("RegAfcFei", 8, [
    ("AfcAutoClearOn",                  1),
    ("AfcClear",                        1),
    (None,                              1),
    (None,                              1),
    ("AgcStart",                        1),
    (None,                              3),
])

# RegAfcMsb(0x1b)
# RegAfcLsb(0x1c)

# RegFeiMsb_FSK(0x1d)
# RegFeiLsb_FSK(0x1e)

# RegPreambleDetect(0x1f)
RegPreambleDetect = bitstruct("RegPreambleDetect", 8, [
    ("PreambleDetectorTol",             5),
    ("PreambleDetectorSize",            2), # Range 0b00 -> 0b10, 0b11 is reserved.
    ("PreambleDetectorOn",              1),
])

# RegRxTimeout1(0x20)

# RegRxTimeout2(0x21)

# RegRxTimeout3(0x22)

# RegRxDelay(0x23)

# RegOsc(0x24)
class ClkOut(enum.IntEnum):
    FXOSC                               = 0b000
    FXOSC_DIV_2                         = 0b001
    FXOSC_DIV_4                         = 0b010
    FXOSC_DIV_8                         = 0b011
    FXOSC_DIV_16                        = 0b100
    FXOSC_DIV_32                        = 0b101
    RC                                  = 0b110
    OFF                                 = 0b111

RegOsc = bitstruct("RegOsc", 8, [
    ("ClkOut",                          3),
    ("RcCalStart",                      1),
    (None,                              4),
])

# RegPreambleMsb_FSK(0x25)
# RegPreambleLsb_FSK(0x26)

# RegSyncConfig(0x27)
class AutoRestartRxMode(enum.IntEnum):
    OFF                                 = 0b00
    ON_WITHOUT_RELOCK                   = 0b01
    ON                                  = 0b10

RegSyncConfig = bitstruct("RegSyncConfig", 8, [
    ("SyncSize",                        3),
    (None,                              1),
    ("SyncOn",                          1),
    ("PreamblePolarity",                1), # 0b0 -> 0xAA, 0b1 -> 0x55
    ("AutoRestartRxMode",               2),
])

# RegSyncValue1(0x28)
# RegSyncValue2(0x29)
# RegSyncValue3(0x2a)
# RegSyncValue4(0x2b)
# RegSyncValue5(0x2c)
# RegSyncValue6(0x2d)
# RegSyncValue7(0x2e)
# RegSyncValue8(0x2f)

# RegPacketConfig1(0x30)
class CrcWhiteningType(enum.IntEnum):
    CCITT                               = 0b0
    IBM                                 = 0b1

class AddressFiltering(enum.IntEnum):
    Off                                 = 0b00
    NodeAddress                         = 0b01
    NodeAddress_or_BroadcastAddress     = 0b10

class DcFree(enum.IntEnum):
    Off                                 = 0b00
    Manchester                          = 0b01
    Whitening                           = 0b10

RegPacketConfig1 = bitstruct("RegPacketConfig1", 8, [
    ("CrcWhiteningType",                1),
    ("AddressFiltering",                2),
    ("CrcAutoClearOff",                 1),
    ("CrcOn",                           1),
    ("DcFree",                          2),
    ("PacketFormat",                    1),
])

# RegPacketConfig2(0x31)
class DataMode(enum.IntEnum):
    Continuous                          = 0b0
    Packet                              = 0b1

RegPacketConfig2 = bitstruct("RegPacketConfig2", 8, [
    ("PayloadLength_MSB",               3),
    ("BeaconOn",                        1),
    ("IoHomePowerFrame",                1),
    ("IoHomeOn",                        1),
    ("DataMode",                        1),
    (None,                              1),
])

# RegPayloadLength_FSK(0x32)

# RegNodeAdrs(0x33)

# RegBroadcastAdrs(0x34)

# RegFifoThresh(0x35)
class TxStartCondition(enum.IntEnum):
    FifoLevel                           = 0b0
    FifoEmpty                           = 0b1

RegFifoThresh = bitstruct("RegFifoThresh", 8, [
    ("FifoThreshold",                   6),
    (None,                              1),
    ("TxStartCondition",                1),
])


# RegSeqConfig1(0x36)
class FromStart(enum.IntEnum):
    to_LowPowerSelection                = 0b00
    to_RX                               = 0b01
    to_TX                               = 0b10
    to_TX_on_FifoLevel_Int              = 0b11

class IdleMode(enum.IntEnum):
    Standby                             = 0b0
    Sleep                               = 0b1

RegSeqConfig1 = bitstruct("RegSeqConfig1", 8, [
    ("FromTransmit",                    1),
    ("FromIdle",                        1),
    ("LowPowerSelection",               1),
    ("FromStart",                       2),
    ("IdleMode",                        1),
    ("SequencerStop",                   1),
    ("SequencerStart",                  1),
])

# RegSeqConfig2(0x37)
class FromPacketReceived(enum.IntEnum):
    to_SequencerOff                     = 0b000
    to_TX_on_FifoEmpty                  = 0b001
    to_LowPowerSelection                = 0b010
    to_RX_via_FS                        = 0b011 # if frequency changed
    to_RX                               = 0b100 # (no frequency change)

class FromRxTimeout(enum.IntEnum):
    to_RX_via_ReceiveRestart            = 0b00
    to_TX                               = 0b01
    to_LowPowerSelection                = 0b10
    to_SequencerOff                     = 0b11

class FromReceive(enum.IntEnum):
    to_PacketReceived_on_PayloadReady       = 0b001
    to_LowPowerSelection_on_PayloadReady    = 0b010
    to_PacketReceived_on_CrcOk              = 0b011
    to_SequencerOff_on_Rssi                 = 0b100
    to_SequencerOff_on_SyncAddress          = 0b101
    to_SequencerOff_on_PreambleDetect       = 0b110

RegSeqConfig2 = bitstruct("RegSeqConfig2", 8, [
    ("FromPacketReceived",              3),
    ("FromRxTimeout",                   2),
    ("FromReceive",                     3),
])

# RegTimerResol(0x38)
class _TimerResolution(enum.IntEnum):
    OFF                                 = 0b00
    _64us                               = 0b01
    _4_1ms                              = 0b10
    _262ms                              = 0b11

class Timer1Resolution(_TimerResolution):
    pass

class Timer2Resolution(_TimerResolution):
    pass

RegTimerResol = bitstruct("RegTimerResol", 8, [
    ("Timer2Resolution",                2),
    ("Timer1Resolution",                2),
    (None,                              4),
])

# RegTimer1Coef(0x39)

# RegTimer2Coef(0x3a)

# RegImageCal(0x3b)
class TempThreshold(enum.IntEnum):
    _5C                                 = 0b00
    _10C                                = 0b01
    _15C                                = 0b10
    _20C                                = 0b11

class TempChange(enum.IntEnum):
    Lower_than_TempThreshold            = 0b0
    Greater_than_TempThreshold          = 0b1

RegImageCal = bitstruct("RegImageCal", 8, [
    ("TempMonitorOff",                  1),
    ("TempThreshold",                   2),
    ("TempChange",                      1),
    (None,                              1),
    ("ImageCalRunning",                 1),
    ("ImageCalStart",                   1),
    ("AutoImageCalOn",                  1),
])

# RegTemp(0x3c)

# RegLowBat(0x3d)
class LowBatTrim(enum.IntEnum):
    _1_695V                             = 0b000
    _1_764V                             = 0b001
    _1_835V                             = 0b010 # default
    _1_905V                             = 0b011
    _1_976V                             = 0b100
    _2_045V                             = 0b101
    _2_116V                             = 0b110
    _2_185V                             = 0b111

RegLowBat = bitstruct("RegLowBat", 8, [
    ("LowBatTrim",                      3),
    ("LowBatOn",                        1),
    (None,                              4),
])

# RegIrqFlags1(0x3e)
RegIrqFlags1 = bitstruct("RegIrqFlags1", 8, [
    ("SyncAddressMatch",                1),
    ("PreambleDetect",                  1),
    ("Timeout",                         1),
    ("Rssi",                            1),
    ("PllLock",                         1),
    ("TxReady",                         1),
    ("RxReady",                         1),
    ("ModeReady",                       1),
])

# RegIrqFlags2(0x3f)
RegIrqFlags2 = bitstruct("RegIrqFlags2", 8, [
    ("LowBat",                          1),
    ("CrcOk",                           1),
    ("PayloadReady",                    1),
    ("PacketSent",                      1),
    ("FifoOverrun",                     1),
    ("FifoLevel",                       1),
    ("FifoEmpty",                       1),
    ("FifoFull",                        1),
])

# RegPllHop(0x44)
RegPllHop = bitstruct("RegPllHop", 8, [
    (None,                              7),
    ("FastHopOn",                       1),
])

# RegBitRateFrac(0x5d)
RegBitRateFrac = bitstruct("RegBitRateFrac", 8, [
    ("BitRateFrac",                     4),
    (None,                              4),
])

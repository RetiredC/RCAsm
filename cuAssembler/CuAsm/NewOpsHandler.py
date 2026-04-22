# This file is a part of RCAsm software
# (c) 2026, RetiredCoder (RC)
# License: GPLv3, see "LICENSE.TXT" file
# https://github.com/RetiredC

#########################################
# credits:
# https://github.com/kuterd/nv_isa_solver
# though note there are many errors there
#########################################

SM_VER = 89

obfuscate:bool = False
#obfuscate:bool = True

def unsigned(val: int, bits_cnt: int) -> int:
    # Keep only the lowest `bits_cnt` bits
    if bits_cnt <= 0:
        return 0
    mask = (1 << bits_cnt) - 1
    return val & mask

def BRA_II(ins_key, ins_vals, ins_modi):
    if (len(ins_vals) != 2) and (len(ins_vals) != 4):
        return -1
    is_full = len(ins_vals) == 4
    pred = int(ins_vals[0])
    opcode = 2375
    inst = opcode
    inst |= (pred) << 12

    if is_full:
        p = int(ins_vals[1])
        ur = int(ins_vals[2])
        imm = int(ins_vals[3])

        #temp fix
        if (SM_VER == 120) and (ur == 63):
            ur = 255

        if SM_VER == 120:
            mask50 = (1 << 58) - 1
            imm_bits = imm & mask50
            inst |= (imm_bits & 0x3FF) << 14
            inst |= (imm_bits >> 10) << 34
        else:
            mask50 = (1 << 50) - 1
            imm_bits = imm & mask50
            inst |= imm_bits << 32

        inst |= (p << 87)
        if "1_cNOT" in ins_modi:
            inst |= (1 << 90)
        inst |= (1 << 91) #turn on UR
        inst |= (ur << 24)

        if "2_cINV" in ins_modi:
            if SM_VER == 120:
                inst |= 1 << 82
            else:
                inst |= 1 << 30

        if not ("0_DIV" in ins_modi) and not ("0_CONV" in ins_modi):
            print("BRA UR must contain DIV or CONV!")
            return -1
    else:
        imm = int(ins_vals[1])
        if SM_VER == 120:
            mask50 = (1 << 58) - 1
            imm_bits = imm & mask50
            inst |= (imm_bits & 0x3FF) << 14
            inst |= (imm_bits >> 10) << 34
        else:
            mask50 = (1 << 50) - 1
            imm_bits = imm & mask50
            inst |= imm_bits << 32
        inst |= (7 << 87)

    if "0_U" in ins_modi:
        inst |= (1 << 32)
    if "0_DIV" in ins_modi:
        inst |= (2 << 32)
    if "0_CONV" in ins_modi:
        inst |= (3 << 32)

    if "0_INC" in ins_modi:
        inst |= (1 << 85)
    if "0_DEC" in ins_modi:
        inst |= (2 << 85)

    return inst

#todo: not ready for blackwell
def BRX_R_II(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 3:
        return -1
    opcode = 2377  # 0x949
    pred = int(ins_vals[0])
    reg = int(ins_vals[1])
    imm = int(ins_vals[2])
    # 50-bit for imm
    mask50 = (1 << 50) - 1
    imm_bits = imm & mask50
    # opcode [0..11]
    inst = opcode
    # pred [12..15]
    inst |= (pred) << 12
    # [16..23] = 0
    # reg in [24..31]
    inst |= reg << 24
    # imm in [32..81]
    inst |= imm_bits << 32
    inst |= (7 << 87)
    return inst

def BRXU_UR_II(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 3:
        return -1
    opcode = 2392
    pred = int(ins_vals[0])
    ureg = int(ins_vals[1])
    imm = int(ins_vals[2])
    # opcode [0..11]
    inst = opcode
    # pred [12..15]
    inst |= (pred) << 12
    # [16..23] = 0

    # temp fix
    if (SM_VER == 120) and (ureg == 63):
        ureg = 255

    # ureg in [24..31]
    inst |= ureg << 24
    inst |= (23 << 87)

    if SM_VER == 120:
        mask50 = (1 << 58) - 1
        imm_bits = imm & mask50
        inst |= (imm_bits & 0x3FF) << 14
        inst |= (imm_bits >> 10) << 34
    else:
        mask50 = (1 << 50) - 1
        imm_bits = imm & mask50
        # imm in [32..81]
        inst |= imm_bits << 32

    if "0_U" in ins_modi:
        inst |= (1 << 32)
    if "0_DIV" in ins_modi:
        inst |= (2 << 32)
    if "0_CONV" in ins_modi:
        inst |= (3 << 32)

    return inst

def R2UR_UR_R(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 3:
        return -1
    opcode = 962
    pred = int(ins_vals[0])
    ureg = int(ins_vals[1])
    reg = int(ins_vals[2])
    # opcode [0..11]
    inst = opcode
    # pred [12..15]
    inst |= (pred) << 12
    # ureg in [16..23]
    inst |= ureg << 16
    # reg [24..31]
    inst |= reg << 24
    inst |= (7 << 81)
    return inst

def IADD3_R_P_P_R_R_R_P_P(ins_key, ins_vals, ins_modi):
    if (len(ins_vals) != 9) and not ((ins_key == "IADD3_R_P_R_II_R_P_P") and (len(ins_vals) == 8)):
        return -1
    opcode = 528
    if (ins_key == "IADD3_R_P_P_R_II_R_P_P"):
        opcode = 2064
    pred = int(ins_vals[0])
    rdst = int(ins_vals[1])
    pout0 = int(ins_vals[2])
    pout1 = int(ins_vals[3])
    rsrc0 = int(ins_vals[4])
    rsrc1 = unsigned(int(ins_vals[5]), 32)  # or imm
    rsrc2 = int(ins_vals[6])
    pin0 = int(ins_vals[7])
    pin1 = int(ins_vals[8])

    inst = opcode
    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (pout0) << 81
    inst |= (pout1) << 84
    inst |= (rsrc0) << 24
    inst |= (rsrc1) << 32
    inst |= (rsrc2) << 64
    inst |= (pin0) << 87
    inst |= (pin1) << 77
    inst |= (1 << 74)

    if "4_cINV" in ins_modi:
        inst |= (1 << 72)
    if "5_cINV" in ins_modi:
        inst |= (1 << 63)
    if "6_cINV" in ins_modi:
        inst |= (1 << 75)
    if "7_cNOT" in ins_modi:
        inst |= (1 << 90)
    if "8_cNOT" in ins_modi:
        inst |= (1 << 80)
    for md in ins_modi:
        if md.find("cNEG") != -1:  # not supported in IADD3.X
            return -1
    if "4_reuse" in ins_modi:
        inst |= (1 << 122)
    if "5_reuse" in ins_modi:
        inst |= (1 << 123)
    if "6_reuse" in ins_modi:
        inst |= (1 << 124)

    if obfuscate:
        if (ins_key == "IADD3_R_P_P_R_II_R_P_P"):
            inst |= (1 << 123)

    return inst

def IADD3_R_P_R_R_R_P_P(ins_key, ins_vals, ins_modi):
    if (len(ins_vals) != 8):
        return -1
    opcode = 528
    if (ins_key == "IADD3_R_P_R_II_R_P_P"):
        opcode = 2064
    pred = int(ins_vals[0])
    rdst = int(ins_vals[1])
    pout0 = int(ins_vals[2])
    pout1 = 7
    rsrc0 = int(ins_vals[3])
    rsrc1 = unsigned(int(ins_vals[4]), 32) #imm
    rsrc2 = int(ins_vals[5])
    pin0 = int(ins_vals[6])
    pin1 = int(ins_vals[7])

    inst = opcode
    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (pout0) << 81
    inst |= (pout1) << 84
    inst |= (rsrc0) << 24
    inst |= (rsrc1) << 32
    inst |= (rsrc2) << 64
    inst |= (pin0) << 87
    inst |= (pin1) << 77
    inst |= (1 << 74)

    if "3_cINV" in ins_modi:
        inst |= (1 << 72)
    if "4_cINV" in ins_modi:
        inst |= (1 << 63)
    if "5_cINV" in ins_modi:
        inst |= (1 << 75)
    if "6_cNOT" in ins_modi:
        inst |= (1 << 90)
    if "7_cNOT" in ins_modi:
        inst |= (1 << 80)
    for md in ins_modi:
        if md.find("cNEG") != -1:  # not supported in IADD3.X
            return -1
    if "3_reuse" in ins_modi:
        inst |= (1 << 122)
    if "4_reuse" in ins_modi:
        inst |= (1 << 123)
    if "5_reuse" in ins_modi:
        inst |= (1 << 124)

    return inst

def IMAD_R_P_R_R_R_P(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 7:
        return -1
    if not ("0_WIDE" in ins_modi):  # handle only wide version
        return -1
    opcode = 549
    pred = int(ins_vals[0])
    rdst = int(ins_vals[1])
    pout = int(ins_vals[2])
    rsrc0 = int(ins_vals[3])
    rsrc1 = int(ins_vals[4])
    rsrc2 = int(ins_vals[5])
    pin = int(ins_vals[6])
    inst = opcode
    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (pout) << 81
    inst |= (rsrc0) << 24
    inst |= (rsrc1) << 32
    inst |= (rsrc2) << 64
    inst |= (pin) << 87
    if "0_U32" in ins_modi:
        inst |= (1) << 74  # U32
    if "5_cINV" in ins_modi:
        inst |= (1 << 75)
    if "6_cNOT" in ins_modi:
        inst |= (1 << 90)
    for md in ins_modi:
        if md.find("cNEG") != -1:  # not supported in IMAD.X
            return -1
    if "3_reuse" in ins_modi:
        inst |= (1 << 122)
    if "4_reuse" in ins_modi:
        inst |= (1 << 123)
    if "5_reuse" in ins_modi:
        inst |= (1 << 124)

    return inst

def IMAD_R_P_R_II_R_P(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 7:
        return -1
    if not ("0_WIDE" in ins_modi):  # handle only wide version
        return -1
    opcode = 2085
    pred = int(ins_vals[0])
    rdst = int(ins_vals[1])
    pout = int(ins_vals[2])
    rsrc0 = int(ins_vals[3])
    rsrc1 = unsigned(int(ins_vals[4]), 32) #imm
    rsrc2 = int(ins_vals[5])
    pin = int(ins_vals[6])
    inst = opcode
    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (pout) << 81
    inst |= (rsrc0) << 24
    inst |= (rsrc1) << 32
    inst |= (rsrc2) << 64
    inst |= (pin) << 87
    if "0_U32" in ins_modi:
        inst |= (1) << 74  # U32
    if "5_cINV" in ins_modi:
        inst |= (1 << 75)
    if "6_cNOT" in ins_modi:
        inst |= (1 << 90)
    for md in ins_modi:
        if md.find("cNEG") != -1:  # not supported in IMAD.X
            return -1
    if "3_reuse" in ins_modi:
        inst |= (1 << 122)

    if obfuscate:
        inst |= (1 << 123)

    return inst

def IMAD_R_R_R_R_P(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 6:
        return -1
    if ("0_WIDE" in ins_modi):  # here we handle only non-wide version
        return -1
    opcode = 548
    pred = int(ins_vals[0])
    rdst = int(ins_vals[1])
    rsrc0 = int(ins_vals[2])
    rsrc1 = int(ins_vals[3])
    rsrc2 = int(ins_vals[4])
    pin = int(ins_vals[5])
    inst = opcode
    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (rsrc0) << 24
    inst |= (rsrc1) << 32
    inst |= (rsrc2) << 64
    inst |= (pin) << 87
    inst |= (7 << 81)

    u32 = 1
    if "0_U32" in ins_modi:
        u32 = 0
    inst |= (u32 << 73)  # U32
    if "0_X" in ins_modi:
        inst |= (1 << 74)
    if "4_cINV" in ins_modi:
        inst |= (1 << 75)
    if "5_cNOT" in ins_modi:
        inst |= (1 << 90)
    for md in ins_modi:
        if md.find("cNEG") != -1:  # not supported in IMAD.X
            return -1
    if "2_reuse" in ins_modi:
        inst |= (1 << 122)
    if "3_reuse" in ins_modi:
        inst |= (1 << 123)
    if "4_reuse" in ins_modi:
        inst |= (1 << 124)

    return inst

def STG_dARI_R_R_II_256(ins_key, ins_vals, ins_modi): #undocumented
    IsUR : bool = ins_key == "STG_ARURI_R_R_II"
    if len(ins_vals) != 7:
        return -1
    if not ("0_256" in ins_modi):
        return -1
    if IsUR and not ("1_R.U32" in ins_modi):
        return -1

    opcode = 2431
    pred = int(ins_vals[0])
    rsrc1 = int(ins_vals[4])
    rsrc2 = int(ins_vals[5])
    urcache = int(ins_vals[1])
    rsrc = int(ins_vals[2])
    ofs = int(ins_vals[3])
    unk = int(ins_vals[6]) #mask what registers must be loaded
    inst = opcode
    inst |= (pred) << 12
    inst |= (rsrc2) << 16
    inst |= (rsrc1) << 32
    inst |= (ofs//32) << 40 #19bits only but multiplied by 32
    if IsUR:
        inst |= (rsrc) << 64
        inst |= (urcache) << 24
    else:
        inst |= (rsrc) << 24
        inst |= (urcache) << 64

    if SM_VER == 120:
        inst |= (unk & 31) << 59  # 5bits
        unk = unk // 32
        inst |= (unk) << 88  # 3bits
    else:
        inst |= (unk & 31) << 59  # 5bits
        unk = unk // 32
        inst |= (unk) << 70  # 3bits

    if not IsUR:
        inst |= 3 << 75 # 3=[R.64], 0=[R.32+UR], 1=[R.64+UR], 2=unsupported

    inst |= 1 << 91 #just required

    if not IsUR:
        inst |= 1 << 101  # show "desc" (available only in for [R.64] mode)

    # ModifierGroup1: 0:none    #1:LTC64B    2:LTC128B    3:LTC256B
    if "0_LTC64B" in ins_modi:
        inst |= (1 << 73)  # 1:LTC64B  2:LTC128B    3:LTC256B
    if "0_LTC128B" in ins_modi:
        inst |= (2 << 73)
    if "0_LTC256B" in ins_modi:
        inst |= (3 << 73)

    # ModifierGroup4: 0:none   1: CONSTANT.PRIVATE   2:CONSTANT.CTA   3:CONSTANT.CTA.PRIVATE   4:CONSTANT
    # 5:STRONG.SM   6:STRONG.GPU.PRIVATE   7:STRONG.GPU   8:MMIO.GPU   9:CONSTANT.SM   10:STRONG.SYS
    # 11:CONSTANT.SM.PRIVATE   12:MMIO.SYS   13:CONSTANT.VC   14:CONSTANT.VC.PRIVATE   15:CONSTANT.GPU
    modi2 = 0
    if "0_CONSTANT_PRIVATE" in ins_modi:
        modi2 = 1
    if "0_CONSTANT_CTA" in ins_modi:
        modi2 = 2
    if "0_CONSTANT_CTA_PRIVATE" in ins_modi:
        modi2 = 3
    if "0_CONSTANT" in ins_modi:
        modi2 = 4
    if "0_STRONG_SM" in ins_modi:
        modi2 = 5
    if "0_STRONG_GPU_PRIVATE" in ins_modi:
        modi2 = 6
    if "0_STRONG_GPU" in ins_modi:  # skip L1
        modi2 = 7
    if "0_MMIO_GPU" in ins_modi:
        modi2 = 8
    if "0_CONSTANT_SM" in ins_modi:
        modi2 = 9
    if "0_STRONG_SYS" in ins_modi:
        modi2 = 10
    if "0_CONSTANT_SM_PRIVATE" in ins_modi:
        modi2 = 11
    if "0_MMIO_SYS" in ins_modi:
        modi2 = 12
    if "0_CONSTANT_VC" in ins_modi:
        modi2 = 13
    if "0_CONSTANT_VC_PRIVATE" in ins_modi:
        modi2 = 14
    if "0_CONSTANT_GPU" in ins_modi:
        modi2 = 15

    if "0_EFL2" in ins_modi:
        modi2 = modi2 | 0
    if "0_ENL2" in ins_modi:
        modi2 = modi2 | 16
    if "0_ELL2" in ins_modi:
        modi2 = modi2 | 32
    if "0_INVALID3" in ins_modi:
        modi2 = modi2 | 48

    inst |= (modi2 << 77)

    # ModifierGroup3: 0:EF   1:none   2:EL   3:LU   4:EU   5:NA   6:INVALID6   7:INVALID7
    modi3 = 1
    if "0_EF" in ins_modi:  # evict_first - streaming
        modi3 = 0
    if "0_EL" in ins_modi:  # evict_last - keep data in cache
        modi3 = 2
    if "0_LU" in ins_modi:  # evict_unchanged
        modi3 = 3
    if "0_EU" in ins_modi:  # evict_unchanged
        modi3 = 4
    if "0_NA" in ins_modi:  # no_allocate cache
        modi3 = 5
    inst |= (modi3 << 84)

    return inst

def LDG_R_R_dARI_II_256(ins_key, ins_vals, ins_modi):
    IsUR : bool = ins_key == "LDG_R_R_ARURI_II"
    if len(ins_vals) != 7:
        return -1
    if not ("0_256" in ins_modi):
        return -1
    if IsUR and not ("3_R.U32" in ins_modi):
        return -1

    opcode = 2430
    pred = int(ins_vals[0])
    rdst1 = int(ins_vals[1])
    rdst2 = int(ins_vals[2])
    urcache = int(ins_vals[3])
    rsrc = int(ins_vals[4])
    ofs = int(ins_vals[5])
    unk = int(ins_vals[6]) #mask what registers must be loaded
    inst = opcode
    inst |= (pred) << 12
    inst |= (rdst1) << 64
    inst |= (rdst2) << 16
    if IsUR:
        inst |= (rsrc) << 32
        inst |= (urcache) << 24
    else:
        inst |= (rsrc) << 24
        inst |= (urcache) << 32

    inst |= (ofs//32) << 40 #19bits only but multiplied by 32

    if SM_VER == 120:
        inst |= (unk & 3) << 57
        unk = unk //4
        inst |= (unk & 31) << 59 #5bits
        inst |= (unk >> 5) << 72 #3bits
    else:
        inst |= (unk & 3) << 38
        unk = unk //4
        inst |= (unk & 31) << 59 #5bits
        inst |= (unk >> 5) << 72 #3bits

    if not IsUR:
        inst |= 3 << 75 # 3=[R.64], 0=[R.32+UR], 1=[R.64+UR], 2=unsupported

    inst |= 1 << 91 #just required
    if not IsUR:
        inst |= 1 << 101  # show "desc" (available only in for [R.64] mode)

    # ModifierGroup1: 0:none    #1:LTC64B    2:LTC128B    3:LTC256B
    if "0_LTC64B" in ins_modi:
        inst |= (1 << 73)  # 1:LTC64B  2:LTC128B    3:LTC256B
    if "0_LTC128B" in ins_modi:
        inst |= (2 << 73)
    if "0_LTC256B" in ins_modi:
        inst |= (3 << 73)

    # ModifierGroup4: 0:none   1: CONSTANT.PRIVATE   2:CONSTANT.CTA   3:CONSTANT.CTA.PRIVATE   4:CONSTANT
    # 5:STRONG.SM   6:STRONG.GPU.PRIVATE   7:STRONG.GPU   8:MMIO.GPU   9:CONSTANT.SM   10:STRONG.SYS
    # 11:CONSTANT.SM.PRIVATE   12:MMIO.SYS   13:CONSTANT.VC   14:CONSTANT.VC.PRIVATE   15:CONSTANT.GPU
    modi2 = 0
    if "0_CONSTANT_PRIVATE" in ins_modi:
        modi2 = 1
    if "0_CONSTANT_CTA" in ins_modi:
        modi2 = 2
    if "0_CONSTANT_CTA_PRIVATE" in ins_modi:
        modi2 = 3
    if "0_CONSTANT" in ins_modi:
        modi2 = 4
    if "0_STRONG_SM" in ins_modi:
        modi2 = 5
    if "0_STRONG_GPU_PRIVATE" in ins_modi:
        modi2 = 6
    if "0_STRONG_GPU" in ins_modi:  # skip L1
        modi2 = 7
    if "0_MMIO_GPU" in ins_modi:
        modi2 = 8
    if "0_CONSTANT_SM" in ins_modi:
        modi2 = 9
    if "0_STRONG_SYS" in ins_modi:
        modi2 = 10
    if "0_CONSTANT_SM_PRIVATE" in ins_modi:
        modi2 = 11
    if "0_MMIO_SYS" in ins_modi:
        modi2 = 12
    if "0_CONSTANT_VC" in ins_modi:
        modi2 = 13
    if "0_CONSTANT_VC_PRIVATE" in ins_modi:
        modi2 = 14
    if "0_CONSTANT_GPU" in ins_modi:
        modi2 = 15

    if "0_EFL2" in ins_modi:
        modi2 = modi2 | 0
    if "0_ENL2" in ins_modi:
        modi2 = modi2 | 16
    if "0_ELL2" in ins_modi:
        modi2 = modi2 | 32
    if "0_INVALID3" in ins_modi:
        modi2 = modi2 | 48

    inst |= (modi2 << 77)

    # ModifierGroup3: 0:EF   1:none   2:EL   3:LU   4:EU   5:NA   6:INVALID6   7:INVALID7
    modi3 = 1
    if "0_EF" in ins_modi:  # evict_first - streaming
        modi3 = 0
    if "0_EL" in ins_modi:  # evict_last - keep data in cache
        modi3 = 2
    if "0_LU" in ins_modi:  # evict_unchanged
        modi3 = 3
    if "0_EU" in ins_modi:  # evict_unchanged
        modi3 = 4
    if "0_NA" in ins_modi:  # no_allocate cache
        modi3 = 5
    inst |= (modi3 << 84)
    return inst


def LDG_R_dARI(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 5:
        return -1
    opcode = 2433
    pred = int(ins_vals[0])
    rdst = int(ins_vals[1])
    urcache = int(ins_vals[2])
    rsrc = int(ins_vals[3])
    ofs = int(ins_vals[4])
    inst = opcode
    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (rsrc) << 24
    inst |= (urcache) << 32
    inst |= (ofs) << 40

    inst |= (1 << 76)
    inst |= (7 << 81)
    inst |= (3 << 90)
    inst |= (1 << 101) #show "desc UR" in nvdisasm

    # ModifierGroup1: 0:none    #1:LTC64B    2:LTC128B    3:LTC256B
    if "0_LTC64B" in ins_modi:
        inst |= (1 << 68)  # 1:LTC64B  2:LTC128B    3:LTC256B
    if "0_LTC128B" in ins_modi:
        inst |= (2 << 68)
    if "0_LTC256B" in ins_modi:
        inst |= (3 << 68)

    # ModifierGroup2: 0:???0  1:E, means 64bit addr, so use it everywhere
    if "0_E" in ins_modi:
        inst |= (1 << 72)

    # ModifierGroup3: 0:U8   1:S8   2:U16   3:S16   4: none   5:64   6:128   7:invalid
    modi3 = 4
    if "0_U8" in ins_modi:
        modi3 = 0
    if "0_S8" in ins_modi:
        modi3 = 1
    if "0_U16" in ins_modi:
        modi3 = 2
    if "0_S16" in ins_modi:
        modi3 = 3
    if "0_64" in ins_modi:
        modi3 = 5
    if "0_128" in ins_modi:
        modi3 = 6
    inst |= (modi3 << 73)

    # ModifierGroup4: 0:none   1: CONSTANT.PRIVATE   2:CONSTANT.CTA   3:CONSTANT.CTA.PRIVATE   4:CONSTANT
    # 5:STRONG.SM   6:STRONG.GPU.PRIVATE   7:STRONG.GPU   8:MMIO.GPU   9:CONSTANT.SM   10:STRONG.SYS
    # 11:CONSTANT.SM.PRIVATE   12:MMIO.SYS   13:CONSTANT.VC   14:CONSTANT.VC.PRIVATE   15:CONSTANT.GPU
    modi4 = 0
    if "0_CONSTANT_PRIVATE" in ins_modi:
        modi4 = 1
    if "0_CONSTANT_CTA" in ins_modi:
        modi4 = 2
    if "0_CONSTANT_CTA_PRIVATE" in ins_modi:
        modi4 = 3
    if "0_CONSTANT" in ins_modi:
        modi4 = 4
    if "0_STRONG_SM" in ins_modi:
        modi4 = 5
    if "0_STRONG_GPU_PRIVATE" in ins_modi: 
        modi4 = 6
    if "0_STRONG_GPU" in ins_modi:  # skip L1
        modi4 = 7
    if "0_MMIO_GPU" in ins_modi:
        modi4 = 8
    if "0_CONSTANT_SM" in ins_modi:
        modi4 = 9
    if "0_STRONG_SYS" in ins_modi:
        modi4 = 10
    if "0_CONSTANT_SM_PRIVATE" in ins_modi:
        modi4 = 11
    if "0_MMIO_SYS" in ins_modi:
        modi4 = 12
    if "0_CONSTANT_VC" in ins_modi:
        modi4 = 13
    if "0_CONSTANT_VC_PRIVATE" in ins_modi:
        modi4 = 14
    if "0_CONSTANT_GPU" in ins_modi:
        modi4 = 15
    inst |= (modi4 << 77)

    # ModifierGroup5: 0:EF   1:none   2:EL   3:LU   4:EU   5:NA   6:INVALID6   7:INVALID7
    modi5 = 1
    if "0_EF" in ins_modi:  # evict_first - streaming
        modi5 = 0
    if "0_EL" in ins_modi:  # evict_last - keep data in cache
        modi5 = 2
    if "0_LU" in ins_modi:  # evict_unchanged
        modi5 = 3
    if "0_EU" in ins_modi:  # evict_unchanged
        modi5 = 4
    if "0_NA" in ins_modi:  # no_allocate cache
        modi5 = 5
    inst |= (modi5 << 84)

    if "0_PM1" in ins_modi:
        inst |= (1 << 102)  # ?PM1,2,3 - two bits
    if "0_PM2" in ins_modi:
        inst |= (2 << 102)
    if "0_PM3" in ins_modi:
        inst |= (3 << 102)
    # inst |= (1 << 104) nothing
    return inst

def LDG_R_ARURI_P(ins_key, ins_vals, ins_modi):
    if (len(ins_vals) != 6) and (len(ins_vals) != 5):
        return -1
    if not ("2_R.U32" in ins_modi): #we support only most convenient option with URbase
        return -1
    opcode = 2433
    if len(ins_vals) == 6:
        pred = int(ins_vals[0])
        rdst = int(ins_vals[1])
        radr = int(ins_vals[2])
        uradr = int(ins_vals[3])
        ofs = int(ins_vals[4])
        psrc = int(ins_vals[5])
    else:
        pred = int(ins_vals[0])
        rdst = int(ins_vals[1])
        radr = int(ins_vals[2])
        uradr = int(ins_vals[3])
        ofs = int(ins_vals[4])
        psrc = 7

    inst = opcode
    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (radr) << 24
    inst |= (uradr) << 32
    inst |= (ofs) << 40
    inst |= (psrc ^ 0b111) << 64
    if "3_cNOT" in ins_modi: #we support only most convenient option with URbase
        inst |= (1 << 67)

    inst |= (7 << 81)
    inst |= (3 << 91)

    # ModifierGroup1: 0:none    #1:LTC64B    2:LTC128B    3:LTC256B
    if "0_LTC64B" in ins_modi:
        inst |= (1 << 68)  # 1:LTC64B  2:LTC128B    3:LTC256B
    if "0_LTC128B" in ins_modi:
        inst |= (2 << 68)
    if "0_LTC256B" in ins_modi:
        inst |= (3 << 68)

    # ModifierGroup2: 0:???0  1:E, means 64bit addr, so use it everywhere
    if "0_E" in ins_modi:
        inst |= (1 << 72)

    # ModifierGroup3: 0:U8   1:S8   2:U16   3:S16   4: none   5:64   6:128   7:invalid
    modi3 = 4
    if "0_U8" in ins_modi:
        modi3 = 0
    if "0_S8" in ins_modi:
        modi3 = 1
    if "0_U16" in ins_modi:
        modi3 = 2
    if "0_S16" in ins_modi:
        modi3 = 3
    if "0_64" in ins_modi:
        modi3 = 5
    if "0_128" in ins_modi:
        modi3 = 6
    inst |= (modi3 << 73)

    # ModifierGroup4: 0:none   1: CONSTANT.PRIVATE   2:CONSTANT.CTA   3:CONSTANT.CTA.PRIVATE   4:CONSTANT
    # 5:STRONG.SM   6:STRONG.GPU.PRIVATE   7:STRONG.GPU   8:MMIO.GPU   9:CONSTANT.SM   10:STRONG.SYS
    # 11:CONSTANT.SM.PRIVATE   12:MMIO.SYS   13:CONSTANT.VC   14:CONSTANT.VC.PRIVATE   15:CONSTANT.GPU
    modi4 = 0
    if "0_CONSTANT_PRIVATE" in ins_modi:
        modi4 = 1
    if "0_CONSTANT_CTA" in ins_modi:
        modi4 = 2
    if "0_CONSTANT_CTA_PRIVATE" in ins_modi:
        modi4 = 3
    if "0_CONSTANT" in ins_modi:
        modi4 = 4
    if "0_STRONG_SM" in ins_modi:
        modi4 = 5
    if "0_STRONG_GPU_PRIVATE" in ins_modi:
        modi4 = 6
    if "0_STRONG_GPU" in ins_modi:  # skip L1
        modi4 = 7
    if "0_MMIO_GPU" in ins_modi:
        modi4 = 8
    if "0_CONSTANT_SM" in ins_modi:
        modi4 = 9
    if "0_STRONG_SYS" in ins_modi:
        modi4 = 10
    if "0_CONSTANT_SM_PRIVATE" in ins_modi:
        modi4 = 11
    if "0_MMIO_SYS" in ins_modi:
        modi4 = 12
    if "0_CONSTANT_VC" in ins_modi:
        modi4 = 13
    if "0_CONSTANT_VC_PRIVATE" in ins_modi:
        modi4 = 14
    if "0_CONSTANT_GPU" in ins_modi:
        modi4 = 15
    inst |= (modi4 << 77)

    # ModifierGroup5: 0:EF   1:none   2:EL   3:LU   4:EU   5:NA   6:INVALID6   7:INVALID7
    modi5 = 1
    if "0_EF" in ins_modi:  # evict_first - streaming
        modi5 = 0
    if "0_EL" in ins_modi:  # evict_last - keep data in cache
        modi5 = 2
    if "0_LU" in ins_modi:  # evict_unchanged
        modi5 = 3
    if "0_EU" in ins_modi:  # evict_unchanged
        modi5 = 4
    if "0_NA" in ins_modi:  # no_allocate cache
        modi5 = 5
    inst |= (modi5 << 84)

    if "0_PM1" in ins_modi:
        inst |= (1 << 102)  # ?PM1,2,3 - two bits
    if "0_PM2" in ins_modi:
        inst |= (2 << 102)
    if "0_PM3" in ins_modi:
        inst |= (3 << 102)
    # inst |= (1 << 104) nothing
    return inst

def STG_dARI_R(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 5:
        return -1
    opcode = 2438
    pred = int(ins_vals[0])
    urcache = int(ins_vals[1])
    rpnt = int(ins_vals[2])
    ofs = int(ins_vals[3])
    rsrc = int(ins_vals[4])
    inst = opcode
    inst |= (pred) << 12
    inst |= (rpnt) << 24
    inst |= (rsrc) << 32
    inst |= (ofs) << 40
    inst |= (urcache) << 64
    inst |= (1 << 76)
    inst |= (3 << 90)
    inst |= (1 << 101) #show "desc UR" in nvdisasm

    # ModifierGroup2: 0:???0  1:E, means 64bit addr, so use it everywhere
    if "0_E" in ins_modi:
        inst |= (1 << 72)

    # ModifierGroup3: 0:U8   1:S8   2:U16   3:S16   4: none   5:64   6:128   7:invalid
    modi2 = 4
    if "0_U8" in ins_modi:
        modi2 = 0
    if "0_S8" in ins_modi:
        modi2 = 1
    if "0_U16" in ins_modi:
        modi2 = 2
    if "0_S16" in ins_modi:
        modi2 = 3
    if "0_64" in ins_modi:
        modi2 = 5
    if "0_128" in ins_modi:
        modi2 = 6
    inst |= (modi2 << 73)

    # ModifierGroup3: 0:none   1: CONSTANT.PRIVATE   2:CONSTANT.CTA   3:CONSTANT.CTA.PRIVATE   4:STRONG.SM.PRIVATE.
    # 5:STRONG.SM   6:STRONG.GPU.PRIVATE   7:STRONG.GPU   8:MMIO.GPU   9:CONSTANT.SM   10:STRONG.SYS
    # 11:CONSTANT.SM.PRIVATE   12:MMIO.SYS   13:CONSTANT.VC   14:CONSTANT.VC.PRIVATE   15:CONSTANT.GPU
    modi3 = 0
    if "0_CONSTANT_PRIVATE" in ins_modi:
        modi3 = 1
    if "0_CONSTANT_CTA" in ins_modi:
        modi3 = 2
    if "0_CONSTANT_CTA_PRIVATE" in ins_modi:
        modi3 = 3
    if "0_STRONG_SM_PRIVATE" in ins_modi:
        modi3 = 4
    if "0_STRONG_SM" in ins_modi:
        modi3 = 5
    if "0_STRONG_GPU_PRIVATE" in ins_modi:
        modi3 = 6
    if "0_STRONG_GPU" in ins_modi:  # skip L1
        modi3 = 7
    if "0_MMIO_GPU" in ins_modi:
        modi3 = 8
    if "0_CONSTANT_SM" in ins_modi:
        modi3 = 9
    if "0_STRONG_SYS" in ins_modi:
        modi3 = 10
    if "0_CONSTANT_SM_PRIVATE" in ins_modi:
        modi3 = 11
    if "0_MMIO_SYS" in ins_modi:
        modi3 = 12
    if "0_CONSTANT_VC" in ins_modi:
        modi3 = 13
    if "0_CONSTANT_VC_PRIVATE" in ins_modi:
        modi3 = 14
    if "0_CONSTANT_GPU" in ins_modi:
        modi3 = 15
    inst |= (modi3 << 77)

    # ModifierGroup4: 0:EF   1:none   2:EL   3:LU   4:EU   5:NA   6:INVALID6   7:INVALID7
    modi4 = 1
    if "0_EF" in ins_modi:  # evict_first - streaming
        modi4 = 0
    if "0_EL" in ins_modi:  # evict_last - keep data in cache
        modi4 = 2
    if "0_LU" in ins_modi:  # evict_unchanged
        modi4 = 3
    if "0_EU" in ins_modi:  # evict_unchanged
        modi4 = 4
    if "0_NA" in ins_modi:  # no_allocate cache
        modi4 = 5
    inst |= (modi4 << 84)
    return inst

def STG_ARURI_R(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 5:
        return -1
    opcode = 2438
    pred = int(ins_vals[0])
    radr = int(ins_vals[1])
    uradr = int(ins_vals[2])
    ofs = int(ins_vals[3])
    rsrc = int(ins_vals[4])
    inst = opcode
    inst |= (pred) << 12
    inst |= (radr) << 24
    inst |= (rsrc) << 32
    inst |= (ofs) << 40
    inst |= (uradr) << 64
    inst |= (1 << 91)

    # ModifierGroup2: 0:???0  1:E, means 64bit addr, so use it everywhere
    if "0_E" in ins_modi:
        inst |= (1 << 72)

    # ModifierGroup3: 0:U8   1:S8   2:U16   3:S16   4: none   5:64   6:128   7:invalid
    modi2 = 4
    if "0_U8" in ins_modi:
        modi2 = 0
    if "0_S8" in ins_modi:
        modi2 = 1
    if "0_U16" in ins_modi:
        modi2 = 2
    if "0_S16" in ins_modi:
        modi2 = 3
    if "0_64" in ins_modi:
        modi2 = 5
    if "0_128" in ins_modi:
        modi2 = 6
    inst |= (modi2 << 73)

    # ModifierGroup3: 0:none   1: CONSTANT.PRIVATE   2:CONSTANT.CTA   3:CONSTANT.CTA.PRIVATE   4:STRONG.SM.PRIVATE.
    # 5:STRONG.SM   6:STRONG.GPU.PRIVATE   7:STRONG.GPU   8:MMIO.GPU   9:CONSTANT.SM   10:STRONG.SYS
    # 11:CONSTANT.SM.PRIVATE   12:MMIO.SYS   13:CONSTANT.VC   14:CONSTANT.VC.PRIVATE   15:CONSTANT.GPU
    modi3 = 0
    if "0_CONSTANT_PRIVATE" in ins_modi:
        modi3 = 1
    if "0_CONSTANT_CTA" in ins_modi:
        modi3 = 2
    if "0_CONSTANT_CTA_PRIVATE" in ins_modi:
        modi3 = 3
    if "0_STRONG_SM_PRIVATE" in ins_modi:
        modi3 = 4
    if "0_STRONG_SM" in ins_modi:
        modi3 = 5
    if "0_STRONG_GPU_PRIVATE" in ins_modi:
        modi3 = 6
    if "0_STRONG_GPU" in ins_modi:  # skip L1
        modi3 = 7
    if "0_MMIO_GPU" in ins_modi:
        modi3 = 8
    if "0_CONSTANT_SM" in ins_modi:
        modi3 = 9
    if "0_STRONG_SYS" in ins_modi:
        modi3 = 10
    if "0_CONSTANT_SM_PRIVATE" in ins_modi:
        modi3 = 11
    if "0_MMIO_SYS" in ins_modi:
        modi3 = 12
    if "0_CONSTANT_VC" in ins_modi:
        modi3 = 13
    if "0_CONSTANT_VC_PRIVATE" in ins_modi:
        modi3 = 14
    if "0_CONSTANT_GPU" in ins_modi:
        modi3 = 15
    inst |= (modi3 << 77)

    # ModifierGroup4: 0:EF   1:none   2:EL   3:LU   4:EU   5:NA   6:INVALID6   7:INVALID7
    modi4 = 1
    if "0_EF" in ins_modi:  # evict_first - streaming
        modi4 = 0
    if "0_EL" in ins_modi:  # evict_last - keep data in cache
        modi4 = 2
    if "0_LU" in ins_modi:  # evict_unchanged
        modi4 = 3
    if "0_EU" in ins_modi:  # evict_unchanged
        modi4 = 4
    if "0_NA" in ins_modi:  # no_allocate cache
        modi4 = 5
    inst |= (modi4 << 84)
    return inst

def LDGSTS_ARI_ARURI(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 6:
        return -1
    if not ("2_R.U32" in ins_modi): #we support only most convenient option with URbase
        return -1
    opcode = 4014
    pred = int(ins_vals[0])
    rdst = int(ins_vals[1])
    dst_ofs = int(ins_vals[2])
    rsrc = int(ins_vals[3])
    ursrc = int(ins_vals[4])
    src_ofs = int(ins_vals[5])
    inst = opcode
    inst |= (pred) << 12

    inst |= (rdst) << 16
    inst |= (rsrc) << 24
    inst |= (src_ofs) << 32
    inst |= (dst_ofs) << 44
    inst |= (ursrc) << 64

    inst |= (7 << 87)
    inst |= (1 << 91)

    if not ("0_BYPASS" in ins_modi):
        inst |= (1 << 81) #0: bypass,  1: none
    if "0_ZFILL" in ins_modi:
        inst |= (1 << 82) #0: none,  1: ZFILL

    # ModifierGroup1: 0:none    #1:LTC64B    2:LTC128B    3:LTC256B
    if "0_LTC64B" in ins_modi:
        inst |= (1 << 71)  # 1:LTC64B  2:LTC128B    3:LTC256B
    if "0_LTC128B" in ins_modi:
        inst |= (2 << 71)
    if "0_LTC256B" in ins_modi:
        inst |= (3 << 71)
    # ModifierGroup2: 4: none   5:64   6:128   7:invalid
    modi2 = 4
    if "0_64" in ins_modi:
        modi2 = 5
    if "0_128" in ins_modi:
        modi2 = 6
    inst |= (modi2 << 73)

    # ModifierGroup3
    modi3 = 0
    if "0_CONSTANT_PRIVATE" in ins_modi:
        modi3 = 1
    if "0_CONSTANT_CTA" in ins_modi:
        modi3 = 2
    if "0_CONSTANT_CTA_PRIVATE" in ins_modi:
        modi3 = 3
    if "0_CONSTANT" in ins_modi:
        modi3 = 4
    if "0_MMIO_CTA" in ins_modi:
        modi3 = 5
    if "0_GPU_PRIVATE" in ins_modi:
        modi3 = 6
    if "0_MMIO_CTA_PRIVATE" in ins_modi:
        modi3 = 7
    if "0_MMIO_SM" in ins_modi:
        modi3 = 8
    if "0_CONSTANT_SM" in ins_modi:
        modi3 = 9
    if "0_MMIO_VC" in ins_modi:
        modi3 = 10
    if "0_CONSTANT_SM_PRIVATE" in ins_modi:
        modi3 = 11
    if "0_MMIO_GPU" in ins_modi:
        modi3 = 12
    if "0_CONSTANT_VC" in ins_modi:
        modi3 = 13
    if "0_CONSTANT_VC_PRIVATE" in ins_modi:
        modi3 = 14
    if "0_CONSTANT_GPU" in ins_modi:
        modi3 = 15
    inst |= (modi3 << 77)

    # ModifierGroup4: 0:EF   1:none   2:EL   3:LU   4:EU   5:NA   6:INVALID6   7:INVALID7
    modi4 = 1
    if "0_EF" in ins_modi:  # evict_first - streaming
        modi4 = 0
    if "0_EL" in ins_modi:  # evict_last - keep data in cache
        modi4 = 2
    if "0_LU" in ins_modi:  # evict_unchanged
        modi4 = 3
    if "0_EU" in ins_modi:  # evict_unchanged
        modi4 = 4
    if "0_NA" in ins_modi:  # no_allocate cache
        modi4 = 5
    inst |= (modi4 << 84)
    return inst

def ATOMG_P_R_ARURI_R(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 7:
        return -1
    if not ("3_R.U32" in ins_modi): #we support only most convenient option with URbase
        return -1
    opcode = 2472
    pred = int(ins_vals[0])
    pdst = int(ins_vals[1])
    rdst = int(ins_vals[2])
    radr = int(ins_vals[3])
    uradr = int(ins_vals[4])
    src_ofs = int(ins_vals[5])
    rsrc = int(ins_vals[6])
    inst = opcode
    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (radr) << 24
    inst |= (rsrc) << 32
    inst |= (src_ofs) << 40
    inst |= (uradr) << 64
    inst |= (pdst) << 81
    inst |= (1 << 72) # ".E"
    inst |= (1 << 91)

    # ModifierGroup1
    modi1 = 0
    if "0_S32" in ins_modi:
        modi1 = 1
    if "0_64" in ins_modi:
        modi1 = 2
    if "0_F32_FTZ_RN" in ins_modi:
        modi1 = 3
    if "0_F16x2_RN" in ins_modi:
        modi1 = 4
    if "0_S64" in ins_modi:
        modi1 = 5
    if "0_F64_RN" in ins_modi:
        modi1 = 6
    inst |= (modi1 << 73)

    # ModifierGroup2
    modi2 = 0
    if "0_CONSTANT_PRIVATE" in ins_modi:
        modi2 = 1
    if "0_CONSTANT_CTA" in ins_modi:
        modi2 = 2
    if "0_CONSTANT_CTA_PRIVATE" in ins_modi:
        modi2 = 3
    if "0_STRONG_SM_PRIVATE" in ins_modi:
        modi2 = 4
    if "0_STRONG_SM" in ins_modi:
        modi2 = 5
    if "0_STRONG_GPU_PRIVATE" in ins_modi:
        modi2 = 6
    if "0_STRONG_GPU" in ins_modi: #skip L1
        modi2 = 7
    if "0_MMIO_GPU" in ins_modi:
        modi2 = 8
    if "0_CONSTANT_SM" in ins_modi:
        modi2 = 9
    if "0_STRONG_SYS" in ins_modi:
        modi2 = 10
    if "0_CONSTANT_SM_PRIVATE" in ins_modi:
        modi2 = 11
    if "0_MMIO_SYS" in ins_modi:
        modi2 = 12
    if "0_CONSTANT_VC" in ins_modi:
        modi2 = 13
    if "0_CONSTANT_VC_PRIVATE" in ins_modi:
        modi2 = 14
    if "0_CONSTANT_GPU" in ins_modi:
        modi2 = 15
    inst |= (modi2 << 77)

    # ModifierGroup3: 0:EF   1:none   2:EL   3:LU   4:EU   5:NA   6:INVALID6   7:INVALID7
    modi3 = 1
    if "0_EF" in ins_modi:  # evict_first - streaming
        modi3 = 0
    if "0_EL" in ins_modi:  # evict_last - keep data in cache
        modi3 = 2
    if "0_LU" in ins_modi:  # evict_unchanged
        modi3 = 3
    if "0_EU" in ins_modi:  # evict_unchanged
        modi3 = 4
    if "0_NA" in ins_modi:  # no_allocate cache
        modi3 = 5
    inst |= (modi3 << 84)

    # ModifierGroup4
    modi4 = 1
    if "0_ADD" in ins_modi:
        modi4 = 0
    if "0_MIN" in ins_modi:
        modi4 = 1
    if "0_MAX" in ins_modi:
        modi4 = 2
    if "0_INC" in ins_modi:
        modi4 = 3
    if "0_DEC" in ins_modi:
        modi4 = 4
    if "0_AND" in ins_modi:
        modi4 = 5
    if "0_OR" in ins_modi:
        modi4 = 6
    if "0_XOR" in ins_modi:
        modi4 = 7
    if "0_EXCH" in ins_modi:
        modi4 = 8
    if "0_SAFEADD" in ins_modi:
        modi4 = 9
    inst |= (modi4 << 87)
    return inst

def RED_ARURI_R(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 5:
        return -1
    if not ("1_R.U32" in ins_modi): #we support only most convenient option with URbase
        return -1
    opcode = 2446
    pred = int(ins_vals[0])
    padr = int(ins_vals[1])
    uradr = int(ins_vals[2])
    src_ofs = int(ins_vals[3])
    rsrc = int(ins_vals[4])
    inst = opcode
    inst |= (pred) << 12
    inst |= (padr) << 24
    inst |= (rsrc) << 32
    inst |= (uradr) << 64
    inst |= (src_ofs) << 40


    inst |= (1 << 72) # ".E"
    inst |= (1 << 91)

    # ModifierGroup1
    modi1 = 0
    if "0_S32" in ins_modi:
        modi1 = 1
    if "0_64" in ins_modi:
        modi1 = 2
    if "0_F32_FTZ_RN" in ins_modi:
        modi1 = 3
    if "0_F16x2_RN" in ins_modi:
        modi1 = 4
    if "0_S64" in ins_modi:
        modi1 = 5
    if "0_F64_RN" in ins_modi:
        modi1 = 6
    inst |= (modi1 << 73)

    # ModifierGroup2
    modi2 = 0
    if "0_CONSTANT_PRIVATE" in ins_modi:
        modi2 = 1
    if "0_CONSTANT_CTA" in ins_modi:
        modi2 = 2
    if "0_CONSTANT_CTA_PRIVATE" in ins_modi:
        modi2 = 3
    if "0_STRONG_SM_PRIVATE" in ins_modi:
        modi2 = 4
    if "0_STRONG_SM" in ins_modi:
        modi2 = 5
    if "0_STRONG_GPU_PRIVATE" in ins_modi:
        modi2 = 6
    if "0_STRONG_GPU" in ins_modi: #skip L1
        modi2 = 7
    if "0_MMIO_GPU" in ins_modi:
        modi2 = 8
    if "0_CONSTANT_SM" in ins_modi:
        modi2 = 9
    if "0_STRONG_SYS" in ins_modi:
        modi2 = 10
    if "0_CONSTANT_SM_PRIVATE" in ins_modi:
        modi2 = 11
    if "0_MMIO_SYS" in ins_modi:
        modi2 = 12
    if "0_CONSTANT_VC" in ins_modi:
        modi2 = 13
    if "0_CONSTANT_VC_PRIVATE" in ins_modi:
        modi2 = 14
    if "0_CONSTANT_GPU" in ins_modi:
        modi2 = 15
    inst |= (modi2 << 77)

    # ModifierGroup3: 0:EF   1:none   2:EL   3:LU   4:EU   5:NA   6:INVALID6   7:INVALID7
    modi3 = 1
    if "0_EF" in ins_modi:  # evict_first - streaming
        modi3 = 0
    if "0_EL" in ins_modi:  # evict_last - keep data in cache
        modi3 = 2
    if "0_LU" in ins_modi:  # evict_unchanged
        modi3 = 3
    if "0_EU" in ins_modi:  # evict_unchanged
        modi3 = 4
    if "0_NA" in ins_modi:  # no_allocate cache
        modi3 = 5
    inst |= (modi3 << 84)

    # ModifierGroup4
    modi4 = 1
    if "0_ADD" in ins_modi:
        modi4 = 0
    if "0_MIN" in ins_modi:
        modi4 = 1
    if "0_MAX" in ins_modi:
        modi4 = 2
    if "0_INC" in ins_modi:
        modi4 = 3
    if "0_DEC" in ins_modi:
        modi4 = 4
    if "0_AND" in ins_modi:
        modi4 = 5
    if "0_OR" in ins_modi:
        modi4 = 6
    if "0_XOR" in ins_modi:
        modi4 = 7
    inst |= (modi4 << 87)
    return inst

def LEA_R_P_R_R_II_P(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 7:
        return -1
    opcode = 529
    pred = int(ins_vals[0])
    rdst = int(ins_vals[1])
    pdst = int(ins_vals[2])
    rscr1 = int(ins_vals[3])
    rsrc2 = int(ins_vals[4])
    imm = int(ins_vals[5]) #5bits
    psrc = int(ins_vals[6])
    inst = opcode
    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (rscr1) << 24
    inst |= (rsrc2) << 32

    inst |= (imm) << 75
    inst |= (pdst) << 81
    inst |= (psrc) << 87

    if "0_SX32" in ins_modi:
        inst |= 1 << 73 #SX32
    inst |= 1 << 74 #enable psrc
    if "0_HI" in ins_modi:
        inst |= 1 << 80 #HI
    if "3_cINV" in ins_modi:
        inst |= 1 << 72
    if "4_cINV" in ins_modi:
        inst |= 1 << 63
    if "6_cNOT" in ins_modi:
        inst |= 1 << 90

    if "3_reuse" in ins_modi:
        inst |= (1 << 122)
    if "4_reuse" in ins_modi:
        inst |= (1 << 123)

    return inst

def CALL_II(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 2:
        return -1
    opcode = -1
    if "0_ABS" in ins_modi:
        opcode = 2371
    if "0_REL" in ins_modi:
        opcode = 2372
    if (opcode < 0):
        return -1
    pred = int(ins_vals[0])
    imm = int(ins_vals[1])
    # 50-bit for imm
    mask50 = (1 << 50) - 1
    imm_bits = imm & mask50
    inst = opcode
    inst |= (pred) << 12
    inst |= (imm_bits) << 32
    if "0_NOINC" in ins_modi:
        inst |= 1 << 86
    inst |= 7 << 87
    return inst

def LDC_R_cAI(ins_key, ins_vals, ins_modi):
    if (len(ins_vals) != 4) and (len(ins_vals) != 5):
        return -1
    opcode = 2946
    rsrc = 255
    pred = int(ins_vals[0])
    rdst = int(ins_vals[1])
    ad1 = int(ins_vals[2])
    if len(ins_vals) == 4:
        ad2 = int(ins_vals[3])
    else:
        rsrc = int(ins_vals[3])
        ad2 = int(ins_vals[4])


    inst = opcode

    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (ad1) << 54
    inst |= (ad2) << 38

    inst |= rsrc << 24 # [ad1][Rsrc + ad2]

    modi1 = 4
    if "0_U8" in ins_modi:
        modi1 = 0
    if "0_S8" in ins_modi:
        modi1 = 1
    if "0_U16" in ins_modi:
        modi1 = 2
    if "0_S16" in ins_modi:
        modi1 = 3
    if "0_64" in ins_modi:
        modi1 = 5
    inst |= (modi1) << 73

    modi2 = 0
    if "0_IL" in ins_modi:
        modi2 = 1
    if "0_IS" in ins_modi:
        modi2 = 2
    if "0_ISL" in ins_modi:
        modi2 = 3
    inst |= (modi2) << 78

    return inst

def LOP3_P_R_R_R_R_II_P(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 8:
        return -1
    is_imm = (ins_key == "LOP3_P_R_R_II_R_II_P")
    is_ur = (ins_key == "LOP3_P_R_R_UR_R_II_P")
    opcode = 530
    if is_imm:
        opcode = 2066
    if is_ur:
        opcode = 3090
    pred = int(ins_vals[0])
    pdst = int(ins_vals[1])
    rdst = int(ins_vals[2])
    r1 = int(ins_vals[3])
    r2 = int(ins_vals[4]) #can be imm or ur
    r3 = int(ins_vals[5])
    op = int(ins_vals[6])
    psrc = int(ins_vals[7])

    inst = opcode

    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (r1) << 24
    inst |= (r2) << 32
    inst |= (r3) << 64
    inst |= (op) << 72
    inst |= (pdst) << 81
    inst |= (psrc) << 87

    if "0_PAND" in ins_modi:
        inst |= 1 << 80
    if "7_cNOT" in ins_modi:
        inst |= 1 << 90

    if is_ur:
        inst |= 1 << 91

    return inst

#sm_120
def LDCU_UR_cAI(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 4:
        return -1
    opcode = 1964
    pred = int(ins_vals[0])
    ur = int(ins_vals[1])
    ad1 = int(ins_vals[2])
    ad2 = int(ins_vals[3])
    inst = opcode
    if "0_64" in ins_modi:
        inst |= 1 << 73
    inst |= (pred) << 12
    inst |= (ur) << 16
    inst |= (ad1) << 54
    inst |= (ad2) << 37
    inst |= 1 << 75
    inst |= 1 << 91
    inst |= 255 << 24
    return inst

#sm_120
def IADD_R_P_R_R_P(ins_key, ins_vals, ins_modi):
    if len(ins_vals) != 6:
        return -1
    opcode = 565
    pred = int(ins_vals[0])
    rdst = int(ins_vals[1])
    pdst = int(ins_vals[2])
    r1 = int(ins_vals[3])
    r2 = int(ins_vals[4])
    psrc = int(ins_vals[5])
    inst = opcode

    inst |= (pred) << 12
    inst |= (rdst) << 16
    inst |= (r1) << 24
    inst |= (r2) << 32
    inst |= (pdst) << 81
    inst |= (psrc) << 87
    if "5_cNOT" in ins_modi:
        inst |= 1 << 90
    if "0_64" in ins_modi:
        inst |= 1 << 73

    inst |= 1 << 74 # enable Psrc (IADD.X)

    if "3_reuse" in ins_modi:
        inst |= (1 << 122)
    if "4_reuse" in ins_modi:
        inst |= (1 << 123)
    return inst


##########################################################################################
def check_new_ops(sm, ins_key, ins_vals, ins_modi):
    global SM_VER
    SM_VER = sm
    # WARNING: dont set any bits from 105 and higher(except reuse)! It's control codes and they will be ADDed(not ORed) later
    if (ins_key == "BRA_II") or (ins_key == "BRA_P_UR_II"):
        return BRA_II(ins_key, ins_vals, ins_modi)
    if ins_key == "BRX_R_II":
        return BRX_R_II(ins_key, ins_vals, ins_modi)
    if ins_key == "BRXU_UR_II":
        return BRXU_UR_II(ins_key, ins_vals, ins_modi)
    if ins_key == "R2UR_UR_R":
        return R2UR_UR_R(ins_key, ins_vals, ins_modi)
    if (ins_key == "IADD3_R_P_P_R_R_R_P_P") or (ins_key == "IADD3_R_P_P_R_II_R_P_P"):
        return IADD3_R_P_P_R_R_R_P_P(ins_key, ins_vals, ins_modi)
    if (ins_key == "IADD3_R_P_R_R_R_P_P") or (ins_key == "IADD3_R_P_R_II_R_P_P"):
        return IADD3_R_P_R_R_R_P_P(ins_key, ins_vals, ins_modi)
    # IMAD wide (there is no non-wide version with same params)
    if ins_key == "IMAD_R_P_R_R_R_P":
        return IMAD_R_P_R_R_R_P(ins_key, ins_vals, ins_modi)
    # IMAD wide imm (there is no non-wide version with same params)
    if ins_key == "IMAD_R_P_R_II_R_P":
        return IMAD_R_P_R_II_R_P(ins_key, ins_vals, ins_modi)
    # IMAD.X (not wide)
    if ins_key == "IMAD_R_R_R_R_P":
        return IMAD_R_R_R_R_P(ins_key, ins_vals, ins_modi)
    # LDG, STG
    if ins_key == "LDG_R_dARI":
        return LDG_R_dARI(ins_key, ins_vals, ins_modi)
    if (ins_key == "LDG_R_ARURI_P") or (ins_key == "LDG_R_ARURI"):
        return LDG_R_ARURI_P(ins_key, ins_vals, ins_modi)
    if (ins_key == "LDG_R_R_dARI_II") or (ins_key == "LDG_R_R_ARURI_II"):
        return LDG_R_R_dARI_II_256(ins_key, ins_vals, ins_modi)
    if (ins_key == "STG_dARI_R_R_II") or (ins_key == "STG_ARURI_R_R_II"):
        return STG_dARI_R_R_II_256(ins_key, ins_vals, ins_modi)
    if ins_key == "STG_dARI_R":
        return STG_dARI_R(ins_key, ins_vals, ins_modi)
    if ins_key == "STG_ARURI_R":
        return STG_ARURI_R(ins_key, ins_vals, ins_modi)
    #LDGSTS
    if ins_key == "LDGSTS_ARI_ARURI":
        return LDGSTS_ARI_ARURI(ins_key, ins_vals, ins_modi)
    #atomic
    if ins_key == "ATOMG_P_R_ARURI_R":
        return ATOMG_P_R_ARURI_R(ins_key, ins_vals, ins_modi)
    if ins_key == "RED_ARURI_R":
        return RED_ARURI_R(ins_key, ins_vals, ins_modi)
    #misc
    if ins_key == "LEA_R_P_R_R_II_P":
        return LEA_R_P_R_R_II_P(ins_key, ins_vals, ins_modi)
    if ins_key == "CALL_II":
        return CALL_II(ins_key, ins_vals, ins_modi)
    if (ins_key == "LDC_R_cAI") or (ins_key == "LDC_R_cARI"):
        return LDC_R_cAI(ins_key, ins_vals, ins_modi)
    if (ins_key == "LOP3_P_R_R_R_R_II_P") or (ins_key == "LOP3_P_R_R_II_R_II_P") or (ins_key == "LOP3_P_R_R_UR_R_II_P"):
        return LOP3_P_R_R_R_R_II_P(ins_key, ins_vals, ins_modi)
    #blackwell
    #nvidia increased UR count to 255, so URZ=255 (old was URZ=UR63)
    #but we cannot use cuAsm Repos anymore for any instructions that accept UR>63
    #we will have to implement them here if we decide to support UR>63
    if SM_VER == 120:
        if ins_key == "LDCU_UR_cAI":
            return LDCU_UR_cAI(ins_key, ins_vals, ins_modi)
        if ins_key == "IADD_R_P_R_R_P": #IADD.64 support
            return IADD_R_P_R_R_P(ins_key, ins_vals, ins_modi)

    return -1
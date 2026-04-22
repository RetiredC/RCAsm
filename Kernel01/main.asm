//(c) 2026, Retired Coder(RC)

CONST STRIDE = 8 //in ints
CONST INT_SIZE = 4 //in bytes

KERNEL mulKernel(regcnt=255, Input=R8, Output=R24, TmpArr=R32, global_id=R52, block_id=R53, ptr=R54, LoopCntR=R56, \
cp=UR0, dev_a=UR2, dev_b=UR4, dev_c=UR6, LoopCnt=UR11, RetAdr=UR12, LoopAdr=UR14)
{
////start mulKernel
    [B------:R-:W0:-:S01]    S2R global_id, SR_TID.X
    [B------:R-:W0:-:S02]    S2R block_id, SR_CTAID.X
    [B0-----:R-:W-:-:S01]    LEA global_id, block_id, global_id, 0x8
#IF {SM_VER} == 89
    [B------:R-:W-:-:S01]    ULDC.64 cp, c[0x0][0x118] //cache policy
    [B------:R-:W-:-:S01]    ULDC.64 dev_a, c[0x0][0x160] //dev_a
    [B------:R-:W-:-:S01]    ULDC.64 dev_b, c[0x0][0x168] //dev_b
    [B------:R-:W-:-:S01]    ULDC.64 dev_c, c[0x0][0x170] //dev_c
    [B------:R-:W-:-:S01]    ULDC LoopCnt, c[0x0][0x178] //repeat_cnt
#ELSE
    [B------:R-:W-:-:S01]    UMOV URZ, 0x00 //for sm_120 we have limited UR support, same 63 instead of 255
    [B------:R-:W0:-:S01]    LDCU.64 cp, c[0x0][0x358] //zero cache policy
    [B------:R-:W0:-:S01]    LDCU.64 dev_a, c[0x0][{0x160 + 0x220}] //dev_a
    [B------:R-:W0:-:S01]    LDCU.64 dev_b, c[0x0][{0x168 + 0x220}] //dev_b
    [B------:R-:W0:-:S01]    LDCU.64 dev_c, c[0x0][{0x170 + 0x220}] //dev_c
    [B------:R-:W0:-:S02]    LDCU LoopCnt, c[0x0][{0x178 + 0x220}] //repeat_cnt
#ENDIF

    [B0-----:R-:W-:-:S05]    IMAD.U32 ptr, global_id, {STRIDE * INT_SIZE}, RZ
    [B------:R-:W0:-:S01]    LDG.E.128 Input0, [ptr.U32 + dev_a]
    [B------:R-:W0:-:S01]    LDG.E.128 Input4, [ptr.U32 + dev_a + 0x10]
    [B------:R-:W0:-:S01]    LDG.E.128 Input8, [ptr.U32 + dev_b]
    [B------:R-:W0:-:S02]    LDG.E.128 Input12, [ptr.U32 + dev_b + 0x10]

    [B0-----:R-:W-:-:S01]    MOV LoopCntR, LoopCnt
    [B------:R-:W-:-:S01]    UMOV RetAdr1, 0xFFFFFFFF
//store end of "MulMod256" for return
//    [B------:R-:W-:-:S01]   UMOV RetAdr0, `(.relN_end_MulMod256) //RCASM:CallPointA

    [B------:R-:W-:-:S01]    UMOV LoopAdr0, 0x00
    [B------:R-:W-:-:S01]    UMOV LoopAdr1, 0x00
    [B------:R-:W-:-:S01]    UMOV LoopAdr2, `(.relP_loop_end) - 0x10

.label_loop_beg:
    [B------:R-:W-:-:S01]    UISETP.NE.AND UP0, UPT, LoopCnt, 0x01, UPT

//"inc_func" cannot use caller vars directly, only as parameters
inc_func MulMod256(Ri=Input, Ro=Output, Rt=TmpArr, Pt=0)


//if you don't care about possible issues and want to use caller vars directly, use "include"
//include MulMod256(Ri=8, Ro=Output, Rt=TmpArr, Pt=0)

//"call_func" slower because of two jumps, but you can call same code from different places (with same parameters)
//dont forget to uncomment "UMOV RetAdr" line too :)
//call_func MulMod256(Ri=8, Ro=Output, Rt=TmpArr, Pt=0, Ret="[B------:R-:W-:-:S01] BRXU RetAdr0, 0x00") //RCASM:CallPointA

//loop with BRA
//    [B------:R-:W-:-:S09]    IADD3 LoopCntR, LoopCntR, -0x1, RZ
//    [B------:R-:W-:Y:S13]    ISETP.EQ.AND P0, PT, LoopCntR, 0x00, PT
//    [B------:R-:W-:Y:S05] @!P0 BRA `(.label_loop_beg)

//loop with BRXU
    [B------:R-:W-:-:S01] @!UP0 UMOV LoopAdr0, LoopAdr2
    [B------:R-:W-:-:S01]    UIADD3 LoopCnt, LoopCnt, -0x1, URZ
    [B------:R-:W-:-:S01]    BRXU LoopAdr0, `(.label_loop_beg)

.relP_loop_end:
    [B------:R-:W-:-:S05]    IMAD.U32 ptr, global_id, {STRIDE * INT_SIZE}, RZ
    [B------:R-:W-:-:S01]    STG.E.128 [ptr.U32 + dev_c], Output0
    [B------:R-:W-:-:S01]    STG.E.128 [ptr.U32 + dev_c + 0x10], Output4
    [B------:R-:W-:-:S05]    EXIT
////end mulKernel
}
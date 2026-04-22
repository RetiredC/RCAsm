//(c)Retired Coder(RC), 2026

// 120G/s on 4090, 180G/s on 5090, 190G on 6000pro
// check "algo.png" for details
FUNCTION MulMod256(First=Ri0, Second=Ri8)
{ //Ri_cnt=8+8, Ro_cnt=8, Ro_tmp=20, P=[0..5]
////start MulMod256
//0: 0A 0C
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32 Ro0, First0.reuse, Second0, RZ
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32 Ro2, First0, Second2, RZ
//2: 1B 0E
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Ro2, Pt0, First1.reuse, Second1, Ro2
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Ro4, First0, Second4, RZ, Pt0
//2: 2A 1D 0G
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Ro2, Pt1, First2, Second0, Ro2
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Ro4, Pt1, First1.reuse, Second3, Ro4, Pt1
    [B------:R-:W-:-:S02]    IMAD.WIDE.U32.X Ro6, First0, Second6, RZ, Pt1
//4: 2C 1F 1H
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Ro4, Pt0, First2, Second2, Ro4
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Ro6, Pt0, First1.reuse, Second5, Ro6, Pt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt12, First1, Second7, RZ, Pt0
//4: 3B 2E 2G 3H
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Ro4, Pt0, First3, Second1, Ro4
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Ro6, Pt0, First2.reuse, Second4, Ro6, Pt0
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt12, Pt0, First2, Second6, Rt12, Pt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt14, PT, First3.reuse, Second7, RZ, Pt0
//4: 4A 3D 3F 4G 5H
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Ro4, Pt0, First4, Second0, Ro4
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Ro6, Pt0, First3.reuse, Second3, Ro6, Pt0
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt12, Pt0, First3, Second5, Rt12, Pt0
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt14, Pt0, First4.reuse, Second6, Rt14, Pt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt16, First5, Second7, RZ, Pt0
//6: 4C 4E 5F 6G 7H
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Ro6, Pt0, First4.reuse, Second2, Ro6
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt12, Pt0, First4, Second4, Rt12, Pt0
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt14, Pt0, First5, Second5, Rt14, Pt0
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt16, Pt0, First6, Second6, Rt16, Pt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt18, First7, Second7, RZ, Pt0
//6: 5B 5D 6E 7F, get C3
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Ro6, Pt0, First5.reuse, Second1, Ro6
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt12, Pt0, First5, Second3, Rt12, Pt0
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt14, Pt0, First6.reuse, Second4, Rt14, Pt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt16, Pt3, First7, Second5, Rt16, Pt0
//6: 6A 6C 7D, get C2
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Ro6, Pt0, First6.reuse, Second0, Ro6
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt12, Pt0, First6, Second2, Rt12, Pt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt14, Pt2, First7.reuse, Second3, Rt14, Pt0
//8: 7B, get C1
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32 Rt12, Pt1, First7, Second1, Rt12
///////////////////////////////
//0: 0B
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32 Rt0, First0, Second1, RZ
    [B------:R-:W-:-:S01]    IADD3.X Rt10, RZ, RZ, RZ, Pt1, !PT //C1 to Rt10
//0: 1A 0D
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Rt0, Pt0, First1, Second0, Rt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt2, First0, Second3, RZ, Pt0
    [B------:R-:W-:-:S01]    IADD3.X Rt11, RZ, RZ, RZ, Pt2, !PT //C2 to Rt11
//2: 1C 0F
    [B------:R-:W-:-:S03]    IMAD.WIDE.U32 Rt2, Pt0, First1, Second2, Rt2
    [B------:R-:W-:-:S01]    IADD3.X Rt18, Pt1, PT, Rt18, RZ, RZ, Pt3, !PT //now use C3 and C7 and forget
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt4, First0, Second5, RZ, Pt0
    [B------:R-:W-:-:S01]    IADD3 Ro1, Pt3, Ro1, Rt0, RZ //build res
//2: 2B 1E 0H
    [B------:R-:W-:-:S03]    IMAD.WIDE.U32 Rt2, Pt0, First2, Second1, Rt2
    [B------:R-:W-:-:S01]    IADD3.X Ro2, Pt3, Ro2, Rt1, RZ, Pt3, !PT //build res
    [B------:R-:W-:-:S04]    IMAD.WIDE.U32.X Rt4, Pt0, First1, Second4, Rt4, Pt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt0, First0, Second7, RZ, Pt0
//2: 3A 2D 1G 2H
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Rt2, Pt0, First3, Second0, Rt2
    [B------:R-:W-:-:S02]    IMAD.WIDE.U32.X Rt4, Pt0, First2, Second3, Rt4, Pt0
    [B------:R-:W-:-:S01]    IADD3.X Ro3, Pt3, Ro3, Rt2, RZ, Pt3, !PT //build res
    [B------:R-:W-:-:S03]    IMAD.WIDE.U32.X Rt0, Pt0, First1, Second6, Rt0, Pt0
    [B------:R-:W-:-:S01]    IADD3.X Ro4, Pt3, Ro4, Rt3, RZ, Pt3, !PT //build res
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt2, First2, Second7, RZ, Pt0
//4: 3C 2F 3G 4H
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Rt4, Pt0, First3, Second2, Rt4
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt0, Pt0, First2, Second5, Rt0, Pt0
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt2, Pt0, First3, Second6, Rt2, Pt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt6, First4, Second7, RZ, Pt0
//4: 4B 3E 4F 5G 6H
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Rt4, Pt0, First4, Second1, Rt4
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt0, Pt0, First3, Second4, Rt0, Pt0
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt2, Pt0, First4, Second5, Rt2, Pt0
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt6, Pt0, First5, Second6, Rt6, Pt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt8, First6, Second7, RZ, Pt0
//4: 5A 4D 5E 6F 7G, get C7(store in Pt4)
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Rt4, Pt0, First5, Second0, Rt4
    [B------:R-:W-:-:S02]    IMAD.WIDE.U32.X Rt0, Pt0, First4, Second3, Rt0, Pt0
    [B------:R-:W-:-:S01]    IADD3.X Ro5, Pt3, Ro5, Rt4, RZ, Pt3, !PT //build res
    [B------:R-:W-:-:S02]    IMAD.WIDE.U32.X Rt2, Pt0, First5, Second4, Rt2, Pt0
    [B------:R-:W-:-:S01]    IADD3.X Ro6, Pt3, Ro6, Rt5, RZ, Pt3, !PT //build res
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt6, Pt0, First6, Second5, Rt6, Pt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt8, Pt4, First7, Second6, Rt8, Pt0
//6: 5C 6D 7E, get C6
    [B------:R-:W-:-:S03]    IMAD.WIDE.U32 Rt0, Pt0, First5, Second2, Rt0
    [B------:R-:W-:-:S01]    IADD3.X Rt19, PT, PT, Rt19, RZ, RZ, Pt1, Pt4 //now use C3 and C7 and forget
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32.X Rt2, Pt0, First6, Second3, Rt2, Pt0
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt6, Pt5, First7, Second4, Rt6, Pt0 //C6 to Pt5
//6: 6B 7C, get C5
    [B------:R-:W-:Y:S04]    IMAD.WIDE.U32 Rt0, Pt0, First6, Second1, Rt0

    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt2, Pt2, First7, Second2, Rt2, Pt0
//6: 7A, get C4
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32 Rt0, Pt4, First7, Second0, Rt0
    [B------:R-:W-:-:S01]    IADD3.X Rt4, RZ, RZ, RZ, Pt2, !PT //C5 to Rt4
    [B------:R-:W-:Y:S04]    IADD3.X Ro7, Pt3, Ro7, Rt0, RZ, Pt3, !PT //build res
    [B------:R-:W-:Y:S04]    IADD3.X Rt12, Pt3, Rt12, Rt1, RZ, Pt3, !PT //build res
    [B------:R-:W-:-:S01]    IADD3.X Rt13, Pt3, Pt4, Rt13, Rt2, RZ, Pt3, Pt4 //build res
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32 Rt0, Rt12, 0x3D1, RZ
    [B------:R-:W-:-:S01]    IADD3.X Rt14, Pt3, Pt4, Rt14, Rt3, Rt10, Pt3, Pt4 //build res
    [B------:R-:W-:-:S01]    IADD3.X Rt10, RZ, RZ, RZ, Pt5, !PT //C6 to Rt10
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt2, Pt2, Rt13, 0x3D1, Rt12, !PT
    [B------:R-:W-:-:S01]    IADD3.X Rt15, Pt3, Pt4, Rt15, Rt6, Rt4, Pt3, Pt4 //build res
    [B------:R-:W-:-:S01]    IADD3.X Ro0, Pt0, Pt1, Ro0, Rt0, RZ, !PT, !PT
    [B------:R-:W-:-:S01]    IADD3.X Rt16, Pt3, Pt4, Rt16, Rt7, Rt11, Pt3, Pt4 //build res
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32 Rt4, Rt14, 0x3D1, RZ
    [B------:R-:W-:-:S01]    IADD3.X Rt17, Pt3, Pt4, Rt17, Rt8, Rt10, Pt3, Pt4 //build res
    [B------:R-:W-:-:S01]    IADD3.X Ro1, Pt0, Pt1, Rt1, Rt2, Ro1, Pt0, Pt1
    [B------:R-:W-:-:S01]    IADD3.X Rt18, Pt3, Pt4, Rt18, Rt9, RZ, Pt3, Pt4 //build res
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt6, Pt2, Rt15, 0x3D1, Rt14, Pt2
    [B------:R-:W-:-:S01]    IADD3.X Rt19, Rt19, RZ, RZ, Pt3, Pt4 //build res
// reduction
    [B------:R-:W-:-:S01]    IADD3.X Ro2, Pt0, Pt1, Rt3, Rt4, Ro2, Pt0, Pt1
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32 Rt8, Rt16, 0x3D1, RZ
    [B------:R-:W-:-:S01]    IADD3.X Ro3, Pt0, Pt1, Rt5, Rt6, Ro3, Pt0, Pt1
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt4, Pt2, Rt17, 0x3D1, Rt16, Pt2
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32 Rt0, Rt18, 0x3D1, RZ
    [B------:R-:W-:-:S01]    IADD3.X Ro4, Pt0, Pt1, Rt7, Rt8, Ro4, Pt0, Pt1
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Rt2, Pt2, Rt19, 0x3D1, Rt18, Pt2
    [B------:R-:W-:Y:S04]    IADD3.X Ro5, Pt0, Pt1, Rt9, Rt4, Ro5, Pt0, Pt1
    [B------:R-:W-:Y:S04]    IADD3.X Ro6, Pt0, Pt1, Rt5, Rt0, Ro6, Pt0, Pt1
    [B------:R-:W-:Y:S04]    IADD3.X Ro7, Pt0, Pt1, Rt1, Rt2, Ro7, Pt0, Pt1
//Rt8..Rt9 is "tmp[4] in cpu code, Rt8 <= 0x3d1 (checked P-1*P-1), Rt9 <= 1
    [B------:R-:W-:Y:S04]    IADD3.X Rt8, Pt0, PT, Rt3, RZ, RZ, Pt0, Pt1
    [B------:R-:W-:-:S01]    IADD3.X Rt9, Pt0, Pt1, RZ, RZ, RZ, Pt0, Pt2
////
    [B------:R-:W-:-:S01]    IMAD.WIDE.U32.X Ro0, Pt3, Rt8, 0x3D1, Ro0, !PT
    [B------:R-:W-:-:S03]    IMAD.WIDE.U32 Rt2, Rt9, 0x3D1, Rt8 //no carry occurs!
    [B------:R-:W-:Y:S04]    IADD3.X Ro1, Pt0, PT, Ro1, Rt2, RZ, !PT, !PT
    [B------:R-:W-:Y:S04]    IADD3.X Ro2, Pt0, Pt1, Rt3, Ro2, RZ, Pt0, Pt3
    [B------:R-:W-:Y:S04]    IADD3.X Ro3, Pt0, PT, Ro3, RZ, RZ, Pt0, Pt1
    [B------:R-:W-:Y:S04]    IADD3.X Ro4, Pt0, PT, Ro4, RZ, RZ, Pt0, !PT
    [B------:R-:W-:Y:S04]    IADD3.X Ro5, Pt0, PT, Ro5, RZ, RZ, Pt0, !PT
    [B------:R-:W-:Y:S04]    IADD3.X Ro6, Pt0, PT, Ro6, RZ, RZ, Pt0, !PT
    [B------:R-:W-:Y:S04]    IADD3.X Ro7, PT, PT, Ro7, RZ, RZ, Pt0, !PT
//now if P(carry) is 1 then we need Sub(256k1_P), chance is about 1/2^129 so just ignore it
////end MulMod256
}
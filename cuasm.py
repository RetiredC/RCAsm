# This file is a part of RCAsm software
# (c) 2026, RetiredCoder (RC)
# License: GPLv3, see "LICENSE.TXT" file
# https://github.com/RetiredC

import os, sys
from pathlib import Path

import defs
import utils

REPO_ROOT = Path(__file__).parent / "cuAssembler"
sys.path.insert(0, str(REPO_ROOT))
from cuAssembler.CuAsm import CubinFile, CuAsmParser, config

########################################################################################################################

def cubin2cuasm(fn_cubin: Path | str) -> bool:
    fbase, fext = os.path.splitext(fn_cubin)
    asmname = fbase + '.cuasm'
    try:
        cf = CubinFile.CubinFile(fn_cubin)
        cf.saveAsCuAsm(asmname)
    except Exception as e:
        utils.to_log(f"cubin2cuasm error: {e}")
        return False
    return True

def cuasm2cubin(fn_cuasm: Path | str) -> bool:
    cap = CuAsmParser()
    cap.set_sm(defs.SM_VER)
    try:
        cap.parse(fn_cuasm)
    except Exception as e:
        utils.to_log(f"cuasm2cubin asm parsing error: {e}")
        return False
    fbase, fext = os.path.splitext(fn_cuasm)
    binname = fbase + '.cubin'
    try:
        cap.saveAsCubin(binname)
    except Exception as e:
        utils.to_log(f"cuasm2cubin cubin saving error: {e}")
        return False
    return True

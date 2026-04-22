# This file is a part of RCAsm software
# (c) 2026, RetiredCoder (RC)
# License: GPLv3, see "LICENSE.TXT" file
# https://github.com/RetiredC

import sys
########################################################################################################################

PROJECT_PATH = "./Kernel01"
#PROJECT_PATH = "./Kernel02"
#PROJECT_PATH = "./Kernel03"


CUASM_NAME89 = "kernel_sm89.cuasm"
CUASM_NAME120 = "kernel_sm120.cuasm"

EXE_NAME = "MBench.exe" if sys.platform.startswith("win") else "build/mbench"
EXE_PARAMS89 = "-test_sm 89"
EXE_PARAMS120 = "-test_sm 120"

#empty - process all kernels
#KERNELS_TO_PROCESS = ["KernelB"]
KERNELS_TO_PROCESS = []


#options in "config.json"
SM_VER = 120
AUTO_RUN = True
WND_GEOMETRY = None
SPL_STATE = None
########################################################################################################################

VERBOSE = False #True


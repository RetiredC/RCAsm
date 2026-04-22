# This file is a part of RCAsm software
# (c) 2026, RetiredCoder (RC)
# License: GPLv3, see "LICENSE.TXT" file
# https://github.com/RetiredC
import os
import struct
from pathlib import Path
#########################################
# credits:
# https://github.com/cloudcores/CuAssembler
#########################################

from typing import List, Dict, Tuple, Optional
import time, subprocess
from dataclasses import dataclass

import utils, defs, cuasm, unit_params
from cuAssembler.CuAsm.CuAsmParser import CuAsmParser
from cuAssembler.CuAsm.CubinFile import CubinFile


########################################################################################################################

@dataclass
class AsmUnit:
    type: str # KERNEL, FUNCTION, CONST
    name: str
    fn: str
    const_val: str
    body: List[str]
    kernel_asm_out: List[str]
    kernel_regcnt: int
    params: Dict[str, int | str]

def get_units(lines: List[str], fn: str) -> List[AsmUnit]:
    #Parse kernels, funcs and consts
    units: List[AsmUnit] = []
    seen_names: set[str] = set()
    n = len(lines)

    # Preprocess lines: remove comments and trim spaces
    stripped: List[str] = utils.remove_comments(lines)

    i = 0
    while i < n:
        line = stripped[i]

        # Skip empty lines between units
        if line == "":
            i += 1
            continue

        # Header must be "KERNEL name" or "FUNCTION name"
        if line.startswith("KERNEL ") or line.startswith("FUNCTION "):
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                utils.to_log(f"expected KERNEL/FUNCTION + name, but found: {line}")
                return []

            unit_type = parts[0]          # "KERNEL" or "FUNCTION"
            res = unit_params.parse_unit_params(parts[1].strip())
            if (res is None) or (res[0] == ""):
                utils.to_log(f"wrong KERNEL/FUNCTION declaration: {line}")
                return []
            name = res[0]
            # Check for duplicate name
            if name in seen_names:
                utils.to_log(f"duplicate KERNEL/FUNCTION/CONST name: {name}")
                return []

            # Next line (after stripping/comments) must be "{"
            if i + 1 >= n or stripped[i + 1].strip() != "{":
                utils.to_log(f"expected {{ after KERNEL/FUNCTION declaration, but found: {line}")
                return []

            body_start = i + 2
            j = body_start

            # Find closing "}", checking for nested KERNEL/FUNCTION
            while j < n and stripped[j].strip() != "}":
                inner = stripped[j]
                if inner.startswith("KERNEL ") or inner.startswith("FUNCTION "):
                    # New header inside body before closing brace -> error
                    utils.to_log(f"expected }} at the end of KERNEL/FUNCTION body but found: {line}")
                    return []
                j += 1

            if j >= n:
                # No closing brace
                utils.to_log(f"expected }} at the end of KERNEL/FUNCTION body")
                return []

            # Body: keep original lines (with comments, spaces)
            body: List[str] = []
            for kk in range(body_start, j):
                if not stripped[kk].strip() and lines[kk].strip() and not lines[kk].strip().startswith("//"):
                    body.append("//" + lines[kk])
                else:
                    body.append(lines[kk])

            units.append(AsmUnit(type=unit_type, name=name, fn=fn, body=body, kernel_asm_out=[], kernel_regcnt=0, params=res[1], const_val=""))
            seen_names.add(name)

            # Continue after closing brace
            i = j + 1
        else:
            if line.startswith("CONST "):
                s = line[6:].strip()
                cname, cval = s.split("=", 1)
                cname = cname.strip()
                cval = "(" + cval.strip() + ")"
                if not cname:
                    utils.to_log(f"expected CONST + name=val, but found: {line}")
                    return []
                # Check for duplicate name
                if cname in seen_names:
                    utils.to_log(f"duplicate CONST name: {cname}")
                    return []
                units.append(AsmUnit(type="CONST", name=cname, fn=fn, body=[], kernel_asm_out=[],
                                     kernel_regcnt=0, params={}, const_val=cval))
                seen_names.add(cname)
                i += 1
            else:
                utils.to_log(f"expected KERNEL/FUNCTION/CONST + name, but found: {line}")
                return []

    #also add SM_VER const
    if "SM_VER" in seen_names:
        utils.to_log(f"duplicate CONST name: SM_VER")
        return []
    units.append(AsmUnit(type="CONST", name="SM_VER", fn="", body=[], kernel_asm_out=[],
                         kernel_regcnt=0, params={}, const_val=str(defs.SM_VER)))

    return units

def check_code(liness : List[Tuple[List[str], str]]) -> bool:
    units: List[AsmUnit] = []
    for lines, fn in liness:
        uns : List[AsmUnit] = get_units(lines, fn)
        units.extend(uns)
    if len(units) == 0:
        utils.to_log("cannot parse units, checking FAILED")
        return False
    cnt = 0
    for unit in units:
        if not unit.name.startswith("_") and (len(unit.fn) > 0):
            cnt += 1
    utils.to_log(f"{cnt} public units found:")
    for i, unit in enumerate(units):
        if unit.name.startswith("_") or (len(unit.fn) == 0):
            continue
        utils.to_log(f"  {unit.fn}: {unit.type} {unit.name}")
        if (unit.type != "CONST") and (len(unit.body) == 0):
            utils.to_log(f"unit {unit.name} has no body")
    return True

def compile_code(liness : List[Tuple[List[str], str]], is_inject: bool) -> bool:
    start_ns = time.perf_counter_ns()
    utils.to_log("Compiling code...")

    #first of all, we need to check code
    if not check_code(liness):
        utils.to_log("Checking code failed, compiling FAILED")
        return False

    units: List[AsmUnit] = []
    for lines, fn in liness:
        uns: List[AsmUnit] = get_units(lines, fn)
        units.extend(uns)

    #calc expressions
    consts: Dict[str, str] = {}
    for unit in units:
        if unit.type == "CONST":
            consts[unit.name] = unit.const_val
    for unit in units:
        if (unit.type == "FUNCTION") or (unit.type == "KERNEL"):
            for i, line in enumerate(unit.body):
                res: str = utils.process_expressions(line, consts)
                if res and (res != line):
                    unit.body[i] = res

    #compile kernels
    kcnt: int = 0
    for i, unit in enumerate(units):
        if unit.type != "KERNEL":
            continue
        if len(defs.KERNELS_TO_PROCESS) > 0:
            if not (units[i].name in defs.KERNELS_TO_PROCESS):
                continue

        if not compile_kernel(units, i):
            utils.to_log(f"    unit {unit.name}: compiling failed")
            return False
        kcnt += 1

    if kcnt == 0:
        utils.to_log("No kernels found, compiling FAILED")
        return False

    if not is_inject:
        elapsed_us = int((time.perf_counter_ns() - start_ns) / 1_000_000)
        utils.to_log(f"Done({elapsed_us}ms): compiling SUCCESSFUL")
        return True

    for unit in units:
        if unit.type != "KERNEL":
            continue
        if len(defs.KERNELS_TO_PROCESS) > 0:
            if not (unit.name in defs.KERNELS_TO_PROCESS):
                continue
        if not inject_kernel(unit):
            utils.to_log(f"    unit {unit.name}: injecting FAILED")
            return False
    utils.to_log("injecting SUCCESSFUL")

    #run cuasm to build modified cubin
    cuasm_name = defs.CUASM_NAME89
    if defs.SM_VER == 120:
        cuasm_name = defs.CUASM_NAME120

    if not create_cubin(defs.PROJECT_PATH + "/" + cuasm_name):
        utils.to_log("cuasm building cubin file FAILED")
        return False

    elapsed_us = int((time.perf_counter_ns() - start_ns) / 1_000_000)
    utils.to_log(f"Done({elapsed_us}ms): compiling+injecting SUCCESSFUL")
    return True

def inject_kernel(unit: AsmUnit) -> bool:
    cuasm_name = defs.CUASM_NAME89
    if defs.SM_VER == 120:
        cuasm_name = defs.CUASM_NAME120

    lines = utils.load_list_from_file(defs.PROJECT_PATH + "/" + cuasm_name)
    #find kernel name there
    k_line_ind: int = -1
    target = f".section\t.text.{unit.name}," # kernels start from ".section	.text.addKernel,"...
    for i, line in enumerate(lines):
        line = line.split("//", 1)[0]
        if line.lstrip().startswith(target):
            k_line_ind = i
            break
    if (k_line_ind < 0):
        utils.to_log(f"  error: cannot find kernel {unit.name} in {cuasm_name}")
        return False

    #now find regcnt line
    #we wont find it for SM120
    target = '.sectioninfo\t@"SHI_REGISTERS='
    regcnt_line_ind = -1
    for i in range(k_line_ind + 1, len(lines)):
        line = lines[i].split("//", 1)[0]
        if line.lstrip().startswith(target):
            regcnt_line_ind = i
            break
    if regcnt_line_ind < 0:
        if defs.SM_VER < 120:
            utils.to_log(f"  error: cannot find SHI_REGISTERS for kernel {unit.name} in {cuasm_name}")
            return False
        else:
            regcnt_line_ind = k_line_ind + 1

    #now find body
    target = f".text.{unit.name}:"
    kernel_body_ind: int = -1
    for i in range(regcnt_line_ind + 1, len(lines)):
        line = lines[i].split("//", 1)[0]
        if line.lstrip().startswith(target):
            kernel_body_ind = i
            break
    if (kernel_body_ind < 0):
        utils.to_log(f"  error: cannot find body for kernel {unit.name} in {cuasm_name}")
        return False
    kernel_body_ind += 1

    #now find the end of kernel
    end_line_label = ""
    target = f" {unit.name},(.L_" #for example, ".size           addKernel,(.L_x_1 - addKernel)"
    for i in range(k_line_ind + 1, len(lines)):
        line = lines[i].split("//", 1)[0]
        if line.lstrip().startswith(".size") and (line.lstrip().find(target) > 0):
            rest = line[line.find("(") + 1:]
            end_line_label = rest.split()[0]
            break
    if (end_line_label == ""):
        utils.to_log(f"  error: cannot find end label for kernel {unit.name} in {cuasm_name}")
        return False
    k_end_ind: int = -1
    for i in range(k_line_ind + 1, len(lines)):
        line = lines[i].split("//", 1)[0]
        if line.lstrip().startswith(end_line_label):
            k_end_ind = i
            break
    if (k_end_ind < 0):
        utils.to_log(f"  error: cannot find body end for kernel {unit.name} in {cuasm_name}")
        return False
    k_end_ind += 1
    #NEWMY
    #update regcnt
    if defs.SM_VER < 120:
        lines[regcnt_line_ind] = f'  	.sectioninfo\t@"SHI_REGISTERS={unit.kernel_regcnt}"'
    else: #for sm_120 renum is .nv.info section
        found = False
        idxs = [i for i, line in enumerate(lines) if "nvinfo : EIATTR_REGCOUNT" in line]
        for idx in idxs: #todo: this is bad code
            s = lines[idx + 6]
            if s.find(unit.name) > 0:
                ns = f"0x{unit.kernel_regcnt:08X}"
                lines[idx + 7] = f"/*0008*/ 	.word	{ns}"
                found = True
                break
            else:
                s = lines[idx + 7]
                if s.find(unit.name) > 0:
                    ns = f"0x{unit.kernel_regcnt:08X}"
                    lines[idx + 8] = f"/*0008*/ 	.word	{ns}"
                    found = True
                    break
        if not found:
            utils.to_log(f"  error: cannot set regnum for kernel {unit.name} in {cuasm_name}")
            return False

    #inject kernel
    lines = lines[:kernel_body_ind] + unit.kernel_asm_out + lines[k_end_ind-1:]  # I like python :)

    #save modified .cuasm file
    utils.save_list_to_file(lines, defs.PROJECT_PATH + "/" + cuasm_name)

    return True

def run_exe(lines_out: List[str], args: Optional[List[str]] = None) -> bool:
    exe_path = utils.find_exe(defs.PROJECT_PATH + "/" + defs.EXE_NAME)

    cmd = [exe_path]
    if args:
        cmd.extend(args)

    utils.to_log(f"Run: {' '.join(cmd)} ...")

    p = subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )

    lines_out += p.stdout.splitlines()
    return True

def find_func_in_list(func_list: List[Tuple[int, int, Dict[str, int | str]]], find:int, fparams: Dict[str, int | str]) -> Tuple[int, int]:
    for i, f in enumerate(func_list):
        if (f[0] == find) and (fparams == f[2]):
            return i, f[1]
    return -1, -1

# returns final func body, also adds func calls to called_func_list (does not process them, just adds)
def compile_func(units: List[AsmUnit], unit_index: int, glob_func_cnt: List[int], called_func_list: List[Tuple[int, int, Dict[str, int | str]]], params: Dict[str, int | str], cur_func_cnt: int) -> List[str] | None:
    function: AsmUnit = units[unit_index]
    fcalls: List[Tuple[int, str, int, Dict[str, int | str]]] = []
    body: List[str] = function.body.copy()

    body_opt = utils.check_if_else_end(body)
    if body_opt is None:
        utils.to_log(f"wrong #IF #ELSE #ENDIF block")
        return None
    body = body_opt  # type: ignore

    #create list of used functions
    for i in range(0, len(body)):
        line = body[i]

        if line.find("RCASM:CallPoint") >= 0:
            body[i] = body[i].rstrip() + str(cur_func_cnt)

        line = line.split("//", 1)[0].strip()
        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            continue
        if (parts[0] == "call_func") or (parts[0] == "inc_func") or (parts[0] == "include"):
            res = unit_params.parse_unit_params(parts[1].strip())
            if (res is None) or (res[0] == ""):
                utils.to_log(f"wrong FUNCTION call/include: {line}")
                return None
            name = res[0]
            #we cannot call/include kernels and itself
            if name == function.name:
                utils.to_log(f"wrong FUNCTION call/include: not allowed: {line}")
                return None
            findex = -1
            for j, u in enumerate(units):
                if u.name == name:
                    if u.type != "FUNCTION":
                        utils.to_log(f"wrong FUNCTION call/include: {name} is not a function: {line}")
                        return None
                    findex = j
                    break
            if findex < 0:
                utils.to_log(f"cannot find FUNCTION {name} in call/include: {line}")
                return None

            # adjust params for call. For example "Ri=8" must become "Ri=18" if we have "Ri=10" for current function
            # Also "Ri=Rt10" must become "Ri=30" if we have "Rt=20" for current function
            # Also "Rval=val" must become "Rval=Rt50" if we have "val=Rt50" for own params of current function
            regname:str = ""
            regofs:int = 0
            for k, v in res[1].items():
                if k == "Ret":
                    continue

                if type(v) is int:
                    regname = k
                    regofs = int(res[1][k])
                    adv_regofs = 0
                else:
                    #check own params firstly
                    # we support two options: Rval=tmp or Rval=tmp0, so both indexed and non-indexed
                    regname, adv_regofs = utils.extract_word_and_index(str(v))
                    if not regname: #non-indexed
                        if v in units[unit_index].params:
                            v = units[unit_index].params[str(v)]
                    else: #indexed, like Rval=tmp5  and tmp=Rt12 so replace tmp5 to tmp17
                        if regname in units[unit_index].params: # if "tmp" is in current func own params
                            v = units[unit_index].params[regname]
                        else:
                            adv_regofs = 0
                    regname, regofs = utils.extract_word_and_index(str(v))
                    if not regname:
                        utils.to_log(f"cannot parse func param {v} in call/include: {line}")
                        return None

                cur_ofs = params.get(regname, -1)
                if type(cur_ofs) is int:
                    if (cur_ofs < 0) and (regname == "R" or regname == "UR" or regname == "P"):  # for kernel level
                        cur_ofs = 0
                    if cur_ofs >= 0:
                        res[1][k] = regofs + cur_ofs + adv_regofs

            # fix reg in return command when necessary
            ret_cmd = str(res[1].get("Ret", ""))
            if ret_cmd:
                retlist : List[str] | None = [ret_cmd]
                retlist = rename_vars_regs_labels(retlist, units[unit_index].params, cur_func_cnt, params)
                res[1]["Ret"] = retlist[0]

            fcalls.append((i, parts[0], findex, res[1])) #line index, call/include, func index in units, params

    out_body: List[str] = []
    cur_line = 0
    part: List[str]
    for call in fcalls:
        line_ind_call = call[0]
        if call[1] == "include": #plain include, no other actions
            glob_func_cnt[0] += 1
            func_body = compile_func(units, call[2], glob_func_cnt, called_func_list, call[3], glob_func_cnt[0])
            if func_body is None:
                utils.to_log(f"failed to calc FUNCTION {units[call[2]].name} into {function.name}")
                return None

            #change vars for included func, here, in this function
            func_body = rename_vars_regs_labels(func_body, units[unit_index].params, cur_func_cnt, params)

            part = body[cur_line:line_ind_call]
            part = rename_vars_regs_labels(part, units[unit_index].params, cur_func_cnt, params)
            out_body = out_body + part + func_body
            cur_line = line_ind_call + 1
        if call[1] == "inc_func":
            glob_func_cnt[0] += 1
            func_body = compile_func(units, call[2], glob_func_cnt, called_func_list, call[3], glob_func_cnt[0])
            if func_body is None:
                utils.to_log(f"failed to calc FUNCTION {units[call[2]].name} into {function.name}")
                return None
            part = body[cur_line:line_ind_call]
            part = rename_vars_regs_labels(part, units[unit_index].params, cur_func_cnt, params)
            out_body = out_body + part + func_body
            cur_line = line_ind_call + 1
        if call[1] == "call_func": #it's more tricky, we need to modify both code and func and append func after kernel
            ind, g_func_ind = find_func_in_list(called_func_list, call[2], call[3])
            if ind < 0: #this func with same params not found
                glob_func_cnt[0] += 1
                g_func_ind = glob_func_cnt[0]
                called_func_list.append((call[2], g_func_ind, call[3]))

            point_lab:str = ""
            nn = body[line_ind_call].find("RCASM:CallPoint")
            if nn >= 0:
                point_lab = body[line_ind_call][nn + 6:]

            part = body[cur_line:line_ind_call]
            part = rename_vars_regs_labels(part, units[unit_index].params, cur_func_cnt, params)
            out_body = out_body + part + [f"[B------:R-:W-:-:S01] BRXU URZ, `(.begin_{units[call[2]].name}_{g_func_ind})"]
            cur_line = line_ind_call + 1

            #magic: we need to fix label and offset in UMOV UR30, `(.relN_end_MulMod256) + 0x10 //RCASM:Point1_
            if point_lab:
                found:bool = False
                ln_ind:int = len(out_body)-1
                while ln_ind >= 0:
                    nn = out_body[ln_ind].find("RCASM:CallPoint")
                    if nn >=0:
                        p_lab = out_body[ln_ind][nn + 6:]
                        if p_lab == point_lab:
                            if out_body[ln_ind].find("UMOV"): #found
                                # we need to fix func label: add g_func_ind, check two lines before call_func
                                out_body[ln_ind] = out_body[ln_ind].replace(f"`(.relN_end_{units[call[2]].name}_{cur_func_cnt})", f"`(.relN_end_{units[call[2]].name}_{g_func_ind})")
                                # now calc and add offset
                                offset = 16 * utils.get_cmd_cnt(out_body, ln_ind, len(out_body) - 1)
                                pos = out_body[ln_ind].rfind(")")
                                if pos >= 0:
                                    found = True
                                    ln = out_body[ln_ind]
                                    ln = ln[0:pos + 1] + " + " + hex(offset) + ln[pos + 1:]
                                    out_body[ln_ind] = ln

                    ln_ind -= 1
                if not found:
                    utils.to_log(f"failed to fix RCASM:Point in {function.name}")
                    return None

    #add last part + append functions bodies
    part = body[cur_line:]
    res_part = rename_vars_regs_labels(part, units[unit_index].params, cur_func_cnt, params)
    if res_part is None:
        utils.to_log(f"failed to rename vars in {function.name}")
        return None
    out_body = out_body + res_part

    if defs.VERBOSE:
        if not function.name.startswith("_"):
            ops = utils.get_cmd_cnt(out_body, 0, len(out_body))
            utils.to_log(f"func {function.name}, ops: {ops}")

    return out_body


def compile_kernel(units: List[AsmUnit], unit_index: int) -> bool:
    # list of called funcs: ind in units, glob_func_index and params.
    # if same func is called twice with different params, it works as calling two different functions
    # for example call_func myfunc(Ri=0) and myfunc(Ri=8) will cause myfunc body will be added twice with different glob_func_index, regs, labels
    called_func_list: List[Tuple[int, int, Dict[str, int | str]]] = []
    glob_func_cnt : List[int] = [0]
    kernel: AsmUnit = units[unit_index]

    kernel_body: List[str] | None = compile_func(units, unit_index, glob_func_cnt, called_func_list, {}, 0)

    if kernel_body is None:
        utils.to_log(f"failed to compile KERNEL {kernel.name}")
        return False

    append_body: List[str] = []
    for func in called_func_list: #list can grow during calling compile_func, it's ok
        func_body : List[str] | None = compile_func(units, func[0], glob_func_cnt, called_func_list, func[2], func[1])
        if func_body is None:
            utils.to_log(f"failed to compile FUNC {units[func[0]].name}")
            return False

        beg_label = f".begin_{units[func[0]].name}_{func[1]}:"
        end_label = f".relN_end_{units[func[0]].name}_{func[1]}:"
        func_body.insert(0, beg_label)
        func_body.append(end_label)
        ret_cmd = func[2].get("Ret", "")
        if ret_cmd:
            func_body.append(str(ret_cmd))
        append_body = append_body + func_body

    kernel.kernel_asm_out = kernel_body + append_body

    if not ("regcnt" in kernel.params):
        utils.to_log(f"failed to finish KERNEL {kernel.name}, missed regcnt parameter")
        return False
    kernel.kernel_regcnt = int(kernel.params["regcnt"])

    asm_cnt = utils.get_cmd_cnt(kernel.kernel_asm_out, 0, len(kernel.kernel_asm_out))

    utils.to_log(f"  kernel {kernel.name}: compiled, regcnt: {kernel.kernel_regcnt}, asm_lines: {asm_cnt}")
    utils.to_log("    appended functions:")
    for func in called_func_list:
        utils.to_log(f"      {units[func[0]].name} glob_func_index {func[1]}")
    return True

def rename_vars_regs_labels(lines: List[str] | None, unit_params: Dict[str, int | str], glob_func_cnt: int, params: Dict[str, int | str]) -> List[str] | None:
    if lines is None:
        return None
    rtypes: Dict[str, Tuple[str, int | str]] = {}
    for k, v in params.items():
        if k == "Ret":
            continue
        if k in rtypes:
            utils.to_log(f"error: same var {k} specified more than once")
            return None
        else:
            r = ""
            if k.startswith("R"):
                r = "R"
            if k.startswith("UR"):
                r = "UR"
            if k.startswith("P"):
                r = "P"
            if k.startswith("C"): #const
                r = "C"
            if not r:
                return None
            if r == "C":
                r = ""
            rtypes[k] = (r, v)

    own_params: Dict[str, Tuple[str, int]] = {}
    for k, v in unit_params.items():
        name, ind = utils.get_var_index(str(v))
        if name:
            own_params[k] = (name, ind)

    res = []
    for line in lines:
        s = utils.add_label_index(line, glob_func_cnt)
        for kk, vv in own_params.items():
            if vv[1] >= 0:
                s = utils.add_offset(kk, vv[0], vv[1], s)
        for kkk, vvv in rtypes.items():
            if (type(vvv[1]) is int) and (vvv[1] >= 0):
                s = utils.add_offset(kkk, vvv[0], int(vvv[1]), s)
        res.append(s)
    return res

#TESTED WITH CUDA v12.8 ONLY!
def create_cubin(fn_cuasm:str) -> bool:
    if defs.SM_VER == 89:
        if not cuasm.cuasm2cubin(fn_cuasm):
            return False
        return True

    #for 5090 we need to copy some new sections from original cubin, thanks to nvidia, they add more and more...
    cubin_orig = utils.change_ext(fn_cuasm, "cubin_orig")
    cubin_new = utils.change_ext(fn_cuasm, "cubin")
    cubin_tmp = utils.change_ext(fn_cuasm, "cubin_tmp")
    if not cuasm.cuasm2cubin(fn_cuasm):
        return False
    patch_cubin(cubin_orig, cubin_new, cubin_tmp)
    utils.rename_file(cubin_tmp, cubin_new)
    return True

def patch_cubin(cubin_orig, cubin_new, cubin_out):
    replace_sections_data(cubin_orig, cubin_new, [".note.nv.tkinfo", ".note.nv.cuver"], cubin_out)

def cubin2cuasm(binname, asmname=None):
    if asmname is None:
        fbase, fext = os.path.splitext(binname)
        asmname = fbase + '.cuasm'
    cf = CubinFile(binname)
    cf.saveAsCuAsm(asmname)

def cuasm2cubin(asmname, binname=None):
    cap = CuAsmParser()
    cap.parse(asmname)
    if binname is None:
        fbase, fext = os.path.splitext(asmname)
        binname = fbase + '.cubin'
    cap.saveAsCubin(binname)

#########################################################################################################

class Elf64LE:
    ELF_HDR_FMT = "<16sHHIQQQIHHHHHH"
    SHDR_FMT = "<IIQQQQIIQQ"      # Elf64_Shdr
    PHDR_FMT = "<IIQQQQQQ"        # Elf64_Phdr

    ELF_HDR_SIZE = struct.calcsize(ELF_HDR_FMT)
    SHDR_SIZE = struct.calcsize(SHDR_FMT)
    PHDR_SIZE = struct.calcsize(PHDR_FMT)

    PT_LOAD = 1
    PT_NOTE = 4

    SHT_NOBITS = 8
    SHT_NOTE = 7

    def __init__(self, data: bytes):
        self.data = data
        self._parse_header()
        self.sections = self._parse_sections()
        self.phdrs = self._parse_phdrs()

    def _parse_header(self) -> None:
        if len(self.data) < self.ELF_HDR_SIZE:
            raise ValueError("File is too small to be ELF64.")

        (e_ident, e_type, e_machine, e_version,
         e_entry, e_phoff, e_shoff, e_flags,
         e_ehsize, e_phentsize, e_phnum,
         e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from(self.ELF_HDR_FMT, self.data, 0)

        if e_ident[0:4] != b"\x7fELF":
            raise ValueError("Not an ELF file (bad magic).")
        if e_ident[4] != 2:
            raise ValueError("Not ELF64 (EI_CLASS != 2).")
        if e_ident[5] != 1:
            raise ValueError("Not little-endian (EI_DATA != 1).")

        if e_shentsize != self.SHDR_SIZE:
            raise ValueError(f"Unexpected e_shentsize={e_shentsize}, expected {self.SHDR_SIZE}.")
        if e_phnum and e_phentsize != self.PHDR_SIZE:
            raise ValueError(f"Unexpected e_phentsize={e_phentsize}, expected {self.PHDR_SIZE}.")

        self.e_phoff = e_phoff
        self.e_phnum = e_phnum
        self.e_phentsize = e_phentsize

        self.e_shoff = e_shoff
        self.e_shnum = e_shnum
        self.e_shentsize = e_shentsize
        self.e_shstrndx = e_shstrndx

        if self.e_shoff == 0 or self.e_shnum == 0:
            raise ValueError("ELF has no section header table (e_shoff/e_shnum).")

    def _parse_sections(self) -> List[dict]:
        shoff = self.e_shoff
        shnum = self.e_shnum
        end = shoff + shnum * self.e_shentsize
        if end > len(self.data):
            raise ValueError("Section header table goes past end of file.")

        shdrs = []
        for i in range(shnum):
            off = shoff + i * self.e_shentsize
            (sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size,
             sh_link, sh_info, sh_addralign, sh_entsize) = struct.unpack_from(self.SHDR_FMT, self.data, off)

            shdrs.append({
                "index": i,
                "sh_name": sh_name,
                "sh_type": sh_type,
                "sh_flags": sh_flags,
                "sh_addr": sh_addr,
                "sh_offset": sh_offset,
                "sh_size": sh_size,
                "sh_link": sh_link,
                "sh_info": sh_info,
                "sh_addralign": sh_addralign,
                "sh_entsize": sh_entsize,
                "hdr_off": off,  # file offset of this section header entry
                "name": None,     # resolved later
            })

        # Resolve names via .shstrtab
        if not (0 <= self.e_shstrndx < len(shdrs)):
            raise ValueError("Invalid e_shstrndx.")
        shstr = shdrs[self.e_shstrndx]
        shstr_off = shstr["sh_offset"]
        shstr_size = shstr["sh_size"]
        if shstr_off + shstr_size > len(self.data):
            raise ValueError(".shstrtab is out of file bounds.")
        shstr_bytes = self.data[shstr_off: shstr_off + shstr_size]

        def get_cstr(buf: bytes, off: int) -> str:
            if off >= len(buf):
                return ""
            end0 = buf.find(b"\x00", off)
            if end0 == -1:
                end0 = len(buf)
            return buf[off:end0].decode("utf-8", "replace")

        for sh in shdrs:
            sh["name"] = get_cstr(shstr_bytes, sh["sh_name"])

        return shdrs

    def _parse_phdrs(self) -> List[dict]:
        if not self.e_phnum or not self.e_phoff:
            return []

        phoff = self.e_phoff
        end = phoff + self.e_phnum * self.e_phentsize
        if end > len(self.data):
            raise ValueError("Program header table goes past end of file.")

        phdrs = []
        for i in range(self.e_phnum):
            off = phoff + i * self.e_phentsize
            (p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align) = struct.unpack_from(
                self.PHDR_FMT, self.data, off
            )
            phdrs.append({
                "index": i,
                "p_type": p_type,
                "p_flags": p_flags,
                "p_offset": p_offset,
                "p_vaddr": p_vaddr,
                "p_paddr": p_paddr,
                "p_filesz": p_filesz,
                "p_memsz": p_memsz,
                "p_align": p_align,
                "hdr_off": off,
            })
        return phdrs

    def section_by_name(self, name: str) -> dict:
        for sh in self.sections:
            if sh["name"] == name:
                return sh
        raise KeyError(f"Section not found: {name}")

    @staticmethod
    def align_up(x: int, align: int) -> int:
        if align <= 1:
            return x
        return (x + (align - 1)) & ~(align - 1)


def _patch_sh_offset_and_size(buf: bytearray, sh_hdr_off: int, new_off: int, new_size: int) -> None:
    """Patch sh_offset/sh_size inside Elf64_Shdr."""
    # In Elf64_Shdr: sh_offset at +24, sh_size at +32
    struct.pack_into("<Q", buf, sh_hdr_off + 24, new_off)
    struct.pack_into("<Q", buf, sh_hdr_off + 32, new_size)


def _extend_segment_to_cover_range(buf: bytearray, phdrs: List[dict], want_type: int, rng_start: int, rng_end: int) -> None:
    """
    Extend one program header segment (PT_NOTE or PT_LOAD) so that [rng_start, rng_end) is inside it.
    If no matching segment exists, do nothing.
    """
    if not phdrs:
        return

    # Prefer a segment of want_type that already overlaps the original location (best guess).
    candidates = [p for p in phdrs if p["p_type"] == want_type]
    if not candidates:
        # Fallback to any PT_LOAD if requested type not found.
        if want_type != Elf64LE.PT_LOAD:
            candidates = [p for p in phdrs if p["p_type"] == Elf64LE.PT_LOAD]
        if not candidates:
            return

    # Choose the segment with the largest end (common "last segment" strategy).
    seg = max(candidates, key=lambda p: int(p["p_offset"] + p["p_filesz"]))

    seg_start = int(seg["p_offset"])
    seg_end = int(seg["p_offset"] + seg["p_filesz"])

    # If appended range is before segment start, we won't try to fix that here.
    if rng_start < seg_start:
        return

    new_filesz = max(seg_end, rng_end) - seg_start
    new_memsz = max(int(seg["p_memsz"]), new_filesz)

    # In Elf64_Phdr: p_filesz at +32, p_memsz at +40
    struct.pack_into("<Q", buf, seg["hdr_off"] + 32, new_filesz)
    struct.pack_into("<Q", buf, seg["hdr_off"] + 40, new_memsz)


def replace_sections_data(
    old_cubin: str | Path,
    new_cubin: str | Path,
    section_names: List[str],
    out_cubin: str | Path,
    *,
    allow_append: bool = True,
    update_sh_size: bool = True,
    extend_phdrs: bool = True,
) -> None:
    """
    Copy multiple sections' bytes from old_cubin into the same-named sections of new_cubin.
    Writes a single output file.

    Notes:
      - ELF64 little-endian only.
      - SHT_NOBITS sections are rejected (no bytes stored in file).
      - If a section doesn't fit, it is relocated to EOF (aligned) if allow_append=True.
      - If extend_phdrs=True, PT_NOTE/PT_LOAD is extended to include appended data.
    """
    old_cubin = Path(old_cubin)
    new_cubin = Path(new_cubin)
    out_cubin = Path(out_cubin)

    old_bytes = old_cubin.read_bytes()
    new_bytes = bytearray(new_cubin.read_bytes())

    old_elf = Elf64LE(old_bytes)
    new_elf = Elf64LE(bytes(new_bytes))  # parse once (we'll patch offsets in-place)

    for sec_name in section_names:
        old_sec = old_elf.section_by_name(sec_name)
        new_sec = new_elf.section_by_name(sec_name)

        if old_sec["sh_type"] == Elf64LE.SHT_NOBITS or new_sec["sh_type"] == Elf64LE.SHT_NOBITS:
            raise ValueError(f"{sec_name}: SHT_NOBITS has no file bytes to copy.")

        old_off = int(old_sec["sh_offset"])
        old_size = int(old_sec["sh_size"])
        new_off = int(new_sec["sh_offset"])
        new_size = int(new_sec["sh_size"])

        if old_off + old_size > len(old_bytes):
            raise ValueError(f"{sec_name}: old section data is out of bounds.")
        if new_off + new_size > len(new_bytes):
            raise ValueError(f"{sec_name}: new section data is out of bounds.")

        payload = old_bytes[old_off: old_off + old_size]

        # In-place overwrite if it fits
        if old_size <= new_size:
            new_bytes[new_off: new_off + old_size] = payload
            if old_size < new_size:
                # Keep deterministic padding.
                new_bytes[new_off + old_size: new_off + new_size] = b"\x00" * (new_size - old_size)

            if update_sh_size and old_size != new_size:
                _patch_sh_offset_and_size(new_bytes, int(new_sec["hdr_off"]), new_off, old_size)

            continue

        # Otherwise relocate to EOF
        if not allow_append:
            raise ValueError(
                f"{sec_name}: old section is larger (old={old_size}, new={new_size}). "
                f"Enable allow_append=True to relocate to EOF."
            )

        align = int(new_sec["sh_addralign"]) if int(new_sec["sh_addralign"]) else 1
        eof = len(new_bytes)
        new_off2 = Elf64LE.align_up(eof, align)
        if new_off2 > eof:
            new_bytes.extend(b"\x00" * (new_off2 - eof))
        new_bytes.extend(payload)

        if update_sh_size:
            _patch_sh_offset_and_size(new_bytes, int(new_sec["hdr_off"]), new_off2, old_size)
        else:
            # Still must update sh_offset if we relocated
            struct.pack_into("<Q", new_bytes, int(new_sec["hdr_off"]) + 24, new_off2)

        # Extend program headers to cover appended range (optional but often crucial)
        if extend_phdrs and new_elf.phdrs:
            is_note = (int(new_sec["sh_type"]) == Elf64LE.SHT_NOTE) or sec_name.startswith(".note.")
            want = Elf64LE.PT_NOTE if is_note else Elf64LE.PT_LOAD
            _extend_segment_to_cover_range(new_bytes, new_elf.phdrs, want, new_off2, new_off2 + old_size)
    out_cubin.write_bytes(new_bytes)







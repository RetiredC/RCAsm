(c) 2026, RetiredCoder (RC)



INTRODUCTION

Why ASM?
PTX is not powerful enough:
1. You still cannot control registers usage.
2. PTX does not provide all instructions, some of them can be really important if you are going to create really fast code.
3. There is no way to declare fast functions: if you define "inline" function, it's just including its code so main code grows every time when you call that function.  If it's not inline, calls are very slow.
4. There is no way to use uniform registers and instructions directly.
5. There is no way to specify control codes.
6. There is no good management for carry flags, also some carry-related instruction are missed.
7. You have to check what SASS is generated every time, spend time to convince compiler to make it as you want, etc.
As a result, often ASM is really faster if you know what you are doing.


RCAsm features:
- sm89 and sm120 support.
- variables for R, UR, P.
- asm functions (include/call).
- supports constants and math expressions.
- automatic kernels injection into .cuasm file.
- simple but convenient editor for asm sources.
- #IF #ELSEIF #ENDIF support.
- open source, written in Python.
- supports both Windows and Linux.



REQUIREMENTS

RCAsm uses modified cuAssembler to compile/decompile .cubin files of CUDA v12.8, credits to this guy: https://github.com/cloudcores/CuAssembler 
Make sure that you use CUDA v12.8, other versions are not supported! Though, of course, you can use any recent CUDA version to run compiled .cubin files.



SETUP

Install CUDA 12.8, Python and required components:
pip install -r requirements.txt

"defs.py" contains some constants related to current ASM project.
Also check "NVDISASM_PATH" in "config.py", it must contain correct path to "nvdisasm.exe" of CUDA v12.8.



SHORT TUTORIAL

First of all, learn SASS :)
Most instructions are here (but note there are many errors in bits offsets there), credits to this guy: https://kuterdinel.com/nv_isa_sm89/
RCAsm adds some sugar to SASS, but you must know SASS itself.
Use sample kernel from RCAsm to understand basic rules.


0. Projects

- RCAsm requires template (empty) kernel, so declare empty CUDA kernel in some .cu file and compile it with nvcc to get .cubin. Then use cuAsm to make .cuasm file which will be used by RCASm to embed real kernel there and then build real .cubin file. Check .bat files in sample kernel from RCAsm for details (a.bat/a.sh to create template .cubin, b.bat/b.sh to create template .cuasm)
- Every project can contain one or more .asm files in same folder, all names are global between all files.


1. Variables and constants

- You define variables in a function header, or as a parameter when you call a function with "inc_func", "call_func" or "include".
- Don't use digit(s) at the end of variables: "tempvar" name is good, "tmp5" is bad, because digits are used for register offsets, for example if tempvar=R50, tempvar1 means R51. 
- Inside of function you can use any names, but if you pass a variable from outside, that variable must begin with R if it's register, UR if it's uniform register, 
P if it's predicate, C if it's const.
- Don't forget about register alignment requirements when you assign registers. Also remember that R255 is RZ (URZ is 63, even for sm_120 because of limited support) and you cannot use R253 and R254.
- Kernel parameters are passed in constant buffer #0 at some offset (this offset is different for sm_89 and sm_120), check samples for details.
- Declare constants with CONST keyword. They can contain other constants. All constants are global for project. Constants can be used only in expressions.


2. Kernels and functions

- Declare kernels with KERNEL keyword and function with FUNCTION.
- nested functions are not fully supported.
- "call_func" generates BRXU to jump to a function and another BRXU to return. If same function is called twice with different parameters, two versions of the function will be generated.
- "inc_func" and "include" include a function body directly, but the function cannot use caller's variables directly if you use "inc_func", you must pass all variables as parameters.


3. Expressions

- use {} for expressions, for example: MOV SomeVar, {(SOME_CONST >> 2) + 0x100 / 4}


4. Labels

- use ".some_label:" to declare "some_label" label.
- labels are unique for every function, therefore you cannot use some external label in a function.


5. Conditional compilation directives

- Example: 

#IF some_condition
//..some code
#ELSE
//..some code
#ENDIF

- nested directives are supported.
- Use "SM_VER" constant to detect current generation: #IF {SM_VER} == 89



LIMITATIONS

- RCAsm has some minor issues, I made this tool for myself and I'm happy with it, it was used to create rather complex kernels, but it can be too weak or buggy for you, don’t use it then :)
- Only sm89 and sm120 are supported currently, though it’s not difficult to add sm86 and older.
- cuAsm does not support all instructions, RCAsm fixes it with "NewOpsHandler.py", but not completely. You can add new instructions there when needed.
- sm_120 has 255 unified registers, but RCAsm supports only 63 (as for sm_89) because cuAsm does not support new UR range. When you use "URZ", UR63 is used, so make sure that you call UMOV UR63, 0x00 at the very beginning of your kernel and don't write anything to URZ.











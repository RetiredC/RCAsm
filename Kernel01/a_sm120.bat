#!/bin/bash

"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin\nvcc.exe" -arch=sm_120 -O3 -cubin kernel.cu -o kernel_sm120.cubin
copy /y "kernel_sm120.cubin" "kernel_sm120.cubin_orig"
PAUSE

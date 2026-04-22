nvcc -arch=sm_120 -O3 -cubin kernel.cu -o kernel_sm120.cubin
cp -f "kernel_sm120.cubin" "kernel_sm120.cubin_orig"

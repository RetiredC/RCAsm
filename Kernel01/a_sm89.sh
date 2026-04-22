#!/bin/bash

nvcc -arch=sm_89 -O3 -cubin kernel.cu -o kernel_sm89.cubin


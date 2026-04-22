#!/bin/bash

export PYTHONPATH="../cuAssembler"
python3 ../cuAssembler/bin/cuasm.py kernel_sm120.cubin kernel_sm120.cuasm


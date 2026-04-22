#!/bin/bash

export PYTHONPATH="../cuAssembler"
python3 ../cuAssembler/bin/cuasm.py kernel_sm89.cubin kernel_sm89.cuasm


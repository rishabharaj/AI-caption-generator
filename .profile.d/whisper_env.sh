#!/bin/bash
# Set Whisper model cache to a writable directory on Heroku
export WHISPER_CACHE_DIR="/app/.whisper_cache"
export XDG_CACHE_HOME="/app/.whisper_cache"
# Force CPU-only mode (no CUDA)
export CUDA_VISIBLE_DEVICES=""
# Optimize PyTorch for CPU inference
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export NUMEXPR_NUM_THREADS=2

#!/bin/bash
set -e

# Core build only: PyMuPDF4LLM + Docling. Heavy/copyleft engines are excluded
# in build.spec and should be installed separately by users when needed.
uv sync --extra pymupdf --extra docling
uv pip install pyinstaller
uv pip install --reinstall --index-url https://download.pytorch.org/whl/cpu torch==2.10.0+cpu torchvision==0.25.0+cpu
uv pip uninstall cuda-bindings cuda-pathfinder nvidia-cublas-cu12 nvidia-cuda-cupti-cu12 nvidia-cuda-nvrtc-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12 nvidia-cufile-cu12 nvidia-curand-cu12 nvidia-cusolver-cu12 nvidia-cusparse-cu12 nvidia-cusparselt-cu12 nvidia-nccl-cu12 nvidia-nvjitlink-cu12 nvidia-nvshmem-cu12 nvidia-nvtx-cu12 triton || true
uv run pyinstaller build.spec --clean
echo "Binary dostępne w dist/"

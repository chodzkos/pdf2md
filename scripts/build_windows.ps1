Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Run this script on Windows. PyInstaller does not produce reliable Windows
# executables from Linux/macOS, so use a Windows host or the GitHub Actions
# release workflow.
#
# Tesseract for Windows:
#   - Chocolatey: choco install tesseract
#   - Installer: https://github.com/UB-Mannheim/tesseract/wiki
#
# Poppler for Windows:
#   - Chocolatey: choco install poppler
#   - Releases: https://github.com/oschwartz10612/poppler-windows/releases
#
# Adapters that call external binaries must locate them with shutil.which().
# This matters for MinerU on Windows because the executable can resolve to
# mineru.exe, mineru.cmd or another launcher shim.

uv sync --extra pymupdf --extra docling
uv pip install pyinstaller
uv pip install --reinstall --index-url https://download.pytorch.org/whl/cpu torch==2.10.0+cpu torchvision==0.25.0+cpu
uv pip uninstall cuda-bindings cuda-pathfinder nvidia-cublas-cu12 nvidia-cuda-cupti-cu12 nvidia-cuda-nvrtc-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12 nvidia-cufile-cu12 nvidia-curand-cu12 nvidia-cusolver-cu12 nvidia-cusparse-cu12 nvidia-cusparselt-cu12 nvidia-nccl-cu12 nvidia-nvjitlink-cu12 nvidia-nvshmem-cu12 nvidia-nvtx-cu12 triton
if ($LASTEXITCODE -ne 0) {
    Write-Host "CUDA packages already absent; continuing."
}
uv run pyinstaller build.spec --clean
Write-Host "Binary dostępne w dist/"

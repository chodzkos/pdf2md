"""Globalne ustawienia testów ustawiane przed importem ciężkich silników."""

import os

os.environ.setdefault("PDFTEXT_WORKERS", "1")
os.environ.setdefault("TORCH_DEVICE", "cpu")

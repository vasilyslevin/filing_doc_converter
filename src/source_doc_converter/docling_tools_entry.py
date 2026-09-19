import sys

RUNTIME_CHECK_FLAG = "--runtime-check"


def run_runtime_check() -> int:
    import importlib

    import torch
    import torchvision
    from docling.document_converter import DocumentConverter
    from pypdf import PdfReader
    from scipy import ndimage
    from transformers import AutoImageProcessor

    array_api_module = None
    for module_name in (
        "scipy._external.array_api_compat.numpy.fft",
        "scipy._lib.array_api_compat.numpy.fft",
    ):
        try:
            importlib.import_module(module_name)
            array_api_module = module_name
            break
        except ModuleNotFoundError:
            continue
    if array_api_module is None:
        raise ModuleNotFoundError(
            "No SciPy array API compatibility FFT module found in runtime."
        )

    filtered = ndimage.gaussian_filter1d([1.0, 2.0, 3.0], sigma=0.1)
    if len(filtered) != 3:
        raise RuntimeError("SciPy ndimage runtime check returned an unexpected result.")
    if not torchvision.extension._has_ops():
        raise RuntimeError(
            "Torchvision native operators are unavailable in this runtime; "
            "packaged _C.pyd or dependent DLLs may be missing."
        )

    print(f"Torch: {torch.__version__}")
    print(f"Torchvision: {torchvision.__version__}")
    print(f"AutoImageProcessor: {AutoImageProcessor.__name__}")
    print(f"DocumentConverter: {DocumentConverter.__name__}")
    print(f"PdfReader: {PdfReader.__name__}")
    print(f"SciPyArrayAPI: {array_api_module}")
    return 0


def main() -> int:
    if RUNTIME_CHECK_FLAG in sys.argv:
        return run_runtime_check()

    from docling.cli.tools import app

    app(prog_name="docling-tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

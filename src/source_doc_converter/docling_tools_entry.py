import sys

RUNTIME_CHECK_FLAG = "--runtime-check"


def run_runtime_check() -> int:
    from docling.document_converter import DocumentConverter
    from pypdf import PdfReader
    from transformers import AutoImageProcessor

    print(f"AutoImageProcessor: {AutoImageProcessor.__name__}")
    print(f"DocumentConverter: {DocumentConverter.__name__}")
    print(f"PdfReader: {PdfReader.__name__}")
    return 0


def main() -> int:
    if RUNTIME_CHECK_FLAG in sys.argv:
        return run_runtime_check()

    from docling.cli.tools import app

    app(prog_name="docling-tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import os
import sys
from pathlib import Path

import torch

_DLL_DIRECTORY_HANDLES = []


def _load_torchvision_extension() -> None:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    candidates = sorted(bundle_root.rglob("_C*.pyd"))
    extensions = [path for path in candidates if path.parent.name == "torchvision"]
    if not extensions:
        raise RuntimeError("Packaged torchvision native extension _C.pyd was not found.")

    extension = extensions[0]
    dll_directories = (extension.parent, bundle_root / "torch" / "lib")
    if hasattr(os, "add_dll_directory"):
        for directory in dll_directories:
            if directory.is_dir():
                _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(directory)))

    try:
        torch.ops.load_library(str(extension))
    except Exception as error:
        raise RuntimeError(
            f"Could not load packaged torchvision native extension: {extension}"
        ) from error


_load_torchvision_extension()

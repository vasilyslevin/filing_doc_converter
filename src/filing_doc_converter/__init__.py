import importlib
import sys
import warnings

warnings.warn(
    "'filing_doc_converter' is deprecated and will be removed in a future release; "
    "use 'source_doc_converter' instead.",
    DeprecationWarning,
    stacklevel=2,
)

_module = importlib.import_module("source_doc_converter")
sys.modules[__name__] = _module

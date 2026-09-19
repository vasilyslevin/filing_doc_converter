import warnings

from source_doc_converter.app import main

warnings.warn(
    "python -m filing_doc_converter is deprecated; use python -m source_doc_converter instead.",
    DeprecationWarning,
    stacklevel=2,
)

if __name__ == "__main__":
    raise SystemExit(main())

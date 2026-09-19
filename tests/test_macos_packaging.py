import pytest

from source_doc_converter.macos_packaging import (
    build_macos_bundle_metadata,
    normalize_macos_architecture,
)


def test_architecture_aliases_are_normalized() -> None:
    assert normalize_macos_architecture("arm64") == "arm64"
    assert normalize_macos_architecture("aarch64") == "arm64"


def test_unsupported_architecture_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported macOS architecture"):
        normalize_macos_architecture("x86_64")


def test_bundle_metadata_uses_source_document_converter_identity() -> None:
    metadata = build_macos_bundle_metadata(version="0.1.0a0", architecture="arm64")

    assert metadata.bundle_name == "Source Document Converter"
    assert metadata.executable_name == "SourceDocumentConverter"
    assert metadata.bundle_identifier == "com.source.document.converter"

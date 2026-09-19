#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/build/macos}"
ARCH="${ARCH:-$(uname -m)}"
MIN_MACOS_VERSION="${MIN_MACOS_VERSION:-12.0}"
PYTHON_BIN="${PYTHON_BIN:-python}"
APP_NAME="Source Document Converter.app"
EXECUTABLE_NAME="SourceDocumentConverter"
DIST_DIR="$OUTPUT_DIR/dist"
WORK_DIR="$OUTPUT_DIR/work"
SPEC_DIR="$OUTPUT_DIR/spec"
ICON_PATH="$OUTPUT_DIR/SourceDocumentConverter.icns"
ICON_SOURCE="$REPO_ROOT/src/source_doc_converter/assets/app_icon.svg"
GUI_ENTRY="$SCRIPT_DIR/SourceDocumentConverter.py"
TOOLS_ENTRY="$SCRIPT_DIR/docling-tools.py"
OCR_ENTRY="$REPO_ROOT/src/source_doc_converter/ocrmypdf_entry.py"
PACKAGE_NOTES="$SCRIPT_DIR/PACKAGING_NOTES.txt"

case "$ARCH" in
  arm64|x86_64) ;;
  aarch64) ARCH="arm64" ;;
  amd64) ARCH="x86_64" ;;
  *) echo "Unsupported architecture: $ARCH" >&2; exit 2 ;;
esac

rm -rf "$OUTPUT_DIR"
mkdir -p "$DIST_DIR" "$WORK_DIR" "$SPEC_DIR"

"$PYTHON_BIN" "$SCRIPT_DIR/create_icns.py" "$ICON_SOURCE" "$ICON_PATH"

COMMON_ARGS=(
  -m PyInstaller
  --noconfirm
  --clean
  --onedir
  "--target-architecture=$ARCH"
  "--paths=$REPO_ROOT/src"
  "--distpath=$DIST_DIR"
  "--specpath=$SPEC_DIR"
  "--osx-bundle-identifier=com.source.document.converter"
)

DOCLING_ARGS=(
  --collect-all=docling
  --collect-all=docling_core
  --collect-all=docling_parse
  --collect-all=rapidocr
  --collect-all=transformers
  --hidden-import=docling.cli.tools
  --hidden-import=docling.document_converter
)

"$PYTHON_BIN" "${COMMON_ARGS[@]}" "${DOCLING_ARGS[@]}" \
  "--workpath=$WORK_DIR/$EXECUTABLE_NAME" \
  "--name=$EXECUTABLE_NAME" \
  "--windowed" \
  "--icon=$ICON_PATH" \
  "--add-data=$REPO_ROOT/src/source_doc_converter/assets/app_icon.svg:source_doc_converter/assets" \
  "$GUI_ENTRY"

"$PYTHON_BIN" "${COMMON_ARGS[@]}" "${DOCLING_ARGS[@]}" \
  "--workpath=$WORK_DIR/docling-tools" \
  --name=docling-tools \
  --console \
  "$TOOLS_ENTRY"

"$PYTHON_BIN" "${COMMON_ARGS[@]}" \
  --collect-all=ocrmypdf \
  --hidden-import=ocrmypdf.__main__ \
  "--workpath=$WORK_DIR/ocrmypdf" \
  --name=ocrmypdf \
  --console \
  "$OCR_ENTRY"

APP_DIR="$DIST_DIR/$EXECUTABLE_NAME.app"
if [[ ! -d "$APP_DIR" ]]; then
  echo "PyInstaller did not produce $EXECUTABLE_NAME.app" >&2
  exit 1
fi
RENAMED_APP_DIR="$DIST_DIR/$APP_NAME"
mv "$APP_DIR" "$RENAMED_APP_DIR"
APP_DIR="$RENAMED_APP_DIR"

cp "$DIST_DIR/docling-tools/docling-tools" "$APP_DIR/Contents/MacOS/docling-tools"
cp "$DIST_DIR/ocrmypdf/ocrmypdf" "$APP_DIR/Contents/MacOS/ocrmypdf"
rm -rf "$DIST_DIR/docling-tools" "$DIST_DIR/ocrmypdf"

cp "$REPO_ROOT/LICENSE" "$APP_DIR/Contents/Resources/LICENSE"
cp "$REPO_ROOT/THIRD_PARTY_NOTICES.md" "$APP_DIR/Contents/Resources/THIRD_PARTY_NOTICES.md"
cp "$PACKAGE_NOTES" "$APP_DIR/Contents/Resources/PACKAGING_NOTES.txt"

PLIST="$APP_DIR/Contents/Info.plist"
set_or_add_plist() {
  local key="$1"
  local type="$2"
  local value="$3"
  /usr/libexec/PlistBuddy -c "Set :$key $value" "$PLIST" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Add :$key $type $value" "$PLIST"
}

set_or_add_plist "CFBundleDisplayName" "string" "Source Document Converter"
set_or_add_plist "CFBundleName" "string" "Source Document Converter"
set_or_add_plist "CFBundleExecutable" "string" "$EXECUTABLE_NAME"
set_or_add_plist "LSMinimumSystemVersion" "string" "$MIN_MACOS_VERSION"
/usr/libexec/PlistBuddy -c "Delete :LSArchitecturePriority" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :LSArchitecturePriority array" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :LSArchitecturePriority:0 string $ARCH" "$PLIST"

codesign --force --deep --sign - "$APP_DIR"
codesign --verify --deep --strict "$APP_DIR"

(
  cd "$DIST_DIR"
  ZIP_NAME="SourceDocumentConverter-macOS-$ARCH.zip"
  ditto -c -k --sequesterRsrc --keepParent "$APP_NAME" "$ZIP_NAME"
  shasum -a 256 "$ZIP_NAME" > "$ZIP_NAME.sha256"
)

if command -v hdiutil >/dev/null 2>&1; then
  DMG_NAME="SourceDocumentConverter-macOS-$ARCH.dmg"
  hdiutil create -volname "Source Document Converter ($ARCH)" \
    -srcfolder "$APP_DIR" \
    -ov -format UDZO "$DIST_DIR/$DMG_NAME"
  shasum -a 256 "$DIST_DIR/$DMG_NAME" > "$DIST_DIR/$DMG_NAME.sha256"
fi

echo "Created macOS build at $APP_DIR"

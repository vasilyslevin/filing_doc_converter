#!/usr/bin/env bash
set -euo pipefail

APP_PATH="${1:?app path required}"
ARCH="${2:?arch required}"

required_vars=(MACOS_CERT_BASE64 MACOS_CERT_PASSWORD MACOS_SIGNING_IDENTITY APPLE_API_KEY_ID APPLE_API_ISSUER_ID APPLE_API_PRIVATE_KEY_BASE64)
missing=()
for key in "${required_vars[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    missing+=("$key")
  fi
done

if [[ "${#missing[@]}" -gt 0 ]]; then
  echo "Skipping Developer ID signing/notarization: missing required secrets (${#missing[@]} values)." >&2
  exit 0
fi

KEYCHAIN_PATH="$RUNNER_TEMP/source-doc-converter-signing.keychain-db"
CERT_PATH="$RUNNER_TEMP/source-doc-converter-signing.p12"
API_KEY_PATH="$RUNNER_TEMP/AuthKey_${APPLE_API_KEY_ID}.p8"
PROFILE_NAME="SourceDocumentConverter-notarytool"

echo "$MACOS_CERT_BASE64" | base64 --decode > "$CERT_PATH"
echo "$APPLE_API_PRIVATE_KEY_BASE64" | base64 --decode > "$API_KEY_PATH"

security create-keychain -p "$MACOS_CERT_PASSWORD" "$KEYCHAIN_PATH"
security set-keychain-settings -lut 21600 "$KEYCHAIN_PATH"
security unlock-keychain -p "$MACOS_CERT_PASSWORD" "$KEYCHAIN_PATH"
security import "$CERT_PATH" -k "$KEYCHAIN_PATH" -P "$MACOS_CERT_PASSWORD" -T /usr/bin/codesign
security list-keychains -d user -s "$KEYCHAIN_PATH"

codesign --force --deep --options runtime --sign "$MACOS_SIGNING_IDENTITY" "$APP_PATH"
codesign --verify --deep --strict "$APP_PATH"

ZIP_PATH="$(dirname "$APP_PATH")/SourceDocumentConverter-macOS-$ARCH-signed.zip"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"

xcrun notarytool store-credentials "$PROFILE_NAME" \
  --key "$API_KEY_PATH" \
  --key-id "$APPLE_API_KEY_ID" \
  --issuer "$APPLE_API_ISSUER_ID"

xcrun notarytool submit "$ZIP_PATH" --keychain-profile "$PROFILE_NAME" --wait
xcrun stapler staple "$APP_PATH"
codesign --verify --deep --strict "$APP_PATH"

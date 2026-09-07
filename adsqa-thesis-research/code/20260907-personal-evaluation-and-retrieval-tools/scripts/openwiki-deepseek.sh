#!/bin/zsh
# Run OpenWiki through DeepSeek's Anthropic-compatible API on this Mac.

set -euo pipefail

if [[ -z "${OPENAI_COMPATIBLE_API_KEY:-}" ]]; then
  OPENAI_COMPATIBLE_API_KEY=$(launchctl getenv OPENAI_COMPATIBLE_API_KEY 2>/dev/null || true)
  export OPENAI_COMPATIBLE_API_KEY
fi

if [[ -z "${OPENAI_COMPATIBLE_API_KEY:-}" ]]; then
  print -u2 "OPENAI_COMPATIBLE_API_KEY is not configured. Re-run the DeepSeek key setup first."
  exit 1
fi

tmp_ca=$(mktemp /tmp/openwiki-macos-ca.XXXXXX.pem)
cleanup() {
  rm -f "$tmp_ca"
}
trap cleanup EXIT

umask 077
security find-certificate -a -p "$HOME/Library/Keychains/login.keychain-db" >> "$tmp_ca" 2>/dev/null || true
security find-certificate -a -p /Library/Keychains/System.keychain >> "$tmp_ca" 2>/dev/null || true
security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain >> "$tmp_ca" 2>/dev/null || true

export PATH="/Users/bytedance/.npm-global/bin:/opt/homebrew/bin:$PATH"
unset NODE_TLS_REJECT_UNAUTHORIZED
export NODE_EXTRA_CA_CERTS="$tmp_ca"
export OPENWIKI_TELEMETRY_DISABLED=1
export OPENWIKI_PROVIDER=anthropic
export OPENWIKI_MODEL_ID=deepseek-v4-flash
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_API_KEY="$OPENAI_COMPATIBLE_API_KEY"

cd "${0:A:h:h}"
openwiki code "$@"

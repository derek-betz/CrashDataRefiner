#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_root="$repo_root/output/playwright"
session_name="${PWCLI_SESSION:-default}"
default_url="${CDR_PLAYWRIGHT_URL:-http://127.0.0.1:8081}"

export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PWCLI="${PWCLI:-$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh}"

usage() {
  cat <<'EOF'
Usage:
  scripts/playwright_skill_audit.sh open [url]
  scripts/playwright_skill_audit.sh desktop
  scripts/playwright_skill_audit.sh mobile
  scripts/playwright_skill_audit.sh capture <label>
  scripts/playwright_skill_audit.sh close

Environment:
  PWCLI_SESSION        Playwright CLI session name. Default: default
  CDR_PLAYWRIGHT_URL   App URL used by `open`. Default: http://127.0.0.1:8081

Examples:
  scripts/playwright_skill_audit.sh open
  scripts/playwright_skill_audit.sh desktop
  scripts/playwright_skill_audit.sh capture initial-load
  scripts/playwright_skill_audit.sh mobile
  scripts/playwright_skill_audit.sh capture mobile-results
EOF
}

require_pwcli() {
  if ! command -v npx >/dev/null 2>&1; then
    echo "npx is required for the Playwright skill wrapper." >&2
    exit 1
  fi
  if [[ ! -x "$PWCLI" ]]; then
    echo "Playwright skill wrapper not found at $PWCLI" >&2
    exit 1
  fi
}

run_pwcli() {
  "$PWCLI" --session "$session_name" "$@"
}

copy_session_artifacts() {
  local dest="$1"
  local session_dir="$repo_root/.playwright-cli"
  if [[ -d "$session_dir" ]]; then
    mkdir -p "$dest/playwright-cli"
    cp -R "$session_dir/." "$dest/playwright-cli/"
  fi
}

open_browser() {
  local url="${1:-$default_url}"
  mkdir -p "$artifact_root"
  "$PWCLI" open "$url" --headed | tee "$artifact_root/open.txt"
}

capture_artifacts() {
  local label="${1:-}"
  if [[ -z "$label" ]]; then
    echo "capture requires a label" >&2
    exit 1
  fi
  local capture_dir="$artifact_root/$label"
  mkdir -p "$capture_dir"
  run_pwcli snapshot --filename "$capture_dir/snapshot.md"
  run_pwcli screenshot --filename "$capture_dir/screenshot.png" --full-page
  run_pwcli console error > "$capture_dir/console-error.txt"
  run_pwcli network > "$capture_dir/network.txt"
  copy_session_artifacts "$capture_dir"
  echo "Captured Playwright artifacts in $capture_dir"
}

main() {
  require_pwcli
  mkdir -p "$artifact_root"

  local command="${1:-}"
  case "$command" in
    open)
      shift
      open_browser "${1:-$default_url}"
      ;;
    desktop)
      run_pwcli resize 1440 900
      ;;
    mobile)
      run_pwcli resize 390 844
      ;;
    capture)
      shift
      capture_artifacts "${1:-}"
      ;;
    close)
      run_pwcli close
      ;;
    ""|-h|--help|help)
      usage
      ;;
    *)
      echo "Unknown command: $command" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"

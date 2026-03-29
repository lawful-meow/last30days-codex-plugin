#!/bin/bash
set -euo pipefail

# Check if last30days has any configuration source available.
# Priority: .codex/last30days.env > .claude/last30days.env > ~/.config/last30days/.env > env vars

CODEX_PROJECT_ENV=".codex/last30days.env"
CLAUDE_PROJECT_ENV=".claude/last30days.env"
GLOBAL_ENV="$HOME/.config/last30days/.env"

# Helper: warn if file permissions are too open
check_perms() {
  local file="$1"
  if [[ ! -f "$file" ]]; then return; fi
  local perms
  perms=$(stat -f '%Lp' "$file" 2>/dev/null || stat -c '%a' "$file" 2>/dev/null || echo "")
  if [[ -n "$perms" && "$perms" != "600" && "$perms" != "400" ]]; then
    echo "/last30days: WARNING — $file has permissions $perms (should be 600)."
    echo "  Fix: chmod 600 $file"
  fi
}

# Check per-project config
if [[ -f "$CODEX_PROJECT_ENV" ]]; then
  check_perms "$CODEX_PROJECT_ENV"
  exit 0
fi

if [[ -f "$CLAUDE_PROJECT_ENV" ]]; then
  check_perms "$CLAUDE_PROJECT_ENV"
  exit 0
fi

# Check global config
if [[ -f "$GLOBAL_ENV" ]]; then
  check_perms "$GLOBAL_ENV"
  exit 0
fi

# Check if OPENAI_API_KEY is set in environment (minimum requirement)
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  exit 0
fi

# Check if SCRAPECREATORS_API_KEY is set (also sufficient)
if [[ -n "${SCRAPECREATORS_API_KEY:-}" ]]; then
  exit 0
fi

# No config found — inform user
cat <<'EOF'
/last30days: No API keys configured.

Create .codex/last30days.env with your API keys, or use
.claude/last30days.env for compatibility, or create
~/.config/last30days/.env globally. At minimum,
SCRAPECREATORS_API_KEY or OPENAI_API_KEY is required.
EOF

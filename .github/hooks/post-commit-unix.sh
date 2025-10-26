#!/usr/bin/env bash
# Omega_KG Universal Post-Commit Hook
# Auto-detects environment (Git Bash/WSL2/Linux) and logs to Obsidian

set -euo pipefail

# Detect session log path
if [[ -n "${OMEGA_VAULT:-}" ]]; then
    SESSION_LOG="$OMEGA_VAULT/Sessions/$(date +%Y-%m-%d).md"
elif [[ -n "${OMEGA_VAULT_WIN:-}" ]]; then
    # Windows path conversion
    SESSION_LOG="${OMEGA_VAULT_WIN//\\//}/Sessions/$(date +%Y-%m-%d).md"
else
    # Fallback: Try to find vault in common locations
    # Enable nullglob to avoid literal non-matching patterns
    shopt -s nullglob
    for path in \
        "$HOME/Documents/OmegaVault.as" \
        /mnt/c/Users/*/Documents/OmegaVault.as \
        "$USERPROFILE/Documents/OmegaVault.as"
    do
        if [[ -d "$path" ]]; then
            SESSION_LOG="$path/Sessions/$(date +%Y-%m-%d).md"
            break
        fi
    done
    # Restore nullglob setting
    shopt -u nullglob
fi

# Abort if no session log found
if [[ -z "${SESSION_LOG:-}" ]] || [[ ! -f "$SESSION_LOG" ]]; then
    # Silent failure - don't block commits
    exit 0
fi

# Capture commit metadata
COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)
REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")
TIMESTAMP=$(date +%H:%M:%S)
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Extract Linear issue ID (supports multiple formats)
LINEAR_ID=$(echo "$COMMIT_MSG" | grep -oP '(LIN-\d+|#\d+)' | head -1 || echo "")

# Extract file changes with stats
FILES_CHANGED=$(git diff-tree --no-commit-id --name-status -r HEAD | head -10)
NUM_FILES=$(echo "$FILES_CHANGED" | wc -l)

# Detect commit type (conventional commits)
COMMIT_TYPE=$(echo "$COMMIT_MSG" | grep -oP '^(feat|fix|docs|style|refactor|test|chore|perf|ci|build)' || echo "change")

# Build markdown entry with semantic richness
ENTRY="
#### [$TIMESTAMP] 🔨 Commit: \`$COMMIT_HASH\` [$REPO_NAME]
**Branch:** \`$BRANCH\` | **Type:** \`$COMMIT_TYPE\` | **Files:** $NUM_FILES"

# Add Linear link if present
if [[ -n "$LINEAR_ID" ]]; then
    ENTRY="$ENTRY | **Linear:** [[$LINEAR_ID]]"
fi

ENTRY="$ENTRY

\`\`\`
$COMMIT_MSG
\`\`\`

<details>
<summary>Changed files</summary>

\`\`\`
$FILES_CHANGED
\`\`\`

</details>
"

# Atomic append (prevents race conditions if multiple commits happen simultaneously)
{
    flock -x 200
    echo "$ENTRY" >> "$SESSION_LOG"
} 200>"$SESSION_LOG.lock"

# Cleanup lock file
rm -f "$SESSION_LOG.lock"

exit 0

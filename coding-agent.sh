#!/usr/bin/env bash
# =============================================================================
# sdd-loop.sh — Spec-Driven Development agent loop (pi-agent framework)
# =============================================================================
set -euo pipefail

PROJECT_DIR="${1:-$(pwd)}"
AGENTS_DIR="$PROJECT_DIR/.pi/agents"
ORIENTATION="$AGENTS_DIR/orientation.md"
INTROSPECTION="$AGENTS_DIR/introspection.md"
IMPLEMENTATION="$AGENTS_DIR/implementation.md"
STATE_FILE="$PROJECT_DIR/WORKFLOW_STATE.md"
SPEC_FILE="$PROJECT_DIR/SPEC.md"
CODING_GUIDELINES="$PROJECT_DIR/.pi/CODING_GUIDELINES.md"
TRANSITION_PAUSE=2

# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------


for f in "$ORIENTATION" "$INTROSPECTION" "$IMPLEMENTATION"; do
    if [[ ! -f "$f" ]]; then
        echo "ERROR: Agent file not found: $f"
        exit 1
    fi
done

cd "$PROJECT_DIR"

APPEND_FLAG=()
if [[ -f "$CODING_GUIDELINES" ]]; then
    APPEND_FLAG=(--append-system-prompt "$(cat "$CODING_GUIDELINES")")
    echo "  ✓ CODING_GUIDELINES.md found"
fi

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

banner() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "  Step %-3s  %s\n" "$1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

run_agent() {
    pi "start!" --system-prompt "$1" --append-system-prompt "$CODING_GUIDELINES"
    echo ""
}

ask_continue() {
    read -rp "  Continue to the next step? [Y/n]  " answer
    echo ""
}

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------

echo ""
echo "  SDD Loop — $PROJECT_DIR"
echo ""

if [[ ! -f "$SPEC_FILE" ]]; then
    banner "ORIENTATION  (initial)"
    pi --system-prompt "$ORIENTATION"
fi

while true; do
    banner "ORIENTATION  (re-orient)"
    run_agent "$ORIENTATION"
    
    banner "IMPLEMENTATION"
    run_agent "$IMPLEMENTATION"

    echo "  Starting introspection in ${TRANSITION_PAUSE}s..."
    sleep "$TRANSITION_PAUSE"

    banner "INTROSPECTION"
    run_agent "$INTROSPECTION"

    echo ""
    ask_continue
done

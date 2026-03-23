#!/usr/bin/env bash
# check-permissions.sh — Verify macOS permissions for macos-control-cli

echo "🔍 Checking macOS permissions..."
echo ""

# 1. Screen Recording
TMP_IMG="/tmp/_permission_check_$$.png"
/usr/sbin/screencapture -x "$TMP_IMG" 2>/dev/null
if [[ -f "$TMP_IMG" ]]; then
    SIZE=$(wc -c < "$TMP_IMG")
    rm -f "$TMP_IMG"
    if [[ "$SIZE" -gt 1000 ]]; then
        echo "✅ Screen Recording — granted"
    else
        echo "❌ Screen Recording — image empty (permission likely denied)"
        echo "   → System Settings → Privacy & Security → Screen Recording → add Terminal"
    fi
else
    echo "❌ Screen Recording — screencapture failed"
    echo "   → System Settings → Privacy & Security → Screen Recording → add Terminal"
fi

# 2. Accessibility (cliclick)
CLICLICK="/opt/homebrew/bin/cliclick"
if [[ ! -f "$CLICLICK" ]]; then
    echo "❌ cliclick not found at $CLICLICK"
    echo "   → brew install cliclick"
else
    # Try a no-op mouse move and check exit code
    "$CLICLICK" m:1,1 2>/dev/null
    if [[ $? -eq 0 ]]; then
        echo "✅ Accessibility (cliclick) — granted"
    else
        echo "❌ Accessibility (cliclick) — permission denied"
        echo "   → System Settings → Privacy & Security → Accessibility → add Terminal + cliclick"
    fi
fi

echo ""

# Summary
echo "──────────────────────────────────────"
echo "✅ All permissions granted — ready to use"

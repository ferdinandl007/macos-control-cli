# macOS Permissions Setup

`macos-control-cli` requires two macOS permissions to work. Both must be granted manually — macOS does not allow apps to grant themselves these permissions.

---

## 1. Screen Recording

Required for `screencapture` to capture the display.

**How to grant:**

1. Open **System Settings** → **Privacy & Security** → **Screen Recording**
2. Click **+** and add **Terminal** (or whichever app runs your scripts — iTerm2, Warp, etc.)
3. If you run via a Python venv, you may also need to add **Python** directly
4. Toggle it **on**
5. Restart the terminal

**To verify it's working:**
```bash
/usr/sbin/screencapture -x /tmp/test.png && echo "✅ Screen recording works" || echo "❌ Permission denied"
```

---

## 2. Accessibility (Mouse & Keyboard Control)

Required for `cliclick` to move the mouse and send keystrokes.

**How to grant:**

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Click **+** and add **Terminal** (or iTerm2/Warp)
3. Toggle it **on**
4. You may also need to add `/opt/homebrew/bin/cliclick` directly

**To verify it's working:**
```bash
cliclick m:500,500 && echo "✅ Accessibility works" || echo "❌ Permission denied"
```

---

## 3. Quick Permission Check

Run this to verify both permissions are granted:

```bash
bash check-permissions.sh
```

---

## Troubleshooting

**Screen capture returns a blank/black image**
→ Screen Recording permission not granted for your terminal app. Go to System Settings → Privacy & Security → Screen Recording and add your terminal.

**cliclick has no effect or errors**
→ Accessibility permission not granted. Go to System Settings → Privacy & Security → Accessibility and add your terminal + cliclick.

**"Operation not permitted" errors**
→ Both permissions needed. Grant both and restart your terminal.

**Running in a background agent (e.g. OpenClaw cron)**
→ The process running the cron job needs the permissions, not just your terminal. Add the `node` binary or the OpenClaw process to both permission lists.
For OpenClaw: add `/opt/homebrew/opt/node@22/bin/node` to both Screen Recording and Accessibility.

---

## One-time setup checklist

- [ ] Terminal/iTerm2/Warp → Screen Recording: ON
- [ ] Terminal/iTerm2/Warp → Accessibility: ON  
- [ ] `/opt/homebrew/bin/cliclick` → Accessibility: ON
- [ ] (For OpenClaw agents) `node` binary → Screen Recording: ON
- [ ] (For OpenClaw agents) `node` binary → Accessibility: ON
- [ ] Run `bash check-permissions.sh` → both green

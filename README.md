# 🖥️ macOS Control CLI

**OmniParser v2 powered macOS desktop automation.** Take a screenshot, detect every UI element by label using local AI, then click, type, and scroll — in any app — with human-like or fast timing.

No Selenium. No AppleScript selectors. No hardcoded coordinates. Just describe what you want to click.

```bash
desktop-control focus "Google Chrome"
desktop-control click "Sign in"
desktop-control type "hello@example.com"
desktop-control key return
desktop-control verify "Dashboard"
```

---

## Modes

| Mode | Flag | Use case |
|------|------|----------|
| **Human** | *(default)* | Posting to Reddit, any site with bot detection — curved mouse, random delays, per-char typing |
| **Fast** | `--fast` | Internal tools, Gmail, Outlook, anything where speed > stealth |

```bash
desktop-control --fast click "Archive"    # ~0.8s — instant
desktop-control click "Post"              # ~2.4s — curved movement, human timing
```

---

## How it works

1. **Screenshot** — captures the full display via `screencapture`
2. **YOLOv8** — detects all icon/button bounding boxes
3. **Florence-2** — captions each element with a human-readable label
4. **easyOCR** — extracts all text regions
5. **cliclick** — executes mouse moves and keyboard input

Everything runs **100% locally** — no API calls, no cloud, no rate limits.

---

## Features

- 🔍 **Find any UI element by label** — fuzzy matching across 400+ detected elements
- 🖱️ **Human mouse movement** — curved path with random timing (or skip with `--fast`)
- ⌨️ **Human-like typing** — per-character random delays with pauses (or skip with `--fast`)
- 📐 **HiDPI/Retina aware** — auto-detects display scale (1x/2x), works on 4K displays
- 🪟 **Window/app focus** — bring any app to front, reuse existing tabs
- 🔗 **URL navigation** — navigate Chrome (or any browser) to a URL
- 📋 **Task runner** — multi-step automation from a JSON file
- ⚡ **Fast mode** — skip all simulation for internal automation
- 🤖 **OpenClaw compatible** — designed as an agent skill for [OpenClaw](https://openclaw.ai)

---

## Installation

### Requirements

- macOS (Apple Silicon recommended)
- Python 3.12
- [uv](https://github.com/astral-sh/uv)
- [cliclick](https://github.com/BlueM/cliclick) (`brew install cliclick`)

### Setup

```bash
git clone https://github.com/ferdinandl007/macos-control-cli.git
cd macos-control-cli
bash setup.sh
```

This will:
- Create a Python 3.12 venv at `~/.openclaw/tools/desktop-control/.venv`
- Install torch, ultralytics, transformers==4.49.0, easyocr, einops, timm
- Download OmniParser v2 models (~1.1 GB) from HuggingFace

### Add to PATH

```bash
ln -sf "$(pwd)/desktop-control.sh" ~/.local/bin/desktop-control
```

---

## CLI Usage

```bash
# Window management
desktop-control focus "Google Chrome"
desktop-control focus-url "https://example.com"
desktop-control focus-url "https://example.com" --app "Safari"
desktop-control active-app

# Screen detection
desktop-control screenshot [--output /tmp/screen.png]
desktop-control scan                    # detect all elements + labels
desktop-control scan --json             # JSON output

# Find elements
desktop-control find "Submit"           # fuzzy match, print coords

# Interaction — human mode (default)
desktop-control click "Submit"          # curved mouse, random delays
desktop-control type "hello world"      # per-char delays with pauses
desktop-control key return
desktop-control scroll down --amount 5

# Interaction — fast mode
desktop-control --fast click "Submit"   # direct click, no delay
desktop-control --fast type "hello"     # instant type

# Task automation
desktop-control run-task my-task.json
```

---

## Task JSON

Chain multiple actions in a JSON file:

```json
[
  {"action": "focus-url", "url": "https://example.com", "app": "Google Chrome"},
  {"action": "wait", "seconds": 3},
  {"action": "click", "query": "Log in"},
  {"action": "type", "text": "user@example.com"},
  {"action": "key", "key": "tab"},
  {"action": "type", "text": "password"},
  {"action": "key", "key": "return"},
  {"action": "verify", "query": "Dashboard", "timeout": 10}
]
```

Supported actions: `focus`, `focus-url`, `click`, `type`, `key`, `scroll`, `wait`, `verify`

---

## Python API

```python
import sys
sys.path.insert(0, '/path/to/macos-control-cli')
from desktop_control import DesktopControl

# Human mode (default) — for sites with bot detection
dc = DesktopControl()

# Fast mode — for internal tools
dc = DesktopControl(fast=True)

dc.focus("Google Chrome")
dc.focus_url("https://example.com")

elements = dc.find_all_elements()
# [{"label": "Sign in", "center_x": 960, "center_y": 540, "confidence": 0.92, ...}, ...]

dc.click_element("Sign in")
dc.type_text("hello@example.com")
dc.scroll("down", amount=3)
app = dc.get_focused_app()
```

---

## Performance

| Step | Time |
|------|------|
| Screenshot | ~0.1s |
| YOLOv8 detection | ~0.5s |
| Florence-2 captioning (400 elements) | ~5–8s (cached) / ~25s (first run) |
| easyOCR text extraction | ~3s |
| Click — fast mode | ~0.8s total |
| Click — human mode | ~2.4s total |

Models are cached in memory between calls — subsequent scans are fast.

---

## Display Scale

Automatically detects HiDPI/Retina scale:
- Screenshots are captured at native resolution (e.g. 3840×2160 on 4K)
- cliclick uses logical coordinates (e.g. 1920×1080)
- All coordinates are automatically divided by the scale factor

Works correctly on 1x and 2x displays.

---

## When to use each mode

**Human mode** (default):
- Posting comments on Reddit, forums, social media
- Any site that detects automation
- When you want natural-looking behaviour

**Fast mode** (`--fast`):
- Email clients (Gmail, Outlook)
- Internal dashboards and tools
- Any automation where stealth doesn't matter
- Scripted pipelines where speed matters

---

## OpenClaw Integration

Built as an agent skill for [OpenClaw](https://openclaw.ai). The `SKILL.md` file makes it directly loadable as an OpenClaw skill.

Example cron job using fast mode for email tidy:
```
desktop-control --fast focus-url "https://outlook.cloud.microsoft/mail/"
desktop-control --fast scan
desktop-control --fast click "Archive"
```

Example cron job using human mode for Reddit outreach:
```
desktop-control focus-url "https://reddit.com/r/..."
desktop-control click "Join the conversation"
desktop-control type "Your comment here"
desktop-control click "Comment"
```

---

## Models

| Model | Purpose | Size |
|-------|---------|------|
| [OmniParser v2 icon_detect](https://huggingface.co/microsoft/OmniParser-v2.0) | YOLOv8 UI element detection | ~39 MB |
| [OmniParser v2 icon_caption](https://huggingface.co/microsoft/OmniParser-v2.0) | Florence-2 element labelling | ~1 GB |
| [Florence-2-base](https://huggingface.co/microsoft/Florence-2-base-ft) | Processor/tokenizer | ~1 MB |

> **Note:** `transformers` must stay at version `4.49.0` — v5.x breaks Florence-2 compatibility.

---

## Acknowledgements

- [OmniParser](https://github.com/microsoft/OmniParser) by Microsoft
- [cliclick](https://github.com/BlueM/cliclick) by Carsten Blüm
- [ultralytics](https://github.com/ultralytics/ultralytics) — YOLOv8
- [OpenClaw](https://openclaw.ai) — agent platform this was built for

---

## License

MIT

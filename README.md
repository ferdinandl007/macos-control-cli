# 🖥️ macOS Desktop Control

**OmniParser v2 powered macOS desktop automation.** Take a screenshot, detect every UI element by label using local AI, then click, type, and scroll — in any app — with human-like timing.

No Selenium. No AppleScript selectors. No hardcoded coordinates. Just describe what you want to click.

```bash
desktop-control focus "Google Chrome"
desktop-control click "Sign in"
desktop-control type "hello@example.com"
desktop-control key return
desktop-control verify "Dashboard"
```

---

## How it works

1. **Screenshot** — captures the full display via `screencapture`
2. **YOLOv8** — detects all icon/button bounding boxes
3. **Florence-2** — captions each element with a human-readable label
4. **easyOCR** — extracts all text regions
5. **cliclick** — executes mouse moves and keyboard input with randomised human-like delays

Everything runs **100% locally** — no API calls, no cloud, no rate limits.

---

## Features

- 🔍 **Find any UI element by label** — fuzzy matching across 400+ detected elements
- 🖱️ **Natural mouse movement** — curved path with random timing, not robotic straight lines
- ⌨️ **Human-like typing** — per-character random delays with occasional pauses
- 📐 **HiDPI/Retina aware** — auto-detects display scale (1x/2x/3x), works on 4K displays
- 🪟 **Window/app focus** — bring any app to front before interacting
- 🔗 **URL navigation** — navigate Chrome (or any browser) to a URL, reuse existing tabs
- 📋 **Task runner** — run multi-step automation from a JSON file
- 🤖 **OpenClaw compatible** — designed to work as an agent skill in [OpenClaw](https://openclaw.ai)

---

## Installation

### Requirements

- macOS (Apple Silicon recommended)
- Python 3.12
- [uv](https://github.com/astral-sh/uv)
- [cliclick](https://github.com/BlueM/cliclick) (`brew install cliclick`)

### Setup

```bash
git clone https://github.com/ferdinandl007/macos-desktop-control.git
cd macos-desktop-control
bash setup.sh
```

This will:
- Create a Python 3.12 venv at `~/.openclaw/tools/desktop-control/.venv`
- Install torch, ultralytics, transformers, easyocr, einops, timm
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
desktop-control active-app

# Screen detection
desktop-control screenshot
desktop-control scan                    # detect all elements + labels
desktop-control scan --json             # JSON output

# Interaction
desktop-control find "Submit"           # find element, print coords
desktop-control click "Submit"          # find + click
desktop-control click "960,540"         # click by x,y
desktop-control type "hello world"
desktop-control key return
desktop-control scroll down --amount 5

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
sys.path.insert(0, '/path/to/macos-desktop-control')
from desktop_control import DesktopControl

dc = DesktopControl()
dc.focus("Google Chrome")
dc.focus_url("https://example.com")

elements = dc.find_all_elements()
# [{"label": "Sign in", "center_x": 960, "center_y": 540, "confidence": 0.92, ...}, ...]

dc.click_element("Sign in")
dc.type_text("hello@example.com")
dc.scroll("down", amount=3)
```

---

## Performance

| Step | Time |
|------|------|
| Screenshot | ~0.1s |
| YOLOv8 detection | ~0.5s |
| Florence-2 captioning (400 elements) | ~5–8s (cached) / ~25s (first run) |
| easyOCR text extraction | ~3s |
| **Total** | **~8–12s per scan** |

Models are cached in memory between calls — subsequent scans are fast.

---

## Display Scale

Automatically detects HiDPI/Retina scale:
- Screenshots are captured at native resolution (e.g. 3840×2160 on 4K)
- cliclick uses logical coordinates (e.g. 1920×1080)
- All coordinates are automatically divided by the scale factor

Works correctly on 1x, 2x, and 3x displays.

---

## OpenClaw Integration

This tool was built as an agent skill for [OpenClaw](https://openclaw.ai) — a personal AI assistant platform. The `SKILL.md` file at the root makes it directly loadable as an OpenClaw skill.

```yaml
# In your OpenClaw agent session:
# "Use the desktop-control skill to click the Submit button"
```

See the [OpenClaw docs](https://docs.openclaw.ai) for more on building agent skills.

---

## Models

| Model | Purpose | Size |
|-------|---------|------|
| [OmniParser v2 icon_detect](https://huggingface.co/microsoft/OmniParser-v2.0) | YOLOv8 UI element detection | ~39 MB |
| [OmniParser v2 icon_caption](https://huggingface.co/microsoft/OmniParser-v2.0) | Florence-2 element labelling | ~1 GB |
| [Florence-2-base](https://huggingface.co/microsoft/Florence-2-base-ft) | Processor/tokenizer for captioning | ~1 MB |

---

## Acknowledgements

- [OmniParser](https://github.com/microsoft/OmniParser) by Microsoft — UI screen parsing
- [cliclick](https://github.com/BlueM/cliclick) by Carsten Blüm — macOS mouse/keyboard CLI
- [ultralytics](https://github.com/ultralytics/ultralytics) — YOLOv8
- [OpenClaw](https://openclaw.ai) — agent platform this was built for

---

## License

MIT

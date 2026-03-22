---
name: desktop-control
description: "Generic macOS desktop automation via OmniParser v2. Takes screenshots, detects UI elements by label using local AI (YOLOv8 + Florence-2 + OCR), and controls mouse/keyboard with human-like timing. Use when you need to automate any app on the Mac — browser, native app, terminal, anything visible on screen. No app-specific code lives here."
---

# Desktop Control Skill

Generic macOS desktop automation. No app-specific logic — just primitives.

## Prerequisites

Run once:
```bash
bash skills/desktop-control/setup.sh
```

## CLI (available globally as `desktop-control`)

```bash
# Window/App focus
desktop-control focus "Google Chrome"           # bring app to front
desktop-control focus-url "https://example.com" # navigate + focus Chrome
desktop-control focus-url "https://..." --app "Safari"
desktop-control active-app                      # print frontmost app name

# Screen capture & element detection
desktop-control screenshot [--output /tmp/screen.png]
desktop-control scan [--json]                   # detect all elements with labels

# Find elements
desktop-control find "Submit"                   # fuzzy label match, prints coords
desktop-control find "comment box"

# Interact
desktop-control click "Post"                    # click by label (fresh scan)
desktop-control click "820,450"                 # click by x,y coords
desktop-control type "hello world"              # human-like typing
desktop-control key return                      # send keystroke (return, tab, escape, etc)
desktop-control scroll down [--amount 3]

# Run a task sequence from JSON
desktop-control run-task tasks/my-task.json
```

## Python API

```python
import sys
sys.path.insert(0, 'skills/desktop-control')
from desktop_control import DesktopControl

dc = DesktopControl()
dc.focus("Google Chrome")
dc.focus_url("https://example.com")
elements = dc.find_all_elements()        # returns list of {label, bbox, center_x, center_y, confidence}
el = dc.find_element("Submit")           # fuzzy match, returns dict or None
dc.click_element("Submit")              # find + click
dc.type_text("hello world")
dc.scroll("down", amount=3)
app = dc.get_focused_app()
```

## Task JSON format

```json
[
  {"action": "focus", "app": "Google Chrome"},
  {"action": "focus-url", "url": "https://...", "app": "Google Chrome"},
  {"action": "wait", "seconds": 3},
  {"action": "click", "query": "Sign in"},
  {"action": "type", "text": "my text here"},
  {"action": "key", "key": "return"},
  {"action": "scroll", "direction": "down", "amount": 5},
  {"action": "verify", "query": "Success", "timeout": 10},
  {"action": "click", "x": 820, "y": 450}
]
```

## How it works

1. **Screenshot** → `/usr/sbin/screencapture`
2. **YOLOv8** (icon_detect model) → finds icon/button bounding boxes
3. **Florence-2** (icon_caption model) → captions each crop with a human-readable label
4. **easyocr** → extracts text regions
5. **cliclick** → executes mouse moves/clicks and keyboard input with randomised delays

## Paths

- Venv: `~/.openclaw/tools/desktop-control/.venv`
- Models: `~/.openclaw/models/omniparser/` + `~/.openclaw/models/florence2-base/`
- CLI: `~/.local/bin/desktop-control` (symlink)
- Tasks: `skills/desktop-control/tasks/` (put your JSON task files here)

## Performance

- First run: ~25–30s (models load into memory)
- Subsequent scans (models cached): ~5–8s
- Detects 400+ elements on a typical desktop

## Notes

- `transformers` must stay at 4.49.0 — v5.x breaks Florence-2
- All task logic (what to do with which app) lives in task JSON files, not in this skill
- This skill has no knowledge of any specific app, website, or workflow

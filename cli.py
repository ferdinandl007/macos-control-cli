#!/usr/bin/env python3
"""
desktop-control CLI — macOS desktop automation via OmniParser v2 + cliclick.

Usage:
  desktop-control [--fast] screenshot [--output /tmp/screen.png]
  desktop-control scan [--output /tmp/screen.png] [--json]
  desktop-control find <query> [--screenshot /tmp/existing.png]
  desktop-control click <query_or_coords> [--screenshot /tmp/existing.png]
  desktop-control type <text>
  desktop-control key <keyname>
  desktop-control scroll <up|down> [--amount 3]
  desktop-control focus <app_name>
  desktop-control focus-url <url> [--app "Google Chrome"]
  desktop-control active-app
  desktop-control run-task <taskfile.json>
"""

import argparse
import json
import os
import sys
import time

# Ensure skill directory is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from desktop_control import DesktopControl


def fuzzy_match_elements(elements: list[dict], query: str) -> list[dict]:
    """Fuzzy match elements by label. Returns matches sorted best-first."""
    q = query.lower().strip()
    q_words = set(q.split())

    scored = []
    for el in elements:
        label = el["label"].lower().strip()
        label_words = set(label.split())

        score = 0.0
        # Exact match
        if label == q:
            score = 100.0
        # Exact word match (e.g. query "Post" matches label "Post")
        elif q in label_words or label in q_words:
            score = 80.0
        # Substring match
        elif q in label:
            score = 60.0
        # Reverse substring
        elif label in q:
            score = 40.0
        # Word overlap
        else:
            overlap = q_words & label_words
            if overlap:
                score = 20.0 * len(overlap) / max(len(q_words), len(label_words))

        if score > 0:
            # Boost by confidence
            score += el["confidence"] * 0.5
            scored.append((score, el))

    scored.sort(key=lambda x: -x[0])
    return [el for _, el in scored]


def cmd_screenshot(args):
    dc = DesktopControl(screenshot_path=args.output, fast=args.fast)
    path = dc.screenshot()
    print(path)


def cmd_scan(args):
    dc = DesktopControl(screenshot_path=args.output, fast=args.fast)
    dc.screenshot()
    elements = dc.find_all_elements()

    if args.json:
        out = [
            {"label": el["label"], "x": el["center_x"], "y": el["center_y"],
             "confidence": round(el["confidence"], 3)}
            for el in elements
        ]
        print(json.dumps(out, indent=2))
    else:
        print(f"Detected {len(elements)} elements:")
        for el in elements:
            src = f" [{el.get('source', 'yolo')}]" if el.get("source") else ""
            print(f"  [{el['confidence']:.2f}]{src} \"{el['label']}\" @ ({el['center_x']}, {el['center_y']})")


def cmd_find(args):
    dc = DesktopControl(screenshot_path=args.screenshot, fast=args.fast)
    if not os.path.exists(args.screenshot):
        dc.screenshot()
    elements = dc.find_all_elements()
    matches = fuzzy_match_elements(elements, args.query)

    if not matches:
        print(f"Not found: {args.query}", file=sys.stderr)
        sys.exit(1)

    best = matches[0]
    print(f"{best['center_x']},{best['center_y']}")
    if len(matches) > 1:
        print(f"  ({len(matches)} matches, best: \"{best['label']}\" [{best['confidence']:.2f}])",
              file=sys.stderr)
    else:
        print(f"  \"{best['label']}\" [{best['confidence']:.2f}]", file=sys.stderr)


def cmd_click(args):
    query = args.query_or_coords

    # Check if it's direct coordinates (e.g. "123,456")
    if "," in query:
        parts = query.split(",")
        if len(parts) == 2:
            try:
                x, y = int(parts[0].strip()), int(parts[1].strip())
                dc = DesktopControl(fast=args.fast)
                dc.click(x, y)
                print(f"Clicked ({x}, {y})")
                return
            except ValueError:
                pass

    # Otherwise treat as a label query
    dc = DesktopControl(screenshot_path=args.screenshot, fast=args.fast)
    if not os.path.exists(args.screenshot):
        dc.screenshot()
    elements = dc.find_all_elements()
    matches = fuzzy_match_elements(elements, query)

    if not matches:
        print(f"Not found: {query}", file=sys.stderr)
        sys.exit(1)

    best = matches[0]
    dc.click(best["center_x"], best["center_y"])
    print(f"Clicked \"{best['label']}\" @ ({best['center_x']}, {best['center_y']})")


def cmd_type(args):
    dc = DesktopControl(fast=args.fast)
    dc.type_text(args.text)
    print(f"Typed {len(args.text)} chars")


def cmd_key(args):
    import subprocess
    CLICLICK = "/opt/homebrew/bin/cliclick"
    subprocess.run([CLICLICK, f"kp:{args.keyname}"], check=True)
    print(f"Pressed {args.keyname}")


def cmd_scroll(args):
    dc = DesktopControl(fast=args.fast)
    dc.scroll(args.direction, args.amount)
    print(f"Scrolled {args.direction} x{args.amount}")


def cmd_run_task(args):
    with open(args.taskfile) as f:
        actions = json.load(f)

    dc = DesktopControl(fast=args.fast)

    for i, action in enumerate(actions):
        act = action["action"]
        print(f"[{i+1}/{len(actions)}] {act}", end="")

        if act == "navigate":
            app = action.get("app", "Google Chrome")
            url = action["url"]
            print(f" → {url}")
            import subprocess
            subprocess.run(
                ["osascript", "-e", f'tell application "{app}" to activate'],
                check=True,
            )
            time.sleep(0.5)
            subprocess.run(
                ["osascript", "-e",
                 f'tell application "{app}" to set URL of active tab of front window to "{url}"'],
                check=True,
            )
            time.sleep(action.get("wait", 5))

        elif act == "screenshot":
            out = action.get("output", "/tmp/screenshot.png")
            dc.screenshot_path = out
            dc.screenshot()
            print(f" → {out}")

        elif act == "scan":
            dc.screenshot()
            elements = dc.find_all_elements()
            print(f" → {len(elements)} elements")

        elif act == "find":
            query = action["query"]
            dc.screenshot()
            elements = dc.find_all_elements()
            matches = fuzzy_match_elements(elements, query)
            if matches:
                best = matches[0]
                print(f" \"{query}\" → \"{best['label']}\" @ ({best['center_x']}, {best['center_y']})")
            else:
                print(f" \"{query}\" → NOT FOUND")
                if not action.get("optional", False):
                    print("Task failed: element not found", file=sys.stderr)
                    sys.exit(1)

        elif act == "click":
            query = action.get("query", "")
            if "x" in action and "y" in action:
                dc.click(action["x"], action["y"])
                print(f" → ({action['x']}, {action['y']})")
            else:
                dc.screenshot()
                elements = dc.find_all_elements()
                matches = fuzzy_match_elements(elements, query)
                if not matches:
                    print(f" \"{query}\" → NOT FOUND")
                    if not action.get("optional", False):
                        print("Task failed: element not found", file=sys.stderr)
                        sys.exit(1)
                    continue
                best = matches[0]
                dc.click(best["center_x"], best["center_y"])
                print(f" \"{query}\" → \"{best['label']}\" @ ({best['center_x']}, {best['center_y']})")

        elif act == "type":
            text = action["text"]
            dc.type_text(text)
            print(f" → {len(text)} chars")

        elif act == "key":
            import subprocess
            subprocess.run(["/opt/homebrew/bin/cliclick", f"kp:{action['key']}"], check=True)
            print(f" → {action['key']}")

        elif act == "scroll":
            direction = action.get("direction", "down")
            amount = action.get("amount", 3)
            dc.scroll(direction, amount)
            print(f" → {direction} x{amount}")

        elif act == "focus":
            app = action["app"]
            dc.focus(app)
            print(f" → focused {app}")

        elif act == "focus-url":
            url = action["url"]
            app = action.get("app", "Google Chrome")
            dc.focus_url(url, app)
            print(f" → navigated {app} to {url}")

        elif act == "find-text":
            # OCR-only search — fast, no Florence-2
            from omniparser import detect_elements
            dc.screenshot()
            elements = detect_elements(dc.screenshot_path, caption=False)
            q = action["query"].lower()
            matches = [e for e in elements if q in e["label"].lower()]
            if matches:
                best = sorted(matches, key=lambda x: -x["confidence"])[0]
                print(f" \"{action['query']}\" → \"{best['label']}\" @ ({best['center_x']}, {best['center_y']})")
            else:
                print(f" \"{action['query']}\" → NOT FOUND")
                if not action.get("optional", False):
                    sys.exit(1)

        elif act == "wait-for":
            query = action["query"]
            timeout = action.get("timeout", 10)
            interval = action.get("interval", 2.0)
            deadline = time.time() + timeout
            found = False
            while time.time() < deadline:
                dc.screenshot()
                elements = dc.find_all_elements()
                matches = fuzzy_match_elements(elements, query)
                if matches:
                    print(f" \"{query}\" → FOUND \"{matches[0]['label']}\"")
                    found = True
                    break
                time.sleep(min(interval, deadline - time.time()))
            if not found:
                print(f" \"{query}\" → TIMEOUT")
                if not action.get("optional", False):
                    sys.exit(1)

        elif act == "wait":
            secs = action.get("seconds", 2)
            print(f" → {secs}s")
            time.sleep(secs)

        elif act == "verify":
            query = action["query"]
            timeout = action.get("timeout", 5)
            print(f" \"{query}\"", end="")
            found = False
            deadline = time.time() + timeout
            while time.time() < deadline:
                dc.screenshot()
                elements = dc.find_all_elements()
                matches = fuzzy_match_elements(elements, query)
                if matches:
                    print(f" → FOUND \"{matches[0]['label']}\"")
                    found = True
                    break
                time.sleep(1)
            if not found:
                print(" → NOT FOUND")
                if not action.get("optional", False):
                    print("Verification failed", file=sys.stderr)
                    sys.exit(1)

        else:
            print(f" → unknown action: {act}", file=sys.stderr)

        # Small delay between actions
        time.sleep(action.get("delay", 0.5))

    print("Task complete.")


def cmd_find_text(args):
    """Find visible text on screen using OCR only — faster than full scan."""
    from omniparser import detect_elements
    dc = DesktopControl(screenshot_path=args.screenshot, fast=args.fast)
    dc.screenshot()
    # OCR-only: caption=False skips Florence-2, much faster
    elements = detect_elements(dc.screenshot_path, caption=False)
    # Filter to OCR text hits only
    q = args.query.lower()
    matches = [e for e in elements if q in e["label"].lower()]
    matches.sort(key=lambda x: -x["confidence"])
    if not matches:
        print(f"Text not found: {args.query}", file=sys.stderr)
        sys.exit(1)
    best = matches[0]
    print(f"{best['center_x']},{best['center_y']}")
    print(f"  \"{best['label']}\" [{best['confidence']:.2f}]", file=sys.stderr)


def cmd_wait_for(args):
    """Wait until element appears on screen, then print its coordinates."""
    import time as _time
    from omniparser import detect_elements
    dc = DesktopControl(fast=args.fast)
    deadline = _time.time() + args.timeout
    attempt = 0
    while _time.time() < deadline:
        attempt += 1
        dc.screenshot()
        elements = dc.find_all_elements()
        matches = fuzzy_match_elements(elements, args.query)
        if matches:
            best = matches[0]
            print(f"{best['center_x']},{best['center_y']}")
            print(f"  Found after {attempt} scan(s): \"{best['label']}\"", file=sys.stderr)
            return
        remaining = deadline - _time.time()
        if remaining > 0:
            _time.sleep(min(args.interval, remaining))
    print(f"Timeout: \"{args.query}\" not found after {args.timeout}s", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="desktop-control",
        description="macOS desktop automation via OmniParser v2 + cliclick",
    )
    parser.add_argument("--fast", action="store_true",
                        help="Skip human-simulation delays and curved mouse movement (faster, no bot-detection evasion)")
    sub = parser.add_subparsers(dest="command", required=True)

    # screenshot
    p = sub.add_parser("screenshot", help="Take a screenshot")
    p.add_argument("--output", default="/tmp/screenshot.png")
    p.set_defaults(func=cmd_screenshot)

    # scan
    p = sub.add_parser("scan", help="Screenshot + OmniParser detection")
    p.add_argument("--output", default="/tmp/screenshot.png")
    p.add_argument("--json", action="store_true", help="Output JSON array")
    p.set_defaults(func=cmd_scan)

    # find
    p = sub.add_parser("find", help="Find elements matching query")
    p.add_argument("query", help="Text to search for (fuzzy label match)")
    p.add_argument("--screenshot", default="/tmp/screenshot.png")
    p.set_defaults(func=cmd_find)

    # click
    p = sub.add_parser("click", help="Click element or coordinates")
    p.add_argument("query_or_coords", help="Label query or 'x,y' coordinates")
    p.add_argument("--screenshot", default="/tmp/screenshot.png")
    p.set_defaults(func=cmd_click)

    # type
    p = sub.add_parser("type", help="Type text with human-like delays")
    p.add_argument("text", help="Text to type")
    p.set_defaults(func=cmd_type)

    # key
    p = sub.add_parser("key", help="Press a key (return, tab, escape, etc)")
    p.add_argument("keyname", help="Key name for cliclick (return, tab, escape, etc)")
    p.set_defaults(func=cmd_key)

    # scroll
    p = sub.add_parser("scroll", help="Scroll in a direction")
    p.add_argument("direction", choices=["up", "down", "left", "right"])
    p.add_argument("--amount", type=int, default=3)
    p.set_defaults(func=cmd_scroll)

    # focus
    p = sub.add_parser("focus", help="Bring an application to the foreground")
    p.add_argument("app_name", help="Application name (e.g. 'Google Chrome', 'Terminal')")
    p.set_defaults(func=lambda a: (DesktopControl().focus(a.app_name), print(f"Focused: {a.app_name}")))

    # focus-url
    p = sub.add_parser("focus-url", help="Navigate an app to a URL and bring it to front")
    p.add_argument("url", help="URL to navigate to")
    p.add_argument("--app", default="Google Chrome", help="Application name")
    p.set_defaults(func=lambda a: (DesktopControl().focus_url(a.url, a.app), print(f"Navigated {a.app} to {a.url}")))

    # active-app
    p = sub.add_parser("active-app", help="Print the name of the frontmost application")
    p.set_defaults(func=lambda a: print(DesktopControl().get_focused_app()))

    # display-info
    p = sub.add_parser("display-info", help="Show detected display configuration")
    p.set_defaults(func=lambda a: print(DesktopControl().display_info()))

    # find-text — search visible text via OCR only (fast, no Florence-2 captioning)
    p = sub.add_parser("find-text", help="Find visible text on screen using OCR (faster than scan+find)")
    p.add_argument("query", help="Text to search for")
    p.add_argument("--screenshot", default="/tmp/screenshot.png")
    p.set_defaults(func=cmd_find_text)

    # wait-for — wait until an element appears, with timeout
    p = sub.add_parser("wait-for", help="Wait until an element label appears on screen")
    p.add_argument("query", help="Element label to wait for")
    p.add_argument("--timeout", type=int, default=10, help="Max seconds to wait (default 10)")
    p.add_argument("--interval", type=float, default=2.0, help="Rescan interval in seconds")
    p.set_defaults(func=cmd_wait_for)

    # run-task
    p = sub.add_parser("run-task", help="Run actions from a JSON task file")
    p.add_argument("taskfile", help="Path to JSON task file")
    p.set_defaults(func=cmd_run_task)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

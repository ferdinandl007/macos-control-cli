"""
Desktop Control — macOS desktop automation via OmniParser v2 + cliclick.

Provides a clean Python API for visual UI interaction:
  find_element, click_element, type_text, screenshot, scroll
"""

import os
import random
import subprocess
import sys
import time

# Ensure this directory is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omniparser import detect_elements

CLICLICK = "/opt/homebrew/bin/cliclick"
SCREENCAPTURE = "/usr/sbin/screencapture"


def _get_display_scale() -> float:
    """
    Detect the HiDPI scale factor.
    Screenshot pixels / logical pixels. Typically 2.0 on Retina/4K, 1.0 on 1080p.
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "Finder" to get bounds of window of desktop'],
            capture_output=True, text=True
        )
        parts = result.stdout.strip().split(", ")
        logical_w = int(parts[2])  # right bound = width

        # Get screenshot pixel width
        from PIL import Image as _Image
        tmp = "/tmp/_scale_probe.png"
        subprocess.run([SCREENCAPTURE, "-x", tmp], check=True, capture_output=True)
        img = _Image.open(tmp)
        pixel_w = img.size[0]
        os.unlink(tmp)

        scale = pixel_w / logical_w
        return scale
    except Exception as e:
        import sys
        print(f"[desktop-control] Warning: could not detect display scale ({e}), defaulting to 2.0 for 4K safety", file=sys.stderr)
        return 2.0  # default to 2x (safe for 4K — better to over-divide than under)


class DesktopControl:
    def __init__(self, screenshot_path: str = "/tmp/screenshot.png", app: str | None = None, fast: bool = False):
        """
        Args:
            screenshot_path: Where to save screenshots.
            app: App to focus on init.
            fast: If True, skip all human-simulation delays and curved mouse movement.
                  Use for internal automation where bot detection doesn't matter.
        """
        self.screenshot_path = screenshot_path
        self._elements: list[dict] = []
        self._focused_app = app
        self._scale = _get_display_scale()
        self._fast = fast
        if app:
            self.focus(app)

    # ── Window / App Focus ──────────────────────────────────────────────

    def focus(self, app_name: str) -> None:
        """Bring an application to the foreground and make it active."""
        script = f'tell application "{app_name}" to activate'
        subprocess.run(["osascript", "-e", script], check=True)
        time.sleep(0.8)
        self._focused_app = app_name

    def focus_url(self, url: str, app_name: str = "Google Chrome") -> None:
        """
        Navigate an app (Chrome by default) to a URL and bring it to front.
        Reuses an existing tab with that URL if present, otherwise navigates the active tab.
        """
        # Try to find an existing tab with this URL
        find_script = f'''
        tell application "{app_name}"
            activate
            repeat with w in windows
                set tabIdx to 0
                repeat with t in tabs of w
                    set tabIdx to tabIdx + 1
                    if URL of t contains "{url}" then
                        set active tab index of w to tabIdx
                        set index of w to 1
                        return "found"
                    end if
                end repeat
            end repeat
            -- Not found: navigate active tab
            set URL of active tab of front window to "{url}"
            return "navigated"
        end tell
        '''
        subprocess.run(["osascript", "-e", find_script], capture_output=True)
        time.sleep(5)
        self._focused_app = app_name

    def get_focused_app(self) -> str:
        """Return the name of the currently frontmost application."""
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of first application process whose frontmost is true'],
            capture_output=True, text=True
        )
        return result.stdout.strip()

    def screenshot(self) -> str:
        """Capture full screen. Returns the screenshot file path."""
        subprocess.run(
            [SCREENCAPTURE, "-x", self.screenshot_path],
            check=True,
        )
        return self.screenshot_path

    def find_all_elements(self, fresh_screenshot: bool = False) -> list[dict]:
        """
        Detect all UI elements on screen using OmniParser v2.
        Uses the most recent screenshot unless fresh_screenshot=True.
        """
        if fresh_screenshot or not os.path.exists(self.screenshot_path):
            self.screenshot()
        self._elements = detect_elements(self.screenshot_path)
        return self._elements

    def find_element(self, label: str) -> dict | None:
        """
        Find a UI element by label (case-insensitive substring match).
        Takes a fresh screenshot and re-detects elements.
        Returns the best match or None.
        """
        self.screenshot()
        self._elements = detect_elements(self.screenshot_path)
        return self._match_element(label)

    def _match_element(self, label: str) -> dict | None:
        """Find best matching element from cached elements using fuzzy matching."""
        q = label.lower().strip()
        q_words = set(q.split())

        scored = []
        for el in self._elements:
            el_label = el["label"].lower().strip()
            el_words = set(el_label.split())

            score = 0.0
            # Exact match
            if el_label == q:
                score = 100.0
            # Exact word match (e.g. "Post" matches label "Post")
            elif q in el_words or el_label in q_words:
                score = 80.0
            # Substring match
            elif q in el_label:
                score = 60.0
            # Reverse substring
            elif el_label in q:
                score = 40.0
            # Word overlap
            else:
                overlap = q_words & el_words
                if overlap:
                    score = 20.0 * len(overlap) / max(len(q_words), len(el_words))

            if score > 0:
                score += el["confidence"] * 0.5
                scored.append((score, el))

        if not scored:
            return None

        scored.sort(key=lambda x: -x[0])
        return scored[0][1]

    def _to_logical(self, x: int, y: int) -> tuple[int, int]:
        """Convert screenshot pixel coordinates to logical screen coordinates."""
        return int(x / self._scale), int(y / self._scale)

    def _move_human(self, tx: int, ty: int, steps: int = 8) -> None:
        """
        Move the mouse to (tx, ty) in multiple steps with slight curve deviation,
        simulating natural human mouse movement.
        """
        # Get current mouse position via cliclick (not directly available, use a middle point)
        # We'll just move in steps from an assumed offscreen-ish start toward target
        # Slight bezier-like arc: add a perpendicular wobble that peaks midway
        wobble_x = random.randint(-15, 15)
        wobble_y = random.randint(-15, 15)

        for i in range(1, steps + 1):
            t = i / steps
            # Ease-in-out interpolation
            ease = t * t * (3 - 2 * t)
            # Peak wobble at midpoint, taper to 0 at end
            arc = (1 - abs(2 * t - 1)) * (1 - ease * 0.5)
            ix = int(tx + wobble_x * arc * (1 - t))
            iy = int(ty + wobble_y * arc * (1 - t))
            subprocess.run([CLICLICK, f"m:{ix},{iy}"], check=True)
            time.sleep(random.uniform(0.008, 0.025))

    def click(self, x: int, y: int):
        """
        Click at coordinates. Accepts screenshot pixel coords (OmniParser output)
        and automatically converts to logical screen coords for cliclick.
        In human mode: curved mouse movement + random delays.
        In fast mode: direct click, no delays.
        """
        lx, ly = self._to_logical(x, y)

        if self._fast:
            subprocess.run([CLICLICK, f"c:{lx},{ly}"], check=True)
        else:
            # Small random offset landing point
            lx += random.randint(-2, 2)
            ly += random.randint(-2, 2)
            time.sleep(random.uniform(0.08, 0.25))
            self._move_human(lx, ly)
            time.sleep(random.uniform(0.05, 0.12))
            subprocess.run([CLICLICK, f"c:{lx},{ly}"], check=True)

    def click_element(self, label: str) -> bool:
        """
        Take a screenshot, find the element by label, and click it.
        Returns True if the element was found and clicked, False otherwise.
        """
        el = self.find_element(label)
        if el is None:
            return False
        self.click(el["center_x"], el["center_y"])
        return True

    def type_text(self, text: str):
        """
        Type text character by character with human-like randomized delays.
        Base delay: 40-140ms per character.
        Occasional longer pauses: 300-800ms (roughly every 5-15 characters).
        """
        chars_since_pause = 0
        next_pause_at = random.randint(5, 15)

        if self._fast:
            # Fast mode: type all at once via cliclick
            subprocess.run([CLICLICK, f"t:{text}"], check=True)
            return

        for char in text:
            # Use cliclick's type command for each character
            # cliclick t: types text, kp: presses a key
            if char == "\n":
                subprocess.run([CLICLICK, "kp:return"], check=True)
            elif char == "\t":
                subprocess.run([CLICLICK, "kp:tab"], check=True)
            else:
                subprocess.run([CLICLICK, f"t:{char}"], check=True)

            # Base delay
            delay = random.uniform(0.04, 0.14)

            # Occasional longer pause
            chars_since_pause += 1
            if chars_since_pause >= next_pause_at:
                delay = random.uniform(0.3, 0.8)
                chars_since_pause = 0
                next_pause_at = random.randint(5, 15)

            time.sleep(delay)

    def scroll(self, direction: str = "down", amount: int = 3):
        """
        Scroll in the given direction.
        Directions: up, down, left, right.
        Amount: number of scroll steps.
        """
        # Get current mouse position for scrolling context
        # cliclick scroll syntax: scroll direction amount
        # du = scroll up, dd = scroll down
        direction_map = {
            "up": "su",
            "down": "sd",
            "left": "sl",
            "right": "sr",
        }
        scroll_dir = direction_map.get(direction.lower())
        if not scroll_dir:
            raise ValueError(f"Invalid direction: {direction}. Use: up, down, left, right")

        for _ in range(amount):
            # cliclick doesn't have native scroll, use AppleScript
            time.sleep(random.uniform(0.05, 0.15))

        # Use AppleScript for scrolling (more reliable than cliclick for scroll)
        if direction.lower() in ("up", "down"):
            scroll_amount = amount if direction.lower() == "down" else -amount
            script = f"""
            tell application "System Events"
                repeat {abs(scroll_amount)} times
                    if {scroll_amount} > 0 then
                        key code 125
                    else
                        key code 126
                    end if
                    delay 0.05
                end repeat
            end tell
            """
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
            )
        elif direction.lower() in ("left", "right"):
            key_code = 124 if direction.lower() == "right" else 123
            script = f"""
            tell application "System Events"
                repeat {amount} times
                    key code {key_code}
                    delay 0.05
                end repeat
            end tell
            """
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
            )


if __name__ == "__main__":
    dc = DesktopControl()
    print("Taking screenshot...")
    path = dc.screenshot()
    print(f"Screenshot: {path}")

    print("Detecting elements...")
    elements = dc.find_all_elements()
    print(f"Found {len(elements)} elements")
    for el in elements[:10]:
        print(f"  [{el['confidence']:.2f}] {el['label']} @ ({el['center_x']}, {el['center_y']})")

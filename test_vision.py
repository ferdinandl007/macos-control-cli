#!/usr/bin/env python3
"""
Quick test: take a screenshot, run OmniParser v2, print detected elements.
"""

import os
import sys
import time
import json

# Add skill directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from desktop_control import DesktopControl


def main():
    dc = DesktopControl()

    print("=" * 60)
    print("Desktop Control — Vision Test")
    print("=" * 60)

    # 1. Take screenshot
    print("\n[1] Taking screenshot...")
    t0 = time.time()
    path = dc.screenshot()
    print(f"    Saved to: {path} ({time.time() - t0:.2f}s)")

    # 2. Detect elements
    print("\n[2] Running OmniParser v2 detection...")
    t0 = time.time()
    elements = dc.find_all_elements()
    elapsed = time.time() - t0
    print(f"    Detected {len(elements)} elements in {elapsed:.2f}s")

    # 3. Print results
    print("\n[3] Detected UI Elements:")
    print("-" * 60)
    for i, el in enumerate(elements):
        bbox = el["bbox"]
        print(
            f"  {i+1:3d}. [{el['confidence']:.3f}] \"{el['label']}\""
            f"  @ ({el['center_x']}, {el['center_y']})"
            f"  bbox={bbox}"
        )

    # 4. Save full results to JSON
    output_path = "/tmp/omniparser_test_results.json"
    with open(output_path, "w") as f:
        json.dump(elements, f, indent=2)
    print(f"\n    Full results saved to: {output_path}")

    # 5. Summary
    print(f"\n{'=' * 60}")
    print(f"Total elements: {len(elements)}")
    if elements:
        avg_conf = sum(e["confidence"] for e in elements) / len(elements)
        print(f"Avg confidence: {avg_conf:.3f}")
        print(f"Top element: \"{elements[0]['label']}\" ({elements[0]['confidence']:.3f})")
    print("=" * 60)


if __name__ == "__main__":
    main()

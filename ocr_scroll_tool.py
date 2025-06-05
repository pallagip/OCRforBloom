#!/usr/bin/env python3
"""
ocr_scroll_tool.py

A script that lets you:
  1. Use Ctrl+Shift+1 to mark the top-left corner of the region.
  2. Use Ctrl+Shift+2 to mark the bottom-right corner.
  3. After both corners are marked, use:
       • Ctrl+Shift+C → capture that region, run OCR, append text, send Page Down.
       • Ctrl+Shift+Q → stop and save all collected text.

Usage:
    python ocr_scroll_tool.py

Dependencies:
    pip install pillow pytesseract pynput
    (and Tesseract itself must be installed and on your PATH)
"""

import sys
import time
import pytesseract
from PIL import ImageGrab
from pynput import keyboard, mouse
import os
from datetime import datetime

# Global state
top_left = None       # (x, y) tuple for top-left corner
bottom_right = None   # (x, y) tuple for bottom-right corner
region_ready = False  # True once both corners are marked
ocr_buffer = []       # Stores extracted text chunks
tesseract_cmd = None  # If Tesseract is not on PATH, set full path here (e.g. r"C:\Program Files\Tesseract-OCR\tesseract.exe")

mouse_controller = mouse.Controller()

def on_mark_topleft():
    global top_left
    # Record current mouse position
    top_left = mouse_controller.position
    print(f"[REGION] Top-left corner set to {top_left}. Use Ctrl+Shift+2 for bottom-right.")

def on_mark_bottomright():
    global bottom_right, region_ready
    bottom_right = mouse_controller.position
    if top_left is None:
        print("[ERROR] Please set top-left first with Ctrl+Shift+1.")
        return
    # Ensure bottom-right is actually lower and to the right of top-left
    x1, y1 = top_left
    x2, y2 = bottom_right
    if x2 <= x1 or y2 <= y1:
        print(f"[ERROR] Bottom-right {bottom_right} must be lower-right of top-left {top_left}. Try again.")
        return
    region_ready = True
    print(f"[REGION] Bottom-right corner set to {bottom_right}.")
    print("Region marked. Now press Ctrl+Shift+C to capture+scroll, or Ctrl+Shift+Q to stop and save.")

def on_capture():
    global region_ready, ocr_buffer, tesseract_cmd
    if not region_ready:
        print("[ERROR] Region not ready. Mark corners with Ctrl+Shift+1 and Ctrl+Shift+2.")
        return
    x1, y1 = int(top_left[0]), int(top_left[1])
    x2, y2 = int(bottom_right[0]), int(bottom_right[1])
    bbox = (x1, y1, x2, y2)
    # Short delay to allow any scrolling to finish
    time.sleep(0.1)
    img = ImageGrab.grab(bbox)
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    custom_config = r"--psm 6"
    text = pytesseract.image_to_string(img, config=custom_config)
    ocr_buffer.append(text)
    # Send Page Down
    keyboard.Controller().press(keyboard.Key.page_down)
    keyboard.Controller().release(keyboard.Key.page_down)
    print(f"[OCR] Captured chunk #{len(ocr_buffer)}, {len(text)} characters.")

def on_stop():
    # Stop the hotkey listener
    listener.stop()
    # If no text was captured, exit
    if not ocr_buffer:
        print("[STOP] No text captured. Exiting.")
        sys.exit(0)

    # Determine script directory and build a timestamped filename
    script_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ocr_{timestamp}.txt"
    file_path = os.path.join(script_dir, filename)

    # Write OCR buffer to the new file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(ocr_buffer))
        print(f"[SAVE] OCR text written to: {file_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save file: {e}")
    sys.exit(0)

# Mapping hotkeys to functions
hotkey_actions = {
    "<ctrl>+<shift>+1": on_mark_topleft,
    "<ctrl>+<shift>+2": on_mark_bottomright,
    "<ctrl>+<shift>+c": on_capture,
    "<ctrl>+<shift>+q": on_stop,
}

if __name__ == "__main__":
    print("Instructions:")
    print("  1) Hover mouse over top-left corner of region, press Ctrl+Shift+1")
    print("  2) Hover mouse over bottom-right corner, press Ctrl+Shift+2")
    print("  After marking region, use:")
    print("    • Ctrl+Shift+C → capture+scroll")
    print("    • Ctrl+Shift+Q → stop and save")
    print("")
    listener = keyboard.GlobalHotKeys(hotkey_actions)
    listener.start()
    listener.join()
#!/usr/bin/env python3
"""
ocr_scroll_tool.py

A script that lets you:
  1. Use Ctrl+Shift+1 to mark the top-left corner of the region.
  2. Use Ctrl+Shift+2 to mark the bottom-right corner.
  3. After both corners are marked, use:
       • Ctrl+Shift+C → capture that region, run OCR, append text.
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
import threading
from PIL import ImageOps

# Global state
top_left = None       # (x, y) tuple for top-left corner
bottom_right = None   # (x, y) tuple for bottom-right corner
region_ready = False  # True once both corners are marked
ocr_buffer = []       # Stores extracted text chunks
tesseract_cmd = None  # If Tesseract is not on PATH, set full path here (e.g. r"C:\Program Files\Tesseract-OCR\tesseract.exe")

capturing = False       # Indicates if automatic capture is ongoing
capture_thread = None   # Holds reference to the capture thread
prev_capture = None     # Holds the last captured image for change detection

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
    print("Region marked. Press Ctrl+Shift+C to capture. After capturing, manually scroll and press Ctrl+Shift+C again for next capture.")

def on_capture():
    global region_ready, capturing, capture_thread, prev_capture
    if not region_ready:
        print("[ERROR] Region not ready. Mark corners with Ctrl+Shift+1 and Ctrl+Shift+2.")
        return
    if capturing:
        print("[INFO] Already capturing.")
        return
    capturing = True
    prev_capture = None
    print("[AUTO] Automatic capture started. Scroll manually. Press Ctrl+Shift+Q to stop and save.")
    # Define the capture loop
    def capture_loop():
        global prev_capture, ocr_buffer, tesseract_cmd, capturing
        x1, y1 = int(top_left[0]), int(top_left[1])
        x2, y2 = int(bottom_right[0]), int(bottom_right[1])
        bbox = (x1, y1, x2, y2)
        while capturing:
            img = ImageGrab.grab(bbox)
            # Compare with previous capture
            if prev_capture is None or list(img.getdata()) != list(prev_capture.getdata()):
                gray = ImageOps.grayscale(img)
                if tesseract_cmd:
                    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                custom_config = r"--psm 6"
                text = pytesseract.image_to_string(gray, config=custom_config)
                if text.strip() and (not ocr_buffer or text.strip() != ocr_buffer[-1].strip()):
                    ocr_buffer.append(text)
                    print(f"[OCR] Captured chunk #{len(ocr_buffer)}, {len(text)} chars.")
                prev_capture = img
            time.sleep(0.5)
    # Start capture thread
    capture_thread = threading.Thread(target=capture_loop, daemon=True)
    capture_thread.start()

def on_stop():
    global capturing, capture_thread
    # Stop listening for hotkeys
    listener.stop()
    # Signal the capture loop to stop
    capturing = False
    # Wait for the capture thread to finish
    if capture_thread:
        capture_thread.join()
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
    print("    • Ctrl+Shift+C → capture current region")
    print("      (then manually scroll and press Ctrl+Shift+C again for next capture)")
    print("    • Ctrl+Shift+Q → stop and save")
    print("")
    listener = keyboard.GlobalHotKeys(hotkey_actions)
    listener.start()
    listener.join()
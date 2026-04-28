import time
import pyperclip
import win32gui
import win32process
import psutil
import sys
import tkinter as tk
from tkinter import messagebox  # <-- 新增

if sys.platform != "win32":
    raise RuntimeError("Windows only")

POLL_INTERVAL = 0.08  # 80ms，幾乎即時

def is_calc_foreground() -> bool:
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return False

    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        proc = psutil.Process(pid)
        return "soffice" in proc.name().lower()
    except psutil.Error:
        return False

def strip_trailing_newlines(text: str) -> str:
    return text.rstrip("\r\n")

def main():
    # 顯示「程式已啟動」訊息視窗
    root = tk.Tk()
    root.withdraw()  # 隱藏主視窗
    messagebox.showinfo("Remove_\\r\\n", "The program has started.")
    root.destroy()

    last_text = None

    while True:
        try:
            text = pyperclip.paste()

            if not isinstance(text, str) or text == last_text:
                time.sleep(POLL_INTERVAL)
                continue

            if is_calc_foreground():
                cleaned = strip_trailing_newlines(text)
                if cleaned != text:
                    pyperclip.copy(cleaned)
                    last_text = cleaned
                else:
                    last_text = text
            else:
                last_text = text

        except Exception:
            pass

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()

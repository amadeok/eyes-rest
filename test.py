import ctypes
import ctypes.wintypes as wintypes
import psutil, pygetwindow as gw
import win32process, my_utils
import my_utils.util_, time

time.sleep(1)
hwnd = gw.getActiveWindow()._hWnd   # Replace this with a real window handle
process_path = my_utils.util_.get_path_from_hwd(hwnd)
print(f"Process Path: {process_path}")

# import ctypes
# import ctypes.wintypes as wintypes
# import psutil, pygetwindow as gw
# import win32process, my_utils
# import my_utils.util_, time

# time.sleep(1)
# hwnd = gw.getActiveWindow()._hWnd   # Replace this with a real window handle
# process_path = my_utils.util_.get_path_from_hwd(hwnd)
# print(f"Process Path: {process_path}")

from loge2 import hook, hook_mp

if __name__ == "__main__":
    import time
    def main_process_raw_input_callback(dx, dy, btn_flags, btn_data):
        if dx or dy:
            print(f"[Main Process Client] Mouse delta change detected: {dx:+d}, {dy:+d}")
        if btn_flags & hook.RI_MOUSE_LEFT_BUTTON_DOWN:
            print("[Main Process Client] Left Click down caught!")

    # Instantiate the wrapper utilizing MouseDeltaHook running out-of-process
    # Swap `run_on_other_process=False` to dynamically downgrade it to a basic background thread
    manager = hook_mp.MouseHookManager(
        hook_class=hook_mp.MouseDeltaHook, 
        callback=main_process_raw_input_callback,
        run_on_other_process=1
    )

    with manager:
        print(" -> Tracking relative deltas inside a distinct process context for 4 seconds...")
        time.sleep(4)

        print("\n -> ACTIVATING FREEZE SYSTEM-WIDE (Swallowing events on child process) for 4 seconds...")
        manager.block()
        time.sleep(4)

        print("\n -> RESTORING SYSTEM INTERACTION CONTROL for 3 seconds...")
        manager.unblock()
        time.sleep(3)

    print("Finished execution loop execution gracefully.")
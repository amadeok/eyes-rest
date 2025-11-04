import threading
import tkinter as tk, pygetwindow as gw
import time, pythoncom
from pycaw.pycaw import AudioUtilities
import winsound  # Windows only
from pynput.keyboard import Key, Controller

import my_utils.util_ as ut

keyboard = Controller()

# Configuration
class Context():
    def __init__(self):
        self.was_audio_playing = False
        self.unpause_timer = None
POP_UP_EVERY = 10 * 60      # seconds (600s = 10 minutes)
POP_UP_DURATION = 20        # seconds
CHECK_INTERVAL = 1          # seconds

ctx = Context()

# Hook registry: map title -> (pre_hook, post_hook)
def media_prehook_action():
    print("media_prehook_action")

    if is_audio_playing():
        print("Pausing audio")
        ctx.was_audio_playing = True
        keyboard.press(Key.media_play_pause)
        #time.sleep(0.01)
        keyboard.release(Key.media_play_pause)

def media_posthook_action(window):
    print("media_posthook_action")

    def task():

        if ctx.was_audio_playing:
            print("Unpausing media")
            try:
                ut.force_foreground(window._hWnd)
                time.sleep(0.03)
            except Exception as e:
                print(f"Error setting fore, {e}")
                
            for x in range(3):
                keyboard.press(Key.media_play_pause)
                time.sleep(0.01)
                keyboard.release(Key.media_play_pause)
                time.sleep(0.01)
        ctx.was_audio_playing = False
    ctx.unpause_timer = threading.Timer(0.5, task)
    ctx.unpause_timer.start()


HOOKS = {}

for elem in ["- mpv", "msedge.exe"]:
    HOOKS[elem] = ( media_prehook_action, media_posthook_action )

def is_audio_playing():
    pythoncom.CoInitialize()
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        
        if session.Process and session.Process.name()  == "parsecd.exe":
            continue
        if session.State == 1:  # 1 means active
            return True
    return False


    
import tkinter as tk
from screeninfo import get_monitors  # You may need: pip install screeninfo

def show_fullscreen_popup(window: gw.Win32Window, duration=POP_UP_DURATION):
    # Gather all monitors
    monitors = get_monitors()
    if not monitors:
        print("No monitors detected!")
        return

    title = window.title if window else ""
    print(f"Popup, window was: {title}")

    # Determine hooks once (same for all monitors)
    found = None
    for k, e in HOOKS.items():
        try:
            if ".exe" not in k:
                target_string = title.lower()
            else:
                target_string = ut.get_path_from_hwd(window._hWnd)
            if k.lower() in target_string:
                print(f"Found match: {k} -> {target_string}")
                found = k
                break
        except Exception as ex:
            print(f"Failed in hook loop: {ex}")

    pre_hook, post_hook = HOOKS.get(found, (None, None))
    if pre_hook:
        pre_hook()

    # Create one root per monitor
    roots = []
    closed_by_user = False
    start_time = time.time()

    def on_close():
        nonlocal closed_by_user
        closed_by_user = True

        if post_hook:
            post_hook(window)
            time.sleep(0.03)
        for root in roots:
            root.destroy()
        

    # Create a popup per monitor
    for m in monitors:
        root = tk.Tk()
        root.title("Eyes rest")
        root.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
        root.attributes("-topmost", True)
        root.configure(bg="black")
        root.overrideredirect(True)
        root.focus_set()

        root.bind("<Escape>", lambda e: on_close())
        root.bind("<Alt_L>", lambda e: on_close())

        label = tk.Label(
            root,
            text="Eyes rest",
            font=("Helvetica", 32, "bold"),
            fg="#999999",
            bg="black"
        )
        label.pack(expand=True)

        roots.append(root)

    roots[0].after(100,ut.force_foreground( int(roots[0].frame(), 16) ) )
    # Main update loop (manual event processing)
    #threading.Timer(0.1, lambda: ut.force_foreground( int(roots[0].frame(), 16) )).start( )
    try:
        while not closed_by_user and (time.time() - start_time) < duration:
            for root in roots:
                root.update()
            time.sleep(0.01)
    except tk.TclError:
        # Window(s) already destroyed
        pass
    finally:
        if not closed_by_user:
            # Timeout reached → run post-hook if not already run
            if post_hook and not closed_by_user:
                post_hook(window)
            for root in roots:
                try:
                    root.destroy()
                except:
                    pass

def main_loop():
    last_popup_time = time.time() - POP_UP_EVERY  # Trigger first popup after full interval
    print("Eye rest reminder started. Checking every 1 second...")
    beep_scheduled = False  # Prevent multiple beep sequences

    try:
        while True:
            now = time.time() 
            time_since_last = now - last_popup_time
            time_until_next = POP_UP_EVERY - time_since_last

            if time_until_next <= 0:
                # Time to show popup
                try:
                    window = gw.getActiveWindow()
                    show_fullscreen_popup(window, duration=POP_UP_DURATION)
                    last_popup_time = time.time()
                    beep_scheduled = False  # Reset for next cycle
                except Exception as e:
                    print(f"Error at main loop: {e}")
            else:
                # Print countdown
                mins = int(time_until_next // 60)
                secs = int(time_until_next % 60)
                print(f"Next popup in: {mins:02d}:{secs:02d}", end='\r', flush=True)

                # Trigger beep 3 times ~5 seconds before popup
                if not beep_scheduled and 0 < time_until_next <= 5:
                    beep_scheduled = True
                    for i in range(3):
                        winsound.Beep(800, 300)  # Frequency=800Hz, Duration=300ms
                        time.sleep(0.2)  # Small gap between beeps

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main_loop()
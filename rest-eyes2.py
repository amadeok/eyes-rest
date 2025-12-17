import threading
import tkinter as tk, pygetwindow as gw
import time, pythoncom
from pycaw.pycaw import AudioUtilities
import winsound  # Windows only
from pynput.keyboard import Key, Controller
import settingsManager
import win32api
import msvcrt
import my_utils.util_ as ut
import win32con

keyboard = Controller()

# Configuration
class Context():
    def __init__(self):
        self.was_audio_playing = False
        self.unpause_timer = None
        self.controller = None
        self.ignore_procs = []
        self.block_input = False
        self.settings_man = settingsManager.SettingsManager(defaults={"ignore_procs", "block_input"}, target=self)
        self.settings_man.load_settings()
        self.hook = None
        try:
            import PyHookCpp
            self.hook = PyHookCpp.InputHookController()
        except:
            print("Failed to import PyHookCpp")
        
POP_UP_EVERY = 10 * 60      # seconds (600s = 10 minutes)
POP_UP_DURATION = 20        # seconds
CHECK_INTERVAL = 1          # seconds

ctx = Context()


# Hook registry: map title -> (pre_hook, post_hook)
def media_prehook_action():
    program_playing_audio =  is_audio_playing(ctx.ignore_procs)
    print("media_prehook_action,", program_playing_audio)
    
    if program_playing_audio:
        print("Pausing audio, program_playing_audio:", program_playing_audio )
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
                
            for x in range(5):
                print("Resuming audio attempt: ",x+1)
                keyboard.press(Key.media_play_pause)
                time.sleep(0.01)
                keyboard.release(Key.media_play_pause)
                time.sleep(0.01)
                time.sleep(0.5)
                if is_audio_playing(ctx.ignore_procs):
                    break
                
        ctx.was_audio_playing = False
    ctx.unpause_timer = threading.Timer(0.5, task)
    ctx.unpause_timer.start()


HOOKS = {}

for elem in ["- mpv", "msedge.exe"]:
    HOOKS[elem] = ( media_prehook_action, media_posthook_action )

def is_audio_playing(ignore_procs):
    pythoncom.CoInitialize()
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        proc_name = session.Process.name() if session.Process and session.Process.name() else None
        if proc_name  in ignore_procs:
            continue
        if session.State == 1:  # 1 means active
            return proc_name
    return False


# while 1:
#     print( is_audio_playing(ctx.ignore_procs))
#     time.sleep(0.1)
import tkinter as tk
from screeninfo import get_monitors  # You may need: pip install screeninfo

def show_fullscreen_popup(window: gw.Win32Window, duration=POP_UP_DURATION):
    monitors = get_monitors()
    if not monitors:
        print("No monitors detected!")
        return

    title = window.title if window else ""
    print(f"Popup, window was: {title}")

    found = None
    if title:
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

    roots = []
    closed_by_user = False
    start_time = time.time()

    def on_close():
        nonlocal closed_by_user
        closed_by_user = True
        if post_hook:
            post_hook(window)
        for root in roots:
            try:
                root.destroy()
            except:
                pass

    # Create popup per monitor
    for m in monitors:
        root = tk.Tk()
        root.title("Eyes rest")
        root.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
        root.attributes("-topmost", True)
        root.configure(bg="black")
        root.overrideredirect(True)
        root.focus_set()

        label = tk.Label(
            root,
            text=".",
            font=("Helvetica", 32, "bold"),
            fg="#999999",
            bg="black"
        )
        label.pack(expand=True)
        roots.append(root)

    # Force foreground once
    
    def set_fore():
        try:
            print("Set fore")
            ut.force_foreground(int(roots[0].frame(), 16))
        except Exception as e:
            print(f"Foreground error: {e}")
            
    root.after(200, set_fore)
    
    if ctx.block_input and ctx.hook:
        ctx.hook.start_hook()
        time.sleep(0.1)
        ctx.hook.set_mouse_block(True)
        ctx.hook.set_keyboard_block(True)
    # print("pre loop")
    try:
        while True:
        # while not closed_by_user and (time.time() - start_time) < duration:
            # Poll for Escape or Alt
            
            if win32api.GetAsyncKeyState(win32con.VK_ESCAPE) & 0x8000:
                on_close()
                break
            if win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000:  # Alt key
                on_close()
                if  (win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000):
                    print("Pausing..")
                    ctx.controller.paused = True
                break

            for root in roots:
                root.update()
            time.sleep(0.01)
            if closed_by_user:
                print("closed by user")
                break
            if (time.time() - start_time) > duration:
                print("closed by timeout")
                break
    except tk.TclError as e:
        print("--------> Error tlc: ", e)
        pass
    finally:
        if ctx.block_input and ctx.hook:
            ctx.hook.set_mouse_block(False)
            ctx.hook.set_keyboard_block(False)
            time.sleep(0.1)
            ctx.hook.end_hook()
            time.sleep(0.1)
        if not closed_by_user:
            if post_hook:
                post_hook(window)
            for root in roots:
                try:
                    root.destroy()
                except:
                    pass
        

                
                
                
class MainController:
    def __init__(self):
        self.paused = False
        self.lock = threading.Lock()
        self._start_input_thread()

    def _start_input_thread(self):
        def listen():
            while True:
                try:
                    key = msvcrt.getch().decode('utf-8').lower()
                    if key == 'p':
                        with self.lock:
                            self.paused = not self.paused
                            state = "PAUSED" if self.paused else "RESUMED"
                            print(f"\nProgram {state}. Press 'p' again to toggle.")
                    if key == 'b':
                        ctx.block_input = not ctx.block_input
                        ctx.settings_man.queue_save()
                        print("Blocking input: ", ctx.block_input)
                except Exception as e:
                    print(f"Input thread error: {e}")
        threading.Thread(target=listen, daemon=True, name="InputListener").start()

    def is_paused(self):
        with self.lock:
            return self.paused
        
def main_loop():
    ctx.controller = MainController()  # ← Add this
    last_popup_time = time.time() - POP_UP_EVERY + 5
    print("Eye rest reminder started. Checking every 1 second...")
    print("Press 'p' anytime to pause/resume.")
    beep_scheduled = False

    try:
        while True:
            # Respect pause state
            if ctx.controller.is_paused():
                print("Paused. Waiting...", end='\r')
                time.sleep(CHECK_INTERVAL)
                continue

            now = time.time()
            time_since_last = now - last_popup_time
            time_until_next = POP_UP_EVERY - time_since_last

            if time_until_next <= 0:
                try:
                    window = gw.getActiveWindow()
                    show_fullscreen_popup(window, duration=POP_UP_DURATION)
                    last_popup_time = time.time()
                    beep_scheduled = False
                except Exception as e:
                    print(f"Error at main loop: {e}")
            else:
                mins = int(time_until_next // 60)
                secs = int(time_until_next % 60)
                print(f"Next popup in: {mins:02d}:{secs:02d}", end='\r', flush=True)

                if not beep_scheduled and 1 < time_until_next <= 5:
                    beep_scheduled = True
                    for i in range(3):
                        winsound.Beep(800, 300)
                        time.sleep(0.2)

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main_loop()
import msvcrt
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import pygetwindow as gw
import time, json, os
import pythoncom
from pycaw.pycaw import AudioUtilities
import winsound
import win32api, win32con
# import keyboard
import loge2.bg_keyboard  as bg_keyboard
from  keyboard import press_and_release
import my_utils.util_ as ut
import settingsManager

# Configuration
# POP_UP_EVERY = 10 * 60
# POP_UP_DURATION = 20
CHECK_INTERVAL = 1


class EyeRestApp:
    def _schedule_auto_unpause(self):
        if self.auto_resume_minutes and self.auto_unpause_timer:
            self.auto_unpause_timer.cancel()
        if self.auto_resume_minutes:
            self.auto_unpause_timer = threading.Timer(self.auto_resume_minutes * 60, self._auto_unpause)
            self.auto_unpause_timer.daemon = True
            self.auto_unpause_timer.start()
            self.pause_start_time = time.time()

    def _auto_unpause(self):
        if self.paused:
            self.paused = False
            self.pause_start_time = None

    def get_time_until_auto_unpause(self):
        if not self.paused or not self.pause_start_time or not self.auto_resume_minutes:
            return None
        remaining = self.auto_resume_minutes * 60 - (time.time() - self.pause_start_time)
        return max(0, remaining)
    
    @property
    def auto_resume_minutes(self):
        return self.resume_var.get()
    
    def __init__(self):
        self.paused = False
        self.pause_start_time = None

        self.auto_unpause_timer = None
        # threading.Thread(target=self._input_listener, daemon=True).start()

        self.settings = self.load_settings()
        self.popup_count = 0
        self.session_start = time.time()
        self.total_break_time = 0
        
        self.root = tk.Tk()
        self.root.title("👁️ Eye Rest Reminder")
        self.root.geometry("400x600")
        self.root.configure(bg="#2b2b2b")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.ignore_procs = []
                
        self.block_var = tk.BooleanVar(value=False)
        self.beep_var = tk.BooleanVar(value=True)
        self.interval_var = tk.DoubleVar(value=10)
        self.duration_var = tk.IntVar(value=20)
        self.resume_var = tk.IntVar(value=0)

        def task(*args): self.last_popup_time = time.time()
        self.interval_var.trace_add("write", task)

        self.settings_man = settingsManager.SettingsManager(defaults={"ignore_procs", "block_var", "interval_var", 
                                                                       "duration_var", "resume_var"}, target=self)
        self.settings_man.load_settings()
        self.last_popup_time = time.time() - self.pop_up_every + 5

        self._create_widgets()
        self.center_window()
        
        self.HOOKS = {elem: (self.media_prehook_action, self.media_posthook_action) for elem in ["- mpv", "msedge.exe"]}
        threading.Thread(target=self._main_loop, daemon=True).start()
        threading.Thread(target=self._update_display, daemon=True).start()
        self.was_audio_playing = False
        self.unpause_timer = None
        
        def task(e):
            return
            # print(self.popup_shown.is_set())
            if  self.block_input and self.popup_shown.is_set() :
                return False
            return True
        
        # bg_keyboard.hook(task)
        
        self.hook = None
        try:
            from loge2.hook_mp import MouseHookManager
            self.hook = MouseHookManager(lambda *args: 1, run_on_other_process=1)
            self.hook.start()
        except Exception as e:
            print("Failed to import hook", e)
        self.popup_shown = threading.Event()
        self.root.mainloop()

    

    @property
    def pop_up_every(self):
        try:
            return max(self.interval_var.get(), 0.5) * 60
        except Exception as e:
            # print("Error in pop_up_every", e)
            return 10 * 60

    def _block_input(self):
        bg_keyboard.block_all_keys()
        self.hook.block()

    def unblock_input(self):
        bg_keyboard.unblock_all_keys()
        self.hook.unblock()
    
    @property
    def block_input(self):
        return self.block_var.get()
        
    def load_settings(self):
        defaults = {"popup_interval": 600, "popup_duration": 20, "auto_resume_minutes": 30, 
                   "block_input": True, "beep_warning": True}
        try:
            if os.path.exists("eye_rest_settings.json"):
                with open("eye_rest_settings.json") as f:
                    saved = json.load(f)
                    defaults.update(saved)
        except: pass
        return defaults

    def save_settings(self):
        try:
            with open("eye_rest_settings.json", "w") as f:
                json.dump(self.settings, f, indent=2)
        except: pass

    def _create_widgets(self):
        colors = {"bg": "#2b2b2b", "fg": "#ffffff", "btn_bg": "#3c3c3c", "entry_bg": "#3c3c3c"}
        
        # Header
        tk.Label(self.root, text="👁️ Eye Rest Reminder", font=("Arial", 16, "bold"),
                bg=colors["bg"], fg=colors["fg"]).pack(pady=10)
        
        # Status Frame
        status_frame = tk.Frame(self.root, bg=colors["bg"])
        status_frame.pack(pady=10, fill="x", padx=20)
        
        self.status_label = tk.Label(status_frame, text="Status: Active", font=("Arial", 12),
                                     bg=colors["bg"], fg="#4CAF50")
        self.status_label.pack()
        
        self.time_label = tk.Label(status_frame, text="Next break: --:--", font=("Arial", 14, "bold"),
                                   bg=colors["bg"], fg=colors["fg"])
        self.time_label.pack(pady=5)
        
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', pady=10, padx=20)
        
        # Settings Frame
        settings_frame = tk.LabelFrame(self.root, text="⚙️ Settings", font=("Arial", 11, "bold"),
                                       bg=colors["bg"], fg=colors["fg"], padx=15, pady=10)
        settings_frame.pack(pady=10, fill="x", padx=20)
        


        # Popup Interval
        tk.Label(settings_frame, text="Popup Interval (minutes):", font=("Arial", 10),
                bg=colors["bg"], fg=colors["fg"]).grid(row=0, column=0, sticky="w", pady=5)

        interval_entry = tk.Entry(settings_frame, textvariable=self.interval_var, width=10,
                                  bg=colors["entry_bg"], fg=colors["fg"])
        interval_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # Popup Duration
        tk.Label(settings_frame, text="Popup Duration (seconds):", font=("Arial", 10),
                bg=colors["bg"], fg=colors["fg"]).grid(row=1, column=0, sticky="w", pady=5)
        duration_entry = tk.Entry(settings_frame, textvariable=self.duration_var, width=10,
                                  bg=colors["entry_bg"], fg=colors["fg"])
        duration_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # Auto Resume
        tk.Label(settings_frame, text="Auto-resume (minutes, 0=off):", font=("Arial", 10),
                bg=colors["bg"], fg=colors["fg"]).grid(row=2, column=0, sticky="w", pady=5)
        resume_entry = tk.Entry(settings_frame, textvariable=self.resume_var, width=10,
                                bg=colors["entry_bg"], fg=colors["fg"])
        resume_entry.grid(row=2, column=1, padx=10, pady=5)
        
        # # Checkboxes
        # self.block_var.set(self.settings["block_input"])
        # self.beep_var.set(self.settings["beep_warning"])
        
        tk.Checkbutton(settings_frame, text="Block input during break", variable=self.block_var,
                      bg=colors["bg"], fg=colors["fg"], selectcolor=colors["bg"]).grid(
                      row=3, column=0, columnspan=2, sticky="w", pady=5)
        
        tk.Checkbutton(settings_frame, text="Beep warning before popup", variable=self.beep_var,
                      bg=colors["bg"], fg=colors["fg"], selectcolor=colors["bg"]).grid(
                      row=4, column=0, columnspan=2, sticky="w", pady=5)
        
        
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', pady=10, padx=20)
        
        # Control Buttons Frame
        btn_frame = tk.Frame(self.root, bg=colors["bg"])
        btn_frame.pack(pady=10)
        
        self.pause_btn = tk.Button(btn_frame, text="⏸️ Pause", command=self.toggle_pause,
                                  font=("Arial", 11), bg=colors["btn_bg"], fg=colors["fg"], width=12)
        self.pause_btn.pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="📊 Stats", command=self.open_stats,
                 font=("Arial", 11), bg=colors["btn_bg"], fg=colors["fg"], width=12).pack(side="left", padx=5)
        
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', pady=10, padx=20)
        
        # Tips
        info = tk.Label(self.root, text="💡 Tips:\n• Press 'p' to pause/resume\n• Press 'b' to toggle input blocking",
                       font=("Arial", 9), bg=colors["bg"], fg=colors["fg"], justify="left")
        info.pack(pady=10, fill="both", expand=True, padx=20)
        
        # Version
        tk.Label(self.root, text="v2.0", font=("Arial", 8), bg=colors["bg"], fg="gray").pack(side="bottom", pady=5)


    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_start_time = time.time()
        self.pause_btn.config(text="▶️ Resume" if self.paused else "⏸️ Pause")
        if not self.paused and self.auto_unpause_timer:
            self.auto_unpause_timer.cancel()

    def open_stats(self):
        win = tk.Toplevel(self.root)
        win.title("Statistics")
        win.geometry("350x250")
        win.configure(bg="#2b2b2b")
        win.transient(self.root)
        
        session_mins = int((time.time() - self.session_start) / 60)
        stats = [
            ("Session Duration:", f"{session_mins} minutes"),
            ("Breaks Taken:", self.popup_count),
            ("Total Rest Time:", f"{int(self.total_break_time / 60)} minutes"),
            ("Status:", "Paused" if self.paused else "Active")
        ]
        
        for i, (label, value) in enumerate(stats):
            tk.Label(win, text=label, font=("Arial", 10, "bold"), bg="#2b2b2b", fg="white"
                    ).grid(row=i, column=0, sticky="w", padx=20, pady=5)
            tk.Label(win, text=str(value), font=("Arial", 10), bg="#2b2b2b", fg="white"
                    ).grid(row=i, column=1, sticky="w", padx=10, pady=5)
        
        def reset():
            self.popup_count = 0
            self.session_start = time.time()
            self.total_break_time = 0
            win.destroy()
            messagebox.showinfo("Stats Reset", "Statistics reset!")
        
        tk.Button(win, text="Reset Stats", command=reset, bg="#FF9800", fg="white",
                 padx=20).grid(row=4, column=0, columnspan=2, pady=20)

    def center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - self.root.winfo_height()) // 2
        self.root.geometry(f"+{x}+{y}")

    def show_popup(self, window):
        found = None
        self.popup_shown.set()
        if window.title:
            for k in self.HOOKS.keys():
                try:
                    target = window.title.lower() if ".exe" not in k else ut.get_path_from_hwd(window._hWnd)
                    if k.lower() in target:
                        found = k
                        break
                except: pass
        
        pre_hook, post_hook = self.HOOKS.get(found, (None, None))
        if pre_hook:
            pre_hook()
        
        from screeninfo import get_monitors
        roots = []
        closed_by_user = False
        start_time = time.time()
        
        def on_close():
            self.popup_shown.clear()
            nonlocal closed_by_user
            closed_by_user = True
            if post_hook:
                post_hook(window)
            for r in roots:
                try: r.destroy()
                except: pass
        
        for m in get_monitors() or [type('', (), {'width': 1920, 'height': 1080, 'x': 0, 'y': 0})()]:
            root = tk.Tk()
            root.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
            root.attributes("-topmost", True)
            root.configure(bg="black")
            root.overrideredirect(True)
            tk.Label(root, text=".", font=("Helvetica", 32, "bold"), fg="#999999", bg="black"
                    ).pack(expand=True)
            roots.append(root)
        
        if self.block_input and self.hook:
            self._block_input()
        
        def is_key_pressed(key):
            return bg_keyboard.is_pressed(key)
            return win32api.GetAsyncKeyState(key) & 0x8000 #win32con.VK_ESCAPE # win32con.VK_MENU
        try:
            while not closed_by_user and (time.time() - start_time) < self.duration_var.get():
                # if any(is_key_pressed(key) for key in ["esc", "alt"]):
                #     print("canceled by keypress ")
                #     on_close()
                #     break
                for root in roots:
                    root.update()
                time.sleep(0.01)
        except Exception as e:
            print(e)
            pass
        finally:
            self.popup_shown.clear()
            if self.block_input and self.hook:
                self.unblock_input()
            if not closed_by_user and post_hook:
                post_hook(window)
            for root in roots:
                try: root.destroy()
                except: pass

    def _main_loop(self):
        beep_scheduled = False
        while True:
            if self.paused:
                time.sleep(CHECK_INTERVAL)
                continue
            
            now = time.time()
            if now - self.last_popup_time >= self.pop_up_every:
                try:
                    self.show_popup(gw.getActiveWindow())
                    self.last_popup_time = now
                    self.popup_count += 1
                    self.total_break_time += self.duration_var.get()
                    beep_scheduled = False
                except Exception as e:
                    print(f"Error: {e}")
            elif self.settings["beep_warning"] and not beep_scheduled and 1 < (self.pop_up_every - (now - self.last_popup_time)) <= 5:
                beep_scheduled = True
                for _ in range(3):
                    winsound.Beep(800, 300)
                    time.sleep(0.2)
            time.sleep(CHECK_INTERVAL)

    def _update_display(self):
        while True:
            try:
                if self.root.winfo_exists():
                    if self.paused:
                        remaining = self.get_time_until_auto_unpause()
                        if remaining and remaining > 0:
                            # Show auto-resume countdown
                            mins = int(remaining // 60)
                            secs = int(remaining % 60)
                            text = f"Auto-resume: {mins:02d}:{secs:02d}"
                            self.status_label.config(text=f"Status: Paused - {text}", fg="#FF9800")
                            self.time_label.config(text="")
                        else:
                            # Paused without auto-resume or timer expired
                            self.status_label.config(text="Status: Paused", fg="#FF9800")
                            self.time_label.config(text="")
                    else:
                        remaining = max(0, self.pop_up_every - (time.time() - self.last_popup_time))
                        self.status_label.config(text="Status: Active", fg="#4CAF50")
                        self.time_label.config(text=f"Next break: {int(remaining//60):02d}:{int(remaining%60):02d}")
                time.sleep(0.5)
            except: break

    def on_closing(self):
        # if messagebox.askokcancel("Quit", "Quit Eye Rest Reminder?"):
        self.root.destroy()
        import sys
        sys.exit(0)


    def is_audio_playing(self, ignore_procs):

        pythoncom.CoInitialize()
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            proc_name = session.Process.name() if session.Process and session.Process.name() else None
            if proc_name not in ignore_procs and session.State == 1:
                return proc_name
        return False

    def media_prehook_action(self):
        program_playing_audio = self.is_audio_playing(self.ignore_procs)
        if program_playing_audio:
            self.was_audio_playing = True
            press_and_release('play/pause media')

    def media_posthook_action(self, window):
        def task():
            if self.was_audio_playing:
                try:
                    ut.force_foreground(window._hWnd)
                    time.sleep(0.03)
                except Exception as e:
                    print(f"Error setting fore, {e}")
                for _ in range(5):
                    press_and_release('play/pause media')
                    time.sleep(0.5)
                    if self.is_audio_playing(self.ignore_procs):
                        break
            self.was_audio_playing = False
        self.unpause_timer = threading.Timer(0.5, task)
        self.unpause_timer.start()

    

if __name__ == "__main__":
    app = EyeRestApp()
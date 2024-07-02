import keyboard, pygetwindow as gw
from time import sleep
from pynput.mouse import Controller
from contextlib import nullcontext
from logging import disable
import pyautogui, winsound
import threading
import sys
import msvcrt
from time import time, sleep
import PySimpleGUI as sg
import datetime
from ctypes import *
import win32gui
import win32file
import re
import win32com.client
import pythoncom
try:
    import pyHook
except:
    print(r"failed to load pyHook, use python 3.7 and run C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python37\python -m pip install pyHook-1.5.1-cp37-cp37m-win_amd64.whl")
    exit()
import os
from threading import Timer
from playsound import playsound

audio_file = os.path.dirname(__file__)+"\\alarm.wav"
conf_file = os.path.dirname(__file__)+"\\settings.conf"
pop_up_every = 10*60
pop_up_duration = 20
play_sound = 1
block_input = 1
force_rest_time = 1
size = pyautogui.size()


class context:
    def __init__(self):
        self.window = None


ctx = context()


def locate_usb():  # this will check any external Drives
    drive_list = []
    drivebits = win32file.GetLogicalDrives()
    # print(drivebits)
    for d in range(1, 26):
        mask = 1 << d
        if drivebits & mask:
            # here if the drive is at least there
            drname = '%c:\\' % chr(ord('A') + d)
            t = win32file.GetDriveType(drname)
            if t == win32file.DRIVE_REMOVABLE:
                drive_list.append(drname)
    return drive_list


class blockInput():
    def OnKeyboardEvent(self, event):
        return False

    def OnMouseEvent(self, event):
        return False

    def unblock(self):

        try:
            self.hm.UnhookKeyboard()
        except:
            pass
        try:
            self.hm.UnhookMouse()
        except:
            pass

    def block(self, keyboard=True, mouse=True):

        while(1):
            if mouse:
                self.hm.MouseAll = self.OnMouseEvent
                self.hm.HookMouse()
            if keyboard:
                self.hm.KeyAll = self.OnKeyboardEvent
                self.hm.HookKeyboard()
            win32gui.PumpWaitingMessages()
            # cg = locate_usb()
            # if cg:
            #    break
            sleep(0.1)

    def __init__(self):
        self.hm = pyHook.HookManager()


def put_on_foreground():
    def windowEnumerationHandler(hwnd, top_windows):
        """Add window title and ID to array."""
        top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))
    found = False
    top_windows = []
    win32gui.EnumWindows(windowEnumerationHandler, top_windows)
    for i in top_windows:
        if "eyes rest pop up" in i[1].lower():
            win32gui.SetForegroundWindow(i[0])
            found = True
            return True
    if found == False:
        print("Window not found")
    return False

import configparser

config = configparser.ConfigParser()

config.read('settings.ini')

# Access the settings
pop_up_every = config.getint('PopupSettings', 'Pop up every (minutes)')*60
pop_up_duration = config.getint('PopupSettings', 'Pop up duration (seconds)')
play_sound = config.getboolean('PopupSettings', 'Play sound before pop up')
block_input = config.getboolean('PopupSettings', 'Block mouse and keyboard during pop up')
press_key = config.get('PopupSettings', 'Press key before and after popup')
press_key_active = len(press_key)

# if os.path.isfile(conf_file):
#     print("Reading settings file..")
#     try:
#         with open(conf_file, 'r') as input_:
#             settings = input_.read().splitlines()
#             if len(settings):
#                 pop_up_every = int(settings[0].split(":")[1])*60
#             if len(settings) > 1:
#                 pop_up_duration = int(settings[1].split(":")[1])
#             if len(settings) > 2:
#                 play_sound = int(settings[2].split(":")[1])
#             if len(settings) > 3:
#                 block_input = int(settings[3].split(":")[1])

#     except Exception as e:
#         print("Error while reading settings file:", e)

if block_input:
    force_rest_time = 1
else:
    force_rest_time = 0


def is_enabled(setting):
    if setting:
        return "enabled"
    else:
        return "disabled"


block = blockInput()
sg.theme('Black')


def blockinput_start():
    mouse = Controller()
    global block_input_flag
    for i in range(150):
        keyboard.block_key(i)
    while block_input_flag == 1:
        mouse.position = (0, 0)
        sleep(0.01)


def blockinput_stop():
    global block_input_flag
    for i in range(150):
        keyboard.unblock_key(i)
    block_input_flag = 0


def blockinput():
    global block_input_flag
    block_input_flag = 1
    t1 = threading.Thread(target=blockinput_start)
    t1.start()
    print("[SUCCESS] Input blocked!")


def unblockinput():
    blockinput_stop()
    print("[SUCCESS] Input unblocked!")


print(
    f"Starting..\nPop up every {pop_up_every/60} minutes with duration {pop_up_duration} seconds")
print(
    f"Playing sound before pop up is {is_enabled(play_sound)}, blocking input during pop up is {is_enabled(block_input)}")
args = sys.argv
if len(args) == 3:
    pop_up_every = int(args[1])
    pop_up_duration = int(args[2])
pyautogui.FAILSAFE = False
prev_time = time()
prev_time2 = time()
exiting = False


def check_key_presses():
    global exiting, pop_up_every, pop_up_duration, prev_time2
    x = ""
    while 1:  # ESC
        try:
            x = msvcrt.getch().decode('UTF-8')
        except Exception as e:
            print(e)
            continue
        if x == 'r' or x == "R":
            prev_time2 = time()
            print("Timer resetted")
        elif x == '1':
            pop_up_every -= 60
            print("Pop up every ", pop_up_every/60, " minutes")
        elif x == '2':
            pop_up_every += 60
            print("Pop up every ", pop_up_every/60, " minutes")
        elif x == '3':
            pop_up_duration -= 1
            print("Pop up duration ", pop_up_duration, " seconds")
        elif x == '4':
            pop_up_duration += 1
            print("Pop up duration ", pop_up_duration, " seconds")
        elif x == 'q' or x == 'Q':
            print("exiting")
            exiting = True
            sys.exit()
        elif x == 'k' or x == 'K':
            global block_input; global force_rest_time
            block_input = not block_input
            force_rest_time = not force_rest_time
            print(f"{'Not b' if not block_input else 'B'}locking input during popup")
        elif x == "s" or x == "S":
            global play_sound
            play_sound = not play_sound
            print(f"{'Not p' if not play_sound else 'P'}laying sound before popup")
        elif x == "p" or x == "P":
            global press_key_active
            global press_key
            press_key_active = not press_key_active
            print(f"{'Not p' if not press_key_active else 'P'}ressing key  {press_key} before and after popup")
            


print("Starting key press checker..")
thread1 = threading.Thread(target=check_key_presses,)
thread1.start()
thread_reminder_delta = 0


def thread_reminder(seconds, ctx):

    prev_time = time()
    global thread_reminder_delta
    time_string = ""
    print(f"Showing pop up..")
    try:
        while time() - prev_time < seconds:
            if block_input:
                blockinput()
                sleep(1)
                unblockinput()
            else:
                sleep(1)

            thread_reminder_delta = seconds - (time() - prev_time)
            time_string = f'Pop up will close in:  {format(seconds - (time() - prev_time), ".2f")} seconds'
            print(time_string)
            if ctx.window != None:
                ctx.window['-TEXT-'].update(time_string)
            elif not force_rest_time:
                break

    except Exception as e:
        print("error ", e)

    thread_reminder_delta = 0
    try:
        if ctx.window != None:
            ctx.window.write_event_value('Alarm', "1 minute passed")
    except Exception as e:
        print("error ", e)


print("Starting loop..")

def   press_key_fun(press_key):
    print("pressing key ", press_key)
    pyautogui.press(press_key)
    sleep(0.1)

while 1:
    exiting = False
    # layout = [ [sg.Button('Close')],[sg.Text('', key='-TEXT-', justification='center')] ]
    # window = sg.Window('Eyes rest pop up', layout,size=(size.width, size.height))
    aw = gw.getActiveWindow()
    mpos = pyautogui.position()
    print("aw is ", aw.title if aw else "no window")
    if press_key_active:
        press_key_fun(press_key)
    
    column_to_be_centered = [[sg.Text('Eyes Rest')],
                             [sg.Text(size=(30, 1), key='-TEXT-')],
                             [sg.Button('Exit')]]

    layout = [[sg.Text(key='-EXPAND-', font='ANY 1', pad=(0, 0))],  # the thing that expands from top
              [sg.Text('', pad=(0, 0), key='-EXPAND2-'),
              sg.Column(column_to_be_centered, vertical_alignment='center', justification='center',  k='-C-')]]

    ctx.window = sg.Window('Eyes Rest', layout, resizable=True,
                           finalize=True, size=(size.width, size.height), no_titlebar=True)
    ctx.window['-C-'].expand(True, True, True)
    ctx.window['-EXPAND-'].expand(True, True, True)
    ctx.window['-EXPAND2-'].expand(True, False, True)
    
    w = gw.getWindowsWithTitle('Eyes Rest')
    for x in range(5):
        try:
            sleep(0.1)
            win32gui.SetForegroundWindow(w[0]._hWnd)
            break
        except:
            print("error");pass

    threading.Thread(target=thread_reminder, args=(pop_up_duration, ctx), daemon=True).start()

    while True:
        event, values = ctx.window.read()
        if event == sg.WIN_CLOSED or event == 'Exit':
            break
        elif event == 'Alarm':
            message = values[event]
            break
    ctx.window.close()
    ctx.window = None
    if exiting:
        break

    if thread_reminder_delta != 0 and force_rest_time:
        print("You closed the window but.. ", thread_reminder_delta)
        prev_time = time()
        if thread_reminder_delta > 0:
            while time() - prev_time < thread_reminder_delta:
                if block_input:
                    blockinput()
                    sleep(1)
                    unblockinput()
                else:
                    sleep(1)
                print(
                    f"Pause time remaining  {(format(thread_reminder_delta - (time() - prev_time), '.2f'))} seconds")
                
    if block_input:
        pyautogui.moveTo(mpos)
        #winsound.Beep(600, 200)
    
    if aw:
        try:
            print("restoring previous active window ", aw.title)
            win32gui.SetForegroundWindow(aw._hWnd) 
            sleep(0.1)
            print("active win", gw.getActiveWindow().title)
        except: 
            print("error restoring active window")
    else: print("not restoring active window because not window")        
    
    
    if press_key_active:
        press_key_fun(press_key)    
        
    prev_time2 = time()
    while (time() - prev_time2 < pop_up_every):
        if play_sound:
            if pop_up_every - (time() - prev_time2) < 9:
                print("Playing alarm sound..")
                try:
                    for x in range(3):
                        winsound.Beep(400, 500)
                        sleep(0.1)

                    #playsound(audio_file)
                except Exception as e:
                    print("Error playing sound: ", e)
                    print(
                        "Try installing playsound 1.2.2: pip install playsound==1.2.2")

        if exiting:
            sys.exit()
        delta = pop_up_every - (time() - prev_time2)
        # + f" Current time: {time():1f}, previous time: {prev_time2:1f}")
        print(f" Time until next pop up: " +
              '{:0>4},'.format(str(datetime.timedelta(seconds=delta))))
        sleep(5)

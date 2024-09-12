import customtkinter as ctk
import subprocess
import threading
import time
import re
import json
import os
import sys

import usb_util_windows

class SidebarFrame(ctk.CTkFrame):
    def __init__(self, master, app_instance, **kwargs):#Widget Placement
        super().__init__(master, width=140, corner_radius=0, **kwargs)
        self.app_instance = app_instance

        self.sidebar_label_logo1 = ctk.CTkLabel(self, text="Watchman", font=("Arial Bold", 20),text_color=("#696969", "#DCE4EE"))
        self.sidebar_label_logo1.grid(row=0, column=0, padx=13, pady=(27, 0), sticky="w")
        self.sidebar_label_logo2 = ctk.CTkLabel(self, text="Pairing Assistant", font=("Arial Bold", 20),text_color=("#696969", "#DCE4EE"))
        self.sidebar_label_logo2.grid(row=1, column=0, padx=13, pady=(0, 27))
        self.sidebar_button_reload = ctk.CTkButton(self,text="Reload", font=("Arial Bold", 12), fg_color=("#a9a9a9","#808080"),hover_color=("#696969","#696969"), command=self.sidebar_button_reload_callback)
        self.sidebar_button_reload.grid(row=2, column=0, padx=20, pady=10)
        self.sidebar_button_pairall = ctk.CTkButton(self,text="PairAll", font=("Arial Bold", 12),command=lambda:self.sidebar_button_callback("pairall"))
        self.sidebar_button_pairall.grid(row=3, column=0, padx=20, pady=10)
        self.sidebar_button_force_pairall = ctk.CTkButton(self,text="ForcePairAll", font=("Arial Bold", 12),command=lambda:self.sidebar_button_callback("forcepairall"))
        self.sidebar_button_force_pairall.grid(row=4, column=0, padx=20, pady=10)
        self.sidebar_button_unpairall = ctk.CTkButton(self,text="UnpairAll", font=("Arial Bold", 12),command=lambda:self.sidebar_button_callback("unpairall"))
        self.sidebar_button_unpairall.grid(row=5, column=0, padx=20, pady=10)
        self.sidebar_button_dongleresetall = ctk.CTkButton(self,text="DongleResetAll", font=("Arial Bold", 12),fg_color="transparent",hover_color=("#696969","#808080"), border_width=2,border_color=("#a9a9a9","#c0c0c0"),text_color=("#696969", "#DCE4EE"),
                                                      command=lambda:self.sidebar_button_callback("dongleresetall"))
        self.sidebar_button_dongleresetall.grid(row=6, column=0, padx=20, pady=10)

    def sidebar_button_reload_callback(self):#Function to reload device
        app_instance = self.master
        exe_path = self.app_instance.get_exe_path()
        output = app_instance.execute_subprocess("serial", exe_path)
        device_serials = app_instance.extract_device_serials(output)
        if device_serials:
            app_instance.insert_log("Recognized devices : " + ", ".join(device_serials))

        app_instance.scrollable_frame.update_device_frames(device_serials,app_instance)
        threading.Thread(target=app_instance.check_status).start()

        app_instance.insert_log("Reloaded devices")
        
    def sidebar_button_callback(self, command):#Processing when a button on the sidebar is pressed
        app_instance = self.master
        exe_path = self.app_instance.get_exe_path() 
        
        def delayed_function():#Process to be executed after 5 seconds
            app_instance.check_status()
            if command == "pairall":
                self.sidebar_button_pairall.configure(text="PairAll", state="normal")
            elif command == "forcepairall":
                self.sidebar_button_force_pairall.configure(text="ForcePairAll", state="normal")
    
        if command == "pairall":
            self.sidebar_button_pairall.configure(text="Pairing...",state="disabled")
        elif command == "forcepairall":
            self.sidebar_button_force_pairall.configure(text="Pairing...",state="disabled")
        
        threading.Thread(target=lambda: app_instance.execute_subprocess(command, exe_path)).start()
        threading.Timer(5, delayed_function).start()

        app_instance.insert_log("Executed command: " + command)

class ScrollableFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.device_frames = []

    def update_device_frames(self, device_serials,app_instance):#Device frames placement
        self.clear_device_frames()
        
        for i, serial in enumerate(device_serials):
            self.device_frame = DeviceFrame(self, fg_color=['#cfcfcf', '#333333'], serial=serial,app_instance=app_instance)
            self.device_frame.grid(row=i, column=0, padx=(10, 10), pady=(10, 10), sticky="nsew")
            self.device_frame.grid_columnconfigure(3, weight=1)
            self.device_frames.append(self.device_frame)

    def clear_device_frames(self):#Clear device frames
        for frame in self.device_frames:
            frame.grid_forget()
            frame.destroy()
            
        self.device_frames = []

class DeviceFrame(ctk.CTkFrame):
    def __init__(self, master, serial, app_instance, **kwargs):#Widget Placement
        super().__init__(master, **kwargs)
        self.app_instance = app_instance

        self.device_label_id = ctk.CTkLabel(self, text="Device ID :", font=("Arial Bold", 12),text_color=("#696969", "#DCE4EE"))
        self.device_label_id.grid(row=0, column=0, padx=(20, 0), pady=20)
        self.device_label_serial = ctk.CTkLabel(self, text=serial, font=("Arial Bold", 12),text_color=("#696969", "#DCE4EE"))  # Display serial here
        self.device_label_serial.grid(row=0, column=1, padx=(5, 20), pady=20)

        self.device_label_name = ctk.CTkLabel(self, text=self.app_instance.get_device_name(serial), font=("Arial Bold", 12),text_color=("#696969", "#DCE4EE")) # Display device name here
        #self.device_label_name.grid(row=0, column=2, padx=20, pady=20)
        self.device_label_name.place(x=220,y=20)

        self.device_button_pair = ctk.CTkButton(self,state="disabled",text="Checking...", font=("Arial Bold", 12),width=100,command=lambda: self.device_button_callback("pair",serial))
        self.device_button_pair.grid(row=0, column=4, padx=(70, 10), pady=20)
        self.device_button_unpair = ctk.CTkButton(self,text="Unpair", font=("Arial Bold", 12),width=100,command=lambda: self.device_button_callback("unpair",serial))
        self.device_button_unpair.grid(row=0, column=5, padx=(10, 10), pady=20)
        self.device_button_reset = ctk.CTkButton(self,text="DongleReset", font=("Arial Bold", 12),width=100, text_color=("#696969", "#DCE4EE"), fg_color="transparent",hover_color=("#696969","#808080"), 
                                                 border_width=2, border_color=("#a9a9a9","#c0c0c0"),
                                                 command=lambda: self.device_button_callback("donglereset",serial))
        self.device_button_reset.grid(row=0, column=6, padx=(10, 20), pady=20)

    def device_button_callback(self,command,serial):#Processing when a button on the device frame is pressed
        exe_path = self.app_instance.get_exe_path()
        
        def check_exists(texts,states):
            if self.device_button_pair.winfo_exists():
                self.device_button_pair.configure(text=texts,state=states)
            
        if command == "pair":
            check_exists("Pairing...","disabled")

        threading.Thread(target=lambda: self.app_instance.execute_subprocess_serial(serial, command, exe_path)).start()
        threading.Timer(5, self.app_instance.check_status).start()

        self.app_instance.insert_log("Executed command : " + serial +" "+ command)

    def change_button_status(self, status):#Change the status of a button on the device frame
        if self.winfo_exists():
            if status == "normal":
                self.device_button_pair.configure(state=status, text="Pair")
                self.configure(fg_color=("#cecece","#323332"))
            elif status == "disabled":
                self.device_button_pair.configure(state=status, text="Paired")
                self.configure(fg_color=("#b0b0b0","#696969"))
                
class App(ctk.CTk):
    def __init__(self):#Frame and widget placement
        super().__init__()

        #Window settings
        ctk.set_default_color_theme("blue")
        self.title("watchman_pairing_assistant")
        self.after(201, lambda :self.iconbitmap(r'resources\icon.ico')) #set icon dir
        self.geometry(f"{940}x{580}")
        config = self.load_config()
        ctk.set_appearance_mode(config.get("theme"))
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = SidebarFrame(self, app_instance=self)
        self.sidebar_frame.grid(row=0, column=0, rowspan=5, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.scrollable_frame = ScrollableFrame(self)
        self.scrollable_frame.grid(row=1, column=1, padx=(20, 20), pady=(10, 0), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        self.textbox_log = ctk.CTkTextbox(self,height= 100)
        self.textbox_log.grid(row=2, column=1, padx=(20, 20), pady=(10, 20), sticky="nsew")

        #reset
        self.insert_log("Welcome to watchman_pairing_assistant ! (v2.0)")
        self.sidebar_frame.sidebar_button_reload_callback()
        
    def insert_log(self,log):#Functio to display logs in console and text box
        current_time = time.strftime("[%Y-%m-%d %H:%M:%S] ")
        self.textbox_log.insert(ctk.END, current_time + log + "\n")
        self.textbox_log.see(ctk.END)
        print(current_time + log)

    def execute_subprocess(self, command, exe_path):#Function to execute an external exe file and get output
        completed_process = subprocess.run([exe_path, command], capture_output=True, text=True)
        return completed_process.stdout
        ##print("Completed Process:", completed_process)

    def execute_subprocess_serial(self, serial, command, exe_path, timeout=5):#Function to execute multiple commands in an external exe file
        process = subprocess.Popen([exe_path], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        try:
            process.stdin.write(f"serial {serial}\n")
            process.stdin.flush()
            process.stdin.write(f"{command}\n")
            process.stdin.flush()
            process.communicate(timeout=timeout)

        except subprocess.TimeoutExpired:
            process.kill()
        finally:
            if process.poll() is None:
                process.wait()

    def check_status(self):#Function to determine dongle connection status
        exe_path = self.get_exe_path()
        output = self.execute_subprocess("dongleinfo", exe_path)
        #print(output)

        for device_frame in self.scrollable_frame.device_frames:
            serial = device_frame.device_label_serial.cget("text")
            serial_appears_disabled = f"VRC-{serial}" in output #Determine if there is a string "VRC-<serial>" in the output result
            
            if serial_appears_disabled:
                self.change_device_status(serial,"disabled")
                self.insert_log("Device connected with "+serial)
            else:
                self.change_device_status(serial,"normal")

    def change_device_status(self, serial, status):#Function to call button status update for device frame
        for device_frame in self.scrollable_frame.device_frames:
            check_serial = device_frame.device_label_serial.cget("text")
            if check_serial == serial:
                if device_frame.winfo_exists():
                    device_frame.change_button_status(status)
                break

    def extract_device_serials(self, output):#Function to extract serial from exe output
        lines = [line.strip() for line in output.split('\n') if line.startswith('\t') and not line.lstrip().startswith('LHR-')] 
        #Extract columns prefixed with a tab, excluding rows prefixed with "LHR-"
        return lines
    
    def get_device_name(self, serial_number):#Function to determine device name from serial
        if serial_number.endswith(("LYM", "RYB")):  #Dongle with built-in IndexHMD, which may have "LYM" or "RYB" at the end of the serial number
            return "IndexHMD"
        elif serial_number.endswith(("LYX")):   #Dongles made with Index firmware when the serial number ends with "LYX"
            return "IndexFW"
        elif serial_number.endswith(("DYX")):   #If the serial ends with DYX, it is dongles made with nrf52840 (etee, Shiftall, etc.)
            return "IndexFW"
        elif re.match(r".*(-[0-9]YX)$", serial_number): 
            #If the last part of the serial number begins with a "-" followed by a single digit and ends with "YX", it is a Tundra labs Super Wireless Dongle
            return "Tundra"
        else:   #Other dongles that are not identifiable (vive HMD or general nrf24 dongles)
            try:
                hmds = list(usb_util_windows.find_hmd())
                for hmd in hmds:
                    dongle_serials = hmd.get_dongle_serials()
                    if serial_number in dongle_serials:
                        return hmd.__class__.__name__
            except Exception as e:
                print(e, file=sys.stderr)
            return "Dongle" 

    def get_exe_path(self):#Get exe path
        config = self.load_config()
        exe_path = config.get("lighthouse_console_path")
        return exe_path

    def load_config(self):  # Generating and getting json
        config_path = os.path.join(os.path.dirname(sys.argv[0]), "resources", "config.json")
        resources_dir = os.path.join(os.path.dirname(sys.argv[0]), "resources")

        default_config = {
            "theme": "Dark",
            "lighthouse_console_path": r"C:\Program Files (x86)\Steam\steamapps\common\SteamVR\tools\lighthouse\bin\win64\lighthouse_console.exe"
        }

        if not os.path.exists(resources_dir):
            os.makedirs(resources_dir, exist_ok=True)

        if not os.path.exists(config_path):
            with open(config_path, "w") as config_file:
                json.dump(default_config, config_file)

        if os.path.exists(config_path):
            with open(config_path, "r") as config_file:
                config = json.load(config_file)

        return config

if __name__ == "__main__":
    app = App() 
    app.mainloop()

import base64
import json
import os
import shutil
import sys
from tkinter import *
from tkinter import messagebox
from tkinter.filedialog import asksaveasfile
import serial.tools.list_ports
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import configparser
import webbrowser

# windowed
import io
stream = io.StringIO()
sys.stdout = stream
sys.stderr = stream


# DEFAULT PATHS
default_arduino_builder_path = "C:/Program Files (x86)/Arduino"
default_arduino_lib_path = os.environ['USERPROFILE'].replace("\\", "/") + "/Documents/Arduino/libraries"
default_avrdude_path = "C:/Program Files (x86)/Arduino/hardware/tools/avr/bin"
default_avrdude_conf_path = "C:/Program Files (x86)/Arduino/hardware/tools/avr/etc/avrdude.conf"

# paths
_arduino_builder_path = ""
_arduino_lib_path = ""
_avrdude_path = ""
_avrdude_conf_path = ""

if os.path.isfile("config.ini"):
    config = configparser.ConfigParser()
    try:
        config.read('config.ini')
    except:
        pass
        messagebox.showerror("", "Uszkodzony plik konfiguracyjny!\nNapraw go lub usuń.")
        sys.exit()

    _flag_all_path_ok = True
    if 'arduino' in config:
        if 'arduino_builder_path' in config['arduino']:
            _arduino_builder_path = config['arduino']['arduino_builder_path']
        else:
            _flag_all_path_ok = False
            _arduino_builder_path = default_arduino_builder_path
            config['arduino']['arduino_builder_path'] = default_arduino_builder_path

        if 'arduino_lib_path' in config['arduino']:
            _arduino_lib_path = config['arduino']['arduino_lib_path']
        else:
            _flag_all_path_ok = False
            _arduino_lib_path = default_arduino_lib_path
            config['arduino']['arduino_lib_path'] = default_arduino_lib_path
    else:
        _flag_all_path_ok = False
        _arduino_builder_path = default_arduino_builder_path
        _arduino_lib_path = default_arduino_lib_path
        config['arduino'] = {}
        config['arduino']['arduino_builder_path'] = default_arduino_builder_path
        config['arduino']['arduino_lib_path'] = default_arduino_lib_path

    if 'avrdude' in config:
        if 'avrdude_path' in config['avrdude']:
            _avrdude_path = config['avrdude']['avrdude_path']
        else:
            _flag_all_path_ok = False
            _avrdude_path = default_avrdude_path
            config['avrdude']['avrdude_path'] = default_avrdude_path

        if 'avrdude_configfile_path' in config['avrdude']:
            _avrdude_conf_path = config['avrdude']['avrdude_configfile_path']
        else:
            flag_all_path_ok = False
            _avrdude_conf_path = default_avrdude_conf_path
            config['avrdude']['avrdude_configfile_path'] = default_avrdude_conf_path
    else:
        _flag_all_path_ok = False
        _avrdude_path = default_avrdude_path
        _avrdude_conf_path = default_avrdude_conf_path
        config['avrdude'] = {}
        config['avrdude']['avrdude_path'] = default_avrdude_path
        config['avrdude']['avrdude_configfile_path'] = default_avrdude_conf_path

    if not _flag_all_path_ok:
        with open('config.ini', mode='w') as configfile:
            config.write(configfile)
            configfile.close()
        messagebox.showinfo("", "Niekompletny plik konfiguracyjny.\nDodano domyślne ścieżki do pliku konfiguracyjnego")
else:
    config = configparser.ConfigParser()
    config['arduino'] = {}
    config['arduino']['arduino_builder_path'] = default_arduino_builder_path
    config['arduino']['arduino_lib_path'] = default_arduino_lib_path
    config['avrdude'] = {}
    config['avrdude']['avrdude_path'] = default_avrdude_path
    config['avrdude']['avrdude_configfile_path'] = default_avrdude_conf_path
    _arduino_builder_path = default_arduino_builder_path
    _arduino_lib_path = default_arduino_lib_path
    _avrdude_path = default_avrdude_path
    _avrdude_conf_path = default_avrdude_conf_path
    with open('config.ini', mode='w') as configfile:
        config.write(configfile)
        configfile.close()
    if messagebox.askyesno("", "Brak pliku konfiguracyjnego.\nUżyć domyślnych ścieżek i kontynuować?", icon='warning'):
        _config_path = os.path.abspath('config.ini')
        messagebox.showinfo("", f"Utworzono plik konfiguracyjny z domyślnymi ścieżkami.\n"
                                f" Znajduje się on w: {_config_path}")
    else:
        _config_path = os.path.abspath('config.ini')
        messagebox.showinfo("", f"Utworzono plik konfiguracyjny z domyślnymi ścieżkami.\n"
                                f" Znajduje się on w: {_config_path}")
        sys.exit()

_flag_all_paths_valid = True

if not os.path.exists(_arduino_builder_path):
    _flag_all_paths_valid = False
    messagebox.showerror("", "Niepoprawna ścieżka w configu:\narduino_builder_path")
if not os.path.exists(_arduino_lib_path):
    _flag_all_paths_valid = False
    messagebox.showerror("", "Niepoprawna ścieżka w configu:\narduino_lib_path")
if not os.path.exists(_avrdude_path):
    _flag_all_paths_valid = False
    messagebox.showerror("", "Niepoprawna ścieżka w configu:\navrdude_path")
if not os.path.isfile(_avrdude_conf_path):
    _flag_all_paths_valid = False
    messagebox.showerror("", "Niepoprawna ścieżka w configu:\navrdude_configfile_path")
if not _flag_all_paths_valid:
    messagebox.showerror("", "Ustaw poprawne ścieżki do folderów i pliku")
    sys.exit()


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def get_serial_ports_list():
    ports = serial.tools.list_ports.comports()
    com_names = []
    for port, desc, hwid in sorted(ports):
        com_names.append(port)
    if len(com_names) == 0:
        com_names.append("None")
    return com_names


def refresh_serials_port():
    _com_ports = get_serial_ports_list()
    selected_port.set(_com_ports[0])
    _menu = com_port_selector['menu']
    _menu.delete(0, "end")
    for string in _com_ports:
        _menu.add_command(label=string, command=lambda value=string: selected_port.set(value))


# zmienne sterujące
window_exited = False  # zmienna używana do zamnięcia wątku kompilatora
run_compiler = False  # zmienna używana do uruchomienia kompilatora
server_status_table = []  # tablica do zgłaszania statusu dla skryptu js
serial_port_locked = False


def compiler_loop():
    global run_compiler, window_exited, server_status_table
    global _arduino_builder_path, _arduino_lib_path, _avrdude_path, _avrdude_conf_path

    while not window_exited:
        if run_compiler:
            server_status_table.append("compilation:started")
            if not os.path.exists("ardueasyblocks_temp"):
                os.mkdir("ardueasyblocks_temp")
            _temp_folder_path = os.path.abspath("ardueasyblocks_temp")
            if not os.path.exists(_temp_folder_path + "/cache"):
                os.mkdir(_temp_folder_path + "/cache")
            if not os.path.exists(_temp_folder_path + "/build"):
                os.mkdir(_temp_folder_path + "/build")

            _run_cmd_comp = f"\"{_arduino_builder_path}/arduino-builder\" -compile -logger=machine" \
                            f" -hardware \"{_arduino_builder_path}/hardware\" " \
                            f"-tools \"{_arduino_builder_path}/tools-builder\" " \
                            f"-tools \"{_arduino_builder_path}/hardware/tools/avr\" " \
                            f"-built-in-libraries \"{_arduino_builder_path}/libraries\" " \
                            f"-libraries \"{_arduino_lib_path}\" " \
                            f"-fqbn=arduino:avr:nano:cpu=atmega328 -vid-pid=0000_0000 -ide-version=10815 " \
                            f"-build-path \"{_temp_folder_path}/build\" " \
                            f"-warnings=none -build-cache \"{_temp_folder_path}/cache\" " \
                            f"-verbose \"{_temp_folder_path}/temp.ino\""

            log_textbox.insert(END, "\n###Compilation started###\n")
            log_textbox.insert(END, _run_cmd_comp + "\n\n")
            log_textbox.see(END)

            # compile
            compile_run = subprocess.Popen(_run_cmd_comp, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           shell=False, creationflags=subprocess.CREATE_NO_WINDOW)

            for line in compile_run.stdout:
                log_textbox.insert(END, line)
                log_textbox.see(END)

            _flag_compilation_error = False

            for line in compile_run.stderr:
                log_textbox.insert(END, line)
                log_textbox.see(END)
                _flag_compilation_error = True

            if _flag_compilation_error:
                log_textbox.insert(END, "\n===================================\n")
                log_textbox.insert(END, "  Compilation failed successfully\n")
                log_textbox.insert(END, "===================================\n")
                log_textbox.see(END)
                server_status_table.append("compilation:failed")
            else:
                log_textbox.insert(END, "\n========================\n")
                log_textbox.insert(END, "  Compilation finished\n")
                log_textbox.insert(END, "========================\n")
                log_textbox.see(END)
                server_status_table.append("compilation:finished,uploading:starts")

            if not _flag_compilation_error:

                log_textbox.insert(END, "\n###Uploading started###\n")
                log_textbox.see(END)

                if not serial_port_locked:
                    server_status_table.append("uploading:fail_port_unlocked")
                    log_textbox.insert(END, "\n===========================================\n")
                    log_textbox.insert(END, "  Uploading fail, serial port is unlocked\n")
                    log_textbox.insert(END, "===========================================\n")
                    log_textbox.see(END)
                else:
                    # flashing
                    _run_upload = f"\"{_avrdude_path}/avrdude\" -C\"{_avrdude_conf_path}\" -v -patmega328p " \
                                  f"-carduino -P\"{selected_port.get()}\" -b115200 -D " \
                                  f"-Uflash:w:\"{_temp_folder_path}/build/temp.ino.with_bootloader.hex\":i"

                    log_textbox.insert(END, _run_upload + "\n")
                    log_textbox.see(END)

                    upload_run = subprocess.Popen(_run_upload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                  shell=False, creationflags=subprocess.CREATE_NO_WINDOW)

                    _flag_upload_error = True
                    for line in upload_run.stderr:
                        log_textbox.insert(END, line)
                        log_textbox.see(END)
                        if "bytes of flash verified" in str(line):
                            _flag_upload_error = False

                    if _flag_upload_error:
                        log_textbox.insert(END, "\n==================================\n")
                        log_textbox.insert(END, "  Uploading failed successfully\n")
                        log_textbox.insert(END, "==================================\n")
                        log_textbox.see(END)
                        server_status_table.append("uploading:failed")
                    else:
                        log_textbox.insert(END, "\n======================\n")
                        log_textbox.insert(END, "  Uploading finished\n")
                        log_textbox.insert(END, "======================\n")
                        log_textbox.see(END)
                        server_status_table.append("uploading:finished")

            if os.path.exists(_temp_folder_path + "/cache"):
                shutil.rmtree(_temp_folder_path + "/cache")
            if os.path.exists(_temp_folder_path + "/build"):
                shutil.rmtree(_temp_folder_path + "/build")
            if os.path.exists(_temp_folder_path+"/temp.ino"):
                os.remove(_temp_folder_path+"/temp.ino")
            run_compiler = False
            compiler_status_indicator_set('idle')

        time.sleep(0.005)


def f_run_compiler():
    global run_compiler
    if not run_compiler:
        run_compiler = True
        compiler_status_indicator_set('busy')
    else:
        log_textbox.insert(END, "\nKompilator jest zajęty!\n")
        print()


def compiler_status_indicator_set(mode):
    if mode == "busy":
        compiler_stats_var.set("Busy")
        compiler_status.config(foreground="#aa0000")
    elif mode == "idle":
        compiler_stats_var.set("Idle")
        compiler_status.config(foreground="#00aa00")


# server http
class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        global run_compiler, server_status_table, serial_port_locked

        self._set_response()
        _get = self.path[2:]

        if _get == "status":
            _status = None
            if len(server_status_table) > 0:
                _status = server_status_table.pop(0)
            else:
                if run_compiler:
                    _status = "busy"
                else:
                    _status = "idle"
            self.wfile.write(json.dumps({"status": _status}).encode('utf-8'))

        elif _get == "ready":
            _status = None
            if run_compiler:
                _status = "busy"
            else:
                if len(server_status_table) > 0:
                    _status = "not_available"
                else:
                    if serial_port_locked:
                        _status = "ready"
                    else:
                        _status = "no_port_selected"
            self.wfile.write(json.dumps({"status": _status}).encode('utf-8'))
        else:
            self.wfile.write(json.dumps({"error": "unknown_command"}).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        _received_data = json.loads(post_data.decode("UTF-8"))
        _status = 'ok'
        if run_compiler:
            _status = "error:compiler_busy"
        else:
            if "code" in _received_data:
                if not os.path.exists("ardueasyblocks_temp"):
                    os.mkdir("ardueasyblocks_temp")
                with open("ardueasyblocks_temp/temp.ino", mode="w") as temp_code_file:
                    temp_code_file.write(base64.b64decode(_received_data['code']).decode("utf-8"))
                    temp_code_file.close()
                f_run_compiler()
            else:
                _status = 'error:code_not_found'
        self._set_response()
        self.wfile.write(json.dumps({"status": _status}).encode('utf-8'))


httpd = None


def http_server_loop(server_class=HTTPServer, handler_class=S, port=8080):
    global window_exited, httpd
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.timeout = 1

    try:
        httpd.serve_forever()
    except:
        pass
    httpd.server_close()


def clear_data_log():
    log_textbox.delete('1.0', END)


def save_to_file():
    datafile = asksaveasfile(initialfile='ardueasyblocks_compiler_log.txt',
                             defaultextension=".csv",
                             filetypes=[("Text Documents", "*.txt")])
    if datafile is not None:
        datafile.write(log_textbox.get('1.0', END))
        datafile.close()


def update_response_buff_indi():
    global server_status_table
    number_of_messages = len(server_status_table)
    if number_of_messages < 100:
        compiler_response_buff_var.set(str(number_of_messages))
    else:
        compiler_response_buff_var.set("99+")
    gui.after(100, lambda: update_response_buff_indi())


def server_status_table_reset():
    global server_status_table, run_compiler
    if run_compiler:
        messagebox.showwarning("", "Nie można zresetować buforu gdy kompilator lub avrdude pracuje")
    else:
        server_status_table = []


def on_closing():
    if run_compiler:
        if messagebox.askyesno("Uwaga", "Kompilator i avrdude jest uruchomiony!\n"
                                        "Zamknięcie avrdude w trakcie flashowania "
                                        "mikrokontrolera może spowodować uszkodzenie bootloadera.\n"
                                        "Czy mimo to chcesz zamknąć program?", icon='warning'):
            gui.destroy()
    else:
        gui.destroy()


def lock_port():
    global serial_port_locked
    connect_btn["state"] = "disable"
    disconnect_btn["state"] = "normal"
    com_port_selector["state"] = "disable"
    refresh_ser_ports_btn["state"] = "disable"
    serial_port_locked = True


def unlock_port():
    global serial_port_locked, run_compiler
    if run_compiler:
        messagebox.showwarning("", "Nie można zmienić portu gdy kompilator lub avrdude pracuje")
    else:
        connect_btn["state"] = "normal"
        disconnect_btn["state"] = "disable"
        com_port_selector["state"] = "normal"
        refresh_ser_ports_btn["state"] = "normal"
        serial_port_locked = False


gui = Tk()
gui.title("ArduEasyBlocks compiler&flash tool v1.0.0")
gui.geometry("520x400")
gui.resizable(False, False)
gui.iconbitmap(resource_path("icon.ico"))

# port select
Label(gui, text="Port:", justify=LEFT).place(x=10, y=5)
com_ports = get_serial_ports_list()
selected_port = StringVar(gui)
selected_port.set(com_ports[0])

com_port_selector = OptionMenu(gui, selected_port, *com_ports)
com_port_selector.place(x=10, y=24, width=150)
refresh_ser_ports_btn = Button(gui, text="Refresh", command=lambda: refresh_serials_port())
refresh_ser_ports_btn.place(x=97, y=5, width=60, height=18)

connect_btn = Button(gui, text="Wybierz port", fg="#00dd00", command=lambda: lock_port())
connect_btn.place(x=170, y=5, width=100, height=20)
disconnect_btn = Button(gui, text="Zmień port", fg="#dd0000", command=lambda: unlock_port())
disconnect_btn.place(x=170, y=30, width=100, height=20)
disconnect_btn["state"] = "disable"

# link to ardueasyblocks
img_open_ardueasyblock = PhotoImage(file=resource_path("open_url.png"))
open_ardueasyblocks_btn = Button(gui, image=img_open_ardueasyblock, fg="#eb346e",
                                 command=lambda: webbrowser.open("https://znow-o-kablach.pl/ardueasyblocks/"))
open_ardueasyblocks_btn.place(x=345, y=5, width=40, height=40)

# compiler status indicator
compiler_stats_var = StringVar()

Label(gui, text="Status kompilatora:", justify=LEFT).place(x=10, y=60)
compiler_status = Label(gui, textvariable=compiler_stats_var, justify=LEFT, width=5, foreground="#00aa00")
compiler_status.place(x=120, y=60)
compiler_status_indicator_set("idle")

# compiler buffer response indicator
compiler_response_buff_var = StringVar()
compiler_response_buff_var.set("0")

Label(gui, text="Bufor odpowiedzi:", justify=LEFT).place(x=10, y=80)
compiler_response_buff = Label(gui, textvariable=compiler_response_buff_var, justify=LEFT,
                               width=5, foreground="#00aaaa")
compiler_response_buff.place(x=120, y=80)

# reset server_status_table button
buff_reset_btn = Button(gui, text="Resetuj bufor", fg="#eb346e", command=lambda: server_status_table_reset())
buff_reset_btn.place(x=170, y=77, width=80, height=20)

frame_log_textbox = Frame()
log_textbox_sb = Scrollbar(frame_log_textbox)
log_textbox_sb.pack(side=RIGHT, fill='y')
log_textbox = Text(frame_log_textbox, height=30, width=45, yscrollcommand=log_textbox_sb.set)
log_textbox_sb.config(command=log_textbox.yview)
log_textbox.place(x=0, y=0, width=385, height=300)
frame_log_textbox.place(x=0, y=100, width=400, height=300)

clear_log_btn = Button(gui, text="Wyczyść log", fg="#777700", command=lambda: clear_data_log())
clear_log_btn.place(x=305, y=52, width=80, height=20)
save_log_btn = Button(gui, text="Zapisz log", fg="#1f75de", command=lambda: save_to_file())
save_log_btn.place(x=305, y=77, width=80, height=20)

img_bg = PhotoImage(file=resource_path("image2.png"))
Label(gui, image=img_bg).place(x=400, y=0)

# compiler thread
compiler_thread = threading.Thread(target=compiler_loop)
compiler_thread.daemon = True
compiler_thread.start()

# http server thread
httpserver_thread = threading.Thread(target=http_server_loop)
httpserver_thread.daemon = True
httpserver_thread.start()
update_response_buff_indi()
gui.protocol("WM_DELETE_WINDOW", on_closing)
gui.mainloop()

window_exited = True

sys.exit()

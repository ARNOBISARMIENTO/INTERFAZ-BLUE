import asyncio
import customtkinter as ctk
from bleak import BleakScanner, BleakClient
from PIL import Image, ImageTk
import threading
import time

# Configurar apariencia
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Ventana principal
root = ctk.CTk()
root.title("Control Bluetooth Arduino")
root.geometry("1200x700")

# Variables globales
connected_client = None
devices_list = []
command_sequence = []

# 📡 Función para buscar dispositivos BLE
async def scan_devices():
    global devices_list
    devices_list = await BleakScanner.discover()
    refresh_device_list()

def start_scan():
    threading.Thread(target=lambda: asyncio.run(scan_devices())).start()

# 🔌 Función para conectar con un dispositivo BLE
async def connect_device(address):
    global connected_client
    try:
        client = BleakClient(address)
        await client.connect()
        if client.is_connected:
            connected_client = client
            status_label.configure(text=f"Conectado a: {address}", text_color="green")
        else:
            status_label.configure(text="No se pudo conectar", text_color="red")
    except Exception as e:
        status_label.configure(text=f"Error: {e}", text_color="red")

def connect_btn(address):
    threading.Thread(target=lambda: asyncio.run(connect_device(address))).start()

# 🧱 Refrescar lista de dispositivos en la GUI
def refresh_device_list():
    for widget in device_frame.winfo_children():
        widget.destroy()

    for d in devices_list:
        frame = ctk.CTkFrame(device_frame)
        frame.pack(fill="x", pady=2)

        label = ctk.CTkLabel(frame, text=f"{d.name or 'Dispositivo BLE'} ({d.address})")
        label.pack(side="left", padx=10)

        btn = ctk.CTkButton(frame, text="Conectar", width=100,
                            command=lambda addr=d.address: connect_btn(addr))
        btn.pack(side="right", padx=10)

# 🕹️ Comandos disponibles
commands = {
    "Adelante": "ADELANTE",
    "Izquierda": "IZQUIERDA",
    "Derecha": "DERECHA",
    "Reversa": "REVERSA",
    "Detener": "STOP",
    "Esperar": "ESPERAR"
}

# 🖼️ Cargar imágenes
def load_image(path, size=(60, 60)):
    try:
        return ctk.CTkImage(Image.open(path), size=size)
    except:
        return None

# 📤 Enviar comando BLE
async def send_command(command):
    if connected_client and connected_client.is_connected:
        try:
            # UUID del servicio BLE donde Arduino espera los datos
            # ⚠️ Cambia este UUID por el de tu Arduino
            CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
            await connected_client.write_gatt_char(CHARACTERISTIC_UUID, command.encode('utf-8'))
        except Exception as e:
            status_label.configure(text=f"Error enviando: {e}", text_color="red")
    else:
        status_label.configure(text="No hay dispositivo conectado", text_color="red")

def send_command_thread(command):
    threading.Thread(target=lambda: asyncio.run(send_command(command))).start()

# ➕ Agregar a secuencia
def add_to_sequence(cmd_name):
    frame = ctk.CTkFrame(sequence_frame)
    frame.pack(side="left", padx=5)
    label = ctk.CTkLabel(frame, text=cmd_name, image=load_image(f"imagenes/{cmd_name.lower()}.png"), compound="top")
    label.pack()
    command_sequence.append(cmd_name)

# ▶️ Ejecutar secuencia
def run_sequence():
    def run():
        for cmd in command_sequence:
            send_command_thread(commands[cmd])
            time.sleep(1)
    threading.Thread(target=run).start()

# 🧹 Limpiar secuencia
def clear_sequence():
    global command_sequence
    for widget in sequence_frame.winfo_children():
        widget.destroy()
    command_sequence = []

# --- GUI Layout ---

# Frame izquierdo: comandos
commands_frame = ctk.CTkFrame(root)
commands_frame.pack(side="left", fill="y", padx=10, pady=10)

ctk.CTkLabel(commands_frame, text="Comandos").pack(pady=5)
for cmd in commands.keys():
    btn = ctk.CTkButton(commands_frame, text=cmd, width=150,
                        command=lambda c=cmd: add_to_sequence(c))
    btn.pack(pady=3)

ctk.CTkButton(commands_frame, text="Ejecutar Secuencia ▶️", fg_color="green",
              command=run_sequence).pack(pady=10)

ctk.CTkButton(commands_frame, text="Limpiar Secuencia 🧹", fg_color="gray",
              command=clear_sequence).pack(pady=5)

# Frame central: secuencia
sequence_frame = ctk.CTkFrame(root, height=200)
sequence_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

# Frame derecho: dispositivos BLE
ble_frame = ctk.CTkFrame(root, width=350)
ble_frame.pack(side="right", fill="y", padx=10, pady=10)

ctk.CTkLabel(ble_frame, text="Conexión Bluetooth").pack(pady=5)
device_frame = ctk.CTkScrollableFrame(ble_frame, height=400)
device_frame.pack(fill="both", expand=True, padx=5, pady=5)

scan_btn = ctk.CTkButton(ble_frame, text="Buscar Dispositivos", command=start_scan)
scan_btn.pack(pady=10)

status_label = ctk.CTkLabel(ble_frame, text="Desconectado", text_color="red")
status_label.pack(pady=5)

# --- Ejecutar app ---
root.mainloop()

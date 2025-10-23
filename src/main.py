import customtkinter as ctk
from PIL import Image
from bleak import BleakScanner
import asyncio
import threading

# ================= CONFIGURACIÓN BASE =================
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Control Bluetooth Arduino")
root.geometry("1100x600")

# ================= FUNCIONES =================
def cargar_img(nombre, size=(80, 80)):
    try:
        return ctk.CTkImage(Image.open(f"imagenes/{nombre}"), size=size)
    except Exception as e:
        print(f"Error al cargar {nombre}: {e}")
        return None

def agregar_accion(nombre):
    acciones_listbox.insert("end", f"{len(secuencia_visual)+1}. {nombre}\n")
    if nombre in imagenes:
        cont = ctk.CTkFrame(frame_centro, corner_radius=10)
        cont.pack(pady=5, fill="x", padx=15)

        lbl_img = ctk.CTkLabel(cont, image=imagenes[nombre], text="")
        lbl_img.pack(side="left", padx=10, pady=5)

        lbl_text = ctk.CTkLabel(cont, text=nombre, font=("Arial", 15, "bold"))
        lbl_text.pack(side="left", padx=10)
        secuencia_visual.append(cont)

def limpiar_secuencia():
    for lbl in secuencia_visual:
        lbl.destroy()
    secuencia_visual.clear()
    acciones_listbox.delete("1.0", "end")

def seleccionar_dispositivo(nombre):
    global dispositivo_seleccionado
    dispositivo_seleccionado = nombre
    lbl_estado.configure(text=f"Seleccionado: {nombre}", text_color="blue")

async def buscar_dispositivos_ble():
    dispositivos = await BleakScanner.discover()
    for d in dispositivos:
        nombre = d.name or "Desconocido"
        btn = ctk.CTkButton(frame_lista_bt, text=f"{nombre} ({d.address})",
                            command=lambda n=nombre: seleccionar_dispositivo(n))
        btn.pack(pady=3, fill="x", padx=5)

def escanear_ble():
    for widget in frame_lista_bt.winfo_children():
        widget.destroy()
    threading.Thread(target=lambda: asyncio.run(buscar_dispositivos_ble())).start()

def toggle_bluetooth_panel():
    global panel_bt_visible
    if panel_bt_visible:
        frame_der.pack_forget()
        panel_bt_visible = False
    else:
        frame_der.pack(side="right", fill="y", padx=5, pady=10)
        panel_bt_visible = True

def conectar_bluetooth():
    if dispositivo_seleccionado:
        lbl_estado.configure(text=f"Conectado a {dispositivo_seleccionado}", text_color="green")

def desconectar_bluetooth():
    lbl_estado.configure(text="No hay dispositivo conectado", text_color="red")

# ================= IMÁGENES =================
imagenes = {
    "Adelante": cargar_img("adelante.jpg"),
    "Izquierda": cargar_img("izquierda.png"),
    "Derecha": cargar_img("derecha.png"),
    "Reversa": cargar_img("reversa.jpg"),
    "Detener": cargar_img("detener.jpg"),
    "Esperar": cargar_img("esperar.jpg"),
    "Encender": cargar_img("encender.jpg"),
}

icono_bt = cargar_img("bluetooth.png", size=(35, 35))

# ================= INTERFAZ =================
frame_izq = ctk.CTkFrame(root, width=250)
frame_izq.pack(side="left", fill="y", padx=10, pady=10)

frame_centro = ctk.CTkScrollableFrame(root, width=500)
frame_centro.pack(side="left", fill="both", expand=True, pady=10)

frame_der = ctk.CTkFrame(root, width=250)  # más estrecho

# --- PANEL IZQUIERDO ---
lbl_acciones = ctk.CTkLabel(frame_izq, text="Comandos", font=("Arial", 17, "bold"))
lbl_acciones.pack(pady=10)

for acc in imagenes.keys():
    ctk.CTkButton(frame_izq, text=acc, command=lambda a=acc: agregar_accion(a)).pack(pady=5, padx=10, fill="x")

ctk.CTkLabel(frame_izq, text="Secuencia actual:", font=("Arial", 14)).pack(pady=(15, 5))
acciones_listbox = ctk.CTkTextbox(frame_izq, height=120)
acciones_listbox.pack(padx=10, pady=5, fill="x")

# --- BOTONES UNO DEBAJO DEL OTRO ---
btn_ejecutar = ctk.CTkButton(frame_izq, text="Ejecutar Secuencia", fg_color="green")
btn_ejecutar.pack(pady=(10, 5), padx=10, fill="x")

btn_parar = ctk.CTkButton(frame_izq, text="Parar Secuencia", fg_color="orange")
btn_parar.pack(pady=5, padx=10, fill="x")

btn_limpiar = ctk.CTkButton(frame_izq, text="Limpiar Secuencia", command=limpiar_secuencia, fg_color="gray")
btn_limpiar.pack(pady=5, padx=10, fill="x")

# --- PANEL CENTRAL ---
ctk.CTkLabel(frame_centro, text="Vista de Secuencia", font=("Arial", 17, "bold")).pack(pady=10)
secuencia_visual = []

# --- BOTÓN BLUETOOTH (esquina superior derecha) ---
btn_bt_icon = ctk.CTkButton(root, image=icono_bt, text="", width=45, height=40, command=toggle_bluetooth_panel)
btn_bt_icon.place(relx=0.975, rely=0.02, anchor="ne")

# --- PANEL DERECHO (Bluetooth) ---
lbl_bt = ctk.CTkLabel(frame_der, text="Conexión Bluetooth", font=("Arial", 17, "bold"))
lbl_bt.pack(pady=10)

frame_lista_bt = ctk.CTkScrollableFrame(frame_der, height=250)
frame_lista_bt.pack(padx=10, pady=5, fill="both")

btn_buscar = ctk.CTkButton(frame_der, text="Buscar Dispositivos", command=escanear_ble)
btn_buscar.pack(pady=5, padx=10, fill="x")

lbl_estado = ctk.CTkLabel(frame_der, text="No hay dispositivo conectado", text_color="red")
lbl_estado.pack(pady=10)

frame_conexion = ctk.CTkFrame(frame_der)
frame_conexion.pack(pady=5)

btn_conectar = ctk.CTkButton(frame_conexion, text="Conectar", fg_color="green", command=conectar_bluetooth)
btn_conectar.grid(row=0, column=0, padx=5)

btn_desconectar = ctk.CTkButton(frame_conexion, text="Desconectar", fg_color="red", command=desconectar_bluetooth)
btn_desconectar.grid(row=0, column=1, padx=5)

# ================= RUN =================
panel_bt_visible = False
dispositivo_seleccionado = None

root.mainloop()

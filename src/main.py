import customtkinter as ctk
from PIL import Image, ImageTk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Interfaz BLE - Arduino HM-10")
app.geometry("1000x650")

# --- FRAME CONEXIÓN ---
frame_conexion = ctk.CTkFrame(app, corner_radius=15)
frame_conexion.pack(fill="x", padx=20, pady=10)

label_titulo = ctk.CTkLabel(frame_conexion, text="INTERFAZ DE CONEXIÓN BLUETOOTH BLE", font=("Arial", 20, "bold"))
label_titulo.pack(pady=10)

boton_buscar = ctk.CTkButton(frame_conexion, text="🔍 Buscar Dispositivos", width=200)
boton_buscar.pack(side="left", padx=20, pady=10)

boton_conectar = ctk.CTkButton(frame_conexion, text="🔗 Conectar", width=200)
boton_conectar.pack(side="left", padx=20, pady=10)

label_estado = ctk.CTkLabel(frame_conexion, text="Estado: Desconectado", font=("Arial", 14))
label_estado.pack(side="right", padx=20)

# --- FRAME MOVIMIENTOS ---
frame_mov = ctk.CTkFrame(app, corner_radius=15)
frame_mov.pack(padx=20, pady=10, fill="both", expand=True)

label_mov = ctk.CTkLabel(frame_mov, text="CONTROLES DE MOVIMIENTO", font=("Arial", 18, "bold"))
label_mov.pack(pady=10)

# --- Cargar imágenes ---
def cargar_img(nombre, size=(80, 80)):
    return ctk.CTkImage(light_image=Image.open(f"imagenes/{nombre}"), size=size)

imagenes = {
    "adelante": cargar_img("adelante.jpg"),
    "izquierda": cargar_img("izquierda.png"),
    "derecha": cargar_img("derecha.png"),
    "detener": cargar_img("detener.jpg"),
    "reversa": cargar_img("reversa.jpg"),
    "esperar": cargar_img("esperar.jpg"),
    "encender": cargar_img("encender.jpg"),
}


# --- FRAME BOTONES DE CONTROL ---
frame_botones = ctk.CTkFrame(frame_mov, fg_color="transparent")
frame_botones.pack(pady=10)

acciones = []

# Función para agregar acción con imagen
def agregar_accion(nombre):
    acciones.append(nombre)
    actualizar_lista()

def actualizar_lista():
    for widget in frame_lista_acciones.winfo_children():
        widget.destroy()

    for i, accion in enumerate(acciones):
        ctk.CTkLabel(frame_lista_acciones, image=imagenes[accion], text=accion.capitalize(), compound="top").grid(row=0, column=i, padx=5)

# Fila superior
ctk.CTkButton(frame_botones, image=imagenes["adelante"], text="Adelante", compound="top", width=120, height=120,
              command=lambda: agregar_accion("adelante")).grid(row=0, column=1, padx=10, pady=10)

# Fila central
ctk.CTkButton(frame_botones, image=imagenes["izquierda"], text="Izquierda", compound="top", width=120, height=120,
              command=lambda: agregar_accion("izquierda")).grid(row=1, column=0, padx=10, pady=10)

ctk.CTkButton(frame_botones, image=imagenes["detener"], text="Detener", compound="top", width=120, height=120,
              command=lambda: agregar_accion("detener")).grid(row=1, column=1, padx=10, pady=10)

ctk.CTkButton(frame_botones, image=imagenes["derecha"], text="Derecha", compound="top", width=120, height=120,
              command=lambda: agregar_accion("derecha")).grid(row=1, column=2, padx=10, pady=10)

# Fila inferior
ctk.CTkButton(frame_botones, image=imagenes["reversa"], text="Reversa", compound="top", width=120, height=120,
              command=lambda: agregar_accion("reversa")).grid(row=2, column=0, padx=10, pady=10)

ctk.CTkButton(frame_botones, image=imagenes["esperar"], text="Esperar", compound="top", width=120, height=120,
              command=lambda: agregar_accion("esperar")).grid(row=2, column=1, padx=10, pady=10)

ctk.CTkButton(frame_botones, image=imagenes["encender"], text="Encender Motor", compound="top", width=120, height=120,
              command=lambda: agregar_accion("encender")).grid(row=2, column=2, padx=10, pady=10)

# --- FRAME LISTA DE ACCIONES ---
frame_lista = ctk.CTkFrame(app, corner_radius=15)
frame_lista.pack(fill="x", padx=20, pady=10)

label_lista = ctk.CTkLabel(frame_lista, text="SECUENCIA A EJECUTAR", font=("Arial", 16, "bold"))
label_lista.pack(anchor="w", padx=10, pady=5)

frame_lista_acciones = ctk.CTkFrame(frame_lista, fg_color="transparent")
frame_lista_acciones.pack(fill="x", padx=10, pady=5)

# --- FRAME INFERIOR ---
frame_acciones = ctk.CTkFrame(app, corner_radius=15)
frame_acciones.pack(fill="x", padx=20, pady=10)

def limpiar_acciones():
    acciones.clear()
    actualizar_lista()

ctk.CTkButton(frame_acciones, text="▶ Ejecutar Secuencia", width=180).pack(side="left", padx=20, pady=10)
ctk.CTkButton(frame_acciones, text="🗑 Limpiar", width=180, command=limpiar_acciones).pack(side="left", padx=20, pady=10)

app.mainloop()

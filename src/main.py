import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import os, threading, time, asyncio, tkinter as tk

# Intentar importar pyserial (para HC-05/HC-06)
try:
    import serial
    import serial.tools.list_ports
    HAS_PYSERIAL = True
except Exception:
    HAS_PYSERIAL = False
    print("⚠️ pyserial no disponible. Solo funcionará BLE.")

# Intentar importar bleak (para BLE)
try:
    from bleak import BleakScanner, BleakClient
    HAS_BLEAK = True
except Exception:
    HAS_BLEAK = False
    print("⚠️ bleak no disponible. Solo funcionará Serial.")

# ---------------- CONFIG ----------------
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ROOT_DIR = os.path.dirname(__file__)
IMAGES_DIR = os.path.join(ROOT_DIR, "imagenes")

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"


# ---------------- APP ----------------
class DragDropApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Control Bluetooth Arduino - Secuencia")
        self.geometry("1200x700")

        self.sequence = []
        self.ble_client = None
        self.serial_port = None
        self.connected_mode = None
        self.scan_results = []
        self.selected_scan_entry = None
        self._stop_execution = threading.Event()

        # iconos (CTkImage para widgets, PIL para preview)
        self.icons = {}
        self.icons_pil = {}
        self._load_icons()
        self._build_ui()

        # drag & drop vars
        self._preview_win = None
        self._preview_imgtk = None
        self._drag_action = None
        self._inside_drop = False

    # ---------- load icons ----------
    def _load_icon_safe(self, fname, size=(64, 64)):
        """Carga imagen PIL, la redimensiona y devuelve (CTkImage, PIL Image)."""
        p = os.path.join(IMAGES_DIR, fname)
        try:
            pil = Image.open(p).convert("RGBA")
            pil_resized = pil.copy()
            pil_resized.thumbnail(size, Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_resized, dark_image=pil_resized, size=size)
            return ctk_img, pil_resized
        except Exception:
            # placeholder
            ph = Image.new("RGBA", size, (230, 230, 230, 255))
            draw = ImageDraw.Draw(ph)
            draw.rectangle((4, 4, size[0]-4, size[1]-4), outline=(180, 180, 180))
            return ctk.CTkImage(light_image=ph, dark_image=ph, size=size), ph

    def _load_icons(self):
        """
        Carga solo las acciones que quieres mantener.
        Quité "Encender" y dejé "Bluetooth" solo como icono de UI.
        """
        mapping = {
             "Adelante": "adelante.png",
    "Izquierda": "izquierda.png",
    "Derecha": "derecha.png",
    "Reversa": "reversa.png",
    "Detener": "detener.png",
    "Esperar": "esperar.png",
    "Bluetooth": "bluetooth.png", # icono de la interfaz, NO acción
        }
        for action_name, fname in mapping.items():
            ctk_img, pil_img = self._load_icon_safe(fname)
            self.icons[action_name] = ctk_img
            self.icons_pil[action_name] = pil_img

    # ---------- build UI ----------
    def _build_ui(self):
        # panel izquierdo (acciones) — ahora sin "Encender"
        self.left = ctk.CTkFrame(self, width=260)
        self.left.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(self.left, text="Acciones", font=("Arial", 16, "bold")).pack(pady=(6, 8))
        # acciones disponibles (sin "Encender")
        for action in ["Adelante", "Izquierda", "Derecha", "Reversa", "Detener", "Esperar"]:
            btn = ctk.CTkButton(self.left, image=self.icons[action], text="", width=90, height=70)
            btn.pack(pady=6, padx=8)
            # bind para iniciar arrastre (el movimiento y release se manejan globalmente)
            btn.bind("<ButtonPress-1>", lambda e, a=action: self._start_drag(e, a))

        ctk.CTkLabel(self.left, text="Secuencia actual:", font=("Arial", 13, "bold")).pack(pady=(12, 4))
        self.seq_box = ctk.CTkTextbox(self.left, height=160)
        self.seq_box.pack(padx=6, pady=4, fill="x")

        # centro (zona de secuencia)
        self.center = ctk.CTkFrame(self)
        self.center.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.center, text="Vista de Secuencia", font=("Arial", 16, "bold")).pack(pady=6)
        self.seq_frame = ctk.CTkScrollableFrame(self.center, border_width=2, border_color="#ccc")
        self.seq_frame.pack(fill="both", expand=True, padx=10, pady=6)

        self.block_container = self.seq_frame

        self.status_label = ctk.CTkLabel(self.center, text="Arrastra una acción para comenzar...", text_color="gray")
        self.status_label.pack(pady=(4, 8))

        # botones ejecutar / parar / limpiar
        buttons_frame = ctk.CTkFrame(self.center, fg_color="transparent")
        buttons_frame.pack(pady=6)

        self.btn_run = ctk.CTkButton(buttons_frame, text="▶ Ejecutar", fg_color="#2e7d32", command=self.start_execution)
        self.btn_run.grid(row=0, column=0, padx=6, pady=4)
        self.btn_stop = ctk.CTkButton(buttons_frame, text="⏹ Parar", fg_color="#ef6c00", command=self.stop_execution)
        self.btn_stop.grid(row=1, column=0, padx=6, pady=4)
        self.btn_clear = ctk.CTkButton(buttons_frame, text="🧹 Limpiar", fg_color="#455a64", command=self.clear_sequence)
        self.btn_clear.grid(row=2, column=0, padx=6, pady=4)

        # panel Bluetooth lateral
        self.bt_panel = ctk.CTkFrame(self, width=320)
        ctk.CTkLabel(self.bt_panel, text="Conexión Bluetooth", font=("Arial", 16, "bold")).pack(pady=10)
        self.frame_devices = ctk.CTkScrollableFrame(self.bt_panel, height=300)
        self.frame_devices.pack(fill="both", padx=10, pady=6)
        ctk.CTkButton(self.bt_panel, text="🔍 Buscar dispositivos", command=self.scan_all).pack(fill="x", padx=10, pady=(4, 8))
        self.lbl_bt_state = ctk.CTkLabel(self.bt_panel, text="No conectado", text_color="red")
        self.lbl_bt_state.pack(pady=6)
        fr_conn = ctk.CTkFrame(self.bt_panel)
        fr_conn.pack(pady=6)
        ctk.CTkButton(fr_conn, text="Conectar", fg_color="#2e7d32", command=self.connect_selected).grid(row=0, column=0, padx=6)
        ctk.CTkButton(fr_conn, text="Desconectar", fg_color="#c62828", command=self.disconnect_current).grid(row=0, column=1, padx=6)

        # icono bluetooth fijo (solo UI)
        icon_bt = self.icons.get("Bluetooth")
        self.bt_button = ctk.CTkButton(self, image=icon_bt, text="", width=44, height=38, command=self._toggle_bt_panel)
        self.bt_button.place(relx=0.99, rely=0.02, anchor="ne")

    # ---------- DRAG & DROP ----------
    def _start_drag(self, event, action):
        self._end_preview_if_any()
        self._drag_action = action

        # Crear ventana flotante con icono (preview)
        self._preview_win = tk.Toplevel(self)
        self._preview_win.overrideredirect(True)
        pil_img = self.icons_pil.get(action)
        if pil_img is None:
            pil_img = Image.new("RGBA", (64, 64), (220, 220, 220, 255))
            ImageDraw.Draw(pil_img).rectangle((5, 5, 59, 59), outline=(0, 0, 0))
        self._preview_imgtk = ImageTk.PhotoImage(pil_img)
        lbl = tk.Label(self._preview_win, image=self._preview_imgtk, bg="white", bd=1, relief="solid")
        lbl.pack()
        self._preview_win.geometry(f"+{event.x_root}+{event.y_root}")
        self._preview_win.lift()

        # texto de guía en zona de secuencia
        self._drop_hint = ctk.CTkLabel(self.seq_frame, text="📍 Suelta aquí",
                                       font=("Arial", 22, "bold"), text_color="gray50")
        self._drop_hint.place(relx=0.5, rely=0.5, anchor="center")
        self.seq_frame.configure(border_color="#ccc")

        # binds globales para movimiento/soltar
        self.bind_all("<Motion>", self._global_motion)
        self.bind_all("<ButtonRelease-1>", self._global_release)
        self.status_label.configure(text=f"Arrastrando: {action}", text_color="black")

    def _global_motion(self, event):
        if not self._preview_win:
            return

        # mover preview junto al cursor
        try:
            self._preview_win.geometry(f"+{event.x_root+8}+{event.y_root+8}")
        except Exception:
            pass

        cx, cy = event.x_root, event.y_root
        sx, sy = self.seq_frame.winfo_rootx(), self.seq_frame.winfo_rooty()
        sw, sh = self.seq_frame.winfo_width(), self.seq_frame.winfo_height()
        inside = (sx <= cx <= sx + sw) and (sy <= cy <= sy + sh)

        if inside and not self._inside_drop:
            self.seq_frame.configure(border_color="#00c853")  # verde
            self._drop_hint.configure(text_color="#00c853")
            self._inside_drop = True
        elif not inside and self._inside_drop:
            self.seq_frame.configure(border_color="#ccc")
            self._drop_hint.configure(text_color="gray50")
            self._inside_drop = False

    def _global_release(self, event):
        if not self._preview_win:
            self._cleanup_drag_binds()
            return

        cx, cy = event.x_root, event.y_root
        sx, sy = self.seq_frame.winfo_rootx(), self.seq_frame.winfo_rooty()
        sw, sh = self.seq_frame.winfo_width(), self.seq_frame.winfo_height()
        inside = (sx <= cx <= sx + sw) and (sy <= cy <= sy + sh)

        if inside and self._drag_action:
            self.add_action(self._drag_action)
            self.status_label.configure(text=f"{self._drag_action} añadida a la secuencia.", text_color="green")
        else:
            self.status_label.configure(text="Suelta dentro del recuadro verde para añadir.", text_color="red")

        self._end_preview_if_any()
        try:
            self._drop_hint.destroy()
        except Exception:
            pass
        self.seq_frame.configure(border_color="#ccc")
        self._cleanup_drag_binds()
        self._drag_action = None
        self._inside_drop = False

    def _end_preview_if_any(self):
        if self._preview_win:
            try:
                self._preview_win.destroy()
            except Exception:
                pass
            self._preview_win = None
            self._preview_imgtk = None

    def _cleanup_drag_binds(self):
        try:
            self.unbind_all("<Motion>")
            self.unbind_all("<ButtonRelease-1>")
        except Exception:
            pass

    # ---------- Add / remove ----------
    def add_action(self, action):
        block = ctk.CTkFrame(self.seq_frame, border_color="#ccc", border_width=1, corner_radius=8)
        block.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(block, image=self.icons[action], text="").pack(side="left", padx=6, pady=6)

        param_var = ctk.StringVar(value="1")
        if action in ["Izquierda", "Derecha"]:
            opt = ctk.CTkOptionMenu(block, values=["45", "90", "180"])
            opt.set("90")
            opt.pack(side="left", padx=6)
            param_getter = lambda: opt.get()
        elif action in ["Adelante", "Reversa", "Esperar"]:
            ent = ctk.CTkEntry(block, width=80, textvariable=param_var)
            ent.pack(side="left", padx=6)
            param_getter = lambda: param_var.get()
        else:
            param_getter = lambda: ""

        del_btn = ctk.CTkButton(block, text="✕", width=30, fg_color="#b71c1c",
                                command=lambda b=block: self.remove_action(b))
        del_btn.pack(side="right", padx=6, pady=6)

        self.sequence.append({"type": action, "frame": block, "param_getter": param_getter})
        self._update_seq_text()

    def remove_action(self, frame):
        self.sequence = [s for s in self.sequence if s["frame"] != frame]
        frame.destroy()
        self._update_seq_text()

    def clear_sequence(self):
        for s in list(self.sequence):
            s["frame"].destroy()
        self.sequence.clear()
        self._update_seq_text()
        self.status_label.configure(text="Secuencia limpiada", text_color="gray")

    def _update_seq_text(self):
        self.seq_box.delete("1.0", "end")
        for i, s in enumerate(self.sequence, 1):
            self.seq_box.insert("end", f"{i}. {s['type']}\n")

    # ---------- Bluetooth ----------
    def _toggle_bt_panel(self):
        if self.bt_panel.winfo_ismapped():
            self.bt_panel.pack_forget()
        else:
            self.bt_panel.pack(side="right", fill="y", padx=8, pady=8)

    def scan_all(self):
        for w in self.frame_devices.winfo_children():
            w.destroy()
        self.scan_results.clear()
        threading.Thread(target=lambda: asyncio.run(self._scan_task()), daemon=True).start()

    async def _scan_task(self):
        if HAS_PYSERIAL:
            ports = serial.tools.list_ports.comports()
            for p in ports:
                e = {"kind": "serial", "port": p.device, "desc": p.description}
                self.scan_results.append(e)
                self.after(0, lambda e=e: self._add_device_row(e))
        if HAS_BLEAK:
            devs = await BleakScanner.discover(timeout=3.0)
            for d in devs:
                e = {"kind": "ble", "addr": d.address, "name": d.name or "Desconocido"}
                self.scan_results.append(e)
                self.after(0, lambda e=e: self._add_device_row(e))

    def _add_device_row(self, e):
        f = ctk.CTkFrame(self.frame_devices)
        f.pack(fill="x", padx=6, pady=4)
        text = e.get("port", e.get("addr", "?"))
        lbl = ctk.CTkLabel(f, text=text, anchor="w")
        lbl.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkButton(f, text="Seleccionar", width=100,
                      command=lambda e=e: self._select_scan_entry(e)).pack(side="right", padx=6)

    def _select_scan_entry(self, e):
        self.selected_scan_entry = e
        self.lbl_bt_state.configure(text=f"Seleccionado: {e.get('port', e.get('addr'))}", text_color="blue")

    def connect_selected(self):
        if not self.selected_scan_entry:
            self.lbl_bt_state.configure(text="Seleccione un dispositivo", text_color="red")
            return
        e = self.selected_scan_entry
        if e["kind"] == "serial":
            threading.Thread(target=self._connect_serial_thread, args=(e["port"],), daemon=True).start()
        else:
            threading.Thread(target=lambda: asyncio.run(self._connect_ble(e["addr"])), daemon=True).start()

    def _connect_serial_thread(self, port):
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.serial_port = serial.Serial(port, 9600, timeout=1)
            self.connected_mode = "serial"
            self.after(0, lambda: self.lbl_bt_state.configure(text=f"Conectado (Serial): {port}", text_color="green"))
        except Exception as e:
            self.after(0, lambda: self.lbl_bt_state.configure(text=f"Error: {e}", text_color="red"))

    async def _connect_ble(self, addr):
        try:
            self.ble_client = BleakClient(addr)
            await self.ble_client.connect(timeout=8)
            self.connected_mode = "ble"
            self.after(0, lambda: self.lbl_bt_state.configure(text=f"Conectado (BLE): {addr}", text_color="green"))
        except Exception as e:
            self.after(0, lambda: self.lbl_bt_state.configure(text=f"Error BLE: {e}", text_color="red"))

    def disconnect_current(self):
        if self.connected_mode == "serial" and self.serial_port:
            try:
                self.serial_port.close()
            except:
                pass
        elif self.connected_mode == "ble" and self.ble_client:
            try:
                asyncio.run(self.ble_client.disconnect())
            except:
                pass
        self.connected_mode = None
        try:
            self.lbl_bt_state.configure(text="No conectado", text_color="red")
        except Exception:
            pass

    # ---------- Execution ----------
    def start_execution(self):
        if not self.sequence:
            self.status_label.configure(text="Secuencia vacía", text_color="red")
            return
        if not self.connected_mode:
            self.status_label.configure(text="No conectado", text_color="red")
            return
        self._stop_execution.clear()
        threading.Thread(target=self._execute_thread, daemon=True).start()

    def stop_execution(self):
        self._stop_execution.set()
        self.status_label.configure(text="Ejecución detenida", text_color="orange")

    def _execute_thread(self):
        # "Encender" quitado del mapeo
        cmd_map = {"Adelante": "A", "Izquierda": "I", "Derecha": "D", "Reversa": "R",
                   "Detener": "S", "Esperar": "W"}
        for idx, it in enumerate(self.sequence, 1):
            if self._stop_execution.is_set():
                break
            code = cmd_map.get(it["type"], "?")
            val = it["param_getter"]()
            msg = f"{code}{val}"
            self._send_command(msg)
            self.after(0, lambda i=idx, t=it["type"]: self.status_label.configure(
                text=f"Ejecutando {i}: {t}", text_color="black"))
            time.sleep(1)
        self.after(0, lambda: self.status_label.configure(text="Secuencia completada", text_color="green"))

    def _send_command(self, msg):
        try:
            if self.connected_mode == "serial" and self.serial_port and self.serial_port.is_open:
                self.serial_port.write(msg.encode())
            elif self.connected_mode == "ble" and self.ble_client:
                # usar write_gatt_char si está conectado
                try:
                    asyncio.run(self.ble_client.write_gatt_char(CHAR_UUID, msg.encode()))
                except Exception:
                    pass
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"Error al enviar: {e}", text_color="red"))


if __name__ == "__main__":
    app = DragDropApp()
    app.mainloop()

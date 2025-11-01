import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import os, threading, time, serial, serial.tools.list_ports, tkinter as tk

# ---------------- CONFIG ----------------
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ROOT_DIR = os.path.dirname(__file__)
IMAGES_DIR = os.path.join(ROOT_DIR, "imagenes")

# ---------------- APP ----------------
class DragDropApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Control Bluetooth Arduino - Puerto COM")
        self.geometry("1200x700")

        self.sequence = []
        self.serial_port = None
        self.selected_port = None
        self._stop_execution = threading.Event()

        # iconos
        self.icons = {}
        self.icons_pil = {}
        self._load_icons()
        self._build_ui()

        # drag & drop vars
        self._preview_win = None
        self._preview_imgtk = None
        self._drag_action = None

    # ---------- load icons ----------
    def _load_icon_safe(self, fname, size=(64, 64)):
        p = os.path.join(IMAGES_DIR, fname)
        try:
            pil = Image.open(p).convert("RGBA")
            pil.thumbnail(size, Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=size)
            return ctk_img, pil
        except Exception:
            ph = Image.new("RGBA", size, (230, 230, 230, 255))
            draw = ImageDraw.Draw(ph)
            draw.rectangle((4, 4, size[0]-4, size[1]-4), outline=(180, 180, 180))
            return ctk.CTkImage(light_image=ph, dark_image=ph, size=size), ph

    def _load_icons(self):
        mapping = {
            "Adelante": "adelante.png",
            "Izquierda": "izquierda.png",
            "Derecha": "derecha.png",
            "Reversa": "reversa.png",
            "Detener": "detener.png",
            "Esperar": "esperar.png",
            "Bluetooth": "bluetooth.png"
        }
        for action_name, fname in mapping.items():
            ctk_img, pil_img = self._load_icon_safe(fname)
            self.icons[action_name] = ctk_img
            self.icons_pil[action_name] = pil_img

    # ---------- build UI ----------
    def _build_ui(self):
        # panel izquierdo (acciones)
        self.left = ctk.CTkFrame(self, width=260)
        self.left.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(self.left, text="Acciones", font=("Arial", 16, "bold")).pack(pady=(6, 8))
        for action in ["Adelante", "Izquierda", "Derecha", "Reversa", "Detener", "Esperar"]:
            btn = ctk.CTkButton(self.left, image=self.icons[action], text="", width=90, height=70)
            btn.pack(pady=6, padx=8)
            btn.bind("<ButtonPress-1>", lambda e, a=action: self._start_drag(e, a))

        ctk.CTkLabel(self.left, text="Secuencia actual:", font=("Arial", 13, "bold")).pack(pady=(12, 4))
        self.seq_box = ctk.CTkTextbox(self.left, height=160)
        self.seq_box.pack(padx=6, pady=4, fill="x")

        # centro
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
        ctk.CTkLabel(self.bt_panel, text="Conexión Bluetooth (COM)", font=("Arial", 16, "bold")).pack(pady=10)
        self.frame_devices = ctk.CTkScrollableFrame(self.bt_panel, height=300)
        self.frame_devices.pack(fill="both", padx=10, pady=6)
        ctk.CTkButton(self.bt_panel, text="🔍 Buscar puertos COM", command=self.scan_ports).pack(fill="x", padx=10, pady=(4, 8))
        self.lbl_bt_state = ctk.CTkLabel(self.bt_panel, text="No conectado", text_color="red")
        self.lbl_bt_state.pack(pady=6)
        fr_conn = ctk.CTkFrame(self.bt_panel)
        fr_conn.pack(pady=6)
        ctk.CTkButton(fr_conn, text="Conectar", fg_color="#2e7d32", command=self.connect_serial).grid(row=0, column=0, padx=6)
        ctk.CTkButton(fr_conn, text="Desconectar", fg_color="#c62828", command=self.disconnect_serial).grid(row=0, column=1, padx=6)

        icon_bt = self.icons.get("Bluetooth")
        self.bt_button = ctk.CTkButton(self, image=icon_bt, text="", width=44, height=38, command=self._toggle_bt_panel)
        self.bt_button.place(relx=0.99, rely=0.02, anchor="ne")

    # ---------- DRAG & DROP ----------
    def _start_drag(self, event, action):
        self._drag_action = action
        self._preview_win = tk.Toplevel(self)
        self._preview_win.overrideredirect(True)
        pil_img = self.icons_pil.get(action)
        self._preview_imgtk = ImageTk.PhotoImage(pil_img)
        lbl = tk.Label(self._preview_win, image=self._preview_imgtk, bg="white", bd=1, relief="solid")
        lbl.pack()
        self._preview_win.geometry(f"+{event.x_root}+{event.y_root}")
        self._drop_hint = ctk.CTkLabel(self.seq_frame, text="📍 Suelta aquí", font=("Arial", 22, "bold"), text_color="gray50")
        self._drop_hint.place(relx=0.5, rely=0.5, anchor="center")
        self.bind_all("<Motion>", self._global_motion)
        self.bind_all("<ButtonRelease-1>", self._global_release)

    def _global_motion(self, event):
        if not self._preview_win:
            return
        self._preview_win.geometry(f"+{event.x_root+8}+{event.y_root+8}")
        cx, cy = event.x_root, event.y_root
        sx, sy = self.seq_frame.winfo_rootx(), self.seq_frame.winfo_rooty()
        sw, sh = self.seq_frame.winfo_width(), self.seq_frame.winfo_height()
        inside = (sx <= cx <= sx + sw) and (sy <= cy <= sy + sh)
        color = "#00c853" if inside else "#ccc"
        self.seq_frame.configure(border_color=color)
        self._drop_hint.configure(text_color=color)

    def _global_release(self, event):
        if not self._preview_win:
            return
        cx, cy = event.x_root, event.y_root
        sx, sy = self.seq_frame.winfo_rootx(), self.seq_frame.winfo_rooty()
        sw, sh = self.seq_frame.winfo_width(), self.seq_frame.winfo_height()
        inside = (sx <= cx <= sx + sw) and (sy <= cy <= sy + sh)
        if inside and self._drag_action:
            self.add_action(self._drag_action)
        self._preview_win.destroy()
        self._preview_win = None
        self._drop_hint.destroy()
        self.unbind_all("<Motion>")
        self.unbind_all("<ButtonRelease-1>")

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

    def _update_seq_text(self):
        self.seq_box.delete("1.0", "end")
        for i, s in enumerate(self.sequence, 1):
            self.seq_box.insert("end", f"{i}. {s['type']}\n")

    # ---------- Bluetooth COM ----------
    def _toggle_bt_panel(self):
        if self.bt_panel.winfo_ismapped():
            self.bt_panel.pack_forget()
        else:
            self.bt_panel.pack(side="right", fill="y", padx=8, pady=8)

    def scan_ports(self):
        for w in self.frame_devices.winfo_children():
            w.destroy()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            f = ctk.CTkFrame(self.frame_devices)
            f.pack(fill="x", padx=6, pady=4)
            lbl = ctk.CTkLabel(f, text=f"{p.description} ({p.device})", anchor="w")
            lbl.pack(side="left", fill="x", expand=True, padx=6)
            ctk.CTkButton(f, text="Seleccionar", width=100,
                          command=lambda port=p.device: self._select_port(port)).pack(side="right", padx=6)

    def _select_port(self, port):
        self.selected_port = port
        self.lbl_bt_state.configure(text=f"Seleccionado: {port}", text_color="blue")

    def connect_serial(self):
        if not self.selected_port:
            self.lbl_bt_state.configure(text="Seleccione un puerto", text_color="red")
            return
        try:
            self.serial_port = serial.Serial(self.selected_port, 9600, timeout=1)
            self.lbl_bt_state.configure(text=f"✅ Conectado a {self.selected_port}", text_color="green")
        except Exception as e:
            self.lbl_bt_state.configure(text=f"Error: {e}", text_color="red")

    def disconnect_serial(self):
        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None
            self.lbl_bt_state.configure(text="No conectado", text_color="red")

    # ---------- Execution ----------
    def start_execution(self):
        if not self.sequence:
            self.status_label.configure(text="Secuencia vacía", text_color="red")
            return
        if not self.serial_port:
            self.status_label.configure(text="No conectado", text_color="red")
            return
        self._stop_execution.clear()
        threading.Thread(target=self._execute_thread, daemon=True).start()

    def stop_execution(self):
        self._stop_execution.set()
        self.status_label.configure(text="Ejecución detenida", text_color="orange")

    def _execute_thread(self):
        cmd_map = {"Adelante": "A", "Izquierda": "I", "Derecha": "D", "Reversa": "R",
                   "Detener": "S", "Esperar": "W"}
        for idx, it in enumerate(self.sequence, 1):
            if self._stop_execution.is_set():
                break
            code = cmd_map.get(it["type"], "?")
            val = it["param_getter"]()
            msg = f"{code}{val}\n"
            self._send_serial(msg)
            self.after(0, lambda i=idx, t=it["type"]: self.status_label.configure(
                text=f"Ejecutando {i}: {t}", text_color="black"))
            time.sleep(1)
        self.after(0, lambda: self.status_label.configure(text="Secuencia completada", text_color="green"))

    def _send_serial(self, msg):
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(msg.encode())
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"Error al enviar: {e}", text_color="red"))


if __name__ == "__main__":
    app = DragDropApp()
    app.mainloop()

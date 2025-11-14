import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import os, asyncio, threading, serial, serial.tools.list_ports, tkinter as tk
from bleak import BleakScanner

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ROOT_DIR = os.path.dirname(__file__)
IMAGES_DIR = os.path.join(ROOT_DIR, "imagenes")


class DragDropApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Control Bluetooth - HC/BLE")
        self.geometry("1200x800")
        self.configure(bg="#f8f9fa")

        self.blocks = []
        self.bt_connected = False
        self.serial_port = None
        self.selected_device = None
        self.icons = {}
        self.icons_pil = {}

        self._load_icons()
        self._build_ui()

    # ---------- ICONOS ----------
    def _load_icon_safe(self, fname, size=(55, 55)):
        p = os.path.join(IMAGES_DIR, fname)
        try:
            pil = Image.open(p).convert("RGBA")
            pil.thumbnail(size, Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=size)
            return ctk_img, pil
        except Exception:
            ph = Image.new("RGBA", size, (220, 220, 220, 255))
            draw = ImageDraw.Draw(ph)
            draw.rectangle((5, 5, size[0]-5, size[1]-5), outline=(180, 180, 180))
            draw.text((8, 8), fname.split(".")[0][:6], fill=(80, 80, 80))
            return ctk.CTkImage(light_image=ph, dark_image=ph, size=size), ph

    def _load_icons(self):
        mapping = {
            "Velocidad": "velocidad.png",
            "Adelante": "adelante.png",
            "Izquierda": "izquierda.png",
            "Derecha": "derecha.png",
            "Reversa": "reversa.png",
            "Detener": "detener.png",
            "Esperar": "esperar.png",
            "Bluetooth": "bluetooth.png",
            "Ejecutar": "ejecutar.png",
            "Limpiar": "limpiar.png"
        }
        for k, f in mapping.items():
            ctk_img, pil_img = self._load_icon_safe(f)
            self.icons[k] = ctk_img
            self.icons_pil[k] = pil_img

    # ---------- UI ----------
    def _build_ui(self):
        self.seq_area = tk.Canvas(self, bg="#dee2e6", highlightthickness=0)
        self.seq_area.pack(fill="both", expand=True, padx=15, pady=(60, 0))
        self.seq_area.create_text(
            600, 100,
            text="🧩 Arrastra los bloques aquí para crear tu secuencia",
            fill="#6c757d",
            font=("Arial Rounded MT Bold", 15, "italic")
        )

        # Botones ejecutar y limpiar
        self.btn_run = ctk.CTkButton(self, image=self.icons["Ejecutar"], text="", width=45, height=45,
                                     fg_color="#38b000", hover_color="#2d8700", command=self._run_sequence)
        self.btn_run.place(relx=0.08, rely=0.05, anchor="nw")

        self.btn_clear = ctk.CTkButton(self, image=self.icons["Limpiar"], text="", width=45, height=45,
                                       fg_color="#6c757d", hover_color="#495057", command=self.clear_all)
        self.btn_clear.place(relx=0.03, rely=0.05, anchor="nw")

        self.status_label = ctk.CTkLabel(self, text="Listo", text_color="gray", bg_color="#f8f9fa")
        self.status_label.place(relx=0.18, rely=0.05)

        # Panel inferior
        bottom = ctk.CTkFrame(self, height=120, fg_color="#ffd60a")
        bottom.pack(side="bottom", fill="x", padx=10, pady=10)
        ctk.CTkLabel(bottom, text="Bloques disponibles:", font=("Arial Rounded MT Bold", 14)).pack(anchor="w", padx=10)
        bar = ctk.CTkFrame(bottom, fg_color="transparent")
        bar.pack(pady=6)

        for action in ["Velocidad", "Adelante", "Izquierda", "Derecha", "Reversa", "Detener", "Esperar"]:
            btn = ctk.CTkButton(bar, image=self.icons[action], text="", width=75, height=75,
                                fg_color="#ffffff", hover_color="#e9ecef", corner_radius=12)
            btn.pack(side="left", padx=10)
            btn.bind("<ButtonPress-1>", lambda e, a=action: self._start_drag(e, a))

        # Bluetooth button
        bt_icon = self.icons["Bluetooth"]
        self.bt_btn = ctk.CTkButton(self, image=bt_icon, text="", width=45, height=45,
                                    corner_radius=25, fg_color="#4cc9f0", hover_color="#3ab0de",
                                    command=self._toggle_bt_panel)
        self.bt_btn.place(relx=0.97, rely=0.05, anchor="ne")

        self.bt_panel = ctk.CTkFrame(self, width=280, fg_color="#e0f7fa", corner_radius=12)
        self._build_bt_panel()

    # ---------- DRAG & DROP ----------
    def _start_drag(self, event, action):
        self.drag_action = action
        self.preview_win = tk.Toplevel(self)
        self.preview_win.overrideredirect(True)
        pil = self.icons_pil[action]
        imgtk = ImageTk.PhotoImage(pil)
        lbl = tk.Label(self.preview_win, image=imgtk, bg="white")
        lbl.image = imgtk
        lbl.pack()
        self.preview_win.geometry(f"+{event.x_root}+{event.y_root}")
        self.bind_all("<Motion>", self._on_motion)
        self.bind_all("<ButtonRelease-1>", self._on_release)

    def _on_motion(self, e):
        if self.preview_win:
            self.preview_win.geometry(f"+{e.x_root+10}+{e.y_root+10}")

    def _on_release(self, e):
        if not self.preview_win:
            return
        x, y = e.x_root, e.y_root
        sx, sy = self.seq_area.winfo_rootx(), self.seq_area.winfo_rooty()
        sw, sh = self.seq_area.winfo_width(), self.seq_area.winfo_height()
        if sx <= x <= sx + sw and sy <= y <= sy + sh:
            relx, rely = x - sx, y - sy
            self._place_block(self.drag_action, relx, rely)
        self.preview_win.destroy()
        self.preview_win = None
        self.unbind_all("<Motion>")
        self.unbind_all("<ButtonRelease-1>")

    # ---------- BLOQUES ----------
    def _place_block(self, action, x, y):
        frame = ctk.CTkFrame(self.seq_area, fg_color="#ffffff", corner_radius=10, border_width=2, border_color="#adb5bd")
        lbl = ctk.CTkLabel(frame, image=self.icons[action], text="")
        lbl.pack(side="left", padx=3)

        entry = None
        if action in ["Adelante", "Reversa", "Esperar"]:
            entry = ctk.CTkEntry(frame, width=40, placeholder_text="s")
            entry.pack(side="left", padx=2)
        elif action in ["Izquierda", "Derecha"]:
            entry = ctk.CTkEntry(frame, width=40, placeholder_text="°")
            entry.pack(side="left", padx=2)
        elif action == "Velocidad":
            entry = ctk.CTkEntry(frame, width=50, placeholder_text="vel")
            entry.insert(0, "100")
            entry.pack(side="left", padx=2)

        btn_del = ctk.CTkButton(frame, text="✖", width=20, fg_color="#c62828",
                                hover_color="#a71d2a", command=lambda f=frame: self._delete_block(f))
        btn_del.pack(side="right", padx=2)

        idw = self.seq_area.create_window(x, y, window=frame)
        frame.bind("<B1-Motion>", lambda ev, fid=idw: self._drag_block(ev, fid))

        self.blocks.append({"id": idw, "frame": frame, "type": action, "param": entry})

    def _drag_block(self, event, window_id):
        self.seq_area.move(window_id, event.x - 40, event.y - 40)

    def _delete_block(self, frame):
        for b in list(self.blocks):
            if b["frame"] == frame:
                self.seq_area.delete(b["id"])
                b["frame"].destroy()
                self.blocks.remove(b)
                break

    # ---------- BLUETOOTH ----------
    def _build_bt_panel(self):
        ctk.CTkLabel(self.bt_panel, text="🔵 Bluetooth (HC / BLE)",
                     font=("Arial Rounded MT Bold", 16), text_color="#0077b6").pack(pady=10)
        self.btn_scan = ctk.CTkButton(self.bt_panel, text="🔍 Buscar dispositivos",
                                      fg_color="#48cae4", hover_color="#00b4d8", command=self.scan_devices)
        self.btn_scan.pack(pady=5)
        self.frame_devices = ctk.CTkScrollableFrame(self.bt_panel, height=250)
        self.frame_devices.pack(fill="both", padx=10, pady=6)
        self.lbl_bt = ctk.CTkLabel(self.bt_panel, text="No conectado", text_color="red")
        self.lbl_bt.pack(pady=4)

    def _toggle_bt_panel(self):
        if self.bt_panel.winfo_ismapped():
            self.bt_panel.place_forget()
        else:
            self.bt_panel.place(relx=0.985, rely=0.13, anchor="ne")

    def scan_devices(self):
        for w in self.frame_devices.winfo_children():
            w.destroy()
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        try:
            devices = []

            # 1️⃣ Escaneo BLE
            self.lbl_bt.configure(text="Buscando BLE...", text_color="blue")
            ble_devices = asyncio.run(BleakScanner.discover(timeout=5.0))
            for d in ble_devices:
                if d.name:
                    devices.append(("BLE", d.name, d.address))

            # 2️⃣ Escaneo HC (puertos COM)
            self.lbl_bt.configure(text="Buscando HC-05/06...", text_color="blue")
            ports = serial.tools.list_ports.comports()
            for p in ports:
                if "HC" in p.description or "Bluetooth" in p.description:
                    devices.append(("HC", p.description, p.device))

            if not devices:
                self.lbl_bt.configure(text="⚠ No se encontraron dispositivos", text_color="orange")
                return

            for typ, name, addr in devices:
                fr = ctk.CTkFrame(self.frame_devices, fg_color="#caf0f8", corner_radius=6)
                fr.pack(fill="x", padx=4, pady=3)
                btn = ctk.CTkButton(fr, text=f"[{typ}] {name} ({addr})", fg_color="#00b4d8",
                                    hover_color="#0096c7",
                                    command=lambda t=typ, a=addr: self._connect_device(t, a))
                btn.pack(fill="x", padx=5, pady=3)

            self.lbl_bt.configure(text="Selecciona un dispositivo para conectar", text_color="green")

        except Exception as e:
            self.lbl_bt.configure(text=f"Error: {e}", text_color="red")

    def _connect_device(self, dev_type, address):
        try:
            if dev_type == "HC":
                self.serial_port = serial.Serial(address, 9600, timeout=1)
                self.bt_connected = True
                self.lbl_bt.configure(text=f"✅ Conectado a {address}", text_color="green")
            else:
                self.lbl_bt.configure(text=f"BLE detectado: {address}\n(soporte lectura opcional)", text_color="blue")
        except Exception as e:
            self.lbl_bt.configure(text=f"Error: {e}", text_color="red")

    # ---------- EJECUTAR ----------
    def _run_sequence(self):
        self.status_label.configure(text="Ejecutando secuencia...", text_color="blue")

    # ---------- LIMPIAR ----------
    def clear_all(self):
        for b in self.blocks:
            try:
                self.seq_area.delete(b["id"])
                b["frame"].destroy()
            except:
                pass
        self.blocks.clear()
        self.status_label.configure(text="Todo limpio", text_color="gray")


if __name__ == "__main__":
    app = DragDropApp()
    app.mainloop()

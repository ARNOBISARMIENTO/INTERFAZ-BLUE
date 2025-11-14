import customtkinter as ctk 
from PIL import Image, ImageTk
import os, serial, serial.tools.list_ports, tkinter as tk

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ROOT_DIR = os.path.dirname(__file__)
IMAGES_DIR = os.path.join(ROOT_DIR, "imagenes")


class DragDropApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Control Bluetooth - Estilo LEGO WeDo")
        self.geometry("1200x800")
        self.configure(bg="#f8f9fa")

        self.sequence = []
        self.serial_port = None
        self.bt_connected = False
        self.selected_port = None
        self.drag_action = None
        self.preview_win = None
        self.drag_line = None
        self.dragging_container = None
        self.containers = []
        self.blocks = []
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
            from PIL import ImageDraw
            ph = Image.new("RGBA", size, (220, 220, 220, 255))
            draw = ImageDraw.Draw(ph)
            draw.rectangle((5, 5, size[0]-5, size[1]-5), outline=(180, 180, 180))
            return ctk.CTkImage(light_image=ph, dark_image=ph, size=size), ph

    def _load_icons(self):
        mapping = {
            "Contenedor": "contenedor.png",
            "Adelante": "adelante.png",
            "Izquierda": "izquierda.png",
            "Derecha": "derecha.png",
            "Reversa": "reversa.png",
            "Detener": "detener.png",
            "Esperar": "esperar.png",
            "Bluetooth": "bluetooth.png"
        }
        for k, f in mapping.items():
            ctk_img, pil_img = self._load_icon_safe(f)
            self.icons[k] = ctk_img
            self.icons_pil[k] = pil_img

    # ---------- UI ----------
    def _build_ui(self):
        self.seq_area = tk.Canvas(self, bg="#dee2e6", highlightthickness=0)
        self.seq_area.pack(fill="both", expand=True, padx=15, pady=(60, 0))
        self.seq_area.create_text(600, 100, text="🧩 Arrastra los bloques o un contenedor aquí",
                                  fill="#6c757d", font=("Arial Rounded MT Bold", 15, "italic"))

        self.btn_clear = ctk.CTkButton(self, text="🧹 Limpiar todo", fg_color="#6c757d", hover_color="#495057",
                                       text_color="white", command=self.clear_all)
        self.btn_clear.place(relx=0.03, rely=0.05, anchor="nw")

        self.status_label = ctk.CTkLabel(self, text="Listo", text_color="gray", bg_color="#f8f9fa")
        self.status_label.place(relx=0.18, rely=0.05)

        bottom = ctk.CTkFrame(self, height=120, fg_color="#ffd60a")
        bottom.pack(side="bottom", fill="x", padx=10, pady=10)

        ctk.CTkLabel(bottom, text="Bloques disponibles:", font=("Arial Rounded MT Bold", 14)).pack(anchor="w", padx=10)
        bar = ctk.CTkFrame(bottom, fg_color="transparent")
        bar.pack(pady=6)

        for action in ["Contenedor", "Adelante", "Izquierda", "Derecha", "Reversa", "Detener", "Esperar"]:
            btn = ctk.CTkButton(bar, image=self.icons[action], text="", width=75, height=75,
                                fg_color="#ffffff", hover_color="#e9ecef", corner_radius=12)
            btn.pack(side="left", padx=10)
            btn.bind("<ButtonPress-1>", lambda e, a=action: self._start_drag(e, a))

        bt_icon = self.icons["Bluetooth"]
        self.bt_btn = ctk.CTkButton(self, image=bt_icon, text="", width=45, height=45,
                                    corner_radius=25, fg_color="#4cc9f0", hover_color="#3ab0de",
                                    command=self._toggle_bt_panel)
        self.bt_btn.place(relx=0.97, rely=0.05, anchor="ne")

        self.bt_panel = ctk.CTkFrame(self, width=260, fg_color="#e0f7fa", corner_radius=12)
        self._build_bt_panel()

    # ---------- DRAG ----------
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
        if not self.preview_win:
            return
        self.preview_win.geometry(f"+{e.x_root+10}+{e.y_root+10}")
        for c in self.containers:
            bbox = self.seq_area.bbox(c["id"])
            if bbox:
                sx, sy, ex, ey = bbox
                if sx < e.x_root - self.seq_area.winfo_rootx() < ex and sy < e.y_root - self.seq_area.winfo_rooty() < ey:
                    inner = c["inner"]
                    blocks = c["blocks"]
                    x_inner = e.x_root - inner.winfo_rootx()
                    self._show_inner_line(inner, blocks, x_inner)
                    return
        self._clear_inner_line()

    def _on_release(self, e):
        if not self.preview_win:
            return
        x, y = e.x_root, e.y_root
        sx, sy = self.seq_area.winfo_rootx(), self.seq_area.winfo_rooty()
        sw, sh = self.seq_area.winfo_width(), self.seq_area.winfo_height()
        if sx <= x <= sx + sw and sy <= y <= sy + sh:
            relx, rely = x - sx, y - sy
            if self.drag_action == "Contenedor":
                self._create_container(relx, rely)
            else:
                self._place_block(self.drag_action, relx, rely)
        self._clear_inner_line()
        self.preview_win.destroy()
        self.preview_win = None
        self.unbind_all("<Motion>")
        self.unbind_all("<ButtonRelease-1>")

    # ---------- LÍNEA DENTRO ----------
    def _show_inner_line(self, inner, blocks, x_inner):
        self._clear_inner_line()
        if not blocks:
            self.inner_line = tk.Frame(inner, bg="#7209b7", width=4, height=70)
            self.inner_line.pack(side="left", padx=5)
            return
        for i, blk in enumerate(blocks):
            mid = blk["frame"].winfo_x() + blk["frame"].winfo_width() // 2
            if x_inner < mid:
                self.inner_line = tk.Frame(inner, bg="#7209b7", width=4, height=70)
                self.inner_line.pack(side="left", before=blk["frame"], padx=2)
                return
        self.inner_line = tk.Frame(inner, bg="#7209b7", width=4, height=70)
        self.inner_line.pack(side="left", padx=2)

    def _clear_inner_line(self):
        if hasattr(self, "inner_line") and self.inner_line.winfo_exists():
            self.inner_line.destroy()

    # ---------- CONTENEDORES ----------
    def _create_container(self, x, y):
        frame = ctk.CTkFrame(self.seq_area, border_color="#7209b7", border_width=3,
                             corner_radius=12, fg_color="#e0bbf5")
        label = ctk.CTkLabel(frame, text=f"Secuencia {len(self.containers)+1}",
                             font=("Arial Rounded MT Bold", 14), text_color="#240046")
        label.pack(pady=(4, 2))
        inner = ctk.CTkFrame(frame, fg_color="#ffffff", corner_radius=10)
        inner.pack(fill="both", expand=True, padx=10, pady=10)
        inner_container = tk.Frame(inner, bg="white")
        inner_container.pack(side="left", padx=5, pady=5)

        fr_btn = ctk.CTkFrame(frame, fg_color="transparent")
        fr_btn.pack(pady=5)
        run = ctk.CTkButton(fr_btn, text="▶ Ejecutar", fg_color="#38b000", hover_color="#2d8700",
                            command=lambda c=inner_container: self._run_container(c))
        run.pack(side="left", padx=4)
        clear = ctk.CTkButton(fr_btn, text="🧹 Limpiar", fg_color="#6c757d", hover_color="#495057",
                              command=lambda c=inner_container: self._clear_container(c))
        clear.pack(side="left", padx=4)

        id_container = self.seq_area.create_window(x, y, window=frame, anchor="center")
        self.containers.append({"id": id_container, "frame": frame, "inner": inner_container, "blocks": []})
        self._make_container_draggable(self.containers[-1])

    def _make_container_draggable(self, container):
        frame = container["frame"]

        def start_drag(event):
            frame._drag_data = {"x": event.x, "y": event.y}

        def do_drag(event):
            dx = event.x - frame._drag_data["x"]
            dy = event.y - frame._drag_data["y"]
            self.seq_area.move(container["id"], dx, dy)

        frame.bind("<Button-1>", start_drag)
        frame.bind("<B1-Motion>", do_drag)

    # ---------- BLOQUES ----------
    def _place_block(self, action, x, y):
        for c in self.containers:
            bbox = self.seq_area.bbox(c["id"])
            if bbox:
                sx, sy, ex, ey = bbox
                if sx < x < ex and sy < y < ey:
                    self._add_block_to_container(c, action)
                    return
        lbl = ctk.CTkLabel(self.seq_area, image=self.icons[action], text="")
        self.seq_area.create_window(x, y, window=lbl)
        lbl.bind("<Button-3>", lambda e, b=lbl: self._delete_free_block(b))
        self.blocks.append(lbl)

    def _add_block_to_container(self, container, action):
        inner = container["inner"]
        blk = ctk.CTkFrame(inner, border_color="#ced4da", border_width=1, corner_radius=8)
        if hasattr(self, "inner_line") and self.inner_line.winfo_exists():
            blk.pack(in_=inner, side="left", before=self.inner_line, padx=4, pady=4)
        else:
            blk.pack(side="left", padx=4, pady=4)

        lbl = ctk.CTkLabel(blk, image=self.icons[action], text="")
        lbl.image = self.icons[action]
        lbl.pack(side="left", padx=3)

        entry = None
        if action in ["Adelante", "Reversa", "Esperar"]:
            entry = ctk.CTkEntry(blk, width=40, placeholder_text="s")
            entry.pack(side="left", padx=2)
        elif action in ["Izquierda", "Derecha"]:
            entry = ctk.CTkEntry(blk, width=40, placeholder_text="°")
            entry.pack(side="left", padx=2)

        del_btn = ctk.CTkButton(blk, text="✖", width=20, fg_color="#c62828",
                                hover_color="#a71d2a", command=lambda b=blk: self._delete_block(container, b))
        del_btn.pack(side="right", padx=2)

        container["blocks"].append({"type": action, "frame": blk, "param": entry})
        self._clear_inner_line()

    # ---------- ELIMINAR Y LIMPIAR ----------
    def _delete_free_block(self, block):
        self.seq_area.delete(self.seq_area.find_withtag("current"))
        if block in self.blocks:
            self.blocks.remove(block)
        block.destroy()

    def _delete_block(self, container, block_frame):
        container["blocks"] = [b for b in container["blocks"] if b["frame"] != block_frame]
        block_frame.destroy()

    def _clear_container(self, inner_container):
        for c in self.containers:
            if c["inner"] == inner_container:
                for blk in c["blocks"]:
                    blk["frame"].destroy()
                c["blocks"].clear()
                break

    # ---------- EJECUTAR CONTENEDOR ----------
    def _run_container(self, inner_container):
        for c in self.containers:
            if c["inner"] == inner_container:
                self._execute_blocks(c["blocks"], 0)
                break

    def _execute_blocks(self, blocks, index):
        if index >= len(blocks):
            self.status_label.configure(text="Listo ✅", text_color="gray")
            if self.bt_connected:
                self.serial_port.write(b"S\n")
            return

        blk = blocks[index]
        action = blk["type"]
        entry = blk.get("param")
        param_value = 1
        if entry:
            try:
                param_value = float(entry.get())
            except:
                param_value = 1

        # Resaltar bloque actual
        highlight = tk.Frame(blk["frame"], bg="#ff6d00", highlightthickness=3)
        highlight.place(relx=0, rely=0, relwidth=1, relheight=1)

        display_text = f"{action}"
        if action in ["Esperar", "Adelante", "Reversa"]:
            display_text += f" - {param_value}s"
        elif action in ["Izquierda", "Derecha"]:
            display_text += f" - {param_value}°"

        self.status_label.configure(text=f"Ejecutando: {display_text}", text_color="blue")

        # Enviar comando al Arduino
        if self.bt_connected:
            cmd = {"Adelante": "F", "Reversa": "B", "Izquierda": "L", "Derecha": "R", "Detener": "S"}.get(action, "S")
            self.serial_port.write(cmd.encode())

        # ---- FLUIDEZ MEJORADA ----
        if action == "Esperar":
            delay = int(param_value * 1000)
        elif action in ["Adelante", "Reversa"]:
            delay = int(param_value * 1000)
        elif action in ["Izquierda", "Derecha"]:
            delay = int((param_value / 90) * 1000)
        else:
            delay = 700

        # pasa al siguiente bloque sin interrupciones
        self.after(delay, lambda: self._finish_block(highlight, blocks, index))

    def _finish_block(self, highlight, blocks, index):
        highlight.destroy()
        # detener movimiento antes de siguiente acción
        if self.bt_connected:
            self.serial_port.write(b"S")
        # ejecutar el siguiente bloque con transición fluida
        self.after(200, lambda: self._execute_blocks(blocks, index + 1))

    # ---------- BLUETOOTH ----------
    def _build_bt_panel(self):
        ctk.CTkLabel(self.bt_panel, text="🔵 Bluetooth", font=("Arial Rounded MT Bold", 16),
                     text_color="#0077b6").pack(pady=10)
        self.btn_scan = ctk.CTkButton(self.bt_panel, text="🔍 Buscar dispositivos", fg_color="#48cae4",
                                      hover_color="#00b4d8", command=self.scan_ports)
        self.btn_scan.pack(pady=5)
        self.frame_ports = ctk.CTkScrollableFrame(self.bt_panel, height=180)
        self.frame_ports.pack(fill="both", padx=10, pady=6)
        self.lbl_bt = ctk.CTkLabel(self.bt_panel, text="No conectado", text_color="red")
        self.lbl_bt.pack(pady=4)
        self.btn_connect = ctk.CTkButton(self.bt_panel, text="Conectar", fg_color="#0077b6",
                                         hover_color="#0096c7", command=self._connect_selected)
        self.btn_connect.pack(pady=4)
        self.btn_disconnect = ctk.CTkButton(self.bt_panel, text="Desconectar", fg_color="#c62828",
                                            hover_color="#a71d2a", command=self.disconnect_bt, state="disabled")
        self.btn_disconnect.pack(pady=4)

    def _toggle_bt_panel(self):
        if self.bt_panel.winfo_ismapped():
            self.bt_panel.place_forget()
        else:
            self.bt_panel.place(relx=0.985, rely=0.13, anchor="ne")

    def scan_ports(self):
        for w in self.frame_ports.winfo_children():
            w.destroy()
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            ctk.CTkLabel(self.frame_ports, text="No se encontraron dispositivos").pack(pady=5)
            return
        for p in ports:
            fr = ctk.CTkFrame(self.frame_ports, fg_color="#caf0f8", corner_radius=6)
            fr.pack(fill="x", padx=4, pady=3)
            btn = ctk.CTkButton(fr, text=f"{p.description} ({p.device})", fg_color="#00b4d8",
                                hover_color="#0096c7", command=lambda port=p.device: self._select_port(port))
            btn.pack(fill="x", padx=5, pady=3)

    def _select_port(self, port):
        self.selected_port = port
        self.lbl_bt.configure(text=f"Seleccionado: {port}", text_color="#0077b6")

    def _connect_selected(self):
        if not self.selected_port:
            self.lbl_bt.configure(text="⚠ Selecciona un puerto", text_color="orange")
            return
        self._connect_serial(self.selected_port)

    def _connect_serial(self, port):
        try:
            self.serial_port = serial.Serial(port, 9600, timeout=1)
            self.lbl_bt.configure(text=f"Conectado: {port}", text_color="green")
            self.btn_disconnect.configure(state="normal")
            self.bt_connected = True
        except Exception as e:
            self.lbl_bt.configure(text=f"Error: {e}", text_color="red")

    def disconnect_bt(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.lbl_bt.configure(text="Desconectado", text_color="red")
        self.btn_disconnect.configure(state="disabled")
        self.bt_connected = False

    # ---------- LIMPIAR ----------
    def clear_all(self):
        for c in self.containers:
            self.seq_area.delete(c["id"])
        for b in self.blocks:
            b.destroy()
        self.containers.clear()
        self.blocks.clear()
        self.status_label.configure(text="Todo limpio", text_color="gray")


if __name__ == "__main__":
    app = DragDropApp()
    app.mainloop()

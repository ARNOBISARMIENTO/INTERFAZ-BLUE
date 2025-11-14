import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import os, asyncio, tkinter as tk, traceback
from bleak import BleakScanner, BleakClient
import serial, serial.tools.list_ports

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ROOT_DIR = os.path.dirname(__file__)
IMAGES_DIR = os.path.join(ROOT_DIR, "imagenes")


class DragDropApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Control Bluetooth (BLE + HC) - LEGO Style")
        self.geometry("1200x800")
        self.configure(bg="#f8f9fa")

        # Estados y variables
        self.blocks = []
        self.bt_connected = False
        self.bt_client = None
        self.bt_write_char = None  # cached write characteristic for BLE
        self.serial_port = None
        self.selected_device = None
        self.devices = []
        self.drag_action = None
        self.preview_win = None
        self.icons, self.icons_pil = {}, {}
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

        self.btn_run = ctk.CTkButton(self, image=self.icons["Ejecutar"], text="", width=45, height=45,
                                     fg_color="#38b000", hover_color="#2d8700", command=self._run_sequence)
        self.btn_run.place(relx=0.08, rely=0.05, anchor="nw")

        self.btn_clear = ctk.CTkButton(self, image=self.icons["Limpiar"], text="", width=45, height=45,
                                       fg_color="#6c757d", hover_color="#495057", command=self.clear_all)
        self.btn_clear.place(relx=0.03, rely=0.05, anchor="nw")

        self.status_label = ctk.CTkLabel(self, text="Listo", text_color="gray", bg_color="#f8f9fa")
        self.status_label.place(relx=0.18, rely=0.05)

        # Panel inferior con bloques
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

        bt_icon = self.icons["Bluetooth"]
        self.bt_btn = ctk.CTkButton(self, image=bt_icon, text="", width=45, height=45,
                                    corner_radius=25, fg_color="#4cc9f0", hover_color="#3ab0de",
                                    command=self._toggle_bt_panel)
        self.bt_btn.place(relx=0.97, rely=0.05, anchor="ne")

        self.bt_panel = ctk.CTkFrame(self, width=320, fg_color="#e0f7fa", corner_radius=12)
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
        # --- Cambios solicitados: segundos entre 1 y 10, giros en 45/90/180/360 ---
        if action == "Velocidad":
            # escala 1..9 (como pediste antes) - interfaz muestra 1..9
            entry = ctk.CTkComboBox(frame, values=[str(i) for i in range(1, 10)], width=60)
            entry.set("5")
            entry.pack(side="left", padx=2)
        elif action in ["Adelante", "Reversa", "Esperar"]:
            # segundos 1..10
            entry = ctk.CTkComboBox(frame, values=[str(i) for i in range(1, 11)], width=60)
            entry.set("1")
            entry.pack(side="left", padx=2)
        elif action in ["Izquierda", "Derecha"]:
            # grados limitados a 45,90,180,360
            entry = ctk.CTkComboBox(frame, values=["45", "90", "180", "360"], width=80)
            entry.set("90")
            entry.pack(side="left", padx=2)

        btn_del = ctk.CTkButton(frame, text="✖", width=20, fg_color="#c62828", hover_color="#a71d2a",
                                command=lambda f=frame: self._delete_block(f))
        btn_del.pack(side="right", padx=2)

        idw = self.seq_area.create_window(x, y, window=frame)
        frame.bind("<B1-Motion>", lambda ev, fid=idw: self._drag_block(ev, fid))
        frame.bind("<ButtonRelease-1>", lambda ev, fid=idw: self._align_blocks())

        self.blocks.append({"id": idw, "frame": frame, "type": action, "param": entry})

    def _drag_block(self, event, window_id):
        dx, dy = event.x, event.y
        # move the window so the mouse stays near the top-left of the block while dragging
        self.seq_area.move(window_id, dx - 40, dy - 40)

    def _align_blocks(self):
        positions = [self.seq_area.bbox(b["id"]) for b in self.blocks]
        for i, b in enumerate(self.blocks):
            if not positions[i]:
                continue
            x1, y1, x2, y2 = positions[i]
            for j, b2 in enumerate(self.blocks):
                if i == j or not positions[j]:
                    continue
                x1b, y1b, x2b, y2b = positions[j]
                # si están cerca verticalmente y muy cerca horizontalmente, alinearlos en la misma fila
                if abs(y1 - y1b) < 40 and abs(x2 - x1b) < 60:
                    self.seq_area.move(b2["id"], x2 - x1b + 10, y1 - y1b)

    def _delete_block(self, frame):
        for b in list(self.blocks):
            if b["frame"] == frame:
                try:
                    self.seq_area.delete(b["id"])
                    b["frame"].destroy()
                except:
                    pass
                self.blocks.remove(b)
                break

    # ---------- EJECUCIÓN ----------
    def _run_sequence(self):
        if not self.blocks:
            self.status_label.configure(text="No hay bloques para ejecutar", text_color="orange")
            return

        sorted_blocks = sorted(self.blocks, key=lambda b: (self.seq_area.bbox(b["id"])[1], self.seq_area.bbox(b["id"])[0]))
        # por defecto velocidad 5 (escala 1–9)
        vel = 5
        # si el primer bloque es velocidad, se respetará en el orden natural; de todas formas el bloque "Velocidad"
        # ahora puede aparecer en cualquier parte — _execute_blocks lo detecta y actualiza la velocidad en tiempo de ejecución.
        self._execute_blocks(sorted_blocks, 0, vel)

    def _execute_blocks(self, blocks, index, vel):
        if index >= len(blocks):
            self.status_label.configure(text="✅ Secuencia completada", text_color="gray")
            self._send_bt("S")
            return

        blk = blocks[index]
        action = blk["type"]
        entry = blk["param"]

        # Si encontramos un bloque Velocidad en cualquier parte, actualizamos la velocidad y avanzamos
        if action == "Velocidad":
            try:
                vel = int(entry.get())
                if vel < 1: vel = 1
                if vel > 9: vel = 9
            except:
                vel = vel
            blk["frame"].configure(border_color="#ffb703", border_width=3)
            # mostrar destacado breve y continuar
            self.after(400, lambda: (
                blk["frame"].configure(border_color="#adb5bd", border_width=2),
                self._execute_blocks(blocks, index + 1, vel)
            ))
            return

        # obtener valor: segundos o grados (según el tipo)
        val = None
        if entry:
            try:
                val = float(entry.get())
            except:
                val = None

        total = len(blocks)
        self.status_label.configure(text=f"▶ Ejecutando {index+1}/{total}: {action}", text_color="blue")
        frame = blk["frame"]
        frame.configure(border_color="#0077b6", border_width=3)

        # Escalar velocidad (1–9 → 28–255) como pediste para enviar al Arduino
        vel_real = int((vel - 1) / 8 * 227 + 28)

        cmd = {"Adelante": "F", "Reversa": "B", "Izquierda": "L", "Derecha": "R", "Detener": "S"}.get(action, "S")
        # enviar comando con velocidad real
        self._send_bt(f"{cmd}{vel_real}")

        # calcular delay respetando las restricciones:
        # - Esperar/Adelante/Reversa: segundos entre 1 y 10 (selector)
        # - Izquierda/Derecha: grados (45,90,180,360) -> usamos la fórmula original: (deg / 90) * 1000 ms
        delay = 700
        if action == "Esperar":
            # val debe venir entre 1 y 10 (combo)
            try:
                v = int(val) if val is not None else 1
                if v < 1: v = 1
                if v > 10: v = 10
                delay = int(v * 1000)
            except:
                delay = 1000
        elif action in ["Adelante", "Reversa"]:
            try:
                v = int(val) if val is not None else 1
                if v < 1: v = 1
                if v > 10: v = 10
                delay = int(v * 1000)
            except:
                delay = 1000
        elif action in ["Izquierda", "Derecha"]:
            try:
                deg = int(val) if val is not None else 90
                if deg not in (45, 90, 180, 360):
                    deg = 90
                delay = int((deg / 90) * 1000)
            except:
                delay = 1000
        else:
            delay = 700

        # continuar al siguiente bloque después del delay (restaurar borde primero)
        self.after(delay, lambda: (
            frame.configure(border_color="#adb5bd", border_width=2),
            self._execute_blocks(blocks, index + 1, vel)
        ))

    # ---------- BLUETOOTH ----------
    def _build_bt_panel(self):
        ctk.CTkLabel(self.bt_panel, text="🔵 Bluetooth BLE / HC", font=("Arial Rounded MT Bold", 16),
                     text_color="#0077b6").pack(pady=10)
        self.btn_scan = ctk.CTkButton(self.bt_panel, text="🔍 Buscar BLE / HC", fg_color="#48cae4",
                                      hover_color="#00b4d8", command=self.scan_devices)
        self.btn_scan.pack(pady=5)
        self.frame_ports = ctk.CTkScrollableFrame(self.bt_panel, height=220)
        self.frame_ports.pack(fill="both", padx=10, pady=6)
        self.lbl_bt = ctk.CTkLabel(self.bt_panel, text="No conectado", text_color="red")
        self.lbl_bt.pack(pady=4)
        self.btn_disconnect = ctk.CTkButton(self.bt_panel, text="Desconectar", fg_color="#c62828",
                                            hover_color="#a71d2a", command=self.disconnect_bt, state="disabled")
        self.btn_disconnect.pack(pady=4)

    def _toggle_bt_panel(self):
        if self.bt_panel.winfo_ismapped():
            self.bt_panel.place_forget()
        else:
            self.bt_panel.place(relx=0.985, rely=0.13, anchor="ne")

    def scan_devices(self):
        # limpia y muestra mensaje
        for w in self.frame_ports.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.frame_ports, text="Buscando dispositivos BLE / HC ...", text_color="gray").pack()
        self.update()
        # usa asyncio.run para evitar tener que reestructurar el app
        asyncio.run(self._scan_ble_and_hc())

    async def _scan_ble_and_hc(self):
        for w in self.frame_ports.winfo_children():
            w.destroy()

        # BLE scan (Bleak)
        try:
            ble_devices = await BleakScanner.discover(timeout=5.0)
        except Exception as e:
            ble_devices = []
            print("Error escaneando BLE:", e)

        # puerto serie (HC-0x / HC-05 / HC-06) enumeración
        try:
            hc_ports = list(serial.tools.list_ports.comports())
        except Exception:
            hc_ports = []

        all_devices = []

        # agregar BLE (filtrando por nombre si existe) — mostramos cualquier BLE con nombre o sin él
        for d in ble_devices:
            # incluir si tiene nombre o su metadata sugiere HC/BLE
            all_devices.append(("BLE", d))

        # agregar HC serie si su descripción contiene 'HC' o 'LMB' (algunos adaptadores muestran LMB)
        for p in hc_ports:
            desc = (p.description or "").upper()
            name = (p.name or "")
            if "HC" in desc or "HC" in (p.device or "") or "LMB" in desc or "BLUETOOTH" in desc:
                all_devices.append(("HC", p))

        if not all_devices:
            ctk.CTkLabel(self.frame_ports, text="No se encontraron dispositivos").pack()
            return

        # mostrar lista
        for typ, dev in all_devices:
            fr = ctk.CTkFrame(self.frame_ports, fg_color="#caf0f8", corner_radius=6)
            fr.pack(fill="x", padx=4, pady=3)
            display_name = getattr(dev, "name", None) or getattr(dev, "description", None) or str(getattr(dev, "device", dev))
            txt = f"[{typ}] {display_name}"
            btn = ctk.CTkButton(fr, text=txt, fg_color="#00b4d8",
                                hover_color="#0096c7", command=lambda t=typ, d=dev: self._connect_device(t, d))
            btn.pack(fill="x", padx=5, pady=3)

    def _connect_device(self, typ, dev):
        # conectar a HC (serial) o BLE (Gatt)
        if typ == "HC":
            try:
                self.serial_port = serial.Serial(dev.device, 9600, timeout=1)
                self.lbl_bt.configure(text=f"Conectado a {dev.device}", text_color="green")
                self.bt_connected = True
                self.btn_disconnect.configure(state="normal")
                # limpiar cualquier cliente BLE previo
                self.bt_client = None
                self.bt_write_char = None
            except Exception as e:
                self.lbl_bt.configure(text=f"Error: {e}", text_color="red")
        else:
            # BLE device object from BleakScanner
            try:
                # crear BleakClient y conectar (sin bloquear UI gracias a asyncio.run)
                self.bt_client = BleakClient(dev)
                asyncio.run(self.bt_client.connect(timeout=10.0))
                # buscar una característica escribible (caché)
                self.bt_write_char = asyncio.run(self._find_write_characteristic(self.bt_client))
                self.bt_connected = True
                name = getattr(dev, "name", "BLE")
                self.lbl_bt.configure(text=f"Conectado a {name}", text_color="green")
                self.btn_disconnect.configure(state="normal")
                # cerrar serial si estaba abierta
                if self.serial_port:
                    try:
                        self.serial_port.close()
                        self.serial_port = None
                    except:
                        pass
            except Exception as e:
                self.lbl_bt.configure(text=f"Error BLE: {e}", text_color="red")
                self.bt_client = None
                self.bt_write_char = None

    async def _find_write_characteristic(self, client: BleakClient):
        """
        Busca la primera characteristic con permiso write o write_without_response.
        Devuelve UUID o None.
        """
        try:
            services = await client.get_services()
            for service in services:
                for char in service.characteristics:
                    props = char.properties or []
                    # buscar propiedades de escritura
                    if "write" in props or "write-without-response" in props:
                        return char.uuid
        except Exception as e:
            print("Error listing services:", e)
        return None

    def _send_bt(self, msg):
        """Envía msg + '\\n' al dispositivo conectado (serial HC o BLE GATT si tiene característica escribible)."""
        if not self.bt_connected:
            return
        try:
            if self.serial_port:
                # puerto serie clásico HC-05/06
                self.serial_port.write((msg + "\n").encode())
            elif self.bt_client and self.bt_client.is_connected:
                # BLE: intentar usar característica cacheada
                if self.bt_write_char:
                    try:
                        asyncio.run(self.bt_client.write_gatt_char(self.bt_write_char, (msg + "\n").encode()))
                    except Exception as e:
                        print("Error escribiendo BLE (cached char):", e)
                        # no hacemos más reintentos aquí
                else:
                    # intentar identificar una characteristic escribible en tiempo real
                    try:
                        char = asyncio.run(self._find_write_characteristic(self.bt_client))
                        if char:
                            self.bt_write_char = char
                            asyncio.run(self.bt_client.write_gatt_char(char, (msg + "\n").encode()))
                        else:
                            print("No se encontró characteristic escribible en el dispositivo BLE.")
                    except Exception as e:
                        print("Error escribiendo BLE:", e)
        except Exception as e:
            print("Error enviando:", e)

    def disconnect_bt(self):
        try:
            if self.serial_port:
                self.serial_port.close()
                self.serial_port = None
            if self.bt_client and self.bt_client.is_connected:
                asyncio.run(self.bt_client.disconnect())
                self.bt_client = None
                self.bt_write_char = None
        except:
            pass
        self.lbl_bt.configure(text="Desconectado", text_color="red")
        self.bt_connected = False
        self.btn_disconnect.configure(state="disabled")

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

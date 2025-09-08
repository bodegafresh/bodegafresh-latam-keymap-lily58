#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Keyboard Combo Inspector (XKB + evdev) para Debian/Linux
- Modo XKB (sin root): captura cuando la ventana tiene foco (Tkinter).
- Modo evdev (con root): captura global desde /dev/input (selecciona dispositivo).
Muestra: modifiers (Shift, Ctrl, Alt_L, Alt_R/AltGr), keysym/char y sugerencia QMK.

Uso:
  python3 keyboard_combo_inspector.py           # XKB por defecto
  sudo python3 keyboard_combo_inspector.py      # para usar evdev global
"""

import os
import sys
import threading
import queue
from dataclasses import dataclass
from typing import Optional, Dict

import tkinter as tk
from tkinter import ttk, messagebox

# evdev es opcional si no se usa el modo de dispositivo
try:
    from evdev import InputDevice, categorize, ecodes, list_devices
    HAVE_EVDEV = True
except Exception:
    HAVE_EVDEV = False

# --- Utilidades QMK simples (suficiente para letras/dígitos y varias teclas comunes) ---
BASE_KEYSYM_TO_QMK = {
    # Letras
    **{chr(c): f"KC_{chr(c).upper()}" for c in range(ord('a'), ord('z')+1)},
    **{chr(c).upper(): f"KC_{chr(c)}" for c in range(ord('A'), ord('Z')+1)},
    # Dígitos
    **{str(d): f"KC_{d}" for d in range(10)},
    # Símbolos "físicos" estándar (aprox. posición ANSI/ISO)
    "-": "KC_MINS", "=": "KC_EQL",
    "[": "KC_LBRC", "]": "KC_RBRC",
    "\\": "KC_BSLS",
    ";": "KC_SCLN", "'": "KC_QUOT",
    ",": "KC_COMM", ".": "KC_DOT", "/": "KC_SLSH",
    "`": "KC_GRV", " ": "KC_SPC",
}

# En layouts ES/LatAm, la tecla física de ';' suele producir 'ñ' en nivel base
EXTRA_CHAR_TO_QMK = {
    "ñ": "KC_SCLN", "Ñ": "S(KC_SCLN)",
    "¡": "S(KC_1)", "¿": "RALT(KC_SLASH)",  # puede variar por layout
}

def qmk_from_char_and_mods(base_char: Optional[str], shift: bool, ralt: bool) -> str:
    """
    Si tenemos el carácter base y los modificadores detectados, sugirió KC_*,
    envolviendo con S() y/o RALT().
    """
    kc = None
    if base_char:
        # directo por char
        kc = BASE_KEYSYM_TO_QMK.get(base_char)
        if not kc:
            kc = EXTRA_CHAR_TO_QMK.get(base_char)
        # fallback por mayúscula -> minúscula
        if not kc and len(base_char) == 1 and base_char.isalpha():
            kc = BASE_KEYSYM_TO_QMK.get(base_char.lower())
    if not kc:
        kc = "<KC_BASE_DESCONOCIDA>"  # avisa que debes ajustar a tu key física

    if shift and ralt:
        return f"S(RALT({kc}))"
    elif ralt:
        return f"RALT({kc})"
    elif shift:
        return f"S({kc})"
    else:
        return kc

# ---------------------- Modelo de estado ----------------------
@dataclass
class KeyEventInfo:
    source: str              # "XKB" o "evdev"
    key: str                 # keysym/char o código
    char: str                # carácter imprimible si aplica
    ctrl: bool
    shift: bool
    alt_l: bool
    alt_r: bool
    meta: bool
    super: bool
    comment: str             # texto auxiliar (p.ej., keycode/nombre evdev)

    @property
    def altgr(self) -> bool:
        # En Linux, AltGr suele ser Right Alt (Alt_R) o ISO_Level3_Shift.
        return self.alt_r

    @property
    def qmk_suggestion(self) -> str:
        # Para QMK, nos importa si hubo Shift/RightAlt y el "carácter base" si lo hubo.
        base_char = self.char if self.char else None
        return qmk_from_char_and_mods(base_char, self.shift, self.altgr)

# ---------------------- UI ----------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Keyboard Combo Inspector – XKB + evdev (QMK Helper)")
        self.geometry("820x600")
        self.minsize(820, 600)

        self.queue = queue.Queue()

        nb = ttk.Notebook(self)
        self.tab_xkb = ttk.Frame(nb)
        self.tab_evdev = ttk.Frame(nb)
        nb.add(self.tab_xkb, text="Modo XKB (sin root)")
        nb.add(self.tab_evdev, text="Modo evdev (global, root)")
        nb.pack(fill="both", expand=True)

        # --- Tab XKB ---
        self._build_xkb_tab()

        # --- Tab evdev ---
        self._build_evdev_tab()

        # Captura eventos Tk (XKB)
        self.bind_all("<KeyPress>", self.on_keypress_tk)
        self.bind_all("<KeyRelease>", self.on_keyrelease_tk)

        # refresco de cola (para evdev)
        self.after(30, self._drain_queue)

        # Estados de modificadores (XKB)
        self.tk_mods = {"Shift": False, "Control": False, "Alt_L": False, "Alt_R": False, "Meta": False, "Super": False}

    # --------- helpers ---------
    def _copy_log(self, text_widget: tk.Text):
        """Copia todo el contenido del Text al portapapeles."""
        try:
            data = text_widget.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(data)
            self.update()  # asegura que permanezca en clipboard
            messagebox.showinfo("Copiado", "Log copiado al portapapeles.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo copiar el log: {e}")

    # --------- XKB TAB ----------
    def _build_xkb_tab(self):
        f = self.tab_xkb

        info = tk.LabelFrame(f, text="Último evento (XKB / ventana con foco)")
        info.pack(fill="x", padx=10, pady=10)

        self.var_xkb_combo = tk.StringVar()
        self.var_xkb_key   = tk.StringVar()
        self.var_xkb_char  = tk.StringVar()
        self.var_xkb_qmk   = tk.StringVar()

        row = 0
        for label, var in [
            ("Combinación",   self.var_xkb_combo),
            ("Keysym / Key",  self.var_xkb_key),
            ("Carácter",      self.var_xkb_char),
            ("Sugerencia QMK",self.var_xkb_qmk),
        ]:
            ttk.Label(info, text=label + ":").grid(row=row, column=0, sticky="w", padx=8, pady=6)
            ttk.Entry(info, textvariable=var, width=80).grid(row=row, column=1, sticky="we", padx=8, pady=6)
            row += 1
        info.columnconfigure(1, weight=1)

        helpbox = tk.LabelFrame(f, text="Ayuda")
        helpbox.pack(fill="x", padx=10, pady=5)
        tk.Label(helpbox, justify="left", text=(
            "Pulsa una tecla o combinación con esta ventana enfocada.\n"
            "AltGr suele ser Right Alt (RALT). Si ves Alt_R, equivale a RALT en QMK.\n"
            "Para copiar la sugerencia QMK: selecciónala del campo y Ctrl+C.\n"
        )).pack(fill="x", padx=8, pady=6)

        # --- Log (XKB) + acciones ---
        logframe = tk.LabelFrame(f, text="Log (XKB)")
        logframe.pack(fill="both", expand=True, padx=10, pady=10)

        # barra de acciones
        toolbar = tk.Frame(logframe)
        toolbar.pack(fill="x", padx=5, pady=(6, 4))

        btn_copy_xkb = ttk.Button(toolbar, text="Copiar log",
                                  command=lambda: self._copy_log(self.txt_xkb_log))
        btn_copy_xkb.pack(side="left")

        # área de texto
        self.txt_xkb_log = tk.Text(logframe, height=12)
        self.txt_xkb_log.pack(fill="both", expand=True, padx=5, pady=(0,6))

        # limpiar
        btn_clear_xkb = ttk.Button(logframe, text="Limpiar log",
                                   command=lambda: self.txt_xkb_log.delete("1.0", "end"))
        btn_clear_xkb.pack(pady=5, anchor="e")

    def on_keypress_tk(self, event: tk.Event):
        # Nota: en Tk, event.state es un bitmask de modificadores; event.keysym es el nombre simbólico
        # event.char es el carácter imprimible (si lo hay)
        ks = event.keysym
        ch = event.char if event.char else ""
        # Actualiza flags (aproximado; Tk no siempre diferencia Alt_L vs Alt_R)
        if ks in ("Shift_L", "Shift_R"):
            self.tk_mods["Shift"] = True
        elif ks == "Control_L" or ks == "Control_R":
            pass
        elif ks == "Alt_L":
            self.tk_mods["Alt_L"] = True
        elif ks == "Alt_R" or ks == "ISO_Level3_Shift" or ks == "Mode_switch":
            self.tk_mods["Alt_R"] = True
        elif ks in ("Meta_L", "Meta_R"):
            self.tk_mods["Meta"] = True
        elif ks in ("Super_L", "Super_R"):
            self.tk_mods["Super"] = True

        # Construir combo humano
        mods = []
        if self.tk_mods["Shift"]: mods.append("Shift")
        if self.tk_mods["Alt_L"]: mods.append("Alt_L")
        if self.tk_mods["Alt_R"]: mods.append("Alt_R (AltGr)")
        if self.tk_mods["Meta"]:  mods.append("Meta")
        if self.tk_mods["Super"]: mods.append("Super")
        combo = "+".join(mods) if mods else "—"

        info = KeyEventInfo(
            source="XKB",
            key=ks,
            char=ch,
            ctrl=False,
            shift=self.tk_mods["Shift"],
            alt_l=self.tk_mods["Alt_L"],
            alt_r=self.tk_mods["Alt_R"],
            meta=self.tk_mods["Meta"],
            super=self.tk_mods["Super"],
            comment=f"Tk keysym={ks}, keycode={getattr(event, 'keycode', '')}"
        )
        self._update_xkb(info)

    def on_keyrelease_tk(self, event: tk.Event):
        ks = event.keysym
        if ks in ("Shift_L", "Shift_R"):
            self.tk_mods["Shift"] = False
        elif ks == "Alt_L":
            self.tk_mods["Alt_L"] = False
        elif ks == "Alt_R" or ks == "ISO_Level3_Shift" or ks == "Mode_switch":
            self.tk_mods["Alt_R"] = False
        elif ks in ("Meta_L", "Meta_R"):
            self.tk_mods["Meta"] = False
        elif ks in ("Super_L", "Super_R"):
            self.tk_mods["Super"] = False

    def _update_xkb(self, info: KeyEventInfo):
        # combo humano
        mods = []
        if info.shift: mods.append("Shift")
        if info.alt_l: mods.append("Alt_L")
        if info.alt_r: mods.append("Alt_R (AltGr)")
        if info.meta:  mods.append("Meta")
        if info.super: mods.append("Super")
        combo = "+".join(mods) if mods else "—"

        self.var_xkb_combo.set(combo)
        self.var_xkb_key.set(info.key)
        self.var_xkb_char.set(info.char if info.char else "—")
        self.var_xkb_qmk.set(info.qmk_suggestion)

        self.txt_xkb_log.insert("end", f"[XKB] {combo} | key={info.key} char='{info.char or ''}' | {info.qmk_suggestion}  ({info.comment})\n")
        self.txt_xkb_log.see("end")

    # --------- evdev TAB ----------
    def _build_evdev_tab(self):
        f = self.tab_evdev

        top = tk.Frame(f); top.pack(fill="x", padx=10, pady=10)
        self.btn_refresh = ttk.Button(top, text="Buscar dispositivos", command=self.refresh_devices)
        self.btn_refresh.pack(side="left")

        self.cmb_devices = ttk.Combobox(top, width=80, state="readonly")
        self.cmb_devices.pack(side="left", padx=10, fill="x", expand=True)

        self.btn_start = ttk.Button(top, text="Iniciar captura (root)", command=self.start_evdev_capture)
        self.btn_start.pack(side="left")

        info = tk.LabelFrame(f, text="Último evento (evdev / global)")
        info.pack(fill="x", padx=10, pady=10)

        self.var_ev_combo = tk.StringVar()
        self.var_ev_key   = tk.StringVar()
        self.var_ev_char  = tk.StringVar()
        self.var_ev_qmk   = tk.StringVar()

        row = 0
        for label, var in [
            ("Combinación",    self.var_ev_combo),
            ("Key (evdev)",    self.var_ev_key),
            ("Carácter",       self.var_ev_char),
            ("Sugerencia QMK", self.var_ev_qmk),
        ]:
            ttk.Label(info, text=label + ":").grid(row=row, column=0, sticky="w", padx=8, pady=6)
            ttk.Entry(info, textvariable=var, width=80).grid(row=row, column=1, sticky="we", padx=8, pady=6)
            row += 1
        info.columnconfigure(1, weight=1)

        # --- Log (evdev) + acciones ---
        logframe = tk.LabelFrame(f, text="Log (evdev)")
        logframe.pack(fill="both", expand=True, padx=10, pady=10)

        # barra de acciones
        toolbar_ev = tk.Frame(logframe)
        toolbar_ev.pack(fill="x", padx=5, pady=(6, 4))

        btn_copy_ev = ttk.Button(toolbar_ev, text="Copiar log",
                                 command=lambda: self._copy_log(self.txt_ev_log))
        btn_copy_ev.pack(side="left")

        # área de texto
        self.txt_ev_log = tk.Text(logframe, height=14)
        self.txt_ev_log.pack(fill="both", expand=True, padx=5, pady=(0,6))

        # limpiar
        btn_clear_ev = ttk.Button(logframe, text="Limpiar log",
                                  command=lambda: self.txt_ev_log.delete("1.0", "end"))
        btn_clear_ev.pack(pady=5, anchor="e")

        # Estado y ayuda
        self.ev_mods = {"Shift": False, "Ctrl": False, "Alt_L": False, "Alt_R": False, "Meta": False, "Super": False}
        self.ev_thread = None
        self.ev_stop = threading.Event()
        self.ev_dev_path = None

        hint = tk.Label(f, text="Sugerencia: el Microsoft Natural Ergonomic Keyboard suele aparecer como "
                                "'/dev/input/by-id/usb-Microsoft_*-event-kbd'", fg="#444")
        hint.pack(fill="x", padx=10)

        self.refresh_devices()

    def refresh_devices(self):
        if not HAVE_EVDEV:
            messagebox.showwarning("evdev no disponible", "python3-evdev no está instalado.")
            return
        paths = list_devices()
        names = []
        for p in paths:
            try:
                dev = InputDevice(p)
                names.append(f"{p}  —  {dev.name}")
                dev.close()
            except Exception:
                pass
        if not names:
            names = ["(No se encontraron dispositivos)"]
        self.cmb_devices["values"] = names
        if names:
            self.cmb_devices.current(0)

    def start_evdev_capture(self):
        if not HAVE_EVDEV:
            messagebox.showwarning("evdev no disponible", "Instala python3-evdev.")
            return
        val = self.cmb_devices.get()
        if not val or val.startswith("("):
            messagebox.showwarning("Sin dispositivo", "Selecciona un dispositivo válido.")
            return
        self.ev_dev_path = val.split("  —  ")[0].strip()
        # avisos de permisos
        if not os.access(self.ev_dev_path, os.R_OK):
            messagebox.showinfo("Permisos", "Necesitas permisos para leer el dispositivo. Ejecuta con sudo.")
            return
        # arrancar hilo
        if self.ev_thread and self.ev_thread.is_alive():
            messagebox.showinfo("Captura", "Ya hay una captura en curso.")
            return
        self.ev_stop.clear()
        self.ev_thread = threading.Thread(target=self._evdev_loop, daemon=True)
        self.ev_thread.start()
        self.txt_ev_log.insert("end", f"[evdev] Captura iniciada en {self.ev_dev_path}\n"); self.txt_ev_log.see("end")

    def _evdev_loop(self):
        try:
            dev = InputDevice(self.ev_dev_path)
            for event in dev.read_loop():
                if self.ev_stop.is_set():
                    break
                if event.type == ecodes.EV_KEY:
                    data = categorize(event)
                    keycode = data.scancode
                    keyname = ecodes.KEY[keycode] if keycode in ecodes.KEY else str(keycode)
                    pressed = (data.keystate == data.key_down)
                    released = (data.keystate == data.key_up)

                    # actualiza modificadores
                    if keyname in ("KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"):
                        self.ev_mods["Shift"] = pressed or (not released and self.ev_mods["Shift"])
                    elif keyname in ("KEY_LEFTALT",):
                        self.ev_mods["Alt_L"] = pressed or (not released and self.ev_mods["Alt_L"])
                    elif keyname in ("KEY_RIGHTALT",):
                        self.ev_mods["Alt_R"] = pressed or (not released and self.ev_mods["Alt_R"])
                    elif keyname in ("KEY_LEFTCTRL","KEY_RIGHTCTRL"):
                        self.ev_mods["Ctrl"] = pressed or (not released and self.ev_mods["Ctrl"])
                    elif keyname in ("KEY_LEFTMETA","KEY_RIGHTMETA"):
                        self.ev_mods["Super"] = pressed or (not released and self.ev_mods["Super"])

                    # char no es trivial en evdev (no hay mapeo a símbolo aquí)
                    char = ""

                    # cuando hay "key_down" de una tecla no-modifier, mostramos
                    if pressed and not keyname.startswith(("KEY_LEFT", "KEY_RIGHT")):
                        info = KeyEventInfo(
                            source="evdev",
                            key=keyname,
                            char=char,
                            ctrl=self.ev_mods["Ctrl"],
                            shift=self.ev_mods["Shift"],
                            alt_l=self.ev_mods["Alt_L"],
                            alt_r=self.ev_mods["Alt_R"],
                            meta=False,
                            super=self.ev_mods["Super"],
                            comment=f"scancode={keycode}"
                        )
                        self.queue.put(info)
        except Exception as e:
            self.queue.put(f"[evdev] Error: {e}")

    def _drain_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                if isinstance(item, KeyEventInfo):
                    self._update_evdev(item)
                else:
                    self.txt_ev_log.insert("end", str(item) + "\n"); self.txt_ev_log.see("end")
        except queue.Empty:
            pass
        self.after(30, self._drain_queue)

    def _update_evdev(self, info: KeyEventInfo):
        mods = []
        if info.shift: mods.append("Shift")
        if info.alt_l: mods.append("Alt_L")
        if info.alt_r: mods.append("Alt_R (AltGr)")
        if info.super: mods.append("Super")
        if info.ctrl:  mods.append("Ctrl")
        combo = "+".join(mods) if mods else "—"

        # En evdev no tenemos 'char' directamente. Para sugerencia QMK, usamos KC desconocido.
        qmk = qmk_from_char_and_mods(info.char or None, info.shift, info.altgr)

        self.var_ev_combo.set(combo)
        self.var_ev_key.set(f"{info.key} ({info.comment})")
        self.var_ev_char.set("—")
        self.var_ev_qmk.set(qmk)

        self.txt_ev_log.insert("end", f"[evdev] {combo} | {info.key} | {qmk}\n")
        self.txt_ev_log.see("end")


if __name__ == "__main__":
    app = App()
    app.mainloop()

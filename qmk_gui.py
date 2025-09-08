#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QMK Helper GUI for Debian/Linux (pretty log edition)
- Limpia códigos ANSI para que no aparezcan \x1b[32m, etc.
- Resalta líneas importantes (OK, errores, warnings, pasos y comandos).
"""

import os
import re
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

DEFAULT_PATH = "/home/bodegafresh/git/qmk_firmware/keyboards/lily58/keymaps/bodegafresh_latam"
DEFAULT_KB = "lily58"
DEFAULT_KM = "bodegafresh_latam"

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE.sub('', text)

class ProcessRunner:
    def __init__(self, output_callback):
        self.proc = None
        self.output_callback = output_callback
        self._stop_event = threading.Event()

    def run(self, cmd, cwd=None, on_done=None):
        """Run a command in a background thread and stream stdout/stderr."""
        def target():
            try:
                self.output_callback("$ " + " ".join(cmd) + "\n", tag="cmd")
                self.proc = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )
                for raw in self.proc.stdout:
                    if self._stop_event.is_set():
                        break
                    line = strip_ansi(raw.rstrip('\n'))
                    # classify
                    lower = line.lower()
                    tag = None
                    if ("error" in lower) or ("failed" in lower) or ("terminó con código" in lower):
                        tag = "error"
                    elif ("warning" in lower) or ("advertencia" in lower):
                        tag = "warn"
                    elif ("[ok]" in lower) or ("finalizado correctamente" in lower) or ("success" in lower):
                        tag = "ok"
                    elif (line.startswith("Compiling") or line.startswith("Linking") or
                          line.startswith("Checking") or line.startswith("Creating") or
                          line.startswith("Copying")):
                        tag = "step"
                    self.output_callback(line + "\n", tag=tag)
                ret = self.proc.wait()
                if ret == 0:
                    self.output_callback("\nComando finalizado correctamente.\n", tag="ok")
                else:
                    self.output_callback(f"\nEl comando terminó con código {ret}.\n", tag="error")
                if on_done:
                    on_done(ret)
            except FileNotFoundError:
                self.output_callback("No se encontró el comando solicitado.\n", tag="error")
                self.output_callback("Asegúrate de tener QMK instalado (p. ej. pipx install qmk)\n")
                if on_done:
                    on_done(127)
            except Exception as e:
                self.output_callback(f"Error ejecutando comando: {e}\n", tag="error")
                if on_done:
                    on_done(1)
        threading.Thread(target=target, daemon=True).start()

    def stop(self):
        self._stop_event.set()
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

class QMKGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QMK Helper · Lily58")
        self.geometry("900x560")
        self.minsize(820, 480)
        self.configure(bg="#0b0f14")

        # Style
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except:
            pass
        style.configure("TLabel", foreground="#e6edf3", background="#0b0f14")
        style.configure("TButton", padding=8)
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Path.TEntry", fieldbackground="#141a21", foreground="#e6edf3")
        style.configure("Log.TFrame", background="#0b0f14")
        style.configure("Controls.TFrame", background="#0b0f14")

        self.runner = ProcessRunner(self.append_log)

        # Top controls frame
        controls = ttk.Frame(self, style="Controls.TFrame")
        controls.pack(side=tk.TOP, fill=tk.X, padx=16, pady=(16, 8))

        ttk.Label(controls, text="QMK Helper (Debian)", style="Header.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8), columnspan=6)

        ttk.Label(controls, text="Ruta de trabajo:").grid(row=1, column=0, sticky="w")
        self.path_var = tk.StringVar(value=DEFAULT_PATH)
        self.path_entry = ttk.Entry(controls, textvariable=self.path_var, width=70, style="Path.TEntry")
        self.path_entry.grid(row=1, column=1, columnspan=4, sticky="we", padx=6)
        ttk.Button(controls, text="Elegir…", command=self.choose_path).grid(row=1, column=5, sticky="we")

        ttk.Label(controls, text="Keyboard (-kb):").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.kb_var = tk.StringVar(value=DEFAULT_KB)
        ttk.Entry(controls, textvariable=self.kb_var, width=18).grid(row=2, column=1, sticky="w", pady=(8, 0))

        ttk.Label(controls, text="Keymap (-km):").grid(row=2, column=2, sticky="w", pady=(8, 0))
        self.km_var = tk.StringVar(value=DEFAULT_KM)
        ttk.Entry(controls, textvariable=self.km_var, width=28).grid(row=2, column=3, sticky="w", pady=(8, 0))

        ttk.Button(controls, text="Limpiar", command=self.on_clean).grid(row=2, column=4, sticky="we", padx=(12, 0), pady=(8,0))
        ttk.Button(controls, text="Compilar", command=self.on_compile).grid(row=2, column=5, sticky="we", pady=(8,0))

        ttk.Button(controls, text="Copiar Log", command=self.copy_log).grid(row=3, column=4, sticky="we", padx=(12, 0), pady=(8,0))
        self.flash_btn = ttk.Button(controls, text="Flashear", command=self.on_flash)
        self.flash_btn.grid(row=3, column=5, sticky="we", pady=(8, 0))

        for i in range(6):
            controls.columnconfigure(i, weight=1)

        # Log frame
        log_frame = ttk.Frame(self, style="Log.TFrame")
        log_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=16, pady=(8, 16))

        # Use a fixed-width font for logs
        try:
            fixed_font = ("JetBrains Mono", 10)
        except:
            fixed_font = ("TkFixedFont", 10)

        self.log = tk.Text(
            log_frame,
            wrap="none",
            background="#0d1117",
            foreground="#e6edf3",
            insertbackground="#e6edf3",
            height=20,
            padx=10,
            pady=10,
            bd=0,
            font=fixed_font
        )
        self.log_scroll_y = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log_scroll_x = ttk.Scrollbar(log_frame, orient="horizontal", command=self.log.xview)
        self.log.configure(yscrollcommand=self.log_scroll_y.set, xscrollcommand=self.log_scroll_x.set)
        self.log.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.log_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Define tags (colors)
        self.log.tag_config("cmd", foreground="#7aa2f7")     # azul
        self.log.tag_config("step", foreground="#89ddff")    # cyan
        self.log.tag_config("ok", foreground="#9ece6a")      # verde
        self.log.tag_config("warn", foreground="#e0af68")    # amarillo
        self.log.tag_config("error", foreground="#f7768e")   # rojo

        self.append_log("👋 Bienvenido. Este panel ejecuta comandos QMK con salida en vivo.\n")
        self.append_log("Sugerencia: primero 'Compilar'. Si sale OK, el botón 'Flashear' funcionará.\n\n")

        hints = ("Consejos para flashear Lily58:\n"
                 "1) Presiona el botón RESET o usa una combinación en el teclado para entrar en bootloader.\n"
                 "2) Conecta solo la mitad que vas a flashear.\n"
                 "3) Si pierdes 'Enter', usa este botón 'Flashear' (no necesitas presionar Enter).\n")
        self.append_log(hints + "\n")

        self.flash_enabled = False
        self.update_flash_state(False)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # -------- UI helpers --------
    def append_log(self, text, tag=None):
        # ensure clean text
        clean = strip_ansi(text)
        if tag:
            self.log.insert(tk.END, clean, tag)
        else:
            self.log.insert(tk.END, clean)
        self.log.see(tk.END)

    def choose_path(self):
        path = filedialog.askdirectory(initialdir=self.path_var.get() or str(Path.home()))
        if path:
            self.path_var.set(path)

    def copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self.log.get("1.0", tk.END))
        messagebox.showinfo("Copiado", "El log se copió al portapapeles.")

    def update_flash_state(self, enabled: bool):
        self.flash_enabled = enabled
        try:
            self.flash_btn.state(["!disabled"] if enabled else ["disabled"])
        except Exception:
            pass

    # -------- Command handlers --------
    def validate_path(self):
        path = self.path_var.get().strip()
        if not path:
            messagebox.showerror("Ruta vacía", "Debes especificar la ruta de trabajo.")
            return None
        if not os.path.isdir(path):
            messagebox.showerror("Ruta inválida", f"La ruta no existe:\n{path}")
            return None
        return path

    def on_clean(self):
        path = self.validate_path()
        if not path:
            return
        if not messagebox.askokcancel("Confirmar limpieza", "Se ejecutará: qmk clean\n¿Continuar?"):
            return
        self.append_log("Limpiando build...\n", tag="step")
        self.runner.run(["qmk", "clean"], cwd=path)

    def on_compile(self):
        path = self.validate_path()
        if not path:
            return
        kb = self.kb_var.get().strip() or DEFAULT_KB
        km = self.km_var.get().strip() or DEFAULT_KM

        if not messagebox.askokcancel("Confirmar compilación", f"Se ejecutará:\nqmk compile -kb {kb} -km {km}\n¿Continuar?"):
            return

        self.append_log("Compilando…\n", tag="step")
        def done(ret):
            if ret == 0:
                self.update_flash_state(True)
                self.after(0, lambda: self.ask_flash_now())
            else:
                self.update_flash_state(False)
                self.after(0, lambda: messagebox.showerror("Compilación fallida", "Revisa el log para ver los errores."))

        self.runner.run(["qmk", "compile", "-kb", kb, "-km", km], cwd=path, on_done=done)

    def ask_flash_now(self):
        if messagebox.askyesno("Compilación OK", "✅ Compilación exitosa.\n\n¿Quieres flashear ahora?"):
            self.on_flash()

    def on_flash(self):
        if not self.flash_enabled:
            if not messagebox.askyesno("Flashear sin compilar", "Aún no hay una compilación exitosa en esta sesión.\n¿Deseas flashear de todas maneras?"):
                return

        path = self.validate_path()
        if not path:
            return
        kb = self.kb_var.get().strip() or DEFAULT_KB
        km = self.km_var.get().strip() or DEFAULT_KM

        proceed = messagebox.askokcancel(
            "Listo para flashear",
            "Conecta SOLO la mitad que vas a flashear y ponla en modo bootloader (RESET).\n\n"
            f"Se ejecutará:\nqmk flash -kb {kb} -km {km}\n\n¿Continuar?"
        )
        if not proceed:
            return

        self.append_log("Flasheando…\n", tag="step")
        def done(ret):
            if ret == 0:
                self.after(0, lambda: messagebox.showinfo("Flasheo completado", "🎉 Firmware flasheado correctamente."))
            else:
                self.after(0, lambda: messagebox.showerror("Flasheo fallido", "Revisa el log para ver los errores."))
        self.runner.run(["qmk", "flash", "-kb", kb, "-km", km], cwd=path, on_done=done)

    def on_close(self):
        try:
            self.runner.stop()
        finally:
            self.destroy()

def main():
    app = QMKGUI()
    app.mainloop()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kbmap_programming_keys.py
Lista letras (incluida ñ), dígitos y símbolos típicos de programación con su combinación de teclas
según el layout ACTUAL en Debian (X11/XWayland).

Uso:
  python3 kbmap_programming_keys.py
Opcional:
  --csv        # salida CSV
  --md         # salida Markdown
  --all        # imprime también teclas que no se encuentran (para diagnosticar)
"""

import os
import re
import sys
import shlex
import subprocess
from collections import defaultdict

WANTED_CHARS = (
    # Letras (minúsculas) y ñ
    list("abcdefghijklmnopqrstuvwxyz") + ["ñ"] +
    # Dígitos
    list("0123456789") +
    # Símbolos comunes en programación
    list(r"""[]{}()<>/\|~^`@#$%&*+-_=;:,"'!?.""") +
    # Extras de ES/LatAm muy usados
    ["¿", "¡", "°", "¬"]
)

# Mapeo de keysyms -> carácter visible
KEYSYM_TO_CHAR = {
    # Puntuación y paréntesis
    "parenleft":"(", "parenright":")",
    "bracketleft":"[", "bracketright":"]",
    "braceleft":"{", "braceright":"}",
    "less":"<", "greater":">",
    "slash":"/", "backslash":"\\",
    "bar":"|", "asciitilde":"~",
    "asciicircum":"^", "grave":"`",
    "at":"@", "numbersign":"#", "dollar":"$",
    "percent":"%", "ampersand":"&", "asterisk":"*",
    "minus":"-", "underscore":"_",
    "equal":"=", "plus":"+",
    "semicolon":";", "colon":":",
    "quotedbl":"\"", "apostrophe":"'",
    "comma":",", "period":".",
    "question":"?", "exclam":"!",
    "exclamdown":"¡", "questiondown":"¿",
    "degree":"°", "notsign":"¬",
    # Letras con tilde/ñ
    "ntilde":"ñ", "Ntilde":"Ñ",
    # Espacio
    "space":" ",
}

# Dead keys: las marcamos explícitas
DEAD_PREFIX = "dead_"

def run(cmd):
    try:
        out = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="replace")
    except Exception:
        return ""

def detect_layouts():
    info = {}
    # setxkbmap (X11/XWayland)
    q = run("setxkbmap -query")
    for line in q.splitlines():
        if ":" in line:
            k,v = [s.strip() for s in line.split(":",1)]
            info[f"xkb_{k.lower()}"] = v
    # localectl (system-wide)
    l = run("localectl status")
    for line in l.splitlines():
        if "X11 Layout" in line:
            info["localectl_layout"] = line.split(":",1)[1].strip()
        if "X11 Variant" in line:
            info["localectl_variant"] = line.split(":",1)[1].strip()
    return info

def parse_modifiers_pm():
    """Devuelve el nombre del modificador que contiene ISO_Level3_Shift (AltGr)."""
    pm = run("xmodmap -pm")
    altgr_mod = None
    for line in pm.splitlines():
        # Ej: mod5        ISO_Level3_Shift (0x42), Mode_switch (0xcb)
        if line.startswith("mod"):
            if "ISO_Level3_Shift" in line or "Mode_switch" in line:
                altgr_mod = line.split()[0]  # mod5, p.ej.
                break
    return altgr_mod or "mod5"

def parse_pke():
    """
    Parsea 'xmodmap -pke' -> { keycode: [lvl1, lvl2, lvl3, lvl4] }
    lvl1: sin modificador
    lvl2: Shift
    lvl3: AltGr (ISO_Level3_Shift)
    lvl4: Shift+AltGr
    """
    pke = run("xmodmap -pke")
    keymap = {}
    pat = re.compile(r"^keycode\s+(\d+)\s+=\s+(.*)$")
    for line in pke.splitlines():
        m = pat.match(line.strip())
        if not m:
            continue
        code = int(m.group(1))
        # tokens separados por espacios, pero algunos 'NoSymbol'
        syms = [t for t in m.group(2).split() if t]
        # normalizamos a 4 niveles
        while len(syms) < 4:
            syms.append("NoSymbol")
        keymap[code] = syms[:4]
    return keymap

def keysym_to_char(sym):
    """Convierte keysym a carácter si se puede, sino intenta interpretar literal."""
    if sym.startswith(DEAD_PREFIX):
        return sym  # lo mostramos como dead_*
    if sym in KEYSYM_TO_CHAR:
        return KEYSYM_TO_CHAR[sym]
    # keysym es ya un carácter ascii visible? (rara vez aquí)
    if len(sym) == 1:
        return sym
    # letras comunes: a/A, ntilde/Ntilde ya mapeadas
    if len(sym) == 1 and sym.isalpha():
        return sym
    # Algunos layouts ponen directamente el carácter
    if len(sym) == 1:
        return sym
    return None

def normalize_char(c):
    """Para comparar: pasamos todo a str exacto."""
    return c

def prefer_key_label(level_syms):
    """
    Devuelve una etiqueta 'Tecla' amigable para esa fila:
    - si nivel 1 es dígito/letra/símbolo simple, úsalo
    - si no, usa el primer símbolo visible de cualquier nivel
    - en último caso, 'keycode N'
    """
    for i in [0,1,2,3]:
        sym = level_syms[i]
        ch = keysym_to_char(sym)
        if ch and not ch.startswith(DEAD_PREFIX):
            if len(ch) == 1 and (ch.isalnum() or ch in r"-_=+[]{}()<>/\\|;:'\",.#!?@^~`%$&*°¬¿¡ "):
                return ch
    # si no, intentamos una representación texto del lvl1
    return keysym_to_char(level_syms[0]) or level_syms[0]

def find_char_positions(keymap):
    """
    Invertimos: caracter -> lista de (keycode, level, sym)
    level: 0,1,2,3  ->  NoMod, Shift, AltGr, Shift+AltGr
    """
    positions = defaultdict(list)
    for code, syms in keymap.items():
        for lvl, sym in enumerate(syms):
            if sym == "NoSymbol":
                continue
            ch = keysym_to_char(sym)
            if not ch:
                continue
            # Si es 'dead_*' no lo consideramos como carácter final normal
            if ch.startswith(DEAD_PREFIX):
                continue
            positions[ch].append((code, lvl, sym, tuple(syms)))
    return positions

def lvl_to_combo(lvl):
    return {
        0: "",
        1: "Shift+",
        2: "AltGr+",
        3: "Shift+AltGr+"
    }.get(lvl, "")

def out_table(rows, mode="plain"):
    headers = ["Carácter", "Tecla", "Combinación", "Keysym", "Ejemplo"]
    if mode == "csv":
        import csv, io
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)
        print(buf.getvalue(), end="")
    elif mode == "md":
        # Markdown
        print("| " + " | ".join(headers) + " |")
        print("|" + "|".join(["---"]*len(headers)) + "|")
        for r in rows:
            print("| " + " | ".join(r) + " |")
    else:
        # tabla monoespaciada simple
        widths = [max(len(h), *(len(r[i]) for r in rows)) for i,h in enumerate(headers)]
        fmt = "  ".join("{:<" + str(w) + "}" for w in widths)
        print(fmt.format(*headers))
        print(fmt.format(*["-"*w for w in widths]))
        for r in rows:
            print(fmt.format(*r))

def main():
    mode = "plain"
    show_missing = False
    if "--csv" in sys.argv:
        mode = "csv"
    if "--md" in sys.argv:
        mode = "md"
    if "--all" in sys.argv:
        show_missing = True

    if not os.environ.get("DISPLAY"):
        print("⚠️  No se detecta DISPLAY. Estás en Wayland puro o TTY.")
        print("    Repite desde una sesión X11/XWayland (KDE/GNOME) o habilita XWayland.")
        print("    Tip: en GNOME/KDE suele estar activo por defecto.")
        sys.exit(1)

    layout_info = detect_layouts()
    altgr_mod = parse_modifiers_pm()
    keymap = parse_pke()
    if not keymap:
        print("⚠️  No pude leer el mapa de teclas con 'xmodmap -pke'.")
        print("    Asegúrate de estar en X11/XWayland y tener x11-utils instalado.")
        sys.exit(1)

    positions = find_char_positions(keymap)

    # Encabezado informativo
    lay = layout_info.get("xkb_layout", layout_info.get("localectl_layout", "desconocido"))
    var = layout_info.get("xkb_variant", layout_info.get("localectl_variant", ""))
    model = layout_info.get("xkb_model", "")
    print(f"Distribución detectada: layout='{lay}' variant='{var}' model='{model}'  (AltGr -> {altgr_mod})\n")

    rows = []
    for want in WANTED_CHARS:
        found = positions.get(want)
        if not found:
            if show_missing:
                rows.append([want, "—", "—", "—", "No hallado en este layout"])
            continue
        # elige la opción con menor nivel (prioriza sin/Shift frente a AltGr)
        found_sorted = sorted(found, key=lambda t: t[1])
        code, lvl, sym, full_syms = found_sorted[0]
        combo = lvl_to_combo(lvl)
        key_label = str(prefer_key_label(full_syms))
        # Construye explicación de ejemplo
        example = f"{combo}Tecla({key_label})"
        rows.append([want, key_label, combo[:-1] if combo else "—", sym, example])

    if not rows:
        print("No se encontraron caracteres objetivo. ¿Layout muy exótico? Prueba con --all para diagnóstico.")
        sys.exit(2)

    out_table(rows, mode=mode)

    # Sugerencias útiles
    print("\nSugerencias:")
    print("  - Para ver todo el mapa crudo: xmodmap -pke")
    print("  - Ver modificadores: xmodmap -pm    (AltGr suele ser ISO_Level3_Shift → mod5)")
    print("  - Confirmar layout en uso: setxkbmap -query   o   localectl status")
    print("  - Si alguna tecla sale como dead_* (tildes), combínala con espacio para producir el carácter.")

if __name__ == "__main__":
    main()

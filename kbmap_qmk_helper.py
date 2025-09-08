#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kbmap_qmk_helper.py
Muestra letras (incluida ñ), dígitos y símbolos de programación con:
- Combinación humana (Shift/AltGr)
- keysym real
- Sugerencia QMK: KC_*, S(KC_*), RALT(KC_*), S(RALT(KC_*))

Requisitos: x11-utils, xkb-data (X11/XWayland).
Uso:
  python3 kbmap_qmk_helper.py            # tabla legible
  python3 kbmap_qmk_helper.py --md       # Markdown
  python3 kbmap_qmk_helper.py --csv      # CSV
"""

import os, re, sys, shlex, subprocess
from collections import defaultdict

# ---------- Objetivo: lo que queremos resolver en QMK ----------
WANTED_CHARS = (
    list("abcdefghijklmnopqrstuvwxyz") + ["ñ"] +
    list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["Ñ"] +
    list("0123456789") +
    list(r"""[]{}()<>/\|~^`@#$%&*+-_=;:,"'!?.""") +
    ["¿", "¡", "°", "¬", "´"]  +
    ["@", "`", "ñ", "Ñ"]
)

# ---------- Utilidades ----------
def run(cmd):
    try:
        out = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="replace")
    except Exception:
        return ""

DEAD_PREFIX = "dead_"

# keysym -> carácter visible (cuando X ya entrega nombres “especiales”)
KEYSYM_TO_CHAR = {
    "parenleft":"(", "parenright":")",
    "bracketleft":"[", "bracketright":"]",
    "braceleft":"{", "braceright":"}",
    "less":"<", "greater":">",
    "slash":"/", "backslash":"\\", "bar":"|",
    "asciitilde":"~", "asciicircum":"^", "grave":"`",
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
    "space":" ",
    "ntilde":"ñ", "Ntilde":"Ñ",
    "dead_grave": "`",   # backtick como carácter directo
    "dead_acute": "´",   # opcional, para acento agudo
    "dead_tilde": "~",   # opcional
}

# keysym nivel0 -> código QMK base (tecla física “KC_*”)
# Nota: esto sirve para formular RALT(KC_*), S(KC_*), etc.
BASE_KEYSYM_TO_QMK = {
    # letras
    **{c: f"KC_{c.upper()}" for c in "abcdefghijklmnopqrstuvwxyz"},
    "ntilde": "KC_SCLN",  # en ES/LatAm usualmente la física de ';' produce ñ en nivel0
    # dígitos (fila numérica)
    **{str(d): f"KC_{d}" for d in range(10)},
    # signos base típicos en nivel0 según ISO/US (puede variar por layout, pero se usa como aproximación física)
    "minus": "KC_MINS",
    "equal": "KC_EQL",
    "bracketleft": "KC_LBRC",
    "bracketright": "KC_RBRC",
    "backslash": "KC_BSLS",
    "slash": "KC_SLSH",
    "semicolon": "KC_SCLN",
    "apostrophe": "KC_QUOT",
    "comma": "KC_COMM",
    "period": "KC_DOT",
    "grave": "KC_GRV",      # `  (backtick)
    "space": "KC_SPC",
}

def keysym_to_char(sym):
    if sym.startswith(DEAD_PREFIX):
        return sym
    if sym in KEYSYM_TO_CHAR:
        return KEYSYM_TO_CHAR[sym]
    # letras/dígitos sencillos
    if len(sym) == 1:
        return sym
    return None

def parse_xmodmap_pke():
    pke = run("xmodmap -pke")
    pat = re.compile(r"^keycode\s+(\d+)\s+=\s+(.*)$")
    keymap = {}
    for line in pke.splitlines():
        m = pat.match(line.strip())
        if not m:
            continue
        code = int(m.group(1))
        syms = [t for t in m.group(2).split() if t]
        while len(syms) < 4:
            syms.append("NoSymbol")
        keymap[code] = syms[:4]
    return keymap

def level_to_combo(lvl):
    return {0:"", 1:"Shift+", 2:"AltGr+", 3:"Shift+AltGr+"}.get(lvl, "")

def prefer_key_label(level_syms):
    for i in [0,1,2,3]:
        sym = level_syms[i]
        ch = keysym_to_char(sym)
        if ch and not ch.startswith(DEAD_PREFIX):
            return ch
    return keysym_to_char(level_syms[0]) or level_syms[0]

def build_positions(keymap):
    pos = defaultdict(list)  # char -> [(code, lvl, keysym, level_syms)]
    for code, syms in keymap.items():
        for lvl, sym in enumerate(syms):
            if sym == "NoSymbol":
                continue
            ch = keysym_to_char(sym)
            if not ch or ch.startswith(DEAD_PREFIX):
                continue
            pos[ch].append((code, lvl, sym, tuple(syms)))
    return pos

def qmk_combo_for(code_entry):
    """Devuelve (combo_humano, keysym, qmk_suggestion)"""
    code, lvl, sym, level_syms = code_entry
    combo_humano = level_to_combo(lvl)  # "", "Shift+", "AltGr+", "Shift+AltGr+"
    # El QMK debe pulsar la TECLA FÍSICA base y añadir Shift/RAlt según el nivel.
    base_keysym = level_syms[0] if level_syms[0] != "NoSymbol" else sym
    qmk_base = None

    # Si es letra/dígito simple en nivel0, mapeo directo:
    if len(base_keysym) == 1 and base_keysym.isalpha():
        qmk_base = f"KC_{base_keysym.upper()}"
    elif len(base_keysym) == 1 and base_keysym.isdigit():
        qmk_base = f"KC_{base_keysym}"
    else:
        # usar diccionario base (incluye ñ como KC_SCLN y símbolos base comunes)
        qmk_base = BASE_KEYSYM_TO_QMK.get(base_keysym)

    # Fallback: si no sabemos el KC_ físico, avisamos:
    if not qmk_base:
        # última chance: si la “tecla amigable” luce como letra/dígito/símbolo con KC_ conocido
        key_label = prefer_key_label(level_syms)
        if len(key_label) == 1 and key_label.isalpha():
            qmk_base = f"KC_{key_label.upper()}"
        elif len(key_label) == 1 and key_label.isdigit():
            qmk_base = f"KC_{key_label}"
        else:
            # Desconocida: devolvemos un marcador para que el usuario ajuste
            qmk_base = f"<KC_BASE_DESCONOCIDA:keysym={base_keysym}>"

    # Apilar modificadores según el nivel
    if lvl == 0:
        qmk = qmk_base
    elif lvl == 1:
        qmk = f"S({qmk_base})"
    elif lvl == 2:
        qmk = f"RALT({qmk_base})"
    else:  # lvl == 3
        qmk = f"S(RALT({qmk_base}))"

    return combo_humano, sym, qmk

def render(rows, mode="plain"):
    headers = ["Carácter", "Combinación", "Keysym", "QMK sugerido", "Tecla"]
    if mode == "md":
        print("| " + " | ".join(headers) + " |")
        print("|" + "|".join(["---"]*len(headers)) + "|")
        for r in rows: print("| " + " | ".join(r) + " |")
        return
    if mode == "csv":
        import csv, io
        buf = io.StringIO()
        w = csv.writer(buf); w.writerow(headers)
        for r in rows: w.writerow(r)
        print(buf.getvalue(), end=""); return
    # plain
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i,h in enumerate(headers)]
    fmt = "  ".join("{:<" + str(w) + "}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-"*w for w in widths]))
    for r in rows: print(fmt.format(*r))

def main():
    mode = "plain"
    if "--md" in sys.argv: mode = "md"
    if "--csv" in sys.argv: mode = "csv"

    if not os.environ.get("DISPLAY"):
        print("⚠️  No DISPLAY. Ejecuta en una sesión X11/XWayland (KDE/GNOME)."); sys.exit(1)

    keymap = parse_xmodmap_pke()
    if not keymap:
        print("⚠️  No pude leer 'xmodmap -pke'. Asegura X11/XWayland y x11-utils."); sys.exit(1)

    positions = build_positions(keymap)
    rows = []
    for c in WANTED_CHARS:
        found = positions.get(c)
        if not found:
            continue
        # Elige el nivel “más simple”: sin mods > Shift > AltGr > Shift+AltGr
        found.sort(key=lambda t: t[1])
        combo_hum, keysym, qmk = qmk_combo_for(found[0])
        key_label = prefer_key_label(found[0][3])
        rows.append([c, combo_hum[:-1] if combo_hum else "—", keysym, qmk, f"{key_label}"])

    if not rows:
        print("No se hallaron caracteres objetivo. ¿Layout muy inusual?"); sys.exit(2)

    render(rows, mode=mode)

    print("\nTips QMK:")
    print(" - Usa RALT(...) para emular AltGr (Right Alt) en Linux.")
    print(" - Ejemplos:  @ → RALT(KC_Q)    ` → KC_GRV    { → RALT(S(KC_7)) (según layout)")
    print(" - Para macros complejas, SEND_STRING(\"@@foo\"); o combina MO/TT para layers.")

if __name__ == "__main__":
    main()

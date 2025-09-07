#include QMK_KEYBOARD_H
#include "quantum.h"
#include "process_unicode.h"
#include "unicode.h"

/* -------------------------------------------------------
 * Capas (NAV al final para máxima prioridad)
 * ----------------------------------------------------- */
enum layer_number {
  _BASE = 0,   // QWERTY LATAM
  _SYM,        // símbolos (momentánea)
  _NUM,        // numpad (toggle)
  _SYS,        // sistema / medios (toggle)
  _NAV,        // navegación + F-keys (momentánea)
};

/* -------------------------------------------------------
 * Keycodes personalizados (Unicode + macros)
 * ----------------------------------------------------- */
enum custom_keycodes {
  // Letras/signos propios ES-LATAM
  ES_NTIL = SAFE_RANGE,   // ñ (Shift => Ñ)
  ES_NTIL_CAP,            // Ñ forzado
  ES_IQUES,               // ¿
  ES_IEXCL,               // ¡

  // Símbolos exactos
  PIPE_UNICODE,           // |
  BSLS_UNICODE,           // (\)
  LCBR_UNICODE,           // {
  RCBR_UNICODE,           // }
  LBRC_UNICODE,           // [
  RBRC_UNICODE,           // ]
  LT_UNICODE,             // <
  GT_UNICODE,             // >
  ARRO_UNICODE,           // @
  ES_DQUO,                // "
  ES_SQUO,                // '
  ES_BKTICK,              // `
  ES_BKTICK3,             // ``` (Markdown)
  ES_TILDE,               // ~

  // Operadores exactos
  EQL_SYM,                // =
  MINUS_SYM,              // -
  SLASH_SYM,              // /
  ASTER_SYM,              // *
  PLUS_SYM,               // +

  // Macro Yakuake
  MACRO_YAKU,
};

/* -------------------------------------------------------
 * Helper Yakuake
 * ----------------------------------------------------- */
static void send_yakuake(void) {
    // En KDE F12 basta para abrir/retraer Yakuake
    tap_code(KC_F12);

    // Si más adelante cambias el atajo a Ctrl+Shift+F12, usa esto:
    // tap_code16(C(S(KC_F12)));
}

/* -------------------------------------------------------
 * Keymaps
 * ----------------------------------------------------- */
const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
[_BASE] = LAYOUT(
  KC_ESC,  KC_1, KC_2, KC_3, KC_4, KC_5,                         KC_6, KC_7, KC_8, KC_9, KC_0, KC_BSPC,
  KC_TAB,  KC_Q, KC_W, KC_E, KC_R, KC_T,                         KC_Y, KC_U, KC_I, KC_O, KC_P, EQL_SYM,
  KC_LSFT, KC_A, KC_S, KC_D, KC_F, KC_G,                         KC_H, KC_J, KC_K, KC_L, ES_NTIL, KC_SCLN,
  KC_LCTL, KC_Z, KC_X, KC_C, KC_V, KC_B, KC_LBRC, KC_RBRC,       KC_N, KC_M, KC_COMM, KC_DOT, SLASH_SYM, KC_RSFT,
                 KC_LALT, KC_LGUI, MO(_SYM), KC_SPC, KC_ENT, MO(_NAV), TG(_NUM), TG(_SYS)
),

[_SYM] = LAYOUT(
  ES_BKTICK, ES_TILDE,  LT_UNICODE, GT_UNICODE, LBRC_UNICODE, RBRC_UNICODE,    LCBR_UNICODE, RCBR_UNICODE, PIPE_UNICODE, BSLS_UNICODE, ARRO_UNICODE, SLASH_SYM,
  KC_F1,     ES_SQUO,   ES_BKTICK3,  ES_DQUO,   ES_BKTICK,    KC_CAPS,         KC_COLN,      ES_IQUES,     KC_QUES,      ES_IEXCL,     KC_EXLM,      KC_F12,
  _______,   _______,   _______,     _______,   _______,      _______,          _______,      KC_LEFT,      KC_DOWN,      KC_UP,        KC_RGHT,      _______,
  _______,   _______,   _______,     _______,   _______,      _______, _______, _______, _______, _______,   _______,      _______,      _______,      _______,
                      _______, _______, _______, _______, _______, _______, _______, _______
),

[_NUM] = LAYOUT(
  _______, _______, _______, _______, _______, _______,               KC_7,   KC_8,   KC_9,   SLASH_SYM, ASTER_SYM, _______,
  _______, _______, _______, _______, _______, _______,               KC_4,   KC_5,   KC_6,   MINUS_SYM, PLUS_SYM,  _______,
  _______, _______, _______, _______, _______, _______,               KC_1,   KC_2,   KC_3,   EQL_SYM,   KC_ENT,    _______,
  _______, _______, _______, _______, _______, _______, _______, _______, _______, KC_0, KC_DOT, _______, _______, _______,
                      _______, _______, _______, _______, _______, _______, _______, _______
),

[_SYS] = LAYOUT(
  _______, _______, _______, _______, _______, _______,                        _______, _______, _______, _______, _______, _______,
  _______, KC_VOLU,  KC_MUTE, KC_VOLD, _______, _______,                      _______, _______, _______, _______, _______, _______,
  _______, KC_MPRV,  KC_MPLY, KC_MNXT, _______, _______,                      _______, LGUI(KC_TAB), LSFT(LGUI(KC_S)), LGUI(KC_L), MACRO_YAKU, _______,
  _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______,
                      _______, _______, _______, _______, _______, _______, _______, _______
),

[_NAV] = LAYOUT(
  KC_F1,  KC_F2, KC_F3, KC_F4, KC_F5, KC_F6,                       KC_F7, KC_F8, KC_F9, KC_F10, KC_F11, KC_F12,
  _______, _______, _______, _______, _______, _______,             KC_HOME, KC_PGDN, KC_PGUP, KC_END, _______, _______,
  _______, _______, _______, _______, _______, _______,             XXXXXXX, KC_LEFT, KC_DOWN, KC_UP,   KC_RGHT, XXXXXXX,
  _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______,
                      _______, _______, _______, _______, _______, _______, _______, _______
),
};

/* -------------------------------------------------------
 * Unicode y macros
 * ----------------------------------------------------- */
bool process_record_user(uint16_t keycode, keyrecord_t *record) {
  if (!record->event.pressed) return true;

  switch (keycode) {
    case ES_NTIL:       send_unicode_string((get_mods() & MOD_MASK_SHIFT) ? "Ñ" : "ñ"); return false;
    case ES_NTIL_CAP:   send_unicode_string("Ñ"); return false;
    case PIPE_UNICODE:  send_unicode_string("|"); return false;
    case LBRC_UNICODE:  send_unicode_string("["); return false;
    case RBRC_UNICODE:  send_unicode_string("]"); return false;
    case LCBR_UNICODE:  send_unicode_string("{"); return false;
    case RCBR_UNICODE:  send_unicode_string("}"); return false;
    case LT_UNICODE:    send_unicode_string("<"); return false;
    case GT_UNICODE:    send_unicode_string(">"); return false;
    case BSLS_UNICODE:  send_unicode_string("\\"); return false;
    case ARRO_UNICODE:  send_unicode_string("@"); return false;
    case ES_IQUES:      send_unicode_string("¿"); return false;
    case ES_IEXCL:      send_unicode_string("¡"); return false;
    case ES_DQUO:       send_unicode_string("\""); return false;
    case ES_SQUO:       send_unicode_string("'"); return false;
    case ES_BKTICK:     send_unicode_string("`"); return false;
    case ES_BKTICK3:    SEND_STRING("```"); return false;
    case ES_TILDE:      send_unicode_string("~"); return false;
    case EQL_SYM:       send_unicode_string("="); return false;
    case MINUS_SYM:     send_unicode_string("-"); return false;
    case SLASH_SYM:     send_unicode_string("/"); return false;
    case ASTER_SYM:     send_unicode_string("*"); return false;
    case PLUS_SYM:      send_unicode_string("+"); return false;

    // Macro Yakuake
    case MACRO_YAKU:    send_yakuake(); return false;
  }
  return true;
}

/* -------------------------------------------------------
 * Iluminación por capas (RGB) — respirar SIEMPRE
 * ----------------------------------------------------- */
#ifdef RGBLIGHT_ENABLE
static bool uppercase_active(void) {
  return host_keyboard_led_state().caps_lock ||
         ((get_mods() | get_oneshot_mods()) & MOD_MASK_SHIFT);
}

static void apply_layer_lighting(layer_state_t st) {
  rgblight_mode_noeeprom(RGBLIGHT_MODE_BREATHING);
  rgblight_set_speed(60);

  if (uppercase_active()) {
    rgblight_sethsv_noeeprom(HSV_RED);
    return;
  }
  if (layer_state_cmp(st, _SYS)) {
    rgblight_sethsv_noeeprom(HSV_MAGENTA);
  } else if (layer_state_cmp(st, _NUM)) {
    rgblight_sethsv_noeeprom(HSV_GREEN);
  } else if (layer_state_cmp(st, _NAV)) {
    rgblight_sethsv_noeeprom(HSV_YELLOW);
  } else if (layer_state_cmp(st, _SYM)) {
    rgblight_sethsv_noeeprom(HSV_BLUE);
  } else {
    rgblight_sethsv_noeeprom(HSV_WHITE);
  }
}
#endif

void keyboard_post_init_user(void) {
  set_unicode_input_mode(UNICODE_MODE_LINUX);
#ifdef RGBLIGHT_ENABLE
  rgblight_enable_noeeprom();
  apply_layer_lighting(layer_state);
#endif
}

layer_state_t layer_state_set_user(layer_state_t state) {
#ifdef RGBLIGHT_ENABLE
  apply_layer_lighting(state);
#endif
  return state;
}

bool led_update_user(led_t led_state) {
#ifdef RGBLIGHT_ENABLE
  apply_layer_lighting(layer_state);
#endif
  return true;
}

void post_process_record_user(uint16_t keycode, keyrecord_t *record) {
#ifdef RGBLIGHT_ENABLE
  if (keycode == KC_LSFT || keycode == KC_RSFT) {
    apply_layer_lighting(layer_state);
  }
#endif
}

/* -------------------------------------------------------
 * OLED (opcional)
 * ----------------------------------------------------- */
#ifdef OLED_ENABLE
#include "oled_driver.h"
static void oled_print_layer_name(void) {
  uint8_t layer = get_highest_layer(layer_state | default_layer_state);
  switch (layer) {
    case _BASE: oled_write_ln_P(PSTR("Layer: BASE"), false); break;
    case _SYM:  oled_write_ln_P(PSTR("Layer: SYM"),  false); break;
    case _NUM:  oled_write_ln_P(PSTR("Layer: NUM"),  false); break;
    case _SYS:  oled_write_ln_P(PSTR("Layer: SYS"),  false); break;
    case _NAV:  oled_write_ln_P(PSTR("Layer: NAV"),  false); break;
    default:    oled_write_ln_P(PSTR("Layer: ???"),  false); break;
  }
}
const char *read_logo(void);
void set_keylog(uint16_t keycode, keyrecord_t *record);
const char *read_keylog(void);
const char *read_keylogs(void);
bool oled_task_user(void) {
  if (is_keyboard_master()) {
    oled_print_layer_name();
    oled_write_ln(read_keylog(),  false);
    oled_write_ln(read_keylogs(), false);
  } else {
    oled_write(read_logo(), false);
  }
  return false;
}
#endif

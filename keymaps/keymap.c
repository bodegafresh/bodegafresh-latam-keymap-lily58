#include QMK_KEYBOARD_H
#include "quantum.h"

/* ──────────────────────────────────────────────────────────────
 *  SYM fila en ES-LATAM (según tu XKB):
 *  - { } = AltGr+[ / AltGr+]
 *  - [ ] = Shift+AltGr+[ / Shift+AltGr+]
 *  - \ | = AltGr+- / AltGr+_
 *  - @   = AltGr+Q
 *  - /   = Shift+7
 *  Sin Unicode. Usa tap_clean() para evitar mods “pegados”.
 * ────────────────────────────────────────────────────────────*/

enum layer_number { _BASE=0, _SYM, _NUM, _SYS, _NAV };

/* Keycodes personalizados */
enum custom_keycodes {
  /* letras/signos ES */
  ES_NTIL = SAFE_RANGE, ES_NTIL_CAP, ES_IQUES, ES_IEXCL, ES_QUES,

  /* símbolos de la fila SYM */
  SYM_BACKTICK, SYM_TILDE, SYM_LT, SYM_GT,
  SYM_LBRC, SYM_RBRC, SYM_LCBR, SYM_RCBR,
  SYM_PIPE, SYM_BSLS, SYM_AT, SYM_SLASH,
  SYM_INIT_A,SYM_INIT_G, SYM_KC_COLN, SYM_CARET,

  /* operadores “normales” */
  EQL_SYM, MINUS_SYM, SLASH_SYM, ASTER_SYM, PLUS_SYM, MINUS_UNDER,

  /* utilitarios */
  DQUO_SYM, SQUO_SYM, BKTICK3_SYM,

  MACRO_YAKU,
};

/* Helpers */
static inline bool shift_active(void){
  return (get_mods() | get_oneshot_mods()) & MOD_MASK_SHIFT;
}

/* limpia mods/oneshot, envía, y restaura (evita AltGr/Shift “pegados”) */
static inline void tap_clean(uint16_t kc){
  uint8_t m = get_mods(), o = get_oneshot_mods();
  clear_mods(); clear_oneshot_mods(); send_keyboard_report();
  tap_code16(kc);
  set_mods(m); set_oneshot_mods(o); send_keyboard_report();
}

static inline void send_yakuake(void){
    tap_code16(C(S(KC_F12)));   // Ctrl + Shift + F12
}

static inline void tap_once16(uint16_t kc) {
    register_code16(kc);
    wait_ms(18);            // 15–25ms suele ser perfecto
    unregister_code16(kc);
    wait_ms(18);
}

static inline void send_triple_backtick(void){
    tap_once16(RALT(KC_NUHS));   // `
    tap_once16(RALT(KC_NUHS));   // `
    tap_once16(RALT(KC_NUHS));   // `
}

static inline void send_caret_from_dead(void){
    tap_clean(RALT(KC_LBRC));  // dead_circumflex
    wait_ms(18);
    tap_clean(KC_SPC);
}
/* ──────────────────────────────────────────────────────────────
 * Keymaps
 * ────────────────────────────────────────────────────────────*/
const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
/* BASE */
[_BASE] = LAYOUT(
  KC_ESC,  KC_1, KC_2, KC_3, KC_4, KC_5,                         KC_6, KC_7, KC_8, KC_9, KC_0, KC_BSPC,
  KC_TAB,  KC_Q, KC_W, KC_E, KC_R, KC_T,                         KC_Y, KC_U, KC_I, KC_O, KC_P, ASTER_SYM,
  KC_LSFT, KC_A, KC_S, KC_D, KC_F, KC_G,                         KC_H, KC_J, KC_K, KC_L, ES_NTIL, KC_DEL,
  KC_LCTL, KC_Z, KC_X, KC_C, KC_V, KC_B, KC_LBRC, KC_RBRC,       KC_N, KC_M, KC_COMM, KC_DOT, MINUS_UNDER, KC_RSFT,
                 KC_LALT, KC_LGUI, MO(_SYM), KC_SPC, KC_ENT, MO(_NAV), TG(_NUM), TG(_SYS)
),

/* SYM (fila 1: `~<>[]{}|\@/) */
[_SYM] = LAYOUT(
  SYM_BACKTICK, SYM_TILDE, SYM_LT,  SYM_GT,  SYM_LBRC, SYM_RBRC, SYM_LCBR, SYM_RCBR, SYM_PIPE, SYM_BSLS, SYM_AT,  SYM_SLASH,
  SYM_INIT_A, BKTICK3_SYM, SQUO_SYM , DQUO_SYM, ASTER_SYM, KC_CAPS, SYM_KC_COLN, ES_IQUES, ES_QUES, ES_IEXCL, KC_EXLM,  SYM_INIT_G,
  SYM_CARET, _______,   _______, _______, _______, _______,   _______, _______, _______,  _______,   _______,  MACRO_YAKU,
  _______,      _______,   _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______,
                           _______, _______, _______, _______, _______, _______, _______, _______
),

/* NUM */
[_NUM] = LAYOUT(
  _______, _______, _______, _______, _______, _______,               KC_7,   KC_8,   KC_9,   SLASH_SYM, ASTER_SYM, XXXXXXX,
  _______, _______, _______, _______, _______, _______,               KC_4,   KC_5,   KC_6,   MINUS_SYM, PLUS_SYM,  XXXXXXX,
  _______, _______, _______, _______, _______, _______,               KC_1,   KC_2,   KC_3,   EQL_SYM,   KC_COMM,    XXXXXXX,
  _______, _______, _______, _______, _______, _______, _______, XXXXXXX, XXXXXXX, KC_0, KC_DOT, XXXXXXX, XXXXXXX, XXXXXXX,
                           _______, _______, _______, _______, KC_ENT, _______, _______, _______
),

/* SYS */
[_SYS] = LAYOUT(
  _______, _______, _______, _______, _______, _______,                        _______, _______, _______, _______, _______, _______,
  _______, KC_VOLD,  KC_MUTE, KC_VOLU, _______, _______,                      _______, _______, _______, _______, _______, _______,
  _______, KC_MPRV,  KC_MPLY, KC_MNXT, _______, _______,                      _______, LGUI(KC_TAB), LSFT(LGUI(KC_S)), LGUI(KC_L), _______, _______,
  _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______,
                           _______, _______, _______, _______, _______, _______, _______, _______
),

/* NAV */
[_NAV] = LAYOUT(
  KC_F1,  KC_F2, KC_F3, KC_F4, KC_F5, KC_F6,                       KC_F7, KC_F8, KC_F9, KC_F10, KC_F11, KC_F12,
  _______, _______, _______, _______, _______, _______,             XXXXXXX, KC_HOME, KC_PGDN, KC_PGUP, KC_END, XXXXXXX,
  KC_LSFT, _______, _______, _______, _______, _______,             XXXXXXX, KC_LEFT, KC_DOWN, KC_UP,   KC_RGHT, XXXXXXX,
  KC_LCTL, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______,
                           _______, _______, _______, _______, _______, _______, _______, _______
),
};

/* ──────────────────────────────────────────────────────────────
 * Lógica personalizada
 * ────────────────────────────────────────────────────────────*/
bool process_record_user(uint16_t keycode, keyrecord_t *record) {
  if (!record->event.pressed) return true;

  switch (keycode) {
    /* Ñ/¿/¡ */
    case ES_NTIL:       tap_clean(shift_active() ? S(KC_SCLN) : KC_SCLN);  return false;
    case ES_NTIL_CAP:   tap_clean(S(KC_SCLN));                             return false;
    case ES_IQUES:      tap_clean(KC_EQL);                                 return false; // ¿
    case ES_IEXCL:      tap_clean(S(RALT(KC_1)));                          return false; // ¡
    case ES_QUES:       tap_clean(S(KC_MINS));                             return false; // ?

    /* Fila SYM (según tu XKB) */
    case SYM_BACKTICK:  tap_clean(RALT(KC_NUHS));          return false; // `  (si no cuadra, te ajusto esto)
    case SYM_TILDE:     tap_clean(RALT(KC_4));             return false; // ~  (ídem)
    case SYM_LT:        tap_clean(KC_NUBS);                return false; // <
    case SYM_GT:        tap_clean(S(KC_NUBS));             return false; // >
    case SYM_LBRC:      tap_clean(RALT(KC_8));             return false; // [
    case SYM_RBRC:      tap_clean(RALT(KC_9));             return false; // ]  (o RALT(KC_0) según distro)
    case SYM_LCBR:      tap_clean(RALT(KC_7));             return false; // {
    case SYM_RCBR:      tap_clean(RALT(KC_0));             return false; // }  (o RALT(S(KC_0)))
    case SYM_BSLS:      tap_clean(RALT(KC_MINS));          return false; // (\)
    case SYM_PIPE:      tap_clean(RALT(KC_1));             return false; // |
    case SYM_AT:        tap_clean(RALT(KC_Q));             return false; // @
    case SYM_SLASH:     tap_clean(S(KC_7));                return false; // /
    case SYM_INIT_A:    tap_clean(RALT(KC_GRV));           return false; // ¬
    case SYM_INIT_G:    tap_clean(S(KC_GRV));              return false; // °
    case SYM_KC_COLN:   tap_clean(S(KC_DOT));              return false; // :
    case SYM_CARET:     send_caret_from_dead();            return false; // ^

    /* Operadores */
    case EQL_SYM:       tap_clean(S(KC_0));                return false; // =
    case MINUS_SYM:     tap_clean(KC_SLSH);                return false; // -
    case SLASH_SYM:     tap_clean(S(KC_7));                return false; // /
    case ASTER_SYM:     tap_clean(KC_KP_ASTERISK);         return false; // *
    case PLUS_SYM:      tap_clean(KC_KP_PLUS);             return false; // +
    case MINUS_UNDER:   tap_clean(shift_active() ? S(KC_SLSH) : KC_SLSH); return false; // _ / -

    /* utilitarios */
    case DQUO_SYM:      tap_clean(RALT(KC_LBRC));          return false; // "
    case SQUO_SYM:      tap_clean(KC_LBRC);                return false; // '
    case BKTICK3_SYM:   send_triple_backtick();            return false;

    case MACRO_YAKU:    send_yakuake();                    return false;
  }
  return true;
}

/* ──────────────────────────────────────────────────────────────
 * RGB “breathing”
 * ────────────────────────────────────────────────────────────*/
#ifdef RGBLIGHT_ENABLE
static inline bool shift_active_local(void){
  return (get_mods() | get_oneshot_mods()) & MOD_MASK_SHIFT;
}
static bool uppercase_active(void) {
  return host_keyboard_led_state().caps_lock || shift_active_local();
}

static void apply_layer_lighting(layer_state_t st) {
  rgblight_mode_noeeprom(RGBLIGHT_MODE_BREATHING);
  rgblight_set_speed(60);
  if (uppercase_active()) { rgblight_sethsv_noeeprom(HSV_RED); return; }
  if (layer_state_cmp(st, _SYS)) rgblight_sethsv_noeeprom(HSV_MAGENTA);
  else if (layer_state_cmp(st, _NUM)) rgblight_sethsv_noeeprom(HSV_GREEN);
  else if (layer_state_cmp(st, _NAV)) rgblight_sethsv_noeeprom(HSV_YELLOW);
  else if (layer_state_cmp(st, _SYM)) rgblight_sethsv_noeeprom(HSV_BLUE);
  else rgblight_sethsv_noeeprom(HSV_WHITE);
}
void keyboard_post_init_user(void){
  rgblight_enable_noeeprom();
  apply_layer_lighting(layer_state);
}
layer_state_t layer_state_set_user(layer_state_t s){ apply_layer_lighting(s); return s; }
bool led_update_user(led_t led_state){ apply_layer_lighting(layer_state); return true; }
void post_process_record_user(uint16_t keycode, keyrecord_t *record){
  if (keycode==KC_LSFT || keycode==KC_RSFT || keycode==KC_CAPS) apply_layer_lighting(layer_state);
}
#endif

/* OLED */
#ifdef OLED_ENABLE
#include "oled_driver.h"
#include "bodegafresh_logo.h"

static const char *layer_name(void) {
  switch (get_highest_layer(layer_state | default_layer_state)) {
    case _BASE: return "BASE";
    case _SYM:  return "SYM";
    case _NUM:  return "NUM";
    case _SYS:  return "SYS";
    case _NAV:  return "NAV";
    default:    return "???";
  }
}

/* Dibuja el logo 112x16 en la esquina superior izquierda
   y limpia el resto de las dos primeras páginas (16 px de alto). */
static void draw_bodegafresh_top(void) {
  oled_clear();  // limpia TODO el buffer primero

  // Escribir el bitmap (224 bytes) en (0,0)
  const uint16_t LOGO_BYTES = (BODEGAFRESH_W * BODEGAFRESH_H) / 8;     // 112*16/8 = 224
  for (uint16_t i = 0; i < LOGO_BYTES; i++) {
    oled_write_raw_byte(pgm_read_byte(&bodegafresh_logo_112x16[i]), i);
  }

  // Rellenar con 0 el resto de las dos primeras páginas para evitar “ruido”
  const uint16_t PAGE_BYTES = 128;                    // 128 columnas por página
  const uint16_t TWO_PAGES  = PAGE_BYTES * 2;         // 16 px alto = 2 páginas
  for (uint16_t i = LOGO_BYTES; i < TWO_PAGES; i++) {
    oled_write_raw_byte(0x00, i);
  }
}

const char *read_logo(void);
void set_keylog(uint16_t keycode, keyrecord_t *record);
const char *read_keylog(void);
const char *read_keylogs(void);
bool oled_task_user(void) {
  if (is_keyboard_master()) {
    draw_bodegafresh_top();

    // Texto abajo (desde y=16 px => fila 2)
    oled_set_cursor(0, 2);                 // columna 0, fila 2 (cada fila = 8 px)
    oled_write_P(PSTR("Layer: "), false);
    oled_write(layer_name(), false);
  } else {
    oled_write(read_logo(), false);
  }
  return false;
}
#endif

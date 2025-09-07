LTO_ENABLE = yes

BOOTMAGIC_ENABLE = yes
MOUSEKEY_ENABLE = no
EXTRAKEY_ENABLE = yes
CONSOLE_ENABLE = no
COMMAND_ENABLE = no
BACKLIGHT_ENABLE = no
AUDIO_ENABLE = no
RGBLIGHT_ENABLE = yes
# RGB_MATRIX_ENABLE = no

NKRO_ENABLE     = yes

OLED_ENABLE = yes
UNICODE_ENABLE = yes

SRC +=  ./lib/rgb_state_reader.c \
        ./lib/layer_state_reader.c \
        ./lib/logo_reader.c \
        ./lib/keylogger.c

/**
 * The one line that picks a board. Uncomment exactly one; panel_bridge.cpp
 * takes PANEL_WIDTH, PANEL_HEIGHT, board_gfx_new() and board_backlight_on()
 * from whichever header this names. See src/boards/README.md for the
 * contract, what is here, and the FQBN/OPTS each board needs from build.sh.
 */
#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

#include "src/boards/guition_jc3248w535.h"         // Guition JC3248W535 3.5" (diymore ESP32-S3 3.5")
// #include "src/boards/waveshare_esp32s3_lcd_147.h"  // Waveshare ESP32-S3-LCD-1.47 / 1.47B
// #include "src/boards/waveshare_esp32c6_lcd_13.h"   // Waveshare ESP32-C6-LCD-1.3 (RISC-V, no PSRAM)
// #include "src/boards/sunton_esp32_3248s035.h"      // Sunton 3.5" "Cheap Yellow Display" (classic ESP32)

#endif /* BOARD_CONFIG_H */

/**
 * scene_player — play the scene compiled into scene_embedded.h, on the
 * board board_config.h names. No network: the scene is part of the firmware.
 *
 *     python embed_scene.py scene.html     # make scene_embedded.h
 *     ./build.sh /dev/ttyACM0              # compile, upload, monitor
 *
 * Everything below the three calls is panel_bridge.cpp.
 */

#include <Arduino.h>

#include "panel_bridge.h"
#include "scene_embedded.h"   // PANEL_SCENE

// Replay the scene's animations, or play once and hold the last frame.
#define LOOP_SCENE  true

void setup() {
    Serial.begin(115200);
    delay(200);

    if(!panel_begin()) {
        Serial.printf("panel: %s\n", panel_error());
        return;
    }
    if(!panel_load_scene(PANEL_SCENE)) {
        Serial.printf("scene refused: %s\n", panel_error());
        return;
    }
    Serial.printf("scene: %dx%d panel, %.1f s\n",
                  panel_width(), panel_height(), panel_duration_ms() / 1000.0f);
    panel_play(LOOP_SCENE);
}

void loop() {
    panel_update();
    delay(5);
}

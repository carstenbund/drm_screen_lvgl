/**
 * panel_bridge — a drm_scene_ir scene on an ESP32 panel.
 *
 * The on-device half of the stack: `drm_composer` compiles screen-HTML into a
 * scene document on a host, and this draws that document on the glass, with
 * the same C evaluator and LVGL renderer drm_screen_lvgl binds on Linux.
 *
 *     scene JSON -> mm_scene_from_json -> mm_evaluate -> mm_render_scene
 *                -> LVGL canvas -> flush -> Arduino_GFX -> panel
 *
 * Which panel is board_config.h's business. The API is plain C so a .c file
 * can call it as well as a sketch.
 */
#ifndef PANEL_BRIDGE_H
#define PANEL_BRIDGE_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Start the board's panel and LVGL, with a canvas covering the screen. */
bool panel_begin(void);

/** Parse a scene document, once. On refusal nothing is drawn until a scene
 *  loads, and panel_error() says why.
 *
 *  Its pictures are checked on the SD card at S:/assets/<src>.bin against the
 *  size and CRC32 the composer wrote. A missing or mismatched picture does not
 *  refuse the scene: it is left out, panel_missing_assets() counts it and
 *  panel_error() names the first. */
bool panel_load_scene(const char *scene_json);

/** Pictures of the loaded scene that are not drawn: missing, or a file from
 *  another build. */
int panel_missing_assets(void);

/** Draw the scene as it is at `scene_time_ms`. Skipped when that frame is
 *  already on the glass, or when the scene has finished moving. For a clock
 *  kept elsewhere -- a server, a sensor, a button. */
void panel_draw(float scene_time_ms);

/** Run the scene on the local clock from now: replay (`loop`) or hold the
 *  last frame. panel_update() then draws it. */
void panel_play(bool loop);

/** Call from every loop(): draws the playing scene, then services LVGL. */
void panel_update(void);

int panel_width(void);
int panel_height(void);
float panel_duration_ms(void);
const char *panel_error(void);

#ifdef __cplusplus
}
#endif

#endif /* PANEL_BRIDGE_H */

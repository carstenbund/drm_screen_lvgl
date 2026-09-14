#include "panel_bridge.h"

#include <Arduino.h>
#include <lvgl.h>
#include <lvgl_private.h>   // lv_image_cache_drop

#include <math.h>
#include <stdio.h>

#include "board_config.h"   // PANEL_WIDTH/HEIGHT, board_gfx_new(), board_backlight_on(), board_sd_begin()

extern "C" {
#include "assets_lvgl.h"
#include "evaluator.h"
#include "geometry.h"
#include "render_lvgl.h"
#include "scene_json.h"
#include "scene_model.h"
}

// LVGL sends the panel strips this many lines tall.
static const int FLUSH_LINES = 40;

// Where a scene's pictures are: the board mounts its SD card at /sd, and
// lv_conf.h maps LVGL's "S:" onto it -- so S:/assets/logo.bin is
// /sd/assets/logo.bin on the card.
#ifndef PANEL_ASSET_ROOT
#define PANEL_ASSET_ROOT "S:/assets/"
#endif

static bool sd_ready = false;
static int missing_assets = 0;

static Arduino_GFX *gfx = nullptr;
static lv_display_t *display = nullptr;
static lv_obj_t *scene_obj = nullptr;
static uint16_t *panel_strip = nullptr;   // one flushed strip, in the panel's RGB565

static mm_scene_t scene;        // ~19 KB: static, never on the stack
static bool scene_ready = false;
static uint32_t scene_generation = 0;
static uint32_t drawn_generation = 0;
static float drawn_time = 0.0f;

static bool playing = false;
static bool looping = false;
static uint32_t play_started_ms = 0;

static char error_text[128] = "";

// millis returns unsigned long; LVGL's tick callback is uint32_t(void), and
// C++ will not convert one function pointer type to the other.
static uint32_t tick_ms(void) {
    return millis();
}

// LVGL renders strips in XRGB8888 -- the format ThorVG draws into directly,
// with no temporary buffer per shape -- and the panel takes RGB565, so each
// strip is converted here on its way out. XRGB8888 is stored B, G, R, X.
static void flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map) {
    const int32_t w = area->x2 - area->x1 + 1;
    const int32_t h = area->y2 - area->y1 + 1;
    const int32_t count = w * h;
    for(int32_t i = 0; i < count; i++) {
        const uint8_t *p = px_map + i * 4;
        panel_strip[i] = (uint16_t)(((p[2] & 0xF8) << 8) | ((p[1] & 0xFC) << 3) | (p[0] >> 3));
    }
    gfx->draw16bitRGBBitmap(area->x1, area->y1, panel_strip, w, h);
    lv_display_flush_ready(disp);
}

// The scene is drawn while LVGL redraws the object, straight into the strip
// being rendered and clipped to it -- no full-screen frame exists anywhere.
static void draw_scene_cb(lv_event_t *e) {
    if(!scene_ready) return;
    mm_render_scene(lv_event_get_layer(e), &scene, PANEL_WIDTH, PANEL_HEIGHT, NULL, 0, drawn_time);
}

static void release_paths(void) {
    for(int i = 0; i < scene.object_count; i++) {
        mm_path_destroy(scene.objects[i].path);
        scene.objects[i].path = NULL;
    }
    scene.object_count = 0;
}

bool panel_begin(void) {
    if(display != nullptr) return true;

    lv_init();
    lv_tick_set_cb(tick_ms);

    // No card is not an error: a scene without pictures needs none, and one
    // with pictures reports them as missing when it loads.
    sd_ready = board_sd_begin();

    board_backlight_on();
    gfx = board_gfx_new();
    if(!gfx->begin()) {
        snprintf(error_text, sizeof(error_text), "the panel driver did not start");
        return false;
    }
    gfx->fillScreen(0x0000);

    // Memory is one strip twice over: FLUSH_LINES of XRGB8888 for LVGL and
    // the same strip in RGB565 for the panel. lv_draw_buf_create aligns the
    // render buffer as LVGL requires.
    lv_draw_buf_t *strip = lv_draw_buf_create(PANEL_WIDTH, FLUSH_LINES, LV_COLOR_FORMAT_XRGB8888, 0);
    panel_strip = (uint16_t *)lv_malloc(sizeof(uint16_t) * PANEL_WIDTH * FLUSH_LINES);
    if(strip == NULL || panel_strip == NULL) {
        snprintf(error_text, sizeof(error_text), "no memory for a %d-line strip", FLUSH_LINES);
        return false;
    }
    display = lv_display_create(PANEL_WIDTH, PANEL_HEIGHT);
    lv_display_set_color_format(display, LV_COLOR_FORMAT_XRGB8888);
    lv_display_set_flush_cb(display, flush_cb);
    lv_display_set_draw_buffers(display, strip, NULL);
    lv_display_set_render_mode(display, LV_DISPLAY_RENDER_MODE_PARTIAL);

    scene_obj = lv_obj_create(lv_display_get_screen_active(display));
    lv_obj_remove_style_all(scene_obj);
    lv_obj_set_pos(scene_obj, 0, 0);
    lv_obj_set_size(scene_obj, PANEL_WIDTH, PANEL_HEIGHT);
    lv_obj_set_style_bg_color(scene_obj, lv_color_hex(0x000000), 0);
    lv_obj_set_style_bg_opa(scene_obj, LV_OPA_COVER, 0);
    lv_obj_remove_flag(scene_obj, (lv_obj_flag_t)(LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE));
    lv_obj_add_event_cb(scene_obj, draw_scene_cb, LV_EVENT_DRAW_MAIN, NULL);
    return true;
}

bool panel_load_scene(const char *scene_json) {
    // Parsed paths are allocations the scene owns; a new document replaces
    // them, so the old ones go first or every load leaks them.
    release_paths();
    playing = false;
    scene_generation++;
    scene_ready = mm_scene_from_json(scene_json, &scene, error_text, sizeof(error_text));
    missing_assets = 0;
    if(scene_ready) {
        // A decoded picture stays in LVGL's cache under its path; a new scene
        // may name a file that has since been replaced on the card.
        lv_image_cache_drop(NULL);
        missing_assets = mm_scene_load_assets(&scene, PANEL_ASSET_ROOT, error_text, sizeof(error_text));
        if(missing_assets > 0 && !sd_ready) {
            snprintf(error_text, sizeof(error_text), "no SD card: %d picture(s) not drawn", missing_assets);
        }
    }
    if(scene_obj != nullptr) lv_obj_invalidate(scene_obj);   // the glass shows what is loaded
    return scene_ready;
}

void panel_draw(float scene_time_ms) {
    if(scene_obj == nullptr || !scene_ready) return;

    // A frame is a pure function of (scene, time): one already on the glass
    // never needs drawing again, and after the last animation ends no later
    // time looks any different.
    if(drawn_generation == scene_generation) {
        const float end = scene.duration_ms;
        if(scene_time_ms == drawn_time) return;
        if(scene_time_ms >= end && drawn_time >= end) return;
    }

    // Evaluate now; LVGL draws the evaluated state during its next refresh.
    mm_evaluate(&scene, scene_time_ms);
    lv_obj_invalidate(scene_obj);

    drawn_generation = scene_generation;
    drawn_time = scene_time_ms;
}

void panel_play(bool loop) {
    playing = true;
    looping = loop;
    play_started_ms = millis();
}

void panel_update(void) {
    if(playing && scene_ready) {
        float scene_time = (float)(millis() - play_started_ms);
        if(looping && scene.duration_ms > 0.0f) {
            scene_time = fmod(scene_time, scene.duration_ms);
        }
        panel_draw(scene_time);
    }
    lv_timer_handler();
}

int panel_missing_assets(void) {
    return missing_assets;
}

int panel_width(void) {
    return PANEL_WIDTH;
}

int panel_height(void) {
    return PANEL_HEIGHT;
}

float panel_duration_ms(void) {
    return scene_ready ? scene.duration_ms : 0.0f;
}

const char *panel_error(void) {
    return error_text;
}

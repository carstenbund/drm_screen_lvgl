# esp32 — the renderer on a microcontroller

The Python package in this repository draws `drm_scene_ir` scenes on Linux
through LVGL. This folder draws the same documents on an ESP32 panel, with the
same C evaluator and LVGL renderer, and no Python on the device.

```
host     screen-HTML --drm_composer.emit_screen_json--> scene JSON
            embed_scene.py --> scene_embedded.h
device   panel_bridge: mm_scene_from_json -> mm_evaluate
            -> LVGL refresh: mm_render_scene into each XRGB8888 strip
            -> flush: RGB565 -> GFX Library for Arduino -> panel
```

## `scene_player/`

An Arduino sketch that plays one scene compiled into the firmware.

| file | what it is |
|---|---|
| `scene_player.ino` | the call: `panel_begin()`, `panel_load_scene()`, `panel_play()`, then `panel_update()` every loop |
| `panel_bridge.h/.cpp` | the bridge, with a C API: the board's panel, LVGL's clock, display and flush, and the player. The scene is drawn during LVGL's own refresh, straight into the strip being rendered, so no full-screen frame exists: memory is one 40-line strip in XRGB8888 plus the same strip in RGB565 (~77 KB at 320 wide). It frees a scene's paths before loading the next, and only redraws when the scene time changes |
| `board_config.h`, `src/boards/` | one header per board: bus, pins, controller chip, SD card. See [`src/boards/README.md`](scene_player/src/boards/README.md) |
| `lv_conf.h` | LVGL for the panel: vector graphics (ThorVG) on, Montserrat 14–28, pictures from the SD card (`S:` → `/sd`) with a 1 MB image cache |
| `embed_scene.py`, `scene.html` | screen-HTML or scene JSON → `scene_embedded.h`, and each `<img>` → `sd_card/assets/<name>.bin` |
| `link.sh`, `build.sh` | link the player's C in, compile and upload with arduino-cli |

For a clock kept elsewhere (a server, a sensor), skip `panel_play()` and call
`panel_draw(scene_time_ms)` before `panel_update()`.

## Pictures from the SD card

Pictures are not compiled into the firmware. `embed_scene.py` fits each
`<img>` to its box on the host, converts it to LVGL's binary image format and
writes it to `sd_card/assets/<name>.bin`, named after the source file:

```bash
python embed_scene.py scene.html     # writes scene_embedded.h and sd_card/assets/
# copy the contents of sd_card/ to the root of the card
```

The scene refers to each picture by that name, with its size and CRC32. When a
scene loads, the bridge checks every file; a missing file or one from another
build is not drawn, `panel_missing_assets()` counts it and `panel_error()` names
the first. The board header mounts the card at `/sd` (`board_sd_begin()`); a
board without a confirmed card wiring returns false, and its pictures report as
missing.

A decoded picture stays in LVGL's image cache (1 MB ceiling in `lv_conf.h`),
because the scene is drawn strip by strip. On a board without PSRAM, keep
pictures small.

## Where the C comes from

The evaluator and renderer live in
[`mementum-lcd`](https://github.com/carstenbund/mementum-lcd) (`poc/player/`)
until `drm_scene_ir` is versioned, as does the LVGL checkout they are tested
against. `link.sh` and `build.sh` take them from `$MEMENTUM_SRC`, defaulting to
a sibling checkout. Nothing is copied.

```bash
cd scene_player
python embed_scene.py scene.html      # needs drm_composer
./build.sh /dev/ttyACM0               # needs arduino-cli
```

## What is not verified

Nothing here has run on a board. The bridge, the default board header and the
embedded scene have been compiled and run on a Linux host against the same LVGL
9.5 and player, with the Arduino and GFX calls stubbed and the panel recorded:
the frames are right (within 4 of 255 levels of the full-frame canvas render, at
text edges only, with no seam where a stroke crosses a strip), a finished scene
sends nothing to the panel, and reloading leaks nothing. Pictures were checked
the same way, through the real composer conversion, CRC check, LVGL decoder and
image cache: drawn from files at the right colours and alpha, a file with one
changed byte left out and reported, and back when restored.

Still open: the display driver itself, frame time and memory on the chip, and
every board's SD wiring — the JC3248W535 and 1.47B pins come from vendor and
community pin lists, and the C6 and Sunton boards have no card support yet.

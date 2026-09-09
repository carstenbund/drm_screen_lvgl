# drm_screen_lvgl

LVGL renderer plugin for [`drm_screen`](https://github.com/carstenbund/drm_screen).

`drm_screen` owns named, persistent, z-ordered layers and a command API. This
package is one implementation of the thing that draws them:

```
rgba   commands → numpy layers → whole-frame blend → RGBA→BGRA → drm_display → DRM/KMS
lvgl   commands → LVGL objects → LVGL's dirty-area composite            → DRM/KMS
```

Same commands, same layers, same service. Two things change:

- **Only what moved is drawn.** LVGL composites its own dirty rectangles and
  presents them; nothing recomposites a whole screen because a badge moved.
- **A layer can hold a scene.** `PlaceScene` gives a layer paths instead of
  pixels. They are drawn at the panel's own resolution, evaluated at the scene
  time the service passes down, and never rasterised into a buffer that has to
  be carried anywhere. A 1.4 KB scene fills 1920×1080 in ~1.5 ms.

Where LVGL is not available, `drm_screen` keeps composing with numpy. That is
the point of it being a plugin.

## Part of the drm_stack

Each package installs and runs on its own:

| Package | Role |
|---|---|
| [`drm-composer`](https://github.com/carstenbund/drm_composer) | screen-HTML → layer commands |
| [`drm-screen`](https://github.com/carstenbund/drm_screen) | layers → composited frame |
| **`drm-screen-lvgl`** | layers → LVGL → DRM/KMS, and scene layers · *this package* |
| [`drm-display`](https://github.com/carstenbund/drm_display) | frame → DRM/KMS pixels |

Full stack and integration demo:
[`drm_stack`](https://github.com/carstenbund/drm_stack) (Stage 4b).

## Install

```bash
pip install drm-screen-lvgl
```

No Python dependencies. It needs the native library described below, and
`drm_screen_lvgl.is_available()` says whether one was found — so an application
can fall back to the RGBA compositor rather than fail.

Installing it *is* the selection — `drm_screen` discovers it through the
`drm_screen.renderers` entry point:

```python
from drm_screen import ScreenService
from drm_screen.commands import CreateLayer, PlaceScene

service = ScreenService(renderer="lvgl")
service.submit([
    CreateLayer("writing", 1920, 1080, z=10),
    PlaceScene("writing", open("scene.json", "rb").read()),
])
service.start()
```

An existing deployment moves onto it with no code change at all:

```bash
DRM_SCREEN_RENDERER=lvgl python your_app.py
```

## The native library

The renderer is ctypes over `libdrm_screen_lvgl` — LVGL, ThorVG and the scene
evaluator, in portable C, the same sources that run on an ESP32-S3. That C is
developed and tested in [`mementum-lcd`](https://github.com/carstenbund/mementum-lcd)
while the scene format it draws is being settled, and it is found in this order:

| | |
|---|---|
| `DRM_SCREEN_LVGL_LIB` | an explicit path to the library, which wins |
| this package's directory | a wheel that shipped one |
| `MEMENTUM_SRC` | a `mementum-lcd` checkout with `poc/host-player/build/` built |

```bash
export MEMENTUM_SRC=~/code/mementum-lcd
make -C $MEMENTUM_SRC/poc/host-player -j4 lib
```

`drm_screen_lvgl.is_available()` says whether a library was found, so an app
can fall back rather than fail.

## Scene layers

A scene is a document, not a picture: objects, paths, and animations evaluated
against a clock. `PlaceScene(name, scene)` hands one to a layer;
`StartRipple(name, origin=…)` disturbs it locally, for a finger on the glass.
See [`docs/scene-layers.md`](docs/scene-layers.md).

## License

**GPL-3.0-or-later**, matching `drm_screen`. For proprietary use that cannot
comply with the GPL, contact Carsten Bund <carstenbund@gmail.com>.

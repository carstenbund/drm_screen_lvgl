# Third-party licenses — drm-screen-lvgl

`drm-screen-lvgl` is licensed under **GPL-3.0-or-later** (see [LICENSE](LICENSE)).

It has **no Python dependencies** and bundles no third-party source code: the
package is ctypes over a native library that is built separately.

## The native library it binds

`libdrm_screen_lvgl` is compiled from
[`mementum-lcd`](https://github.com/carstenbund/mementum-lcd)'s `poc/player/`
while the scene format is being settled. That build links the following, none of
which is redistributed by this package. All are permissive and compatible with
GPL-3.0-or-later.

### LVGL — MIT
Copyright (c) 2021 LVGL Kft. <https://lvgl.io/>

### ThorVG — MIT
Copyright (c) 2020–2025 the ThorVG project. <https://www.thorvg.org/>
Ships inside LVGL and is used for the vector rasteriser.

### cJSON — MIT
Copyright (c) 2009–2017 Dave Gamble and cJSON contributors.
<https://github.com/DaveGamble/cJSON>

## Optional Python dependency (extra: `numpy`)

### numpy — BSD-3-Clause (AND 0BSD AND MIT AND Zlib AND CC0-1.0)
Copyright (c) 2005–2025, NumPy Developers. All rights reserved.
<https://numpy.org/> — needed only by `snapshot_rgba()`, which returns a frame
in the array form `drm_screen` speaks.

## Sibling packages

### drm-screen — same author, GPL-3.0-or-later
<https://github.com/carstenbund/drm_screen> — not a dependency: this package is
discovered *by* it, through the `drm_screen.renderers` entry point, and works
without it for anything that does not need the service.

---

No copyleft (GPL/AGPL/LGPL/MPL) dependencies are present.

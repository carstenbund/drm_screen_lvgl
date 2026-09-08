"""`drm_screen`'s LVGL renderer — a plugin, used where the platform has it.

`drm_screen` composites RGBA layers with numpy and hands one frame to
`drm_display`. That path is portable and stays the default. Where LVGL is
available this one does the same job differently:

    rgba   commands -> numpy layers -> whole-frame blend -> RGBA→BGRA
                    -> drm_display -> DRM/KMS
    lvgl   commands -> LVGL objects -> LVGL's dirty-area composite -> DRM/KMS

Same command records, same layer semantics, same service. Two things change.
Only what moved is redrawn and presented, and a layer can hold a **scene** --
paths, strokes and transforms drawn at the panel's own resolution, evaluated at
the scene time the service passes down, never rasterised into a buffer that has
to be carried anywhere.

    from drm_screen import ScreenService
    from drm_screen.commands import CreateLayer, PlaceScene

    service = ScreenService(renderer="lvgl")
    service.submit([
        CreateLayer("writing", 1920, 1080, z=10),
        PlaceScene("writing", open("scene.json", "rb").read()),
    ])
    service.start()

Registered as `drm_screen.renderers` entry point `lvgl`, so installing this
package is all the selection there is; `DRM_SCREEN_RENDERER=lvgl` moves an
existing deployment onto it without a code change.
"""

from drm_screen_lvgl.binding import LvglError, LvglScreen, is_available, library_path
from drm_screen_lvgl.renderer import LvglRenderer

__all__ = ["LvglRenderer", "LvglScreen", "LvglError", "is_available", "library_path"]
__version__ = "0.1.0"

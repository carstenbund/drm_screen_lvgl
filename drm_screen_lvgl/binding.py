"""ctypes over `libdrm_screen_lvgl` — layers held by LVGL.

The library is plain C: a stack of LVGL objects, one per layer, presented
through whatever display driver LVGL was built with (DRM/KMS on Linux, a panel
on an MCU, a memory buffer for tests). Nothing here has policy in it; every
method is one `drm_screen` command passed across, and the one addition --
:meth:`set_scene` -- is what lets a layer hold primitives instead of pixels.

Where the library comes from, in order:

    DRM_SCREEN_LVGL_LIB       an explicit path, which wins
    <this package>/           a wheel that shipped one
    MEMENTUM_SRC/poc/host-player/build/libmementum_player.so

The last entry is deliberate and temporary: the C is developed and tested in
`mementum-lcd`, where the scene format it draws is still being settled. It
moves here when that format is versioned (see `docs/scene-layers.md`).
"""

from __future__ import annotations

import ctypes
import os
from ctypes import c_char_p, c_double, c_int, c_size_t, c_void_p

__all__ = ["LvglScreen", "LvglError", "library_path", "is_available"]

_LIB_NAMES = ("libdrm_screen_lvgl.so", "libmementum_player.so")


class LvglError(RuntimeError):
    """The library refused something. Carries its own message."""


def library_path() -> str | None:
    explicit = os.environ.get("DRM_SCREEN_LVGL_LIB")
    if explicit:
        return explicit if os.path.exists(explicit) else None

    here = os.path.dirname(os.path.abspath(__file__))
    for name in _LIB_NAMES:
        candidate = os.path.join(here, name)
        if os.path.exists(candidate):
            return candidate

    source = os.environ.get("MEMENTUM_SRC")
    if source:
        candidate = os.path.join(source, "poc", "host-player", "build",
                                 "libmementum_player.so")
        if os.path.exists(candidate):
            return candidate
    return None


def is_available() -> bool:
    return library_path() is not None


_library = None


def _load():
    """One handle per process: LVGL keeps global state and is initialised once,
    so this is a singleton by necessity rather than by preference."""
    global _library
    if _library is not None:
        return _library

    path = library_path()
    if path is None:
        raise LvglError(
            "libdrm_screen_lvgl not found; set DRM_SCREEN_LVGL_LIB to it "
            "(or MEMENTUM_SRC to a mementum-lcd checkout that has built one)"
        )
    lib = ctypes.CDLL(path)
    lib.mm_screen_create.argtypes = [c_int, c_int, c_char_p]
    lib.mm_screen_create.restype = c_void_p
    lib.mm_screen_destroy.argtypes = [c_void_p]
    lib.mm_screen_width.argtypes = [c_void_p]
    lib.mm_screen_width.restype = c_int
    lib.mm_screen_height.argtypes = [c_void_p]
    lib.mm_screen_height.restype = c_int
    lib.mm_screen_layer_create.argtypes = [
        c_void_p, c_char_p, c_int, c_int, c_int, c_int, c_int, c_int, c_double, c_int, c_char_p
    ]
    lib.mm_screen_layer_create.restype = c_int
    for name in ("delete", "clear"):
        fn = getattr(lib, f"mm_screen_layer_{name}")
        fn.argtypes = [c_void_p, c_char_p]
        fn.restype = c_int
    lib.mm_screen_layer_visible.argtypes = [c_void_p, c_char_p, c_int]
    lib.mm_screen_layer_visible.restype = c_int
    lib.mm_screen_layer_position.argtypes = [c_void_p, c_char_p, c_int, c_int]
    lib.mm_screen_layer_position.restype = c_int
    lib.mm_screen_layer_z.argtypes = [c_void_p, c_char_p, c_int]
    lib.mm_screen_layer_z.restype = c_int
    lib.mm_screen_layer_opacity.argtypes = [c_void_p, c_char_p, c_double]
    lib.mm_screen_layer_opacity.restype = c_int
    lib.mm_screen_layer_interactive.argtypes = [c_void_p, c_char_p, c_int, c_char_p]
    lib.mm_screen_layer_interactive.restype = c_int
    lib.mm_screen_layer_blit.argtypes = [
        c_void_p, c_char_p, ctypes.POINTER(ctypes.c_uint8), c_int, c_int, c_int, c_int
    ]
    lib.mm_screen_layer_blit.restype = c_int
    lib.mm_screen_layer_scene.argtypes = [c_void_p, c_char_p, c_char_p]
    lib.mm_screen_layer_scene.restype = c_int
    lib.mm_screen_layer_offset.argtypes = [c_void_p, c_char_p, c_double]
    lib.mm_screen_layer_offset.restype = c_int
    lib.mm_screen_layer_ripple.argtypes = [c_void_p, c_char_p] + [c_double] * 7
    lib.mm_screen_layer_ripple.restype = c_int
    lib.mm_screen_hit_test.argtypes = [c_void_p, c_int, c_int]
    lib.mm_screen_hit_test.restype = c_char_p
    lib.mm_screen_render.argtypes = [c_void_p, c_double]
    lib.mm_screen_render.restype = c_int
    lib.mm_screen_snapshot.argtypes = [c_void_p, ctypes.POINTER(ctypes.c_uint8), c_size_t]
    lib.mm_screen_snapshot.restype = c_int
    lib.mm_screen_last_render_ms.argtypes = [c_void_p]
    lib.mm_screen_last_render_ms.restype = c_double
    lib.mm_screen_error.restype = c_char_p
    _library = lib
    return lib


def _encode(value) -> bytes | None:
    if value is None:
        return None
    return value.encode("utf-8") if isinstance(value, str) else bytes(value)


class LvglScreen:
    """Named layers, composited and presented by LVGL.

    `display="drm"` takes the panel through DRM/KMS and needs no size -- the
    mode decides it. `display="memory"` composites into a buffer :meth:`snapshot`
    can read, which is what a headless test or a capture sink uses.
    """

    def __init__(self, width: int = 0, height: int = 0, display: str = "drm"):
        self._lib = _load()
        handle = self._lib.mm_screen_create(int(width), int(height), display.encode("utf-8"))
        if not handle:
            raise LvglError(self._error())
        self._handle = handle
        self.display = display
        self.width = int(self._lib.mm_screen_width(handle))
        self.height = int(self._lib.mm_screen_height(handle))
        self._snapshot_buffer = None
        self.layers: dict[str, dict] = {}

    def _error(self) -> str:
        message = self._lib.mm_screen_error()
        return message.decode("utf-8", "replace") if message else "unknown error"

    def _check(self, rc: int) -> None:
        if rc != 0:
            raise LvglError(self._error())

    def close(self) -> None:
        if getattr(self, "_handle", None):
            self._lib.mm_screen_destroy(self._handle)
            self._handle = None

    # -- the drm_screen command set -------------------------------------

    def create_layer(self, name, width, height, x=0, y=0, z=0, visible=True,
                     opacity=1.0, interactive=False, hit_id=None) -> None:
        self._check(self._lib.mm_screen_layer_create(
            self._handle, _encode(name), int(width), int(height), int(x), int(y), int(z),
            1 if visible else 0, float(opacity), 1 if interactive else 0, _encode(hit_id),
        ))
        self.layers[name] = dict(name=name, width=width, height=height, x=x, y=y, z=z,
                                 visible=visible, opacity=opacity, interactive=interactive,
                                 hit_id=hit_id, scene=False, offset=0.0)

    def delete_layer(self, name) -> None:
        self._check(self._lib.mm_screen_layer_delete(self._handle, _encode(name)))
        self.layers.pop(name, None)

    def clear_layer(self, name) -> None:
        self._check(self._lib.mm_screen_layer_clear(self._handle, _encode(name)))

    def set_visible(self, name, visible) -> None:
        self._check(self._lib.mm_screen_layer_visible(self._handle, _encode(name),
                                                      1 if visible else 0))
        self.layers[name]["visible"] = visible

    def set_position(self, name, x, y) -> None:
        self._check(self._lib.mm_screen_layer_position(self._handle, _encode(name),
                                                       int(x), int(y)))
        self.layers[name].update(x=x, y=y)

    def set_z(self, name, z) -> None:
        self._check(self._lib.mm_screen_layer_z(self._handle, _encode(name), int(z)))
        self.layers[name]["z"] = z

    def set_opacity(self, name, opacity) -> None:
        self._check(self._lib.mm_screen_layer_opacity(self._handle, _encode(name),
                                                      float(opacity)))
        self.layers[name]["opacity"] = opacity

    def set_interactive(self, name, interactive=True, hit_id=None) -> None:
        self._check(self._lib.mm_screen_layer_interactive(
            self._handle, _encode(name), 1 if interactive else 0, _encode(hit_id)))
        self.layers[name].update(interactive=interactive, hit_id=hit_id)

    def blit(self, name, rgba, width, height, x=0, y=0) -> None:
        """RGBA8888 bytes into a layer. Accepts bytes or anything with
        `tobytes()`, so a numpy array works without importing numpy here."""
        if hasattr(rgba, "tobytes"):
            rgba = rgba.tobytes()
        data = (ctypes.c_uint8 * len(rgba)).from_buffer_copy(rgba)
        self._check(self._lib.mm_screen_layer_blit(
            self._handle, _encode(name), data, int(width), int(height), int(x), int(y)))

    def set_scene(self, name, scene) -> None:
        """The layer now holds a scene: paths drawn at the panel's resolution
        every frame, never rasterised into a buffer that has to be carried."""
        self._check(self._lib.mm_screen_layer_scene(self._handle, _encode(name),
                                                    _encode(scene)))
        if name in self.layers:
            self.layers[name]["scene"] = scene is not None

    def set_scene_offset(self, name, offset_ms) -> None:
        """Shift one layer's own clock against the screen's.

        The screen is rendered at a single time; a layer with an offset is
        evaluated at `scene_time - offset`. That is how units standing on one
        wall start one after another, or hold different moments of the same
        scene, without anything being rendered twice."""
        self._check(self._lib.mm_screen_layer_offset(self._handle, _encode(name),
                                                     float(offset_ms)))
        if name in self.layers:
            self.layers[name]["offset"] = float(offset_ms)

    def add_ripple(self, name, origin, start=0.0, amplitude=6.0, wavelength=120.0,
                   speed=0.35, life_ms=1400.0, width=260.0) -> None:
        self._check(self._lib.mm_screen_layer_ripple(
            self._handle, _encode(name), float(origin), float(start), float(amplitude),
            float(wavelength), float(speed), float(life_ms), float(width)))

    def hit_test(self, x, y) -> str | None:
        hit = self._lib.mm_screen_hit_test(self._handle, int(x), int(y))
        return hit.decode("utf-8") if hit else None

    # -- present --------------------------------------------------------

    def render(self, scene_time_ms: float = 0.0) -> None:
        self._check(self._lib.mm_screen_render(self._handle, float(scene_time_ms)))

    @property
    def last_render_ms(self) -> float:
        return float(self._lib.mm_screen_last_render_ms(self._handle))

    def snapshot(self) -> bytes:
        """The presented frame as RGBA bytes. Memory backend only -- on DRM the
        frame is in the scanout buffer and was never ours to copy."""
        needed = self.width * self.height * 4
        if self._snapshot_buffer is None:
            self._snapshot_buffer = (ctypes.c_uint8 * needed)()
        self._check(self._lib.mm_screen_snapshot(self._handle, self._snapshot_buffer, needed))
        return bytes(self._snapshot_buffer)

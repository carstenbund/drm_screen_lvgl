"""The renderer itself: `drm_screen`'s command records, applied to LVGL.

Dispatch is by class *name*, never by identity. A command record may come from
`drm_screen.commands`, from a version of it older than this package, or across
a socket from a machine with neither -- and it means the same thing to the
screen either way. Fields are read with defaults for the same reason: the
record has grown over releases and an older composer's batch must still apply.
"""

from __future__ import annotations

from drm_screen_lvgl.binding import LvglError, LvglScreen

__all__ = ["LvglRenderer", "default_cursor"]

CAP_LAYERS = "layers"
CAP_RAW_BUFFER = "raw_buffer"
CAP_HIT_TEST = "hit_test"
CAP_SNAPSHOT = "snapshot"
CAP_SCENE = "scene"
CAP_PARTIAL_UPDATE = "partial_update"

_POINTER_NAME = "__pointer__"
_POINTER_Z = 1_000_000
_CURSOR_R = 11


def default_cursor() -> tuple[bytes, int, int]:
    """`drm_screen`'s cursor -- white ring, red centre -- as RGBA bytes.

    Taken from `drm_screen` when it is installed, so the pointer looks the same
    on either renderer; drawn here otherwise, because this package must run on
    a device that has no numpy.
    """
    try:
        from drm_screen.commands import default_cursor as _cursor

        image = _cursor()
        return image.tobytes(), int(image.shape[1]), int(image.shape[0])
    except Exception:
        size = _CURSOR_R * 2 + 3
        centre = size // 2
        buffer = bytearray(size * size * 4)
        for y in range(size):
            for x in range(size):
                distance = ((x - centre) ** 2 + (y - centre) ** 2) ** 0.5
                index = (y * size + x) * 4
                if distance <= 2.0:
                    buffer[index:index + 4] = bytes((255, 80, 80, 255))
                elif _CURSOR_R - 1.5 <= distance <= _CURSOR_R + 0.5:
                    buffer[index:index + 4] = bytes((255, 255, 255, 255))
        return bytes(buffer), size, size


class LvglRenderer:
    """A `drm_screen.Renderer` backed by LVGL.

    `display="drm"` presents to the panel; `display="memory"` composites into a
    readable buffer, for tests and for capture. Construct it directly, or ask
    `drm_screen` for it by name -- `ScreenService(renderer="lvgl")`.
    """

    name = "lvgl"
    capabilities = frozenset({
        CAP_LAYERS, CAP_RAW_BUFFER, CAP_HIT_TEST, CAP_SNAPSHOT,
        CAP_SCENE, CAP_PARTIAL_UPDATE,
    })

    @staticmethod
    def available() -> bool:
        """Installed is not the same as usable: without the native library
        this package is a package, and `drm_screen` should not offer it."""
        from drm_screen_lvgl.binding import is_available

        return is_available()

    def __init__(self, width: int = 0, height: int = 0, display: str = "drm",
                 screen: LvglScreen | None = None):
        # `display`, not `backend`: on the RGBA path a backend is a drm_display
        # adapter object, and the two would collide in `renderer_options`.
        self.screen = screen or LvglScreen(width, height, display)
        self.width = self.screen.width
        self.height = self.screen.height

    # -- Renderer protocol ----------------------------------------------

    @property
    def animating(self) -> bool:
        """True while any layer holds a scene. Such a screen is never
        finished: the picture is a function of time, so "nothing was
        submitted" does not mean "nothing changed"."""
        return any(layer["scene"] for layer in self.screen.layers.values())

    def apply(self, command) -> None:
        kind = type(command).__name__
        screen = self.screen

        if kind == "CreateLayer":
            screen.create_layer(
                command.name, command.width, command.height,
                getattr(command, "x", 0), getattr(command, "y", 0), getattr(command, "z", 0),
                getattr(command, "visible", True), getattr(command, "opacity", 1.0),
                getattr(command, "interactive", False), getattr(command, "hit_id", None),
            )
        elif kind == "DeleteLayer":
            screen.delete_layer(command.name)
        elif kind == "ClearLayer":
            screen.clear_layer(command.name)
        elif kind == "ShowLayer":
            screen.set_visible(command.name, True)
        elif kind == "HideLayer":
            screen.set_visible(command.name, False)
        elif kind == "SetPosition":
            screen.set_position(command.name, command.x, command.y)
        elif kind == "SetZ":
            screen.set_z(command.name, command.z)
        elif kind == "SetOpacity":
            screen.set_opacity(command.name, command.opacity)
        elif kind == "SetInteractive":
            screen.set_interactive(command.name, getattr(command, "interactive", True),
                                   getattr(command, "hit_id", None))
        elif kind == "PlaceRawBuffer":
            if getattr(command, "fmt", "RGBA8888") != "RGBA8888":
                raise LvglError(f"unsupported fmt {command.fmt!r}")
            screen.blit(command.name, command.data, command.width, command.height,
                        getattr(command, "x", 0), getattr(command, "y", 0))
        elif kind == "PlaceScene":
            screen.set_scene(command.name, command.scene)
        elif kind == "SetSceneOffset":
            screen.set_scene_offset(command.name, command.offset)
        elif kind == "StartRipple":
            screen.add_ripple(command.name, command.origin, getattr(command, "start", 0.0),
                              getattr(command, "amplitude", 6.0),
                              getattr(command, "wavelength", 120.0),
                              getattr(command, "speed", 0.35),
                              getattr(command, "life_ms", 1400.0),
                              getattr(command, "width", 260.0))
        elif kind == "SetPointer":
            self._pointer(command)
        else:
            raise TypeError(f"unknown command {command!r}")

    def present(self, scene_time_ms: float = 0.0) -> None:
        self.screen.render(scene_time_ms)

    def hit_test(self, x: int, y: int) -> str | None:
        return self.screen.hit_test(x, y)

    def snapshot_rgba(self):
        """The presented frame as a numpy (h, w, 4) array, for callers that
        speak `drm_screen`'s buffers. numpy is imported only here."""
        import numpy as np

        return np.frombuffer(self.screen.snapshot(), dtype=np.uint8).reshape(
            self.height, self.width, 4
        ).copy()

    def close(self) -> None:
        self.screen.close()

    # -- the pointer overlay --------------------------------------------

    def _pointer(self, command) -> None:
        """The reserved cursor layer: above everything, never hit-tested, moved
        straight from the touch controller without waiting for the app loop."""
        screen = self.screen
        if _POINTER_NAME not in screen.layers:
            image, width, height = default_cursor()
            screen.create_layer(_POINTER_NAME, width, height, z=_POINTER_Z,
                                visible=getattr(command, "visible", True))
            screen.blit(_POINTER_NAME, image, width, height)
        layer = screen.layers[_POINTER_NAME]
        screen.set_position(_POINTER_NAME, command.x - layer["width"] // 2,
                            command.y - layer["height"] // 2)
        screen.set_visible(_POINTER_NAME, getattr(command, "visible", True))

    @property
    def last_render_ms(self) -> float:
        return self.screen.last_render_ms

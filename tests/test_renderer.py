"""The plugin, against the real library where there is one.

Everything that does not need the native library is checked unconditionally:
the renderer declares what it can do, dispatches command records by name, and
accepts the fields an older `drm_screen` record carries. The rest runs only
where `libdrm_screen_lvgl` was found, because a machine without it must still
be able to run the suite -- that is the whole premise of a plugin.
"""

import pytest

from drm_screen_lvgl import LvglRenderer, is_available
from drm_screen_lvgl.renderer import CAP_SCENE, default_cursor

pytestmark = pytest.mark.skipif(
    not is_available(),
    reason="libdrm_screen_lvgl not found; set DRM_SCREEN_LVGL_LIB or MEMENTUM_SRC",
)

W, H = 120, 80
RED = (220, 60, 60, 255)


def solid(width, height, rgba):
    return bytes(rgba) * (width * height)


def pixel(frame: bytes, width: int, x: int, y: int):
    index = (y * width + x) * 4
    return tuple(frame[index:index + 3])


@pytest.fixture
def renderer():
    renderer = LvglRenderer(W, H, display="memory")
    yield renderer
    renderer.close()


class Command:
    """A command record from somewhere else -- the point being that the
    renderer never asks where."""

    def __init__(self, kind, **fields):
        self.__class__ = type(kind, (Command,), {})
        self.__dict__.update(fields)


def test_it_declares_what_it_can_do():
    assert CAP_SCENE in LvglRenderer.capabilities


def test_a_command_record_is_taken_by_name_not_by_type(renderer):
    renderer.apply(Command("CreateLayer", name="box", width=40, height=20, x=10, y=10))
    renderer.apply(Command("PlaceRawBuffer", name="box", width=40, height=20,
                           data=solid(40, 20, RED)))
    renderer.present()

    frame = renderer.screen.snapshot()
    assert pixel(frame, W, 20, 15) == RED[:3]
    assert pixel(frame, W, 5, 5) == (0, 0, 0)


def test_an_older_record_still_applies(renderer):
    """`CreateLayer` grew `interactive`/`hit_id` after it shipped; a batch from
    before that must not be refused."""
    renderer.apply(Command("CreateLayer", name="box", width=40, height=20))
    renderer.present()

    assert "box" in renderer.screen.layers


def test_z_and_visibility_behave_as_drm_screen_documents(renderer):
    renderer.apply(Command("CreateLayer", name="under", width=W, height=H, z=1))
    renderer.apply(Command("CreateLayer", name="over", width=W, height=H, z=2))
    renderer.apply(Command("PlaceRawBuffer", name="under", width=W, height=H,
                           data=solid(W, H, RED)))
    renderer.apply(Command("PlaceRawBuffer", name="over", width=W, height=H,
                           data=solid(W, H, (20, 200, 120, 255))))
    renderer.present()
    assert pixel(renderer.screen.snapshot(), W, 60, 40) == (20, 200, 120)

    renderer.apply(Command("HideLayer", name="over"))
    renderer.present()
    assert pixel(renderer.screen.snapshot(), W, 60, 40) == RED[:3]


def test_hit_testing_finds_the_topmost_interactive_layer(renderer):
    renderer.apply(Command("CreateLayer", name="under", width=60, height=60, x=0, y=0,
                           z=1, interactive=True, hit_id="under"))
    renderer.apply(Command("CreateLayer", name="over", width=60, height=60, x=0, y=0,
                           z=5, interactive=True, hit_id="over"))

    assert renderer.hit_test(10, 10) == "over"
    assert renderer.hit_test(100, 70) is None


def test_the_pointer_overlay_is_reserved_and_on_top(renderer):
    renderer.apply(Command("SetPointer", x=60, y=40, visible=True))
    renderer.present()

    assert "__pointer__" in renderer.screen.layers
    assert renderer.screen.layers["__pointer__"]["z"] == 1_000_000
    assert renderer.hit_test(60, 40) is None       # a cursor is not a target


def test_a_scene_layer_animates_without_being_asked_again(renderer):
    """Time is a change even when no command is."""
    import json

    scene = json.dumps({
        "version": 1, "id": 1, "name": "one-line", "width": W, "height": H,
        "fit": "contain", "duration": 2000,
        "layers": [{"id": "ink", "z": 10, "objects": [{
            "type": "path", "id": "line", "d": "M 10 40 L 110 40",
            "stroke": "#ffffff", "stroke_width": 3, "progress": 0,
        }]}],
        "animations": [{"target": "line", "property": "progress", "start": 0,
                        "duration": 2000, "from": 0, "to": 1, "easing": "linear"}],
    }).encode()

    renderer.apply(Command("CreateLayer", name="scene", width=W, height=H))
    renderer.apply(Command("PlaceScene", name="scene", scene=scene))
    assert renderer.animating

    renderer.present(0.0)
    early = renderer.screen.snapshot()
    renderer.present(1800.0)
    late = renderer.screen.snapshot()

    assert early != late, "a scene layer must be a function of the scene time"


def test_the_cursor_is_a_cursor():
    image, width, height = default_cursor()
    assert width == height and len(image) == width * height * 4

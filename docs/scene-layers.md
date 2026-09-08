# Scene layers

A bitmap is finished. That is the whole difficulty: a layer of pixels cannot be
half a line, so anything that is *drawn* — a stroke arriving, a symbol being
written — has to be re-rasterised and re-sent, frame after frame, by whoever
made it.

A scene layer is a description instead. `PlaceScene` sends it once; the renderer
evaluates it against the clock every frame and draws the result at the panel's
own resolution.

```python
service.submit([
    CreateLayer("writing", 1920, 1080, z=10),
    PlaceScene("writing", scene_json),
])
```

## The document

`drm_scene_ir` — the same format the ESP32 player loads, so a panel and a Pi
draw the same picture from the same bytes.

```json
{
  "version": 1,
  "name": "one-line",
  "width": 800, "height": 480,
  "fit": "contain",
  "duration": 3000,
  "layers": [
    { "id": "ink", "z": 10, "objects": [
      { "type": "path", "id": "rule", "d": "M 60 240 L 740 240",
        "stroke": "#e8e8f0", "stroke_width": 4, "progress": 0 } ] }
  ],
  "animations": [
    { "target": "rule", "property": "progress", "start": 0,
      "duration": 3000, "from": 0, "to": 1, "easing": "linear" }
  ]
}
```

`width`/`height` are the *design* size and `fit` maps it onto whatever panel is
present, so one document is correct on a 450×250 LCD and on a 1920×1080 screen.

`progress` is the fraction of the path's ordered length that has been drawn.
Animate it and the line draws itself — that is the property a bitmap cannot
hold.

## Time

The renderer draws the scene at the `scene_time_ms` the service passes down:

```python
service = ScreenService(renderer="lvgl", clock=shared_now)
```

Nothing accumulates. A frame is a pure function of the time it was asked for, so
a dropped frame costs nothing and two screens on one clock agree without
talking to each other.

## Ripples

`StartRipple(name, origin=…)` disturbs a scene layer's ink locally — a finger on
the glass, or somebody else's finger relayed. Transient by design: a ripple that
arrives too late is not shown, and nothing has to recover.

## Where the format is defined

`mementum-lcd` — with the C evaluator, the conformance suite that binds it to a
Python reference, and the authoring tools that emit it. `drm_composer` emits it
for a layer of `<path>` elements. This package only draws it.

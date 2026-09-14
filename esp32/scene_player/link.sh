#!/bin/sh
# The player's C lives in mementum-lcd (poc/player/) until drm_scene_ir is
# versioned, and the Arduino IDE only compiles what is in the sketch folder.
# Symlink rather than copy: a copy is a second evaluator waiting to happen.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
MEMENTUM_SRC="${MEMENTUM_SRC:-$here/../../../mementum-lcd}"
player="$MEMENTUM_SRC/poc/player"
cjson="$MEMENTUM_SRC/third_party/cJSON"

[ -d "$player" ] || { echo "no player at $player -- set MEMENTUM_SRC to a mementum-lcd checkout" >&2; exit 1; }
[ -f "$cjson/cJSON.c" ] || { echo "cJSON not fetched: run $MEMENTUM_SRC/poc/host-player/fetch-cjson.sh" >&2; exit 1; }

for source in easing evaluator geometry ripple scene_json render_lvgl; do
    ln -sf "$player/$source.c" "$here/$source.c"
    ln -sf "$player/$source.h" "$here/$source.h"
done
ln -sf "$player/scene_model.h" "$here/scene_model.h"
ln -sf "$cjson/cJSON.c" "$here/cJSON.c"
ln -sf "$cjson/cJSON.h" "$here/cJSON.h"
echo "linked the player from $player"

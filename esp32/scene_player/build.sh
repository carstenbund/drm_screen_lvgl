#!/bin/sh
# Compile, and optionally upload and monitor, with arduino-cli.
#
#   ./build.sh                 compile only
#   ./build.sh /dev/ttyACM0    compile, upload, monitor
#
# FQBN/OPTS default to the board board_config.h selects by default (Guition
# JC3248W535); src/boards/README.md lists the settings for the others.
set -eu

here="$(cd "$(dirname "$0")" && pwd)"
port="${1:-}"
MEMENTUM_SRC="${MEMENTUM_SRC:-$here/../../../mementum-lcd}"
export MEMENTUM_SRC

FQBN="${FQBN:-esp32:esp32:esp32s3}"
OPTS="${OPTS:-PSRAM=opi,PartitionScheme=huge_app,FlashSize=16M,CPUFreq=240,USBMode=hwcdc,CDCOnBoot=cdc}"

command -v arduino-cli >/dev/null || {
    echo "arduino-cli not found: https://arduino.github.io/arduino-cli/" >&2
    exit 1
}

sh "$here/link.sh"

echo "== libraries =="
# The panel driver, pinned as mementum-lcd CI pins it; 1.6.5+ builds against
# ESP32 Arduino core 3.3.6+.
arduino-cli lib install "GFX Library for Arduino@1.6.7"
# mementum-lcd's vendored LVGL, patches included -- the LVGL the player's host
# tests run against. lv_conf.h goes beside the library folder, where LVGL looks.
libraries="${ARDUINO_LIBRARIES:-$HOME/Arduino/libraries}"
mkdir -p "$libraries"
ln -sfn "$MEMENTUM_SRC/third_party/lvgl" "$libraries/lvgl"
ln -sfn "$here/lv_conf.h" "$libraries/lv_conf.h"

echo "== compile =="
arduino-cli compile --fqbn "$FQBN:$OPTS" --warnings default "$here"

if [ -n "$port" ]; then
    echo "== upload to $port =="
    arduino-cli upload --fqbn "$FQBN:$OPTS" -p "$port" "$here"
    echo "== monitor =="
    arduino-cli monitor -p "$port" -c baudrate=115200
fi

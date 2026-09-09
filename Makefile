# Makefile for drm-screen-lvgl — PyPI build & publish helper.
#
# Pure Python: the package is ctypes over a native library that is built
# elsewhere (see README), so there is nothing to compile here and the wheel is
# py3-none-any. These targets wrap the standard build/twine workflow, and are
# the same ones drm-screen uses.
#
# Requires:  pip install build twine
#
# Targets:
#   make build         - build sdist + wheel into dist/
#   make check         - twine check the built artifacts
#   make publish-test  - upload to TestPyPI
#   make publish       - upload to PyPI
#   make lib           - build the native library from a mementum-lcd checkout
#   make test          - run the package's own tests against that library
#   make clean         - remove build artifacts
#   make info          - show package name + version

# Prefer the stack venv (which has build + twine); fall back to system python3.
PY ?= $(firstword $(wildcard ../.venv/bin/python3) $(wildcard ../mementum-lcd/.venv/bin/python3) python3)

# Where the native library is built from. Only needed for `make lib` / `make test`.
MEMENTUM_SRC ?= ../mementum-lcd

.PHONY: build check publish publish-test clean info lib test

build: clean
	$(PY) -m build

check: build
	$(PY) -m twine check dist/*

publish-test: check
	$(PY) -m twine upload --repository testpypi dist/*

publish: check
	$(PY) -m twine upload dist/*

lib:
	@test -d "$(MEMENTUM_SRC)/poc/host-player" || \
	  { echo "set MEMENTUM_SRC to a mementum-lcd checkout"; exit 1; }
	$(MAKE) -C "$(MEMENTUM_SRC)/poc/host-player" -j4 lib
	@echo "built $(MEMENTUM_SRC)/poc/host-player/build/libdrm_screen_lvgl.so"

test:
	MEMENTUM_SRC="$(abspath $(MEMENTUM_SRC))" $(PY) -m pytest tests -q

clean:
	rm -rf dist build *.egg-info

info:
	@grep -E '^(name|version)' pyproject.toml

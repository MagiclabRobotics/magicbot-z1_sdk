#!/usr/bin/env bash
# Runs inside the Ubuntu 20.04 builder container.
set -euo pipefail

SDK_ROOT="/work"
BUILD_DIR="${MAGICBOT_Z1_SDK_BUILD:-$SDK_ROOT/build-focal}"
SCRIPT_DIR="$SDK_ROOT/example/python/viz_example"
PYTHON="/usr/bin/python3"

echo "==> 容器 Python: $($PYTHON --version)"

PYBIND_SO=""
for f in "$BUILD_DIR"/magicbot_z1_python.cpython-*.so; do
  if [[ -f "$f" ]]; then
    PYBIND_SO="$f"
    break
  fi
done

if [[ -z "$PYBIND_SO" ]]; then
  echo "==> 在容器内编译 SDK (Ubuntu 20.04 / glibc 2.31) ..."
  cmake -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$BUILD_DIR/install" \
    -DSDK_INSTALL=ON \
    -DPython3_EXECUTABLE="$PYTHON"
  cmake --build "$BUILD_DIR" --parallel "$(nproc)"
  cmake --install "$BUILD_DIR"
fi

export MAGICBOT_Z1_SDK_BUILD="$BUILD_DIR"
export MAGICBOT_VIZ_PYTHON="$PYTHON"
bash "$SCRIPT_DIR/build_viz.sh"

echo ""
echo "==> 容器内 glibc: $(ldd --version | head -1)"
echo "==> 产物: $SCRIPT_DIR/dist/magicbot_z1_viz"


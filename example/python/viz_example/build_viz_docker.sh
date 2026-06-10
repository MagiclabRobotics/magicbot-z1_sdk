#!/usr/bin/env bash
# Build magicbot_z1_viz inside Ubuntu 20.04 (glibc 2.31) for older Linux targets.
#
# Use this when the host is Ubuntu 22.04+ and the target machine reports:
#   GLIBC_2.35 not found (required by .../libpython3.10.so.1.0)
#
# Output:
#   example/python/viz_example/dist/magicbot_z1_viz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DOCKER_DIR="$SCRIPT_DIR/docker"
IMAGE_NAME="${MAGICBOT_VIZ_DOCKER_IMAGE:-magicbot-z1-viz-builder:focal}"

if ! command -v docker >/dev/null 2>&1; then
  echo "错误: 未找到 docker，请先安装 Docker。" >&2
  exit 1
fi

echo "==> 构建 Docker 镜像: $IMAGE_NAME"
docker build -t "$IMAGE_NAME" "$DOCKER_DIR"

echo "==> 在 Ubuntu 20.04 容器内编译 SDK 并打包 viz ..."
docker run --rm \
  -v "$SDK_ROOT:/work" \
  -e MAGICBOT_Z1_SDK_BUILD=/work/build-focal \
  "$IMAGE_NAME" \
  bash /work/example/python/viz_example/docker/build_inside.sh

echo ""
echo "完成。可在 glibc >= 2.31 的系统上运行:"
echo "  $SCRIPT_DIR/dist/magicbot_z1_viz"
echo ""
echo "目标机检查 glibc 版本: ldd --version"


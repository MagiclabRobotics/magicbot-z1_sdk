#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MagicBot Z1 head RGBD depth image visualizer.

Subscribes to head_rgbd_depth_image via the SDK and displays a false-color depth map.
"""

from __future__ import annotations

import argparse
import logging
import queue
import signal
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk
from typing import Optional

import numpy as np

_SDK_BUILD = Path(__file__).resolve().parents[2] / "build"
if _SDK_BUILD.is_dir():
    sys.path.insert(0, str(_SDK_BUILD))

try:
    import magicbot_z1_python as magicbot
except ImportError as exc:
    raise SystemExit(
        "Cannot import magicbot_z1_python. Build the SDK and run:\n"
        "  export PYTHONPATH=/path/to/magicbot_z1_sdk/build:$PYTHONPATH\n"
        f"  ({exc})"
    ) from exc

try:
    import cv2
    from PIL import Image, ImageTk

    _HAS_VIZ_DEPS = True
except ImportError:
    _HAS_VIZ_DEPS = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

APP_BG = "#eef2f7"
CARD_BG = "#ffffff"
HEADER_BG = "#172554"
HEADER_FG = "#f8fafc"
PANEL_BG = "#0f172a"
PANEL_FG = "#94a3b8"


@dataclass
class DepthFrameMeta:
    width: int = 0
    height: int = 0
    encoding: str = ""
    frame_count: int = 0
    fps: float = 0.0
    min_depth_m: float = 0.0
    max_depth_m: float = 0.0
    valid_ratio: float = 0.0


def _dtype_for_encoding(encoding: str, is_bigendian: bool) -> np.dtype:
    enc = (encoding or "").lower()
    endian = ">" if is_bigendian else "<"
    if enc in ("16uc1", "mono16"):
        return np.dtype(f"{endian}u2")
    if enc in ("32fc1",):
        return np.dtype(f"{endian}f4")
    if enc in ("mono8", "8uc1"):
        return np.dtype(np.uint8)
    return np.dtype(f"{endian}u2")


def _reshape_image_buffer(
    data: bytes, height: int, width: int, dtype: np.dtype, step: int
) -> np.ndarray:
    elem_size = int(dtype.itemsize)
    row_bytes = width * elem_size
    if step <= 0 or step == row_bytes:
        return np.frombuffer(data, dtype=dtype, count=height * width).reshape(
            height, width
        )

    rows = []
    raw = np.frombuffer(data, dtype=np.uint8)
    for row in range(height):
        start = row * step
        chunk = raw[start : start + row_bytes]
        rows.append(np.frombuffer(chunk, dtype=dtype, count=width))
    return np.vstack(rows)


def _is_compressed_depth(img: magicbot.Image) -> bool:
    enc = (img.encoding or "").lower()
    if img.height <= 0 or img.width <= 0:
        return True
    if "compressed" in enc:
        return True
    return enc in ("png", "jpeg", "jpg", "webp", "bmp")


def _decode_compressed_depth_array(data: bytes) -> np.ndarray:
    buffer = np.frombuffer(data, dtype=np.uint8)
    raw = cv2.imdecode(buffer, cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise ValueError("cv2.imdecode returned None for compressed depth image")
    if raw.ndim == 3:
        raw = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
    return raw


def decode_depth_meters(img: magicbot.Image) -> np.ndarray:
    """Decode SDK Image to depth in meters (float32, HxW)."""
    if _is_compressed_depth(img):
        raw = _decode_compressed_depth_array(bytes(img.data)).astype(np.float32)
        enc = (img.encoding or "").lower()
        if "32fc1" in enc or raw.dtype == np.float32:
            return raw
        if raw.dtype == np.uint16 or "16uc1" in enc or "mono16" in enc:
            return raw / 1000.0
        if raw.dtype == np.uint8 or "mono8" in enc or "8uc1" in enc:
            return raw / 255.0
        return raw

    dtype = _dtype_for_encoding(img.encoding, img.is_bigendian)
    depth = _reshape_image_buffer(
        bytes(img.data), img.height, img.width, dtype, img.step
    ).astype(np.float32)

    enc = (img.encoding or "").lower()
    if enc in ("16uc1", "mono16"):
        depth /= 1000.0
    elif enc in ("mono8", "8uc1"):
        depth /= 255.0
    return depth


DEPTH_COLOR_MODES = ("jet", "grayscale", "turbo")


def _depth_to_scaled_uint8(depth_m: np.ndarray, max_depth_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Map depth to 0–255: higher value = closer (near=255, far=0)."""
    valid = depth_m > 0
    scaled = np.zeros(depth_m.shape, dtype=np.uint8)
    if max_depth_m > 0 and np.any(valid):
        norm = np.clip(depth_m[valid] / max_depth_m, 0.0, 1.0)
        scaled[valid] = ((1.0 - norm) * 255.0).astype(np.uint8)
    return scaled, valid


def depth_to_display_rgb(
    depth_m: np.ndarray, max_depth_m: float, mode: str = "jet"
) -> np.ndarray:
    """Render depth for display. Default jet: near=red, far=blue (common depth convention)."""
    scaled, valid = _depth_to_scaled_uint8(depth_m, max_depth_m)
    mode = (mode or "jet").lower()

    if mode == "grayscale":
        rgb = np.stack([scaled, scaled, scaled], axis=-1)
        rgb[~valid] = 0
        return rgb

    colormap = cv2.COLORMAP_JET if mode == "jet" else cv2.COLORMAP_TURBO
    colored_bgr = cv2.applyColorMap(scaled, colormap)
    colored_bgr[~valid] = 0
    return cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2RGB)


class DepthVizApp:
    def __init__(self, root: tk.Tk, default_local_ip: str) -> None:
        self.root = root
        self.root.title("MagicBot Z1 Depth Visualizer")
        self.root.geometry("1080x760")
        self.root.minsize(900, 640)
        self.root.configure(background=APP_BG)

        self.robot: Optional[magicbot.MagicRobot] = None
        self.sensor: Optional[magicbot.SensorController] = None
        self.running = True
        self.streaming = False

        self.local_ip_var = tk.StringVar(value=default_local_ip)
        self.connect_status_var = tk.StringVar(value="Disconnected")
        self.max_depth_var = tk.StringVar(value="5.0")
        self.colormap_var = tk.StringVar(value="jet")
        self.stats_var = tk.StringVar(
            value=(
                "FPS: —  |  Frames: —  |  Resolution: —  |  Encoding: —  |  "
                "Depth range: —  |  Valid pixels: —"
            )
        )
        self.cursor_var = tk.StringVar(value="Cursor: —")

        self._frame_queue: queue.Queue = queue.Queue(maxsize=1)
        self._meta = DepthFrameMeta()
        self._meta_lock = threading.Lock()
        self._frame_times: list[float] = []
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._depth_m: Optional[np.ndarray] = None
        self._display_size: tuple[int, int] = (0, 0)

        self._build_ui()
        self.root.after(50, self._poll_frame_queue)
        signal.signal(signal.SIGINT, self._on_sigint)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    @staticmethod
    def _on_sigint(*_):
        raise KeyboardInterrupt

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg=HEADER_BG, padx=18, pady=14)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="MagicBot Z1 Depth Visualizer",
            bg=HEADER_BG,
            fg=HEADER_FG,
            font=("TkDefaultFont", 16, "bold"),
        ).pack(side=tk.LEFT)
        tk.Label(
            header,
            text="Head RGBD depth stream",
            bg=HEADER_BG,
            fg="#bfdbfe",
            font=("TkDefaultFont", 10),
        ).pack(side=tk.RIGHT)

        conn = ttk.LabelFrame(self.root, text="Connection", padding=12)
        conn.pack(fill=tk.X, padx=14, pady=(12, 8))

        ttk.Label(conn, text="Local IP").pack(side=tk.LEFT)
        ttk.Entry(conn, textvariable=self.local_ip_var, width=18).pack(
            side=tk.LEFT, padx=(8, 10)
        )
        ttk.Button(conn, text="Connect", command=self.connect_robot).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(conn, text="Disconnect", command=self.disconnect_robot).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Label(conn, text="Status:").pack(side=tk.LEFT, padx=(16, 4))
        self._status_label = ttk.Label(conn, textvariable=self.connect_status_var)
        self._status_label.pack(side=tk.LEFT)

        ctrl = ttk.LabelFrame(self.root, text="Depth Stream", padding=12)
        ctrl.pack(fill=tk.X, padx=14, pady=8)

        ttk.Button(ctrl, text="Start", command=self.start_stream).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(ctrl, text="Stop", command=self.stop_stream).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Label(ctrl, text="Max depth (m)").pack(side=tk.LEFT, padx=(16, 4))
        ttk.Entry(ctrl, textvariable=self.max_depth_var, width=8).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Label(ctrl, text="Color").pack(side=tk.LEFT, padx=(16, 4))
        ttk.Combobox(
            ctrl,
            values=DEPTH_COLOR_MODES,
            textvariable=self.colormap_var,
            width=10,
            state="readonly",
        ).pack(side=tk.LEFT, padx=4)
        ttk.Label(
            ctrl,
            text="Near=red/bright, far=blue/dark; black=invalid",
        ).pack(side=tk.LEFT, padx=(16, 0))

        view = ttk.LabelFrame(self.root, text="Depth Image", padding=10)
        view.pack(fill=tk.BOTH, expand=True, padx=14, pady=8)

        self._image_label = tk.Label(
            view,
            text="No depth frame",
            bg=PANEL_BG,
            fg=PANEL_FG,
            font=("TkDefaultFont", 12),
        )
        self._image_label.pack(fill=tk.BOTH, expand=True)
        self._image_label.bind("<Motion>", self._on_mouse_move)
        self._image_label.bind("<Leave>", self._on_mouse_leave)

        stats = ttk.LabelFrame(self.root, text="Frame Info", padding=10)
        stats.pack(fill=tk.X, padx=14, pady=(0, 14))
        ttk.Label(stats, textvariable=self.stats_var, font=("TkFixedFont", 10)).pack(
            anchor="w"
        )
        ttk.Label(stats, textvariable=self.cursor_var, font=("TkFixedFont", 10)).pack(
            anchor="w", pady=(6, 0)
        )

    def _log(self, message: str) -> None:
        logging.info(message)

    def _set_status(self, connected: bool) -> None:
        self.connect_status_var.set("Connected" if connected else "Disconnected")

    def _parse_max_depth(self) -> Optional[float]:
        try:
            value = float(self.max_depth_var.get().strip())
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            self._log("Invalid max depth; use a positive number in meters.")
            return None

    def connect_robot(self) -> None:
        if self.robot is not None:
            self._log("Robot already connected.")
            return

        def worker() -> None:
            try:
                robot = magicbot.MagicRobot()
                ip = self.local_ip_var.get().strip()
                if not robot.initialize(ip):
                    self._log("initialize failed")
                    robot.shutdown()
                    return

                status = robot.connect()
                if status.code != magicbot.ErrorCode.OK:
                    self._log(f"connect failed: {status.message}")
                    robot.shutdown()
                    return

                sensor = robot.get_sensor_controller()
                if not sensor.initialize():
                    self._log("sensor controller initialize failed")
                    robot.disconnect()
                    robot.shutdown()
                    return

                self.robot = robot
                self.sensor = sensor
                self.root.after(0, lambda: self._set_status(True))
                self._log("Robot connected.")
            except Exception as exc:
                self._log(f"connect exception: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def disconnect_robot(self) -> None:
        self.stop_stream()
        if self.robot is None:
            return
        try:
            if self.sensor is not None:
                try:
                    self.sensor.shutdown()
                except Exception:
                    pass
            self.robot.disconnect()
            self.robot.shutdown()
        except Exception as exc:
            self._log(f"disconnect exception: {exc}")
        finally:
            self.robot = None
            self.sensor = None
            self._set_status(False)
            self._clear_view()
            self._log("Robot disconnected.")

    def start_stream(self) -> None:
        if self.sensor is None:
            self._log("Connect robot first.")
            return
        if not _HAS_VIZ_DEPS:
            self._log("Install opencv-python and Pillow (see requirements.txt).")
            return
        if self.streaming:
            self._log("Depth stream already running.")
            return
        max_depth = self._parse_max_depth()
        if max_depth is None:
            return

        status = self.sensor.open_head_rgbd_camera()
        if status.code != magicbot.ErrorCode.OK:
            self._log(f"open_head_rgbd_camera failed: {status.message}")
            return

        self.streaming = True
        with self._meta_lock:
            self._meta = DepthFrameMeta()
            self._frame_times.clear()

        def on_depth_image(img: magicbot.Image) -> None:
            if not self.streaming:
                return
            try:
                max_depth_m = self._parse_max_depth() or 5.0
                depth_m = decode_depth_meters(img)
                rgb = depth_to_display_rgb(
                    depth_m, max_depth_m, self.colormap_var.get()
                )

                valid = depth_m > 0
                min_d = float(depth_m[valid].min()) if np.any(valid) else 0.0
                max_d = float(depth_m[valid].max()) if np.any(valid) else 0.0
                valid_ratio = float(valid.mean()) if valid.size else 0.0

                now = time.monotonic()
                with self._meta_lock:
                    self._meta.frame_count += 1
                    self._meta.width = img.width
                    self._meta.height = img.height
                    self._meta.encoding = img.encoding
                    self._meta.min_depth_m = min_d
                    self._meta.max_depth_m = max_d
                    self._meta.valid_ratio = valid_ratio
                    self._frame_times.append(now)
                    window = 1.0
                    self._frame_times = [
                        t for t in self._frame_times if t >= now - window
                    ]
                    if len(self._frame_times) >= 2:
                        span = self._frame_times[-1] - self._frame_times[0]
                        if span > 0:
                            self._meta.fps = (len(self._frame_times) - 1) / span

                payload = (rgb, depth_m, self._meta_snapshot())
                try:
                    self._frame_queue.put_nowait(payload)
                except queue.Full:
                    try:
                        self._frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._frame_queue.put_nowait(payload)
            except Exception as exc:
                logging.debug("depth callback: %s", exc)

        try:
            self.sensor.subscribe_head_rgbd_depth_image(on_depth_image)
            self._log("Subscribed to head RGBD depth image.")
        except Exception as exc:
            self.streaming = False
            self._log(f"subscribe failed: {exc}")

    def _meta_snapshot(self) -> DepthFrameMeta:
        with self._meta_lock:
            return DepthFrameMeta(
                width=self._meta.width,
                height=self._meta.height,
                encoding=self._meta.encoding,
                frame_count=self._meta.frame_count,
                fps=self._meta.fps,
                min_depth_m=self._meta.min_depth_m,
                max_depth_m=self._meta.max_depth_m,
                valid_ratio=self._meta.valid_ratio,
            )

    def stop_stream(self) -> None:
        if not self.streaming and self.sensor is None:
            return
        self.streaming = False
        if self.sensor is not None:
            try:
                self.sensor.unsubscribe_head_rgbd_depth_image()
            except Exception:
                pass
            try:
                self.sensor.close_head_rgbd_camera()
            except Exception:
                pass
        while not self._frame_queue.empty():
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                break
        self._log("Depth stream stopped.")

    def _poll_frame_queue(self) -> None:
        if not self.running:
            return
        try:
            rgb, depth_m, meta = self._frame_queue.get_nowait()
            self._show_rgb_frame(rgb, depth_m)
            self._update_stats(meta)
        except queue.Empty:
            pass
        self.root.after(50, self._poll_frame_queue)

    def _show_rgb_frame(self, rgb: np.ndarray, depth_m: np.ndarray) -> None:
        self._depth_m = depth_m
        img = Image.fromarray(rgb)
        label_w = max(self._image_label.winfo_width(), 320)
        label_h = max(self._image_label.winfo_height(), 240)
        w, h = img.size
        scale = min(label_w / w, label_h / h, 1.0)
        if scale < 1.0:
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        self._display_size = img.size
        self._photo = ImageTk.PhotoImage(image=img)
        self._image_label.configure(image=self._photo, text="")

    def _on_mouse_move(self, event: tk.Event) -> None:
        if self._depth_m is None or self._display_size == (0, 0):
            return

        label_w = self._image_label.winfo_width()
        label_h = self._image_label.winfo_height()
        disp_w, disp_h = self._display_size
        offset_x = max(0, (label_w - disp_w) // 2)
        offset_y = max(0, (label_h - disp_h) // 2)
        px = event.x - offset_x
        py = event.y - offset_y
        if px < 0 or py < 0 or px >= disp_w or py >= disp_h:
            self.cursor_var.set("Cursor: —")
            return

        src_h, src_w = self._depth_m.shape
        src_x = min(max(int(px * src_w / disp_w), 0), src_w - 1)
        src_y = min(max(int(py * src_h / disp_h), 0), src_h - 1)
        depth = float(self._depth_m[src_y, src_x])
        if depth <= 0:
            self.cursor_var.set(f"Cursor: pixel ({src_x}, {src_y})  invalid / no depth")
        else:
            self.cursor_var.set(
                f"Cursor: pixel ({src_x}, {src_y})  "
                f"{depth:.3f} m  ({depth * 1000:.0f} mm)"
            )

    def _on_mouse_leave(self, _event: tk.Event) -> None:
        self.cursor_var.set("Cursor: —")

    def _update_stats(self, meta: DepthFrameMeta) -> None:
        self.stats_var.set(
            f"FPS: {meta.fps:5.1f}  |  Frames: {meta.frame_count}  |  "
            f"Resolution: {meta.width}x{meta.height}  |  Encoding: {meta.encoding or '—'}  |  "
            f"Depth range: {meta.min_depth_m:.3f}–{meta.max_depth_m:.3f} m  |  "
            f"Valid pixels: {meta.valid_ratio * 100:.1f}%"
        )

    def _clear_view(self) -> None:
        self._photo = None
        self._depth_m = None
        self._display_size = (0, 0)
        self._image_label.configure(image="", text="No depth frame")
        self.stats_var.set(
            "FPS: —  |  Frames: —  |  Resolution: —  |  Encoding: —  |  "
            "Depth range: —  |  Valid pixels: —"
        )
        self.cursor_var.set("Cursor: —")

    def on_close(self) -> None:
        if not self.running:
            return
        self.running = False
        self.disconnect_robot()
        self.root.quit()
        self.root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description="MagicBot Z1 head RGBD depth visualizer")
    parser.add_argument(
        "--local-ip",
        default="192.168.54.111",
        help="Local network interface IP for SDK (default: 192.168.54.111)",
    )
    args = parser.parse_args()

    if not _HAS_VIZ_DEPS:
        print(
            "Missing dependencies. Install with:\n"
            "  pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    root = tk.Tk()
    app = DepthVizApp(root, default_local_ip=args.local_ip)
    logging.info("Robot model: %s", magicbot.get_robot_model())
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

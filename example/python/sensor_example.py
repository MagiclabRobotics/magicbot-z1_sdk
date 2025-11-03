#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import signal
import logging
from typing import Optional

import magicbot_z1_python as magicbot

# Configure logging format and level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)

# Global variables
robot: Optional[magicbot.MagicRobot] = None
running = True

# Counters for data reception
lidar_imu_counter = 0
lidar_pointcloud_counter = 0
head_rgbd_color_counter = 0
head_rgbd_depth_counter = 0
head_rgbd_camera_info_counter = 0
binocular_image_counter = 0


def signal_handler(signum, frame):
    """Signal handler function for graceful exit"""
    global running, robot
    logging.info("Received interrupt signal (%s), exiting...", signum)
    running = False
    if robot:
        robot.disconnect()
        logging.info("Robot disconnected")
        robot.shutdown()
        logging.info("Robot shutdown")
    exit(-1)


class SensorManager:
    """Manages sensor subscriptions for MagicBot Z1"""

    def __init__(self, sensor_controller):
        self.sensor_controller = sensor_controller
        self.sensors_state = {
            "lidar": False,
            "head_rgbd_camera": False,
            "binocular_camera": False,
        }
        self.subscriptions = {
            # LiDAR subscriptions
            "lidar_imu": False,
            "lidar_point_cloud": False,
            # Head RGBD subscriptions
            "head_rgbd_color_image": False,
            "head_rgbd_depth_image": False,
            "head_rgbd_camera_info": False,
            # Binocular camera subscriptions
            "binocular_image": False,
        }

    # === LiDAR Control ===
    def open_lidar(self) -> bool:
        """Open LiDAR"""
        if self.sensors_state["lidar"]:
            logging.warning("LiDAR already opened")
            return True

        status = self.sensor_controller.open_lidar()
        if status.code != magicbot.ErrorCode.OK:
            logging.error("Failed to open LiDAR: %s", status.message)
            return False

        self.sensors_state["lidar"] = True
        logging.info("✓ LiDAR opened successfully")
        return True

    def close_lidar(self) -> bool:
        """Close LiDAR"""
        if not self.sensors_state["lidar"]:
            logging.warning("LiDAR already closed")
            return True

        status = self.sensor_controller.close_lidar()
        if status.code != magicbot.ErrorCode.OK:
            logging.error("Failed to close LiDAR: %s", status.message)
            return False

        self.sensors_state["lidar"] = False
        logging.info("✓ LiDAR closed")
        return True

    # === Head RGBD Camera Control ===
    def open_head_rgbd_camera(self) -> bool:
        """Open head RGBD camera"""
        if self.sensors_state["head_rgbd_camera"]:
            logging.warning("Head RGBD camera already opened")
            return True

        status = self.sensor_controller.open_head_rgbd_camera()
        if status.code != magicbot.ErrorCode.OK:
            logging.error("Failed to open head RGBD camera: %s", status.message)
            return False

        self.sensors_state["head_rgbd_camera"] = True
        logging.info("✓ Head RGBD camera opened")
        return True

    def close_head_rgbd_camera(self) -> bool:
        """Close head RGBD camera"""
        if not self.sensors_state["head_rgbd_camera"]:
            logging.warning("Head RGBD camera already closed")
            return True

        status = self.sensor_controller.close_head_rgbd_camera()
        if status.code != magicbot.ErrorCode.OK:
            logging.error("Failed to close head RGBD camera: %s", status.message)
            return False

        self.sensors_state["head_rgbd_camera"] = False
        logging.info("✓ Head RGBD camera closed")
        return True

    # === Binocular Camera Control ===
    def open_binocular_camera(self) -> bool:
        """Open binocular camera"""
        if self.sensors_state["binocular_camera"]:
            logging.warning("Binocular camera already opened")
            return True

        status = self.sensor_controller.open_binocular_camera()
        if status.code != magicbot.ErrorCode.OK:
            logging.error("Failed to open binocular camera: %s", status.message)
            return False

        self.sensors_state["binocular_camera"] = True
        logging.info("✓ Binocular camera opened")
        return True

    def close_binocular_camera(self) -> bool:
        """Close binocular camera"""
        if not self.sensors_state["binocular_camera"]:
            logging.warning("Binocular camera already closed")
            return True

        status = self.sensor_controller.close_binocular_camera()
        if status.code != magicbot.ErrorCode.OK:
            logging.error("Failed to close binocular camera: %s", status.message)
            return False

        self.sensors_state["binocular_camera"] = False
        logging.info("✓ Binocular camera closed")
        return True

    # === LiDAR Subscribe Methods ===
    def toggle_lidar_imu_subscription(self):
        """Toggle LiDAR IMU subscription"""
        if self.subscriptions["lidar_imu"]:
            self.sensor_controller.unsubscribe_lidar_imu()
            self.subscriptions["lidar_imu"] = False
            logging.info("✗ LiDAR IMU unsubscribed")
        else:

            def lidar_imu_callback(imu):
                global lidar_imu_counter
                lidar_imu_counter += 1
                if lidar_imu_counter % 100 == 0:
                    logging.info("========== LiDAR IMU Data ==========")
                    logging.info("Counter: %d", lidar_imu_counter)
                    logging.info("Timestamp: %d", imu.timestamp)
                    logging.info(
                        "Orientation (x,y,z,w): [%.4f, %.4f, %.4f, %.4f]",
                        imu.orientation[0],
                        imu.orientation[1],
                        imu.orientation[2],
                        imu.orientation[3],
                    )
                    logging.info(
                        "Angular velocity (x,y,z): [%.4f, %.4f, %.4f]",
                        imu.angular_velocity[0],
                        imu.angular_velocity[1],
                        imu.angular_velocity[2],
                    )
                    logging.info(
                        "Linear acceleration (x,y,z): [%.4f, %.4f, %.4f]",
                        imu.linear_acceleration[0],
                        imu.linear_acceleration[1],
                        imu.linear_acceleration[2],
                    )
                    logging.info("Temperature: %.2f", imu.temperature)
                    logging.info("=" * 40)

            self.sensor_controller.subscribe_lidar_imu(lidar_imu_callback)
            self.subscriptions["lidar_imu"] = True
            logging.info("✓ LiDAR IMU subscribed")

    def toggle_lidar_point_cloud_subscription(self):
        """Toggle LiDAR point cloud subscription"""
        if self.subscriptions["lidar_point_cloud"]:
            self.sensor_controller.unsubscribe_lidar_point_cloud()
            self.subscriptions["lidar_point_cloud"] = False
            logging.info("✗ LiDAR point cloud unsubscribed")
        else:

            def lidar_pointcloud_callback(pointcloud):
                global lidar_pointcloud_counter
                lidar_pointcloud_counter += 1
                if lidar_pointcloud_counter % 10 == 0:
                    logging.info("========== LiDAR Point Cloud ==========")
                    logging.info("Counter: %d", lidar_pointcloud_counter)
                    logging.info("Data size: %d bytes", len(pointcloud.data))
                    logging.info("Width: %d", pointcloud.width)
                    logging.info("Height: %d", pointcloud.height)
                    logging.info("Is dense: %s", pointcloud.is_dense)
                    logging.info("Point step: %d", pointcloud.point_step)
                    logging.info("Row step: %d", pointcloud.row_step)
                    logging.info("Number of fields: %d", len(pointcloud.fields))
                    if pointcloud.fields:
                        logging.info("First field name: %s", pointcloud.fields[0].name)
                    logging.info("=" * 40)

            self.sensor_controller.subscribe_lidar_point_cloud(
                lidar_pointcloud_callback
            )
            self.subscriptions["lidar_point_cloud"] = True
            logging.info("✓ LiDAR point cloud subscribed")

    # === Head RGBD Subscribe Methods ===
    def toggle_head_rgbd_color_image_subscription(self):
        """Toggle head RGBD color image subscription"""
        if self.subscriptions["head_rgbd_color_image"]:
            self.sensor_controller.unsubscribe_head_rgbd_color_image()
            self.subscriptions["head_rgbd_color_image"] = False
            logging.info("✗ Head RGBD color image unsubscribed")
        else:

            def head_rgbd_color_image_callback(img):
                global head_rgbd_color_counter
                head_rgbd_color_counter += 1
                if head_rgbd_color_counter % 15 == 0:
                    logging.info("========== Head RGBD Color Image ==========")
                    logging.info("Counter: %d", head_rgbd_color_counter)
                    logging.info("Size: %d bytes", len(img.data))
                    logging.info("Resolution: %dx%d", img.width, img.height)
                    logging.info("Encoding: %s", img.encoding)
                    logging.info("=" * 40)

            self.sensor_controller.subscribe_head_rgbd_color_image(
                head_rgbd_color_image_callback
            )
            self.subscriptions["head_rgbd_color_image"] = True
            logging.info("✓ Head RGBD color image subscribed")

    def toggle_head_rgbd_depth_image_subscription(self):
        """Toggle head RGBD depth image subscription"""
        if self.subscriptions["head_rgbd_depth_image"]:
            self.sensor_controller.unsubscribe_head_rgbd_depth_image()
            self.subscriptions["head_rgbd_depth_image"] = False
            logging.info("✗ Head RGBD depth image unsubscribed")
        else:

            def head_rgbd_depth_image_callback(img):
                global head_rgbd_depth_counter
                head_rgbd_depth_counter += 1
                if head_rgbd_depth_counter % 15 == 0:
                    logging.info("========== Head RGBD Depth Image ==========")
                    logging.info("Counter: %d", head_rgbd_depth_counter)
                    logging.info("Size: %d bytes", len(img.data))
                    logging.info("Resolution: %dx%d", img.width, img.height)
                    logging.info("Encoding: %s", img.encoding)
                    logging.info("=" * 40)

            self.sensor_controller.subscribe_head_rgbd_depth_image(
                head_rgbd_depth_image_callback
            )
            self.subscriptions["head_rgbd_depth_image"] = True
            logging.info("✓ Head RGBD depth image subscribed")

    def toggle_head_rgbd_camera_info_subscription(self):
        """Toggle head RGBD camera info subscription"""
        if self.subscriptions["head_rgbd_camera_info"]:
            self.sensor_controller.unsubscribe_head_rgbd_camera_info()
            self.subscriptions["head_rgbd_camera_info"] = False
            logging.info("✗ Head RGBD camera info unsubscribed")
        else:

            def head_rgbd_camera_info_callback(info):
                global head_rgbd_camera_info_counter
                head_rgbd_camera_info_counter += 1
                if head_rgbd_camera_info_counter % 30 == 0:
                    logging.info("========== Head RGBD Camera Info ==========")
                    logging.info("Counter: %d", head_rgbd_camera_info_counter)
                    logging.info("Resolution: %dx%d", info.width, info.height)
                    logging.info("Distortion model: %s", info.distortion_model)
                    logging.info("=" * 40)

            self.sensor_controller.subscribe_head_rgbd_camera_info(
                head_rgbd_camera_info_callback
            )
            self.subscriptions["head_rgbd_camera_info"] = True
            logging.info("✓ Head RGBD camera info subscribed")

    # === Binocular Camera Subscribe Methods ===
    def toggle_binocular_image_subscription(self):
        """Toggle binocular camera image subscription"""
        if self.subscriptions["binocular_image"]:
            self.sensor_controller.unsubscribe_binocular_image()
            self.subscriptions["binocular_image"] = False
            logging.info("✗ Binocular image unsubscribed")
        else:

            def binocular_image_callback(frame):
                global binocular_image_counter
                binocular_image_counter += 1
                if binocular_image_counter % 15 == 0:
                    logging.info("========== Binocular Camera Image ==========")
                    logging.info("Counter: %d", binocular_image_counter)
                    logging.info("Timestamp: %d", frame.header.stamp)
                    logging.info("Frame ID: %s", frame.header.frame_id)
                    logging.info("Format: %s", frame.format)
                    logging.info(
                        "Data size: %d bytes (left+right concatenated)",
                        len(frame.data),
                    )
                    logging.info("=" * 40)

            self.sensor_controller.subscribe_binocular_image(binocular_image_callback)
            self.subscriptions["binocular_image"] = True
            logging.info("✓ Binocular image subscribed")

    def show_status(self):
        """Display current sensor status"""
        logging.info("\n" + "=" * 80)
        logging.info("MAGICBOT Z1 SENSOR STATUS")
        logging.info("=" * 80)
        logging.info(
            "LiDAR:                         %s",
            "OPEN" if self.sensors_state["lidar"] else "CLOSED",
        )
        logging.info(
            "Head RGBD Camera:              %s",
            "OPEN" if self.sensors_state["head_rgbd_camera"] else "CLOSED",
        )
        logging.info(
            "Binocular Camera:              %s",
            "OPEN" if self.sensors_state["binocular_camera"] else "CLOSED",
        )
        logging.info("\nLIDAR SUBSCRIPTIONS:")
        logging.info(
            "  LiDAR IMU:                   %s",
            "✓ SUBSCRIBED" if self.subscriptions["lidar_imu"] else "✗ UNSUBSCRIBED",
        )
        logging.info(
            "  LiDAR Point Cloud:           %s",
            (
                "✓ SUBSCRIBED"
                if self.subscriptions["lidar_point_cloud"]
                else "✗ UNSUBSCRIBED"
            ),
        )
        logging.info("\nHEAD RGBD SUBSCRIPTIONS:")
        logging.info(
            "  Color Image:                 %s",
            (
                "✓ SUBSCRIBED"
                if self.subscriptions["head_rgbd_color_image"]
                else "✗ UNSUBSCRIBED"
            ),
        )
        logging.info(
            "  Depth Image:                 %s",
            (
                "✓ SUBSCRIBED"
                if self.subscriptions["head_rgbd_depth_image"]
                else "✗ UNSUBSCRIBED"
            ),
        )
        logging.info(
            "  Camera Info:                 %s",
            (
                "✓ SUBSCRIBED"
                if self.subscriptions["head_rgbd_camera_info"]
                else "✗ UNSUBSCRIBED"
            ),
        )
        logging.info("\nBINOCULAR CAMERA SUBSCRIPTIONS:")
        logging.info(
            "  Binocular Image:             %s",
            (
                "✓ SUBSCRIBED"
                if self.subscriptions["binocular_image"]
                else "✗ UNSUBSCRIBED"
            ),
        )
        logging.info("=" * 80 + "\n")


def print_menu():
    """Print interactive menu"""
    logging.info("\n" + "=" * 80)
    logging.info("MAGICBOT Z1 SENSOR CONTROL MENU")
    logging.info("=" * 80)
    logging.info("Sensor Open/Close:")
    logging.info("  1 - Open LiDAR                     2 - Close LiDAR")
    logging.info("  3 - Open Head RGBD Camera          4 - Close Head RGBD Camera")
    logging.info("  5 - Open Binocular Camera          6 - Close Binocular Camera")
    logging.info("\nLiDAR Subscriptions:")
    logging.info("  i - Toggle LiDAR IMU               p - Toggle LiDAR Point Cloud")
    logging.info("\nHead RGBD Camera Subscriptions:")
    logging.info("  c - Toggle Head Color Image        d - Toggle Head Depth Image")
    logging.info("  C - Toggle Head Camera Info")
    logging.info("\nBinocular Camera Subscriptions:")
    logging.info("  b - Toggle Binocular Image")
    logging.info("\nCommands:")
    logging.info(
        "  s - Show Status                    ESC - Quit              ? - Help"
    )
    logging.info("=" * 80)


def main():
    """Main function"""
    global robot, running

    # Bind signal handler
    signal.signal(signal.SIGINT, signal_handler)

    logging.info("\n" + "=" * 80)
    logging.info("MagicBot Z1 SDK Sensor Interactive Example")
    logging.info("Robot Model: %s", magicbot.get_robot_model())

    # Create robot instance
    robot = magicbot.MagicRobot()
    logging.info("SDK Version: %s", robot.get_sdk_version())
    logging.info("=" * 80 + "\n")

    try:
        # Configure local IP address for direct network connection and initialize SDK
        local_ip = "192.168.54.111"
        if not robot.initialize(local_ip):
            logging.error("Failed to initialize robot SDK")
            robot.shutdown()
            return -1

        logging.info("✓ Robot SDK initialized successfully")

        # Connect to robot
        status = robot.connect()
        if status.code != magicbot.ErrorCode.OK:
            logging.error(
                "Failed to connect to robot, code: %s, message: %s",
                status.code,
                status.message,
            )
            robot.shutdown()
            return -1

        logging.info("✓ Successfully connected to robot")

        # Get sensor controller
        sensor_controller = robot.get_sensor_controller()

        # Initialize sensor controller
        if not sensor_controller.initialize():
            logging.error("Failed to initialize sensor controller")
            robot.disconnect()
            robot.shutdown()
            return -1

        logging.info("✓ Sensor controller initialized successfully\n")

        sensor_manager = SensorManager(sensor_controller)

        print_menu()

        while running:
            try:
                choice = input("\nEnter your choice: ").strip()

                if choice == "\x1b" or choice.lower() == "esc":  # ESC key
                    logging.info("ESC key pressed, exiting program...")
                    break

                # Sensor open/close control
                if choice == "1":
                    sensor_manager.open_lidar()
                elif choice == "2":
                    sensor_manager.close_lidar()
                elif choice == "3":
                    sensor_manager.open_head_rgbd_camera()
                elif choice == "4":
                    sensor_manager.close_head_rgbd_camera()
                elif choice == "5":
                    sensor_manager.open_binocular_camera()
                elif choice == "6":
                    sensor_manager.close_binocular_camera()

                # LiDAR subscriptions
                elif choice == "i":
                    sensor_manager.toggle_lidar_imu_subscription()
                elif choice == "p":
                    sensor_manager.toggle_lidar_point_cloud_subscription()

                # Head RGBD subscriptions
                elif choice == "c":
                    sensor_manager.toggle_head_rgbd_color_image_subscription()
                elif choice == "d":
                    sensor_manager.toggle_head_rgbd_depth_image_subscription()
                elif choice == "C":
                    sensor_manager.toggle_head_rgbd_camera_info_subscription()

                # Binocular camera subscriptions
                elif choice == "b":
                    sensor_manager.toggle_binocular_image_subscription()
                # Commands
                elif choice.lower() == "s":
                    sensor_manager.show_status()
                elif choice == "?" or choice.lower() == "help":
                    print_menu()
                elif choice == "":
                    continue
                else:
                    logging.warning("Invalid choice: '%s'. Press '?' for help.", choice)

            except KeyboardInterrupt:
                logging.info("\nReceived keyboard interrupt, shutting down...")
                break
            except EOFError:
                logging.info("\nReceived EOF, shutting down...")
                break
            except Exception as e:
                logging.error("Error occurred while processing input: %s", e)

    except Exception as e:
        logging.error("Exception occurred during program execution: %s", e)
        import traceback

        traceback.print_exc()
        return -1

    finally:
        # Cleanup: close all sensors
        logging.info("\n" + "=" * 80)
        logging.info("Cleaning up resources...")
        logging.info("=" * 80)

        try:
            # Close all sensors
            if sensor_manager.sensors_state["lidar"]:
                sensor_manager.close_lidar()
            if sensor_manager.sensors_state["head_rgbd_camera"]:
                sensor_manager.close_head_rgbd_camera()
            if sensor_manager.sensors_state["binocular_camera"]:
                sensor_manager.close_binocular_camera()

            # Allow time for cleanup
            time.sleep(0.5)

            sensor_controller.shutdown()
            logging.info("✓ Sensor controller shutdown")

            robot.disconnect()
            logging.info("✓ Robot disconnected")

            robot.shutdown()
            logging.info("✓ Robot shutdown")

            logging.info("=" * 80)
            logging.info("Cleanup complete")
            logging.info("=" * 80 + "\n")

        except Exception as e:
            logging.error("Exception occurred while cleaning up resources: %s", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())

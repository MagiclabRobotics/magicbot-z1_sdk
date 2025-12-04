#include "magic_robot.h"
#include "magic_sdk_version.h"
#include "magic_type.h"

#include <termios.h>
#include <unistd.h>
#include <csignal>

#include <atomic>
#include <iomanip>
#include <iostream>
#include <map>
#include <string>

using namespace magic::z1;

// Global variables
magic::z1::MagicRobot robot;
std::atomic<bool> running(true);

// Counters for data reception
std::atomic<int> lidar_imu_counter(0);
std::atomic<int> lidar_pointcloud_counter(0);
std::atomic<int> head_rgbd_color_counter(0);
std::atomic<int> head_rgbd_depth_counter(0);
std::atomic<int> head_rgbd_camera_info_counter(0);
std::atomic<int> binocular_image_counter(0);
std::atomic<int> binocular_camera_info_counter(0);

void signalHandler(int signum) {
  std::cout << "\nInterrupt signal (" << signum << ") received.\n";
  running = false;
  robot.Shutdown();
  exit(signum);
}

/**
 * @class SensorManager
 * @brief Manages sensor subscriptions for MagicBot Z1
 */
class SensorManager {
 public:
  explicit SensorManager(sensor::SensorController& controller)
      : sensor_controller_(controller) {
    // Initialize sensor states
    sensors_state_["lidar"] = false;
    sensors_state_["head_rgbd_camera"] = false;
    sensors_state_["binocular_camera"] = false;

    // Initialize subscription states
    subscriptions_["lidar_imu"] = false;
    subscriptions_["lidar_point_cloud"] = false;
    subscriptions_["head_rgbd_color_image"] = false;
    subscriptions_["head_rgbd_depth_image"] = false;
    subscriptions_["head_rgbd_camera_info"] = false;
    subscriptions_["binocular_image"] = false;
    subscriptions_["binocular_camera_info"] = false;
  }

  // === LiDAR Control ===
  bool OpenLidar() {
    if (sensors_state_["lidar"]) {
      std::cout << "[WARN] LiDAR already opened" << std::endl;
      return true;
    }

    auto status = sensor_controller_.OpenLidar();
    if (status.code != ErrorCode::OK) {
      std::cerr << "[ERROR] Failed to open LiDAR: " << status.message << std::endl;
      return false;
    }

    sensors_state_["lidar"] = true;
    std::cout << "[INFO] ✓ LiDAR opened successfully" << std::endl;
    return true;
  }

  bool CloseLidar() {
    if (!sensors_state_["lidar"]) {
      std::cout << "[WARN] LiDAR already closed" << std::endl;
      return true;
    }

    auto status = sensor_controller_.CloseLidar();
    if (status.code != ErrorCode::OK) {
      std::cerr << "[ERROR] Failed to close LiDAR: " << status.message << std::endl;
      return false;
    }

    sensors_state_["lidar"] = false;
    std::cout << "[INFO] ✓ LiDAR closed" << std::endl;
    return true;
  }

  // === Head RGBD Camera Control ===
  bool OpenHeadRgbdCamera() {
    if (sensors_state_["head_rgbd_camera"]) {
      std::cout << "[WARN] Head RGBD camera already opened" << std::endl;
      return true;
    }

    auto status = sensor_controller_.OpenHeadRgbdCamera();
    if (status.code != ErrorCode::OK) {
      std::cerr << "[ERROR] Failed to open head RGBD camera: " << status.message << std::endl;
      return false;
    }

    sensors_state_["head_rgbd_camera"] = true;
    std::cout << "[INFO] ✓ Head RGBD camera opened" << std::endl;
    return true;
  }

  bool CloseHeadRgbdCamera() {
    if (!sensors_state_["head_rgbd_camera"]) {
      std::cout << "[WARN] Head RGBD camera already closed" << std::endl;
      return true;
    }

    auto status = sensor_controller_.CloseHeadRgbdCamera();
    if (status.code != ErrorCode::OK) {
      std::cerr << "[ERROR] Failed to close head RGBD camera: " << status.message << std::endl;
      return false;
    }

    sensors_state_["head_rgbd_camera"] = false;
    std::cout << "[INFO] ✓ Head RGBD camera closed" << std::endl;
    return true;
  }

  // === Binocular Camera Control ===
  bool OpenBinocularCamera() {
    if (sensors_state_["binocular_camera"]) {
      std::cout << "[WARN] Binocular camera already opened" << std::endl;
      return true;
    }

    auto status = sensor_controller_.OpenBinocularCamera();
    if (status.code != ErrorCode::OK) {
      std::cerr << "[ERROR] Failed to open binocular camera: " << status.message << std::endl;
      return false;
    }

    sensors_state_["binocular_camera"] = true;
    std::cout << "[INFO] ✓ Binocular camera opened" << std::endl;
    return true;
  }

  bool CloseBinocularCamera() {
    if (!sensors_state_["binocular_camera"]) {
      std::cout << "[WARN] Binocular camera already closed" << std::endl;
      return true;
    }

    auto status = sensor_controller_.CloseBinocularCamera();
    if (status.code != ErrorCode::OK) {
      std::cerr << "[ERROR] Failed to close binocular camera: " << status.message << std::endl;
      return false;
    }

    sensors_state_["binocular_camera"] = false;
    std::cout << "[INFO] ✓ Binocular camera closed" << std::endl;
    return true;
  }

  // === LiDAR Subscribe Methods ===
  void ToggleLidarImuSubscription() {
    if (subscriptions_["lidar_imu"]) {
      sensor_controller_.UnsubscribeLidarImu();
      subscriptions_["lidar_imu"] = false;
      std::cout << "[INFO] ✗ LiDAR IMU unsubscribed" << std::endl;
    } else {
      sensor_controller_.SubscribeLidarImu([](const std::shared_ptr<Imu>& imu) {
        int count = ++lidar_imu_counter;
        if (count % 100 == 0) {
          std::cout << "========== LiDAR IMU Data ==========" << std::endl;
          std::cout << "Counter: " << count << std::endl;
          std::cout << "Timestamp: " << imu->timestamp << std::endl;
          std::cout << std::fixed << std::setprecision(4);
          std::cout << "Orientation (w,x,y,z): ["
                    << imu->orientation[0] << ", "
                    << imu->orientation[1] << ", "
                    << imu->orientation[2] << ", "
                    << imu->orientation[3] << "]" << std::endl;
          std::cout << "Angular velocity (x,y,z): ["
                    << imu->angular_velocity[0] << ", "
                    << imu->angular_velocity[1] << ", "
                    << imu->angular_velocity[2] << "]" << std::endl;
          std::cout << "Linear acceleration (x,y,z): ["
                    << imu->linear_acceleration[0] << ", "
                    << imu->linear_acceleration[1] << ", "
                    << imu->linear_acceleration[2] << "]" << std::endl;
          std::cout << std::setprecision(2);
          std::cout << "Temperature: " << imu->temperature << std::endl;
          std::cout << "========================================" << std::endl;
        }
      });
      subscriptions_["lidar_imu"] = true;
      std::cout << "[INFO] ✓ LiDAR IMU subscribed" << std::endl;
    }
  }

  void ToggleLidarPointCloudSubscription() {
    if (subscriptions_["lidar_point_cloud"]) {
      sensor_controller_.UnsubscribeLidarPointCloud();
      subscriptions_["lidar_point_cloud"] = false;
      std::cout << "[INFO] ✗ LiDAR point cloud unsubscribed" << std::endl;
    } else {
      sensor_controller_.SubscribeLidarPointCloud([](const std::shared_ptr<PointCloud2>& pointcloud) {
        int count = ++lidar_pointcloud_counter;
        if (count % 10 == 0) {
          std::cout << "========== LiDAR Point Cloud ==========" << std::endl;
          std::cout << "Counter: " << count << std::endl;
          std::cout << "Data size: " << pointcloud->data.size() << " bytes" << std::endl;
          std::cout << "Width: " << pointcloud->width << std::endl;
          std::cout << "Height: " << pointcloud->height << std::endl;
          std::cout << "Is dense: " << (pointcloud->is_dense ? "true" : "false") << std::endl;
          std::cout << "Point step: " << pointcloud->point_step << std::endl;
          std::cout << "Row step: " << pointcloud->row_step << std::endl;
          std::cout << "Number of fields: " << pointcloud->fields.size() << std::endl;
          if (!pointcloud->fields.empty()) {
            std::cout << "First field name: " << pointcloud->fields[0].name << std::endl;
          }
          std::cout << "========================================" << std::endl;
        }
      });
      subscriptions_["lidar_point_cloud"] = true;
      std::cout << "[INFO] ✓ LiDAR point cloud subscribed" << std::endl;
    }
  }

  // === Head RGBD Subscribe Methods ===
  void ToggleHeadRgbdColorImageSubscription() {
    if (subscriptions_["head_rgbd_color_image"]) {
      sensor_controller_.UnsubscribeHeadRgbdColorImage();
      subscriptions_["head_rgbd_color_image"] = false;
      std::cout << "[INFO] ✗ Head RGBD color image unsubscribed" << std::endl;
    } else {
      sensor_controller_.SubscribeHeadRgbdColorImage([](const std::shared_ptr<Image>& img) {
        int count = ++head_rgbd_color_counter;
        if (count % 15 == 0) {
          std::cout << "========== Head RGBD Color Image ==========" << std::endl;
          std::cout << "Counter: " << count << std::endl;
          std::cout << "Size: " << img->data.size() << " bytes" << std::endl;
          std::cout << "Resolution: " << img->width << "x" << img->height << std::endl;
          std::cout << "Encoding: " << img->encoding << std::endl;
          std::cout << "========================================" << std::endl;
        }
      });
      subscriptions_["head_rgbd_color_image"] = true;
      std::cout << "[INFO] ✓ Head RGBD color image subscribed" << std::endl;
    }
  }

  void ToggleHeadRgbdDepthImageSubscription() {
    if (subscriptions_["head_rgbd_depth_image"]) {
      sensor_controller_.UnsubscribeHeadRgbdDepthImage();
      subscriptions_["head_rgbd_depth_image"] = false;
      std::cout << "[INFO] ✗ Head RGBD depth image unsubscribed" << std::endl;
    } else {
      sensor_controller_.SubscribeHeadRgbdDepthImage([](const std::shared_ptr<Image>& img) {
        int count = ++head_rgbd_depth_counter;
        if (count % 15 == 0) {
          std::cout << "========== Head RGBD Depth Image ==========" << std::endl;
          std::cout << "Counter: " << count << std::endl;
          std::cout << "Size: " << img->data.size() << " bytes" << std::endl;
          std::cout << "Resolution: " << img->width << "x" << img->height << std::endl;
          std::cout << "Encoding: " << img->encoding << std::endl;
          std::cout << "========================================" << std::endl;
        }
      });
      subscriptions_["head_rgbd_depth_image"] = true;
      std::cout << "[INFO] ✓ Head RGBD depth image subscribed" << std::endl;
    }
  }

  void ToggleHeadRgbdCameraInfoSubscription() {
    if (subscriptions_["head_rgbd_camera_info"]) {
      sensor_controller_.UnsubscribeHeadRgbdCameraInfo();
      subscriptions_["head_rgbd_camera_info"] = false;
      std::cout << "[INFO] ✗ Head RGBD camera info unsubscribed" << std::endl;
    } else {
      sensor_controller_.SubscribeHeadRgbdCameraInfo([](const std::shared_ptr<CameraInfo>& info) {
        int count = ++head_rgbd_camera_info_counter;
        if (count % 30 == 0) {
          std::cout << "========== Head RGBD Camera Info ==========" << std::endl;
          std::cout << "Counter: " << count << std::endl;
          std::cout << "Resolution: " << info->width << "x" << info->height << std::endl;
          std::cout << "Distortion model: " << info->distortion_model << std::endl;
          std::cout << "========================================" << std::endl;
        }
      });
      subscriptions_["head_rgbd_camera_info"] = true;
      std::cout << "[INFO] ✓ Head RGBD camera info subscribed" << std::endl;
    }
  }

  // === Binocular Camera Subscribe Methods ===
  void ToggleBinocularImageSubscription() {
    if (subscriptions_["binocular_image"]) {
      sensor_controller_.UnsubscribeBinocularImage();
      subscriptions_["binocular_image"] = false;
      std::cout << "[INFO] ✗ Binocular image unsubscribed" << std::endl;
    } else {
      sensor_controller_.SubscribeBinocularImage([](const std::shared_ptr<BinocularCameraFrame>& frame) {
        int count = ++binocular_image_counter;
        if (count % 15 == 0) {
          std::cout << "========== Binocular Camera Image ==========" << std::endl;
          std::cout << "Counter: " << count << std::endl;
          std::cout << "Timestamp: " << frame->header.stamp << std::endl;
          std::cout << "Frame ID: " << frame->header.frame_id << std::endl;
          std::cout << "Format: " << frame->format << std::endl;
          std::cout << "Data size: " << frame->data.size() << " bytes (left+right concatenated)" << std::endl;
          std::cout << "========================================" << std::endl;
        }
      });
      subscriptions_["binocular_image"] = true;
      std::cout << "[INFO] ✓ Binocular image subscribed" << std::endl;
    }
  }

  void ToggleBinocularCameraInfoSubscription() {
    if (subscriptions_["binocular_camera_info"]) {
      sensor_controller_.UnsubscribeBinocularCameraInfo();
      subscriptions_["binocular_camera_info"] = false;
      std::cout << "[INFO] ✗ Binocular camera info unsubscribed" << std::endl;
    } else {
      sensor_controller_.SubscribeBinocularCameraInfo([](const std::shared_ptr<CameraInfo>& info) {
        int count = ++binocular_camera_info_counter;
        if (count % 2 == 0) {
          std::cout << "========== Binocular Camera Info ==========" << std::endl;
          std::cout << "Counter: " << count << std::endl;
          std::cout << "Resolution: " << info->width << "x" << info->height << std::endl;
          std::cout << "Distortion model: " << info->distortion_model << std::endl;
          std::cout << "========================================" << std::endl;
        }
      });
      subscriptions_["binocular_camera_info"] = true;
      std::cout << "[INFO] ✓ Binocular camera info subscribed" << std::endl;
    }
  }

  void ShowStatus() const {
    std::cout << "\n"
              << std::string(80, '=') << std::endl;
    std::cout << "MAGICBOT Z1 SENSOR STATUS" << std::endl;
    std::cout << std::string(80, '=') << std::endl;
    std::cout << "LiDAR:                         "
              << (sensors_state_.at("lidar") ? "OPEN" : "CLOSED") << std::endl;
    std::cout << "Head RGBD Camera:              "
              << (sensors_state_.at("head_rgbd_camera") ? "OPEN" : "CLOSED") << std::endl;
    std::cout << "Binocular Camera:              "
              << (sensors_state_.at("binocular_camera") ? "OPEN" : "CLOSED") << std::endl;

    std::cout << "\nLIDAR SUBSCRIPTIONS:" << std::endl;
    std::cout << "  LiDAR IMU:                   "
              << (subscriptions_.at("lidar_imu") ? "✓ SUBSCRIBED" : "✗ UNSUBSCRIBED") << std::endl;
    std::cout << "  LiDAR Point Cloud:           "
              << (subscriptions_.at("lidar_point_cloud") ? "✓ SUBSCRIBED" : "✗ UNSUBSCRIBED") << std::endl;

    std::cout << "\nHEAD RGBD SUBSCRIPTIONS:" << std::endl;
    std::cout << "  Color Image:                 "
              << (subscriptions_.at("head_rgbd_color_image") ? "✓ SUBSCRIBED" : "✗ UNSUBSCRIBED") << std::endl;
    std::cout << "  Depth Image:                 "
              << (subscriptions_.at("head_rgbd_depth_image") ? "✓ SUBSCRIBED" : "✗ UNSUBSCRIBED") << std::endl;
    std::cout << "  Camera Info:                 "
              << (subscriptions_.at("head_rgbd_camera_info") ? "✓ SUBSCRIBED" : "✗ UNSUBSCRIBED") << std::endl;

    std::cout << "\nBINOCULAR CAMERA SUBSCRIPTIONS:" << std::endl;
    std::cout << "  Binocular Image:             "
              << (subscriptions_.at("binocular_image") ? "✓ SUBSCRIBED" : "✗ UNSUBSCRIBED") << std::endl;
    std::cout << "  Camera Info:                 "
              << (subscriptions_.at("binocular_camera_info") ? "✓ SUBSCRIBED" : "✗ UNSUBSCRIBED") << std::endl;
    std::cout << std::string(80, '=') << "\n"
              << std::endl;
  }

  // Getters for sensor states
  bool IsSensorOpen(const std::string& sensor_name) const {
    auto it = sensors_state_.find(sensor_name);
    return it != sensors_state_.end() && it->second;
  }

 private:
  sensor::SensorController& sensor_controller_;
  std::map<std::string, bool> sensors_state_;
  std::map<std::string, bool> subscriptions_;
};

void PrintMenu() {
  std::cout << "\n"
            << std::string(80, '=') << std::endl;
  std::cout << "MAGICBOT Z1 SENSOR CONTROL MENU" << std::endl;
  std::cout << std::string(80, '=') << std::endl;
  std::cout << "Sensor Open/Close:" << std::endl;
  std::cout << "  1 - Open LiDAR                     2 - Close LiDAR" << std::endl;
  std::cout << "  3 - Open Head RGBD Camera          4 - Close Head RGBD Camera" << std::endl;
  std::cout << "  5 - Open Binocular Camera          6 - Close Binocular Camera" << std::endl;
  std::cout << "\nLiDAR Subscriptions:" << std::endl;
  std::cout << "  i - Toggle LiDAR IMU               p - Toggle LiDAR Point Cloud" << std::endl;
  std::cout << "\nHead RGBD Camera Subscriptions:" << std::endl;
  std::cout << "  c - Toggle Head Color Image        d - Toggle Head Depth Image" << std::endl;
  std::cout << "  C - Toggle Head Camera Info" << std::endl;
  std::cout << "\nBinocular Camera Subscriptions:" << std::endl;
  std::cout << "  b - Toggle Binocular Image         B - Toggle Binocular Camera Info" << std::endl;
  std::cout << "\nCommands:" << std::endl;
  std::cout << "  s - Show Status                    q - Quit              ? - Help" << std::endl;
  std::cout << std::string(80, '=') << std::endl;
}

int getch() {
  struct termios oldt, newt;
  int ch;
  tcgetattr(STDIN_FILENO, &oldt);
  newt = oldt;
  newt.c_lflag &= ~(ICANON | ECHO);
  tcsetattr(STDIN_FILENO, TCSANOW, &newt);
  ch = getchar();
  tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
  return ch;
}

int main() {
  // Bind SIGINT (Ctrl+C)
  signal(SIGINT, signalHandler);

  std::cout << "\n"
            << std::string(80, '=') << std::endl;
  std::cout << "MagicBot Z1 SDK Sensor Interactive Example" << std::endl;
  std::cout << "SDK Version: " << SDK_VERSION_STRING << std::endl;
  std::cout << std::string(80, '=') << "\n"
            << std::endl;

  std::string local_ip = "192.168.54.111";

  // Initialize robot SDK
  if (!robot.Initialize(local_ip)) {
    std::cerr << "[ERROR] Failed to initialize robot SDK" << std::endl;
    robot.Shutdown();
    return -1;
  }
  std::cout << "[INFO] ✓ Robot SDK initialized successfully" << std::endl;

  // Connect to robot
  auto status = robot.Connect();
  if (status.code != ErrorCode::OK) {
    std::cerr << "[ERROR] Failed to connect to robot, code: " << status.code
              << ", message: " << status.message << std::endl;
    robot.Shutdown();
    return -1;
  }
  std::cout << "[INFO] ✓ Successfully connected to robot" << std::endl;

  // Get sensor controller
  auto& sensor_controller = robot.GetSensorController();

  // Initialize sensor controller
  if (!sensor_controller.Initialize()) {
    std::cerr << "[ERROR] Failed to initialize sensor controller" << std::endl;
    robot.Disconnect();
    robot.Shutdown();
    return -1;
  }
  std::cout << "[INFO] ✓ Sensor controller initialized successfully\n"
            << std::endl;

  // Create sensor manager
  SensorManager sensor_manager(sensor_controller);

  PrintMenu();

  // Main loop
  std::cout << "\nPress any key to continue..." << std::endl;

  while (running) {
    int ch = getch();

    if (ch == 27 || ch == 'q' || ch == 'Q') {  // ESC or 'q'
      std::cout << "\n[INFO] Quit key pressed, exiting program..." << std::endl;
      break;
    }

    // Sensor open/close control
    switch (ch) {
      case '1':
        sensor_manager.OpenLidar();
        break;
      case '2':
        sensor_manager.CloseLidar();
        break;
      case '3':
        sensor_manager.OpenHeadRgbdCamera();
        break;
      case '4':
        sensor_manager.CloseHeadRgbdCamera();
        break;
      case '5':
        sensor_manager.OpenBinocularCamera();
        break;
      case '6':
        sensor_manager.CloseBinocularCamera();
        break;

      // LiDAR subscriptions
      case 'i':
      case 'I':
        sensor_manager.ToggleLidarImuSubscription();
        break;
      case 'p':
      case 'P':
        sensor_manager.ToggleLidarPointCloudSubscription();
        break;

      // Head RGBD subscriptions
      case 'c':
        sensor_manager.ToggleHeadRgbdColorImageSubscription();
        break;
      case 'd':
        sensor_manager.ToggleHeadRgbdDepthImageSubscription();
        break;
      case 'C':
        sensor_manager.ToggleHeadRgbdCameraInfoSubscription();
        break;

      // Binocular camera subscriptions
      case 'b':
        sensor_manager.ToggleBinocularImageSubscription();
        break;
      case 'B':
        sensor_manager.ToggleBinocularCameraInfoSubscription();
        break;

      // Commands
      case 's':
      case 'S':
        sensor_manager.ShowStatus();
        break;
      case '?':
        PrintMenu();
        break;

      default:
        // Ignore unknown keys
        break;
    }
  }

  // Cleanup: close all sensors
  std::cout << "\n"
            << std::string(80, '=') << std::endl;
  std::cout << "Cleaning up resources..." << std::endl;
  std::cout << std::string(80, '=') << std::endl;

  if (sensor_manager.IsSensorOpen("lidar")) {
    sensor_manager.CloseLidar();
  }
  if (sensor_manager.IsSensorOpen("head_rgbd_camera")) {
    sensor_manager.CloseHeadRgbdCamera();
  }
  if (sensor_manager.IsSensorOpen("binocular_camera")) {
    sensor_manager.CloseBinocularCamera();
  }

  // Allow time for cleanup
  usleep(500000);  // 0.5 seconds

  sensor_controller.Shutdown();
  std::cout << "[INFO] ✓ Sensor controller shutdown" << std::endl;

  status = robot.Disconnect();
  if (status.code == ErrorCode::OK) {
    std::cout << "[INFO] ✓ Robot disconnected" << std::endl;
  }

  robot.Shutdown();
  std::cout << "[INFO] ✓ Robot shutdown" << std::endl;

  std::cout << std::string(80, '=') << std::endl;
  std::cout << "Cleanup complete" << std::endl;
  std::cout << std::string(80, '=') << "\n"
            << std::endl;

  return 0;
}

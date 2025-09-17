#pragma once

#include "magic_export.h"
#include "magic_type.h"

#include <atomic>
#include <functional>
#include <memory>
#include <string>

namespace magic::z1::sensor {

class SensorController;
using SensorControllerPtr = std::unique_ptr<SensorController>;

/**
 * @class SensorController
 * @brief Sensor controller class that encapsulates initialization, on/off and data acquisition interfaces for various robot sensors.
 *
 * Supports acquiring IMU, point cloud, RGBD images, binocular camera images and other information, providing unified access methods
 * for upper-level controllers or state fusion modules to call.
 */
class MAGIC_EXPORT_API SensorController final : public NonCopyable {
  // Message pointer type definitions (smart pointers for memory management)
  using PointCloudPtr = std::shared_ptr<PointCloud2>;                // Point cloud message pointer
  using ImuPtr = std::shared_ptr<Imu>;                               // IMU inertial measurement unit message pointer
  using ImagePtr = std::shared_ptr<Image>;                           // Image message pointer
  using CameraInfoPtr = std::shared_ptr<CameraInfo>;                 // Camera intrinsic parameter information pointer
  using BinocularCameraPtr = std::shared_ptr<BinocularCameraFrame>;  // Binocular camera frame data pointer (spelling suggestion: change to Trinocular)

  // Callback function type definitions for various sensor data
  using LidarImuCallback = std::function<void(const ImuPtr)>;                    // Lidar IMU data callback
  using LidarPointCloudCallback = std::function<void(const PointCloudPtr)>;      // Lidar point cloud data callback
  using RgbdImageCallback = std::function<void(const ImagePtr)>;                 // RGBD image data callback
  using CameraInfoCallback = std::function<void(const CameraInfoPtr)>;           // RGBD camera intrinsic parameter callback
  using BinocularImageCallback = std::function<void(const BinocularCameraPtr)>;  // Binocular camera image frame callback

 public:
  /// Constructor: Create SensorController instance, initialize internal state
  SensorController();

  /// Destructor: Release resources, close all sensors
  virtual ~SensorController();

  /**
   * @brief Initialize sensor controller, including resource allocation, driver loading, etc.
   * @return Returns true on successful initialization, false otherwise.
   */
  bool Initialize();

  /**
   * @brief Close all sensor connections and release resources.
   */
  void Shutdown();

  // === Lidar Control ===

  /**
   * @brief Open Lidar.
   * @return Operation status.
   */
  Status OpenLidar();

  /**
   * @brief Close Lidar.
   * @return Operation status.
   */
  Status CloseLidar();

  // === RGBD Camera Control ===

  /**
   * @brief Open head RGBD camera (including head and waist).
   * @return Operation status.
   */
  Status OpenHeadRgbdCamera();

  /**
   * @brief Close head RGBD camera.
   * @return Operation status.
   */
  Status CloseHeadRgbdCamera();

  // === Binocular Camera Control ===

  /**
   * @brief Open binocular camera.
   * @return Operation status.
   */
  Status OpenBinocularCamera();

  /**
   * @brief Close binocular camera.
   * @return Operation status.
   */
  Status CloseBinocularCamera();

  // 订阅各类传感器数据的函数接口

  /**
   * @brief Subscribe to lidar IMU data
   * @param callback Processing callback after receiving lidar IMU data
   */
  void SubscribeLidarImu(const LidarImuCallback callback);

  /**
   * @brief Subscribe to lidar point cloud data
   * @param callback Processing callback after receiving point cloud data
   */
  void SubscribeLidarPointCloud(const LidarPointCloudCallback callback);

  /**
   * @brief Subscribe to head RGBD color image data
   * @param callback Processing callback after receiving image data
   */
  void SubscribeHeadRgbdColorImage(const RgbdImageCallback callback);

  /**
   * @brief Subscribe to head RGBD depth image data
   * @param callback Processing callback after receiving depth image data
   */
  void SubscribeHeadRgbdDepthImage(const RgbdImageCallback callback);

  /**
   * @brief Subscribe to head RGBD camera parameter data
   * @param callback Processing callback after receiving camera intrinsic parameter information
   */
  void SubscribeHeadRgbdCameraInfo(const CameraInfoCallback callback);

  /**
   * @brief Subscribe to binocular camera image frame data
   * @param callback Processing callback after receiving binocular camera data
   */
  void SubscribeBinocularImage(const BinocularImageCallback callback);

  /**
   * @brief Subscribe to binocular camera parameter data
   * @param callback Processing callback after receiving camera intrinsic parameter information
   */
  void SubscribeBinocularCameraInfo(const CameraInfoCallback callback);

 private:
  std::atomic_bool is_shutdown_{true};  // Mark whether initialized
};

}  // namespace magic::z1::sensor

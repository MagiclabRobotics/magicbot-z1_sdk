/*
 * @FilePath: /humanoid_m1_sdk/sdk/include/magic_sensor.h
 * @Version: 1.0.0
 * Copyright © 2025 MagicLab.
 */
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
 * @brief 传感器控制器类，封装机器人各类传感器的初始化、开启/关闭和数据获取接口。
 *
 * 支持获取IMU、点云、RGBD图像、双目相机图像等信息，提供统一的访问方式，
 * 用于上层控制器或状态融合模块调用。
 */
class MAGIC_EXPORT_API SensorController final : public NonCopyable {
  // 消息指针类型定义（智能指针，便于内存管理）
  using PointCloudPtr = std::shared_ptr<PointCloud2>;                // 点云消息指针
  using ImuPtr = std::shared_ptr<Imu>;                               // IMU 惯性测量单元消息指针
  using ImagePtr = std::shared_ptr<Image>;                           // 图像消息指针
  using CameraInfoPtr = std::shared_ptr<CameraInfo>;                 // 相机内参信息指针
  using BinocularCameraPtr = std::shared_ptr<BinocularCameraFrame>;  // 双目相机帧数据指针（拼写建议改为 Trinocular）

  // 各类传感器数据的回调函数类型定义
  using LidarImuCallback = std::function<void(const ImuPtr)>;                    // 雷达 IMU 数据的回调
  using LidarPointCloudCallback = std::function<void(const PointCloudPtr)>;      // 雷达点云数据回调
  using RgbdImageCallback = std::function<void(const ImagePtr)>;                 // RGBD 图像数据回调
  using CameraInfoCallback = std::function<void(const CameraInfoPtr)>;           // RGBD 相机内参回调
  using BinocularImageCallback = std::function<void(const BinocularCameraPtr)>;  // 双目相机图像帧回调

 public:
  /// 构造函数：创建 SensorController 实例，初始化内部状态
  SensorController();

  /// 析构函数：释放资源，关闭所有传感器
  virtual ~SensorController();

  /**
   * @brief 初始化传感器控制器，包括资源申请、驱动加载等。
   * @return 初始化成功返回 true，否则返回 false。
   */
  bool Initialize();

  /**
   * @brief 关闭所有传感器连接并释放资源。
   */
  void Shutdown();

  // === Lidar控制 ===

  /**
   * @brief 打开 Lidar。
   * @return 操作状态。
   */
  Status OpenLidar();

  /**
   * @brief 关闭 Lidar。
   * @return 操作状态。
   */
  Status CloseLidar();

  // === RGBD 相机控制 ===

  /**
   * @brief 打开头部 RGBD 相机（包括头部和腰部）。
   * @return 操作状态。
   */
  Status OpenHeadRgbdCamera();

  /**
   * @brief 关闭头部 RGBD 相机。
   * @return 操作状态。
   */
  Status CloseHeadRgbdCamera();

  // === 双目相机控制 ===

  /**
   * @brief 打开双目相机。
   * @return 操作状态。
   */
  Status OpenBinocularCamera();

  /**
   * @brief 关闭双目相机。
   * @return 操作状态。
   */
  Status CloseBinocularCamera();

  // 订阅各类传感器数据的函数接口

  /**
   * @brief 订阅雷达 IMU 数据
   * @param callback 接收到雷达 IMU 数据后的处理回调
   */
  void SubscribeLidarImu(const LidarImuCallback callback);

  /**
   * @brief 订阅雷达点云数据
   * @param callback 接收到点云数据后的处理回调
   */
  void SubscribeLidarPointCloud(const LidarPointCloudCallback callback);

  /**
   * @brief 订阅头部 RGBD 彩色图像数据
   * @param callback 接收到图像数据后的处理回调
   */
  void SubscribeHeadRgbdColorImage(const RgbdImageCallback callback);

  /**
   * @brief 订阅头部 RGBD 深度图像数据
   * @param callback 接收到深度图像数据后的处理回调
   */
  void SubscribeHeadRgbdDepthImage(const RgbdImageCallback callback);

  /**
   * @brief 订阅头部 RGBD 相机参数数据
   * @param callback 接收到相机内参信息后的处理回调
   */
  void SubscribeHeadRgbdCameraInfo(const CameraInfoCallback callback);

  /**
   * @brief 订阅双目相机图像帧数据
   * @param callback 接收到双目相机数据后的处理回调
   */
  void SubscribeBinocularImage(const BinocularImageCallback callback);

  /**
   * @brief 订阅双目相机参数数据
   * @param callback 接收到相机内参信息后的处理回调
   */
  void SubscribeBinocularCameraInfo(const CameraInfoCallback callback);

 private:
  std::atomic_bool is_shutdown_{true};  // 标记是否已初始化
};

}  // namespace magic::z1::sensor

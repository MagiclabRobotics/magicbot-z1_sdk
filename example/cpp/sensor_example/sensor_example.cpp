#include "magic_robot.h"
#include "magic_type.h"

#include <unistd.h>
#include <csignal>

#include <iostream>

using namespace magic::z1;

magic::z1::MagicRobot robot;

void signalHandler(int signum) {
  std::cout << "Interrupt signal (" << signum << ") received.\n";

  robot.Shutdown();
  // 退出进程
  exit(signum);
}

int main() {
  // 绑定 SIGINT（Ctrl+C）
  signal(SIGINT, signalHandler);

  std::string local_ip = "192.168.54.111";
  // 配置本机网线直连机器的IP地址，并进行SDK初始化
  if (!robot.Initialize(local_ip)) {
    std::cerr << "robot sdk initialize failed." << std::endl;
    robot.Shutdown();
    return -1;
  }

  // 设置rpc超时时间为10s
  robot.SetTimeout(10000);

  // 连接机器人
  auto status = robot.Connect();
  if (status.code != ErrorCode::OK) {
    std::cerr << "connect robot failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    robot.Shutdown();
    return -1;
  }

  auto& controller = robot.GetSensorController();

  // 打开lidar
  status = controller.OpenLidar();
  if (status.code != ErrorCode::OK) {
    std::cerr << "open lidar failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    robot.Shutdown();
    return -1;
  }

  // 订阅Lidar Imu数据
  controller.SubscribeLidarImu([](const std::shared_ptr<Imu> msg) {
    std::cout << "++++++++++ receive lidar imu." << std::endl;

    std::cout << "lidar imu timestamp: " << msg->timestamp << std::endl;
    std::cout << "lidar imu orientation: " << msg->orientation[0] << ", " << msg->orientation[1] << ", " << msg->orientation[2] << ", " << msg->orientation[3] << std::endl;
    std::cout << "lidar imu angular_velocity: " << msg->angular_velocity[0] << ", " << msg->angular_velocity[1] << ", " << msg->angular_velocity[2] << std::endl;
    std::cout << "lidar imu linear_acceleration: " << msg->linear_acceleration[0] << ", " << msg->linear_acceleration[1] << ", " << msg->linear_acceleration[2] << std::endl;
    std::cout << "lidar imu temperature: " << msg->temperature << std::endl;
  });

  // 订阅Lidar PointCloud数据
  controller.SubscribeLidarPointCloud([](const std::shared_ptr<PointCloud2> msg) {
    std::cout << "++++++++++ receive lidar point cloud." << std::endl;
    // TODO: handle lidar point cloud data
    std::cout << "lidar point cloud size: " << msg->data.size() << std::endl;
    std::cout << "lidar point cloud width: " << msg->width << std::endl;
    std::cout << "lidar point cloud height: " << msg->height << std::endl;
    std::cout << "lidar point cloud is_dense: " << msg->is_dense << std::endl;
    std::cout << "lidar point cloud is_bigendian: " << msg->is_bigendian << std::endl;
    std::cout << "lidar point cloud point_step: " << msg->point_step << std::endl;
    std::cout << "lidar point cloud row_step: " << msg->row_step << std::endl;
    std::cout << "lidar point cloud fields: " << msg->fields.size() << std::endl;
    std::cout << "lidar point cloud fields name: " << msg->fields[0].name << std::endl;
    std::cout << "lidar point cloud fields offset: " << msg->fields[0].offset << std::endl;
    std::cout << "lidar point cloud fields datatype: " << msg->fields[0].datatype << std::endl;
    std::cout << "lidar point cloud fields count: " << msg->fields[0].count << std::endl;
  });

  usleep(20000000);

  // 关闭lidar
  status = controller.CloseLidar();
  if (status.code != ErrorCode::OK) {
    std::cerr << "close lidar failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    robot.Shutdown();
    return -1;
  }

  // 断开与机器人的链接
  status = robot.Disconnect();
  if (status.code != ErrorCode::OK) {
    std::cerr << "disconnect robot failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    robot.Shutdown();
    return -1;
  }

  robot.Shutdown();

  return 0;
}
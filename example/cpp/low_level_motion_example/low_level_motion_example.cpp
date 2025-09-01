#include "magic_robot.h"

#include <unistd.h>
#include <csignal>

#include <iostream>

using namespace magic::z1;

magic::z1::MagicRobot robot;

std::atomic<bool> running(true);

void signalHandler(int signum) {
  std::cout << "Interrupt signal (" << signum << ") received.\n";

  running = false;

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

  // 连接机器人
  auto status = robot.Connect();
  if (status.code != ErrorCode::OK) {
    std::cerr << "connect robot failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    robot.Shutdown();
    return -1;
  }

  // 切换运控控制器为底层控制器，默认是高层控制器
  status = robot.SetMotionControlLevel(ControllerLevel::LowLevel);
  if (status.code != ErrorCode::OK) {
    std::cerr << "switch robot motion control level failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    robot.Shutdown();
    return -1;
  }

  // 获取底层控制器
  auto& controller = robot.GetLowLevelMotionController();

  // 设置控制指令发送周期为2ms，500HZ
  controller.SetPeriodMs(2);

  // 订阅imu数据
  controller.SubscribeBodyImu([](const std::shared_ptr<Imu> msg) {
    static int32_t count = 0;
    if (count++ % 1000 == 1) {
      std::cout << "+++++++++++ receive imu data." << std::endl;
      std::cout << "timestamp: " << msg->timestamp << std::endl;
      std::cout << "temperature: " << msg->temperature << std::endl;
      std::cout << "orientation: " << msg->orientation[0] << ", " << msg->orientation[1] << ", " << msg->orientation[2] << ", " << msg->orientation[3] << std::endl;
      std::cout << "angular_velocity: " << msg->angular_velocity[0] << ", " << msg->angular_velocity[1] << ", " << msg->angular_velocity[2] << std::endl;
      std::cout << "linear_acceleration: " << msg->linear_acceleration[0] << ", " << msg->linear_acceleration[1] << ", " << msg->linear_acceleration[2] << std::endl;
    }
    // TODO: handle imu data
  });

  // 订阅手部数据
  controller.SubscribeArmState([](const std::shared_ptr<JointState> msg) {
    static int32_t count = 0;
    if (count++ % 1000 == 1) {
      std::cout << "+++++++++++ receive arm joint data." << std::endl;
      std::cout << "timestamp: " << msg->timestamp << std::endl;
      std::cout << "pos: " << msg->joints[0].posH << ", " << msg->joints[0].posL << std::endl;
      std::cout << "vel: " << msg->joints[0].vel << std::endl;
      std::cout << "toq: " << msg->joints[0].toq << std::endl;
      std::cout << "current: " << msg->joints[0].current << std::endl;
      std::cout << "error_code: " << msg->joints[0].err_code << std::endl;
    }
    // TODO: handle arm joint data
  });

  // 以上臂关节控制为例：
  // 后续关节控制指令，关节的操作模式为1，表示关节处于位置控制模式
  while (running.load()) {
    // 左臂关节，参考文档：
    // 左臂或者右臂1-5关节operation_mode需要从模式：200切换到模式：4（串联PID模式）进行指令下发；
    JointCommand arm_command;
    arm_command.joints.resize(kArmJointNum);
    for (int ii = 0; ii < kArmJointNum; ii++) {
      // 设置关节处于准备状态
      arm_command.joints[ii].operation_mode = 200;
      // TODO:设置目标位置、速度、力矩和增益
      arm_command.joints[ii].pos = 0.0;
      arm_command.joints[ii].vel = 0.0;
      arm_command.joints[ii].toq = 0.0;
      arm_command.joints[ii].kp = 0.0;
      arm_command.joints[ii].kd = 0.0;
    }
    // 发布控制指令
    controller.PublishArmCommand(arm_command);

    // 500HZ的频率(2ms)下发控制指令
    usleep(2000);
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
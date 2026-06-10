#include "magic_robot.h"
#include "magic_sdk_version.h"

#include <unistd.h>
#include <csignal>

#include <iostream>

using namespace magic::z1;

magic::z1::MagicRobot robot;

void signalHandler(int signum) {
  std::cout << "Interrupt signal (" << signum << ") received.\n";

  robot.Shutdown();
  // Exit process
  exit(signum);
}

int main() {
  // Bind SIGINT (Ctrl+C)
  signal(SIGINT, signalHandler);

  std::cout << "SDK Version: " << SDK_VERSION_STRING << std::endl;

  std::string local_ip = "192.168.54.111";
  // Configure local IP address for direct ethernet connection to robot and initialize SDK
  if (!robot.Initialize(local_ip)) {
    std::cerr << "robot sdk initialize failed." << std::endl;
    robot.Shutdown();
    return -1;
  }

  // Connect to robot
  auto status = robot.Connect();
  if (status.code != ErrorCode::OK) {
    std::cerr << "connect robot failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    robot.Shutdown();
    return -1;
  }
  // Wait for 5 seconds
  usleep(5000000);

  auto& monitor = robot.GetStateMonitor();

  RobotState state;
  status = monitor.GetCurrentState(state);
  if (status.code != ErrorCode::OK) {
    std::cerr << "get robot state failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    robot.Shutdown();
    return -1;
  }

  std::cout << "*** battery health: " << state.bms_data.battery_health
            << ", battery percentage: " << state.bms_data.battery_percentage
            << ", battery state: " << std::to_string((int8_t)state.bms_data.battery_state)
            << ", battery power supply status: " << std::to_string((int8_t)state.bms_data.power_supply_status)
            << std::endl;

  auto& faults = state.faults;
  if (faults.size() > 0) {
    std::cout << "*** robot has " << faults.size() << " faults" << std::endl;
    for (auto& fault : faults) {
      std::cout << "error code: " << fault.error_code << std::endl;
      std::cout << "error code: 0x" << std::hex << std::uppercase << fault.error_code << std::dec
                << std::nouppercase << ", error message: " << fault.error_message << std::endl;
    }
  } else {
    std::cout << "*** robot has no faults" << std::endl;
  }

  // Disconnect from robot
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
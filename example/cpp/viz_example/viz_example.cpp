#include "magic_robot.h"
#include "magic_sdk_version.h"

#include <termios.h>
#include <unistd.h>

#include <algorithm>
#include <atomic>
#include <csignal>
#include <ctime>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

using namespace magic::z1;

namespace {

MagicRobot robot;
std::atomic_bool running{true};
std::atomic_int origin_audio_counter{0};
std::atomic_int bf_audio_counter{0};
std::atomic_int wakeup_counter{0};
std::atomic_int odom_counter{0};

int Getch() {
  termios oldt;
  termios newt;
  tcgetattr(STDIN_FILENO, &oldt);
  newt = oldt;
  newt.c_lflag &= ~(ICANON | ECHO);
  tcsetattr(STDIN_FILENO, TCSANOW, &newt);
  int ch = getchar();
  tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
  return ch;
}

std::string ReadLine(const std::string& prompt) {
  std::cout << prompt;
  std::string input;
  std::getline(std::cin, input);
  return input;
}

bool StatusOk(const Status& status, const std::string& action) {
  if (status.code == ErrorCode::OK) {
    std::cout << action << ": success" << std::endl;
    return true;
  }

  std::cerr << action << ": failed, code: " << status.code
            << ", message: " << status.message << std::endl;
  return false;
}

double ParseDoubleOrDefault(const std::string& text, double default_value) {
  if (text.empty()) {
    return default_value;
  }

  std::istringstream iss(text);
  double value = default_value;
  iss >> value;
  return iss.fail() ? default_value : value;
}

int ParseIntOrDefault(const std::string& text, int default_value) {
  if (text.empty()) {
    return default_value;
  }

  std::istringstream iss(text);
  int value = default_value;
  iss >> value;
  return iss.fail() ? default_value : value;
}

void PrintHelp() {
  std::cout << "\n========================================" << std::endl;
  std::cout << "MagicBot Z1 C++ Control Panel Example" << std::endl;
  std::cout << "SDK Version: " << SDK_VERSION_STRING << std::endl;
  std::cout << "========================================" << std::endl;
  std::cout << "Audio:" << std::endl;
  std::cout << "  1  Get volume" << std::endl;
  std::cout << "  2  Set volume" << std::endl;
  std::cout << "  3  Play TTS" << std::endl;
  std::cout << "  4  Stop TTS" << std::endl;
  std::cout << "  a  Start dialog" << std::endl;
  std::cout << "  b  Stop dialog" << std::endl;
  std::cout << "  5  Open audio stream" << std::endl;
  std::cout << "  6  Close audio stream" << std::endl;
  std::cout << "  7  Subscribe audio streams" << std::endl;
  std::cout << "  8  Unsubscribe audio streams" << std::endl;
  std::cout << "  q  Open wakeup stream" << std::endl;
  std::cout << "  w  Close wakeup stream" << std::endl;
  std::cout << "  e  Subscribe wakeup status" << std::endl;
  std::cout << "  r  Unsubscribe wakeup status" << std::endl;
  std::cout << "  z  Subscribe dialog intent" << std::endl;
  std::cout << "  x  Unsubscribe dialog intent" << std::endl;
  std::cout << "\nHigh-Level Motion:" << std::endl;
  std::cout << "  !  Recovery stand" << std::endl;
  std::cout << "  @  Balance stand" << std::endl;
  std::cout << "  #  Execute welcome trick" << std::endl;
  std::cout << "  i/k/j/l/u/o/p  Joystick forward/back/left/right/turn-left/turn-right/stop" << std::endl;
  std::cout << "  h  Move head" << std::endl;
  std::cout << "\nMonitor:" << std::endl;
  std::cout << "  m  Refresh robot state" << std::endl;
  std::cout << "\nSLAM and Navigation:" << std::endl;
  std::cout << "  A  Activate mapping mode" << std::endl;
  std::cout << "  B  Start mapping" << std::endl;
  std::cout << "  C  Cancel mapping" << std::endl;
  std::cout << "  D  Save map" << std::endl;
  std::cout << "  E  Load map" << std::endl;
  std::cout << "  F  Delete map" << std::endl;
  std::cout << "  G  Get all map info" << std::endl;
  std::cout << "  H  Get map path" << std::endl;
  std::cout << "  I  Get point cloud map" << std::endl;
  std::cout << "  J  Close SLAM" << std::endl;
  std::cout << "  K  Activate localization mode" << std::endl;
  std::cout << "  L  Init pose" << std::endl;
  std::cout << "  M  Get localization info" << std::endl;
  std::cout << "  N  Activate navigation mode" << std::endl;
  std::cout << "  O  Set navigation target" << std::endl;
  std::cout << "  P  Pause navigation" << std::endl;
  std::cout << "  R  Resume navigation" << std::endl;
  std::cout << "  S  Cancel navigation" << std::endl;
  std::cout << "  T  Get navigation status" << std::endl;
  std::cout << "  U  Close navigation" << std::endl;
  std::cout << "  V  Open odometry stream" << std::endl;
  std::cout << "  W  Close odometry stream" << std::endl;
  std::cout << "  X  Subscribe odometry" << std::endl;
  std::cout << "  Y  Unsubscribe odometry" << std::endl;
  std::cout << "\nOther:" << std::endl;
  std::cout << "  ?  Print help" << std::endl;
  std::cout << "  ESC  Exit program" << std::endl;
  std::cout << "========================================\n"
            << std::endl;
}

void SignalHandler(int signum) {
  std::cout << "Received interrupt signal (" << signum << "), exiting..." << std::endl;
  running = false;
  robot.Shutdown();
  std::exit(signum);
}

void GetVolume() {
  int volume = 0;
  auto status = robot.GetAudioController().GetVolume(volume);
  if (StatusOk(status, "get_volume")) {
    std::cout << "volume: " << volume << std::endl;
  }
}

void SetVolume() {
  int volume = ParseIntOrDefault(ReadLine("Enter volume [50]: "), 50);
  StatusOk(robot.GetAudioController().SetVolume(volume), "set_volume");
}

void PlayTts() {
  TtsCommand tts;
  tts.id = std::to_string(static_cast<long long>(std::time(nullptr)));
  tts.content = ReadLine("Enter TTS text [How's the weather today!]: ");
  if (tts.content.empty()) {
    tts.content = "How's the weather today!";
  }
  tts.priority = TtsPriority::HIGH;
  tts.mode = TtsMode::CLEARTOP;

  int timeout_ms = ParseIntOrDefault(ReadLine("Enter timeout ms [10000]: "), 10000);
  StatusOk(robot.GetAudioController().Play(tts, timeout_ms), "play_tts");
}

void StartDialog() {
  std::string text = ReadLine("Enter dialog text [Hello, how can I help you?]: ");
  if (text.empty()) {
    text = "Hello, how can I help you?";
  }
  StatusOk(robot.GetAudioController().StartDialog(text), "start_dialog");
}

void SubscribeAudioStreams() {
  auto& audio = robot.GetAudioController();
  audio.SubscribeOriginAudioStream([](const std::shared_ptr<AudioStream> data) {
    if (origin_audio_counter++ % 30 == 0) {
      std::cout << "origin_audio: bytes=" << data->data_length << std::endl;
    }
  });
  audio.SubscribeBfAudioStream([](const std::shared_ptr<AudioStream> data) {
    if (bf_audio_counter++ % 30 == 0) {
      std::cout << "bf_audio: bytes=" << data->data_length << std::endl;
    }
  });
  std::cout << "subscribe_audio_stream: success" << std::endl;
}

void SubscribeWakeupStatus() {
  robot.GetAudioController().SubscribeWakeupStatus([](const std::shared_ptr<WakeupStatus> data) {
    if (data->is_wakeup || wakeup_counter++ % 10 == 0) {
      std::cout << "wakeup: is_wakeup=" << data->is_wakeup
                << ", enable_orientation=" << data->enable_wakeup_orientation
                << ", orientation=" << data->wakeup_orientation << std::endl;
    }
  });
  std::cout << "subscribe_wakeup: success" << std::endl;
}

void SubscribeDialogIntent() {
  robot.GetAudioController().SubscribeDialogIntent([](const std::shared_ptr<DialogIntent> data) {
    std::cout << "dialog_intent: " << data->intent << std::endl;
  });
  std::cout << "subscribe_dialog_intent: success" << std::endl;
}

void SendJoystick(double lx, double ly, double rx, double ry) {
  JoystickCommand command;
  command.left_x_axis = lx;
  command.left_y_axis = ly;
  command.right_x_axis = rx;
  command.right_y_axis = ry;
  StatusOk(robot.GetHighLevelMotionController().SendJoyStickCommand(command), "joystick");
}

void HeadMove() {
  double angle = ParseDoubleOrDefault(ReadLine("Enter head shake angle rad [0.0]: "), 0.0);
  StatusOk(robot.GetHighLevelMotionController().HeadMove(static_cast<float>(angle), 10000), "head_move");
}

void RefreshState() {
  RobotState state;
  auto status = robot.GetStateMonitor().GetCurrentState(state);
  if (!StatusOk(status, "refresh_state")) {
    return;
  }

  std::cout << "battery_percentage: " << state.bms_data.battery_percentage << std::endl;
  std::cout << "battery_health: " << state.bms_data.battery_health << std::endl;
  std::cout << "battery_state: " << static_cast<int>(state.bms_data.battery_state) << std::endl;
  std::cout << "power_supply_status: " << static_cast<int>(state.bms_data.power_supply_status) << std::endl;
  if (state.faults.empty()) {
    std::cout << "faults: none" << std::endl;
    return;
  }

  std::cout << "faults:" << std::endl;
  for (const auto& fault : state.faults) {
    std::cout << "  code=" << fault.error_code
              << ", message=" << fault.error_message << std::endl;
  }
}

void SaveMap() {
  std::string map_name = ReadLine("Enter map name [map_demo]: ");
  if (map_name.empty()) {
    map_name = "map_demo";
  }
  StatusOk(robot.GetSlamNavController().SaveMap(map_name, 20000), "save_map");
}

void LoadMap() {
  std::string map_name = ReadLine("Enter map name: ");
  if (map_name.empty()) {
    std::cerr << "load_map: map name required" << std::endl;
    return;
  }
  StatusOk(robot.GetSlamNavController().LoadMap(map_name, 10000), "load_map");
}

void DeleteMap() {
  std::string map_name = ReadLine("Enter map name: ");
  if (map_name.empty()) {
    std::cerr << "delete_map: map name required" << std::endl;
    return;
  }
  StatusOk(robot.GetSlamNavController().DeleteMap(map_name, 10000), "delete_map");
}

void GetAllMapInfo() {
  AllMapInfo info;
  auto status = robot.GetSlamNavController().GetAllMapInfo(info, 10000);
  if (!StatusOk(status, "get_all_map_info")) {
    return;
  }

  std::cout << "current_map: " << info.current_map_name << std::endl;
  std::cout << "maps:";
  for (const auto& map_info : info.map_infos) {
    std::cout << " " << map_info.map_name;
  }
  std::cout << std::endl;
}

void GetMapPath() {
  std::string map_name = ReadLine("Enter map name [map_demo]: ");
  if (map_name.empty()) {
    map_name = "map_demo";
  }

  std::vector<std::string> paths;
  auto status = robot.GetSlamNavController().GetMapPath(map_name, paths, 10000);
  if (!StatusOk(status, "get_map_path")) {
    return;
  }

  for (const auto& path : paths) {
    std::cout << "map_path: " << path << std::endl;
  }
}

void GetPointCloudMap() {
  PointCloud2 point_cloud;
  auto status = robot.GetSlamNavController().GetPointCloudMap(point_cloud, 10000);
  if (!StatusOk(status, "get_point_cloud_map")) {
    return;
  }

  std::cout << "point_cloud: width=" << point_cloud.width
            << ", height=" << point_cloud.height
            << ", bytes=" << point_cloud.data.size() << std::endl;
}

void ActivateLocalizationMode() {
  std::string map_path = ReadLine("Enter map path: ");
  if (map_path.empty()) {
    std::cerr << "activate_localization_mode: map path required" << std::endl;
    return;
  }
  StatusOk(robot.GetSlamNavController().ActivateSlamMode(SlamMode::LOCALIZATION, map_path, 10000),
           "activate_localization_mode");
}

void InitPose() {
  std::string input = ReadLine("Enter pose x y yaw [0.0 0.0 0.0]: ");
  std::istringstream iss(input);
  double x = 0.0;
  double y = 0.0;
  double yaw = 0.0;
  iss >> x >> y >> yaw;

  Pose3DEuler pose;
  pose.position = {x, y, 0.0};
  pose.orientation = {0.0, 0.0, yaw};
  StatusOk(robot.GetSlamNavController().InitPose(pose, 10000), "init_pose");
}

void GetLocalizationInfo() {
  LocalizationInfo info;
  auto status = robot.GetSlamNavController().GetCurrentLocalizationInfo(info);
  if (!StatusOk(status, "get_localization_info")) {
    return;
  }

  std::cout << "localized: " << info.is_localization << std::endl;
  std::cout << "position: [" << info.pose.position[0] << ", "
            << info.pose.position[1] << ", "
            << info.pose.position[2] << "]" << std::endl;
  std::cout << "orientation: [" << info.pose.orientation[0] << ", "
            << info.pose.orientation[1] << ", "
            << info.pose.orientation[2] << "]" << std::endl;
}

void ActivateNavigationMode() {
  std::string map_path = ReadLine("Enter map path: ");
  if (map_path.empty()) {
    std::cerr << "activate_navigation_mode: map path required" << std::endl;
    return;
  }
  StatusOk(robot.GetSlamNavController().ActivateNavMode(NavMode::GRID_MAP, map_path, 10000),
           "activate_navigation_mode");
}

void SetNavigationTarget() {
  std::string input = ReadLine("Enter target x y yaw [0.0 0.0 0.0]: ");
  std::istringstream iss(input);
  double x = 0.0;
  double y = 0.0;
  double yaw = 0.0;
  iss >> x >> y >> yaw;

  NavTarget target;
  target.id = 1;
  target.frame_id = "map";
  target.goal.position = {x, y, 0.0};
  target.goal.orientation = {0.0, 0.0, yaw};
  StatusOk(robot.GetSlamNavController().SetNavTarget(target, 10000), "set_nav_target");
}

void GetNavigationStatus() {
  NavStatus nav_status;
  auto status = robot.GetSlamNavController().GetNavTaskStatus(nav_status);
  if (!StatusOk(status, "get_nav_status")) {
    return;
  }

  std::cout << "nav_status: id=" << nav_status.id
            << ", status=" << static_cast<int>(nav_status.status)
            << ", error=" << nav_status.error_code
            << ", desc=" << nav_status.error_desc << std::endl;
}

void SubscribeOdometry() {
  robot.GetSlamNavController().SubscribeOdometry([](const std::shared_ptr<Odometry> odom) {
    if (odom_counter++ % 30 == 0) {
      std::cout << "odom: pos=(" << odom->position[0] << ", "
                << odom->position[1] << ", " << odom->position[2] << "), lin=("
                << odom->linear_velocity[0] << ", " << odom->linear_velocity[1]
                << ", " << odom->linear_velocity[2] << ")" << std::endl;
    }
  });
  std::cout << "subscribe_odom: success" << std::endl;
}

bool InitializeControllers() {
  auto& audio = robot.GetAudioController();
  if (!audio.Initialize()) {
    std::cerr << "audio initialize failed" << std::endl;
  }

  auto status = robot.SetMotionControlLevel(ControllerLevel::HighLevel);
  if (!StatusOk(status, "set_motion_control_level(HighLevel)")) {
    return false;
  }

  auto& motion = robot.GetHighLevelMotionController();
  if (!motion.Initialize()) {
    std::cerr << "high-level motion initialize failed" << std::endl;
  }

  auto& monitor = robot.GetStateMonitor();
  if (!monitor.Initialize()) {
    std::cerr << "state monitor initialize failed" << std::endl;
  }

  auto& slam = robot.GetSlamNavController();
  if (!slam.Initialize()) {
    std::cerr << "slam navigation initialize failed" << std::endl;
  }

  return true;
}

void Cleanup() {
  auto& audio = robot.GetAudioController();
  auto& slam = robot.GetSlamNavController();

  audio.UnsubscribeDialogIntent();
  audio.UnsubscribeWakeupStatus();
  audio.UnsubscribeOriginAudioStream();
  audio.UnsubscribeBfAudioStream();
  slam.UnsubscribeOdometry();

  audio.Shutdown();
  robot.GetHighLevelMotionController().Shutdown();
  robot.GetStateMonitor().Shutdown();
  slam.Shutdown();
  robot.Disconnect();
  robot.Shutdown();
}

}  // namespace

int main() {
  std::signal(SIGINT, SignalHandler);

  PrintHelp();

  std::string local_ip = ReadLine("Enter local IP [192.168.54.111]: ");
  if (local_ip.empty()) {
    local_ip = "192.168.54.111";
  }

  if (!robot.Initialize(local_ip)) {
    std::cerr << "robot sdk initialize failed" << std::endl;
    robot.Shutdown();
    return -1;
  }

  auto status = robot.Connect();
  if (!StatusOk(status, "connect")) {
    robot.Shutdown();
    return -1;
  }

  if (!InitializeControllers()) {
    Cleanup();
    return -1;
  }

  std::cout << "Robot connected and controllers initialized." << std::endl;
  std::cout << "Press ? to print help, ESC to exit." << std::endl;

  while (running) {
    int key = Getch();
    if (key == 27) {
      break;
    }

    switch (key) {
      case '?':
        PrintHelp();
        break;
      case '1':
        GetVolume();
        break;
      case '2':
        SetVolume();
        break;
      case '3':
        PlayTts();
        break;
      case '4':
        StatusOk(robot.GetAudioController().Stop(), "stop_tts");
        break;
      case 'a':
        StartDialog();
        break;
      case 'b':
        StatusOk(robot.GetAudioController().StopDialog(), "stop_dialog");
        break;
      case '5':
        StatusOk(robot.GetAudioController().OpenAudioStream(), "open_audio_stream");
        break;
      case '6':
        StatusOk(robot.GetAudioController().CloseAudioStream(), "close_audio_stream");
        break;
      case '7':
        SubscribeAudioStreams();
        break;
      case '8':
        robot.GetAudioController().UnsubscribeOriginAudioStream();
        robot.GetAudioController().UnsubscribeBfAudioStream();
        std::cout << "unsubscribe_audio_stream: success" << std::endl;
        break;
      case 'q':
        StatusOk(robot.GetAudioController().OpenWakeupStatusStream(), "open_wakeup_stream");
        break;
      case 'w':
        StatusOk(robot.GetAudioController().CloseWakeupStatusStream(), "close_wakeup_stream");
        break;
      case 'e':
        SubscribeWakeupStatus();
        break;
      case 'r':
        robot.GetAudioController().UnsubscribeWakeupStatus();
        std::cout << "unsubscribe_wakeup: success" << std::endl;
        break;
      case 'z':
        SubscribeDialogIntent();
        break;
      case 'x':
        robot.GetAudioController().UnsubscribeDialogIntent();
        std::cout << "unsubscribe_dialog_intent: success" << std::endl;
        break;
      case '!':
        StatusOk(robot.GetHighLevelMotionController().SetGait(GaitMode::GAIT_RECOVERY_STAND, 10000),
                 "recovery_stand");
        break;
      case '@':
        StatusOk(robot.GetHighLevelMotionController().SetGait(GaitMode::GAIT_BALANCE_STAND, 10000),
                 "balance_stand");
        break;
      case '#':
        StatusOk(robot.GetHighLevelMotionController().ExecuteTrick(TrickAction::ACTION_WELCOME, 10000),
                 "execute_trick(ACTION_WELCOME)");
        break;
      case 'i':
        SendJoystick(0.0, 1.0, 0.0, 0.0);
        break;
      case 'k':
        SendJoystick(0.0, -1.0, 0.0, 0.0);
        break;
      case 'j':
        SendJoystick(-1.0, 0.0, 0.0, 0.0);
        break;
      case 'l':
        SendJoystick(1.0, 0.0, 0.0, 0.0);
        break;
      case 'u':
        SendJoystick(0.0, 0.0, -1.0, 0.0);
        break;
      case 'o':
        SendJoystick(0.0, 0.0, 1.0, 0.0);
        break;
      case 'p':
        SendJoystick(0.0, 0.0, 0.0, 0.0);
        break;
      case 'h':
        HeadMove();
        break;
      case 'm':
        RefreshState();
        break;
      case 'A':
        StatusOk(robot.GetSlamNavController().ActivateSlamMode(SlamMode::MAPPING, "", 10000),
                 "activate_mapping_mode");
        break;
      case 'B':
        StatusOk(robot.GetSlamNavController().StartMapping(10000), "start_mapping");
        break;
      case 'C':
        StatusOk(robot.GetSlamNavController().CancelMapping(10000), "cancel_mapping");
        break;
      case 'D':
        SaveMap();
        break;
      case 'E':
        LoadMap();
        break;
      case 'F':
        DeleteMap();
        break;
      case 'G':
        GetAllMapInfo();
        break;
      case 'H':
        GetMapPath();
        break;
      case 'I':
        GetPointCloudMap();
        break;
      case 'J':
        StatusOk(robot.GetSlamNavController().ActivateSlamMode(SlamMode::IDLE, "", 10000), "close_slam");
        break;
      case 'K':
        ActivateLocalizationMode();
        break;
      case 'L':
        InitPose();
        break;
      case 'M':
        GetLocalizationInfo();
        break;
      case 'N':
        ActivateNavigationMode();
        break;
      case 'O':
        SetNavigationTarget();
        break;
      case 'P':
        StatusOk(robot.GetSlamNavController().PauseNavTask(), "pause_nav");
        break;
      case 'R':
        StatusOk(robot.GetSlamNavController().ResumeNavTask(), "resume_nav");
        break;
      case 'S':
        StatusOk(robot.GetSlamNavController().CancelNavTask(), "cancel_nav");
        break;
      case 'T':
        GetNavigationStatus();
        break;
      case 'U':
        StatusOk(robot.GetSlamNavController().ActivateNavMode(NavMode::IDLE, "", 10000), "close_navigation");
        break;
      case 'V':
        StatusOk(robot.GetSlamNavController().OpenOdometryStream(), "open_odom_stream");
        break;
      case 'W':
        StatusOk(robot.GetSlamNavController().CloseOdometryStream(), "close_odom_stream");
        break;
      case 'X':
        SubscribeOdometry();
        break;
      case 'Y':
        robot.GetSlamNavController().UnsubscribeOdometry();
        std::cout << "unsubscribe_odom: success" << std::endl;
        break;
      default:
        std::cout << "Unknown key: " << key << ". Press ? for help." << std::endl;
        break;
    }

    usleep(10000);
  }

  Cleanup();
  return 0;
}

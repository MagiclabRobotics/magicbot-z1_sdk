#include "magic_robot.h"
#include "magic_sdk_version.h"

#include <chrono>
#include <cmath>
#include <csignal>
#include <iostream>
#include <mutex>
#include <string>
#include <termios.h>
#include <unistd.h>
#include <vector>

using namespace magic::z1;

magic::z1::MagicRobot robot;

// ---- 上肢/双手最新状态缓存(由订阅回调更新), 用于记录初始位姿与轨迹起始点 ----
static std::mutex g_state_mutex;
static std::vector<double> g_upper_pos;  // 最新上肢各关节位置
static std::vector<double> g_hand_pos;   // 最新双手手指位置(平铺: 左手所有指 + 右手所有指)
static std::vector<double> g_home_upper; // 初始位置(Home): 上肢关节
static std::vector<double> g_home_hand;  // 初始位置(Home): 双手手指
static std::vector<double> g_boot_upper; // 上电初始位资: 上肢关节(订阅首帧快照)
static std::vector<double> g_boot_hand;  // 上电初始位资: 双手手指
static bool g_home_valid = false;
static bool g_boot_valid = false;

void signalHandler(int signum) {
  std::cout << "\nInterrupt signal (" << signum << ") received.\n";
  robot.Shutdown();
  exit(signum);
}

void print_help() {
  std::cout << "Key Function Description:\n";
  std::cout << "Gait and Mode Functions:\n";
  std::cout << "  0        Function 0: Get gait\n";
  std::cout << "  1        Function 1: Set recovery stand gait\n";
  std::cout << "  2        Function 2: Switch to hybrid motion control level\n";
  std::cout << "\n";
  std::cout << "Joystick Functions:\n";
  std::cout << "  w        Function w: Move forward\n";
  std::cout << "  a        Function a: Move left\n";
  std::cout << "  s        Function s: Move backward\n";
  std::cout << "  d        Function d: Move right\n";
  std::cout << "  x        Function x: Stop\n";
  std::cout << "  t        Function t: Turn left\n";
  std::cout << "  g        Function g: Turn right\n";
  std::cout << "\n";
  std::cout << "Upper Body Functions:\n";
  std::cout << "  3        Function 3: Subscribe upper body state\n";
  std::cout << "  4        Function 4: Unsubscribe upper body state\n";
  std::cout << "  5        Function 5: Publish upper body command\n";
  std::cout << "  6        Function 6: Subscribe all hand state\n";
  std::cout << "  7        Function 7: Unsubscribe all hand state\n";
  std::cout << "  8        Function 8: Publish all hand command\n";
  std::cout << "\n";
  std::cout << "Arm/Hand Pose Functions:\n";
  std::cout << "  r        Record current arm & hand pose as reference pose\n";
  std::cout << "  f        Arms & hands move to reference pose\n";
  std::cout << "  h        Arms & hands return to boot pose\n";
  std::cout << "  z        Arms & hands return to all-zero pose\n";
  std::cout << "  m        Manual guide pose (enter joint angles one by one)\n";
  std::cout << "  n        Manual guide hand (enter finger angles one by one)\n";
  std::cout << "\n";
  std::cout << "  ESC      Exit program\n";
  std::cout << "  ?        Function ?: Print help\n";
}

// 主循环单键读取的统一入口。为了与 ManualGuidePose 的数值输入(getline)共用同一
// std::cin 流、避免 getchar/std::cin 字节缓冲相互竞争, 这里直接用 std::cin.get()。
// 调用前需处于是非行缓冲(ICANON off)状态, 以支持按键即响应; ManualGuidePose 进入
// 行缓冲前会排空脏输入, 退出后再清空, 保证与主循环无缝衔接。
static int GetKey() {
  char ch = 0;
  // 设置 stdin 为原始模式(非缓冲), 这样 std::cin.get() 也能立即返回, 无需回车
  struct termios t;
  tcgetattr(STDIN_FILENO, &t);
  t.c_lflag &= ~(ICANON | ECHO);
  t.c_cc[VMIN] = 1;
  t.c_cc[VTIME] = 0;
  tcsetattr(STDIN_FILENO, TCSANOW, &t);
  if (std::cin.get(ch)) {
    return static_cast<unsigned char>(ch);
  }
  return EOF;
}

void GetGait() {
  auto& controller = robot.GetHighLevelMotionController();
  GaitMode gait_mode;
  auto status = controller.GetGait(gait_mode);
  if (status.code != ErrorCode::OK) {
    std::cerr << "get robot gait failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    return;
  }
  std::cout << "robot gait: " << static_cast<int>(gait_mode) << std::endl;
}

void SetRecoveryStandGait() {
  auto& controller = robot.GetHighLevelMotionController();
  auto status = controller.SetGait(GaitMode::GAIT_RECOVERY_STAND, 10000);
  if (status.code != ErrorCode::OK) {
    std::cerr << "set robot gait failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    return;
  }
  std::cout << "robot gait set to GAIT_RECOVERY_STAND successfully." << std::endl;
}

void SetHybridMode() {
  auto& controller = robot.GetHighLevelMotionController();
  auto status = controller.SetGait(GaitMode::GAIT_HYBRID_SDK, 10000);
  if (status.code != ErrorCode::OK) {
    std::cerr << "set robot gait failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    return;
  }
  std::cout << "robot gait set to GAIT_HYBRID_SDK successfully." << std::endl;
}

void JoyStickCommand(float left_x_axis, float left_y_axis, float right_x_axis, float right_y_axis) {
  auto& controller = robot.GetHighLevelMotionController();
  JoystickCommand joy_command;
  joy_command.left_x_axis = left_x_axis;
  joy_command.left_y_axis = left_y_axis;
  joy_command.right_x_axis = right_x_axis;
  joy_command.right_y_axis = right_y_axis;
  auto status = controller.SendJoyStickCommand(joy_command);
  if (status.code != ErrorCode::OK) {
    std::cerr << "send joystick command failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    usleep(50000);
    return;
  }
  usleep(50000);
}

void SubscribeUpperBodyState() {
  auto& controller = robot.GetUpperBodyMotionController();
  auto printed = std::make_shared<bool>(false);
  controller.SubscribeUpperBodyState([printed](const std::shared_ptr<JointState> msg) {
    // 缓存最新位置(加锁), 供记录参考位/返回初位使用
    {
      std::lock_guard<std::mutex> lock(g_state_mutex);
      g_upper_pos.resize(msg->joints.size());
      for (int ii = 0; ii < static_cast<int>(msg->joints.size()); ii++) {
        g_upper_pos[ii] = msg->joints[ii].posL;  // 用实际位置(posL)
      }
      if (!g_boot_valid) {
        g_boot_upper = g_upper_pos;
        g_boot_valid = true;
      }
    }
    // 仅打印一次首帧, 避免刷屏
    if (!*printed) {
      *printed = true;
      std::cout << "--- upper body state (first frame) ---" << std::endl;
      for (int ii = 0; ii < static_cast<int>(msg->joints.size()); ii++) {
        std::cout << "joint " << ii << " posL=" << msg->joints[ii].posL
                  << ", posH=" << msg->joints[ii].posH
                  << ", vel=" << msg->joints[ii].vel
                  << ", toq=" << msg->joints[ii].toq << std::endl;
      }
      std::cout << "---------------------------------------" << std::endl;
    }
  });
  std::cout << "[subscribe] upper body state subscribed.\n";
}

void UnsubscribeUpperBodyState() {
  auto& controller = robot.GetUpperBodyMotionController();
  controller.UnsubscribeUpperBodyState();
}

void PublishUpperBodyCommand() {
  auto& controller = robot.GetUpperBodyMotionController();

  JointCommand command;
  command.timestamp = std::chrono::duration_cast<std::chrono::nanoseconds>(
                          std::chrono::system_clock::now().time_since_epoch())
                          .count();
  command.motion_mode = 1;
  command.joints.resize(kArmJointNum + kWaistJointNum + kHeadJointNum);
  static double pos = 0.0;
  for (auto& joint : command.joints) {
    joint.operation_mode = 3;
    joint.pos = pos;
    joint.vel = 0.0;
    joint.toq = 0.0;
    joint.kp = 0.0;
    joint.kd = 0.0;
  }

  // command.joints[0].pos = 0.01;
  // command.joints[1].pos = 0.11;
  // command.joints[2].pos = 1.18;
  // command.joints[3].pos = -0.51;
  // command.joints[4].pos = -1.49;
  // command.joints[5].pos = 0.0;
  // command.joints[6].pos = 0.0;

  // command.joints[7].pos = 0.01;
  // command.joints[8].pos = -0.11;
  // command.joints[9].pos = -1.18;
  // command.joints[10].pos = 0.51;
  // command.joints[11].pos = 1.49;
  // command.joints[12].pos = 0.0;
  // command.joints[13].pos = 0.0;

  // command.joints[14].pos = 0.0;  // waist
  // command.joints[15].pos = 0.0;  // head yaw
  // command.joints[16].pos = 0.0;  // head pitch

  // command.joints[0].kp = 5.0;
  // command.joints[0].kd = 40.0;
  // command.joints[1].kp = 5.0;
  // command.joints[1].kd = 40.0;
  // for (int ii = 2; ii <= 13; ++ii) {
  //   command.joints[ii].kp = 10.0;
  //   command.joints[ii].kd = 25.0;
  // }
  // command.joints[14].kp = 50.0;
  // command.joints[14].kd = 200.0;
  // command.joints[15].kp = 250.0;
  // command.joints[15].kd = 10.0;
  // command.joints[16].kp = 250.0;
  // command.joints[16].kd = 10.0;

  auto status = controller.PublishUpperBodyCommand(command);
  if (status.code != ErrorCode::OK) {
    std::cerr << "publish upper body command failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    return;
  }
  std::cout << status.message << std::endl;
}

void SubscribeAllHandState() {
  auto& controller = robot.GetUpperBodyMotionController();
  auto printed = std::make_shared<bool>(false);
  controller.SubscribeAllHandState([printed](const std::shared_ptr<AllHandState> msg) {
    // 缓存最新手指位置(平铺: 左手所有指 + 右手所有指)
    {
      std::lock_guard<std::mutex> lock(g_state_mutex);
      g_hand_pos.clear();
      for (const auto& hand : msg->state) {
        g_hand_pos.insert(g_hand_pos.end(), hand.pos.begin(), hand.pos.end());
      }
      if (!g_boot_valid) {
        g_boot_hand = g_hand_pos;
      }
    }
    // 仅打印一次首帧, 避免刷屏
    if (!*printed) {
      *printed = true;
      std::cout << "--- all hand state (first frame) ---" << std::endl;
      for (int ii = 0; ii < static_cast<int>(msg->state.size()); ii++) {
        std::cout << "hand " << ii << " pos:";
        for (double p : msg->state[ii].pos) {
          std::cout << " " << p;
        }
        std::cout << std::endl;
      }
      std::cout << "------------------------------------" << std::endl;
    }
  });
  std::cout << "[subscribe] all hand state subscribed.\n";
}

void UnsubscribeAllHandState() {
  auto& controller = robot.GetUpperBodyMotionController();
  controller.UnsubscribeAllHandState();
}

void PublishAllHandCommand() {
  auto& controller = robot.GetUpperBodyMotionController();
  HandCommand command;
  command.timestamp = std::chrono::duration_cast<std::chrono::nanoseconds>(
                          std::chrono::system_clock::now().time_since_epoch())
                          .count();
  command.cmd.resize(kHandNum);
  static double pos = 0.0;
  for (int ii = 0; ii < kHandNum; ii++) {
    command.cmd[ii].operation_mode = 1;
    command.cmd[ii].pos.resize(kHandJointNum);
    for (int jj = 0; jj < kHandJointNum; jj++) {
      command.cmd[ii].pos[jj] = pos;
    }
  }

  if (kHandNum >= 2 && kHandJointNum >= 6) {
    command.cmd[0].pos[0] = 2.77;
    command.cmd[0].pos[1] = 2.77;
    command.cmd[0].pos[2] = 2.77;
    command.cmd[0].pos[3] = 2.77;
    command.cmd[0].pos[4] = 0.77;
    command.cmd[0].pos[5] = 2.81;

    command.cmd[1].pos[0] = 2.77;
    command.cmd[1].pos[1] = 2.77;
    command.cmd[1].pos[2] = 2.77;
    command.cmd[1].pos[3] = 2.77;
    command.cmd[1].pos[4] = 0.77;
    command.cmd[1].pos[5] = 2.81;
  }

  controller.PublishAllHandCommand(command);
}

// ============ V3/V5 关节配置 (与 bridge 的 JOINT_NAME_LIST / URDF 一致) ============
// 上肢关节顺序均为: 左臂 + 右臂 + 腰(joint_wy) + 头(joint_hy)
//  - V3: 左臂 5 关节 joint_la1..5, 右臂 5 关节 joint_ra1..5  => 上肢 5+5+1+1 = 12 关节
//  - V5: 左臂 7 关节 joint_la1..7, 右臂 7 关节 joint_ra1..7  => 上肢 7+7+1+1 = 16 关节
// operation_mode=3(混合控制); toq 为力矩上限(Nm, 可带方向)。
// 运行时根据 GetArmJointNum() (V3=10, V5=14) 自动选用对应配置。

// ---- V3 配置 ----
static const char* kUpperNamesV3[] = {
    "joint_la1", "joint_la2", "joint_la3", "joint_la4", "joint_la5",
    "joint_ra1", "joint_ra2", "joint_ra3", "joint_ra4", "joint_ra5",
    "joint_wy",  "joint_hy",
};
static const double kArmKpV3[] = {500, 500, 300, 500, 350, 500, 500, 300, 500, 350, 60, 50};
static const double kArmKdV3[] = {7,   7,   7,   7,   7,   7,   7,   7,   7,   7,   6,   8};
static const double kArmToqV3[] = {-5,  4,   0,  -3,   0,  -5,  -4,   0,  -3,   0,   0,   0};
static const double kArmPosMinV3[] = {-2.88, -0.175, -2.618, -0.96, -1.571, -2.88, -2.2515, -2.618, -0.96, -1.571, -2.79, -0.6981};
static const double kArmPosMaxV3[] = { 2.88,  2.2515,  2.618,  1.5708,  1.571,  2.88,  0.175,  2.618,  1.5708,  1.571,  2.79,  0.6981};

// ---- V5 配置 (来自 bridge_MagicBotZ1V5_HandS01.py 与 MagicBotZ1V5_HandS01.urdf) ----
static const char* kUpperNamesV5[] = {
    "joint_la1", "joint_la2", "joint_la3", "joint_la4", "joint_la5", "joint_la6", "joint_la7",
    "joint_ra1", "joint_ra2", "joint_ra3", "joint_ra4", "joint_ra5", "joint_ra6", "joint_ra7",
    "joint_wy",  "joint_hy",
};
static const double kArmKpV5[] = {500,500,300,500,350,300,300, 500,500,300,500,350,300,300, 60,50};
static const double kArmKdV5[] = {7,7,7,7,7,7,7, 7,7,7,7,7,7,7, 6,8};
static const double kArmToqV5[] = {-5,4,0,-3,0,0,0, -5,-4,0,-3,0,0,0, 0,0};
static const double kArmPosMinV5[] = {-2.7925, -0.175,  -2.618, -0.96, -1.5708, -1.5708, -1.5708,
                                      -2.7925, -2.2515, -2.618, -0.96, -1.5708, -1.5708, -1.5708,
                                      -2.79,   -0.6981};
static const double kArmPosMaxV5[] = { 2.7925,  2.2515,  2.618,  1.5708,  1.5708,  1.5708,  1.5708,
                                       2.7925,  0.175,   2.618,  1.5708,  1.5708,  1.5708,  1.5708,
                                       2.79,    0.6981};

// 当前的关节配置指针(运行时按型号选择)
static int kUpperJointCount = 12;
static const char** kUpperJointNames = kUpperNamesV3;
static const double* kArmKp = kArmKpV3;
static const double* kArmKd = kArmKdV3;
static const double* kArmToq = kArmToqV3;
static const double* kArmPosMin = kArmPosMinV3;
static const double* kArmPosMax = kArmPosMaxV3;

// 在 main 中 Initialize 后根据实际型号切换配置
static void SetupJointConfig() {
  int arm = GetArmJointNum();  // V3=10, V5=14
  if (arm == 14) {
    kUpperJointCount = 16;
    kUpperJointNames = kUpperNamesV5;
    kArmKp = kArmKpV5;
    kArmKd = kArmKdV5;
    kArmToq = kArmToqV5;
    kArmPosMin = kArmPosMinV5;
    kArmPosMax = kArmPosMaxV5;
    std::cout << "[config] RobotType=V5 (arm=14), upper joints=16\n";
  } else {
    kUpperJointCount = 12;
    kUpperJointNames = kUpperNamesV3;
    kArmKp = kArmKpV3;
    kArmKd = kArmKdV3;
    kArmToq = kArmToqV3;
    kArmPosMin = kArmPosMinV3;
    kArmPosMax = kArmPosMaxV3;
    std::cout << "[config] RobotType=V3 (arm=10), upper joints=12\n";
  }
}

// 平滑运动时长(秒)与频率
const double kMoveDuration = 2.0;
const int kMoveHz = 500;

// ============ 手部关节配置 ============
// 每只手 6 关节, 顺序: 小指、无名指、中指、食指、大拇指弯曲、大拇指内外旋转(与 bridge/URDF 一致)。
// g_hand_pos 缓存为: 左手6 + 右手6 平铺, 索引 0..5 左, 6..11 右。
static const int kHandJointPerHand = 6;
static const char* kHandJointNames[kHandJointPerHand] = {
    "little", "ring", "middle", "forefinger", "thumb_bend", "thumb_rot",
};
// 手部范围(rad), 取自 bridge HAND_JOINT_POS_MIN/MAX 与 URDF:
// 四指[0.5,2.76], 大拇指弯曲[0.3,0.7], 大拇指内外旋转[1.63,2.72]
static const double kHandPosMin[kHandJointPerHand] = {0.5, 0.5, 0.5, 0.5, 0.3, 1.63};
static const double kHandPosMax[kHandJointPerHand] = {2.76, 2.76, 2.76, 2.76, 0.7, 2.72};

// 把目标关节角度约束到安全范围内(越界则提示并返回是否越界)
static bool ClampJointPos(int idx, double& pos) {
  if (idx < 0 || idx >= kUpperJointCount) {
    return false;
  }
  double lo = kArmPosMin[idx];
  double hi = kArmPosMax[idx];
  if (pos < lo || pos > hi) {
    std::cerr << "[clamp] joint " << idx << " (" << kUpperJointNames[idx]
              << ") target " << pos << " out of range [" << lo << ", " << hi << "]. Ignored." << std::endl;
    return false;
  }
  return true;
}

// 从缓存快照读取当前实际位置, 返回是否有效(已有数据)
// 注意: 手部数据可能为空(真机未启用手部或型号不匹配), 此时手部目标维持不动。
static bool GetCurrentPose(std::vector<double>& upper, std::vector<double>& hand) {
  std::lock_guard<std::mutex> lock(g_state_mutex);
  if (g_upper_pos.empty()) {
    return false;
  }
  upper = g_upper_pos;
  hand = g_hand_pos;  // 可能为空, 调用方处理
  return true;
}

// ============ 手动引导摆位 ============
// 注意: kUpperJointCount / kUpperJointNames / 各关节增益与范围在文件上方已定义

// 从缓存读取一个关节的当前实际角度
static double GetJointCurrentPos(int idx) {
  std::lock_guard<std::mutex> lock(g_state_mutex);
  if (idx >= 0 && idx < static_cast<int>(g_upper_pos.size())) {
    return g_upper_pos[idx];
  }
  return 0.0;
}

// 在输入数值时临时恢复行缓冲, 结束/中止时切回无缓冲模式
// 切换前会排空 std::cin 的脏字节, 避免残留影响后续输入。
static void SetCanonicalMode(bool canonical) {
  if (!canonical) {
    // 切回非行缓冲前, 丢弃残留的脏字节
    std::cin.clear();
    std::cin.ignore(std::cin.rdbuf()->in_avail());
    // 清理 stdin 文件描述符缓冲区
    struct termios t;
    tcgetattr(STDIN_FILENO, &t);
    t.c_cc[VMIN] = 0;
    t.c_cc[VTIME] = 0;
    tcsetattr(STDIN_FILENO, TCSANOW, &t);
    int c;
    while ((c = getchar()) != EOF && c != '\n');
    ungetc(c, stdin);
    t.c_cc[VMIN] = 1;
    t.c_cc[VTIME] = 0;
    tcsetattr(STDIN_FILENO, TCSANOW, &t);
  }
  struct termios t;
  if (tcgetattr(STDIN_FILENO, &t) != 0) {
    return;
  }
  if (canonical) {
    t.c_lflag |= (ICANON | ECHO);
  } else {
    t.c_lflag &= ~(ICANON | ECHO);
  }
  tcsetattr(STDIN_FILENO, TCSANOW, &t);
}

// 一次性发布整组 12 关节目标(joint_la1..5 / ra1..5 / wy / hy),
// 机器人整体动作到该组角度。
static void MoveToGroup(const std::vector<double>& target_upper, const std::vector<double>& target_hand) {  auto& ctrl = robot.GetUpperBodyMotionController();

  JointCommand cmd;
  cmd.motion_mode = 1;  // movej
  cmd.joints.resize(kArmJointNum + kWaistJointNum + kHeadJointNum);

  // vel 取当前实际速度(非 0), 每个关节用配置的 kp/kd/toq
  std::vector<double> cur_upper, cur_hand;
  GetCurrentPose(cur_upper, cur_hand);  // 拿不到则用 0 兜底
  for (int i = 0; i < static_cast<int>(cmd.joints.size()); ++i) {
    cmd.joints[i].operation_mode = 3;                          // 混合控制
    cmd.joints[i].pos = (i < static_cast<int>(target_upper.size())) ? target_upper[i] : 0.0;
    // vel: 用当前实际速度。拿不到实际速度用 0。
    cmd.joints[i].vel = 0.0;  // 若拿到原始关节速度缓存, 这里应填实际 vel; 当前缓存不含 vel, 保守用 0
    cmd.joints[i].toq = (i < kUpperJointCount) ? kArmToq[i] : 0.0;
    cmd.joints[i].kp = (i < kUpperJointCount) ? kArmKp[i] : 0.0;
    cmd.joints[i].kd = (i < kUpperJointCount) ? kArmKd[i] : 0.0;
  }
  cmd.timestamp = std::chrono::duration_cast<std::chrono::nanoseconds>(
                      std::chrono::system_clock::now().time_since_epoch()).count();
  ctrl.PublishUpperBodyCommand(cmd);

  // 手部:无论是否有数据都发布(空则全 0)
  {
    HandCommand hand_cmd;
    hand_cmd.timestamp = cmd.timestamp;
    hand_cmd.cmd.resize(kHandNum);
    for (int h = 0; h < kHandNum; ++h) {
      hand_cmd.cmd[h].operation_mode = 4;  // 与 bridge 一致: 位置控制模式
      hand_cmd.cmd[h].pos.resize(kHandJointNum, 0.0);
      for (int f = 0; f < kHandJointNum; ++f) {
        int idx = h * kHandJointNum + f;
        hand_cmd.cmd[h].pos[f] = (idx < static_cast<int>(target_hand.size())) ? target_hand[idx] : 0.0;
      }
    }
    ctrl.PublishAllHandCommand(hand_cmd);
  }
  std::cout << "[move] published 12-joint command (movej).\n";
}

// 手动引导: 一次收集 12 关节目标, 最后一次性发布。
static void ManualGuidePose() {
  std::vector<double> start_upper, start_hand;
  if (!GetCurrentPose(start_upper, start_hand)) {
    std::cerr << "[guide] no state cache yet. Press 3 to subscribe then wait.\n";
    return;
  }
  if (start_upper.size() < static_cast<size_t>(kUpperJointCount)) {
    std::cerr << "[guide] unexpected upper joint count: " << start_upper.size() << std::endl;
    return;
  }

  std::vector<double> target_upper = start_upper;  // 默认全部保持当前
  // 灵巧手控制值 = 读取当前灵巧手关节数据; 无则全 0
  std::vector<double> target_hand;
  if (!start_hand.empty()) {
    target_hand = start_hand;
  } else {
    target_hand.assign(kHandNum * kHandJointNum, 0.0);
    std::cout << "[guide] 未检测到灵巧手数据, 灵巧手控制值取全 0。\n";
  }
  std::cout << "\n==== 手动引导摆位: 一次输入 12 关节目标, 最后一次性发布 ====\n";
  std::cout << "对每个关节输入目标角(rad), 回车=保持当前; 输入 q=中止; 全部输完后一次发布。\n";

  SetCanonicalMode(true);  // 行缓冲以支持输入
  std::string line;
  bool aborted = false;
  for (int i = 0; i < kUpperJointCount; ++i) {
    double cur = GetJointCurrentPos(i);
    std::cout << "\n  [" << i << "] " << kUpperJointNames[i]
              << "  当前 " << cur << "  范围 [" << kArmPosMin[i] << ", " << kArmPosMax[i] << "] rad\n";
    std::cout << "     输入目标角 [回车=保持, q=中止]: " << std::flush;
    if (!std::getline(std::cin, line)) {
      std::cin.clear();
      break;
    }
    size_t first = line.find_first_not_of(" \t");
    if (line.empty() || first == std::string::npos) {
      std::cout << "[guide] keep " << kUpperJointNames[i] << " = " << cur << std::endl;
      continue;
    }
    if (line[first] == 'q' || line[first] == 'Q') {
      std::cout << "[guide] aborted.\n";
      aborted = true;
      break;
    }
    double target;
    try {
      target = std::stod(line.substr(first));
    } catch (const std::exception&) {
      std::cout << "[guide] invalid, keep = " << cur << std::endl;
      continue;
    }
    if (!ClampJointPos(i, target)) {
      continue;
    }
    target_upper[i] = target;
    std::cout << "[guide] set " << kUpperJointNames[i] << " = " << target << std::endl;
  }
  SetCanonicalMode(false);
  if (aborted) {
    return;
  }

  std::cout << "\n==== 发布整组目标 ====\n";
  std::cout << "关节目标 (rad):\n";
  for (int i = 0; i < kUpperJointCount; ++i) {
    std::cout << "  [" << i << "] " << kUpperJointNames[i] << " = " << target_upper[i] << std::endl;
  }
  MoveToGroup(target_upper, target_hand);
  std::cout << "[guide] 已发布. 按 'r' 记录此姿态为参考位, 之后按 'f' 可复现。\n";
}

// 约束手部关节角度到范围(越界则提示并返回是否越界)
static bool ClampHandPos(int idx, double& pos) {
  if (idx < 0 || idx >= kHandJointPerHand) {
    return false;
  }
  double lo = kHandPosMin[idx];
  double hi = kHandPosMax[idx];
  if (pos < lo || pos > hi) {
    std::cerr << "[clamp] hand joint " << idx << " (" << kHandJointNames[idx]
              << ") target " << pos << " out of range [" << lo << ", " << hi << "]. Ignored." << std::endl;
    return false;
  }
  return true;
}

// 手部手动引导: 像 m 一样逐指输入目标角, 左/右手各6指, 最后一次性发布。
// 无论灵巧手是否有数据都发完整指令(arm+hand):
// - 手臂控制值取当前实际位置(start_upper)
// - 灵巧手控制值由本次输入决定(target_hand; 无初始数据则从全0起)
static void ManualGuideHand() {
  std::vector<double> start_upper, start_hand;
  if (!GetCurrentPose(start_upper, start_hand)) {
    std::cerr << "[guide] no state cache yet. Press 3 to subscribe then wait.\n";
    return;
  }

  std::vector<double> target_hand = start_hand;
  if (target_hand.empty()) {
    target_hand.assign(kHandNum * kHandJointNum, 0.0);  // 无灵巧手数据, 从全0起
  }
  std::cout << "\n==== 手动引导摆位 - 双手: 一次输入双手目标, 最后一次性发布 ====\n";
  std::cout << "每只手 6 指: " << kHandJointNames[0] << ", " << kHandJointNames[1] << ", "
            << kHandJointNames[2] << ", " << kHandJointNames[3] << ", "
            << kHandJointNames[4] << ", " << kHandJointNames[5] << "\n";
  std::cout << "回车=保持当前; 输入 q=中止; 全部输完后一次发布。\n";

  SetCanonicalMode(true);
  std::string line;
  bool aborted = false;
  for (int h = 0; h < kHandNum && !aborted; ++h) {
    std::cout << "\n--- " << (h == 0 ? "左手" : "右手") << " ---\n";
    for (int f = 0; f < kHandJointPerHand; ++f) {
      int idx = h * kHandJointPerHand + f;
      double cur = (idx < static_cast<int>(start_hand.size())) ? start_hand[idx] : 0.0;
      std::cout << "  [" << idx << "] " << kHandJointNames[f]
                << "  当前 " << cur << "  范围 [" << kHandPosMin[f] << ", " << kHandPosMax[f] << "] rad\n";
      std::cout << "     输入目标角 [回车=保持, q=中止]: " << std::flush;
      if (!std::getline(std::cin, line)) {
        std::cin.clear();
        aborted = true;
        break;
      }
      size_t first = line.find_first_not_of(" \t");
      if (line.empty() || first == std::string::npos) {
        std::cout << "[guide] keep hand " << idx << " (" << kHandJointNames[f] << ") = " << cur << std::endl;
        continue;
      }
      if (line[first] == 'q' || line[first] == 'Q') {
        std::cout << "[guide] aborted.\n";
        aborted = true;
        break;
      }
      double target;
      try {
        target = std::stod(line.substr(first));
      } catch (const std::exception&) {
        std::cout << "[guide] invalid, keep = " << cur << std::endl;
        continue;
      }
      if (idx >= static_cast<int>(target_hand.size())) {
        continue;
      }
      if (!ClampHandPos(f, target)) {
        continue;
      }
      target_hand[idx] = target;
      std::cout << "[guide] set hand " << idx << " (" << kHandJointNames[f] << ") = " << target << std::endl;
    }
  }
  SetCanonicalMode(false);
  if (aborted) {
    return;
  }

  std::cout << "\n==== 发布双手目标 ====\n";
  for (int h = 0; h < kHandNum; ++h) {
    std::cout << (h == 0 ? "  左手: " : "  右手: ");
    for (int f = 0; f < kHandJointPerHand; ++f) {
      int idx = h * kHandJointPerHand + f;
      std::cout << kHandJointNames[f] << "=" << target_hand[idx] << "  ";
    }
    std::cout << std::endl;
  }
  MoveToGroup(start_upper, target_hand);
  std::cout << "[guide] 已发布双手. 按 'r' 记录此姿态为参考位, 之后按 'f' 可复现。\n";
}

// 把当前实际位置记录为参考位(Home)。要求已订阅并收到过上肢与手部状态。
static void RecordReference() {
  std::vector<double> upper, hand;
  if (!GetCurrentPose(upper, hand)) {
    std::cerr << "[record] no upper-body state cache yet. Press 3 to subscribe, then wait a moment.\n";
    return;
  }
  std::lock_guard<std::mutex> lock(g_state_mutex);
  g_home_upper = upper;
  g_home_hand = hand;  // 可能为空(手机未启用手部), 运动时手部保持不动
  g_home_valid = true;
  std::cout << "[record] reference pose recorded. upper=" << upper.size()
            << " joints, hand=" << hand.size() << " fingers.\n";
}

// 双臂(+双手)运动到 target: 一次性发布整组目标(和 bridge 一致)
static void MoveTo(const std::vector<double>& target_upper, const std::vector<double>& target_hand,
                   double duration) {
  (void)duration;  // 一次性 movej, 不需插值时长(嵌入式自行插值)
  MoveToGroup(target_upper, target_hand);
  std::cout << "[move] reached target pose.\n";
}

// 双臂+双手运动到参考位
static void MoveToReference() {
  std::vector<double> upper, hand;
  {
    std::lock_guard<std::mutex> lock(g_state_mutex);
    if (!g_home_valid) {
      std::cerr << "[move] no reference recorded. Press 'r' to record current pose first.\n";
      return;
    }
    upper = g_home_upper;
    hand = g_home_hand;
  }
  std::cout << "[move] moving to reference pose...\n";
  MoveTo(upper, hand, kMoveDuration);
}

// 双臂+双手返回上电初始位姿(开机后订阅到的首帧实际位置)
static void MoveToHome() {
  std::vector<double> upper, hand;
  {
    std::lock_guard<std::mutex> lock(g_state_mutex);
    if (!g_boot_valid || g_boot_upper.empty()) {
      std::cerr << "[move] no boot pose yet. Press 3 to subscribe, then wait a moment.\n";
      return;
    }
    upper = g_boot_upper;
    hand = g_boot_hand;  // 可能为空(未启用手部), 运动时手部保持不动
  }
  std::cout << "[move] returning all arms & hands to boot pose...\n";
  MoveTo(upper, hand, kMoveDuration);
}

// 双臂+双手返回全零位
static void MoveToZero() {
  std::vector<double> upper(static_cast<size_t>(kArmJointNum + kWaistJointNum + kHeadJointNum), 0.0);
  std::vector<double> hand(static_cast<size_t>(kHandNum * kHandJointNum), 0.0);
  std::cout << "[move] returning all arms & hands to all-zero pose...\n";
  MoveTo(upper, hand, kMoveDuration);
}

int main() {
  signal(SIGINT, signalHandler);

  std::cout << "SDK Version: " << SDK_VERSION_STRING << std::endl;
  print_help();

  std::string local_ip = "192.168.54.111";
  if (!robot.Initialize(local_ip)) {
    std::cerr << "robot sdk initialize failed." << std::endl;
    robot.Shutdown();
    return -1;
  }
  // 根据实际型号(V3/V5)选择关节配置(手臂数量、名称、增益、范围)
  SetupJointConfig();

  auto status = robot.Connect();
  if (status.code != ErrorCode::OK) {
    std::cerr << "connect robot failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    robot.Shutdown();
    return -1;
  }

  std::cout << "Press any key to continue (ESC to exit)..." << std::endl;

  while (1) {
    // 统一用 std::cin 读取单字符(非行缓冲), 按键即响应
    int key = GetKey();
    if (key == 27 || key == EOF) {
      break;
    }
    std::cout << "Key ASCII: " << key << ", Character: " << static_cast<char>(key) << std::endl;

    switch (key) {
      case '0':
        GetGait();
        break;
      case '1':
        SetRecoveryStandGait();
        break;
      case '2':
        SetHybridMode();
        break;
      case 'w':
      case 'W':
        JoyStickCommand(0.0, 1.0, 0.0, 0.0);
        break;
      case 'a':
      case 'A':
        JoyStickCommand(-1.0, 0.0, 0.0, 0.0);
        break;
      case 's':
      case 'S':
        JoyStickCommand(0.0, -1.0, 0.0, 0.0);
        break;
      case 'd':
      case 'D':
        JoyStickCommand(1.0, 0.0, 0.0, 0.0);
        break;
      case 'x':
      case 'X':
        JoyStickCommand(0.0, 0.0, 0.0, 0.0);
        break;
      case 't':
      case 'T':
        JoyStickCommand(0.0, 0.0, -1.0, 0.0);
        break;
      case 'g':
      case 'G':
        JoyStickCommand(0.0, 0.0, 1.0, 0.0);
        break;
      case '3':
        SubscribeUpperBodyState();
        break;
      case '4':
        UnsubscribeUpperBodyState();
        break;
      case '5':
        PublishUpperBodyCommand();
        break;
      case '6':
        SubscribeAllHandState();
        break;
      case '7':
        UnsubscribeAllHandState();
        break;
      case '8':
        PublishAllHandCommand();
        break;
      case 'r':
      case 'R':
        RecordReference();
        break;
      case 'f':
      case 'F':
        MoveToReference();
        break;
      case 'h':
      case 'H':
        MoveToHome();
        break;
      case 'z':
      case 'Z':
        MoveToZero();
        break;
      case 'm':
      case 'M':
        ManualGuidePose();
        break;
      case 'n':
      case 'N':
        ManualGuideHand();
        break;
      case '?':
        print_help();
        break;
      default:
        std::cout << "Unknown key: " << key << std::endl;
        break;
    }
    usleep(10000);
  }

  // 退出前切回行缓冲并停止持续发布
  SetCanonicalMode(true);
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

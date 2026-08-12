#!/usr/bin/env python3

import gc
import logging
import signal
import sys
import termios
import threading
import time
import tty
from typing import Optional

import magicbot_z1_python as magicbot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

robot: Optional[magicbot.MagicRobot] = None
running = True
pos = 0.0
upper_body_state_counter = 0
all_hand_state_counter = 0

# ---- 状态缓存(由订阅回调更新), 用于记录初始位资与轨迹 ----
upper_pos_lock = threading.Lock()  # noqa (暂用 list + GIL, 简单同步)
cur_upper_pos: list = []   # 最新上肢关节位置(12)
cur_hand_pos: list = []    # 最新双手手指位置(左手6 + 右手6 平铺)
boot_upper: list = []      # 上电初始位资(首帧快照)
boot_hand: list = []
boot_valid = False
# 参考位
home_upper: list = []
home_hand: list = []
home_valid = False

# 与 C++/bridge 相同的关节配置。运行时按型号(V3/V5)选用:
# 上肢关节顺序均为 左臂 + 右臂 + 腰(joint_wy) + 头(joint_hy)
#  - V3: 左臂5(joint_la1..5) + 右臂5(joint_ra1..5) + 腰 + 头 = 12 关节
#  - V5: 左臂7(joint_la1..7) + 右臂7(joint_ra1..7) + 腰 + 头 = 16 关节

# ---- V3 配置 ----
UPPER_JOINT_NAMES_V3 = [
    "joint_la1", "joint_la2", "joint_la3", "joint_la4", "joint_la5",
    "joint_ra1", "joint_ra2", "joint_ra3", "joint_ra4", "joint_ra5",
    "joint_wy",  "joint_hy",
]
ARM_KP_V3 = [500, 500, 300, 500, 350, 500, 500, 300, 500, 350, 60, 50]
ARM_KD_V3 = [7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 6, 8]
ARM_TOQ_V3 = [-5, 4, 0, -3, 0, -5, -4, 0, -3, 0, 0, 0]
ARM_POS_MIN_V3 = [-2.88, -0.175, -2.618, -0.96, -1.571, -2.88, -2.2515, -2.618, -0.96, -1.571, -2.79, -0.6981]
ARM_POS_MAX_V3 = [2.88, 2.2515, 2.618, 1.5708, 1.571, 2.88, 0.175, 2.618, 1.5708, 1.571, 2.79, 0.6981]

# ---- V5 配置 ----
UPPER_JOINT_NAMES_V5 = [
    "joint_la1", "joint_la2", "joint_la3", "joint_la4", "joint_la5", "joint_la6", "joint_la7",
    "joint_ra1", "joint_ra2", "joint_ra3", "joint_ra4", "joint_ra5", "joint_ra6", "joint_ra7",
    "joint_wy",  "joint_hy",
]
ARM_KP_V5 = [500,500,300,500,350,300,300, 500,500,300,500,350,300,300, 60,50]
ARM_KD_V5 = [7,7,7,7,7,7,7, 7,7,7,7,7,7,7, 6,8]
ARM_TOQ_V5 = [-5,4,0,-3,0,0,0, -5,-4,0,-3,0,0,0, 0,0]
ARM_POS_MIN_V5 = [-2.7925, -0.175, -2.618, -0.96, -1.5708, -1.5708, -1.5708,
                  -2.7925, -2.2515, -2.618, -0.96, -1.5708, -1.5708, -1.5708,
                  -2.79, -0.6981]
ARM_POS_MAX_V5 = [2.7925, 2.2515, 2.618, 1.5708, 1.5708, 1.5708, 1.5708,
                  2.7925, 0.175,  2.618, 1.5708, 1.5708, 1.5708, 1.5708,
                  2.79,   0.6981]

# 当前生效的配置(initialize 后按型号选择)
UPPER_JOINT_NAMES = UPPER_JOINT_NAMES_V3
ARM_KP = ARM_KP_V3
ARM_KD = ARM_KD_V3
ARM_TOQ = ARM_TOQ_V3
ARM_POS_MIN = ARM_POS_MIN_V3
ARM_POS_MAX = ARM_POS_MAX_V3

HAND_JOINT_NAMES = ["little", "ring", "middle", "forefinger", "thumb_bend", "thumb_rot"]
HAND_POS_MIN = [0.5, 0.5, 0.5, 0.5, 0.3, 1.63]
HAND_POS_MAX = [2.76, 2.76, 2.76, 2.76, 0.7, 2.72]


def setup_robot_config():
    """按 robot.get_robot_type() 选择 V3/V5 内置关节配置(与 C++ SetupJointConfig 一致)。"""
    global UPPER_JOINT_NAMES, ARM_KP, ARM_KD, ARM_TOQ, ARM_POS_MIN, ARM_POS_MAX
    arm = magicbot.ARM_JOINT_NUM  # V3=10, V5=14
    if arm == 14:
        UPPER_JOINT_NAMES = UPPER_JOINT_NAMES_V5
        ARM_KP = ARM_KP_V5
        ARM_KD = ARM_KD_V5
        ARM_TOQ = ARM_TOQ_V5
        ARM_POS_MIN = ARM_POS_MIN_V5
        ARM_POS_MAX = ARM_POS_MAX_V5
        logging.info("[config] RobotType=V5 (arm=14), upper joints=16")
    else:
        UPPER_JOINT_NAMES = UPPER_JOINT_NAMES_V3
        ARM_KP = ARM_KP_V3
        ARM_KD = ARM_KD_V3
        ARM_TOQ = ARM_TOQ_V3
        ARM_POS_MIN = ARM_POS_MIN_V3
        ARM_POS_MAX = ARM_POS_MAX_V3
        logging.info("[config] RobotType=V3 (arm=10), upper joints=12")


def signal_handler(signum, frame):
    global running, robot
    logging.info("Received interrupt signal (%s), exiting...", signum)
    running = False
    if robot:
        robot.shutdown()
        logging.info("Robot shutdown")
    exit(signum)


def print_help():
    logging.info("Key Function Description:")
    logging.info("Gait and Mode Functions:")
    logging.info("  0        Function 0: Get gait")
    logging.info("  1        Function 1: Set recovery stand gait")
    logging.info("  2        Function 2: Switch to hybrid motion control level")
    logging.info("")
    logging.info("Joystick Functions:")
    logging.info("  w        Function w: Move forward")
    logging.info("  a        Function a: Move left")
    logging.info("  s        Function s: Move backward")
    logging.info("  d        Function d: Move right")
    logging.info("  x        Function x: Stop")
    logging.info("  t        Function t: Turn left")
    logging.info("  g        Function g: Turn right")
    logging.info("")
    logging.info("Upper Body Functions:")
    logging.info("  3        Function 3: Subscribe upper body state")
    logging.info("  4        Function 4: Unsubscribe upper body state")
    logging.info("  5        Function 5: Publish upper body command")
    logging.info("  6        Function 6: Subscribe all hand state")
    logging.info("  7        Function 7: Unsubscribe all hand state")
    logging.info("  8        Function 8: Publish all hand command")
    logging.info("")
    logging.info("")
    logging.info("Arm/Hand Pose Functions:")
    logging.info("  m        Manual guide arm pose (enter joint angles one by one)")
    logging.info("  n        Manual guide hand pose (enter finger angles one by one)")
    logging.info("  r        Record current arm & hand pose as reference pose")
    logging.info("  f        Arms & hands move to reference pose")
    logging.info("  h        Arms & hands return to boot pose")
    logging.info("  z        Arms & hands return to all-zero pose")
    logging.info("")
    logging.info("  ESC      Exit program")
    logging.info("  ?        Function ?: Print help")


def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, old_settings)
    return ch


def _enter_line_input():
    """切到 cbreak(关ICANON/按字节输入)但保留 ECHO, 让输入数字即时回显。返回旧设置。"""
    fd = sys.stdin.fileno()
    oldt = termios.tcgetattr(fd)
    newt = termios.tcgetattr(fd)
    newt[3] &= ~(termios.ICANON)   # 去 ICANON(按字节)
    newt[3] |= termios.ECHO        # 保留 ECHO(显示输入)
    termios.tcsetattr(fd, termios.TCSANOW, newt)
    return fd, oldt


def get_gait():
    global robot
    controller = robot.get_high_level_motion_controller()
    status, gait_mode = controller.get_gait()
    if status.code != magicbot.ErrorCode.OK:
        logging.error("get robot gait failed, code: %s, message: %s", status.code, status.message)
        return
    logging.info("robot gait: %s", int(gait_mode))


def set_recovery_stand_gait():
    global robot
    controller = robot.get_high_level_motion_controller()
    status = controller.set_gait(magicbot.GaitMode.GAIT_RECOVERY_STAND, 10000)
    if status.code != magicbot.ErrorCode.OK:
        logging.error("set robot gait failed, code: %s, message: %s", status.code, status.message)
        return
    logging.info("robot gait set to GAIT_RECOVERY_STAND successfully.")


def set_hybrid_mode():
    global robot
    controller = robot.get_high_level_motion_controller()
    status = controller.set_gait(magicbot.GaitMode.GAIT_HYBRID_SDK, 10000)
    if status.code != magicbot.ErrorCode.OK:
        logging.error(
            "set robot gait failed, code: %s, message: %s",
            status.code,
            status.message,
        )
        return
    logging.info("robot gait set to GAIT_HYBRID_SDK successfully.")


def joystick_command(left_x_axis, left_y_axis, right_x_axis, right_y_axis):
    global robot
    controller = robot.get_high_level_motion_controller()
    joy_command = magicbot.JoystickCommand()
    joy_command.left_x_axis = left_x_axis
    joy_command.left_y_axis = left_y_axis
    joy_command.right_x_axis = right_x_axis
    joy_command.right_y_axis = right_y_axis

    status = controller.send_joystick_command(joy_command)
    if status.code != magicbot.ErrorCode.OK:
        logging.error("send joystick command failed, code: %s, message: %s", status.code, status.message)
    time.sleep(0.05)


def subscribe_upper_body_state():
    global robot
    controller = robot.get_upper_body_motion_controller()
    try:
        controller.unsubscribe_upper_body_state()
        gc.collect()
        time.sleep(0.2)
    except Exception:
        pass

    def upper_body_state_callback(joint_state):
        global upper_body_state_counter, cur_upper_pos, boot_upper, boot_valid
        upper_body_state_counter += 1
        # 缓存当前上肢位置
        cur_upper_pos = [j.posL for j in joint_state.joints]
        if not boot_valid:
            boot_upper = list(cur_upper_pos)
            boot_valid = True
        # 首帧打印一次
        if upper_body_state_counter == 1:
            logging.info("--- upper body state (first frame) ---")
            for ii in range(len(joint_state.joints)):
                j = joint_state.joints[ii]
                logging.info(
                    "joint %d posL=%s posH=%s vel=%s toq=%s",
                    ii, j.posL, j.posH, j.vel, j.toq,
                )
            logging.info("---------------------------------------")

    controller.subscribe_upper_body_state(upper_body_state_callback)
    logging.info("Subscribed to upper body state")


def unsubscribe_upper_body_state():
    global robot
    controller = robot.get_upper_body_motion_controller()
    controller.unsubscribe_upper_body_state()
    gc.collect()
    logging.info("Unsubscribed from upper body state")


def publish_upper_body_command():
    global robot, pos
    controller = robot.get_upper_body_motion_controller()
    command = magicbot.JointCommand()
    command.timestamp = int(time.time() * 1e9)
    command.motion_mode = 1

    total_upper_joints = magicbot.ARM_JOINT_NUM + magicbot.WAIST_JOINT_NUM + magicbot.HEAD_JOINT_NUM
    for _ in range(total_upper_joints):
        joint = magicbot.SingleJointCommand()
        joint.operation_mode = 3
        joint.pos = pos
        joint.vel = 0.0
        joint.toq = 0.0
        joint.kp = 0.0
        joint.kd = 0.0
        command.joints.append(joint)

    # command.joints[0].pos = 0.01
    # command.joints[1].pos = 0.11
    # command.joints[2].pos = 1.18
    # command.joints[3].pos = -0.51
    # command.joints[4].pos = -1.49
    # command.joints[5].pos = 0.0
    # command.joints[6].pos = 0.0
    # command.joints[7].pos = 0.01
    # command.joints[8].pos = -0.11
    # command.joints[9].pos = -1.18
    # command.joints[10].pos = 0.51
    # command.joints[11].pos = 1.49
    # command.joints[12].pos = 0.0
    # command.joints[13].pos = 0.0
    # command.joints[14].pos = 0.0
    # command.joints[15].pos = 0.0
    # command.joints[16].pos = 0.0

    # command.joints[0].kp = 5.0
    # command.joints[0].kd = 40.0
    # command.joints[1].kp = 5.0
    # command.joints[1].kd = 40.0
    # for ii in range(2, 14):
    #     command.joints[ii].kp = 10.0
    #     command.joints[ii].kd = 25.0
    # command.joints[14].kp = 50.0
    # command.joints[14].kd = 200.0
    # command.joints[15].kp = 250.0
    # command.joints[15].kd = 10.0
    # command.joints[16].kp = 250.0
    # command.joints[16].kd = 10.0

    status = controller.publish_upper_body_command(command)
    if status.code != magicbot.ErrorCode.OK:
        logging.error("publish upper body command failed, code: %s, message: %s", status.code, status.message)
    else:
        logging.info(status.message)


def subscribe_all_hand_state():
    global robot
    controller = robot.get_upper_body_motion_controller()
    try:
        controller.unsubscribe_all_hand_state()
        gc.collect()
        time.sleep(0.2)
    except Exception:
        pass

    def all_hand_state_callback(all_hand_state):
        global all_hand_state_counter, cur_hand_pos, boot_hand
        all_hand_state_counter += 1
        # 缓存双手手指位置(平铺: 左手6 + 右手6)
        cur_hand_pos = []
        for s in all_hand_state.state:
            cur_hand_pos.extend(list(s.pos))
        if not boot_valid:
            boot_hand = list(cur_hand_pos)
        # 首帧打印
        if all_hand_state_counter == 1:
            logging.info("--- all hand state (first frame) ---")
            for ii in range(len(all_hand_state.state)):
                logging.info("hand %d pos: %s", ii, list(all_hand_state.state[ii].pos))
            logging.info("------------------------------------")

    controller.subscribe_all_hand_state(all_hand_state_callback)
    logging.info("Subscribed to all hand state")


def unsubscribe_all_hand_state():
    global robot
    controller = robot.get_upper_body_motion_controller()
    controller.unsubscribe_all_hand_state()
    gc.collect()
    logging.info("Unsubscribed from all hand state")


def publish_all_hand_command():
    global robot, pos
    controller = robot.get_upper_body_motion_controller()
    command = magicbot.HandCommand()
    command.timestamp = int(time.time() * 1e9)
    for _ in range(magicbot.HAND_NUM):
        single_hand_cmd = magicbot.SingleHandJointCommand()
        single_hand_cmd.operation_mode = 4
        for _ in range(magicbot.HAND_JOINT_NUM):
            single_hand_cmd.pos.append(pos)
        command.cmd.append(single_hand_cmd)

    if magicbot.HAND_NUM >= 2 and magicbot.HAND_JOINT_NUM >= 6:
        command.cmd[0].pos[0:6] = [2.77, 2.77, 2.77, 2.77, 0.77, 2.81]
        command.cmd[1].pos[0:6] = [2.77, 2.77, 2.77, 2.77, 0.77, 2.81]

    controller.publish_all_hand_command(command)
    logging.info("Published all hand command")


# ============ 双臂+双手 摆放 (与 C++ 例程一致) ============

def clamp_arm_pos(idx, pos):
    lo = ARM_POS_MIN[idx]
    hi = ARM_POS_MAX[idx]
    if pos < lo or pos > hi:
        logging.error("[clamp] joint %d (%s) target %s out of range [%s, %s]. Ignored.",
                      idx, UPPER_JOINT_NAMES[idx], pos, lo, hi)
        return False
    return True


def clamp_hand_pos(idx, pos):
    lo = HAND_POS_MIN[idx]
    hi = HAND_POS_MAX[idx]
    if pos < lo or pos > hi:
        logging.error("[clamp] hand joint %d (%s) target %s out of range [%s, %s]. Ignored.",
                      idx, HAND_JOINT_NAMES[idx], pos, lo, hi)
        return False
    return True


def move_to_group(target_upper, target_hand):
    """一次性发布整组目标(与 C++ MoveToGroup 一致)。m/n 都走这里: 完整发手臂 + 灵巧手,
    无论手部是否有数据, 都发(空则全 0)。"""
    global robot
    controller = robot.get_upper_body_motion_controller()
    # 用运行时关节数(而非编译期常量), 支持 V3(12)/V5(16)
    arm_num = magicbot.get_arm_joint_num() + magicbot.get_waist_joint_num() + magicbot.get_head_joint_num()

    cmd = magicbot.JointCommand()
    cmd.timestamp = int(time.time() * 1e9)
    cmd.motion_mode = 1
    for i in range(arm_num):
        joint = magicbot.SingleJointCommand()
        joint.operation_mode = 3
        joint.pos = target_upper[i] if i < len(target_upper) else 0.0
        joint.vel = 0.0
        joint.toq = ARM_TOQ[i] if i < len(ARM_TOQ) else 0.0
        joint.kp = ARM_KP[i] if i < len(ARM_KP) else 0.0
        joint.kd = ARM_KD[i] if i < len(ARM_KD) else 0.0
        cmd.joints.append(joint)
    status = controller.publish_upper_body_command(cmd)
    if status.code != magicbot.ErrorCode.OK:
        logging.error("publish upper body command failed, code: %s, message: %s", status.code, status.message)
        return

    # 手部: 与 C++ 一致, 无论是否有数据都发布(空则全 0)
    hand_cmd = magicbot.HandCommand()
    hand_cmd.timestamp = cmd.timestamp
    for h in range(magicbot.HAND_NUM):
        sc = magicbot.SingleHandJointCommand()
        sc.operation_mode = 4  # 位置控制模式
        for f in range(magicbot.HAND_JOINT_NUM):
            idx = h * magicbot.HAND_JOINT_NUM + f
            sc.pos.append(target_hand[idx] if idx < len(target_hand) else 0.0)
        hand_cmd.cmd.append(sc)
    status = controller.publish_all_hand_command(hand_cmd)
    if status.code != magicbot.ErrorCode.OK:
        logging.error("publish all hand command failed, code: %s, message: %s", status.code, status.message)
    logging.info("[move] published upper-body(%d) + both hands command (movej).", arm_num)


def _get_current_pose():
    """返回 (cur_upper, cur_hand); 上肢缓存为空则返回 (None, None)"""
    if not cur_upper_pos:
        return None, None
    return list(cur_upper_pos), list(cur_hand_pos)


def manual_guide_pose():
    """m: 手部手动引导(逐臂关节输入后发布完整指令)。
    - 手臂控制值 = 本次输入目标(target_upper)
    - 灵巧手控制值 = 读取当前灵巧手关节数据(start_hand), 无则全 0
    """
    start_upper, start_hand = _get_current_pose()
    if start_upper is None:
        logging.error("[guide] no state cache yet. Press 3 to subscribe then wait.")
        return
    if len(start_upper) < len(UPPER_JOINT_NAMES):
        logging.error("[guide] unexpected upper joint count: %d", len(start_upper))
        return

    target_upper = list(start_upper)  # 默认保持当前
    # 灵巧手控制值: 读取当前灵巧手关节数据, 无则全 0
    if start_hand:
        target_hand = list(start_hand)
    else:
        target_hand = [0.0] * (magicbot.HAND_NUM * magicbot.HAND_JOINT_NUM)
        print("[guide] 未检测到灵巧手数据, 灵巧手控制值取全 0。")
    logging.info("\n==== 手动引导摆位: 一次输入 12 关节目标, 最后一次性发布 ====")
    logging.info("对每个关节输入目标角(rad), 回车=保持当前; 输入 q=中止; 全部输完后一次发布。")

    fd = sys.stdin.fileno()
    fd, oldt = _enter_line_input()  # 关ICANON保留ECHO, 数字即时显示
    try:
        aborted = False
        for i in range(len(UPPER_JOINT_NAMES)):
            cur = cur_upper_pos[i] if i < len(cur_upper_pos) else 0.0
            print(f"  [{i}] {UPPER_JOINT_NAMES[i]}  当前 {cur}  范围 [{ARM_POS_MIN[i]}, {ARM_POS_MAX[i]}] rad")
            line = input("     输入目标角 [回车=保持, q=中止]: ").strip()
            if line == "":
                print(f"[guide] keep {UPPER_JOINT_NAMES[i]} = {cur}")
                continue
            if line.lower() == "q":
                print("[guide] aborted.")
                aborted = True
                break
            try:
                target = float(line)
            except ValueError:
                print(f"[guide] invalid, keep = {cur}")
                continue
            if not clamp_arm_pos(i, target):
                continue
            target_upper[i] = target
            print(f"[guide] set {UPPER_JOINT_NAMES[i]} = {target}")
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, oldt)

    if aborted:
        return

    print("\n==== 发布整组目标 ====")
    for i in range(len(UPPER_JOINT_NAMES)):
        print(f"  [{i}] {UPPER_JOINT_NAMES[i]} = {target_upper[i]}")
    move_to_group(target_upper, target_hand)
    print("[guide] 已发布. 按 'r' 记录此姿态为参考位, 之后按 'f' 可复现。")


def manual_guide_hand():
    """手部手动引导: 左/右手各6指, 逐指输入, 最后发布。
    无论手部是否有数据都发完整指令(move_to_group 统一发手臂+灵巧手):
    - 手臂控制值取当前实际位置(start_upper)
    - 灵巧手控制值由本次输入决定(target_hand; 无初始数据则从全0起)
    """
    start_upper, start_hand = _get_current_pose()
    if start_upper is None:
        logging.error("[guide] no state cache yet. Press 3 to subscribe then wait.")
        return

    target_hand = list(start_hand) if start_hand else [0.0] * (magicbot.HAND_NUM * magicbot.HAND_JOINT_NUM)
    print("\n==== 手动引导摆位 - 双手: 一次输入双手目标, 最后一次性发布 ====")
    print(f"每只手 6 指: {', '.join(HAND_JOINT_NAMES)}")
    if not start_hand:
        print("[guide] 未检测到灵巧手数据, 手指将从全 0 开始; 发布时仍会发完整手臂+灵巧手命令。")
    print("回车=保持当前; 输入 q=中止; 全部输完后一次发布。")

    fd, oldt = _enter_line_input()  # 关ICANON保留ECHO, 数字即时显示
    try:
        aborted = False
        for h in range(magicbot.HAND_NUM):
            print(f"\n--- {'左手' if h == 0 else '右手'} ---")
            for f in range(magicbot.HAND_JOINT_NUM):
                idx = h * magicbot.HAND_JOINT_NUM + f
                cur = start_hand[idx] if idx < len(start_hand) else 0.0
                print(f"  [{idx}] {HAND_JOINT_NAMES[f]}  当前 {cur}  范围 [{HAND_POS_MIN[f]}, {HAND_POS_MAX[f]}] rad")
                line = input("     输入目标角 [回车=保持, q=中止]: ").strip()
                if line == "":
                    print(f"[guide] keep hand {idx} ({HAND_JOINT_NAMES[f]}) = {cur}")
                    continue
                if line.lower() == "q":
                    print("[guide] aborted.")
                    aborted = True
                    break
                try:
                    target = float(line)
                except ValueError:
                    print(f"[guide] invalid, keep = {cur}")
                    continue
                if not clamp_hand_pos(f, target):
                    continue
                target_hand[idx] = target
                print(f"[guide] set hand {idx} ({HAND_JOINT_NAMES[f]}) = {target}")
            if aborted:
                break
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, oldt)

    if aborted:
        return

    print("\n==== 发布双手目标 ====")
    for h in range(magicbot.HAND_NUM):
        print(f"  {'左手' if h == 0 else '右手'}: " + "  ".join(
            f"{HAND_JOINT_NAMES[f]}={target_hand[h * magicbot.HAND_JOINT_NUM + f]}"
            for f in range(magicbot.HAND_JOINT_NUM)))
    move_to_group(start_upper, target_hand)
    print("[guide] 已发布双手. 按 'r' 记录此姿态为参考位, 之后按 'f' 可复现。")


def record_reference():
    global home_upper, home_hand, home_valid
    start_upper, start_hand = _get_current_pose()
    if start_upper is None:
        logging.error("[record] no upper-body state cache yet. Press 3 to subscribe, then wait a moment.")
        return
    home_upper = start_upper
    home_hand = start_hand
    home_valid = True
    logging.info("[record] reference pose recorded. upper=%d joints, hand=%d fingers.",
                 len(home_upper), len(home_hand))


def move_to_reference():
    global home_upper, home_hand, home_valid
    if not home_valid:
        logging.error("[move] no reference recorded. Press 'r' to record current pose first.")
        return
    logging.info("[move] moving to reference pose...")
    move_to_group(list(home_upper), list(home_hand))
    logging.info("[move] reached target pose.")


def move_to_home():
    if not boot_valid or not boot_upper:
        logging.error("[move] no boot pose yet. Press 3 to subscribe, then wait a moment.")
        return
    logging.info("[move] returning all arms & hands to boot pose...")
    move_to_group(list(boot_upper), list(boot_hand))
    logging.info("[move] reached target pose.")


def move_to_zero():
    arm_num = magicbot.get_arm_joint_num() + magicbot.get_waist_joint_num() + magicbot.get_head_joint_num()
    logging.info("[move] returning all arms & hands to all-zero pose...")
    move_to_group([0.0] * arm_num, [0.0] * (magicbot.HAND_NUM * magicbot.HAND_JOINT_NUM))
    logging.info("[move] reached target pose.")


def main():
    global robot, running
    sys.stdout.reconfigure(line_buffering=True)
    signal.signal(signal.SIGINT, signal_handler)

    robot = magicbot.MagicRobot()
    logging.info("SDK Version: %s", robot.get_sdk_version())
    print_help()

    local_ip = "192.168.54.111"

    try:
        if not robot.initialize(local_ip):
            logging.error("robot sdk initialize failed.")
            robot.shutdown()
            return -1
        # 根据实际型号(V3/V5)选择关节配置
        setup_robot_config()

        status = robot.connect()
        if status.code != magicbot.ErrorCode.OK:
            logging.error("connect robot failed, code: %s, message: %s", status.code, status.message)
            robot.shutdown()
            return -1

        logging.info("Press any key to continue (ESC to exit)...")
        while running:
            key = getch()
            if ord(key) == 27:
                break

            logging.info("Key ASCII: %d, Character: %s", ord(key), key)
            if key == "0":
                get_gait()
            elif key == "1":
                set_recovery_stand_gait()
            elif key == "2":
                set_hybrid_mode()
            elif key.lower() == "w":
                joystick_command(0.0, 1.0, 0.0, 0.0)
            elif key.lower() == "a":
                joystick_command(-1.0, 0.0, 0.0, 0.0)
            elif key.lower() == "s":
                joystick_command(0.0, -1.0, 0.0, 0.0)
            elif key.lower() == "d":
                joystick_command(1.0, 0.0, 0.0, 0.0)
            elif key.lower() == "x":
                joystick_command(0.0, 0.0, 0.0, 0.0)
            elif key.lower() == "t":
                joystick_command(0.0, 0.0, -1.0, 0.0)
            elif key.lower() == "g":
                joystick_command(0.0, 0.0, 1.0, 0.0)
            elif key == "3":
                subscribe_upper_body_state()
            elif key == "4":
                unsubscribe_upper_body_state()
            elif key == "5":
                publish_upper_body_command()
            elif key == "6":
                subscribe_all_hand_state()
            elif key == "7":
                unsubscribe_all_hand_state()
            elif key == "8":
                publish_all_hand_command()
            elif key.lower() == "m":
                manual_guide_pose()
            elif key.lower() == "n":
                manual_guide_hand()
            elif key.lower() == "r":
                record_reference()
            elif key.lower() == "f":
                move_to_reference()
            elif key.lower() == "h":
                move_to_home()
            elif key.lower() == "z":
                move_to_zero()
            elif key == "?":
                print_help()
            else:
                logging.info("Unknown key: %s", key)
            time.sleep(0.01)

        status = robot.disconnect()
        if status.code != magicbot.ErrorCode.OK:
            logging.error("disconnect robot failed, code: %s, message: %s", status.code, status.message)
            robot.shutdown()
            return -1

        robot.shutdown()
        return 0

    except Exception as e:
        logging.error("Exception occurred during program execution: %s", e)
        return -1

    finally:
        try:
            if robot:
                robot.shutdown()
        except Exception as e:
            logging.error("Exception occurred while cleaning up resources: %s", e)


if __name__ == "__main__":
    sys.exit(main())

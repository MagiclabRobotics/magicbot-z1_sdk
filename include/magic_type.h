#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace magic::z1 {

/************************************************************
 *                        Constant Information                *
 ************************************************************/

constexpr uint8_t kHandJointNum = 6;   ///< Number of dexterous hand joints
constexpr uint8_t kHandNum = 2;        ///< Number of dexterous hands (left and right hand)
constexpr uint8_t kHeadJointNum = 2;   ///< Number of head joints
constexpr uint8_t kArmJointNum = 14;   ///< Number of arm joints (left and right arm)
constexpr uint8_t kWaistJointNum = 1;  ///< Number of waist joints
constexpr uint8_t kLegJointNum = 12;   ///< Number of leg joints

constexpr uint64_t kPeriodMs = 2;  ///< Low-level controller cycle time in milliseconds

/************************************************************
 *                        Interface Information               *
 ************************************************************/

enum ErrorCode {
  OK = 0,
  SERVICE_NOT_READY = 1,
  TIMEOUT = 2,
  INTERNAL_ERROR = 3,
  SERVICE_ERROR = 4,
};

struct Status {
  ErrorCode code;
  std::string message;
};

/************************************************************
 *                        Status Information                  *
 ************************************************************/
/**
 * @brief Error information structure
 *
 * Used to represent error information that occurs in the system, including error code and error message.
 */
struct Fault {
  /**
   * @brief Error code
   *
   * Integer value used to identify specific exception types. Different error codes can correspond to different error types, facilitating error management and handling.
   */
  int error_code;

  /**
   * @brief Error message
   *
   * Describes specific information about the error occurrence, usually a detailed description of the error cause, facilitating debugging and problem localization.
   */
  std::string error_message;
};

/**
 * @brief Battery state enumeration type
 *
 * Represents the current state of the battery, containing multiple possible battery state options, used for battery state judgment and processing in the system.
 */
enum class BatteryState : int8_t {
  UNKNOWN = 0,                ///< Unknown state
  GOOD = 1,                   ///< Battery state is good
  OVERHEAT = 2,               ///< Battery overheating
  DEAD = 3,                   ///< Battery damaged
  OVERVOLTAGE = 4,            ///< Battery overvoltage
  UNSPEC_FAILURE = 5,         ///< Unknown failure
  COLD = 6,                   ///< Battery overcooled
  WATCHDOG_TIMER_EXPIRE = 7,  ///< Watchdog timer timeout
  SAFETY_TIMER_EXPIRE = 8,    ///< Safety timer timeout
};

/**
 * @brief Battery charge/discharge state
 */
enum class PowerSupplyStatus : int8_t {
  UNKNOWN = 0,      ///< Unknown state
  CHARGING = 1,     ///< Battery charging
  DISCHARGING = 2,  ///< Battery discharging
  NOTCHARGING = 3,  ///< Battery not charging/discharging
  FULL = 4,         ///< Battery fully charged
};

/**
 * @brief Battery management system data structure
 *
 * Used to store battery-related information, including battery remaining power, battery health status, battery state and charging status.
 */
typedef struct bms_data {
  /**
   * @brief Battery remaining power
   *
   * Current battery power percentage, ranging from 0 to 100, representing the remaining battery power.
   */
  float battery_percentage;

  /**
   * @brief Battery health status
   *
   * Battery health condition, usually a floating value representing battery performance. Higher health status indicates better battery condition.
   */
  float battery_health;

  /**
   * @brief Battery state
   *
   * Current state of the battery, usually associated with values of the `BatteryState` enumeration type to represent different battery states.
   */
  BatteryState battery_state;

  /**
   * @brief Charging status
   *
   * A boolean value indicating whether the battery is charging. `true` means the battery is charging, `false` means the battery is not charging.
   */
  PowerSupplyStatus power_supply_status;
} BmsData;

typedef struct robot_state {
  std::vector<Fault> faults;  ///< Fault information list
  BmsData bms_data;           ///< Battery management system data
} RobotState;

/************************************************************
 *                        Motion Control                      *
 ************************************************************/

/**
 * @brief Motion controller level type, used to distinguish different controller responsibilities.
 */
enum class ControllerLevel : int8_t {
  UNKKOWN = 0,
  HighLevel = 1,  ///< High-level controller
  LowLevel = 2    ///< Low-level controller
};

/**
 * @brief Data structure for high-level motion control joystick commands
 */
struct JoystickCommand {
  /**
   * @brief Left joystick X-axis direction value
   *
   * This value represents the left joystick input along the X-axis direction, ranging from -1.0 to 1.0.
   * -1.0 means left movement, 1.0 means right movement, 0 means neutral position.
   */
  float left_x_axis;

  /**
   * @brief Left joystick Y-axis direction value
   *
   * This value represents the left joystick input along the Y-axis direction, ranging from -1.0 to 1.0.
   * -1.0 means downward movement, 1.0 means upward movement, 0 means neutral position.
   */
  float left_y_axis;

  /**
   * @brief Right joystick X-axis direction value
   *
   * This value represents the right joystick rotation along the Z-axis direction, ranging from -1.0 to 1.0.
   * -1.0 means left rotation, 1.0 means right rotation, 0 means neutral position.
   */
  float right_x_axis;

  /**
   * @brief Right joystick Y-axis direction value, to be determined
   */
  float right_y_axis;
};

/**
 * @brief Robot state enumeration, suitable for state machine control
 */
enum class GaitMode : int32_t {
  GAIT_PASSIVE = 0,          // Idle mode
  GAIT_RECOVERY_STAND = 1,   // Standing lock/standing recovery
  GAIT_BALANCE_STAND = 46,   // Balanced standing (supports movement)
  GAIT_ARM_SWING_WALK = 78,  // Arm swinging walk
  GAIT_HUMANOID_WALK = 79,   // Humanoid walking
  GAIT_LOWLEVL_SDK = 200,    // Low-level control SDK mode
};

/**
 * @brief Humanoid robot action command enumeration (corresponding to action ID)
 */
enum class TrickAction : int32_t {
  ACTION_NONE = 0,                         // No trick, default
  ACTION_SHAKE_LEFT_HAND_REACHOUT = 215,   // Handshake (left hand) - reach out
  ACTION_SHAKE_LEFT_HAND_WITHDRAW = 216,   // Handshake (left hand) - withdraw
  ACTION_SHAKE_RIGHT_HAND_REACHOUT = 217,  // Handshake (right hand) - reach out
  ACTION_SHAKE_RIGHT_HAND_WITHDRAW = 218,  // Handshake (right hand) - withdraw
  ACTION_SHAKE_HEAD = 220,                 // Shake head
  ACTION_LEFT_GREETING = 300,              // Greeting (left hand)
  ACTION_RIGHT_GREETING = 301,             // Greeting (right hand)
  ACTION_TRUN_LEFT_INTRODUCE_HIGH = 304,   // Turn left introduction - high
  ACTION_TRUN_LEFT_INTRODUCE_LOW = 305,    // Turn left introduction - low
  ACTION_TRUN_RIGHT_INTRODUCE_HIGH = 306,  // Turn right introduction - high
  ACTION_TRUN_RIGHT_INTRODUCE_LOW = 307,   // Turn right introduction - low
  ACTION_WELCOME = 340,                    // Welcome
};

/**
 * @brief Control command for a single hand joint
 */
struct SingleHandJointCommand {
  int16_t operation_mode = 0;  ///< Control mode (e.g., position, torque, impedance, etc.)
  std::vector<float> pos;      ///< Desired position array (7 degrees of freedom)
};

/**
 * @brief Complete hand control command
 */
struct HandCommand {
  int64_t timestamp;                        ///< Timestamp (unit: nanoseconds)
  std::vector<SingleHandJointCommand> cmd;  ///< Control command array, left hand and right hand in order
};

/**
 * @brief State of a single hand joint
 */
struct SingleHandJointState {
  int16_t status_word;     ///< Status
  std::vector<float> pos;  ///< Actual position (unit depends on controller definition)
  std::vector<float> toq;  ///< Actual torque (unit: Nm)
  std::vector<float> cur;  ///< Actual current (unit: A)
  int16_t error_code;      ///< Error code (0 indicates normal)
};

/**
 * @brief Complete hand state information
 */
struct HandState {
  int64_t timestamp;                        ///< Timestamp (unit: nanoseconds)
  std::vector<SingleHandJointState> state;  ///< All hand joint states (total two), left hand and right hand in order
};

/**
 * @brief Control command for a single joint
 */
struct SingleJointCommand {
  int16_t operation_mode = 200;  ///< Operation mode (e.g., position control, velocity control, torque control, etc.)
  float pos;                     ///< Target position (unit: rad or m, depending on joint type)
  float vel;                     ///< Target velocity (unit: rad/s or m/s)
  float toq;                     ///< Target torque (unit: Nm)
  float kp;                      ///< Position loop control gain (proportional term)
  float kd;                      ///< Velocity loop control gain (derivative term)
};

/**
 * @brief All joint control commands
 *
 * Lower limbs contain 12 joint state items, in the same order as control commands.
 * Upper limbs contain 14 joint state items, in the same order as control commands.
 * Head contains 2 joint state items, in the same order as control commands.
 * Waist contains 3 joint state items, in the same order as control commands.
 */
struct JointCommand {
  int64_t timestamp;                       ///< Timestamp (unit: nanoseconds)
  std::vector<SingleJointCommand> joints;  ///< Control commands for all joints
};

/**
 * @brief State information for a single joint
 */
struct SingleJointState {
  int16_t status_word;  ///< Current joint state (custom state machine encoding)
  float posH;           ///< Actual position (high encoder reading, possibly redundant encoder)
  float posL;           ///< Actual position (low encoder reading)
  float vel;            ///< Current velocity (unit: rad/s or m/s)
  float toq;            ///< Current torque (unit: Nm)
  float current;        ///< Current current (unit: A)
  int16_t err_code;     ///< Error code (e.g., encoder exception, motor overcurrent, etc.)
};

/**
 * @brief All joint state data
 *
 * Lower limbs contain 12 joint state items, in the same order as control commands.
 * Upper limbs contain 14 joint state items, in the same order as control commands.
 * Head contains 2 joint state items, in the same order as control commands.
 * Waist contains 3 joint state items, in the same order as control commands.
 */
struct JointState {
  int64_t timestamp;                     ///< Timestamp (unit: nanoseconds)
  std::vector<SingleJointState> joints;  ///< State data for all joints
};

/************************************************************
 *                        Voice Control                       *
 ************************************************************/

/**
 * @brief TTS broadcast priority level
 *
 * Used to control interrupt behavior between different TTS tasks. Higher priority tasks will interrupt the playback of current lower priority tasks.
 */
enum class TtsPriority : int8_t {
  HIGH = 0,    ///< Highest priority, e.g.: low battery warning, emergency reminder
  MIDDLE = 1,  ///< Medium priority, e.g.: system prompts, status broadcast
  LOW = 2      ///< Lowest priority, e.g.: daily voice dialogue, background broadcast
};

/**
 * @brief Task scheduling strategy under the same priority
 *
 * Used to refine control of playback order and clearing logic for multiple TTS tasks under the same priority condition.
 */
enum class TtsMode : int8_t {
  CLEARTOP = 0,    ///< Clear all tasks of current priority (including currently playing and waiting queue), immediately play this request
  ADD = 1,         ///< Append this request to the end of current priority queue, play in order (do not interrupt current playback)
  CLEARBUFFER = 2  ///< Clear unplayed requests in queue, keep current playback, then play this request
};

/**
 * @brief TTS (Text-To-Speech) playback command structure
 *
 * Used to describe complete information of a TTS playback request, supporting setting unique identifier, text content, priority control and scheduling mode under the same priority.
 *
 * Example scenarios: When playing weather broadcast, battery reminder and other voice content, determine broadcast order and interrupt behavior based on priority and mode.
 */
typedef struct tts_cmd {
  /**
   * @brief TTS task unique ID
   *
   * Used to identify a TTS task, track TTS status in subsequent callbacks (e.g., start playback, playback completion, etc.).
   * For example: "id_01"
   */
  std::string id;
  /**
   * @brief Text content to be played
   *
   * Supports any readable UTF-8 string, for example: "Hello, welcome to the intelligent voice system."
   */
  std::string content;
  /**
   * @brief Broadcast priority
   *
   * Controls interrupt relationship between different TTS requests, higher priority requests will interrupt currently playing lower priority requests.
   */
  TtsPriority priority;
  /**
   * @brief Scheduling mode under the same priority
   *
   * Controls processing logic for multiple TTS requests under the same priority condition, avoiding infinite expansion of priority values.
   */
  TtsMode mode;
} TtsCommand;

/************************************************************
 *                        Sensors                              *
 ************************************************************/

/**
 * @brief IMU data structure, containing timestamp, attitude, angular velocity, acceleration and temperature information
 */
struct Imu {
  int64_t timestamp;                          ///< Timestamp (unit: nanoseconds), represents the time point when this IMU data was collected
  std::array<double, 4> orientation;          ///< Attitude quaternion (w, x, y, z), used to represent spatial attitude, avoiding Euler angle gimbal lock problem
  std::array<double, 3> angular_velocity;     ///< Angular velocity (unit: rad/s), angular velocity around X, Y, Z axes, usually from gyroscope
  std::array<double, 3> linear_acceleration;  ///< Linear acceleration (unit: m/s^2), linear acceleration of X, Y, Z axes, usually from accelerometer
  float temperature;                          ///< Temperature (unit: Celsius or other, should be clarified when used)
};

/**
 * @brief Header structure, containing timestamp and frame name
 */
struct Header {
  int64_t stamp;         ///< Timestamp, unit: nanoseconds
  std::string frame_id;  ///< Coordinate system name
};

/**
 * @brief Point cloud field description structure, corresponding to sensor_msgs::msg::PointField in ROS2.
 */
struct PointField {
  std::string name;  ///< Field name, e.g., "x", "y", "z", "intensity", etc.
  int32_t offset;    ///< Starting byte offset
  int8_t datatype;   ///< Data type (corresponding constant)
  int32_t count;     ///< Number of elements contained in this field
};

/**
 * @brief General point cloud data structure, similar to ROS2's sensor_msgs::msg::PointCloud2
 */
struct PointCloud2 {
  Header header;  ///< Standard message header

  int32_t height;  ///< Number of rows
  int32_t width;   ///< Number of columns

  std::vector<PointField> fields;  ///< Point field array

  bool is_bigendian;   ///< Byte order
  int32_t point_step;  ///< Number of bytes occupied by each point
  int32_t row_step;    ///< Number of bytes occupied by each row

  std::vector<uint8_t> data;  ///< Raw point cloud data (packed by field)

  bool is_dense;  ///< Whether it is a dense point cloud (no invalid points)
};

/**
 * @brief Image data structure, supporting multiple encoding formats
 */
struct Image {
  Header header;

  int32_t height;  ///< Image height (pixels)
  int32_t width;   ///< Image width (pixels)

  std::string encoding;  ///< Image encoding type, e.g., "rgb8", "mono8", "bgr8"
  bool is_bigendian;     ///< Whether data is in big-endian mode
  int32_t step;          ///< Number of bytes occupied by each image row

  std::vector<uint8_t> data;  ///< Raw image byte data
};

/**
 * @brief Camera intrinsic parameters and distortion information, usually published together with Image messages
 */
struct CameraInfo {
  Header header;

  int32_t height;  ///< Image height (number of rows)
  int32_t width;   ///< Image width (number of columns)

  std::string distortion_model;  ///< Distortion model, e.g., "plumb_bob"

  std::vector<double> D;  ///< Distortion parameter array

  std::array<double, 9> K;   ///< Camera intrinsic parameter matrix
  std::array<double, 9> R;   ///< Rectification matrix
  std::array<double, 12> P;  ///< Projection matrix

  int32_t binning_x;  ///< Horizontal binning coefficient
  int32_t binning_y;  ///< Vertical binning coefficient

  int32_t roi_x_offset;  ///< ROI starting x
  int32_t roi_y_offset;  ///< ROI starting y
  int32_t roi_height;    ///< ROI height
  int32_t roi_width;     ///< ROI width
  bool roi_do_rectify;   ///< Whether to perform rectification
};

/**
 * @brief Binocular camera frame data structure, containing format and image frame
 */
struct BinocularCameraFrame {
  Header header;  ///< General message header (timestamp + frame_id)

  std::string format;

  std::vector<uint8_t> data;  ///< Left and right eye stitched image data, left half is left eye image, right half is right eye image
};

/**
 * @brief Audio stream data structure
 */
struct AudioStream {
  // Audio data
  int32_t data_length;            // Actual length of audio data (bytes)
  std::vector<uint8_t> raw_data;  // Audio data
};

class NonCopyable {
 protected:
  NonCopyable() = default;
  ~NonCopyable() = default;
  NonCopyable(NonCopyable&&) = default;
  NonCopyable& operator=(NonCopyable&&) = default;
  NonCopyable(const NonCopyable&) = delete;
  NonCopyable& operator=(const NonCopyable&) = delete;
};

}  // namespace magic::z1

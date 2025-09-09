#include "magic_robot.h"

#include <termios.h>
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

void print_help(const char* prog_name) {
  std::cout << "按键功能演示程序\n\n";
  std::cout << "用法: " << prog_name << "\n";
  std::cout << "按键功能说明:\n";
  std::cout << "  ESC      退出程序\n";
  std::cout << "  1        功能1:获取音量\n";
  std::cout << "  2        功能2:设置音量\n";
  std::cout << "  3        功能3:播放语音\n";
  std::cout << "  4        功能4:停止播放\n";
  std::cout << "  5        功能5:打开音频流\n";
  std::cout << "  6        功能6:关闭音频流\n";
  std::cout << "  7        功能7:订阅音频流\n";
}

int getch() {
  struct termios oldt, newt;
  int ch;
  tcgetattr(STDIN_FILENO, &oldt);  // 获取当前终端设置
  newt = oldt;
  newt.c_lflag &= ~(ICANON | ECHO);  // 关闭缓冲和回显
  tcsetattr(STDIN_FILENO, TCSANOW, &newt);
  ch = getchar();                           // 读取按键
  tcsetattr(STDIN_FILENO, TCSANOW, &oldt);  // 恢复设置
  return ch;
}

void GetVolume() {
  // 获取音频控制器
  auto& controller = robot.GetAudioController();

  // 获取音量
  int get_volume = 0;
  auto status = controller.GetVolume(get_volume);
  if (status.code != ErrorCode::OK) {
    std::cerr << "get volume failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    return;
  }
  std::cout << "get volume success, volume: " << std::to_string(get_volume) << std::endl;
}

void SetVolume() {
  // 获取音频控制器
  auto& controller = robot.GetAudioController();
  // 设置音量
  auto status = controller.SetVolume(7);
  if (status.code != ErrorCode::OK) {
    std::cerr << "set volume failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    return;
  }
  std::cout << "set volume success" << std::endl;
}

void PlayTts() {
  // 获取音频控制器
  auto& controller = robot.GetAudioController();
  // 播放语音
  TtsCommand tts;
  tts.id = "100000000001";
  tts.content = "今天天气怎么样！";
  tts.priority = TtsPriority::HIGH;
  tts.mode = TtsMode::CLEARTOP;
  auto status = controller.Play(tts);
  if (status.code != ErrorCode::OK) {
    std::cerr << "play tts failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    return;
  }
  std::cout << "play tts success" << std::endl;
}

void StopTts() {
  // 获取音频控制器
  auto& controller = robot.GetAudioController();
  // 停止播放语音
  auto status = controller.Stop();
  if (status.code != ErrorCode::OK) {
    std::cerr << "stop tts failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    return;
  }
  std::cout << "stop tts success" << std::endl;
}

void OpenAudioStream() {
  // 获取音频控制器
  auto& controller = robot.GetAudioController();
  // 打开音频流
  auto status = controller.OpenAudioStream();
  if (status.code != ErrorCode::OK) {
    std::cerr << "open audio stream failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    return;
  }
  std::cout << "open audio stream success" << std::endl;
}

void CloseAudioStream() {
  // 获取音频控制器
  auto& controller = robot.GetAudioController();
  // 关闭音频流
  auto status = controller.CloseAudioStream();
  if (status.code != ErrorCode::OK) {
    std::cerr << "close audio stream failed"
              << ", code: " << status.code
              << ", message: " << status.message << std::endl;
    return;
  }
  std::cout << "close audio stream success" << std::endl;
}

void SubscribeAudioStream() {
  // 获取音频控制器
  auto& controller = robot.GetAudioController();

  // 订阅音频流
  controller.SubscribeOriginAudioStream([](const std::shared_ptr<AudioStream> data) {
    static int32_t counter = 0;
    if (counter++ % 30 == 0) {
      std::cout << "Received origin audio stream data, size: " << data->data_length << std::endl;
    }
  });

  controller.SubscribeBfAudioStream([](const std::shared_ptr<AudioStream> data) {
    static int32_t counter = 0;
    if (counter++ % 30 == 0) {
      std::cout << "Received bf audio stream data, size: " << data->data_length << std::endl;
    }
  });
  std::cout << "Subscribed to audio streams" << std::endl;
}

int main(int argc, char* argv[]) {
  // 绑定 SIGINT（Ctrl+C）
  signal(SIGINT, signalHandler);

  print_help(argv[0]);

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

  std::cout << "按任意键继续 (ESC退出)..."
            << std::endl;

  // 等待用户输入
  while (1) {
    int key = getch();
    if (key == 27)
      break;  // ESC键ASCII码为27

    std::cout << "按键ASCII: " << key << ", 字符: " << static_cast<char>(key) << std::endl;
    switch (key) {
      case '1': {
        // 获取音量
        GetVolume();
        break;
      }
      case '2': {
        // 设置音量
        SetVolume();
        break;
      }
      case '3': {
        PlayTts();
        break;
      }
      case '4': {
        StopTts();
        break;
      }
      case '5': {
        OpenAudioStream();
        break;
      }
      case '6': {
        CloseAudioStream();
        break;
      }
      case '7': {
        SubscribeAudioStream();
        break;
      }
      default:
        std::cout << "未知按键: " << key << std::endl;
        break;
    }
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
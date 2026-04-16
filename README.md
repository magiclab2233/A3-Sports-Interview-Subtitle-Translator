# A3 智能体育采访字幕翻译助手 —— 运动员姿态监测与提醒系统

本项目是“智能体育采访字幕翻译助手”的硬件感知端，部署于树莓派（Raspberry Pi）平台，基于 MediaPipe 人体姿态识别技术，实时监测运动员在采访过程中的颈部与躯干姿态，并通过 LED 指示灯进行即时反馈，帮助运动员保持良好体态，从而提升后续字幕翻译与视频制作的成片质量。

---

## 项目简介

在体育采访场景中，运动员若出现颈部前倾、后仰或躯干过度前倾/后仰等不良姿态，不仅影响画面观感，也会给后期口型识别与字幕对齐带来困难。本系统利用 Raspberry Pi + Camera Module 采集视频流，借助 Google MediaPipe Pose Landmarker 模型提取人体关键点，通过向量夹角计算判断颈部与躯干的姿态状态；当检测到异常姿态时，自动点亮 LED 提醒设备，提示运动员调整姿势。

---

## 功能特点

- **实时姿态检测**：基于 MediaPipe Pose Landmarker Full 模型，在边缘端实现 33 个人体关键点的实时检测与跟踪。
- **双摄像头支持**：
  - `main.py`：针对 Raspberry Pi Camera Module，使用 `picamera2` 驱动，支持硬件级视频配置与全分辨率裁剪。
  - `pose.py`：基于 OpenCV `VideoCapture`，兼容 USB 摄像头，方便在 PC 或 Mac 上进行开发与调试。
- **异步推理机制**：`main.py` 采用 `LIVE_STREAM` 异步检测模式，避免推理阻塞主线程，确保画面流畅。
- **颈部 / 躯干双维度评估**：
  - **颈部**：通过耳部中点与肩部中点的向量夹角，判断 `front`（前倾）、`back`（后仰）、`normal`（正常）。
  - **躯干**：通过肩部中点与髋部中点的向量，以及髋部中点与膝部中点的向量夹角，判断 `front`（前倾）、`back`（后仰）、`normal`（正常）。
- **硬件联动反馈**：通过 SenseStorm/RCU 扩展板的 LED 控制接口，在检测到异常姿态时即时点亮指示灯。
- **可视化调试**：实时显示 FPS、姿态状态文本，并可选开启人体分割遮罩（Segmentation Mask）辅助观察。

---

## 技术架构与实现原理

### 1. 整体架构

```
┌─────────────────┐      RGB 帧      ┌──────────────────┐
│  Raspberry Pi   │ ───────────────► │  MediaPipe Pose  │
│  Camera Module  │                  │  Landmarker      │
└─────────────────┘                  └────────┬─────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │  33 个关键点输出  │
                                    └────────┬─────────┘
                                              │
              ┌───────────────────────────────┼───────────────────────────────┐
              ▼                               ▼                               ▼
        ┌─────────────┐                 ┌─────────────┐                 ┌─────────────┐
        │  颈部姿态    │                 │  躯干姿态    │                 │  可视化输出  │
        │  judge.py   │                 │  judge.py   │                 │  OpenCV     │
        └──────┬──────┘                 └──────┬──────┘                 └─────────────┘
               │                               │
               └───────────────┬───────────────┘
                               ▼
                        ┌─────────────┐
                        │  LED 控制    │
                        │  led_ctl.py │
                        └─────────────┘
```

### 2. 姿态判定算法（`judge.py`）

算法利用三维世界坐标（`pose_world_landmarks`）计算关键骨骼向量之间的夹角：

- **耳部中点** `(ear_l + ear_r) / 2`
- **肩部中点** `(shoulder_l + shoulder_r) / 2`
- **髋部中点** `(hip_l + hip_r) / 2`
- **膝部中点** `(knee_l + knee_r) / 2`

通过 `angle_between_vectors` 计算两向量夹角：

```python
neck_d = angle_between_vectors(ear→shoulder, 垂直向下)
body_d = angle_between_vectors(shoulder→hip, hip→knee)
```

阈值设定：

| 部位 | 判定条件 | 状态 |
|------|----------|------|
| 颈部 | `neck_d > 20°` | `front`（前倾） |
| 颈部 | `neck_d < 0°` | `back`（后仰） |
| 颈部 | 其他 | `normal`（正常） |
| 躯干 | `body_d > 100°` | `back`（后仰） |
| 躯干 | `body_d < 80°` | `front`（前倾） |
| 躯干 | 其他 | `normal`（正常） |

### 3. 异步推理（`main.py`）

```python
detector.detect_async(mp_image, timestamp_ms)
```

配合 `DETECTION_BUSY` 标志位，确保在当前帧推理尚未完成时，不会向模型塞入新帧，降低丢帧与资源冲突风险。每 3 帧执行一次姿态判定与 LED 控制，平衡实时性与稳定性。

### 4. LED 控制（`led_ctl.py`）

通过 `importlib.util` 动态加载树莓派 SenseStorm3 RCU 控制库 `/home/pi/sensestorm3-rcu/src/rcu.py`，调用 `set_color_light(port, brightness)` 方法：

- `led_on()` → `set_color_light(1, 7)` 点亮 LED
- `led_off()` → `set_color_light(1, 0)` 熄灭 LED

> 注：若在非树莓派环境运行，可注释掉 `led_ctl` 相关调用或自行适配 GPIO 库。

---

## 项目目录结构

```
A3-智能体育采访字幕翻译助手/
├── README.md                     # 项目说明文档
├── requirements.txt              # Python 依赖（mediapipe）
├── .gitignore                    # Git 忽略规则
├── pose_landmarker_full.task     # MediaPipe Pose Landmarker 模型文件
├── main.py                       # 主程序（推荐在树莓派运行，使用 picamera2）
├── pose.py                       # 兼容版本（使用 OpenCV VideoCapture，适合 PC 调试）
├── pose_bk.py                    # pose.py 的备份副本
├── judge.py                      # 姿态判定核心逻辑
└── led_ctl.py                    # LED 硬件控制封装
```

---

## 安装与运行说明

### 环境要求

- **硬件**：Raspberry Pi 4 / 5 + Raspberry Pi Camera Module（或 USB 摄像头）
- **操作系统**：Raspberry Pi OS（64-bit 推荐）
- **Python**：3.9+
- **关键依赖**：
  - `mediapipe`
  - `opencv-python`
  - `numpy`
  - `picamera2`（仅树莓派 Camera Module 需要）

### 安装步骤

1. 克隆或解压项目到树莓派目录：

   ```bash
   cd ~/A3-智能体育采访字幕翻译助手
   ```

2. 安装 Python 依赖：

   ```bash
   pip install -r requirements.txt
   # 若使用 picamera2，请确保系统已安装该库
   # sudo apt install -y python3-picamera2
   ```

3. （可选）若使用 SenseStorm/RCU 扩展板，请确认控制库路径正确：

   ```python
   # led_ctl.py 中默认路径
   file_path = "/home/pi/sensestorm3-rcu/src/rcu.py"
   ```

### 运行方式

#### 方式一：树莓派 + Camera Module（推荐）

```bash
python3 main.py
```

支持的命令行参数：

```bash
python3 main.py \
  --model pose_landmarker_full.task \
  --numPoses 1 \
  --minPoseDetectionConfidence 0.5 \
  --minPosePresenceConfidence 0.5 \
  --minTrackingConfidence 0.5 \
  --frameWidth 1280 \
  --frameHeight 960
```

#### 方式二：PC / Mac + USB 摄像头（调试用）

```bash
python3 pose.py
```

参数与 `main.py` 相同，额外支持 `--cameraId` 指定摄像头索引。

### 退出程序

在可视化窗口中按下键盘 **ESC** 键即可退出。

---

## 使用场景

1. **体育赛后采访**：将摄像头对准运动员上半身，实时监测坐姿/站姿，出现前倾或后仰时 LED 亮起提醒，帮助运动员维持最佳画面角度，便于后续字幕识别与翻译。
2. **主播/解说席姿态管理**：在直播或录播场景中，作为辅助提醒工具，防止长期不良坐姿影响形象与发音清晰度。
3. **教学演示**：可用于展示 MediaPipe 在边缘设备上的实时人体关键点检测与角度计算方案。

---

## 许可证 / 声明

- 本项目中的 `pose.py`、`pose_bk.py` 核心骨架参考了 [MediaPipe Authors](https://github.com/google-ai-edge/mediapipe) 的开源示例代码，遵循 **Apache License 2.0**。
- `pose_landmarker_full.task` 模型文件为 Google MediaPipe 官方预训练模型，仅供学习与研究使用。
- 其余代码（`main.py`、`judge.py`、`led_ctl.py`）由本项目团队基于教学与实践目的编写，欢迎交流与二次开发。

> **提示**：本系统仅作为姿态辅助提醒工具，检测结果受光线、遮挡、摄像头角度等因素影响，不作为医疗或专业运动康复诊断依据。

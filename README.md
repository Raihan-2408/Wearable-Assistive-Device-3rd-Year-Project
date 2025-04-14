# Wearable Assistive Device 3rd Year Project

A low-cost, wearable device for real-time object detection and auditory narration to support visually impaired individuals with spatial awareness and environmental context.

## 📌 Project Summary

This project presents an affordable and modular assistive wearable system designed to help visually impaired (VI) individuals navigate environments using real-time object detection and audio narration. Developed on the Raspberry Pi 4, the device uses AI models (YOLOv5n, EfficientDet Lite), an ultrasonic sensor for obstacle proximity feedback, and a text-to-speech engine to convey detected objects.

The system is built to function entirely offline and prioritizes low power consumption, user comfort, and intuitive interaction.

## 🎯 Key Features

- **Offline Real-Time Object Detection**
- **Text-to-Speech Narration (eSpeak / pyttsx3)**
- **Ultrasonic Obstacle Alert System**
- **Multi-object narration with duplicate filtering**
- **Lightweight, wearable, and fully mobile setup**
- **Modular camera mounting for flexibility**

## 🔧 Hardware Components

| Component                  | Function                                       |
|---------------------------|------------------------------------------------|
| Raspberry Pi 4 Model B    | Main processing unit                           |
| Pi Camera Module v2       | Real-time video input                          |
| HC-SR04 Ultrasonic Sensor | Obstacle detection with audible proximity beeps|
| Wired Over-Ear Earphones  | Audio feedback without blocking ambient sound |
| Power Bank (10,000 mAh)   | Portable power for extended usage              |
| 3D-Printed Housing        | Modular camera and board mounting              |

## 💻 Software Stack

- **Language**: Python 3
- **OS**: Raspberry Pi OS (Bullseye 11)
- **Libraries**:
  - OpenCV (cv2)
  - TensorFlow Lite / PyTorch
  - pyttsx3 / eSpeak
  - RPi.GPIO
  - Pygame (for audio beeps)
- **Models Tested**:
  - EfficientDet Lite0
  - YOLOv5n

 
## ⚙️ System Architecture

```mermaid
flowchart TD
    A[Pi Camera Input] --> B[AI Object Detection Model]
    B --> C[Filtering & Formatting]
    C --> D[TTS Engine - Narration]
    A --> E[Ultrasonic Sensor]
    E --> F[Beep Feedback]

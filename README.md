# 🌡️ InfiRay Micro III Python Control GUI

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GUI: PyQt5](https://img.shields.io/badge/GUI-PyQt5-green.svg)](https://pypi.org/project/PyQt5/)

A robust, cross-platform graphical user interface designed to control and view the **InfiRay Micro III thermal camera** via its Windows USB SDK. Built with modern Python, OpenCV, and PyQt5.

---

## ✨ Features

- **🔌 Plug & Play Device Connection:** Search and connect to available USB thermal cameras instantly.
- **🎥 Real-Time Thermal Video:** Smooth 16-bit YUYV raw feed converted beautifully into RGB in real-time.
- **🎯 ROI Temperature Measurement:** Draw a rectangle on the video feed to measure Max, Min, and Average temperatures in that exact region.
- **🛠️ Camera Control panel:**
  - 🔄 **Shutter Correction (NUC)** for calibrating image noise.
  - 🎨 **Multiple Color Palettes:** Toggle between White Hot, Black Hot, Iron, Rainbow, and more.
- **🌍 Environmental Tuning:** Dynamically adjust Emissivity, Distance, and Air Temperature for precise measurements.
- **📸 Screenshot Capture:** Save your current thermal discoveries as high-quality images.

---

## 📦 Requirements

- **OS:** Windows (Due to `USBSDK.dll` dependency)
- **Python:** Version 3.8 or newer (required for secure DLL loading strategies)
- **Packages:** Defined in `requirements.txt` (`pip install PyQt5 numpy opencv-python`)

---

## 🚀 Installation & Setup

1. **Clone or Download the Repository:**
   Ensure you have the entire project folder, including the `lib/` directory which houses the critical SDK files.

2. **Install Dependencies:**
   Open your terminal/command prompt and run:
   ```bash
   pip install -r requirements.txt
Run the Application: Start the GUI by executing:
python main.py
🖥️ How to Use
Click "Search Devices" to find your connected InfiRay Micro III camera.
Select the camera from the dropdown menu and click "Connect".
View the live thermal feed!
Draw on the video by clicking and dragging your mouse to create a Region of Interest (ROI) and see live temperature metrics.
Use the control panels on the right to tweak Palettes, environmental settings, or take a Screenshot.
📂 Project Structure
infiray_gui/
│
├── main.py               # 🚀 The main PyQt5 GUI application
├── infiray_sdk.py        # 🌉 Python ctypes wrapper for the C++ SDK
├── requirements.txt      # 📦 Python dependencies
├── README.md             # 📖 This documentation file
│
└── lib/                  # 🛠️ SDK Binaries and Headers
    ├── USBSDK.dll        # Windows 64-bit SDK Library
    ├── USBSDK.lib
    ├── USBSDK.h
    ├── InfEntity.h
    └── outPaletteFTII.dat# Palette data configuration
⚠️ Notes
The included USBSDK.dll and dependencies in the lib directory are 64-bit libraries provided by InfiRay. Make sure you are running a 64-bit installation of Python.
If you see a Failed to open device error, verify that the USB is properly connected and no other application is currently locking the camera's COM port.

# InfiRay Micro III Python Control GUI

This is a Python Graphical User Interface built with PyQt5 to control and view the InfiRay Micro III thermal camera via its Windows USB SDK.

## Requirements
- Windows OS (the SDK relies on `USBSDK.dll`)
- Python 3.7+
- Requirements in `requirements.txt` (`PyQt5`, `numpy`, `opencv-python`)

## Setup
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python main.py
   ```

## Features
- **Device Connection**: Search and connect to connected USB thermal cameras.
- **Video Display**: Real-time display of the thermal image.
- **ROI Temperature Measurement**: Draw a rectangle on the video using the mouse to measure the Max, Min, and Average temperature in that region.
- **Camera Controls**:
  - Shutter Correction (NUC).
  - Change color palettes (White Hot, Black Hot, Iron, Rainbow, etc.).
- **Environment Parameters**: Adjust Emissivity, Distance, and Air Temperature.
- **Capture**: Save the current thermal frame as an image.

## Notes
- The included `USBSDK.dll` and dependencies in the `lib` directory are 64-bit and provided by InfiRay.

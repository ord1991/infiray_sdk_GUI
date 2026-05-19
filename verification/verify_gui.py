import sys
import os
import ctypes
import numpy as np

# Mock SDK to verify GUI logic calls
class MockSDK:
    def __init__(self, *args): pass
    def create(self): pass
    def login_device(self, *args): pass
    def get_width(self): return 384
    def get_height(self): return 288
    def get_core_type(self): return 2
    def get_sn_pn(self): return "SN123", "PN456"
    def get_fpa_temp(self): return 35.5
    def get_wtr_status(self): return 1
    def get_wtr_low_threshold(self): return 0
    def get_wtr_high_threshold(self): return 1000000
    def get_env_param(self):
        class Env:
            emissivity = 9500
            airTemp = 250000
            reflectTemp = 250000
            humidity = 500000
            distance = 20000
        return Env()
    def get_temp_unit(self): return 0
    def get_camera_temp(self): return 36.0
    def close_device(self): pass
    def release_sdk(self): pass

# Patch InfiRaySDK before importing main
import infiray_sdk
infiray_sdk.InfiRaySDK = MockSDK

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from main import CameraControlApp

def capture():
    try:
        app.processEvents()

        # Verify histogram removal
        has_hist = hasattr(window, 'hist_label')
        print(f"Histogram components present (attr): {has_hist}")

        # Verify scaling configuration
        scaled = window.video_label.hasScaledContents()
        print(f"Video label scaled contents: {scaled}")

        # Grab the window
        screen = window.grab()
        screen.save("verification/gui_screenshot_v3.png")
        print("Screenshot saved to verification/gui_screenshot_v3.png")
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
    finally:
        app.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraControlApp()
    window.show()
    QTimer.singleShot(2000, capture)
    sys.exit(app.exec_())

import sys
import os
import ctypes
import re
import numpy as np
import cv2
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QComboBox,
                             QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
                             QMessageBox, QFileDialog, QCheckBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from infiray_sdk import InfiRaySDK


class SignalEmitter(QObject):
    update_video = pyqtSignal(np.ndarray)
    update_temp = pyqtSignal(np.ndarray)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CameraControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("InfiRay Micro III Control")
        self.resize(1024, 768)
        self.statusBar().showMessage("Ready")

        self.sdk = None
        self.connected = False
        self.core_type = 2  # MicroIII

        self.width = 384
        self.height = 288

        self.emitter = SignalEmitter()
        self.emitter.update_video.connect(self.display_video)
        self.emitter.update_temp.connect(self.process_temp)

        self.current_frame = None
        self.current_temp_frame = None

        self.drawing = False
        self.roi_start = None
        self.roi_end = None
        self.roi_rect = None

        self.init_ui()
        self.init_sdk()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Video Area
        self.video_label = QLabel("No Video")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white; font-size: 24px;")
        self.video_label.setMinimumSize(640, 480)
        self.video_label.mousePressEvent = self.mouse_press
        self.video_label.mouseMoveEvent = self.mouse_move
        self.video_label.mouseReleaseEvent = self.mouse_release
        main_layout.addWidget(self.video_label, 1)

        # Controls Area
        controls_layout = QVBoxLayout()
        main_layout.addLayout(controls_layout)

        # Connection Group
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout()
        self.btn_search = QPushButton("Search Devices")
        self.btn_search.clicked.connect(self.search_devices)
        self.cb_devices = QComboBox()
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self.connect_device)
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.clicked.connect(self.disconnect_device)
        self.btn_disconnect.setEnabled(False)

        conn_layout.addWidget(self.btn_search)
        conn_layout.addWidget(self.cb_devices)
        conn_layout.addWidget(self.btn_connect)
        conn_layout.addWidget(self.btn_disconnect)
        conn_group.setLayout(conn_layout)
        controls_layout.addWidget(conn_group)

        # Camera Controls Group
        cam_group = QGroupBox("Camera Controls")
        cam_layout = QVBoxLayout()

        self.btn_nuc = QPushButton("Shutter Correction (NUC)")
        self.btn_nuc.clicked.connect(self.do_nuc)
        cam_layout.addWidget(self.btn_nuc)

        pal_layout = QHBoxLayout()
        pal_layout.addWidget(QLabel("Palette:"))
        self.cb_palette = QComboBox()
        self.cb_palette.addItems(["White Hot", "Black Hot", "Iron", "Rainbow", "Medical", "Arctic", "..."])
        self.cb_palette.currentIndexChanged.connect(self.change_palette)
        pal_layout.addWidget(self.cb_palette)
        cam_layout.addLayout(pal_layout)

        cap_layout = QHBoxLayout()
        self.btn_snap = QPushButton("Screenshot")
        self.btn_snap.clicked.connect(self.screenshot)
        cap_layout.addWidget(self.btn_snap)
        cam_layout.addLayout(cap_layout)

        cam_group.setLayout(cam_layout)
        cam_group.setEnabled(False)
        self.cam_group = cam_group
        controls_layout.addWidget(cam_group)

        # Envir Params Group
        env_group = QGroupBox("Environment Parameters")
        env_layout = QFormLayout()

        self.sp_emis = QDoubleSpinBox()
        self.sp_emis.setRange(0.01, 1.00)
        self.sp_emis.setSingleStep(0.01)
        self.sp_emis.setValue(0.95)

        self.sp_dist = QSpinBox()
        self.sp_dist.setRange(1, 1000)
        self.sp_dist.setValue(2)  # m

        self.sp_air_temp = QSpinBox()
        self.sp_air_temp.setRange(-40, 150)
        self.sp_air_temp.setValue(25)

        env_layout.addRow("Emissivity:", self.sp_emis)
        env_layout.addRow("Distance (m):", self.sp_dist)
        env_layout.addRow("Air Temp (C):", self.sp_air_temp)

        self.btn_set_env = QPushButton("Set Environment")
        self.btn_set_env.clicked.connect(self.set_env_params)
        env_layout.addRow(self.btn_set_env)

        env_group.setLayout(env_layout)
        env_group.setEnabled(False)
        self.env_group = env_group
        controls_layout.addWidget(env_group)

        info_group = QGroupBox("ROI Temperature")
        info_layout = QVBoxLayout()
        self.lbl_info = QLabel("Draw rectangle on video to measure ROI.")
        self.lbl_cam_temp = QLabel("Camera Temp: N/A")

        btn_clear_roi = QPushButton("Clear ROI")
        btn_clear_roi.clicked.connect(self.clear_roi)

        info_layout.addWidget(self.lbl_info)
        info_layout.addWidget(self.lbl_cam_temp)
        info_layout.addWidget(btn_clear_roi)
        info_group.setLayout(info_layout)
        controls_layout.addWidget(info_group)

        # Scene Statistics Group
        stats_group = QGroupBox("Scene Statistics")
        stats_layout = QFormLayout()
        self.lbl_max_temp = QLabel("Waiting for data...")
        self.lbl_min_temp = QLabel("Waiting for data...")
        self.lbl_center_temp = QLabel("Waiting for data...")
        stats_layout.addRow("Max Temp:", self.lbl_max_temp)
        stats_layout.addRow("Min Temp:", self.lbl_min_temp)
        stats_layout.addRow("Center Temp:", self.lbl_center_temp)
        stats_group.setLayout(stats_layout)
        controls_layout.addWidget(stats_group)

        # Histogram Group
        hist_group = QGroupBox("Histogram")
        hist_layout = QVBoxLayout()
        self.hist_label = QLabel()
        self.hist_label.setFixedSize(256, 120)
        self.hist_label.setStyleSheet("background-color: #111; border: 1px solid #444;")
        hist_layout.addWidget(self.hist_label)
        hist_group.setLayout(hist_layout)
        controls_layout.addWidget(hist_group)

        # Raw Data Group
        raw_group = QGroupBox("Raw Data")
        raw_layout = QVBoxLayout()
        self.chk_view_raw = QCheckBox("View Raw (16-bit)")
        self.btn_save_raw = QPushButton("Save Raw Data")
        self.btn_save_raw.clicked.connect(self.save_raw_data)
        raw_layout.addWidget(self.chk_view_raw)
        raw_layout.addWidget(self.btn_save_raw)
        raw_group.setLayout(raw_layout)
        controls_layout.addWidget(raw_group)

        controls_layout.addStretch(1)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_info)

    def init_sdk(self):
        try:
            dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'USBSDK.dll')
            if sys.platform == 'win32':
                logging.info(f"Loading SDK from {dll_path}")
                self.sdk = InfiRaySDK(dll_path)
                self.sdk.create()
                self.sdk.login_device()
                logging.info("SDK initialized and device logged in.")
            else:
                logging.warning("Not on Windows, SDK not fully initialized.")
        except Exception as e:
            logging.error(f"SDK Load Error: {e}")
            QMessageBox.warning(self, "SDK Load Error", str(e))

    def search_devices(self):
        if not self.sdk: return
        logging.info("Searching for devices...")
        self.cb_devices.clear()

        if self.sdk.handle is None:
            self.sdk.create()

        dev_list = self.sdk.search_device()
        logging.info(f"Found {dev_list.iNumber} devices and {dev_list.iComCount} COM ports.")
        self.devices = []

        com_ports = []
        for i in range(dev_list.iComCount):
            com_name = dev_list.ComNameInfo[i].cComPort.decode('utf-8', 'ignore')
            port_num = 0
            try:
                match = re.search(r'\d+', com_name)
                if match:
                    port_num = int(match.group())
            except Exception:
                pass
            com_ports.append(port_num)

        for i in range(dev_list.iNumber):
            name = dev_list.DevInfo[i].cName.decode('utf-8', 'ignore')
            port_num = com_ports[i] if i < len(com_ports) else 0
            self.devices.append((i, name, port_num))
            self.cb_devices.addItem(f"{i}: {name} (Port: {port_num})")

    def py_video_cb(self, pBuffer, w, h, context):
        if pBuffer:
            try:
                # SDK returns YUV422 (UYVY format), meaning 2 bytes per pixel
                size = w * h * 2
                BufferType = ctypes.c_ubyte * size
                buf = ctypes.cast(pBuffer, ctypes.POINTER(BufferType)).contents
                arr_yuv = np.frombuffer(buf, dtype=np.uint8).reshape((h, w, 2)).copy()
                arr_rgb = cv2.cvtColor(arr_yuv, cv2.COLOR_YUV2RGB_YUYV)
                self.emitter.update_video.emit(arr_rgb)
            except Exception as e:
                logging.error(f"Error in video callback: {e}")

    def py_temp_cb(self, pBuffer, w, h, context):
        if pBuffer:
            try:
                size = w * h * 2
                BufferType = ctypes.c_ubyte * size
                buf = ctypes.cast(pBuffer, ctypes.POINTER(BufferType)).contents
                arr = np.frombuffer(buf, dtype=np.uint16).reshape((h, w)).copy()
                self.emitter.update_temp.emit(arr)
            except Exception as e:
                logging.error(f"Error in temp callback: {e}")

    def connect_device(self):
        if not self.sdk: return
        idx = self.cb_devices.currentIndex()
        if idx < 0: return

        dev_id, dev_name, port_indx = self.devices[idx]

        hwnd = int(self.winId()) if sys.platform == 'win32' else None
        self.sdk.login_device(hwnd)

        # Register callbacks BEFORE opening device
        self.sdk.set_video_callback(self.py_video_cb)
        self.sdk.set_temp_callback(self.py_temp_cb)

        res = self.sdk.open_device(idx, port_indx)

        if res:
            self.connected = True
            logging.info(f"Connected to device {idx} on port {port_indx}")

            w = self.sdk.get_width()
            h = self.sdk.get_height()
            if w > 0 and h > 0:
                self.width, self.height = w, h

            ct = self.sdk.get_core_type()
            tm = self.sdk.get_temp_measure_type()
            sn, pn = self.sdk.get_sn_pn()
            logging.info(f"Device Info: CoreType={ct}, TempMeasureType={tm}, SN={sn}, PN={pn}")
            self.core_type = ct if ct > 0 else 2

            # Ensure temp measurement is active
            self.sdk.set_temp_unit(0) # 0: Celsius

            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.cam_group.setEnabled(True)
            self.env_group.setEnabled(True)
            self.timer.start(2000)
        else:
            QMessageBox.warning(self, "Error", "Failed to open device.")

    def disconnect_device(self):
        if not self.sdk: return
        self.timer.stop()
        self.sdk.close_device()
        self.connected = False
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.cam_group.setEnabled(False)
        self.env_group.setEnabled(False)
        self.video_label.clear()
        self.video_label.setText("No Video")

    def do_nuc(self):
        if self.sdk:
            self.sdk.shutter_correction(self.core_type, 1)

    def change_palette(self, index):
        if self.sdk:
            self.sdk.set_color_plate(self.core_type, index)

    def screenshot(self):
        if self.current_frame is not None:
            filename, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "Images (*.png *.jpg)")
            if filename:
                img_bgr = cv2.cvtColor(self.current_frame, cv2.COLOR_RGB2BGR)
                cv2.imwrite(filename, img_bgr)

    def set_env_params(self):
        if self.sdk:
            emis = int(self.sp_emis.value() * 10000)
            air = int(self.sp_air_temp.value() * 10000)
            dist = int(self.sp_dist.value() * 10000)
            self.sdk.set_envir_param(emis, air, air, 50000, dist)

    def update_info(self):
        if self.sdk and self.connected:
            t = self.sdk.get_camera_temp()
            if t is not None:
                self.lbl_cam_temp.setText(f"Camera Temp: {t:.2f} C")

    def display_video(self, frame):
        if self.chk_view_raw.isChecked():
            if self.current_temp_frame is not None:
                # Normalize 16-bit raw data to 8-bit for display
                raw = self.current_temp_frame.astype(np.float32)
                rmin, rmax = np.min(raw), np.max(raw)
                if rmax > rmin:
                    raw_norm = ((raw - rmin) / (rmax - rmin) * 255.0).astype(np.uint8)
                else:
                    raw_norm = np.zeros_like(raw, dtype=np.uint8)

                h, w = raw_norm.shape
                qimg = QImage(raw_norm.data, w, h, w, QImage.Format_Grayscale8).copy()
            else:
                # If no temp frame yet, show the normal frame but maybe with a status message
                self.current_frame = frame
                h, w, ch = frame.shape
                qimg = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888).copy()
                self.statusBar().showMessage("Waiting for 16-bit temperature data...", 1000)
        else:
            self.current_frame = frame
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(qimg)
        pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio)

        if self.roi_rect or (self.roi_start and self.roi_end):
            painter = QPainter(pixmap)
            painter.setPen(QPen(Qt.green, 2))
            label_w, label_h = pixmap.width(), pixmap.height()
            scale_x = label_w / w
            scale_y = label_h / h

            if self.roi_rect:
                x = int(self.roi_rect[0] * scale_x)
                y = int(self.roi_rect[1] * scale_y)
                rw = int(self.roi_rect[2] * scale_x)
                rh = int(self.roi_rect[3] * scale_y)
                painter.drawRect(x, y, rw, rh)
            elif self.roi_start and self.roi_end:
                sx = int(self.roi_start[0] * scale_x)
                sy = int(self.roi_start[1] * scale_y)
                ex = int(self.roi_end[0] * scale_x)
                ey = int(self.roi_end[1] * scale_y)
                painter.drawRect(min(sx, ex), min(sy, ey), abs(sx - ex), abs(sy - ey))
            painter.end()

        self.video_label.setPixmap(pixmap)

    def process_temp(self, temp_frame):
        self.current_temp_frame = temp_frame

        # Global Statistics
        h, w = temp_frame.shape
        max_t = np.max(temp_frame) / 100.0
        min_t = np.min(temp_frame) / 100.0
        center_t = temp_frame[h // 2, w // 2] / 100.0

        self.lbl_max_temp.setText(f"{max_t:.1f} C")
        self.lbl_min_temp.setText(f"{min_t:.1f} C")
        self.lbl_center_temp.setText(f"{center_t:.1f} C")

        self.update_histogram(temp_frame)

        if self.roi_rect:
            x, y, w_roi, h_roi = self.roi_rect
            y2, x2 = min(y + h_roi, h), min(x + w_roi, w)
            y1, x1 = max(0, y), max(0, x)
            roi_data = temp_frame[y1:y2, x1:x2]
            if roi_data.size > 0:
                max_roi = np.max(roi_data) / 100.0
                min_roi = np.min(roi_data) / 100.0
                avg_roi = np.mean(roi_data) / 100.0
                self.lbl_info.setText(f"ROI Temp:\nMax: {max_roi:.1f} C\nMin: {min_roi:.1f} C\nAvg: {avg_roi:.1f} C")

    def get_video_click_pos(self, event):
        if not self.video_label.pixmap(): return None
        label_size = self.video_label.size()
        pix_size = self.video_label.pixmap().size()
        offset_x = (label_size.width() - pix_size.width()) / 2
        offset_y = (label_size.height() - pix_size.height()) / 2
        click_x = event.pos().x() - offset_x
        click_y = event.pos().y() - offset_y
        if 0 <= click_x <= pix_size.width() and 0 <= click_y <= pix_size.height():
            scale_x = self.width / pix_size.width()
            scale_y = self.height / pix_size.height()
            return int(click_x * scale_x), int(click_y * scale_y)
        return None

    def mouse_press(self, event):
        pos = self.get_video_click_pos(event)
        if pos:
            self.drawing = True
            self.roi_start = pos
            self.roi_end = pos
            self.roi_rect = None

    def mouse_move(self, event):
        if self.drawing:
            pos = self.get_video_click_pos(event)
            if pos: self.roi_end = pos

    def mouse_release(self, event):
        if self.drawing:
            self.drawing = False
            pos = self.get_video_click_pos(event)
            if pos:
                self.roi_end = pos
                x = min(self.roi_start[0], self.roi_end[0])
                y = min(self.roi_start[1], self.roi_end[1])
                w = abs(self.roi_start[0] - self.roi_end[0])
                h = abs(self.roi_start[1] - self.roi_end[1])
                if w > 5 and h > 5:
                    self.roi_rect = (x, y, w, h)
                else:
                    self.roi_rect = None
            self.roi_start = None
            self.roi_end = None

    def clear_roi(self):
        self.roi_rect = None
        self.lbl_info.setText("Draw rectangle on video to measure ROI.")

    def update_histogram(self, temp_frame):
        try:
            # Calculate histogram of temperature data
            # temp_frame is uint16, values are Temp*100
            min_val = float(np.min(temp_frame))
            max_val = float(np.max(temp_frame))

            if max_val <= min_val:
                logging.warning(f"Histogram: max_val ({max_val}) <= min_val ({min_val})")
                return

            # Use 256 bins between min and max value
            hist = cv2.calcHist([temp_frame.astype(np.float32)], [0], None, [256], [min_val, max_val])
            cv2.normalize(hist, hist, 0, 100, cv2.NORM_MINMAX)

            # Draw histogram
            width, height = 256, 100
            hist_img = np.zeros((height, width, 3), dtype=np.uint8)
            # Draw background grid
            for i in range(0, 256, 64):
                cv2.line(hist_img, (i, 0), (i, height), (40, 40, 40), 1)

            # Use height-1 to stay within image bounds
            for i in range(1, 256):
                y1 = int((height - 1) - (hist[i-1][0] * (height - 1) / 100.0))
                y2 = int((height - 1) - (hist[i][0] * (height - 1) / 100.0))
                cv2.line(hist_img, (i - 1, y1), (i, y2), (0, 255, 0), 1)

            # Ensure we make a copy for the QImage to avoid memory issues with ephemeral numpy arrays
            qimg = QImage(hist_img.data, width, height, width * 3, QImage.Format_RGB888).copy()
            self.hist_label.setPixmap(QPixmap.fromImage(qimg))
        except Exception as e:
            logging.error(f"Error updating histogram: {e}")

    def save_raw_data(self):
        if self.current_temp_frame is not None:
            filename, _ = QFileDialog.getSaveFileName(self, "Save Raw Data", "thermal_raw.npy", "NumPy files (*.npy)")
            if filename:
                np.save(filename, self.current_temp_frame)
                self.statusBar().showMessage(f"Raw data saved to {filename}", 3000)

    def closeEvent(self, event):
        if self.sdk:
            if self.connected:
                self.disconnect_device()
            self.sdk.release_sdk()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CameraControlApp()
    window.show()
    sys.exit(app.exec_())
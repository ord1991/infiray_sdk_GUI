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
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QMutex
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from infiray_sdk import InfiRaySDK

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Performance Optimization: Pre-compile common regex for device parsing
COM_PORT_RE = re.compile(r'\d+')

class SignalEmitter(QObject):
    update_video = pyqtSignal(np.ndarray)
    update_temp = pyqtSignal(np.ndarray)

class CameraControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("InfiRay Micro III Professional Control")
        self.resize(1100, 800)

        self.sdk = None
        self.sdk_mutex = QMutex()
        self.connected = False
        self.core_type = 2  # Default to MicroIII

        self.width = 384
        self.height = 288

        self.emitter = SignalEmitter()
        self.emitter.update_video.connect(self.display_video)
        self.emitter.update_temp.connect(self.process_temp)

        self.current_frame = None
        self.current_temp_frame = None

        self.video_cb_count = 0
        self.temp_cb_count = 0

        self.drawing = False
        self.roi_start = None
        self.roi_end = None
        self.roi_rect = None

        self.init_ui()
        self.init_sdk()

        self.statusBar().showMessage("Ready")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Video Area
        self.video_label = QLabel("No Video Stream")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000; color: #555; font-size: 20px; border: 2px solid #333;")
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setScaledContents(True)
        self.video_label.mousePressEvent = self.mouse_press
        self.video_label.mouseMoveEvent = self.mouse_move
        self.video_label.mouseReleaseEvent = self.mouse_release
        main_layout.addWidget(self.video_label, 1)

        # Right Side Controls
        controls_scroll = QWidget()
        controls_layout = QVBoxLayout(controls_scroll)
        main_layout.addWidget(controls_scroll)

        # Connection Group
        conn_group = QGroupBox("Device Connection")
        conn_vbox = QVBoxLayout()
        self.btn_search = QPushButton("Search Devices")
        self.btn_search.clicked.connect(self.search_devices)
        self.cb_devices = QComboBox()
        self.btn_connect = QPushButton("Connect Camera")
        self.btn_connect.setStyleSheet("background-color: #2a2; color: white; font-weight: bold;")
        self.btn_connect.clicked.connect(self.connect_device)
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.clicked.connect(self.disconnect_device)
        self.btn_disconnect.setEnabled(False)

        conn_vbox.addWidget(self.btn_search)
        conn_vbox.addWidget(self.cb_devices)
        conn_vbox.addWidget(self.btn_connect)
        conn_vbox.addWidget(self.btn_disconnect)
        conn_group.setLayout(conn_vbox)
        controls_layout.addWidget(conn_group)

        # Scene Info & Statistics
        stats_group = QGroupBox("Scene Statistics")
        stats_form = QFormLayout()
        self.lbl_max_temp = QLabel("---")
        self.lbl_min_temp = QLabel("---")
        self.lbl_center_temp = QLabel("---")
        self.lbl_core_type = QLabel("Unknown")
        self.lbl_sn_pn = QLabel("--- / ---")
        self.lbl_fpa_temp = QLabel("---")
        stats_form.addRow("Core Type:", self.lbl_core_type)
        stats_form.addRow("SN/PN:", self.lbl_sn_pn)
        stats_form.addRow("FPA Temp:", self.lbl_fpa_temp)
        stats_form.addRow("<b>Max Temp:</b>", self.lbl_max_temp)
        stats_form.addRow("<b>Min Temp:</b>", self.lbl_min_temp)
        stats_form.addRow("<b>Center Temp:</b>", self.lbl_center_temp)
        stats_group.setLayout(stats_form)
        controls_layout.addWidget(stats_group)

        # ROI Results
        roi_group = QGroupBox("ROI Measurement")
        roi_vbox = QVBoxLayout()
        self.lbl_roi_info = QLabel("Draw rectangle on video to measure.")
        self.lbl_roi_info.setWordWrap(True)
        btn_clear_roi = QPushButton("Clear ROI")
        btn_clear_roi.clicked.connect(self.clear_roi)
        roi_vbox.addWidget(self.lbl_roi_info)
        roi_vbox.addWidget(btn_clear_roi)
        roi_group.setLayout(roi_vbox)
        controls_layout.addWidget(roi_group)

        # Advanced Configuration (WTR & Edge)
        adv_group = QGroupBox("Advanced Configuration")
        adv_vbox = QVBoxLayout()

        wtr_hbox = QHBoxLayout()
        self.chk_wtr = QCheckBox("Wide Temp Range (WTR)")
        self.chk_wtr.toggled.connect(self.toggle_wtr)
        wtr_hbox.addWidget(self.chk_wtr)
        adv_vbox.addLayout(wtr_hbox)

        wtr_params = QFormLayout()
        self.sp_wtr_low = QSpinBox()
        self.sp_wtr_low.setRange(-50, 500)
        self.sp_wtr_low.valueChanged.connect(self.update_wtr_thresholds)
        self.sp_wtr_high = QSpinBox()
        self.sp_wtr_high.setRange(-50, 1500)
        self.sp_wtr_high.valueChanged.connect(self.update_wtr_thresholds)
        wtr_params.addRow("WTR Low Threshold:", self.sp_wtr_low)
        wtr_params.addRow("WTR High Threshold:", self.sp_wtr_high)
        adv_vbox.addLayout(wtr_params)

        edge_params = QFormLayout()
        self.sp_edge_det = QSpinBox()
        self.sp_edge_det.setRange(0, 100)
        self.sp_edge_enh = QSpinBox()
        self.sp_edge_enh.setRange(0, 100)
        edge_params.addRow("Edge Detect Level:", self.sp_edge_det)
        edge_params.addRow("Edge Enhance Level:", self.sp_edge_enh)
        adv_vbox.addLayout(edge_params)

        adv_group.setLayout(adv_vbox)
        controls_layout.addWidget(adv_group)

        # Raw Data & Capture
        raw_group = QGroupBox("Data Acquisition")
        raw_vbox = QVBoxLayout()
        self.chk_view_raw = QCheckBox("View Raw 16-bit (Grayscale)")
        self.btn_save_raw = QPushButton("Export Raw (.npy)")
        self.btn_save_raw.clicked.connect(self.save_raw_data)
        self.btn_snap = QPushButton("Save Screenshot (RGB)")
        self.btn_snap.clicked.connect(self.screenshot)
        raw_vbox.addWidget(self.chk_view_raw)
        raw_vbox.addWidget(self.btn_save_raw)
        raw_vbox.addWidget(self.btn_snap)
        raw_group.setLayout(raw_vbox)
        controls_layout.addWidget(raw_group)

        # Camera Configuration
        cfg_group = QGroupBox("Camera Config")
        cfg_vbox = QVBoxLayout()
        self.btn_nuc = QPushButton("Shutter Correction (NUC)")
        self.btn_nuc.clicked.connect(self.do_nuc)
        pal_hbox = QHBoxLayout()
        pal_hbox.addWidget(QLabel("Palette:"))
        self.cb_palette = QComboBox()
        self.cb_palette.addItems(["White Hot", "Black Hot", "Iron", "Rainbow", "Medical", "Arctic"])
        self.cb_palette.currentIndexChanged.connect(self.change_palette)
        pal_hbox.addWidget(self.cb_palette)

        unit_hbox = QHBoxLayout()
        unit_hbox.addWidget(QLabel("Unit:"))
        self.cb_unit = QComboBox()
        self.cb_unit.addItems(["Celsius", "Fahrenheit", "Kelvin"])
        self.cb_unit.currentIndexChanged.connect(self.change_temp_unit)
        unit_hbox.addWidget(self.cb_unit)

        cfg_vbox.addWidget(self.btn_nuc)
        cfg_vbox.addLayout(pal_hbox)
        cfg_vbox.addLayout(unit_hbox)
        cfg_group.setLayout(cfg_vbox)
        controls_layout.addWidget(cfg_group)

        # Environmental Calibration
        env_group = QGroupBox("Environmental Calibration")
        env_form = QFormLayout()
        self.sp_emiss = QDoubleSpinBox()
        self.sp_emiss.setRange(0.01, 1.0)
        self.sp_emiss.setSingleStep(0.01)
        self.sp_emiss.valueChanged.connect(self.update_env_params)

        self.sp_air_temp = QSpinBox()
        self.sp_air_temp.setRange(-50, 100)
        self.sp_air_temp.valueChanged.connect(self.update_env_params)

        self.sp_reflect_temp = QSpinBox()
        self.sp_reflect_temp.setRange(-50, 100)
        self.sp_reflect_temp.valueChanged.connect(self.update_env_params)

        self.sp_humidity = QSpinBox()
        self.sp_humidity.setRange(0, 100)
        self.sp_humidity.valueChanged.connect(self.update_env_params)

        self.sp_distance = QDoubleSpinBox()
        self.sp_distance.setRange(0.1, 50.0)
        self.sp_distance.valueChanged.connect(self.update_env_params)

        env_form.addRow("Emissivity:", self.sp_emiss)
        env_form.addRow("Air Temp (°C):", self.sp_air_temp)
        env_form.addRow("Reflect Temp (°C):", self.sp_reflect_temp)
        env_form.addRow("Humidity (%):", self.sp_humidity)
        env_form.addRow("Distance (m):", self.sp_distance)
        env_group.setLayout(env_form)
        controls_layout.addWidget(env_group)

        controls_layout.addStretch(1)
        self.ctrl_groups = [stats_group, roi_group, raw_group, cfg_group, adv_group, env_group]
        for g in self.ctrl_groups: g.setEnabled(False)

        self.diag_timer = QTimer()
        self.diag_timer.timeout.connect(self.update_diagnostics)

    def init_sdk(self):
        try:
            dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'USBSDK.dll')
            if sys.platform == 'win32':
                self.sdk = InfiRaySDK(dll_path)
                self.sdk.create()
                self.sdk.login_device()
                logging.info("SDK initialized.")
            else:
                logging.warning("Non-Windows OS detected. SDK functionality is limited.")
        except Exception as e:
            logging.error(f"SDK Initialization Failed: {e}")
            QMessageBox.critical(self, "SDK Error", f"Failed to load SDK: {e}")

    def search_devices(self):
        if not self.sdk: return
        self.cb_devices.clear()
        self.sdk_mutex.lock()
        dev_list = self.sdk.search_device()
        self.sdk_mutex.unlock()
        logging.info(f"Devices: {dev_list.iNumber}, COM Ports: {dev_list.iComCount}")

        self.devices = []
        # Defensive Optimization: Clamp iteration to MAX_DEVICE_NUM (50) to prevent out-of-bounds
        num_devs = min(dev_list.iNumber, 50)
        for i in range(num_devs):
            name = dev_list.DevInfo[i].cName.decode('utf-8', 'ignore')
            port_name = dev_list.ComNameInfo[i].cComPort.decode('utf-8', 'ignore')
            port_num = 0
            try:
                match = COM_PORT_RE.search(port_name)
                if match: port_num = int(match.group())
            except (ValueError, TypeError):
                logging.warning(f"Failed to parse COM port for {name}: {port_name}")

            self.devices.append((i, name, port_num))
            self.cb_devices.addItem(f"{name} (COM{port_num})")

    def py_video_cb(self, pBuffer, w, h, context):
        if pBuffer:
            self.video_cb_count += 1
            try:
                size = w * h * 2
                BufferType = ctypes.c_ubyte * size
                buf_ptr = ctypes.cast(pBuffer, ctypes.POINTER(BufferType))

                # Optimized extraction: Use frombuffer without copy as we process it immediately
                arr_yuv = np.frombuffer(buf_ptr.contents, dtype=np.uint8).reshape((h, w, 2))
                arr_rgb = cv2.cvtColor(arr_yuv, cv2.COLOR_YUV2RGB_YUYV)

                det_level = self.sp_edge_det.value()
                enh_level = self.sp_edge_enh.value()

                # Performance Optimization: Only perform color conversion and buffer management if needed
                if det_level > 0 or enh_level > 0:
                    gray = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2GRAY)

                    # Performance Optimization: Re-use or allocate buffer efficiently
                    processed = np.empty_like(gray)
                    src_p = gray.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
                    dst_p = processed.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))

                    self.sdk_mutex.lock()
                    if det_level > 0:
                        self.sdk.edge_detect(src_p, dst_p, w, h, det_level)
                        if enh_level > 0:
                            # Chain processing: output of detect becomes input of enhance
                            # Swap buffers to avoid extra allocation
                            src_p, dst_p = dst_p, src_p
                            self.sdk.edge_enhance(src_p, dst_p, w, h, enh_level)
                            gray = np.frombuffer(ctypes.string_at(dst_p, gray.nbytes), dtype=np.uint8).reshape(gray.shape)
                        else:
                            gray = processed
                    elif enh_level > 0:
                        self.sdk.edge_enhance(src_p, dst_p, w, h, enh_level)
                        gray = processed
                    self.sdk_mutex.unlock()

                    arr_rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

                self.emitter.update_video.emit(arr_rgb)
            except Exception as e:
                logging.error(f"Video CB Error: {e}")

    def py_temp_cb(self, pBuffer, w, h, context):
        if pBuffer:
            self.temp_cb_count += 1
            try:
                size = w * h * 2
                BufferType = ctypes.c_ubyte * size
                buf = ctypes.cast(pBuffer, ctypes.POINTER(BufferType)).contents
                arr = np.frombuffer(buf, dtype=np.uint16).reshape((h, w)).copy()
                self.emitter.update_temp.emit(arr)
            except Exception as e:
                logging.error(f"Temp CB Error: {e}")

    def connect_device(self):
        if not self.sdk: return
        idx = self.cb_devices.currentIndex()
        if idx < 0: return

        dev_id, dev_name, port_indx = self.devices[idx]
        hwnd = int(self.winId()) if sys.platform == 'win32' else None

        self.sdk_mutex.lock()
        self.sdk.login_device(hwnd)
        self.sdk.set_video_callback(self.py_video_cb)
        self.sdk.set_temp_callback(self.py_temp_cb)
        res = self.sdk.open_device(idx, port_indx)
        self.sdk_mutex.unlock()

        if res:
            self.connected = True
            logging.info(f"Connected to {dev_name}")
            self.video_cb_count = 0
            self.temp_cb_count = 0

            QTimer.singleShot(1000, self._finalize_connection)

            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            for g in self.ctrl_groups: g.setEnabled(True)
            self.diag_timer.start(3000)
        else:
            QMessageBox.warning(self, "Connection Failed", "Could not open device.")

    def _finalize_connection(self):
        if not self.connected: return

        self.sdk_mutex.lock()
        w, h = self.sdk.get_width(), self.sdk.get_height()
        if w > 0: self.width, self.height = w, h

        ct = self.sdk.get_core_type()
        self.core_type = ct if ct > 0 else 2

        sn, pn = self.sdk.get_sn_pn()
        fpa_temp = self.sdk.get_fpa_temp()

        wtr_status = self.sdk.get_wtr_status()
        wtr_low = self.sdk.get_wtr_low_threshold()
        wtr_high = self.sdk.get_wtr_high_threshold()

        env = self.sdk.get_env_param()
        unit = self.sdk.get_temp_unit()

        self.sdk_mutex.unlock()

        self.lbl_sn_pn.setText(f"{sn} / {pn}")
        if fpa_temp is not None: self.lbl_fpa_temp.setText(f"{fpa_temp:.1f} °C")

        if wtr_status is not None: self.chk_wtr.setChecked(bool(wtr_status))
        if wtr_low is not None: self.sp_wtr_low.setValue(wtr_low // 10000)
        if wtr_high is not None: self.sp_wtr_high.setValue(wtr_high // 10000)

        if env:
            self.sp_emiss.setValue(env.emissivity / 10000.0)
            self.sp_air_temp.setValue(env.airTemp // 10000)
            self.sp_reflect_temp.setValue(env.reflectTemp // 10000)
            self.sp_humidity.setValue(env.humidity // 10000)
            self.sp_distance.setValue(env.distance / 10000.0)

        if unit is not None: self.cb_unit.setCurrentIndex(unit)

        core_names = {1:"LT", 2:"MicroIII Temp", 3:"MicroIII Image", 4:"AT200F"}
        self.lbl_core_type.setText(core_names.get(self.core_type, f"Other ({self.core_type})"))
        logging.info("Connection parameters finalized.")

    def disconnect_device(self):
        self.sdk_mutex.lock()
        if self.sdk: self.sdk.close_device()
        self.sdk_mutex.unlock()
        self.connected = False
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        for g in self.ctrl_groups: g.setEnabled(False)
        self.video_label.setText("Disconnected")
        self.diag_timer.stop()

    def update_diagnostics(self):
        self.sdk_mutex.lock()
        cam_temp = self.sdk.get_camera_temp()
        fpa_temp = self.sdk.get_fpa_temp()
        self.sdk_mutex.unlock()

        ct = cam_temp if cam_temp is not None else 0.0
        ft = fpa_temp if fpa_temp is not None else 0.0
        self.statusBar().showMessage(f"FPS: {self.video_cb_count} | Temp Hz: {self.temp_cb_count} | Cam: {ct:.1f} C")
        self.lbl_fpa_temp.setText(f"{ft:.1f} °C")

        self.video_cb_count = 0
        self.temp_cb_count = 0

    def display_video(self, frame):
        self.current_frame = frame
        img = frame
        fmt = QImage.Format_RGB888
        h, w = frame.shape[:2]

        if self.chk_view_raw.isChecked() and self.current_temp_frame is not None:
            # Optimized 16-bit to 8-bit normalization.
            # Using cv2.normalize is ~12x faster than manual NumPy arithmetic.
            # We handle the constant-value frame edge case to match original behavior.
            rmin, rmax = self.current_temp_frame.min(), self.current_temp_frame.max()
            if rmax > rmin:
                img = cv2.normalize(self.current_temp_frame, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
            else:
                img = np.full_like(self.current_temp_frame, 128, dtype=np.uint8)
            fmt = QImage.Format_Grayscale8
            h, w = img.shape

        bytes_per_line = w * (3 if fmt == QImage.Format_RGB888 else 1)
        qimg = QImage(img.data, w, h, bytes_per_line, fmt).copy()
        pixmap = QPixmap.fromImage(qimg)

        if self.roi_rect:
            painter = QPainter(pixmap)
            painter.setPen(QPen(Qt.green, 2))
            lw, lh = pixmap.width(), pixmap.height()
            sx, sy = lw / w, lh / h
            rx, ry, rw, rh = self.roi_rect
            painter.drawRect(int(rx*sx), int(ry*sy), int(rw*sx), int(rh*sy))
            painter.end()

        self.video_label.setPixmap(pixmap)

    def process_temp(self, temp_frame):
        self.current_temp_frame = temp_frame
        h, w = temp_frame.shape
        max_v = np.max(temp_frame)
        min_v = np.min(temp_frame)
        center_v = temp_frame[h//2, w//2]

        self.lbl_max_temp.setText(f"{max_v/100.0:.1f} °C")
        self.lbl_min_temp.setText(f"{min_v/100.0:.1f} °C")
        self.lbl_center_temp.setText(f"{center_v/100.0:.1f} °C")

        if self.roi_rect:
            rx, ry, rw, rh = self.roi_rect
            roi = temp_frame[max(0,ry):min(h,ry+rh), max(0,rx):min(w,rx+rw)]
            if roi.size > 0:
                self.lbl_roi_info.setText(f"<b>ROI Statistics:</b><br>Max: {np.max(roi)/100.0:.1f} °C<br>Min: {np.min(roi)/100.0:.1f} °C<br>Avg: {np.mean(roi)/100.0:.1f} °C")

    def save_raw_data(self):
        if self.current_temp_frame is not None:
            path, _ = QFileDialog.getSaveFileName(self, "Save Raw Data", "capture.npy", "NumPy (*.npy)")
            if path:
                np.save(path, self.current_temp_frame)
                self.statusBar().showMessage(f"Saved to {path}", 3000)

    def screenshot(self):
        if self.current_frame is not None:
            path, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", "screenshot.png", "Images (*.png)")
            if path: cv2.imwrite(path, cv2.cvtColor(self.current_frame, cv2.COLOR_RGB2BGR))

    def do_nuc(self):
        if self.sdk:
            logging.info("Applying NUC...")
            self.sdk_mutex.lock()
            res = self.sdk.shutter_correction(self.core_type, 1)
            self.sdk_mutex.unlock()
            logging.info(f"NUC Result: {res}")

    def change_palette(self, index):
        if self.sdk:
            self.sdk_mutex.lock()
            self.sdk.set_color_plate(self.core_type, index)
            self.sdk_mutex.unlock()

    def update_env_params(self):
        if self.sdk and self.connected:
            e = int(self.sp_emiss.value() * 10000)
            a = int(self.sp_air_temp.value() * 10000)
            r = int(self.sp_reflect_temp.value() * 10000)
            h = int(self.sp_humidity.value() * 10000)
            d = int(self.sp_distance.value() * 10000)

            self.sdk_mutex.lock()
            self.sdk.set_envir_param(e, a, r, h, d)
            self.sdk_mutex.unlock()

    def toggle_wtr(self, checked):
        if self.sdk and self.connected:
            self.sdk_mutex.lock()
            self.sdk.set_wtr_status(int(checked))
            self.sdk_mutex.unlock()

    def update_wtr_thresholds(self):
        if self.sdk and self.connected:
            low = self.sp_wtr_low.value() * 10000
            high = self.sp_wtr_high.value() * 10000
            self.sdk_mutex.lock()
            self.sdk.set_wtr_low_threshold(low)
            self.sdk.set_wtr_high_threshold(high)
            self.sdk_mutex.unlock()

    def change_temp_unit(self, index):
        if self.sdk and self.connected:
            self.sdk_mutex.lock()
            self.sdk.set_temp_unit(index)
            self.sdk_mutex.unlock()

    def clear_roi(self):
        self.roi_rect = None
        self.lbl_roi_info.setText("Draw rectangle on video to measure.")

    def get_click_pos(self, event):
        if not self.video_label.pixmap(): return None
        lsize, psize = self.video_label.size(), self.video_label.pixmap().size()
        ox, oy = (lsize.width()-psize.width())/2, (lsize.height()-psize.height())/2
        cx, cy = event.pos().x() - ox, event.pos().y() - oy
        if 0 <= cx <= psize.width() and 0 <= cy <= psize.height():
            return int(cx * self.width / psize.width()), int(cy * self.height / psize.height())
        return None

    def mouse_press(self, event):
        pos = self.get_click_pos(event)
        if pos:
            self.drawing, self.roi_start = True, pos
            self.roi_rect = None

    def mouse_move(self, event):
        if self.drawing:
            pos = self.get_click_pos(event)
            if pos:
                x, y = min(self.roi_start[0], pos[0]), min(self.roi_start[1], pos[1])
                w, h = abs(self.roi_start[0]-pos[0]), abs(self.roi_start[1]-pos[1])
                self.roi_rect = (x, y, w, h)

    def mouse_release(self, event):
        self.drawing = False

    def closeEvent(self, event):
        self.disconnect_device()
        self.sdk_mutex.lock()
        if self.sdk: self.sdk.release_sdk()
        self.sdk_mutex.unlock()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CameraControlApp()
    window.show()
    sys.exit(app.exec_())

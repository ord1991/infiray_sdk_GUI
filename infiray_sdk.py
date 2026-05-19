import ctypes
from ctypes import *
import os
import sys

# Define constants
MAX_PATH = 260
MAX_DEVICE_NUM = 50


# Data structures
class DeviceInfo(Structure):
    _fields_ = [
        ("id", c_int),
        ("cName", c_char * MAX_PATH)
    ]


class ComName(Structure):
    _fields_ = [
        ("cComPort", c_char * MAX_PATH)
    ]


class DeviceLst(Structure):
    _fields_ = [
        ("iComCount", c_int),
        ("iNumber", c_int),
        ("DevInfo", DeviceInfo * MAX_DEVICE_NUM),
        ("ComNameInfo", ComName * MAX_DEVICE_NUM)
    ]


class envir_param(Structure):
    _fields_ = [
        ("emissivity", c_int),
        ("airTemp", c_int),
        ("reflectTemp", c_int),
        ("humidity", c_int),
        ("distance", c_int)
    ]


# Callback types
# Using WINFUNCTYPE (__stdcall) on Windows to match USBSDK convention
if sys.platform == 'win32':
    VideoCallBack = WINFUNCTYPE(None, POINTER(c_ubyte), c_int, c_int, c_void_p)
    TempCallBack = WINFUNCTYPE(None, POINTER(c_ubyte), c_int, c_int, c_void_p)
else:
    VideoCallBack = CFUNCTYPE(None, POINTER(c_ubyte), c_int, c_int, c_void_p)
    TempCallBack = CFUNCTYPE(None, POINTER(c_ubyte), c_int, c_int, c_void_p)


class InfiRaySDK:
    def __init__(self, dll_path):
        # Change directory to load dependencies correctly
        self.lib_dir = os.path.dirname(os.path.abspath(dll_path))
        self.original_cwd = os.getcwd()
        os.chdir(self.lib_dir)

        if sys.platform == 'win32' and sys.version_info >= (3, 8):
            try:
                os.add_dll_directory(self.lib_dir)
            except AttributeError:
                pass

        try:
            # Using WinDLL for __stdcall convention on Windows
            if sys.platform == 'win32':
                if sys.version_info >= (3, 8):
                    self.dll = ctypes.WinDLL(dll_path, winmode=0)
                else:
                    self.dll = ctypes.WinDLL(dll_path)
            else:
                self.dll = ctypes.CDLL(dll_path)
        except Exception as e:
            os.chdir(self.original_cwd)
            raise e

        os.chdir(self.original_cwd)

        self._setup_functions()
        self.handle = None

        # Keep references to callbacks to prevent GC
        self.c_video_callback = None
        self.c_temp_callback = None

    def _setup_functions(self):
        self.dll.sdk_create.restype = c_void_p
        self.dll.sdk_create.argtypes = []

        self.dll.sdk_loginDevice.restype = c_int
        self.dll.sdk_loginDevice.argtypes = [c_void_p, c_void_p]

        self.dll.ReleaseSDK.restype = None
        self.dll.ReleaseSDK.argtypes = [c_void_p]

        self.dll.SearchDevice.restype = c_int
        self.dll.SearchDevice.argtypes = [c_void_p, POINTER(DeviceLst)]

        self.dll.OpenDevice.restype = c_bool
        self.dll.OpenDevice.argtypes = [c_void_p, c_int, c_int]

        self.dll.CloseDevice.restype = None
        self.dll.CloseDevice.argtypes = [c_void_p]

        self.VideoCallBackType = VideoCallBack
        self.TempCallBackType = TempCallBack

        # SetVideoCallBack and SetTempCallBack are __stdcall, which WinDLL handles automatically
        self.dll.SetVideoCallBack.restype = None
        self.dll.SetVideoCallBack.argtypes = [c_void_p, self.VideoCallBackType, c_void_p]

        self.dll.SetTempCallBack.restype = None
        self.dll.SetTempCallBack.argtypes = [c_void_p, self.TempCallBackType, c_void_p]

        self.dll.sdk_shutter_correction.restype = c_int
        self.dll.sdk_shutter_correction.argtypes = [c_void_p, c_int, c_int]

        self.dll.sdk_set_color_plate.restype = c_int
        self.dll.sdk_set_color_plate.argtypes = [c_void_p, c_int, c_int]

        self.dll.sdk_get_color_plate.restype = c_int
        self.dll.sdk_get_color_plate.argtypes = [c_void_p, c_int, POINTER(c_int)]

        self.dll.sdk_get_camera_temp.restype = c_int
        self.dll.sdk_get_camera_temp.argtypes = [c_void_p, POINTER(c_float)]

        self.dll.sdk_get_FPA_temp.restype = c_int
        self.dll.sdk_get_FPA_temp.argtypes = [c_void_p, POINTER(c_float)]

        self.dll.CoreType.restype = c_int
        self.dll.CoreType.argtypes = [c_void_p]

        self.dll.TempMeasureType.restype = c_int
        self.dll.TempMeasureType.argtypes = [c_void_p]

        self.dll.sdk_get_SN_PN.restype = c_int
        self.dll.sdk_get_SN_PN.argtypes = [c_void_p, c_char_p, POINTER(c_int), c_char_p, POINTER(c_int)]

        self.dll.sdk_read_temp_unit.restype = c_int
        self.dll.sdk_read_temp_unit.argtypes = [c_void_p, POINTER(c_ubyte)]

        self.dll.sdk_set_temp_unit.restype = c_int
        self.dll.sdk_set_temp_unit.argtypes = [c_void_p, c_ubyte]

        self.dll.sdk_get_width.restype = c_int
        self.dll.sdk_get_width.argtypes = [c_void_p, POINTER(c_int)]

        self.dll.sdk_get_height.restype = c_int
        self.dll.sdk_get_height.argtypes = [c_void_p, POINTER(c_int)]

        self.dll.sdk_set_envir_param.restype = c_int
        self.dll.sdk_set_envir_param.argtypes = [c_void_p, envir_param]

        self.dll.sdk_get_envir_param.restype = c_int
        self.dll.sdk_get_envir_param.argtypes = [c_void_p, POINTER(envir_param)]

        self.dll.sdk_envir_effect.restype = c_int
        self.dll.sdk_envir_effect.argtypes = [c_void_p]

        self.dll.sdk_get_wtr_status.restype = c_int
        self.dll.sdk_get_wtr_status.argtypes = [c_void_p, POINTER(c_int)]

        self.dll.sdk_set_wtr_status.restype = c_int
        self.dll.sdk_set_wtr_status.argtypes = [c_void_p, c_int]

        self.dll.sdk_set_wtr_low_threshold.restype = c_int
        self.dll.sdk_set_wtr_low_threshold.argtypes = [c_void_p, c_int]

        self.dll.sdk_get_wtr_low_threshold.restype = c_int
        self.dll.sdk_get_wtr_low_threshold.argtypes = [c_void_p, POINTER(c_int)]

        self.dll.sdk_set_wtr_high_threshold.restype = c_int
        self.dll.sdk_set_wtr_high_threshold.argtypes = [c_void_p, c_int]

        self.dll.sdk_get_wtr_high_threshold.restype = c_int
        self.dll.sdk_get_wtr_high_threshold.argtypes = [c_void_p, POINTER(c_int)]

        self.dll.SetReflect.restype = c_int
        self.dll.SetReflect.argtypes = [c_void_p, c_int]

        self.dll.SetAirTemp.restype = c_int
        self.dll.SetAirTemp.argtypes = [c_void_p, c_int]

        self.dll.SetHumidity.restype = c_int
        self.dll.SetHumidity.argtypes = [c_void_p, c_int]

        self.dll.SetEmiss.restype = c_int
        self.dll.SetEmiss.argtypes = [c_void_p, c_int]

        self.dll.SetDistance.restype = c_int
        self.dll.SetDistance.argtypes = [c_void_p, c_int]

        self.dll.GetReflect.restype = c_int
        self.dll.GetReflect.argtypes = [c_void_p, POINTER(c_int)]

        self.dll.GetAirTemp.restype = c_int
        self.dll.GetAirTemp.argtypes = [c_void_p, POINTER(c_int)]

        self.dll.GetHumidity.restype = c_int
        self.dll.GetHumidity.argtypes = [c_void_p, POINTER(c_int)]

        self.dll.GetEmiss.restype = c_int
        self.dll.GetEmiss.argtypes = [c_void_p, POINTER(c_int)]

        self.dll.GetDistance.restype = c_int
        self.dll.GetDistance.argtypes = [c_void_p, POINTER(c_int)]

        self.dll.sdk_get_temp_coefficient.restype = c_int
        self.dll.sdk_get_temp_coefficient.argtypes = [c_void_p, c_int, POINTER(c_short), POINTER(c_short)]

        self.dll.sdk_edge_detect.restype = c_int
        self.dll.sdk_edge_detect.argtypes = [c_void_p, POINTER(c_ubyte), POINTER(c_ubyte), c_int, c_int, c_int]

        self.dll.sdk_edge_enhace.restype = c_int
        self.dll.sdk_edge_enhace.argtypes = [c_void_p, POINTER(c_ubyte), POINTER(c_ubyte), c_int, c_int, c_int]

    def create(self):
        self.handle = self.dll.sdk_create()
        return self.handle

    def login_device(self, hwnd=None):
        hwnd_ptr = c_void_p(hwnd) if hwnd else None
        return self.dll.sdk_loginDevice(self.handle, hwnd_ptr)

    def search_device(self):
        dev_list = DeviceLst()
        self.dll.SearchDevice(self.handle, byref(dev_list))
        return dev_list

    def open_device(self, iGetCurSel, portIndx):
        return self.dll.OpenDevice(self.handle, iGetCurSel, portIndx)

    def close_device(self):
        self.dll.CloseDevice(self.handle)

    def release_sdk(self):
        self.dll.ReleaseSDK(self.handle)
        self.handle = None

    def set_video_callback(self, py_callback):
        self.c_video_callback = self.VideoCallBackType(py_callback)
        self.dll.SetVideoCallBack(self.handle, self.c_video_callback, None)

    def set_temp_callback(self, py_callback):
        self.c_temp_callback = self.TempCallBackType(py_callback)
        self.dll.SetTempCallBack(self.handle, self.c_temp_callback, None)

    def get_width(self):
        val = c_int()
        self.dll.sdk_get_width(self.handle, byref(val))
        return val.value

    def get_height(self):
        val = c_int()
        self.dll.sdk_get_height(self.handle, byref(val))
        return val.value

    def get_camera_temp(self):
        val = c_float()
        ret = self.dll.sdk_get_camera_temp(self.handle, byref(val))
        return val.value if ret == 0 else None

    def get_fpa_temp(self):
        val = c_float()
        ret = self.dll.sdk_get_FPA_temp(self.handle, byref(val))
        return val.value if ret == 0 else None

    def get_core_type(self):
        return self.dll.CoreType(self.handle)

    def get_temp_measure_type(self):
        return self.dll.TempMeasureType(self.handle)

    def get_sn_pn(self):
        sn = create_string_buffer(MAX_PATH)
        pn = create_string_buffer(MAX_PATH)
        sn_len = c_int(MAX_PATH)
        pn_len = c_int(MAX_PATH)
        ret = self.dll.sdk_get_SN_PN(self.handle, sn, byref(sn_len), pn, byref(pn_len))
        if ret == 0:
            return sn.value.decode('utf-8', 'ignore'), pn.value.decode('utf-8', 'ignore')
        return "", ""

    def get_temp_unit(self):
        unit = c_ubyte()
        ret = self.dll.sdk_read_temp_unit(self.handle, byref(unit))
        return unit.value if ret == 0 else None

    def set_temp_unit(self, unit):
        return self.dll.sdk_set_temp_unit(self.handle, c_ubyte(unit)) == 0

    def shutter_correction(self, core_type=2, type=1):
        return self.dll.sdk_shutter_correction(self.handle, core_type, type)

    def set_color_plate(self, core_type, color_plate):
        return self.dll.sdk_set_color_plate(self.handle, core_type, color_plate)

    def get_color_plate(self, core_type):
        color_plate = c_int()
        ret = self.dll.sdk_get_color_plate(self.handle, core_type, byref(color_plate))
        return color_plate.value if ret == 0 else None

    def get_env_param(self):
        params = envir_param()
        ret = self.dll.sdk_get_envir_param(self.handle, byref(params))
        return params if ret == 0 else None

    def set_envir_param(self, emissivity, airTemp, reflectTemp, humidity, distance):
        params = envir_param(emissivity, airTemp, reflectTemp, humidity, distance)
        ret1 = self.dll.sdk_set_envir_param(self.handle, params)
        ret2 = self.dll.sdk_envir_effect(self.handle)
        return ret1 == 0 and ret2 == 0

    def get_wtr_status(self):
        val = c_int()
        ret = self.dll.sdk_get_wtr_status(self.handle, byref(val))
        return val.value if ret == 0 else None

    def set_wtr_status(self, status):
        return self.dll.sdk_set_wtr_status(self.handle, c_int(status)) == 0

    def set_wtr_low_threshold(self, threshold):
        return self.dll.sdk_set_wtr_low_threshold(self.handle, c_int(threshold)) == 0

    def get_wtr_low_threshold(self):
        val = c_int()
        ret = self.dll.sdk_get_wtr_low_threshold(self.handle, byref(val))
        return val.value if ret == 0 else None

    def set_wtr_high_threshold(self, threshold):
        return self.dll.sdk_set_wtr_high_threshold(self.handle, c_int(threshold)) == 0

    def get_wtr_high_threshold(self):
        val = c_int()
        ret = self.dll.sdk_get_wtr_high_threshold(self.handle, byref(val))
        return val.value if ret == 0 else None

    def set_reflect(self, value):
        return self.dll.SetReflect(self.handle, c_int(value)) == 0

    def set_air_temp(self, value):
        return self.dll.SetAirTemp(self.handle, c_int(value)) == 0

    def set_humidity(self, value):
        return self.dll.SetHumidity(self.handle, c_int(value)) == 0

    def set_emiss(self, value):
        return self.dll.SetEmiss(self.handle, c_int(value)) == 0

    def set_distance(self, value):
        return self.dll.SetDistance(self.handle, c_int(value)) == 0

    def get_reflect(self):
        val = c_int()
        ret = self.dll.GetReflect(self.handle, byref(val))
        return val.value if ret == 0 else None

    def get_air_temp(self):
        val = c_int()
        ret = self.dll.GetAirTemp(self.handle, byref(val))
        return val.value if ret == 0 else None

    def get_humidity(self):
        val = c_int()
        ret = self.dll.GetHumidity(self.handle, byref(val))
        return val.value if ret == 0 else None

    def get_emiss(self):
        val = c_int()
        ret = self.dll.GetEmiss(self.handle, byref(val))
        return val.value if ret == 0 else None

    def get_distance(self):
        val = c_int()
        ret = self.dll.GetDistance(self.handle, byref(val))
        return val.value if ret == 0 else None

    def get_temp_coefficient(self, gain):
        p1 = c_short()
        p2 = c_short()
        ret = self.dll.sdk_get_temp_coefficient(self.handle, c_int(gain), byref(p1), byref(p2))
        return (p1.value, p2.value) if ret == 0 else None

    def edge_detect(self, src_ptr, dst_ptr, width, height, level):
        return self.dll.sdk_edge_detect(self.handle, src_ptr, dst_ptr, width, height, level)

    def edge_enhance(self, src_ptr, dst_ptr, width, height, level):
        return self.dll.sdk_edge_enhace(self.handle, src_ptr, dst_ptr, width, height, level)

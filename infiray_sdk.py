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
VideoCallBack = CFUNCTYPE(None, POINTER(c_ubyte), c_int, c_int, c_void_p)
TempCallBack = CFUNCTYPE(None, POINTER(c_ubyte), c_int, c_int, c_void_p)


class InfiRaySDK:
    def __init__(self, dll_path):
        # Change directory to load dependencies like outPaletteFTII.dat correctly
        self.lib_dir = os.path.dirname(os.path.abspath(dll_path))
        self.original_cwd = os.getcwd()
        os.chdir(self.lib_dir)

        # For Python 3.8+ on Windows, we need to explicitly add the DLL directory
        # so its dependencies are found.
        if sys.platform == 'win32' and sys.version_info >= (3, 8):
            try:
                os.add_dll_directory(self.lib_dir)
            except AttributeError:
                pass

        try:
            # We can also pass the absolute path directly. Using absolute path + winmode for python 3.8+
            if sys.version_info >= (3, 8) and sys.platform == 'win32':
                self.dll = ctypes.CDLL(dll_path, winmode=0)
            else:
                self.dll = ctypes.CDLL(dll_path)
        except Exception as e:
            os.chdir(self.original_cwd)
            raise e

        os.chdir(self.original_cwd)

        self._setup_functions()
        self.handle = None

    def _setup_functions(self):
        # USBSDK_API IRNETHANDLE sdk_create();
        self.dll.sdk_create.restype = c_void_p
        self.dll.sdk_create.argtypes = []

        # USBSDK_API int sdk_loginDevice(IRNETHANDLE hHandle, HWND hWnd);
        self.dll.sdk_loginDevice.restype = c_int
        self.dll.sdk_loginDevice.argtypes = [c_void_p, c_void_p]

        # USBSDK_API void ReleaseSDK(IRNETHANDLE p);
        self.dll.ReleaseSDK.restype = None
        self.dll.ReleaseSDK.argtypes = [c_void_p]

        # USBSDK_API int SearchDevice(IRNETHANDLE p, DeviceLst &devList);
        self.dll.SearchDevice.restype = c_int
        self.dll.SearchDevice.argtypes = [c_void_p, POINTER(DeviceLst)]

        # USBSDK_API bool OpenDevice(IRNETHANDLE p, int iGetCurSel, int portIndx);
        self.dll.OpenDevice.restype = c_bool
        self.dll.OpenDevice.argtypes = [c_void_p, c_int, c_int]

        # USBSDK_API void CloseDevice(IRNETHANDLE p);
        self.dll.CloseDevice.restype = None
        self.dll.CloseDevice.argtypes = [c_void_p]

        # USBSDK_API void __stdcall SetVideoCallBack(IRNETHANDLE p, VideoCallBack pVideoCallBack, void *pContext);
        # Typedef in header: typedef void(*VideoCallBack)(unsigned char *pBuffer, int iWidth, int iHeight, void *pContext);
        # This typedef doesn't specify __stdcall, so the callback itself is __cdecl.
        self.VideoCallBackType = CFUNCTYPE(None, POINTER(c_ubyte), c_int, c_int, c_void_p)
        self.TempCallBackType = CFUNCTYPE(None, POINTER(c_ubyte), c_int, c_int, c_void_p)

        if sys.platform == 'win32':
            # The registration functions themselves are marked __stdcall in the header.
            self.SetVideoCallBack = WINFUNCTYPE(None, c_void_p, self.VideoCallBackType, c_void_p)(("SetVideoCallBack", self.dll))
            self.SetTempCallBack = WINFUNCTYPE(None, c_void_p, self.TempCallBackType, c_void_p)(("SetTempCallBack", self.dll))
        else:
            self.SetVideoCallBack = self.dll.SetVideoCallBack
            self.SetVideoCallBack.restype = None
            self.SetVideoCallBack.argtypes = [c_void_p, self.VideoCallBackType, c_void_p]

            self.SetTempCallBack = self.dll.SetTempCallBack
            self.SetTempCallBack.restype = None
            self.SetTempCallBack.argtypes = [c_void_p, self.TempCallBackType, c_void_p]

        # USBSDK_API int sdk_shutter_correction(IRNETHANDLE p, int iCoreType, int type);
        self.dll.sdk_shutter_correction.restype = c_int
        self.dll.sdk_shutter_correction.argtypes = [c_void_p, c_int, c_int]

        # USBSDK_API int sdk_set_color_plate(IRNETHANDLE p, int iType, int color_plate);
        self.dll.sdk_set_color_plate.restype = c_int
        self.dll.sdk_set_color_plate.argtypes = [c_void_p, c_int, c_int]

        # USBSDK_API int sdk_get_color_plate(IRNETHANDLE p, int iType, int* color_plate);
        self.dll.sdk_get_color_plate.restype = c_int
        self.dll.sdk_get_color_plate.argtypes = [c_void_p, c_int, POINTER(c_int)]

        # USBSDK_API int sdk_get_camera_temp(IRNETHANDLE p, float *fTemp);
        self.dll.sdk_get_camera_temp.restype = c_int
        self.dll.sdk_get_camera_temp.argtypes = [c_void_p, POINTER(c_float)]

        # USBSDK_API int sdk_get_width(IRNETHANDLE p, int *iValue);
        self.dll.sdk_get_width.restype = c_int
        self.dll.sdk_get_width.argtypes = [c_void_p, POINTER(c_int)]

        # USBSDK_API int sdk_get_height(IRNETHANDLE p, int *iValue);
        self.dll.sdk_get_height.restype = c_int
        self.dll.sdk_get_height.argtypes = [c_void_p, POINTER(c_int)]

        # Environment params
        self.dll.sdk_set_envir_param.restype = c_int
        self.dll.sdk_set_envir_param.argtypes = [c_void_p, envir_param]

        self.dll.sdk_get_envir_param.restype = c_int
        self.dll.sdk_get_envir_param.argtypes = [c_void_p, POINTER(envir_param)]

        self.dll.sdk_envir_effect.restype = c_int
        self.dll.sdk_envir_effect.argtypes = [c_void_p]

    def create(self):
        self.handle = self.dll.sdk_create()
        return self.handle

    def login_device(self, hwnd=None):
        hwnd_ptr = c_void_p(hwnd) if hwnd else None
        return self.dll.sdk_loginDevice(self.handle, hwnd_ptr)

    def search_device(self):
        dev_list = DeviceLst()
        ret = self.dll.SearchDevice(self.handle, byref(dev_list))
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
        self.SetVideoCallBack(self.handle, self.c_video_callback, None)

    def set_temp_callback(self, py_callback):
        self.c_temp_callback = self.TempCallBackType(py_callback)
        self.SetTempCallBack(self.handle, self.c_temp_callback, None)

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

    def shutter_correction(self, core_type=2, type=1):
        return self.dll.sdk_shutter_correction(self.handle, core_type, type)

    def set_color_plate(self, core_type, color_plate):
        return self.dll.sdk_set_color_plate(self.handle, core_type, color_plate)

    def get_color_plate(self, core_type):
        color_plate = c_int()
        ret = self.dll.sdk_get_color_plate(self.handle, core_type, byref(color_plate))
        return color_plate.value if ret == 0 else None

    def get_envir_param(self):
        params = envir_param()
        ret = self.dll.sdk_get_envir_param(self.handle, byref(params))
        return params if ret == 0 else None

    def set_envir_param(self, emissivity, airTemp, reflectTemp, humidity, distance):
        params = envir_param(emissivity, airTemp, reflectTemp, humidity, distance)
        ret1 = self.dll.sdk_set_envir_param(self.handle, params)
        ret2 = self.dll.sdk_envir_effect(self.handle)
        return ret1 == 0 and ret2 == 0
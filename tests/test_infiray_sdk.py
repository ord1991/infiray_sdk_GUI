import unittest
from unittest.mock import MagicMock, patch
from infiray_sdk import InfiRaySDK

class TestInfiRaySDK(unittest.TestCase):
    @patch('infiray_sdk.ctypes.CDLL')
    @patch('infiray_sdk.os.chdir')
    @patch('infiray_sdk.os.getcwd')
    @patch('infiray_sdk.os.path.abspath')
    @patch('infiray_sdk.os.path.dirname')
    def test_create(self, mock_dirname, mock_abspath, mock_getcwd, mock_chdir, mock_cdll):
        # Setup mocks
        mock_abspath.return_value = '/fake/path/lib/USBSDK.dll'
        mock_dirname.return_value = '/fake/path/lib'
        mock_getcwd.return_value = '/fake/cwd'

        mock_dll = MagicMock()
        mock_cdll.return_value = mock_dll

        # Mock the return value of sdk_create
        fake_handle = 12345
        mock_dll.sdk_create.return_value = fake_handle

        # Instantiate SDK
        sdk = InfiRaySDK('lib/USBSDK.dll')

        # Call create
        handle = sdk.create()

        # Verify
        mock_dll.sdk_create.assert_called_once()
        self.assertEqual(handle, fake_handle)
        self.assertEqual(sdk.handle, fake_handle)

if __name__ == '__main__':
    unittest.main()

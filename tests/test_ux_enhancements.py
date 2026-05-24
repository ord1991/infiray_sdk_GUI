import unittest
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from main import CameraControlApp

# Create a global QApplication instance for testing
app = QApplication(sys.argv)

class TestUXEnhancements(unittest.TestCase):
    def setUp(self):
        self.window = CameraControlApp()

    def test_video_label_ux(self):
        # Verify that the cursor is set to CrossCursor
        self.assertEqual(self.window.video_label.cursor().shape(), Qt.CrossCursor)

        # Verify that the tooltip is correctly set
        expected_tooltip = "Click and drag to draw a Region of Interest (ROI) for temperature measurement."
        self.assertEqual(self.window.video_label.toolTip(), expected_tooltip)

if __name__ == '__main__':
    unittest.main()

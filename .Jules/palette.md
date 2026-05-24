## 2026-05-24 - Interactive Feedback for ROI Drawing
**Learning:** Users need visual cues to understand that a static-looking image feed is interactive. A crosshair cursor (`Qt.CrossCursor`) immediately signals that a selection/drawing action is possible, while a descriptive tooltip provides essential context without cluttering the UI.
**Action:** Always set appropriate interactive cursors and tooltips on custom-drawn or interactive QLabels/Canvases to improve feature discoverability.

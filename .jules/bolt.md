## 2025-05-15 - OpenCV Vectorized Normalization Speedup
**Learning:** Manual NumPy-based normalization of 16-bit thermal data to 8-bit grayscale using `((raw - rmin) / (rmax - rmin) * 255.0).astype(np.uint8)` is significantly slower than using `cv2.normalize`. The bottleneck is the multiple intermediate floating-point arrays created during the arithmetic.
**Action:** Always prefer `cv2.normalize(src, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)` for mapping wide-range thermal data to displayable grayscale. It provides ~12x speedup and handles the bit-depth conversion in a single pass.

import unittest

import cv2
import numpy as np

from model.plate_crop_enhance import DEFAULT_MAX_SCALE, analyze_crop, enhance_plate_crop


class PlateCropEnhanceTests(unittest.TestCase):
    def test_upscales_tiny_crop(self) -> None:
        tiny = np.zeros((8, 14, 3), dtype=np.uint8)
        tiny[:, :, :] = 128
        cv2.rectangle(tiny, (2, 2), (11, 5), (255, 255, 255), 1)
        result = enhance_plate_crop(tiny, min_width=200, min_height=50)
        h, w = result.image_bgr.shape[:2]
        self.assertGreaterEqual(w, 200)
        self.assertGreaterEqual(h, 50)
        self.assertGreater(result.scale_factor, 1.0)
        self.assertTrue(any("upscale" in m for m in result.methods))

    def test_scale_capped(self) -> None:
        tiny = np.zeros((4, 6, 3), dtype=np.uint8)
        result = enhance_plate_crop(
            tiny,
            min_width=2000,
            min_height=500,
            max_scale=DEFAULT_MAX_SCALE,
        )
        self.assertLessEqual(result.scale_factor, DEFAULT_MAX_SCALE + 0.01)

    def test_analyze_flags_low_resolution(self) -> None:
        img = np.zeros((10, 12, 3), dtype=np.uint8)
        analysis = analyze_crop(img)
        self.assertIn("very_low_resolution", analysis.issues)


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pc_app"))

from image_processing import process_frame  # noqa: E402


class ImageProcessingBaselineTest(unittest.TestCase):
    def test_baseline_returns_independent_copy(self):
        frame = np.arange(8 * 8 * 3, dtype=np.uint8).reshape((8, 8, 3))
        result = process_frame(frame)

        np.testing.assert_array_equal(result, frame)
        self.assertIsNot(result, frame)

    def test_none_is_preserved(self):
        self.assertIsNone(process_frame(None))


if __name__ == "__main__":
    unittest.main()

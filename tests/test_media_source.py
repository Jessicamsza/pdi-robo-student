import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pc_app"))

from media_source import MediaFileSource  # noqa: E402


class MediaFileSourceTest(unittest.TestCase):
    def test_image_source_returns_independent_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frame.png"
            expected = np.full((24, 32, 3), 120, dtype=np.uint8)
            self.assertTrue(cv2.imwrite(str(path), expected))

            source = MediaFileSource(path)
            first = source.read_frame()
            second = source.read_frame()

            np.testing.assert_array_equal(first, expected)
            np.testing.assert_array_equal(second, expected)
            self.assertIsNot(first, second)
            self.assertTrue(source.get_status()["opened"])
            source.release()

    def test_video_source_reads_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clip.avi"
            writer = cv2.VideoWriter(
                str(path),
                cv2.VideoWriter_fourcc(*"MJPG"),
                10.0,
                (32, 24),
            )
            self.assertTrue(writer.isOpened())
            for value in (30, 90, 150):
                writer.write(np.full((24, 32, 3), value, dtype=np.uint8))
            writer.release()

            source = MediaFileSource(path, loop=False)
            frame = source.read_frame()

            self.assertIsNotNone(frame)
            self.assertEqual(frame.shape, (24, 32, 3))
            source.release()

    def test_missing_source_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            MediaFileSource("/arquivo/que/nao/existe.mp4")


if __name__ == "__main__":
    unittest.main()

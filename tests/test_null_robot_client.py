import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pc_app"))

from null_robot_client import NullRobotClient  # noqa: E402


class NullRobotClientTest(unittest.TestCase):
    def test_commands_are_safe_noops(self):
        robot = NullRobotClient()

        self.assertTrue(robot.forward())
        self.assertTrue(robot.left())
        self.assertTrue(robot.stop())
        self.assertEqual(robot.get_status()["packets_sent"], 0)
        self.assertEqual(robot.get_status()["send_errors"], 0)


if __name__ == "__main__":
    unittest.main()

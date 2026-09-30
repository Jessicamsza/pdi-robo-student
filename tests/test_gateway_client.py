import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pc_app"))

from gateway_client import GatewayRobotClient  # noqa: E402


class GatewayClientPayloadTest(unittest.TestCase):
    def test_payload_without_token(self):
        client = object.__new__(GatewayRobotClient)
        client.session_token = ""
        client.angular_sign = -1

        payload = client._build_payload(230, 80, 120)
        self.assertEqual(payload, b"V:230,W:-80,F:120")

    def test_payload_with_token(self):
        client = object.__new__(GatewayRobotClient)
        client.session_token = "aula-01"
        client.angular_sign = 1

        payload = client._build_payload(230, -80, 0)
        self.assertEqual(payload, b"T:aula-01,V:230,W:-80,F:0")


if __name__ == "__main__":
    unittest.main()

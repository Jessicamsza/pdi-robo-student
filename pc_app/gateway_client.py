import logging
import socket
import threading
import time


logger = logging.getLogger(__name__)


class GatewayRobotClient:
    """envia ao gateway o último comando de movimento em taxa fixa."""

    def __init__(
        self,
        gateway_host,
        control_port=4211,
        session_token="",
        send_hz=20,
        packet_repeats=1,
        angular_sign=1,
        command_timeout_sec=0.8,
    ):
        self.address = (gateway_host, int(control_port))
        self.session_token = session_token
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.send_period = 1.0 / max(1, int(send_hz))
        self.packet_repeats = max(1, int(packet_repeats))
        self.angular_sign = -1 if int(angular_sign) < 0 else 1
        self.command_timeout_sec = max(0.1, float(command_timeout_sec))

        self.speed = 180
        self.flash = 0
        self.linear = 0
        self.angular = 0
        self.last_motion_update = time.monotonic()

        self.running = True
        self.lock = threading.Lock()
        self.packets_sent = 0
        self.send_errors = 0
        self.last_error = None
        self.failsafe_active = False
        self._last_error_log = 0.0

        self.thread = threading.Thread(
            target=self._send_loop,
            name="gateway-udp-sender",
            daemon=True,
        )
        self.thread.start()

        logger.info(
            "cliente do gateway iniciado em %s:%s, envio a %.1f hz",
            self.address[0],
            self.address[1],
            1.0 / self.send_period,
        )

    def _build_payload(self, linear, angular, flash):
        physical_angular = int(angular) * self.angular_sign
        fields = []

        if self.session_token:
            fields.append(f"T:{self.session_token}")

        fields.extend(
            [
                f"V:{int(linear)}",
                f"W:{physical_angular}",
                f"F:{int(flash)}",
            ]
        )
        return ",".join(fields).encode("utf-8")

    def _send_loop(self):
        while self.running:
            with self.lock:
                linear = self.linear
                angular = self.angular
                flash = self.flash
                age = time.monotonic() - self.last_motion_update

            failsafe = age > self.command_timeout_sec
            if failsafe:
                linear = 0
                angular = 0

            self.failsafe_active = failsafe
            payload = self._build_payload(linear, angular, flash)

            for _ in range(self.packet_repeats):
                try:
                    self.sock.sendto(payload, self.address)
                    self.packets_sent += 1
                except OSError as exc:
                    self.send_errors += 1
                    self.last_error = str(exc)
                    self._log_send_error(exc)

            time.sleep(self.send_period)

    def _log_send_error(self, exc):
        now = time.monotonic()
        if now - self._last_error_log < 2.0:
            return

        logger.warning("falha ao enviar pacote ao gateway: %s", exc)
        self._last_error_log = now

    def _set_motion(self, linear: int, angular: int) -> bool:
        with self.lock:
            self.linear = max(-255, min(255, int(linear)))
            self.angular = max(-255, min(255, int(angular)))
            self.last_motion_update = time.monotonic()

        return self.running

    def move(self, linear: int, angular: int) -> bool:
        return self._set_motion(linear, angular)

    def set_speed(self, speed: int) -> bool:
        with self.lock:
            self.speed = max(0, min(255, int(speed)))

        return self.running

    def set_flash(self, value: int) -> bool:
        with self.lock:
            self.flash = max(0, min(255, int(value)))

        return self.running

    def forward(self) -> bool:
        with self.lock:
            speed = self.speed
        return self._set_motion(speed, 0)

    def backward(self) -> bool:
        with self.lock:
            speed = self.speed
        return self._set_motion(-speed, 0)

    def left(self) -> bool:
        with self.lock:
            speed = self.speed
        return self._set_motion(0, -speed)

    def right(self) -> bool:
        with self.lock:
            speed = self.speed
        return self._set_motion(0, speed)

    def stop(self) -> bool:
        return self._set_motion(0, 0)

    def get_status(self):
        return {
            "running": self.running,
            "packets_sent": self.packets_sent,
            "send_errors": self.send_errors,
            "last_error": self.last_error,
            "failsafe_active": self.failsafe_active,
        }

    def close(self):
        if not self.running:
            return

        self.stop()
        time.sleep(0.05)
        self.running = False
        self.thread.join(timeout=1.0)
        self.sock.close()
        logger.info("cliente do gateway encerrado")

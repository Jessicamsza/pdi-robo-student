class NullRobotClient:
    """implementa a interface de controle sem enviar comandos a hardware."""

    def __init__(self):
        self.speed = 0
        self.flash = 0

    def set_speed(self, speed):
        self.speed = int(speed)
        return True

    def set_flash(self, value):
        self.flash = int(value)
        return True

    def move(self, linear, angular):
        return True

    def forward(self):
        return True

    def backward(self):
        return True

    def left(self):
        return True

    def right(self):
        return True

    def stop(self):
        return True

    def get_status(self):
        return {
            "running": True,
            "packets_sent": 0,
            "send_errors": 0,
            "last_error": None,
            "failsafe_active": False,
        }

    def close(self):
        return None

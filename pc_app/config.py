import os


APP_VERSION = "0.5.1"


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if not value:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


# modos disponíveis:
# - gateway: uso oficial da atividade, sem acesso direto ao robô;
# - robot: desenvolvimento com uma esp32-cam própria ou de bancada;
# - video: desenvolvimento somente com arquivo de imagem ou vídeo.
RUN_MODE = os.getenv("PDI_MODE", "gateway").strip().lower()
VALID_RUN_MODES = {"gateway", "robot", "video"}

# modo gateway: o estudante conhece somente a infraestrutura da atividade.
GATEWAY_HOST = os.getenv("PDI_GATEWAY_HOST", "127.0.0.1")
GATEWAY_STREAM_PORT = _int_env("PDI_GATEWAY_STREAM_PORT", 8090)
GATEWAY_CONTROL_PORT = _int_env("PDI_GATEWAY_CONTROL_PORT", 4211)
GATEWAY_STREAM_URL = os.getenv(
    "PDI_GATEWAY_STREAM_URL",
    f"http://{GATEWAY_HOST}:{GATEWAY_STREAM_PORT}/stream",
)
SESSION_TOKEN = os.getenv("PDI_SESSION_TOKEN", "").strip()

# modo robot: conexão direta usada somente para desenvolvimento.
ROBOT_IP = os.getenv("PDI_ROBOT_IP", "micromouse.local")
ROBOT_UDP_PORT = _int_env("PDI_ROBOT_UDP_PORT", 4210)
ROBOT_CAMERA_URL = os.getenv(
    "PDI_ROBOT_CAMERA_URL",
    f"http://{ROBOT_IP}:81/stream",
)

# modo video: aceita arquivo de vídeo ou imagem local.
MEDIA_SOURCE = os.getenv("PDI_MEDIA_SOURCE", "").strip()
MEDIA_LOOP = _bool_env("PDI_MEDIA_LOOP", True)

# envio contínuo de comandos e fail-safe local.
CONTROL_SEND_HZ = _int_env("PDI_CONTROL_SEND_HZ", 20)
CONTROL_PACKET_REPEATS = _int_env("PDI_CONTROL_PACKET_REPEATS", 1)
CONTROL_COMMAND_TIMEOUT_SEC = _float_env("PDI_CONTROL_COMMAND_TIMEOUT_SEC", 0.80)
CONTROL_ANGULAR_SIGN = -1 if _int_env("PDI_ANGULAR_SIGN", -1) < 0 else 1

# controle manual.
DEFAULT_SPEED = _int_env("PDI_DEFAULT_SPEED", 230)
MIN_SPEED = 80
MAX_SPEED = 255
SPEED_STEP = 10
FLASH_ON_VALUE = 120
FLASH_OFF_VALUE = 0

# console.
WINDOW_W = 1280
WINDOW_H = 800
FPS = _int_env("PDI_CONSOLE_FPS", 30)
LOG_LEVEL = os.getenv("PDI_LOG_LEVEL", "INFO").upper()

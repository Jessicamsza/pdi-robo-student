import logging
import time

import pygame

from camera_viewer import CameraViewer
from config import (
    APP_VERSION,
    CONTROL_ANGULAR_SIGN,
    CONTROL_COMMAND_TIMEOUT_SEC,
    CONTROL_PACKET_REPEATS,
    CONTROL_SEND_HZ,
    DEFAULT_SPEED,
    FLASH_OFF_VALUE,
    FLASH_ON_VALUE,
    FPS,
    GATEWAY_CONTROL_PORT,
    GATEWAY_HOST,
    GATEWAY_STREAM_URL,
    LOG_LEVEL,
    MAX_SPEED,
    MEDIA_LOOP,
    MEDIA_SOURCE,
    MIN_SPEED,
    ROBOT_CAMERA_URL,
    ROBOT_IP,
    ROBOT_UDP_PORT,
    RUN_MODE,
    SESSION_TOKEN,
    SPEED_STEP,
    VALID_RUN_MODES,
    WINDOW_H,
    WINDOW_W,
)
from gateway_client import GatewayRobotClient
from image_processing import process_frame
from media_source import MediaFileSource
from null_robot_client import NullRobotClient
from robot_client import RobotClient


logger = logging.getLogger(__name__)


MODE_LABELS = {
    "gateway": "gateway da atividade",
    "robot": "robô direto de desenvolvimento",
    "video": "arquivo local",
}


def configure_logging():
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def draw_text(screen, text, x, y, font, color=(235, 235, 235)):
    screen.blit(font.render(str(text), True, color), (x, y))


def get_manual_command(keys):
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        return "forward"
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        return "backward"
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        return "left"
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        return "right"
    return "stop"


def send_robot_command(robot, command):
    actions = {
        "forward": robot.forward,
        "backward": robot.backward,
        "left": robot.left,
        "right": robot.right,
        "stop": robot.stop,
    }
    return actions.get(command, robot.stop)()


def build_runtime():
    if RUN_MODE not in VALID_RUN_MODES:
        valid = ", ".join(sorted(VALID_RUN_MODES))
        raise ValueError(f"PDI_MODE inválido: {RUN_MODE}. use: {valid}")

    if RUN_MODE == "gateway":
        source = CameraViewer(GATEWAY_STREAM_URL)
        robot = GatewayRobotClient(
            gateway_host=GATEWAY_HOST,
            control_port=GATEWAY_CONTROL_PORT,
            session_token=SESSION_TOKEN,
            send_hz=CONTROL_SEND_HZ,
            packet_repeats=CONTROL_PACKET_REPEATS,
            angular_sign=CONTROL_ANGULAR_SIGN,
            command_timeout_sec=CONTROL_COMMAND_TIMEOUT_SEC,
        )
        source_description = GATEWAY_STREAM_URL
        control_description = f"{GATEWAY_HOST}:{GATEWAY_CONTROL_PORT}"
        control_enabled = True
        return source, robot, source_description, control_description, control_enabled

    if RUN_MODE == "robot":
        source = CameraViewer(ROBOT_CAMERA_URL)
        robot = RobotClient(
            robot_ip=ROBOT_IP,
            udp_port=ROBOT_UDP_PORT,
            send_hz=CONTROL_SEND_HZ,
            packet_repeats=CONTROL_PACKET_REPEATS,
            angular_sign=CONTROL_ANGULAR_SIGN,
            command_timeout_sec=CONTROL_COMMAND_TIMEOUT_SEC,
        )
        source_description = ROBOT_CAMERA_URL
        control_description = f"{ROBOT_IP}:{ROBOT_UDP_PORT}"
        control_enabled = True
        return source, robot, source_description, control_description, control_enabled

    if not MEDIA_SOURCE:
        raise ValueError(
            "PDI_MEDIA_SOURCE precisa apontar para uma imagem ou vídeo quando PDI_MODE=video"
        )

    source = MediaFileSource(MEDIA_SOURCE, loop=MEDIA_LOOP)
    robot = NullRobotClient()
    source_description = MEDIA_SOURCE
    control_description = "desativado"
    control_enabled = False
    return source, robot, source_description, control_description, control_enabled


def main():
    configure_logging()
    logger.info("iniciando pdi student console v%s", APP_VERSION)
    logger.info("modo: %s", RUN_MODE)

    source, robot, source_description, control_description, control_enabled = build_runtime()
    logger.info("fonte: %s", source_description)
    logger.info("controle: %s", control_description)

    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption(f"pdi student console v{APP_VERSION}")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("monospace", 24)
    small_font = pygame.font.SysFont("monospace", 16)
    tiny_font = pygame.font.SysFont("monospace", 14)

    speed = DEFAULT_SPEED
    flash_enabled = False
    running = True
    processing_error = None
    processing_ms = 0.0
    last_processing_log = 0.0

    robot.set_speed(speed)
    robot.set_flash(FLASH_OFF_VALUE)
    robot.stop()

    try:
        while running:
            clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    continue
                if event.type != pygame.KEYDOWN:
                    continue

                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    speed = min(MAX_SPEED, speed + SPEED_STEP)
                    robot.set_speed(speed)
                    logger.info("velocidade manual: %s", speed)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    speed = max(MIN_SPEED, speed - SPEED_STEP)
                    robot.set_speed(speed)
                    logger.info("velocidade manual: %s", speed)
                elif event.key == pygame.K_l and control_enabled:
                    flash_enabled = not flash_enabled
                    robot.set_flash(FLASH_ON_VALUE if flash_enabled else FLASH_OFF_VALUE)
                    logger.info("flash: %s", "on" if flash_enabled else "off")

            input_frame = source.read_frame()
            processed_frame = None
            processing_error = None

            if input_frame is not None:
                started_at = time.perf_counter()
                try:
                    processed_frame = process_frame(input_frame)
                    if processed_frame is None:
                        raise ValueError("process_frame retornou none")
                except Exception as exc:
                    processing_error = str(exc)
                    now = time.monotonic()
                    if now - last_processing_log >= 2.0:
                        logger.exception("falha no pipeline de processamento")
                        last_processing_log = now
                finally:
                    processing_ms = (time.perf_counter() - started_at) * 1000.0

            keys = pygame.key.get_pressed()
            command = get_manual_command(keys) if control_enabled else "stop"

            # quando existe robô, ausência de referência visual sempre força parada.
            if keys[pygame.K_SPACE] or processed_frame is None:
                command = "stop"

            send_robot_command(robot, command)

            robot_status = robot.get_status()
            source_status = source.get_status()

            screen.fill((18, 18, 18))
            draw_text(screen, f"pdi student console v{APP_VERSION}", 20, 20, font)
            draw_text(
                screen,
                f"modo: {MODE_LABELS[RUN_MODE]}",
                20,
                58,
                small_font,
                color=(120, 255, 120),
            )

            draw_text(screen, "fonte", 20, 100, small_font)
            draw_text(screen, source_description[:35], 20, 126, tiny_font)
            draw_text(
                screen,
                f"stream: {'ok' if source_status['opened'] else 'sem frame'}",
                20,
                148,
                tiny_font,
            )
            draw_text(screen, f"frames: {source_status['frames_received']}", 20, 170, tiny_font)
            draw_text(screen, f"reconexões: {source_status['reconnects']}", 20, 192, tiny_font)
            draw_text(screen, f"pipeline: {processing_ms:.1f} ms", 20, 214, tiny_font)

            draw_text(screen, "controle", 20, 258, small_font)
            draw_text(screen, control_description[:35], 20, 284, tiny_font)
            draw_text(screen, f"velocidade: {speed}", 20, 306, tiny_font)
            draw_text(screen, f"comando: {command}", 20, 328, tiny_font)
            draw_text(
                screen,
                f"flash: {'on' if flash_enabled else 'off'}" if control_enabled else "flash: n/a",
                20,
                350,
                tiny_font,
            )

            draw_text(screen, "comunicação", 20, 394, small_font)
            udp_color = (120, 255, 120) if robot_status["send_errors"] == 0 else (255, 180, 120)
            draw_text(screen, f"pacotes: {robot_status['packets_sent']}", 20, 420, tiny_font, udp_color)
            draw_text(screen, f"erros udp: {robot_status['send_errors']}", 20, 442, tiny_font, udp_color)
            draw_text(
                screen,
                f"fail-safe: {'ativo' if robot_status['failsafe_active'] else 'normal'}",
                20,
                464,
                tiny_font,
                (255, 180, 120) if robot_status["failsafe_active"] else (120, 255, 120),
            )

            draw_text(screen, "controles", 20, 518, small_font)
            if control_enabled:
                draw_text(screen, "wasd / setas: mover", 20, 544, tiny_font)
                draw_text(screen, "espaço: parar", 20, 566, tiny_font)
                draw_text(screen, "+ / -: velocidade", 20, 588, tiny_font)
                draw_text(screen, "l: flash", 20, 610, tiny_font)
            else:
                draw_text(screen, "modo de mídia: sem controle", 20, 544, tiny_font)
            draw_text(screen, "esc: sair", 20, 632, tiny_font)

            if processing_error:
                draw_text(screen, "erro no pipeline", 20, 684, small_font, color=(255, 120, 120))
                draw_text(screen, processing_error[:32], 20, 710, tiny_font, color=(255, 120, 120))

            if processed_frame is not None:
                surface = CameraViewer.frame_to_surface(processed_frame, target_size=(960, 720))
                if surface is not None:
                    screen.blit(surface, (300, 40))
                    draw_text(screen, "saída de pc_app/image_processing.py", 310, 766, tiny_font)
            elif processing_error:
                draw_text(screen, "pipeline de pdi indisponível", 500, 360, font, color=(255, 120, 120))
            else:
                draw_text(screen, "aguardando frame", 500, 360, font, color=(255, 210, 120))

            pygame.display.flip()
    finally:
        logger.info("encerrando aplicação")
        robot.stop()
        robot.set_flash(FLASH_OFF_VALUE)
        robot.close()
        source.release()
        pygame.quit()


if __name__ == "__main__":
    main()

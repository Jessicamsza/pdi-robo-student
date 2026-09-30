import logging
import re
import threading
import time

import cv2
import numpy as np
import pygame
import requests


logger = logging.getLogger(__name__)


class CameraViewer:
    """lê somente o stream entregue pelo gateway e mantém o frame mais recente."""

    CONNECT_TIMEOUT_SEC = 3.0
    READ_TIMEOUT_SEC = 1.5
    RECONNECT_DELAY_SEC = 0.10

    def __init__(self, source, max_frame_age_sec=3.0):
        if not isinstance(source, str) or not source.startswith("http"):
            raise ValueError("a fonte da câmera precisa ser uma url http")

        self.source = source
        self.max_frame_age_sec = max(0.5, float(max_frame_age_sec))

        self.latest_frame = None
        self.latest_frame_time = 0.0
        self.running = True
        self.lock = threading.Lock()

        self.frames_received = 0
        self.decode_errors = 0
        self.connection_errors = 0
        self.reconnects = 0
        self._last_connection_log = 0.0

        self.thread = threading.Thread(
            target=self._mjpeg_loop,
            name="gateway-mjpeg-reader",
            daemon=True,
        )
        self.thread.start()

        logger.info("abrindo stream do gateway: %s", self.source)

    def _mjpeg_loop(self):
        while self.running:
            try:
                self._read_mjpeg_stream()
            except requests.RequestException as exc:
                self._register_connection_error(exc)
            except Exception as exc:
                self._register_connection_error(exc)

            if self.running:
                time.sleep(self.RECONNECT_DELAY_SEC)

    def _read_mjpeg_stream(self):
        with requests.get(
            self.source,
            stream=True,
            timeout=(self.CONNECT_TIMEOUT_SEC, self.READ_TIMEOUT_SEC),
            headers={"User-Agent": "pdi-student-console"},
        ) as response:
            response.raise_for_status()
            buffer = b""

            for chunk in response.iter_content(chunk_size=4096):
                if not self.running:
                    return
                if not chunk:
                    continue

                buffer += chunk
                if len(buffer) > 3_000_000:
                    buffer = buffer[-500_000:]

                while True:
                    frame, buffer = self._extract_frame_from_buffer(buffer)
                    if frame is None:
                        break
                    self._store_frame(frame)

    def _extract_frame_from_buffer(self, buffer):
        header_end = buffer.find(b"\r\n\r\n")

        if header_end != -1:
            header = buffer[:header_end].decode(errors="ignore")
            content_length = self._parse_content_length(header)
            if content_length is not None:
                frame_start = header_end + 4
                frame_end = frame_start + content_length
                if len(buffer) < frame_end:
                    return None, buffer

                jpg = buffer[frame_start:frame_end]
                remaining = buffer[frame_end:]
                return self._decode_jpeg(jpg), remaining

        start = buffer.find(b"\xff\xd8")
        if start == -1:
            return None, buffer[-1024:]
        if start > 0:
            buffer = buffer[start:]

        end = buffer.find(b"\xff\xd9", 2)
        if end == -1:
            return None, buffer

        jpg = buffer[: end + 2]
        remaining = buffer[end + 2 :]
        return self._decode_jpeg(jpg), remaining

    @staticmethod
    def _parse_content_length(header):
        match = re.search(r"Content-Length:\s*(\d+)", header, re.IGNORECASE)
        if not match:
            return None

        try:
            return int(match.group(1))
        except ValueError:
            return None

    def _decode_jpeg(self, jpg):
        if len(jpg) < 100 or not jpg.startswith(b"\xff\xd8") or not jpg.endswith(b"\xff\xd9"):
            self.decode_errors += 1
            return None

        image = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            self.decode_errors += 1
        return image

    def _store_frame(self, frame):
        with self.lock:
            self.latest_frame = frame
            self.latest_frame_time = time.time()
            self.frames_received += 1

    def _register_connection_error(self, exc):
        self.connection_errors += 1
        self.reconnects += 1

        now = time.monotonic()
        if now - self._last_connection_log >= 2.0:
            logger.warning("stream do gateway caiu, tentando reconectar: %s", exc)
            self._last_connection_log = now

    def is_opened(self):
        with self.lock:
            if self.latest_frame is None:
                return False
            age = time.time() - self.latest_frame_time
        return age <= self.max_frame_age_sec

    def read_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return None
            if time.time() - self.latest_frame_time > self.max_frame_age_sec:
                return None
            return self.latest_frame.copy()

    @staticmethod
    def frame_to_surface(frame, target_size=None):
        if frame is None:
            return None

        array = np.asarray(frame)
        if array.size == 0:
            return None

        if array.dtype == np.bool_:
            array = array.astype(np.uint8) * 255
        elif np.issubdtype(array.dtype, np.floating):
            finite = np.nan_to_num(array, nan=0.0, posinf=255.0, neginf=0.0)
            if finite.min() >= 0.0 and finite.max() <= 1.0:
                finite = finite * 255.0
            array = np.clip(finite, 0, 255).astype(np.uint8)
        elif array.dtype != np.uint8:
            array = np.clip(array, 0, 255).astype(np.uint8)

        if array.ndim == 2:
            frame_rgb = cv2.cvtColor(array, cv2.COLOR_GRAY2RGB)
        elif array.ndim == 3 and array.shape[2] == 1:
            frame_rgb = cv2.cvtColor(array[:, :, 0], cv2.COLOR_GRAY2RGB)
        elif array.ndim == 3 and array.shape[2] == 3:
            frame_rgb = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
        elif array.ndim == 3 and array.shape[2] == 4:
            frame_rgb = cv2.cvtColor(array, cv2.COLOR_BGRA2RGB)
        else:
            raise ValueError(f"formato de imagem não suportado para exibição: {array.shape}")

        if target_size is not None:
            frame_rgb = cv2.resize(
                frame_rgb,
                target_size,
                interpolation=cv2.INTER_NEAREST,
            )

        frame_rgb = np.ascontiguousarray(frame_rgb)
        height, width = frame_rgb.shape[:2]
        return pygame.image.frombuffer(frame_rgb.tobytes(), (width, height), "RGB")

    def get_status(self):
        return {
            "frames_received": self.frames_received,
            "decode_errors": self.decode_errors,
            "connection_errors": self.connection_errors,
            "reconnects": self.reconnects,
            "opened": self.is_opened(),
        }

    def release(self):
        self.running = False
        self.thread.join(timeout=1.0)
        logger.info("câmera do gateway encerrada")

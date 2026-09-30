#include <Arduino.h>
#include "esp_camera.h"
#include "esp_http_server.h"
#include "img_converters.h"


#define PART_BOUNDARY "pdi-robot-stream"

static const char *STREAM_CONTENT_TYPE =
    "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char *STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char *STREAM_PART =
    "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static httpd_handle_t streamHttpd = NULL;


static esp_err_t streamHandler(httpd_req_t *req)
{
  esp_err_t result = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  if (result != ESP_OK) {
    return result;
  }

  httpd_resp_set_hdr(req, "Cache-Control", "no-store");

  while (true) {
    camera_fb_t *frame = esp_camera_fb_get();
    if (!frame) {
      Serial.println("falha ao capturar frame");
      return ESP_FAIL;
    }

    uint8_t *jpegBuffer = frame->buf;
    size_t jpegLength = frame->len;
    bool allocated = false;

    if (frame->format != PIXFORMAT_JPEG) {
      if (!frame2jpg(frame, 80, &jpegBuffer, &jpegLength)) {
        esp_camera_fb_return(frame);
        Serial.println("falha ao converter frame para jpeg");
        return ESP_FAIL;
      }
      allocated = true;
    }

    char header[96];
    size_t headerLength = snprintf(
        header,
        sizeof(header),
        STREAM_PART,
        static_cast<unsigned int>(jpegLength)
    );

    result = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
    if (result == ESP_OK) {
      result = httpd_resp_send_chunk(req, header, headerLength);
    }
    if (result == ESP_OK) {
      result = httpd_resp_send_chunk(
          req,
          reinterpret_cast<const char *>(jpegBuffer),
          jpegLength
      );
    }

    if (allocated) {
      free(jpegBuffer);
    }
    esp_camera_fb_return(frame);

    if (result != ESP_OK) {
      break;
    }
  }

  return result;
}


void startCameraServer()
{
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 81;

  httpd_uri_t streamUri = {
      .uri = "/stream",
      .method = HTTP_GET,
      .handler = streamHandler,
      .user_ctx = NULL,
  };

  Serial.printf("iniciando stream na porta %d\n", config.server_port);
  if (httpd_start(&streamHttpd, &config) == ESP_OK) {
    httpd_register_uri_handler(streamHttpd, &streamUri);
  } else {
    Serial.println("falha ao iniciar servidor de stream");
  }
}

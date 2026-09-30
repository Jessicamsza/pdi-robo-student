#include "esp_camera.h"
#include "esp_system.h"
#include <ESPmDNS.h>
#include <WiFi.h>

#include "wifi_secrets.h"


#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22


void startCameraServer();


static void connectToRouter()
{
  WiFi.mode(WIFI_MODE_NULL);
  WiFi.setHostname("micromouse");
  WiFi.mode(WIFI_STA);
  WiFi.persistent(false);
  WiFi.setSleep(false);
  WiFi.setTxPower(WIFI_POWER_19_5dBm);
  WiFi.setAutoReconnect(true);

  Serial.print("conectando ao wi-fi: ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const unsigned long timeoutMs = 20000;
  const unsigned long startedAt = millis();

  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");

    if (millis() - startedAt >= timeoutMs) {
      Serial.println();
      Serial.println("falha ao conectar ao wi-fi; reiniciando...");
      delay(1000);
      ESP.restart();
    }
  }

  Serial.println();
  Serial.println("wi-fi conectado");
  Serial.print("ip: ");
  Serial.println(WiFi.localIP());

  if (MDNS.begin("micromouse")) {
    MDNS.addService("http", "tcp", 81);
    Serial.println("mdns: micromouse.local");
  } else {
    Serial.println("aviso: falha ao iniciar mdns");
  }
}


void CameraWebServer_init()
{
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 10000000;
  config.frame_size = FRAMESIZE_QVGA;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;
  config.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  config.jpeg_quality = 16;
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("falha ao iniciar câmera: 0x%x\n", err);
    return;
  }

  sensor_t *sensor = esp_camera_sensor_get();
  sensor->set_framesize(sensor, FRAMESIZE_QVGA);
  sensor->set_vflip(sensor, 1);
  sensor->set_hmirror(sensor, 1);

  connectToRouter();
  startCameraServer();
}

#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include "soc/rtc_cntl_reg.h"
#include "soc/soc.h"


#define CAMERA_MODEL_AI_THINKER

#define LED_PIN 4


void CameraWebServer_init();


WiFiUDP udp;

const int UDP_PORT = 4210;
const int MOTOR_PWM_FREQUENCY = 5000;
const int MOTOR_PWM_RESOLUTION = 8;
const int MOTOR_MIN_EFFECTIVE_PWM = 105;
const unsigned long UDP_TIMEOUT_MS = 1200;
const unsigned long WIFI_RECONNECT_INTERVAL_MS = 3000;

unsigned long lastUdpCommandTime = 0;
unsigned long lastWifiReconnectAttempt = 0;
bool wifiWasConnected = false;

int gpLb = 14;
int gpLf = 13;
int gpRb = 33;
int gpRf = 15;
int gpLed = LED_PIN;
int ENR = 2;
int ENL = 12;


void wheelAct(int speedRight, int speedLeft, int leftForward, int leftBackward,
              int rightForward, int rightBackward)
{
  ledcWrite(ENR, speedRight);
  ledcWrite(ENL, speedLeft);
  digitalWrite(gpLf, leftForward);
  digitalWrite(gpLb, leftBackward);
  digitalWrite(gpRf, rightForward);
  digitalWrite(gpRb, rightBackward);
}


void initMotors()
{
  pinMode(gpLb, OUTPUT);
  pinMode(gpLf, OUTPUT);
  pinMode(gpRb, OUTPUT);
  pinMode(gpRf, OUTPUT);
  pinMode(gpLed, OUTPUT);
  pinMode(ENR, OUTPUT);
  pinMode(ENL, OUTPUT);

  ledcAttach(ENR, MOTOR_PWM_FREQUENCY, MOTOR_PWM_RESOLUTION);
  ledcAttach(ENL, MOTOR_PWM_FREQUENCY, MOTOR_PWM_RESOLUTION);

  ledcWrite(ENR, 0);
  ledcWrite(ENL, 0);
  digitalWrite(gpLf, LOW);
  digitalWrite(gpLb, LOW);
  digitalWrite(gpRf, LOW);
  digitalWrite(gpRb, LOW);
}


void stopMotors()
{
  wheelAct(0, 0, LOW, LOW, LOW, LOW);
}


int applyMotorCompensation(int command)
{
  if (command == 0) {
    return 0;
  }

  int direction = command < 0 ? -1 : 1;
  int magnitude = constrain(abs(command), MOTOR_MIN_EFFECTIVE_PWM, 255);
  return direction * magnitude;
}


void driveDifferential(int linear, int angular)
{
  int left = constrain(linear - angular, -255, 255);
  int right = constrain(linear + angular, -255, 255);

  left = applyMotorCompensation(left);
  right = applyMotorCompensation(right);

  int leftForward = left > 0 ? HIGH : LOW;
  int leftBackward = left < 0 ? HIGH : LOW;
  int rightForward = right > 0 ? HIGH : LOW;
  int rightBackward = right < 0 ? HIGH : LOW;

  wheelAct(
      abs(right),
      abs(left),
      leftForward,
      leftBackward,
      rightForward,
      rightBackward
  );
}


bool parseUdpCommand(char *packet, int &linear, int &angular, int &flash)
{
  return sscanf(packet, "V:%d,W:%d,F:%d", &linear, &angular, &flash) == 3;
}


void handleUdpControl()
{
  int packetSize = udp.parsePacket();
  if (!packetSize) {
    return;
  }

  char packet[96];
  int length = udp.read(packet, sizeof(packet) - 1);
  if (length <= 0) {
    return;
  }
  packet[length] = '\0';

  int linear = 0;
  int angular = 0;
  int flash = 0;

  if (!parseUdpCommand(packet, linear, angular, flash)) {
    return;
  }

  linear = constrain(linear, -255, 255);
  angular = constrain(angular, -255, 255);
  flash = constrain(flash, 0, 255);

  driveDifferential(linear, angular);
  ledcWrite(gpLed, flash);
  lastUdpCommandTime = millis();
}


void handleWifiConnection()
{
  bool connected = WiFi.status() == WL_CONNECTED;

  if (!connected) {
    if (wifiWasConnected) {
      Serial.println("wi-fi desconectado");
    }

    stopMotors();

    if (millis() - lastWifiReconnectAttempt >= WIFI_RECONNECT_INTERVAL_MS) {
      lastWifiReconnectAttempt = millis();
      Serial.println("tentando reconectar ao wi-fi...");
      WiFi.reconnect();
    }

    wifiWasConnected = false;
    return;
  }

  if (!wifiWasConnected) {
    udp.stop();
    udp.begin(UDP_PORT);
    Serial.print("wi-fi reconectado; ip: ");
    Serial.println(WiFi.localIP());
  }

  wifiWasConnected = true;
}


void setup()
{
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  Serial.begin(115200);
  Serial.setDebugOutput(false);
  Serial.println();
  Serial.println("iniciando robô esp32-cam...");

  initMotors();
  stopMotors();
  CameraWebServer_init();

  ledcAttach(gpLed, 5000, 8);
  ledcWrite(gpLed, 0);

  udp.begin(UDP_PORT);
  Serial.print("controle udp na porta: ");
  Serial.println(UDP_PORT);

  stopMotors();
  lastUdpCommandTime = millis();
  wifiWasConnected = WiFi.status() == WL_CONNECTED;
}


void loop()
{
  handleWifiConnection();

  if (WiFi.status() != WL_CONNECTED) {
    delay(10);
    return;
  }

  handleUdpControl();

  if (millis() - lastUdpCommandTime > UDP_TIMEOUT_MS) {
    stopMotors();
  }
}

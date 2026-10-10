/*
  Coreless-64 Arduino serial I/O bridge, protocol v1.
  Dependency: ArduinoJson 6.x (Library Manager).
  Select the correct DEVICE_ID for the board and match the host baud rate.
  The host sends newline-delimited JSON commands; this sketch emits ack/event/error
  messages with monotonically increasing device-side sequence numbers.
*/
#include <ArduinoJson.h>

static const char DEVICE_ID[] = "arduino-1";
static const unsigned long SERIAL_BAUD = 115200;
static const size_t LINE_CAPACITY = 256;  // suitable for small-RAM boards
static char lineBuffer[LINE_CAPACITY];
static size_t lineLength = 0;
static bool lineOverflow = false;
static uint32_t deviceSequence = 0;
static int32_t lastHostSequence = -1;
static unsigned long lastAnalogSample = 0;

static void sendMessage(const char *kind, uint32_t sequence, JsonDocument &payload) {
  StaticJsonDocument<384> outgoing;
  outgoing["protocol"] = 1;
  outgoing["kind"] = kind;
  outgoing["device_id"] = DEVICE_ID;
  outgoing["sequence"] = sequence;
  outgoing["payload"].set(payload.as<JsonObjectConst>());
  serializeJson(outgoing, Serial);
  Serial.write('\n');
}

static void sendError(const char *message) {
  StaticJsonDocument<96> payload;
  payload["message"] = message;
  sendMessage("error", deviceSequence++, payload);
}

static void sendAck(int32_t requestSequence, const char *operation, int value = -1) {
  StaticJsonDocument<128> payload;
  payload["request_sequence"] = requestSequence;
  payload["op"] = operation;
  payload["ok"] = true;
  if (value >= 0) payload["value"] = value;
  sendMessage("ack", deviceSequence++, payload);
}

static bool integerField(JsonObjectConst payload, const char *key, int minValue, int maxValue, int &out) {
  JsonVariantConst v = payload[key];
  if (v.is<bool>() || !v.is<int>()) return false;
  out = v.as<int>();
  return out >= minValue && out <= maxValue;
}

static void processLine(const char *line) {
  StaticJsonDocument<256> incoming;
  DeserializationError error = deserializeJson(incoming, line);
  if (error || !incoming.is<JsonObject>()) {
    sendError("invalid JSON command");
    return;
  }
  JsonObjectConst msg = incoming.as<JsonObjectConst>();
  if (msg["protocol"] != 1 || !msg["protocol"].is<int>()) {
    sendError("unsupported protocol version");
    return;
  }
  if (msg["kind"] != "command" || msg["device_id"] != DEVICE_ID) {
    sendError("message kind or device identity mismatch");
    return;
  }
  if (!msg["sequence"].is<int32_t>()) {
    sendError("invalid command sequence");
    return;
  }
  int32_t requestSequence = msg["sequence"].as<int32_t>();
  if (requestSequence <= lastHostSequence) {
    sendError("command sequence is not increasing");
    return;
  }
  JsonObjectConst payload = msg["payload"].as<JsonObjectConst>();
  const char *op = payload["op"] | "";
  int pin = -1;
  if (!integerField(payload, "pin", 0, 255, pin)) {
    sendError("invalid pin");
    return;
  }

  if (strcmp(op, "pin_mode") == 0) {
    const char *mode = payload["value"] | "";
    if (strcmp(mode, "input") == 0) pinMode(pin, INPUT);
    else if (strcmp(mode, "input_pullup") == 0) pinMode(pin, INPUT_PULLUP);
    else if (strcmp(mode, "output") == 0) pinMode(pin, OUTPUT);
    else { sendError("invalid pin mode"); return; }
    lastHostSequence = requestSequence;
    sendAck(requestSequence, op);
  } else if (strcmp(op, "digital_write") == 0) {
    int value;
    if (!integerField(payload, "value", 0, 1, value)) { sendError("invalid digital value"); return; }
    digitalWrite(pin, value ? HIGH : LOW);
    lastHostSequence = requestSequence;
    sendAck(requestSequence, op);
  } else if (strcmp(op, "analog_write") == 0) {
    int value;
    if (!integerField(payload, "value", 0, 255, value)) { sendError("invalid analog value"); return; }
    analogWrite(pin, value);
    lastHostSequence = requestSequence;
    sendAck(requestSequence, op);
  } else if (strcmp(op, "digital_read") == 0) {
    int value = digitalRead(pin) == HIGH ? 1 : 0;
    lastHostSequence = requestSequence;
    sendAck(requestSequence, op, value);
  } else if (strcmp(op, "analog_read") == 0) {
    int value = analogRead(pin);
    lastHostSequence = requestSequence;
    sendAck(requestSequence, op, value);
  } else {
    sendError("unsupported operation");
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD);
}

void loop() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n') {
      if (lineOverflow) sendError("command line too long");
      else {
        if (lineLength > 0 && lineBuffer[lineLength - 1] == '\r') --lineLength;
        lineBuffer[lineLength] = '\0';
        processLine(lineBuffer);
      }
      lineLength = 0;
      lineOverflow = false;
    } else if (!lineOverflow) {
      if (lineLength + 1 < LINE_CAPACITY) lineBuffer[lineLength++] = c;
      else lineOverflow = true;
    }
  }

  // Demonstration sensor event: sample A0 once per second.
  // Remove or replace this block for application-specific sensor events.
  unsigned long now = millis();
  if (now - lastAnalogSample >= 1000) {
    lastAnalogSample = now;
    StaticJsonDocument<128> payload;
    payload["sensor"] = "analog";
    payload["pin"] = "A0";
    payload["value"] = analogRead(A0);
    sendMessage("event", deviceSequence++, payload);
  }
}

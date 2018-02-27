#include <Atlasbuggy.h>


Atlasbuggy robot("SlowArduino");

uint8_t array_len = 100;




void setup() {
    robot.begin();
}

void loop() {
    while (robot.available())
    {
        int status = robot.readSerial();
        if (status == 2) {  // start event

        }
        else if (status == 1) {  // stop event

        }
        if (status == 0) {  // user command
            String command = robot.getCommand();
            if (command.equals("on")) {
                robot.setLed(true);
            }
            else if (command.equals("off")) {
                robot.setLed(false);
            }
            else if (command.equals("toggle")) {
                robot.setLed(!robot.getLed());
            }
        }
    }

    if (!robot.isPaused())
    {
        Serial.print(millis());
        Serial.print(';');
        for (uint8_t index = 0; index < array_len; index++) {
            Serial.print(random(0x1000));
            if (index < array_len - 1)
                Serial.print(',');
        }
        Serial.print('\n');

        delay(5);
    }
}

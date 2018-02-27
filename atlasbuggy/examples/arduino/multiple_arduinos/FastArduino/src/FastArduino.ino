#include <Atlasbuggy.h>


Atlasbuggy robot("FastArduino");

int item1 = 0;
int item2 = 0;


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
        Serial.print('\t');
        Serial.print(item1);
        Serial.print('\t');
        Serial.print(item2);
        Serial.print('\n');

        item1++;
        item2 += 2;
        delay(10);
    }
}

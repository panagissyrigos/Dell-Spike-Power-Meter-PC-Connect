#include <Arduino.h>
#include <Wire.h>
#include <INA226.h>

INA226 INA(0x40); // Default I2C address

void setup() {
    Serial.begin(115200);
    Wire.begin(8, 9); // SDA=8, SCL=9 for ESP32-C3

    if (!INA.begin()) {
        Serial.println("Could not find INA226. Check wiring!");
        while (1);
    }

    // Configure for your shunt resistor (usually 0.1 ohm) 
    // and max expected current (e.g. 2 Amps)
    INA.setMaxCurrentShunt(2.0, 0.1); 
}

void loop() {
    float voltage = INA.getBusVoltage();
    float current = INA.getCurrent_mA();
    float power   = INA.getPower_mW();

    // Format: Voltage,Current,Power
    Serial.print(voltage, 3);
    Serial.print(",");
    Serial.print(current, 2);
    Serial.print(",");
    Serial.println(power, 2);

    delay(200); // 5Hz Update rate
}

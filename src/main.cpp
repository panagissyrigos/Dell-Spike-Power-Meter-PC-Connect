#include <Arduino.h>
#include <Wire.h>
#include <INA226.h>

INA226 INA(0x40);

// --- R002 Shunt = 0.002 Ohms ---
const float SHUNT_OHMS = 0.002; 

void setup() {
    Serial.begin(115200);
    delay(2000); 
    Wire.begin(8, 9); // ESP32-C3 Pins

    if (!INA.begin()) {
        while (1) { Serial.println("0,0,0,0"); delay(1000); }
    }

    // Set averaging to 16 samples to smooth out the R002 noise
    INA.setAverage(INA226_16_SAMPLES); 
    
    // We calibrate to a higher range since R002 is for high current
    INA.setMaxCurrentShunt(25.0, SHUNT_OHMS); 
}

void loop() {
    float voltage = INA.getBusVoltage();
    float shunt_mV = INA.getShuntVoltage_mV();

    // Manual Calculation
    // Current (A) = Volts / Resistance
    float current_A = (shunt_mV / 1000.0) / SHUNT_OHMS;
    
    // Power (W) = Volts * Amps
    float power_W = voltage * current_A;

    // Send to Python: V, I(Amps), P(Watts), Shunt_mV
    Serial.print(voltage, 3);
    Serial.print(",");
    Serial.print(current_A, 3); // Send Amps with 3 decimal places
    Serial.print(",");
    Serial.print(power_W, 3);   // Send Watts with 3 decimal places
    Serial.print(",");
    Serial.println(shunt_mV, 4);

    delay(250);
}

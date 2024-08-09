#include <EEPROM.h>
#include "GravityTDS.h"

// K-values for different usage modes
#define INDUSTRIAL_K_VALUE 0.9
#define AGRICULTURE_K_VALUE 0.7
#define HOUSEHOLD_K_VALUE 0.5

#define EEPROM_write(address, p) {int i = 0; byte *pp = (byte*)&(p);for(; i < sizeof(p); i++) EEPROM.write(address+i, pp[i]);}
#define EEPROM_read(address, p)  {int i = 0; byte *pp = (byte*)&(p);for(; i < sizeof(p); i++) pp[i]=EEPROM.read(address+i);}

GravityTDS::GravityTDS()
{
    this->pin = A0;
    this->temperature = 25.0;
    this->aref = 5.0;
    this->adcRange = 1024.0;
    this->kValueAddress = 8;
    this->kValue = 1.0;
    this->usageMode = 0; // Default usage mode
}

GravityTDS::~GravityTDS()
{
}

void GravityTDS::setPin(int pin)
{
    this->pin = pin;
}

void GravityTDS::setTemperature(float temp)
{
    this->temperature = temp;
}

void GravityTDS::setAref(float value)
{
    this->aref = value;
}

void GravityTDS::setAdcRange(float range)
{
    this->adcRange = range;
}

void GravityTDS::setKvalueAddress(int address)
{
    this->kValueAddress = address;
}

void GravityTDS::setUsageMode(int mode)
{
    this->usageMode = mode;
    updateKValue(); // Update k-value based on usage mode
}

void GravityTDS::begin()
{
    pinMode(this->pin, INPUT);
    readKValues();
}

float GravityTDS::getKvalue()
{
    return this->kValue;
}

void GravityTDS::update()
{
    this->analogValue = analogRead(this->pin);
    this->voltage = this->analogValue / this->adcRange * this->aref;
    this->ecValue = (133.42 * this->voltage * this->voltage * this->voltage - 255.86 * this->voltage * this->voltage + 857.39 * this->voltage) * this->kValue;
    this->ecValue25 = this->ecValue / (1.0 + 0.02 * (this->temperature - 25.0));  // Temperature compensation
    this->tdsValue = ecValue25 * TdsFactor;
    if (cmdSerialDataAvailable() > 0)
    {
        ecCalibration(cmdParse());  // If received serial command from the serial monitor, enter into the calibration mode
    }
}

float GravityTDS::getTdsValue()
{
    return tdsValue;
}

float GravityTDS::getEcValue()
{
    return ecValue25;
}

void GravityTDS::readKValues()
{
    EEPROM_read(this->kValueAddress, this->kValue);  
    if (EEPROM.read(this->kValueAddress) == 0xFF && EEPROM.read(this->kValueAddress + 1) == 0xFF && EEPROM.read(this->kValueAddress + 2) == 0xFF && EEPROM.read(this->kValueAddress + 3) == 0xFF)
    {
        this->kValue = 1.0;   // Default value: K = 1.0
        EEPROM_write(this->kValueAddress, this->kValue);
    }
}

void GravityTDS::updateKValue()
{
    switch (this->usageMode)
    {
        case 1: // Industrial mode
            this->kValue = INDUSTRIAL_K_VALUE;
            break;
        case 2: // Agriculture mode 
            this->kValue = AGRICULTURE_K_VALUE;
            break;
        case 3: // Household mode
            this->kValue = HOUSEHOLD_K_VALUE;
            break;
        default:
            this->kValue = HOUSEHOLD_K_VALUE; // Default to Household mode
            break;
    }
    EEPROM_write(this->kValueAddress, this->kValue);
}

boolean GravityTDS::cmdSerialDataAvailable()
{
    char cmdReceivedChar;
    static unsigned long cmdReceivedTimeOut = millis();
    while (Serial.available() > 0) 
    {   
        if (millis() - cmdReceivedTimeOut > 500U) 
        {
            cmdReceivedBufferIndex = 0;
            memset(cmdReceivedBuffer, 0, (ReceivedBufferLength + 1));
        }
        cmdReceivedTimeOut = millis();
        cmdReceivedChar = Serial.read();
        if (cmdReceivedChar == '\n' || cmdReceivedBufferIndex == ReceivedBufferLength)
        {
            cmdReceivedBufferIndex = 0;
            strupr(cmdReceivedBuffer);
            return true;
        }
        else
        {
            cmdReceivedBuffer[cmdReceivedBufferIndex] = cmdReceivedChar;
            cmdReceivedBufferIndex++;
        }
    }
    return false;
}

byte GravityTDS::cmdParse()
{
    byte modeIndex = 0;
    if (strstr(cmdReceivedBuffer, "ENTER") != NULL) 
        modeIndex = 1;
    else if (strstr(cmdReceivedBuffer, "EXIT") != NULL) 
        modeIndex = 3;
    else if (strstr(cmdReceivedBuffer, "CAL:") != NULL)   
        modeIndex = 2;
    return modeIndex;
}

void GravityTDS::ecCalibration(byte mode)
{
    char *cmdReceivedBufferPtr;
    static boolean ecCalibrationFinish = 0;
    static boolean enterCalibrationFlag = 0;
    float KValueTemp, rawECsolution;
    switch (mode)
    {
        case 0:
            if (enterCalibrationFlag)
                Serial.println(F("Command Error"));
            break;
        
        case 1:
            enterCalibrationFlag = 1;
            ecCalibrationFinish = 0;
            Serial.println();
            Serial.println(F(">>>Enter Calibration Mode<<<"));
            Serial.println(F(">>>Please put the probe into the standard buffer solution<<<"));
            Serial.println();
            break;
        
        case 2:
            cmdReceivedBufferPtr = strstr(cmdReceivedBuffer, "CAL:");
            cmdReceivedBufferPtr += strlen("CAL:");
            rawECsolution = strtod(cmdReceivedBufferPtr, NULL) / (float)(TdsFactor);
            rawECsolution = rawECsolution * (1.0 + 0.02 * (temperature - 25.0));
            if (enterCalibrationFlag)
            {
                KValueTemp = rawECsolution / (133.42 * voltage * voltage * voltage - 255.86 * voltage * voltage + 857.39 * voltage);  // Calibrate in the buffer solution
                if ((rawECsolution > 0) && (rawECsolution < 2000) && (KValueTemp >= 0.5) && (KValueTemp <= 0.9))
                {
                    Serial.print(F(">>>Calibration Finished<<<"));
                    Serial.print(F(">>>KValue: "));
                    Serial.print(KValueTemp, 2);
                    Serial.println();
                    kValue = KValueTemp;
                    EEPROM_write(kValueAddress, kValue);
                    enterCalibrationFlag = 0;
                    ecCalibrationFinish = 1;
                    Serial.println(F(">>>Exit Calibration Mode<<<"));
                    Serial.println();
                }
                else
                {
                    Serial.println(F(">>>Error: Please use standard buffer solution<<<"));
                }
            }
            else
            {
                Serial.println(F(">>>Error: Enter Calibration Mode<<<"));
            }
            break;
        
        case 3:
            if (enterCalibrationFlag)
            {
                Serial.println();
                Serial.println(F(">>>Exit Calibration Mode<<<"));
                Serial.println();
                enterCalibrationFlag = 0;
            }
            else
            {
                Serial.println(F(">>>Error: Enter Calibration Mode<<<"));
            }
            break;
    }
}

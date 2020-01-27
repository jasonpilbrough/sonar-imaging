/* ========================================================================================
* FILENAME :        teensy_sonar.c           
*
* DESCRIPTION :
*       Routines for interfacing with sonar hardware using A/D and D/A 
*       converters on the Teensy 3.6 microcontroller.
*
* PUBLIC FUNCTIONS :
*       void    setup()
*       void    loop()
*       void    readAllPinsContinuous()
*       void    readAllPinsOnce()
*       void    sendAllBuffers()
*       void    sendBuffer0()
*       void    clearBuffers()
*       void    startDACtimer(microSecDelay)
*       void    DAC_timerInterupt()
*       double  convertCodeToVoltage(code)
*       double  DAC_speedTest(microSecDelay)
*       double  ADC_speedTest()
*       void    ADC_accuracyTest(trueValue)
*       
* NOTES :
*   -   No ADC sampling rate is specified anywhere in this script. This 
*       is because the ADC is set to automatically sample all channels as 
*       fast as possible. This was by design to maximise performance. 
* 
* AUTHOR :           Jason Pilbrough (jasonpilbrough@gmail.com)                
* START DATE :       07 Dec 2019
* 
*/


/* ==================================== INCLUDE FILES ===================================== */

#include <ADC.h>
#include <math.h>
#include "chirp_signal.h"

/* =================================== GLOBAL VARIABLES =================================== */

/* ----------------------------------- A/D CONVERTER -------------------------------------- */

ADC                   *adc              = new ADC();                         
ADC_CONVERSION_SPEED  CONVERSION_SPEED  = ADC_CONVERSION_SPEED::VERY_HIGH_SPEED;
ADC_SAMPLING_SPEED    SAMPLING_SPEED    = ADC_SAMPLING_SPEED::VERY_HIGH_SPEED;
ADC_REFERENCE         ADC_REF           = ADC_REFERENCE::REF_3V3; //reference voltage used by ADC
double                ADC_REF_VALUE     = 3.3;       //reference voltage used by ADC         
uint32_t              ADC_AVERAGING     = 1;         //number of samples to average   
uint32_t              ADC_RESOLUTION    = 10;        //number of bits       
uint32_t              ADC_GAIN          = 1;         //gain can be 1, 2, 4, 8, 16, 32 or 64           

/* -------------------------------- ANALOGUE INPUT PINS ----------------------------------- */

const int             READ_PIN0         = A0;       // ADC0
const int             READ_PIN1         = A1;       // ADC0
const int             READ_PIN2         = A2;       // ADC0
const int             READ_PIN3         = A3;       // ADC0
const int             READ_PIN4         = A16;      // ADC1
const int             READ_PIN5         = A17;      // ADC1
const int             READ_PIN6         = A18;      // ADC1
const int             READ_PIN7         = A19;      // ADC1

/* -------------------------------- INPUT DATA BUFFERS ------------------------------------ */

uint16_t              PIN0_BUFFER[10000];
uint16_t              PIN1_BUFFER[10000]; 
uint16_t              PIN2_BUFFER[10000];
uint16_t              PIN3_BUFFER[10000]; 
uint16_t              PIN4_BUFFER[10000];
uint16_t              PIN5_BUFFER[10000]; 
uint16_t              PIN6_BUFFER[10000];
uint16_t              PIN7_BUFFER[10000];
uint32_t              ARR_COUNTER        = 0; //counter to store the current number of samples in each buffer
uint32_t              BUFFER_LIMIT       = 6200; //number of samples to read into buffers each time

/* ----------------------------------- D/A CONVERTER -------------------------------------- */

IntervalTimer         MY_TIMER; 
double                TIMER_DELAY        = 1/CHIRP_SAMPLE_RATE * 1000000; //timer delay in microseconds

//use volatile for shared variables
volatile bool         TIMER_RUNNING;               //indicates if the DAC timer is running
volatile unsigned long OUTPUT_COUNTER    = 0;      //indicates the last value that was output

/* ----------------------------------- OUTPUT PINS ---------------------------------------- */

const int             LED_PIN            = 13;     // pin connected to LED
const int             OUTPUT_PIN         = A13;    // pin connected to transmitter

/* ================================ FUNCTION DEFINITIONS ================================== */

/*
 * Function:  setup 
 * ----------------
 * Configures all required I/O resources, including ADC and input/output pins.
 */
void setup(){

  //serial communications speed - USB is always 12 Mbit/sec
  Serial.begin(9600); 

  //configure all input pins to input mode
  pinMode(READ_PIN0, INPUT);
  pinMode(READ_PIN1, INPUT);
  pinMode(READ_PIN2, INPUT);
  pinMode(READ_PIN3, INPUT);
  pinMode(READ_PIN4, INPUT);
  pinMode(READ_PIN5, INPUT);
  pinMode(READ_PIN6, INPUT);
  pinMode(READ_PIN7, INPUT);

  //configure output pins   
  pinMode(OUTPUT_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
    
  //ADC0
  adc->setAveraging(ADC_AVERAGING, ADC_0); // set number of averages
  adc->setResolution(ADC_RESOLUTION, ADC_0); // set bits of resolution
  adc->setConversionSpeed(CONVERSION_SPEED, ADC_0);
  adc->setSamplingSpeed(SAMPLING_SPEED, ADC_0);
  adc->enablePGA(ADC_GAIN, ADC_0);
  adc->setReference(ADC_REF,ADC_0); 

  //ADC1
  adc->setAveraging(ADC_AVERAGING, ADC_1); // set number of averages
  adc->setResolution(ADC_RESOLUTION, ADC_1); // set bits of resolution
  adc->setConversionSpeed(CONVERSION_SPEED, ADC_1);
  adc->setSamplingSpeed(SAMPLING_SPEED, ADC_1);
  adc->enablePGA(ADC_GAIN, ADC_1);
  adc->setReference(ADC_REF,ADC_1); 
 
  delay(500);
  readAllPinsOnce(); //read all pins once during set up
  clearBuffers();
  delay(100);
  
}

/*
 * Function:  loop 
 * ----------------
 * Runs continuously, alternating between checking if any serial input and waiting.
 * 
 * The following command characters/strings are accepted:
 * 
 * i - info mode: confirm micro is connected and send ADC sample rate on Serial
 * f - full op mode: transmit chirp, sample return on 8 channels, send ADC speed and 8 buffers on Serial
 * g - short op mode: transmit chirp, sample return on 8 channels, but only send ADC speed and buffer0 on Serial
 * s - speed ADC: print ADC sample speed to Serial
 * t - speed DAC: print DAC sample speed to Serial
 * a <true value in mV> - accuracy ADC: print ADC accuracy measure to Serial. Enter as 'a <space> <voltage in mV>'
 * o - DAC out: output chirp using DAC (no ADC)
 * 
 */
void loop() {
    
    if (Serial.available()) {
      
        char c = Serial.read();

        if(c=='i') { 
            Serial.println("sample_rate");
            Serial.println(ADC_speedTest());

        } else if (c=='f'){
            int starttime = micros();
            Serial.println("sample_rate");
            Serial.println(ADC_speedTest());
            Serial.println("max_adc_code");
            Serial.println(1<<ADC_RESOLUTION);
            clearBuffers();
            
            OUTPUT_COUNTER = 0;
            startDACtimer(TIMER_DELAY);
            
            readAllPinsContinuous();
            sendAllBuffers();
      
            clearBuffers();
            Serial.print("Runtime: ");
            Serial.print(micros()-starttime);
            Serial.println(" us");
            
        } else if (c=='g'){
            int starttime = micros();
            Serial.println("sample_rate");
            Serial.println(ADC_speedTest());
            Serial.println("max_adc_code");
            Serial.println(1<<ADC_RESOLUTION);
            clearBuffers();
            
            OUTPUT_COUNTER = 0;
            startDACtimer(TIMER_DELAY);
            
            readAllPinsContinuous();
            sendBuffer0();
            
            clearBuffers();
            Serial.print("Runtime: ");
            Serial.print(micros()-starttime);
            Serial.println(" us");
            
        } else if(c=='s') { 
            Serial.println("ADC Speed test:");
            Serial.print(ADC_speedTest()/1000.0);
            Serial.println(" kHz");
        } else if (c=='t'){
            Serial.println("Speed Test - Writing to DAC: ");
            OUTPUT_COUNTER = 0;          
            double period_us = DAC_speedTest(TIMER_DELAY);
            Serial.print(period_us,3);
            Serial.println(" us");
        } else if(c=='a') { //enter 'a <space> <voltage in mV>'
            Serial.println("ADC Accuracy test:");
            ADC_accuracyTest(Serial.parseInt()/1000.0); //convert to V
        } else if (c=='o'){
            Serial.println("Writing to DAC");
            OUTPUT_COUNTER = 0;
            startDACtimer(TIMER_DELAY);
        }       
           
    }

    // Print ADC errors, if any.
    adc->printError();
    delay(100);

}


/*
 * Function:  readAllPinsContinuous 
 * -----------------------------
 * Reads all input pins continuously until buffer limit is reached.
 * 
 */
void readAllPinsContinuous(){

  for(int i =0; i< BUFFER_LIMIT; i++){
     readAllPinsOnce();
  }
  
}


/*
 * Function:  readAllPinsOnce 
 * -----------------------------
 * Reads each analogue input once using the ADC, and stores the resulting ADC code in the corresponsing buffer. 
 * Note that no ADC sampling rate is specified anywhere. This is because the ADC is set to automatically sample
 * all channels as fast as possible. 
 * 
 */
void readAllPinsOnce(){

    adc->startSynchronizedSingleRead(READ_PIN0, READ_PIN4);
    while(!adc->isComplete()){ } 
    ADC::Sync_result res = adc->readSynchronizedSingle();
    adc->startSynchronizedSingleRead(READ_PIN1, READ_PIN5); //NB the order of this command is important
    PIN0_BUFFER[ARR_COUNTER] = (uint16_t)(res.result_adc0);
    PIN4_BUFFER[ARR_COUNTER] = (uint16_t)(res.result_adc1);

    while(!adc->isComplete()){ } 
    res = adc->readSynchronizedSingle();
    adc->startSynchronizedSingleRead(READ_PIN2, READ_PIN6); //NB the order of this command is important
    PIN1_BUFFER[ARR_COUNTER] = (uint16_t)(res.result_adc0);
    PIN5_BUFFER[ARR_COUNTER] = (uint16_t)(res.result_adc1);
    
    while(!adc->isComplete()){ } 
    res = adc->readSynchronizedSingle();
    adc->startSynchronizedSingleRead(READ_PIN3, READ_PIN7); //NB the order of this command is important
    PIN2_BUFFER[ARR_COUNTER] = (uint16_t)(res.result_adc0);
    PIN6_BUFFER[ARR_COUNTER] = (uint16_t)(res.result_adc1);

    while(!adc->isComplete()){ } 
    res = adc->readSynchronizedSingle(); 
    PIN3_BUFFER[ARR_COUNTER] = (uint16_t)(res.result_adc0);
    PIN7_BUFFER[ARR_COUNTER] = (uint16_t)(res.result_adc1);
 
    ARR_COUNTER++;
    
}

/*
 * Function:  sendAllBuffers 
 * ---------------------------
 * Sends the contents of each buffer to Serial one after another. The format used is as follows:
 * 
 * "start_buffer_transfer"
 * "buffer0"
 * 123
 * 122
 * 345
 * ...
 * "buffer1"
 * ...
 * "buffer<n>"
 * ...
 * "end_buffer_transfer"
 * 
 */
void sendAllBuffers(){

  Serial.println("start_buffer_transfer");
  Serial.println("buffer0");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN0_BUFFER[i]);
  }
  Serial.println("buffer1");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN1_BUFFER[i]);
  }
  Serial.println("buffer2");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN2_BUFFER[i]);
  }
  Serial.println("buffer3");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN3_BUFFER[i]);
  }
  Serial.println("buffer4");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN4_BUFFER[i]);
  }
  Serial.println("buffer5");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN5_BUFFER[i]);
  }
  Serial.println("buffer6");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN6_BUFFER[i]);
  }
  Serial.println("buffer7");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN7_BUFFER[i]);
  }
  Serial.println("end_buffer_transfer");
  
}


/*
 * Function:  sendBuffer0 
 * ---------------------------
 * Sends the contents of buffer0 only to Serial one after another. The format used is as follows:
 * 
 * "start_buffer_transfer"
 * "buffer0"
 * 123
 * 122
 * 345
 * ...
 * "end_buffer_transfer"
 * 
 */
void sendBuffer0(){

  Serial.println("start_buffer_transfer");
  Serial.println("buffer0");
  for(uint32_t i = 0; i< ARR_COUNTER; i++){
     Serial.println(PIN0_BUFFER[i]);
  }
  Serial.println("end_buffer_transfer");
   
}






/*
 * Function:  clearBuffers 
 * -----------------------------
 * Clears the contents of each buffer by setting all values to 0.
 */
 void clearBuffers(){
    for(uint32_t i = 0; i < ARR_COUNTER; i++){
      PIN0_BUFFER[i]=0;
      PIN1_BUFFER[i]=0;
      PIN2_BUFFER[i]=0;
      PIN3_BUFFER[i]=0;
      PIN4_BUFFER[i]=0;
      PIN5_BUFFER[i]=0;
      PIN6_BUFFER[i]=0;
      PIN7_BUFFER[i]=0;
    }
    ARR_COUNTER=0;
  
 }

 





/*
 * Function:  startDACtimer 
 * ------------------------
 * Starts the DAC timer with a given delay between interupts.
 * 
 * microSecDelay: delay in microseconds between timer interrupts
 */
void startDACtimer(double microSecDelay){
  
    TIMER_RUNNING = true;
    MY_TIMER.begin(DAC_timerInterupt, microSecDelay); 
    while(TIMER_RUNNING){}  
    
}


/*
 * Function:  DAC_timerInterupt 
 * -----------------------------
 * Handles DAC timer interupts by writing the next value in the TX signal to the output pin.
 * Stops the timer when the entire TX signal has been sent. NB this function should run as fast as possible.
 */
void DAC_timerInterupt() {

  //stop timer if no more samples
  if(OUTPUT_COUNTER>NUM_SAMPLES){
     MY_TIMER.end();
     TIMER_RUNNING =false;
     return;
  }
  
  digitalWrite(OUTPUT_PIN, waveformLookup[OUTPUT_COUNTER]);
  digitalWrite(LED_PIN, waveformLookup[OUTPUT_COUNTER]);
  OUTPUT_COUNTER = OUTPUT_COUNTER + 1; 
  
}


/*
 * Function:  convertCodeToVoltage 
 * -------------------------------
 * Converts an ADC code into a voltage. NOT IN USE CURRENTLY - conversion to voltage in done in later signal processing as it 
 * takes a significant amount of time on the micro. 
 * 
 * value: ADC code to convert into a voltage
 * 
 * returns: the voltage equivalent to the given ADC code 
 */
double convertCodeToVoltage(uint16_t value){
  return ADC_REF_VALUE*value/(adc->getMaxValue());
}



/*
 * Function:  DAC_speedTest 
 * -------------------------------
 * Measures the time it takes to output the TX signal to the DAC. This can be used to verify that the TX signal is being 
 * generated correctly.
 * 
 * microSecDelay: delay in microseconds between timer interrupts
 *
 * returns: the time in microseconds to ouput TX signal
 */
double DAC_speedTest(double microSecDelay){

    TIMER_RUNNING = true;
    MY_TIMER.begin(DAC_timerInterupt, microSecDelay); 
    int starttime = micros();
 
    while(TIMER_RUNNING){}

    double period_us = (micros()-starttime);
    return period_us;

}



 

/*
 * Function:  ADC_speedTest 
 * -------------------------------
 * Measures the sampling rate of ADC when sampling all channels together. Note that no ADC sampling rate is specified 
 * anywhere. This is because the ADC is set to automatically sample all channels as fast as possible. 
 * 
 * returns: the sampling rate of the ADC in hz.
 */
 double ADC_speedTest(){

    int starttime = micros();
    double num_iterations = 100.0; //must be a double
       
    for(int i = 0; i< num_iterations; i++){    
        readAllPinsOnce(); 
    }
   
    double period_us = (micros()-starttime)/(num_iterations);
    double period_s =period_us/1000000.0;
    double freq_hz = 1/period_s;

    return freq_hz;

 }



/*
 * Function:  ADC_accuracyTest 
 * -------------------------------
 * Measures the accuracy of the ADC samples by comapring them to a true value that is provided. Prints the results of the
 * test to Serial. The same voltage much be present on all input channels for the results of this test to be valid. 
 * 
 * trueValue: the true value of the voltage at all channel inputs.
 */
void ADC_accuracyTest(double trueValue){

    double errorSquared[8];
    double num_iterations = 10000.0; //must be a double

    delay(500);
    for(int i = 0; i< num_iterations; i++){    
        readAllPinsOnce(); 
    }

    double tempValue;
    
    //init errorSquared arr
    for(uint32_t i = 0; i < 8; i++){
      errorSquared[i] = 0;
    }
    
    Serial.println("PIN0  PIN1  PIN2  PIN3  PIN4  PIN5  PIN6  PIN7");
    for(uint32_t i = 0; i < ARR_COUNTER; i++){
        tempValue = ADC_REF_VALUE*PIN0_BUFFER[i]/(adc->getMaxValue());
        errorSquared[0] = errorSquared[0] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN1_BUFFER[i]/(adc->getMaxValue());
        errorSquared[1] = errorSquared[1] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN2_BUFFER[i]/(adc->getMaxValue());
        errorSquared[2] = errorSquared[2] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN3_BUFFER[i]/(adc->getMaxValue());
        errorSquared[3] = errorSquared[3] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN4_BUFFER[i]/(adc->getMaxValue());
        errorSquared[4] = errorSquared[4] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN5_BUFFER[i]/(adc->getMaxValue());
        errorSquared[5] = errorSquared[5] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN6_BUFFER[i]/(adc->getMaxValue());
        errorSquared[6] = errorSquared[6] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN7_BUFFER[i]/(adc->getMaxValue());
        errorSquared[7] = errorSquared[7] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.println("");
    }
    Serial.println("Error Stats");
    Serial.println("---------------------------------------------");
    
    
    for(uint32_t i = 0; i < 8; i++){
        Serial.print(sqrt(errorSquared[i]/num_iterations),3);
        Serial.print(" ");
    }

    Serial.println("");
    clearBuffers();
 }







 /* 
    
    ADDITIONAL CODE WORTH KEEPING


    adc->startSingleRead(READ_PIN0, ADC_0);
    adc->startSingleRead(READ_PIN4, ADC_1);
    while(!adc->isComplete(ADC_0)){ } 
    PIN0_BUFFER[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_0);
    while(!adc->isComplete(ADC_1)){ }
    PIN4_BUFFER[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_1);

    adc->startSingleRead(READ_PIN1, ADC_0);
    adc->startSingleRead(READ_PIN5, ADC_1);
    while(!adc->isComplete(ADC_0)){ } 
    PIN1_BUFFER[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_0);
    while(!adc->isComplete(ADC_1)){ }
    PIN5_BUFFER[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_1);

    adc->startSingleRead(READ_PIN2, ADC_0);
    adc->startSingleRead(READ_PIN6, ADC_1);
    while(!adc->isComplete(ADC_0)){ } 
    PIN2_BUFFER[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_0);
    while(!adc->isComplete(ADC_1)){ }
    PIN6_BUFFER[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_1);

    adc->startSingleRead(READ_PIN3, ADC_0);
    adc->startSingleRead(READ_PIN7, ADC_1);
    while(!adc->isComplete(ADC_0)){ } 
    PIN3_BUFFER[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_0);
    while(!adc->isComplete(ADC_1)){ }
    PIN7_BUFFER[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_1);
   
  
  */

#include <ADC.h>
#include <math.h>
#include "chirp_signal.h"

//ADC AND PARAMS
ADC *adc = new ADC(); // adc object

ADC_CONVERSION_SPEED CONVERSION_SPEED = ADC_CONVERSION_SPEED::VERY_HIGH_SPEED;
ADC_SAMPLING_SPEED SAMPLING_SPEED = ADC_SAMPLING_SPEED::VERY_HIGH_SPEED;
ADC_REFERENCE ADC_REF = ADC_REFERENCE::REF_3V3; // change all 3.3 to 1.2 if you change the reference to 1V2
double ADC_REF_VALUE = 3.3;
uint32_t ADC_AVERAGING = 1; //number of samples to average
uint32_t ADC_RESOLUTION = 10; //bits
uint32_t ADC_GAIN = 1; //gain can be 1, 2, 4, 8, 16, 32 or 64

//ANALOGUE INPUT PINS
const int READ_PIN0 = A0; // ADC0
const int READ_PIN1 = A1; // ADC0
const int READ_PIN2 = A2; // ADC0
const int READ_PIN3 = A3; // ADC0
const int READ_PIN4 = A16; // ADC1
const int READ_PIN5 = A17; // ADC1
const int READ_PIN6 = A18; // ADC1
const int READ_PIN7 = A19; // ADC1

//DATA BUFFERS
uint32_t ARR_COUNTER = 0;
uint16_t PIN0_VALUES[10000];
uint16_t PIN1_VALUES[10000]; 
uint16_t PIN2_VALUES[10000];
uint16_t PIN3_VALUES[10000]; 
uint16_t PIN4_VALUES[10000];
uint16_t PIN5_VALUES[10000]; 
uint16_t PIN6_VALUES[10000];
uint16_t PIN7_VALUES[10000];


// VARIABLES FOR THE DAC
IntervalTimer MY_TIMER; // Create an IntervalTimer object 
double TIMER_DELAY = 1/CHIRP_SAMPLE_RATE * 1000000; //timer delay in microseconds
volatile bool TIMER_RUNNING;
volatile unsigned long OUTPUT_COUNTER = 0; // use volatile for shared variables

//OUPUT PINS
const int OUTPUT_PIN = 13;  // pin connected to transmitter


void setup(){

  Serial.begin(9600); // USB is always 12 Mbit/sec

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
    
  //ADC0
  adc->setAveraging(ADC_AVERAGING, ADC_0); // set number of averages
  adc->setResolution(ADC_RESOLUTION, ADC_0); // set bits of resolution
  adc->setConversionSpeed(CONVERSION_SPEED, ADC_0);
  adc->setSamplingSpeed(SAMPLING_SPEED, ADC_0);
  adc->enablePGA(ADC_GAIN, ADC_0);
  adc->setReference(ADC_REF,ADC_0); 
  //adc->enableInterrupts(ADC_0);

  //ADC1
  adc->setAveraging(ADC_AVERAGING, ADC_1); // set number of averages
  adc->setResolution(ADC_RESOLUTION, ADC_1); // set bits of resolution
  adc->setConversionSpeed(CONVERSION_SPEED, ADC_1);
  adc->setSamplingSpeed(SAMPLING_SPEED, ADC_1);
  adc->enablePGA(ADC_GAIN, ADC_1);
  adc->setReference(ADC_REF,ADC_1); 
 
  delay(500);
  read_all_pins_once(); //read all pins once during set up
  clearBuffers();
  delay(100);
  
}


void loop() {

/* The following command characters are accepted:

   i - info mode: confirm micro is connected and send ADC sample rate on Serial
   f - full op mode: transmit chirp, sample return on 8 channels, send ADC speed and 8 buffers on Serial
   g - short op mode: transmit chirp, sample return on 8 channels, but only send ADC speed and buffer0 on Serial

   s - speed ADC: print ADC sample speed to Serial
   t - speed DAC: print DAC sample speed to Serial
   a <true value in mV> - accuracy ADC: print ADC accuracy measure to Serial
   o - DAC out: output chirp using DAC (no ADC)
  
*/
    
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
            outputToDac(TIMER_DELAY);
            
            read_all_pins_cont();
            send_all_buffers();
      
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
            outputToDac(TIMER_DELAY);
            
            read_all_pins_cont();
            send_buffer0();
            
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
        } else if(c=='a') { //enter a <space> <voltage in mV>
            Serial.println("ADC Accuracy test:");
            ADC_accuracyTest(Serial.parseInt()/1000.0); //convert to V
        } else if (c=='o'){
            Serial.println("Writing to DAC");
            OUTPUT_COUNTER = 0;
            outputToDac(TIMER_DELAY);
        }       
           
    }

    // Print errors, if any.
    adc->printError();
    delay(100);

}


void read_all_pins_cont(){

  for(int i =0; i< 6200; i++){
     read_all_pins_once();
  }
  
}

void send_all_buffers(){

  Serial.println("start_buffer_transfer");
  Serial.println("buffer0");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN0_VALUES[i]);
  }
  Serial.println("buffer1");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN1_VALUES[i]);
  }
  Serial.println("buffer2");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN2_VALUES[i]);
  }
  Serial.println("buffer3");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN3_VALUES[i]);
  }
  Serial.println("buffer4");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN4_VALUES[i]);
  }
  Serial.println("buffer5");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN5_VALUES[i]);
  }
  Serial.println("buffer6");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN6_VALUES[i]);
  }
  Serial.println("buffer7");
  for(uint32_t i =0; i< ARR_COUNTER; i++){
     Serial.println(PIN7_VALUES[i]);
  }
  Serial.println("end_buffer_transfer");
  
}

void send_buffer0(){

  Serial.println("start_buffer_transfer");
  Serial.println("buffer0");
  for(uint32_t i = 0; i< ARR_COUNTER; i++){
     Serial.println(PIN0_VALUES[i]);
  }
  Serial.println("end_buffer_transfer");
   
}


double convertCodeToVoltage(uint16_t value){
  return ADC_REF_VALUE*value/(adc->getMaxValue());
}


void read_all_pins_once(){

    adc->startSynchronizedSingleRead(READ_PIN0, READ_PIN4);
    while(!adc->isComplete()){ } 
    ADC::Sync_result res = adc->readSynchronizedSingle();
    adc->startSynchronizedSingleRead(READ_PIN1, READ_PIN5); //NB the order of this command is important
    PIN0_VALUES[ARR_COUNTER] = (uint16_t)(res.result_adc0);
    PIN4_VALUES[ARR_COUNTER] = (uint16_t)(res.result_adc1);

    while(!adc->isComplete()){ } 
    res = adc->readSynchronizedSingle();
    adc->startSynchronizedSingleRead(READ_PIN2, READ_PIN6); //NB the order of this command is important
    PIN1_VALUES[ARR_COUNTER] = (uint16_t)(res.result_adc0);
    PIN5_VALUES[ARR_COUNTER] = (uint16_t)(res.result_adc1);
    
    while(!adc->isComplete()){ } 
    res = adc->readSynchronizedSingle();
    adc->startSynchronizedSingleRead(READ_PIN3, READ_PIN7); //NB the order of this command is important
    PIN2_VALUES[ARR_COUNTER] = (uint16_t)(res.result_adc0);
    PIN6_VALUES[ARR_COUNTER] = (uint16_t)(res.result_adc1);

    while(!adc->isComplete()){ } 
    res = adc->readSynchronizedSingle(); 
    PIN3_VALUES[ARR_COUNTER] = (uint16_t)(res.result_adc0);
    PIN7_VALUES[ARR_COUNTER] = (uint16_t)(res.result_adc1);
 

 
    ARR_COUNTER++;
    
}


 void clearBuffers(){
    for(uint32_t i = 0; i < ARR_COUNTER; i++){
      PIN0_VALUES[i]=0;
      PIN1_VALUES[i]=0;
      PIN2_VALUES[i]=0;
      PIN3_VALUES[i]=0;
      PIN4_VALUES[i]=0;
      PIN5_VALUES[i]=0;
      PIN6_VALUES[i]=0;
      PIN7_VALUES[i]=0;
    }
    ARR_COUNTER=0;
  
 }

 
// this function should run as fast as possible
void DAC_timerInterupt() {

  if(OUTPUT_COUNTER>NUM_SAMPLES){
     MY_TIMER.end();
     TIMER_RUNNING =false;
     return;
  }
  
  digitalWrite(OUTPUT_PIN, waveformLookup[OUTPUT_COUNTER]);
  OUTPUT_COUNTER = OUTPUT_COUNTER + 1; 
  
}

void outputToDac(double microSecDelay){
  
    TIMER_RUNNING = true;
    MY_TIMER.begin(DAC_timerInterupt, microSecDelay); 
    while(TIMER_RUNNING){}  
    
}

double DAC_speedTest(double microSecDelay){

    TIMER_RUNNING = true;
    MY_TIMER.begin(DAC_timerInterupt, microSecDelay); 
    int starttime = micros();
 
    while(TIMER_RUNNING){}

    double period_us = (micros()-starttime);
    return period_us;

}



 

 double ADC_speedTest(){

    int starttime = micros();
    double num_iterations = 100.0; //must be a double
       
    for(int i = 0; i< num_iterations; i++){    
        read_all_pins_once(); 
    }
   
    double period_us = (micros()-starttime)/(num_iterations);
    double period_s =period_us/1000000.0;
    double freq_hz = 1/period_s;


    return freq_hz;

 }

 void ADC_accuracyTest(double trueValue){

    double errorSquared[8];
    double num_iterations = 10000.0; //must be a double

    delay(500);
    for(int i = 0; i< num_iterations; i++){    
        read_all_pins_once(); 
    }

    double tempValue;
    
    //init errorSquared arr
    for(uint32_t i = 0; i < 8; i++){
      errorSquared[i] = 0;
    }
    
    Serial.println("PIN0  PIN1  PIN2  PIN3  PIN4  PIN5  PIN6  PIN7");
    for(uint32_t i = 0; i < ARR_COUNTER; i++){
        tempValue = ADC_REF_VALUE*PIN0_VALUES[i]/(adc->getMaxValue());
        errorSquared[0] = errorSquared[0] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN1_VALUES[i]/(adc->getMaxValue());
        errorSquared[1] = errorSquared[1] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN2_VALUES[i]/(adc->getMaxValue());
        errorSquared[2] = errorSquared[2] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN3_VALUES[i]/(adc->getMaxValue());
        errorSquared[3] = errorSquared[3] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN4_VALUES[i]/(adc->getMaxValue());
        errorSquared[4] = errorSquared[4] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN5_VALUES[i]/(adc->getMaxValue());
        errorSquared[5] = errorSquared[5] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN6_VALUES[i]/(adc->getMaxValue());
        errorSquared[6] = errorSquared[6] + (trueValue - tempValue) * (trueValue - tempValue);
        Serial.print(tempValue,3);
        Serial.print(" ");
        tempValue = ADC_REF_VALUE*PIN7_VALUES[i]/(adc->getMaxValue());
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


void print_buffer0(){

  for(uint32_t i = 0; i < ARR_COUNTER; i++){
    Serial.print(3.3*PIN0_VALUES[i]/(adc->getMaxValue()),3);
    Serial.print(" ");
  }
  Serial.println("");  
  
}



/*
    
    adc->startSingleRead(READ_PIN0, ADC_0);
    adc->startSingleRead(READ_PIN4, ADC_1);
    while(!adc->isComplete(ADC_0)){ } 
    PIN0_VALUES[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_0);
    while(!adc->isComplete(ADC_1)){ }
    PIN4_VALUES[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_1);

    adc->startSingleRead(READ_PIN1, ADC_0);
    adc->startSingleRead(READ_PIN5, ADC_1);
    while(!adc->isComplete(ADC_0)){ } 
    PIN1_VALUES[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_0);
    while(!adc->isComplete(ADC_1)){ }
    PIN5_VALUES[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_1);

    adc->startSingleRead(READ_PIN2, ADC_0);
    adc->startSingleRead(READ_PIN6, ADC_1);
    while(!adc->isComplete(ADC_0)){ } 
    PIN2_VALUES[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_0);
    while(!adc->isComplete(ADC_1)){ }
    PIN6_VALUES[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_1);

    adc->startSingleRead(READ_PIN3, ADC_0);
    adc->startSingleRead(READ_PIN7, ADC_1);
    while(!adc->isComplete(ADC_0)){ } 
    PIN3_VALUES[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_0);
    while(!adc->isComplete(ADC_1)){ }
    PIN7_VALUES[ARR_COUNTER] = (uint16_t)adc->readSingle(ADC_1);
  */

#include <HCSR04.h>

// pIN DIAGRAM - https://www.robot-electronics.co.uk/htm/srf04tech.htm

// Define the pins for the ultrasonic sensor
HCSR04 hc_lr(13, 12); //initialisation class HCSR04 (trig pin , echo pin)
HCSR04 hc_ud(11,10); //initialisation class HCSR04 (trig pin , echo pin)

// Define the pins for controlling the motor/actuator
#define UD_PIN_UP 9
#define UD_PIN_DOWN 6
#define LR_PIN_LEFT 5
#define LR_PIN_RIGHT 3

// Define fixed global variables.
float Home_Up = 51.5; // Neutral position in cm from the Right. It is then modified in movetoHome().
float Home_Right = 48.5; // Neutral position in cm from the Right. It is then modified in movetoHome().
const float Speed_ud = 3; //  Speed UD ~ 3 cm/sec
const float Speed_lr = 1.5; // Speed LR ~ 1.4 cm/sec
const float positions_ud[] = {0, 10, 20, 30, 40}; // Add more if needed (cm)
const float positions_lr[] = {0, 10, 20, 30, 40}; // Add more if needed (cm)
const int numPositions_ud = sizeof(positions_ud) / sizeof(positions_ud[0]);
const int numPositions_lr = sizeof(positions_lr) / sizeof(positions_lr[0]);
const int num_of_avg = 10; // Number of position values to count before yiedling the final answer.
const float thresh = 1.; // Threshold distance in cm close to target.
const unsigned long stayTime = 100000; // 10 seconds. time to stay at each position (in milliseconds)

void setup() { 
    
  // Initialize the motor/actuator control pins
  pinMode(UD_PIN_UP, INPUT); // INPUT =  This makes the pin high-impedance, effectively open
  pinMode(UD_PIN_DOWN, INPUT);
  pinMode(LR_PIN_LEFT, INPUT); // INPUT =  This makes the pin high-impedance, effectively open
  pinMode(LR_PIN_RIGHT, INPUT);
  
  Serial.begin(9600); 

  // Wait for the serial port to open in Python.
  while (!Serial) {
    ; // Wait here until the serial port is opened in Python code.
  }

  // Print a message to indicate that the Arduino is waiting for the 'S' character
  Serial.println("Waiting for the 'S' character to start...");

  // Wait for the 'S' character from Python before continuing
  while (Serial.read() != 'S') {
    // Do nothing, just wait
  }

  // Move to Home
  moveToHome();
}


void loop() {
    // Old code to test.
    // Serial.println( hc_ud.dist() ); //return current distance (cm) in serial
    // Serial.println( hc_lr.dist() ); //return current distance (cm) in serial
    // delay(1000);                   // we suggest to use over 60ms measurement cycle, in order to prevent trigger signal to the echo signal.
    
    static int currentPositionIndex_lr = 0; // Static variable to keep track of current lr position index
    static int currentPositionIndex_ud = 0; 

    // Check if there are lr positions to move
    if (currentPositionIndex_lr < numPositions_lr) 
    {
      // Check if there are ud positions to move
      if (currentPositionIndex_ud < numPositions_ud) 
      {
      // Move to the target position
      moveToPosition(positions_ud[currentPositionIndex_ud], positions_lr[currentPositionIndex_lr]);
      Serial.println("Moved to Up = " + String(curr_pos_ud(num_of_avg) - Home_Up) + " cm, Right = " + String(curr_pos_lr(num_of_avg) - Home_Right) + " cm");
      
      // Stay at the target position for the specified time for data acquisition
      // Serial.println("Staying at this position");
      delay(stayTime);
  
      // Move to the next ud position
      currentPositionIndex_ud++;
      } 
      else 
      {
      // All positions have been processed
      Serial.println("All up-down positions are reached for this lr.");
      // Move to the next lr position
      currentPositionIndex_lr++; // Increase the lr counter once ud sweep is done.
      currentPositionIndex_ud = 0; // Reseting ud counter to 0 for next lr.
      }
    }
    else 
    {
        // All positions have been processed
        Serial.println("All left-right positions are reached. Hence, all positions are reached");
        // Optionally, you can add code here to stop the operation or perform other actions
    }
}


// Function to move to Home position (U=0,R=0)
void moveToHome() {
  pinMode(LR_PIN_RIGHT, OUTPUT);
  digitalWrite(LR_PIN_RIGHT, HIGH);

  pinMode(UD_PIN_DOWN, OUTPUT);
  digitalWrite(UD_PIN_DOWN, LOW);

  Serial.println("Moving to the Home position i.e. bottom, right corner.");
  
  delay(40000); // Enough time to move to home position.
  
  pinMode(LR_PIN_RIGHT, INPUT);
  pinMode(UD_PIN_DOWN, INPUT);

  float Home_Up = curr_pos_ud(num_of_avg);
  float Home_Right = curr_pos_lr(num_of_avg);

  Serial.println("The Up Down Position is U = " + String(Home_Up) + " cm"); //return current distance (cm) in serial
  Serial.println("The Left Right Position is R = " + String(Home_Right) + " cm"); //return current distance (cm) in serial
}
  
void moveToPosition(float UD_targetPosition, float LR_targetPosition) {

  Serial.println("Moving UpDown to " + String(UD_targetPosition) + " cm, LeftRight = " + String(LR_targetPosition) + " cm.");

  float current_pos_ud = curr_pos_ud(num_of_avg);
  float current_pos_lr = curr_pos_lr(num_of_avg);

  float curr_rel_pos_ud = current_pos_ud - Home_Up;
  float curr_rel_pos_lr = current_pos_lr - Home_Right;

  float desired_mov_ud = UD_targetPosition - curr_rel_pos_ud; 
  float desired_mov_lr = LR_targetPosition - curr_rel_pos_lr;

  if (desired_mov_ud > 0) 
  {
    // Move up  
    moveUp(abs(desired_mov_ud));
    float diff_ud = UD_targetPosition - (curr_pos_ud(num_of_avg) - Home_Up);
    AdjustUpDown(diff_ud);
  }
  else if (desired_mov_ud < 0) 
  {
    // Move down
    moveDown(abs(desired_mov_ud));
    float diff_ud = UD_targetPosition - (curr_pos_ud(num_of_avg) - Home_Up);
    AdjustUpDown(diff_ud);
  }
  else 
  {
  }

  if (desired_mov_lr > 0) 
  {
    // Move left  
    moveLeft(abs(desired_mov_lr));
    float diff_lr = LR_targetPosition - (curr_pos_lr(num_of_avg) - Home_Right);
    AdjustLeftRight(diff_lr);
  }
  else if (desired_mov_lr < 0) 
  {
    // Move right
    moveRight(abs(desired_mov_lr));
    float diff_lr = LR_targetPosition - (curr_pos_lr(num_of_avg) - Home_Right);
    AdjustLeftRight(diff_lr);
  }
  else 
  {
  }

}

void moveUp(float distance) {
  int duration = abs(distance/Speed_ud) * 1000; // ms
  pinMode(UD_PIN_UP, OUTPUT);
  digitalWrite(UD_PIN_UP, LOW); // LOW = This connects the pin to GND. HIGH =  This connects the pin to Vcc.
  delay(duration);
  pinMode(UD_PIN_UP, INPUT);
}

void moveDown(float distance) {
  int duration = abs(distance/Speed_ud) * 1000; // ms
  pinMode(UD_PIN_DOWN, OUTPUT);
  digitalWrite(UD_PIN_DOWN, LOW); // LOW = This connects the pin to GND. HIGH =  This connects the pin to Vcc.
  delay(duration);
  pinMode(UD_PIN_DOWN, INPUT);
}

void moveLeft(float distance) {
  int duration = abs(distance/Speed_lr) * 1000; // ms
  pinMode(LR_PIN_LEFT, OUTPUT);
  digitalWrite(LR_PIN_LEFT, HIGH); // LOW = This connects the pin to GND. HIGH =  This connects the pin to Vcc.
  delay(duration);
  pinMode(LR_PIN_LEFT, INPUT);
}

void moveRight(float distance) {
  int duration = abs(distance/Speed_lr) * 1000; // ms
  pinMode(LR_PIN_RIGHT, OUTPUT);
  digitalWrite(LR_PIN_RIGHT, HIGH); // LOW = This connects the pin to GND. HIGH =  This connects the pin to Vcc.
  delay(duration);
  pinMode(LR_PIN_RIGHT, INPUT);
}

// Function for small final adjustments in ud.
void AdjustUpDown(float diff_ud) {
  if (diff_ud > 0) 
  {
    moveUp(abs(diff_ud) + 0.5);
  }
  else if (diff_ud < 0)
  {
    moveDown(abs(diff_ud)+ 0.5);
  }
  else
  {
  }
}

// Function for small final adjustments in lr.
void AdjustLeftRight(float diff_lr) {
  if (diff_lr > 0) 
  {
    moveLeft(abs(diff_lr)+ 0.5);
  }
  else if (diff_lr < 0)
  {
    moveRight(abs(diff_lr) + 0.5);
  }
  else
  {
  }
}



// Function to return the current ud position of the Ultrasonic sensor.
float curr_pos_ud(int num) {
  float curr_pos[num];
  for (int i = 0; i < num; i++) {
    curr_pos[i] = hc_ud.dist();
    delay(100);
  }

  float mode = getMode(curr_pos, num);
  return mode; 
}

// Function to return the current lr position of the Ultrasonic sensor.
float curr_pos_lr(int num) {
  float curr_pos[num];
  for (int i = 0; i < num; i++) {
    curr_pos[i] = hc_lr.dist();
    delay(100);
  }

  float mode = getMode(curr_pos, num);
  return mode;
}

// Function to get mode of an array
float getMode(float arr[], int size) {
  float mode = arr[0];
  int maxCount = 0;

  for (int i = 0; i < size; ++i) 
  {
    int count = 0;
    for (int j = 0; j < size; ++j) 
    {
      if (arr[j] == arr[i]) 
      {
        ++count;
      }
    }

    if (count > maxCount) 
    {
      maxCount = count;
      mode = arr[i];
    }
  }

  return mode;
}

// Function to test movement
void moveToPosition_test(int UD_targetPosition, int LR_targetPosition) {

  pinMode(LR_PIN_RIGHT, INPUT);
  pinMode(LR_PIN_LEFT, OUTPUT);
  digitalWrite(LR_PIN_LEFT, HIGH); // LOW = This connects the pin to GND. HIGH =  This connects the pin to Vcc.
  delay(4000); // Keep UP pin HIGH for 2000 milliseconds 
  pinMode(LR_PIN_LEFT, INPUT);
  
  pinMode(LR_PIN_RIGHT, OUTPUT);
  digitalWrite(LR_PIN_RIGHT, HIGH);
  delay(4000);
  pinMode(LR_PIN_RIGHT, INPUT);

  pinMode(UD_PIN_DOWN, INPUT);
  pinMode(UD_PIN_UP, OUTPUT);
  digitalWrite(UD_PIN_UP, LOW); // LOW = This connects the pin to GND. HIGH =  This connects the pin to Vcc.
  delay(4000);
  pinMode(UD_PIN_UP, INPUT);
  
  pinMode(UD_PIN_DOWN, OUTPUT);
  digitalWrite(UD_PIN_DOWN, LOW);
  delay(4000);
  pinMode(UD_PIN_DOWN, INPUT);
}

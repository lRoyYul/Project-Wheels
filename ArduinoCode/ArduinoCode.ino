const int pushButtonPin = 7;  
const int leftButtonPin = 8;
const int rightButtonPin = 12; 
const int pullButtonPin = 7; 
const int forwardPotPin = A0;  
const int directionPotPin = A1;

void setup() {
  pinMode(pushButtonPin, INPUT_PULLUP);
  pinMode(leftButtonPin, INPUT_PULLUP);
  pinMode(rightButtonPin, INPUT_PULLUP);
  pinMode(pullButtonPin, INPUT_PULLUP);

  Serial.begin(9600);
}

void loop() {
  int pushButtonState = digitalRead(pushButtonPin);
  int leftButtonState = digitalRead(leftButtonPin);
  int rightButtonState = digitalRead(rightButtonPin);
  int pullButtonState = digitalRead(pullButtonPin);
  

  if (pushButtonState != LOW && pushButtonState != HIGH) pushButtonState = 0;
  if (leftButtonState != LOW && leftButtonState != HIGH) leftButtonState = 0;
  if (rightButtonState != LOW && rightButtonState != HIGH) rightButtonState = 0;
  if (pullButtonState != LOW && pullButtonState != HIGH) pullButtonState = 0;

  int rawforwardValue = analogRead(forwardPotPin);
  int rawdirectionValue = analogRead(directionPotPin);

  if (rawforwardValue < 10) rawforwardValue = 0;
  if (rawdirectionValue < 10) rawdirectionValue = 0;

  Serial.print(pushButtonState);
  Serial.print(",");
  Serial.print(rawforwardValue);
  Serial.print(",");
  Serial.print(rawdirectionValue);
  Serial.print(",");
  Serial.print(leftButtonState);
  Serial.print(",");
  Serial.print(rightButtonState);
  Serial.print(",");
  Serial.println(pullButtonState);

  delay(10);
}

const int c1PushButtonPin = 7;  
const int c1LeftButtonPin = 8;
const int c1RightButtonPin = 12; 
const int c1PullButtonPin = 7; 
const int c1ForwardPotPin = A0;  
const int c1DirectionPotPin = A1;
const int c1BackButtonPin = 5;

void setup() {
  pinMode(c1PushButtonPin, INPUT_PULLUP);
  pinMode(c1LeftButtonPin, INPUT_PULLUP);
  pinMode(c1RightButtonPin, INPUT_PULLUP);
  pinMode(c1PullButtonPin, INPUT_PULLUP);
  pinMode(c1BackButtonPin, INPUT_PULLUP);

  Serial.begin(9600);
}

void loop() {
  int c1PushButtonState = digitalRead(c1PushButtonPin);
  int c1LeftButtonState = digitalRead(c1LeftButtonPin);
  int c1RightButtonState = digitalRead(c1RightButtonPin);
  int c1PullButtonState = digitalRead(c1PullButtonPin);
  int c1BackButtonState = digitalRead(c1BackButtonPin);
  

  if (c1PushButtonState != LOW && c1PushButtonState != HIGH) c1PushButtonState = 0;
  if (c1LeftButtonState != LOW && c1LeftButtonState != HIGH) c1LeftButtonState = 0;
  if (c1RightButtonState != LOW && c1RightButtonState != HIGH) c1RightButtonState = 0;
  if (c1PullButtonState != LOW && c1PullButtonState != HIGH) c1PullButtonState = 0;
  if (c1BackButtonState != LOW && c1BackButtonState != HIGH) c1BackButtonState = 0;

  int c1RawforwardValue = analogRead(c1ForwardPotPin);
  int c1RawdirectionValue = analogRead(c1DirectionPotPin);

  if (c1RawforwardValue < 10) c1RawforwardValue = 0;
  if (c1RawdirectionValue < 10) c1RawdirectionValue = 0;

  Serial.print("C1: ");
  Serial.print(c1PushButtonState);
  Serial.print(",");
  Serial.print(c1LeftButtonState);
  Serial.print(",");
  Serial.print(c1RightButtonState);
  Serial.print(",");
  Serial.print(c1BackButtonState);
  Serial.print(",");
  Serial.println(c1RawdirectionValue);
  
  delay(10);
}

import sys, signal, time
from evdev import InputDevice, categorize, ecodes, list_devices
import RPi.GPIO as GPIO

ENA = 12
IN1 = 5
IN2 = 6
DUTY = 70

def pick_gamepad():
  for path in list_devices():
    dev = InputDevice(path)
    name = (dev.name or "").lower()
    if any(k in name for k in ["xbox", "adaptive", "gamepad", "controller", "joystick"]):
      return dev
  devs = list_devices()
  if devs:
    return InputDevice(devs[0])
  raise RuntimeError("device not found")

GPIO.setupmode(GPIO.BCM)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)
pwm = GPIO.PWM(ENA, 1000)
pwm.start(0)

def motor_on():
  GPIO.output(IN1, GPIO.HIGH)
  GPIO.output(IN2, GPIO.LOW)
  pwm.ChangeDutyCycle(DUTY)

def motor_off():
  GPIO.output(IN1, GPIO.LOW)
  GPIO.output(IN2, GPIO.LOW)
  pwm.ChangeDutyCycle(0)

def cleanup_and_exit(code=0):
  try:
    motor_off()
    pwm.stop()
    GPIO.cleanup()
  finally:
    sys.exit(code)

def main():
  signal.signal(signal.SIGINT, lambda s,f: cleanup_and_exit(0))
  signal.signal(signal.SIGTERM, lambda s,f: cleanup_and_exit(0))
  
  dev = InputDevice('/dev/input/event6')
  print(f"Using: {dev.path} ({dev.name})")
  print("start")
  
  A_BTN = ecodes.BTN_SOUTH

  with pick_gamepad() as dev:
    motor_off()
    for event in dev.read_loop():
      if event.type == ecodes.EV_KEY:
        keyevent = categorize(event)
        print(keyevent)
        if keyevent.scancode == A_BTN:
          if keyevent.keystate == 1:
            motor_on()
            print("on")
          elif keyevent.keystate == 0:
            motor_off()
            print("off")

if__name__ == "__main__":
      try:
        main()
      except Exception as e:
        print("Error:", e)
        cleanup_and_exit(1)
Exception ignored in: <function PWM.__del__ at 0x7fff50eca0c0>
traceback (most recent call last):
File "/usr/lib/python3/dist-packages/RPi/GPIO/__init__.py", line 179, in __del__
File "/usr/lib/python3/dist-packages/RPi/GPIO/__init__.py", line 202, in sotp
File "/usr/lib/python3/dist-packages/lgpio.py", line 1084, in tx_pwm
TypeError: unsuported Operand types(s) for &: 'NoneType' and 'int'

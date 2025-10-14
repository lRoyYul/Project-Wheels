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

GPIO.setmode(GPIO.BCM)
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

# def cleanup_and_exit(code=0):
  # try:
   # motor_off()
   # pwm.stop()
   # GPIO.cleanup()
  # finally:
   # sys.exit(code)

def main():
  # signal.signal(signal.SIGINT, lambda s,f: cleanup_and_exit(0))
  # signal.signal(signal.SIGTERM, lambda s,f: cleanup_and_exit(0))
  
  dev = InputDevice('/dev/input/event10')
  print(f"Using: {dev.path} ({dev.name})")
  print("start")
  
  A_BTN = ecodes.BTN_SOUTH
  PROBLEM_BTN = A_BTN

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
      elif keyevent.scancode == PROBLEM_BTN:
        pass

if__name__ == "__main__":
      try:
        main()
      except KeyboardInterrupt:
        print("Keyboard Interrupt")
      except Exception as e:
        print("Error:", e)
      finally:
        print("GPIO Cleanup")
        motor_off()
        pwm.stop()
        GPIO.cleanup()
        print("done")

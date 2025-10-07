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

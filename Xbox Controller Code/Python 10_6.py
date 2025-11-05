import sys, signal, time
from evdev import InputDevice, categorize, ecodes, list_devices
import RPi.GPIO as GPIO

ENA = 12
IN1 = 5
IN2 = 6
DUTY = 70

def pick_gamepad():
    # Prefer Wireless; fall back to Adaptive; otherwise raise
    want_primary = "xbox wireless controller"
    want_fallback = "xbox adaptive controller"

    primary = None
    fallback = None

    for path in list_devices():
        dev = InputDevice(path)
        name = (dev.name or "").strip().lower()
        if name == want_primary:
            primary = dev
            break                     # best possible match
        if fallback is None and name == want_fallback:
            fallback = dev            # remember but keep looking for primary

    if primary:
        return primary
    if fallback:
        return fallback
    raise RuntimeError("Supported controller not found (need Xbox Wireless Controller or Xbox Adaptive Controller)")

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

def cleanup_and_exit(code=0):
    try:
        motor_off()
        pwm.stop()
        GPIO.cleanup()
    finally:
        sys.exit(code)

def main():
    signal.signal(signal.SIGINT,  lambda s, f: cleanup_and_exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: cleanup_and_exit(0))

    dev = pick_gamepad()
    print(f"Using: {dev.path} ({dev.name})")
    print("start")

    A_BTN = ecodes.BTN_SOUTH

    motor_off()
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
            keyevent = categorize(event)
            print(keyevent)
            if keyevent.scancode == A_BTN:
                if keyevent.keystate == 1:      # key down
                    motor_on()
                    print("on")
                elif keyevent.keystate == 0:    # key up
                    motor_off()
                    print("off")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
        cleanup_and_exit(1)

import sys, signal, time
from select import select
from evdev import InputDevice, categorize, ecodes, list_devices
import RPi.GPIO as GPIO

ENA = 12
ENB = 22
IN1 = 5
IN2 = 6
IN3 = 17
IN4 = 27
DUTY = 100

WANT_WIRELESS = "xbox wireless controller"
WANT_ADAPTIVE = "xbox adaptive controller"

def find_controllers():
    wireless = None
    adaptive = None
    for path in list_devices():
        dev = InputDevice(path)
        name = (dev.name or "").strip().lower()
        if name == WANT_WIRELESS and wireless is None:
            wireless = dev
        elif name == WANT_ADAPTIVE and adaptive is None:
            adaptive = dev
    if not wireless and not adaptive:
        raise RuntimeError("Supported controller not found (need Xbox Wireless Controller or Xbox Adaptive Controller)")
    return wireless, adaptive

GPIO.setmode(GPIO.BCM)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)
pwm = GPIO.PWM(ENA, 1000)
pwm.start(0)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)
GPIO.setup(ENB, GPIO.OUT)
pwm2 = GPIO.PWM(ENB, 1000)
pwm2.start(0)

def motor_on():
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    pwm.ChangeDutyCycle(DUTY)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm2.ChangeDutyCycle(DUTY)

def motor_off():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    pwm.ChangeDutyCycle(0)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    pwm2.ChangeDutyCycle(0)

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

    wireless, adaptive = find_controllers()

    # Build the active device list. We process in priority order:
    # Wireless (0) before Adaptive (1).
    devices = []
    priority = {}
    if wireless:
        devices.append(wireless)
        priority[wireless.fd] = 0
        print(f"Found: {wireless.path} ({wireless.name}) [HIGH PRIORITY]")
    if adaptive:
        devices.append(adaptive)
        priority[adaptive.fd] = 1
        print(f"Found: {adaptive.path} ({adaptive.name}) [DEFAULT]")

    A_BTN = ecodes.BTN_SOUTH

    print("Listening for A button (press = motor on, release = motor off)")
    motor_off()

    # Read from both controllers. If both are ready in the same tick,
    # handle Wireless first by sorting ready fds by priority.
    while True:
        ready_fds, _, _ = select(devices, [], [])
        # Sort by our priority (lower number = higher priority)
        ready_fds.sort(key=lambda d: priority.get(d.fd, 99))
        for dev in ready_fds:
            for event in dev.read():
                if event.type == ecodes.EV_KEY:
                    keyevent = categorize(event)
                    # Debug print shows which controller generated the event
                    print(f"[{dev.name}] {keyevent}")
                    if keyevent.scancode == A_BTN:
                        if keyevent.keystate == 1:   # key down
                            motor_on()
                            print("on")
                        elif keyevent.keystate == 0: # key up
                            motor_off()
                            print("off")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
        cleanup_and_exit(1)

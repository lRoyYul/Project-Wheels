import sys, signal, time, errno
from select import select
from evdev import InputDevice, ecodes, list_devices
import RPi.GPIO as GPIO

ENA = 12
ENB = 22
IN1 = 5
IN2 = 6
IN3 = 17
IN4 = 27

STEER_EN  = 13
STEER_IN1 = 23
STEER_IN2 = 24

WANT_NORMAL   = "xbox wireless controller"
WANT_ADAPTIVE = "xbox adaptive controller"

# -------- GPIO (no PWM) --------
def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # Drive
    GPIO.setup(IN1, GPIO.OUT); GPIO.setup(IN2, GPIO.OUT)
    GPIO.setup(IN3, GPIO.OUT); GPIO.setup(IN4, GPIO.OUT)
    GPIO.setup(ENA, GPIO.OUT); GPIO.output(ENA, GPIO.HIGH)   # enable high
    GPIO.setup(ENB, GPIO.OUT); GPIO.output(ENB, GPIO.HIGH)

    # Steering
    GPIO.setup(STEER_IN1, GPIO.OUT); GPIO.setup(STEER_IN2, GPIO.OUT)
    GPIO.setup(STEER_EN,  GPIO.OUT); GPIO.output(STEER_EN,  GPIO.HIGH)

def drive_forward():
    GPIO.output(IN1, GPIO.HIGH); GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH); GPIO.output(IN4, GPIO.LOW) #THIS LINE NO WORK

def drive_backward():
    GPIO.output(IN1, GPIO.LOW);  GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW);  GPIO.output(IN4, GPIO.HIGH)

def drive_stop():
    GPIO.output(IN1, GPIO.LOW);  GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW);  GPIO.output(IN4, GPIO.LOW)

def steer_right():   # forward rotation = right
    GPIO.output(STEER_IN1, GPIO.HIGH); GPIO.output(STEER_IN2, GPIO.LOW)

def steer_left():    # reverse rotation = left
    GPIO.output(STEER_IN1, GPIO.LOW);  GPIO.output(STEER_IN2, GPIO.HIGH)

def steer_stop():
    GPIO.output(STEER_IN1, GPIO.LOW);  GPIO.output(STEER_IN2, GPIO.LOW)

def motor_all_stop():
    drive_stop(); steer_stop()

def cleanup_and_exit(code=0):
    try:
        motor_all_stop()
        GPIO.output(ENA, GPIO.LOW)
        GPIO.output(ENB, GPIO.LOW)
        GPIO.output(STEER_EN, GPIO.LOW)
        GPIO.cleanup()
    finally:
        sys.exit(code)

# -------- Controllers --------
def scan_controllers():
    normal = None
    adaptive = None
    for path in list_devices():
        try:
            dev = InputDevice(path)
            name = (dev.name or "").strip().lower()
            print(name)
            if name == WANT_NORMAL and normal is None:
                normal = dev
                print("find normal!")
            elif name == WANT_ADAPTIVE and adaptive is None:
                adaptive = dev
                print("find adaptive!")
        except Exception:
            print("NO")
            pass
    return normal, adaptive

def hat_dir(v):  # map D-pad value to -1/0/1
    return -1 if v < 0 else (1 if v > 0 else 0)

def main():
    signal.signal(signal.SIGINT,  lambda s,f: cleanup_and_exit(0))
    signal.signal(signal.SIGTERM, lambda s,f: cleanup_and_exit(0))

    setup_gpio()
    motor_all_stop()

    normal, adaptive = scan_controllers()
    devs = [d for d in (normal, adaptive) if d is not None]

    print("Listening...")

    norm_x = norm_y = 0
    adap_x = adap_y = 0

    while True:
        # If any controller missing, keep scanning to reattach
        if normal is None or adaptive is None:
            try:
                n_norm, n_adap = scan_controllers()
                if normal is None and n_norm is not None:
                    normal = n_norm
                    devs.append(normal)
                    print("Reconnected: Xbox Wireless Controller")
                if adaptive is None and n_adap is not None:
                    adaptive = n_adap
                    devs.append(adaptive)
                    print("Reconnected: Xbox Adaptive Controller")
            except Exception:
                pass  # just try again next loop

        if not devs:
            # No devices yet: idle and retry
            time.sleep(0.1)
            # Ensure outputs are safe
            motor_all_stop()
            continue

        rlist, _, _ = select(devs, [], [], 0.05)

        for dev in rlist:
            try:
                events = dev.read()
            except OSError as e:
                # Device disappeared; keep running and wait for reconnection
                if e.errno in (errno.ENODEV, errno.EIO, errno.ENOENT):
                    name = getattr(dev, 'name', 'unknown')
                    print(f"Disconnected: {name}")
                    try: dev.close()
                    except: pass
                    if normal is not None and dev.fd == normal.fd:
                        normal = None; norm_x = norm_y = 0
                    if adaptive is not None and dev.fd == adaptive.fd:
                        adaptive = None; adap_x = adap_y = 0
                    devs = [x for x in devs if x is not dev]
                    motor_all_stop()
                    continue
                else:
                    continue
            except BlockingIOError:
                continue

            is_norm = (normal is not None and dev.fd == normal.fd)
            is_adap = (adaptive is not None and dev.fd == adaptive.fd)

            for e in events:
                if e.type != ecodes.EV_ABS:
                    continue
                if e.code == ecodes.ABS_HAT0Y:       # Up/Down → drive
                    v = hat_dir(e.value)             # -1 forward, 1 backward, 0 stop
                    if is_norm:   norm_y = v
                    elif is_adap: adap_y = v
                elif e.code == ecodes.ABS_HAT0X:     # Left/Right → steer
                    v = hat_dir(e.value)             # -1 left, 1 right, 0 straight
                    if is_norm:   norm_x = v
                    elif is_adap: adap_x = v

        # Per-axis arbitration: Xbox preferred over Adaptive
        y_cmd = norm_y if norm_y != 0 else adap_y
        x_cmd = norm_x if norm_x != 0 else adap_x

        # Apply drive (Y axis)
        if y_cmd == -1:
            drive_forward()
        elif y_cmd == 1:
            drive_backward()
        else:
            drive_stop()

        # Apply steering (X axis)
        if x_cmd == -1:
            steer_left()
        elif x_cmd == 1:
            steer_right()
        else:
            steer_stop()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
        cleanup_and_exit(1)

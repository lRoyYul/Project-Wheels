import sys, signal, time, errno, os
from select import select
from evdev import InputDevice, ecodes, list_devices
import RPi.GPIO as GPIO
from oled_display import OLEDDisplay
from button_logger import ButtonPressLogger, timestamped_output_path

button_logger = None

M1_RPWM = 18   
M1_LPWM = 19   
M1_REN  = 17   
M1_LEN  = 27 

M2_RPWM = 12
M2_LPWM = 16
M2_REN  = 5
M2_LEN  = 6

STEER_RPWM = 23
STEER_LPWM = 24
STEER_REN  = 13
STEER_LEN  = 22

WANT_NORMAL   = "xbox wireless controller"
WANT_ADAPTIVE = "xbox adaptive controller"

WIRELESS_LEFT_JOYSTICK_BUTTON = ecodes.BTN_THUMBL
WIRELESS_RIGHT_JOYSTICK_BUTTON = ecodes.BTN_THUMBR
LOG_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

PWM_FREQ = 500

last_drive_dir = 0   
last_steer_dir = 0 

maxspeed = 50
data_collect_on=False

xac_enabled= True

ACCEL_RATE = 100 / 3.0
last_speed_time = time.time()

def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(M1_RPWM, GPIO.OUT)
    GPIO.setup(M1_LPWM, GPIO.OUT)
    GPIO.setup(M1_REN,  GPIO.OUT)
    GPIO.setup(M1_LEN,  GPIO.OUT)
    GPIO.output(M1_REN, 1)
    GPIO.output(M1_LEN, 1)

    global m1_pwm_fwd, m1_pwm_bwd
    m1_pwm_fwd = GPIO.PWM(M1_RPWM, PWM_FREQ)  
    m1_pwm_bwd = GPIO.PWM(M1_LPWM, PWM_FREQ)
    m1_pwm_fwd.start(0)
    m1_pwm_bwd.start(0)

    GPIO.setup(M2_RPWM, GPIO.OUT)
    GPIO.setup(M2_LPWM, GPIO.OUT)
    GPIO.setup(M2_REN,  GPIO.OUT)
    GPIO.setup(M2_LEN,  GPIO.OUT)
    GPIO.output(M2_REN, 1)
    GPIO.output(M2_LEN, 1)

    global m2_pwm_fwd, m2_pwm_bwd
    m2_pwm_fwd = GPIO.PWM(M2_RPWM, PWM_FREQ)
    m2_pwm_bwd = GPIO.PWM(M2_LPWM, PWM_FREQ)
    m2_pwm_fwd.start(0)
    m2_pwm_bwd.start(0)

    GPIO.setup(STEER_RPWM, GPIO.OUT)
    GPIO.setup(STEER_LPWM, GPIO.OUT)
    GPIO.setup(STEER_REN,  GPIO.OUT)
    GPIO.setup(STEER_LEN,  GPIO.OUT)
    GPIO.output(STEER_REN, 1)
    GPIO.output(STEER_LEN, 1)

    global steer_pwm_right, steer_pwm_left
    steer_pwm_right = GPIO.PWM(STEER_RPWM, PWM_FREQ)
    steer_pwm_left  = GPIO.PWM(STEER_LPWM, PWM_FREQ)
    steer_pwm_right.start(0)
    steer_pwm_left.start(0)


def drive_forward():
    m1_pwm_fwd.ChangeDutyCycle(currentspeed) 
    m1_pwm_bwd.ChangeDutyCycle(0)
    m2_pwm_fwd.ChangeDutyCycle(currentspeed) 
    m2_pwm_bwd.ChangeDutyCycle(0)

def drive_backward():
    m1_pwm_fwd.ChangeDutyCycle(0)
    m1_pwm_bwd.ChangeDutyCycle(currentspeed)
    m2_pwm_fwd.ChangeDutyCycle(0) 
    m2_pwm_bwd.ChangeDutyCycle(currentspeed)

def drive_stop():
    global last_drive_dir

    if last_drive_dir == -1:
        for dc in range(maxspeed, -1, -10):
            m1_pwm_fwd.ChangeDutyCycle(dc)
            m1_pwm_bwd.ChangeDutyCycle(0)
            m2_pwm_fwd.ChangeDutyCycle(dc)
            m2_pwm_bwd.ChangeDutyCycle(0)
            time.sleep(0.02)

    elif last_drive_dir == 1:
        for dc in range(maxspeed, -1, -10):
            m1_pwm_fwd.ChangeDutyCycle(0)
            m1_pwm_bwd.ChangeDutyCycle(dc)
            m2_pwm_fwd.ChangeDutyCycle(0)
            m2_pwm_bwd.ChangeDutyCycle(dc)
            time.sleep(0.02)

    m1_pwm_fwd.ChangeDutyCycle(0)
    m1_pwm_bwd.ChangeDutyCycle(0)
    m2_pwm_fwd.ChangeDutyCycle(0)
    m2_pwm_bwd.ChangeDutyCycle(0)

def update_current_speed(y_cmd):
    global currentspeed, last_speed_time

    now = time.time()
    dt = now - last_speed_time
    last_speed_time = now

    if y_cmd == 0:
        currentspeed = 0
        return

    if currentspeed <= maxspeed:
        currentspeed = min(currentspeed + ACCEL_RATE * dt, maxspeed)
    elif currentspeed > maxspeed:
        currentspeed = maxspeed

def steer_right():   
    steer_pwm_right.ChangeDutyCycle(100)
    steer_pwm_left.ChangeDutyCycle(0)

def steer_left():   
    steer_pwm_right.ChangeDutyCycle(0)
    steer_pwm_left.ChangeDutyCycle(100)

def steer_stop():
    steer_pwm_right.ChangeDutyCycle(0)
    steer_pwm_left.ChangeDutyCycle(0)

def motor_all_stop():
    drive_stop(); steer_stop()

def soft_drive(direction):
    global last_drive_dir


    if direction == last_drive_dir:

        if direction == -1:
            drive_forward()
        elif direction == 1:
            drive_backward()
        else:
            drive_stop()
        return
    
    if (last_drive_dir == -1 and direction == 1) or (last_drive_dir == 1 and direction == -1):
        drive_stop()
        time.sleep(0.15)   
    
    if direction == -1:
        drive_forward()
    elif direction == 1:
        drive_backward()
    else:
        drive_stop()

    last_drive_dir = direction

def soft_steer(direction):
    global last_steer_dir

    if direction == last_steer_dir:
        if direction == -1:
            steer_left()
        elif direction == 1:
            steer_right()
        else:
            steer_stop()
        return

    if (last_steer_dir == -1 and direction == 1) or (last_steer_dir == 1 and direction == -1):
        steer_stop()
        time.sleep(0.15)

    if direction == -1:
        steer_left()
    elif direction == 1:
        steer_right()
    else:
        steer_stop()

    last_steer_dir = direction

def cleanup_and_exit(code=0):
    try:
        motor_all_stop()
        if button_logger is not None:
            button_logger.close()
        if m1_pwm_fwd is not None: m1_pwm_fwd.stop()
        if m1_pwm_bwd is not None: m1_pwm_bwd.stop()
        if m2_pwm_fwd is not None: m2_pwm_fwd.stop()
        if m2_pwm_bwd is not None: m2_pwm_bwd.stop()
        if steer_pwm_right is not None: steer_pwm_right.stop()
        if steer_pwm_left  is not None: steer_pwm_left.stop()
        
        GPIO.output(M1_REN, 0)
        GPIO.output(M1_LEN, 0)
        GPIO.output(M2_REN, 0)
        GPIO.output(M2_LEN, 0)
        GPIO.output(STEER_REN, 0)
        GPIO.output(STEER_LEN, 0)

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

def print_combo_state(y_pressed, left_joystick_pressed, right_joystick_pressed):
    print(
        "Wireless combo state: "
        f"Y={y_pressed}, L3={left_joystick_pressed}, R3={right_joystick_pressed}",
        flush=True,
    )

def main():
    global xac_enabled, maxspeed, data_collect_on, button_logger
    
    signal.signal(signal.SIGINT,  lambda s,f: cleanup_and_exit(0))
    signal.signal(signal.SIGTERM, lambda s,f: cleanup_and_exit(0))

    setup_gpio()
    motor_all_stop()
    
    oled=OLEDDisplay()
    oled.update(maxspeed, data_collect_on)
    os.makedirs(LOG_DIRECTORY, exist_ok=True)
    button_logger = ButtonPressLogger(timestamped_output_path(LOG_DIRECTORY))
    print(f"Button logs: {os.path.abspath(LOG_DIRECTORY)}", flush=True)

    normal, adaptive = scan_controllers()
    devs = [d for d in (normal, adaptive) if d is not None]

    print("Listening...")

    norm_x = norm_y = 0
    adap_x = adap_y = 0
    wireless_y_pressed = False
    wireless_left_joystick_pressed = False
    wireless_right_joystick_pressed = False
    wireless_combo_active = False

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
                    button_logger.discard_device(dev)
                    try: dev.close()
                    except: pass
                    if normal is not None and dev.fd == normal.fd:
                        normal = None; norm_x = norm_y = 0
                        wireless_y_pressed = False
                        wireless_left_joystick_pressed = False
                        wireless_right_joystick_pressed = False
                        wireless_combo_active = False
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
                button_logger.process_event(dev, e)

                if is_norm:
                    previous_combo_state = (
                        wireless_y_pressed,
                        wireless_left_joystick_pressed,
                        wireless_right_joystick_pressed,
                    )
                    if e.type == ecodes.EV_KEY and e.code == ecodes.BTN_NORTH:
                        wireless_y_pressed = e.value == 1
                    elif e.type == ecodes.EV_KEY and e.code == WIRELESS_LEFT_JOYSTICK_BUTTON:
                        wireless_left_joystick_pressed = e.value == 1
                    elif e.type == ecodes.EV_KEY and e.code == WIRELESS_RIGHT_JOYSTICK_BUTTON:
                        wireless_right_joystick_pressed = e.value == 1

                    current_combo_state = (
                        wireless_y_pressed,
                        wireless_left_joystick_pressed,
                        wireless_right_joystick_pressed,
                    )
                    if current_combo_state != previous_combo_state:
                        print_combo_state(*current_combo_state)

                    combo_pressed = (
                        wireless_left_joystick_pressed
                        and wireless_right_joystick_pressed
                    )
                    if combo_pressed and not wireless_combo_active:
                        button_logger.start_new_file()
                    wireless_combo_active = combo_pressed

                if e.type == ecodes.EV_KEY and e.value==1:
                    if is_norm and e.code == ecodes.BTN_SOUTH:
                        xac_enabled = not xac_enabled
                        print("XAC enabled:",xac_enabled)
                        if not xac_enabled:
                            adap_x =0
                            adap_y =0
                            
                    elif is_norm and e.code == ecodes.BTN_NORTH:
                        maxspeed= max(10, maxspeed-10)
                        print("Speed:", maxspeed)
                        oled.update(maxspeed, data_collect_on)
                        
                    elif is_norm and e.code == ecodes.BTN_EAST:
                        maxspeed= min(100, maxspeed+10)
                        print("Speed:", maxspeed)
                        oled.update(maxspeed, data_collect_on)
                        
                    elif is_norm and e.code == ecodes.BTN_WEST:
                        data_collect_on=not data_collect_on
                        print("Data collect", data_collect_on)
                        oled.update(maxspeed, data_collect_on)
                        
                if e.code == ecodes.ABS_HAT0Y:       # Up/Down → drive
                    v = hat_dir(e.value)             # -1 forward, 1 backward, 0 stop
                    if is_norm:   norm_y = v
                    elif is_adap: adap_y = v
                elif e.code == ecodes.ABS_HAT0X:     # Left/Right → steer
                    v = hat_dir(e.value)             # -1 left, 1 right, 0 straight
                    if is_norm:   norm_x = v
                    elif is_adap: adap_x = v

        # Per-axis arbitration: Xbox preferred over Adaptive
        if xac_enabled:
            y_cmd = norm_y if norm_y != 0 else adap_y
            x_cmd = norm_x if norm_x != 0 else adap_x
        else:
            y_cmd=norm_y
            x_cmd=norm_x
        
        update_current_speed(y_cmd)
        
        soft_drive(y_cmd)
        soft_steer(x_cmd)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
        cleanup_and_exit(1)

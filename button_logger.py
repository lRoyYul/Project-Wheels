import argparse
import csv
import os
import signal
import time
from datetime import datetime, timezone

from evdev import InputDevice, ecodes, list_devices

WANT_NORMAL = "xbox wireless controller"
WANT_ADAPTIVE = "xbox adaptive controller"

BUTTON_MOVEMENTS = {
    ecodes.BTN_SOUTH: "toggle XAC",
    ecodes.BTN_NORTH: "decrease speed",
    ecodes.BTN_EAST: "increase speed",
    ecodes.BTN_WEST: "toggle data collection",
}

HAT_MOVEMENTS = {
    ecodes.ABS_HAT0Y: {
        -1: "drive forward",
        0: "stop driving",
        1: "drive backward",
    },
    ecodes.ABS_HAT0X: {
        -1: "steer left",
        0: "straighten steering",
        1: "steer right",
    },
}


def controller_name(device):
    return (device.name or "").strip().lower()


def find_controllers():
    devices = []
    for path in list_devices():
        try:
            device = InputDevice(path)
            if controller_name(device) in (WANT_NORMAL, WANT_ADAPTIVE):
                devices.append(device)
        except OSError:
            continue
    return devices


def event_label(event):
    if event.type == ecodes.EV_KEY and event.value in (0, 1):
        return ecodes.KEY.get(event.code, str(event.code)), BUTTON_MOVEMENTS.get(
            event.code, "unmapped"
        )

    if event.type == ecodes.EV_ABS and event.code in HAT_MOVEMENTS:
        movement = HAT_MOVEMENTS[event.code].get(event.value, "unmapped")
        axis = ecodes.ABS.get(event.code, str(event.code))
        return f"{axis}={event.value}", movement

    return None


def utc_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def timestamped_output_path(output_directory, prefix="button_presses"):
    os.makedirs(output_directory, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return os.path.join(output_directory, f"{prefix}_{timestamp}.csv")


class ButtonPressLogger:
    def __init__(self, output_path="button_presses.csv"):
        self.output_path = output_path
        output_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
        self.output_file = open(output_path, "a", newline="", encoding="utf-8")
        self.writer = csv.writer(self.output_file)
        self.active_presses = {}

        if not output_exists:
            self.writer.writerow(
            [
                "pressed_at_utc",
                "controller",
                "button",
                "movement",
                "duration_seconds",
            ]
            )
            self.output_file.flush()

    def process_event(self, device, event):
        label = event_label(event)
        if label is None:
            return

        button, movement = label
        key = (device.fd, event.type, event.code)
        event_time = event.timestamp() or time.time()

        if event.type == ecodes.EV_KEY and event.value == 1:
            self.active_presses[key] = (event_time, device.name or "unknown controller", button, movement)
        elif event.type == ecodes.EV_KEY and event.value == 0:
            self._finish_press(key, event_time)
        elif event.type == ecodes.EV_ABS and event.value != 0:
            if key in self.active_presses:
                if self.active_presses[key][3] == movement:
                    return
                self._finish_press(key, event_time)
            self.active_presses[key] = (event_time, device.name or "unknown controller", button, movement)
        elif event.type == ecodes.EV_ABS and event.value == 0:
            self._finish_press(key, event_time)

    def _finish_press(self, key, released_at):
        if key not in self.active_presses:
            return

        pressed_at, controller, button, movement = self.active_presses.pop(key)
        duration = max(0.0, released_at - pressed_at)
        self.writer.writerow(
            [
                utc_timestamp(pressed_at),
                controller,
                button,
                movement,
                f"{duration:.3f}",
            ]
        )
        self.output_file.flush()
        print(f"{button}: {movement} ({duration:.3f}s)", flush=True)

    def close(self):
        self.output_file.close()

    def start_new_file(self, output_directory=None):
        if output_directory is None:
            output_directory = os.path.dirname(os.path.abspath(self.output_path)) or "."
        output_path = timestamped_output_path(output_directory)
        new_output_file = open(output_path, "a", newline="", encoding="utf-8")
        new_writer = csv.writer(new_output_file)
        new_writer.writerow(
            [
                "pressed_at_utc",
                "controller",
                "button",
                "movement",
                "duration_seconds",
            ]
        )
        new_output_file.flush()

        self.output_file.close()
        self.output_path = output_path
        self.output_file = new_output_file
        self.writer = new_writer
        self.active_presses = {}
        print(f"Started new button log: {output_path}", flush=True)

    def discard_device(self, device):
        device_fd = device.fd
        self.active_presses = {
            key: value for key, value in self.active_presses.items() if key[0] != device_fd
        }


def main():
    parser = argparse.ArgumentParser(description="Record controller button presses to CSV")
    parser.add_argument("--output", default="button_presses.csv")
    args = parser.parse_args()
    logger = ButtonPressLogger(args.output)
    devices = []
    running = True

    def stop_logger(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop_logger)
    signal.signal(signal.SIGTERM, stop_logger)

    try:
        from select import select

        devices = find_controllers()
        while running:
            if not devices:
                print("No Xbox controller found; scanning again...", flush=True)
                time.sleep(1)
                devices = find_controllers()
                continue

            readable, _, _ = select(devices, [], [], 0.5)
            for device in readable:
                try:
                    for event in device.read():
                        logger.process_event(device, event)
                except OSError:
                    logger.discard_device(device)
                    device.close()
                    devices = [candidate for candidate in devices if candidate is not device]
    finally:
        for device in devices:
            device.close()
        logger.close()


if __name__ == "__main__":
    main()

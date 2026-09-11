from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw

class OLEDDisplay:
    def __init__(self):
        serial = i2c(port=1, address=0x3C)
        self.device = ssd1306(serial, width=128, height=64)

    def update(self, maxspeed, data_collect_on):
        image = Image.new("1", (128, 64))
        draw = ImageDraw.Draw(image)

        draw.text((0, 0), "Project WHEELS", fill=255)
        draw.text((0, 20), f"Speed: {maxspeed}%", fill=255)

        data_status = "ON" if data_collect_on else "OFF"
        draw.text((0, 40), f"Data: {data_status}", fill=255)

        self.device.display(image)

    def clear(self):
        self.device.clear()

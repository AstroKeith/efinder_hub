import serial
import os
import sys
from PIL import Image,ImageDraw,ImageFont


class Handpad:
    """All methods to work with the handpad"""

    def __init__(self, version, tiltSide="right") -> None:
        """Initialize the Handpad class,

        Parameters:
        version (str): The version of the eFinder software
        """
        global Image
        self.version = version
        self.side = tiltSide.lower()
        if self.side == 'auto':
            try:
                import board
                import adafruit_adxl34x
                i2c = board.I2C()
                self.tilt = adafruit_adxl34x.ADXL345(i2c)
            except:
                self.display("tilt set to auto","but no sensor","found")
                sys.exit()
        libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'drive')
        if os.path.exists(libdir):
            sys.path.append(libdir)
        from drive import SSD1305
        self.disp = SSD1305.SSD1305()
        self.disp.command(0x81)# set Contrast Control - 1st byte
        self.disp.command(0xFF)# set Contrast Control - 2nd byte - value
        self.disp.Init()
        self.disp.clear()
        self.width = self.disp.width
        self.height = self.disp.height
        self.image = Image.new('1', (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        self.font = ImageFont.truetype("/home/efinder/Solver/text.ttf",8)
        self.draw.rectangle((0,0,self.width,self.height), outline=0, fill=0)
        self.draw.text((1, 0),"ScopeDog eFinder", font=self.font, fill=255)
        self.draw.text((1, 8),"", font=self.font, fill=255)
        self.draw.text((1, 16),"",  font=self.font, fill=255)
        self.disp.getbuffer(self.image)
        self.disp.ShowImage()
        self.USB_module = False
        self.display("ScopeDog", "eFinder v" + self.version, "")

    def dispGoto(self, ddAz, ddAlt, dispAz, dispAlt, line2):
        def getDistanceDisplay(dd):
            dist = round(dd, 3) if dd < 0.01 else round(dd, 2) if dd < 10 else round(dd, 1)
            distFmt = '%1.3f' if dist < 0.01 else '%2.2f' if dist < 10 else '%3.1f'
            return (distFmt % dist)

        self.draw.rectangle((0,0,self.width,self.height), outline=0, fill=0)
        self.draw.text((51, 0), "Az " + dispAz, font=self.font, fill=255)
        self.draw.text((47, 10), "Alt " + dispAlt, font=self.font, fill=255)

        if ddAz > 180:
            ddAz = (ddAz - 180) * -1
        elif ddAz < -180:
            ddAz = (ddAz + 180) * -1

        if ddAz < 0:
            self.draw.polygon([(3, 1),(1, 3),(3, 5)], fill=255)
            self.draw.line([(7, 3),(4, 3)], fill=255)
        else:
            self.draw.polygon([(5, 1),(7, 3),(5, 5)], fill=255)
            self.draw.line([(1, 3),(4, 3)], fill=255)
        if ddAlt < 0:
            self.draw.polygon([(2, 14),(4, 16),(6, 14)], fill=255)
            self.draw.line([(4, 10),(4, 13)], fill=255)
        else:
            self.draw.polygon([(2, 12),(4, 10),(6, 12)], fill=255)
            self.draw.line([(4, 16),(4, 13)], fill=255)

        self.draw.text((10, 0), getDistanceDisplay(abs(ddAz)), font=self.font, fill=255)
        self.draw.text((10, 10), getDistanceDisplay(abs(ddAlt)), font=self.font, fill=255)
        self.draw.text((1, 20), line2, font=self.font, fill=255)
        im = self.image
        self.disp.getbuffer(im)
        self.disp.ShowImage()

    def findSide(self):
        if self.side == 'auto':
            return self.tilt.acceleration[1]
        elif self.side == 'left':
            return -1
        else:
            return 1


    def bright(self,brightness):
        self.disp.command(0x81)# set Contrast Control - 1st byte
        self.disp.command(int(brightness))# set Contrast Control - 2nd byte - value

    def display(self, line0: str, line1: str, line2: str) -> None:
        """Display the three lines on the display

        """
        self.draw.rectangle((0,0,self.width,self.height), outline=0, fill=0)
        self.draw.text((1, 0),line0, font=self.font, fill=255)
        self.draw.text((1, 10),line1, font=self.font, fill=255)
        self.draw.text((1, 20),line2,  font=self.font, fill=255)

        if self.findSide() < 0:
            im = self.image.transpose(Image.ROTATE_180)
        else:
            im = self.image

        self.disp.getbuffer(im)
        self.disp.ShowImage()

    def dispFocus(self, screen):
       
        if self.findSide() < 0:
            screen = screen.transpose(Image.ROTATE_180)

        self.draw.rectangle((0,0,self.width,self.height), outline=0, fill=0)
        self.disp.getbuffer(screen)
        self.disp.ShowImage()


    def get_box(self) -> serial.Serial:
        """Returns the box variable

        Returns:
        serial.Serial: The box variable"""
        return self.box

    def is_USB_module(self) -> bool:
        """Return true if the handbox is an OLED

        Returns:
        bool: True is the handbox is an OLED"""
        return self.USB_module

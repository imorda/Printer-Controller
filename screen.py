from threading import *
from time import sleep
import I2C_LCD_driver

class ScreenUpdater(Thread):
    def __init__(self, name, state, moveBtn, printBtn, encoder, updPeriod):
        Thread.__init__(self)
        self.name = name
        self.freq = updPeriod
        self.state = state
        self.lcd = None
        self.move = moveBtn
        self.print = printBtn
        self.enc = encoder

    def print_names(self):
        self.lcd.lcd_clear()
        self.lcd.lcd_display_string("LINE:", 1)
        self.lcd.lcd_display_string_pos("%", 1, 15)
        self.lcd.lcd_display_string("----", 2)
        self.lcd.lcd_display_string_pos("-----", 2, 11)

    def print_values(self):
        self.lcd.lcd_display_string_pos("    ", 1, 5)
        self.lcd.lcd_display_string_pos(str(self.state.curL), 1, 5)
        self.lcd.lcd_display_string_pos("    ", 1, 11)
        self.lcd.lcd_display_string_pos(str(int(self.enc.read() * 100 / self.state.width)), 1, 11)
        if self.move.isPressed():
            if self.state.direct:
                self.lcd.lcd_display_string("RIGHT", 2)
            else:
                self.lcd.lcd_display_string("LEFT ", 2)
        else:
            self.lcd.lcd_display_string("-----", 2)
        if self.print.isPressed():
            self.lcd.lcd_display_string_pos("PRINT", 2, 11)
        else:
            self.lcd.lcd_display_string_pos("-----", 2, 11)

    def run(self):
        self.lcd = I2C_LCD_driver.lcd()
        self.print_names()
        self.lcd.backlight(True)
        while True:
            try:
                self.print_values()
                sleep(self.freq)
            except KeyboardInterrupt:
                # cleanup
                break
            except Exception as e:
                print(e)
                break
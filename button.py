from RPi import GPIO
import keyboard


class Button:
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def isPressed(self):
        return not GPIO.input(self.pin)

    def set_callback(self, callback):
        GPIO.add_event_detect(self.pin, GPIO.FALLING, callback=callback, bouncetime=200)

    def dispose(self):
        GPIO.cleanup()


class VirtButton:
    def __init__(self, nameOn, nameOff):
        self.is_pressed = False
        self.nameOn = nameOn
        self.nameOff = nameOff
        keyboard.on_press(self.callback)
        self._callback = None

    def callback(self, key):
        if key.name == self.nameOn:
            self.is_pressed = True
            if self._callback:
                self._callback(None)
        elif key.name == self.nameOff:
            self.is_pressed = False

    def set_callback(self, callback):
        self._callback = callback

    def isPressed(self):
        return self.is_pressed

    def dispose(self):
        pass

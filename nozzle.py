from RPi import GPIO
from threading import *
from time import sleep
import numpy as np


class VirtualNozzle:
    def __init__(self, state):
        self.sig = np.zeros(shape=state.width + 1, dtype=np.uint32)
        self.wait = np.zeros(shape=state.width + 1, dtype=np.uint32)
        self.curL = -1


class Nozzle(Thread):
    def __init__(self, name, enc, pin, but, state):
        Thread.__init__(self)
        self.name = name
        self.state = state
        self.button = but
        self.pin = pin
        self.encoder = enc
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, 0)
        self.sig = np.zeros(shape=self.state.width + 1, dtype=np.uint32)
        self.wait = np.zeros(shape=self.state.width + 1, dtype=np.uint32)
        self.curL = -1
        self.isCleaning = False  # включается когда нужно чистить (выключает форсунку, чистит и выключает переменную)
        self.isOn = False
        self.isUpdating = False

    def run(self):
        while self.state.isAlive:
            try:
                if self.isCleaning:
                    GPIO.output(self.pin, 1)
                    sleep(self.state.cleanNozzleTime/1000)
                    GPIO.output(self.pin, 0)
                    self.isCleaning = False
                if self.button.isPressed() and self.state.curL == self.curL \
                        and not self.isUpdating and self.state.isFeedEnabled:
                    curpos = self.encoder.read()
                    if curpos >= 0 and curpos < self.state.width:
                        if self.sig[curpos] > 0 and self.wait[curpos] > 0:
                            self.isOn = not self.isOn
                            GPIO.output(self.pin, self.isOn)
                            if self.isOn:
                                sleep(self.sig[curpos] / 1000)
                                continue
                            else:
                                sleep(self.wait[curpos] / 1000)
                                continue
                        elif self.sig[curpos] > 0:
                            self.isOn = True
                            GPIO.output(self.pin, self.isOn)
                            sleep(self.sig[curpos]/1000)
                            continue
                self.isOn = False
                GPIO.output(self.pin, self.isOn)
                sleep(0.005)
            except KeyboardInterrupt:
                GPIO.cleanup()
                break
            except Exception as e:
                print(e)
                continue
